"""
backtest.py — Three-strategy comparative backtest engine.

Strategy 1 — plain_orb      : ORB + VWAP, no regime/VIX filter
Strategy 2 — orb_vix_beta   : ORB + VWAP + VIX beta ranking (no regime rotation)
Strategy 3 — full_system     : Complete regime engine, VVIX, sentiment, sector rotation

No lookahead bias: all indicators computed strictly on data available at bar time.
Slippage: 0.03% per entry and exit.
"""
from __future__ import annotations
import logging
import os
from dataclasses import dataclass, field
from datetime import date, datetime
from enum import Enum
from zoneinfo import ZoneInfo

import numpy as np
import pandas as pd

import config
import indicators as ind
from calendar_filter import is_high_impact_day, event_name, EarningsCalendar
from regime import Regime, RegimeEngine
from vix_factor import VIXBetaRanker
from vvix_filter import regime_filter
from sentiment import classify_put_call
from sector_rotation import get_rotation_universe
import performance as perf
from journal import save_trade, save_daily_performance, log_trade_close

logger = logging.getLogger(__name__)
ET = ZoneInfo(config.TIMEZONE)


class StrategyMode(Enum):
    PLAIN_ORB = "plain_orb"
    ORB_VIX_BETA = "orb_vix_beta"
    FULL_SYSTEM = "full_system"
    VWAP_FULL_SYSTEM = "vwap_full_system"
    LONG_SHORT_FULL_SYSTEM = "long_short_full_system"             # full_system + ORB shorts in B/C
    LONG_SHORT_GAP_ALIGNED = "long_short_gap_aligned"             # above + gap-direction filter (all regimes)
    LONG_SHORT_GAP_REGIME = "long_short_gap_regime_aware"         # above + gap filter only in GAP_ALIGNMENT_REGIMES
    LONG_SHORT_GAP_A_SHORTS = "long_short_gap_a_shorts"           # regime-aware + shorts ALSO fire in Regime A (experiment)
    LONG_SHORT_MTF_TREND = "long_short_mtf_trend"                 # regime-aware + per-symbol daily trend filter


def _is_long_short_mode(mode: "StrategyMode") -> bool:
    return mode in (
        StrategyMode.LONG_SHORT_FULL_SYSTEM,
        StrategyMode.LONG_SHORT_GAP_ALIGNED,
        StrategyMode.LONG_SHORT_GAP_REGIME,
        StrategyMode.LONG_SHORT_GAP_A_SHORTS,
        StrategyMode.LONG_SHORT_MTF_TREND,
    )


def _is_full_system_mode(mode: "StrategyMode") -> bool:
    return mode in (
        StrategyMode.FULL_SYSTEM,
        StrategyMode.VWAP_FULL_SYSTEM,
        StrategyMode.LONG_SHORT_FULL_SYSTEM,
        StrategyMode.LONG_SHORT_GAP_ALIGNED,
        StrategyMode.LONG_SHORT_GAP_REGIME,
        StrategyMode.LONG_SHORT_GAP_A_SHORTS,
        StrategyMode.LONG_SHORT_MTF_TREND,
    )


def _is_vix_beta_mode(mode: "StrategyMode") -> bool:
    return mode in (
        StrategyMode.ORB_VIX_BETA,
        StrategyMode.FULL_SYSTEM,
        StrategyMode.VWAP_FULL_SYSTEM,
        StrategyMode.LONG_SHORT_FULL_SYSTEM,
        StrategyMode.LONG_SHORT_GAP_ALIGNED,
        StrategyMode.LONG_SHORT_GAP_REGIME,
        StrategyMode.LONG_SHORT_GAP_A_SHORTS,
        StrategyMode.LONG_SHORT_MTF_TREND,
    )


# ── MTF helpers ───────────────────────────────────────────────────────────────

SYMBOL_TREND_MA_PERIOD: int = 20  # days


def _precompute_symbol_trends(bars_by_symbol: dict, period: int = SYMBOL_TREND_MA_PERIOD) -> dict:
    """
    For each symbol, return a Series indexed by trading_day with True/False:
    True = symbol's prior daily close was above its N-day SMA (i.e. uptrend at open today).
    Shift by 1 so trading_day's value reflects information from before the open.
    """
    trends: dict[str, pd.Series] = {}
    for sym, bars in bars_by_symbol.items():
        if bars.empty:
            continue
        daily_close = bars.groupby(bars.index.date)["close"].last()
        if daily_close.empty:
            continue
        daily_close.index = pd.to_datetime(daily_close.index)
        ma = daily_close.rolling(period, min_periods=max(5, period // 2)).mean()
        uptrend = (daily_close > ma).shift(1).fillna(False)
        trends[sym] = uptrend
    return trends


def _symbol_in_uptrend(trends: dict, sym: str, trading_day) -> bool:
    """Look up the precomputed uptrend bool for a symbol on a given day. Default True if missing."""
    s = trends.get(sym)
    if s is None or s.empty:
        return True
    key = pd.Timestamp(trading_day)
    if key in s.index:
        return bool(s.loc[key])
    # Fallback: take most recent value <= trading_day
    sub = s[s.index <= key]
    if sub.empty:
        return True
    return bool(sub.iloc[-1])


def _short_regimes_for_mode(mode: "StrategyMode") -> tuple:
    """LONG_SHORT_GAP_A_SHORTS lets shorts fire in A too; everyone else uses config.SHORT_REGIMES."""
    if mode == StrategyMode.LONG_SHORT_GAP_A_SHORTS:
        return ("A", "B", "C")
    return tuple(config.SHORT_REGIMES)


@dataclass
class BacktestConfig:
    mode: StrategyMode
    initial_equity: float = config.INITIAL_EQUITY
    slippage_pct: float = config.SLIPPAGE_PCT
    save_trades: bool = False
    trades_file: str = ""


class BacktestEngine:
    """
    Simulates all three strategy modes bar-by-bar with no lookahead.
    Processes timestamps chronologically across all symbols each day.
    """

    def __init__(self, bt_config: BacktestConfig):
        self.cfg = bt_config
        self.equity = bt_config.initial_equity
        self.trades: list[dict] = []
        self.daily_summaries: list[dict] = []
        self._regime_engine = RegimeEngine()
        self._vix_ranker = VIXBetaRanker()
        self._earnings_cal = EarningsCalendar()
        self._symbol_trends: dict = {}

    # ── Public API ────────────────────────────────────────────────────────────

    def run(
        self,
        bars_by_symbol: dict,
        vol_df: pd.DataFrame,        # columns: vix, vvix, vix3m
        spy_daily: pd.DataFrame,
        pc_series: pd.Series,
        daily_returns_by_sym: dict,
    ) -> dict:
        trading_days = self._trading_days(bars_by_symbol)
        if not trading_days:
            logger.warning("No trading days found in data")
            return {}

        logger.info(
            f"Backtest [{self.cfg.mode.value}] | "
            f"equity=${self.cfg.initial_equity:,.0f} | "
            f"days={len(trading_days)} ({trading_days[0]} → {trading_days[-1]})"
        )

        # Pre-fetch earnings dates once for all symbols
        logger.info("Pre-fetching earnings calendars...")
        self._earnings_cal.prefetch(list(bars_by_symbol.keys()))

        # Pre-compute full rolling VIX beta history once — avoids O(n²) refit per day
        if _is_vix_beta_mode(self.cfg.mode):
            if not vol_df.empty and "vix" in vol_df.columns:
                logger.info("Pre-computing VIX beta history...")
                self._vix_ranker.precompute(daily_returns_by_sym, vol_df["vix"])

        # Pre-compute per-symbol daily trends for MTF mode
        if self.cfg.mode == StrategyMode.LONG_SHORT_MTF_TREND:
            logger.info(f"Pre-computing per-symbol daily {SYMBOL_TREND_MA_PERIOD}d trends (MTF filter)...")
            self._symbol_trends = _precompute_symbol_trends(bars_by_symbol)

        for day in trading_days:
            self._simulate_day(
                day, bars_by_symbol, vol_df, spy_daily, pc_series, daily_returns_by_sym
            )

        metrics = perf.calculate_trade_metrics(self.trades)

        spy_bm = None
        if not spy_daily.empty:
            spy_bm = perf.spy_benchmark(spy_daily, self.cfg.initial_equity)

        mc = perf.monte_carlo(
            pd.Series([t["pnl"] for t in self.trades if t.get("result") in ("WIN", "LOSS")]),
            n_sims=2000,
            initial_equity=self.cfg.initial_equity,
        ) if len(self.trades) > 10 else None

        crisis_stats = None
        if not vol_df.empty and "vix" in vol_df.columns:
            crisis_stats = perf.crisis_period_performance(self.trades, vol_df["vix"])

        perf.print_full_report(
            metrics, spy_bm, self.cfg.initial_equity,
            monte_carlo_results=mc,
            crisis_stats=crisis_stats,
            strategy_name=self.cfg.mode.value,
        )

        if self.cfg.save_trades and self.trades:
            for t in self.trades:
                save_trade(t, self.cfg.trades_file)

        return metrics

    # ── Daily simulation ──────────────────────────────────────────────────────

    def _simulate_day(
        self,
        trading_day: date,
        bars_by_symbol: dict,
        vol_df: pd.DataFrame,
        spy_daily: pd.DataFrame,
        pc_series: pd.Series,
        daily_returns: dict,
    ):
        open_positions: dict = {}
        day_trades: list[dict] = []
        trades_today = 0
        daily_start_equity = self.equity
        daily_pnl = 0.0
        entered_today: set = set()

        # ── Calendar filter — skip FOMC, CPI, NFP days ────────────────────
        if is_high_impact_day(trading_day):
            logger.debug(f"[CAL] Skipping {trading_day} — {event_name(trading_day)} day")
            return

        # ── Gap filter — skip if SPY opens with a large gap ───────────────
        gap_too_large = False
        if config.ENABLE_GAP_FILTER and "SPY" in bars_by_symbol:
            spy_all = bars_by_symbol["SPY"]
            spy_today = spy_all[spy_all.index.date == trading_day]
            prev_days = spy_all[spy_all.index.date < trading_day]
            if not spy_today.empty and not prev_days.empty:
                spy_open = float(spy_today.iloc[0]["open"])
                spy_prev_close = float(prev_days.iloc[-1]["close"])
                gap_pct = abs(spy_open - spy_prev_close) / spy_prev_close
                if gap_pct > config.GAP_FILTER_PCT:
                    gap_too_large = True
                    logger.debug(f"[GAP] {trading_day} gap={gap_pct:.2%} — entries blocked")

        # ── Regime detection (end-of-previous-day data only) ──────────────
        as_of = pd.Timestamp(trading_day, tz=ET) - pd.Timedelta(minutes=1)

        if _is_vix_beta_mode(self.cfg.mode):
            regime_state = self._regime_engine.compute_from_dataframes(
                vol_df, spy_daily, pc_series, as_of
            )
            if self.cfg.mode == StrategyMode.ORB_VIX_BETA:
                regime_state.active_universe = config.MOMENTUM_UNIVERSE[:]
                regime_state.size_factor = 1.0
        else:
            regime_state = self._regime_engine._fallback_regime()

        # ── VIX beta ranking (long universe) ──────────────────────────────
        if _is_vix_beta_mode(self.cfg.mode):
            active_universe = self._vix_ranker.rank_at_date(
                regime_state.active_universe,
                as_of_date=as_of,
                top_fraction=config.TOP_SYMBOLS_FRACTION,
                regime_mode="defensive" if regime_state.regime == Regime.C else "momentum",
            )
        else:
            active_universe = config.MOMENTUM_UNIVERSE[:]

        # ── Short universe (long_short modes, regime gated by mode) ───────
        short_universe: list = []
        active_short_regimes = _short_regimes_for_mode(self.cfg.mode)
        if (
            _is_long_short_mode(self.cfg.mode)
            and regime_state.regime.value[0] in active_short_regimes
        ):
            short_universe = self._vix_ranker.rank_at_date(
                config.SHORT_UNIVERSE,
                as_of_date=as_of,
                top_fraction=config.TOP_SYMBOLS_FRACTION,
                regime_mode="short",
            )

        # ── VVIX filter ───────────────────────────────────────────────────
        if _is_full_system_mode(self.cfg.mode) and not vol_df.empty:
            vvix_val = float(vol_df[vol_df.index <= as_of]["vvix"].dropna().iloc[-1]) if "vvix" in vol_df else 100.0
            vvix_f = regime_filter(vvix_val)
        else:
            from vvix_filter import VVIXFilterResult
            vvix_f = VVIXFilterResult(True, 1.0, False, 100.0, 100.0, 0.0, "backtest_disabled")

        # ── Sentiment filter ──────────────────────────────────────────────
        if _is_full_system_mode(self.cfg.mode):
            pc_slice = pc_series[pc_series.index <= as_of] if not pc_series.empty else pd.Series([0.9])
            sent = classify_put_call(pc_slice)
        else:
            from sentiment import SentimentState, SentimentSignal
            sent = SentimentState(
                SentimentSignal.NEUTRAL, 0.9, 0.0, 0.9, 0.1,
                True, False, 1.0, "backtest_disabled"
            )

        # ── SPY daily trend filter (full_system only) ─────────────────────
        spy_uptrend = True
        if (
            _is_full_system_mode(self.cfg.mode)
            and config.SPY_TREND_FILTER
            and not spy_daily.empty
            and "close" in spy_daily.columns
        ):
            spy_slice = spy_daily[spy_daily.index <= as_of]["close"].dropna()
            if len(spy_slice) >= config.SPY_TREND_MA_PERIOD:
                spy_ma = float(spy_slice.tail(config.SPY_TREND_MA_PERIOD).mean())
                spy_uptrend = float(spy_slice.iloc[-1]) > spy_ma

        # ── Prior closes per symbol (for gap alignment) ───────────────────
        # Strict mode: gap filter on every day. Regime-aware mode: only when current regime
        # is in config.GAP_ALIGNMENT_REGIMES (default Regime A — gap continuation thesis).
        if self.cfg.mode == StrategyMode.LONG_SHORT_GAP_ALIGNED:
            gap_required = True
        elif self.cfg.mode in (
            StrategyMode.LONG_SHORT_GAP_REGIME,
            StrategyMode.LONG_SHORT_GAP_A_SHORTS,
            StrategyMode.LONG_SHORT_MTF_TREND,
        ):
            gap_required = regime_state.regime.value[0] in config.GAP_ALIGNMENT_REGIMES
        else:
            gap_required = False
        prior_closes: dict = {}
        if gap_required:
            for sym, all_b in bars_by_symbol.items():
                prior = all_b[all_b.index.date < trading_day]
                if not prior.empty:
                    prior_closes[sym] = float(prior.iloc[-1]["close"])

        # ── Build day bars dict ──────────────────────────────────────────
        day_bars: dict = {}
        all_ts: set = set()
        for sym, all_b in bars_by_symbol.items():
            db = all_b[all_b.index.date == trading_day]
            if not db.empty:
                day_bars[sym] = db
                all_ts.update(db.index)

        # ── Bar-by-bar simulation ─────────────────────────────────────────
        for ts in sorted(all_ts):
            current_time = ts.strftime("%H:%M")

            # Check open positions for stop/target/EOD
            for sym in list(open_positions.keys()):
                if sym not in day_bars or ts not in day_bars[sym].index:
                    continue
                bar = day_bars[sym].loc[ts]
                pos = open_positions[sym]
                pos_side = pos.get("side", "long")
                slip = self.cfg.slippage_pct

                if pos_side == "short":
                    # Short stop hit when price rallies >= stop
                    if float(bar["high"]) >= pos["stop_price"]:
                        fill = pos["stop_price"] * (1 + slip)
                        t = self._close(pos, fill, "STOP_LOSS", ts)
                        day_trades.append(t); daily_pnl += t["pnl"]; self.equity += t["pnl"]
                        del open_positions[sym]; log_trade_close(t); continue

                    if float(bar["low"]) <= pos["target_price"]:
                        fill = pos["target_price"] * (1 + slip)
                        t = self._close(pos, fill, "TAKE_PROFIT", ts)
                        day_trades.append(t); daily_pnl += t["pnl"]; self.equity += t["pnl"]
                        del open_positions[sym]; log_trade_close(t); continue

                    if current_time >= config.CLOSE_ALL_TIME:
                        fill = float(bar["close"]) * (1 + slip)
                        t = self._close(pos, fill, "EOD_CLOSE", ts)
                        day_trades.append(t); daily_pnl += t["pnl"]; self.equity += t["pnl"]
                        del open_positions[sym]; log_trade_close(t); continue
                else:
                    if float(bar["low"]) <= pos["stop_price"]:
                        fill = pos["stop_price"] * (1 - slip)
                        t = self._close(pos, fill, "STOP_LOSS", ts)
                        day_trades.append(t); daily_pnl += t["pnl"]; self.equity += t["pnl"]
                        del open_positions[sym]; log_trade_close(t); continue

                    if float(bar["high"]) >= pos["target_price"]:
                        fill = pos["target_price"] * (1 - slip)
                        t = self._close(pos, fill, "TAKE_PROFIT", ts)
                        day_trades.append(t); daily_pnl += t["pnl"]; self.equity += t["pnl"]
                        del open_positions[sym]; log_trade_close(t); continue

                    if current_time >= config.CLOSE_ALL_TIME:
                        fill = float(bar["close"]) * (1 - slip)
                        t = self._close(pos, fill, "EOD_CLOSE", ts)
                        day_trades.append(t); daily_pnl += t["pnl"]; self.equity += t["pnl"]
                        del open_positions[sym]; log_trade_close(t); continue

            # Entry scan
            if current_time < config.ORB_END_TIME or current_time >= config.LAST_ENTRY_TIME:
                continue
            if config.ENABLE_LUNCH_FILTER and config.LUNCH_BLOCK_START <= current_time < config.LUNCH_BLOCK_END:
                continue
            if gap_too_large:
                continue
            if len(open_positions) >= config.MAX_OPEN_POSITIONS:
                continue
            if trades_today >= config.MAX_TRADES_PER_DAY:
                continue
            if not vvix_f.can_trade:
                continue

            max_loss = daily_start_equity * config.DAILY_MAX_LOSS_PCT
            if daily_pnl < -max_loss:
                continue

            # Block Regime A momentum entries when SPY is below its 20d MA
            if (
                _is_full_system_mode(self.cfg.mode)
                and regime_state.regime == Regime.A
                and not spy_uptrend
            ):
                continue

            for sym in active_universe:
                if sym in entered_today or sym in open_positions:
                    continue
                if self._earnings_cal.is_earnings_day(sym, trading_day):
                    continue
                if sym not in day_bars or ts not in day_bars[sym].index:
                    continue

                bars_so_far = day_bars[sym][day_bars[sym].index <= ts]
                if len(bars_so_far) < 5:
                    continue

                opening_range = ind.calculate_opening_range(bars_so_far, trading_day)
                if opening_range is None:
                    continue

                vwap_s = ind.calculate_vwap(bars_so_far)
                avg_vol_s = ind.calculate_avg_volume(bars_so_far)
                atr_s = ind.calculate_atr(bars_so_far)
                if vwap_s.empty or avg_vol_s.empty or atr_s.empty:
                    continue

                bar = day_bars[sym].loc[ts]
                price = float(bar["close"])
                volume = float(bar["volume"])
                vwap = float(vwap_s.iloc[-1])
                avg_vol = float(avg_vol_s.iloc[-1])
                atr = float(atr_s.iloc[-1])
                orb_high = opening_range["high"]

                if self.cfg.mode == StrategyMode.VWAP_FULL_SYSTEM:
                    # VWAP reclaim: price must have dipped below VWAP earlier today
                    import datetime as _dt
                    orb_cutoff = _dt.datetime.strptime(config.ORB_END_TIME, "%H:%M").time()
                    post_orb = bars_so_far[bars_so_far.index.time > orb_cutoff]
                    if len(post_orb) < 2:
                        continue
                    prev_post_orb = post_orb.iloc[:-1]
                    prev_vwap = ind.calculate_vwap(bars_so_far).reindex(prev_post_orb.index)
                    touched_below = bool((prev_post_orb["low"].values < prev_vwap.values).any())
                    if not touched_below:
                        continue
                    c1 = price > vwap
                    c2 = avg_vol > 0 and volume > config.VWAP_VOL_MULTIPLIER * avg_vol
                    if not (c1 and c2):
                        continue
                    stop = min(
                        vwap * (1 - config.STOP_BUFFER_PCT),
                        ind.atr_stop_price(price, atr),
                    )
                else:
                    # ORB breakout entry
                    orb_range_pct = (opening_range["high"] - opening_range["low"]) / opening_range["low"]
                    if orb_range_pct < config.MIN_ORB_RANGE_PCT:
                        continue
                    c1 = price > orb_high
                    c2 = price > vwap
                    c3 = avg_vol > 0 and volume > config.VOLUME_MULTIPLIER * avg_vol
                    if not (c1 and c2 and c3):
                        continue
                    # MTF daily trend filter — long only if symbol above its 20d MA
                    if self.cfg.mode == StrategyMode.LONG_SHORT_MTF_TREND:
                        if not _symbol_in_uptrend(self._symbol_trends, sym, trading_day):
                            continue
                    # Gap-alignment filter (long_short_gap_aligned mode only)
                    if gap_required:
                        sym_open = float(day_bars[sym].iloc[0]["open"])
                        prior_c = prior_closes.get(sym)
                        if prior_c is None or prior_c <= 0:
                            continue
                        gap = (sym_open - prior_c) / prior_c
                        if gap < config.GAP_ALIGNMENT_THRESHOLD:
                            continue
                    stop = min(
                        vwap,
                        orb_high * (1 - config.STOP_BUFFER_PCT),
                        ind.atr_stop_price(price, atr),
                    )
                if stop >= price:
                    continue

                target = round(price + config.TAKE_PROFIT_R * (price - stop), 2)

                # Size
                regime_sf = regime_state.size_factor
                vvix_sf = vvix_f.size_multiplier
                sent_sf = sent.size_multiplier
                realized_vol = ind.calculate_realized_vol(
                    daily_returns.get(sym, pd.Series(dtype=float)).dropna()
                )
                vol_mult = ind.vol_adjusted_size_multiplier(realized_vol)

                risk_pct = (
                    config.RISK_PER_TRADE_PCT
                    * regime_sf * vvix_sf * sent_sf * vol_mult
                )
                risk_amount = self.equity * risk_pct
                rps = price - stop
                qty = int(risk_amount / rps) if rps > 0 else 0
                if qty <= 0:
                    continue

                entry_fill = price * (1 + self.cfg.slippage_pct)

                open_positions[sym] = {
                    "symbol": sym, "date": trading_day, "entry_time": ts,
                    "entry_price": entry_fill, "stop_price": stop, "target_price": target,
                    "qty": qty, "risk_per_share": max(entry_fill - stop, 0.0001),
                    "regime": regime_state.regime.value,
                    "vix_beta": self._vix_ranker.get_beta(sym),
                    "side": "long",
                    "setup": "orb",
                }
                entered_today.add(sym)
                trades_today += 1

            # ── Short entry scan (long_short modes only) ─────────────────
            if _is_long_short_mode(self.cfg.mode) and short_universe:
                for sym in short_universe:
                    if sym in entered_today or sym in open_positions:
                        continue
                    if len(open_positions) >= config.MAX_OPEN_POSITIONS:
                        break
                    if trades_today >= config.MAX_TRADES_PER_DAY:
                        break
                    if self._earnings_cal.is_earnings_day(sym, trading_day):
                        continue
                    if sym not in day_bars or ts not in day_bars[sym].index:
                        continue
                    bars_so_far = day_bars[sym][day_bars[sym].index <= ts]
                    if len(bars_so_far) < 5:
                        continue
                    opening_range = ind.calculate_opening_range(bars_so_far, trading_day)
                    if opening_range is None:
                        continue
                    vwap_s = ind.calculate_vwap(bars_so_far)
                    avg_vol_s = ind.calculate_avg_volume(bars_so_far)
                    atr_s = ind.calculate_atr(bars_so_far)
                    if vwap_s.empty or avg_vol_s.empty or atr_s.empty:
                        continue
                    bar = day_bars[sym].loc[ts]
                    price = float(bar["close"])
                    volume = float(bar["volume"])
                    vwap = float(vwap_s.iloc[-1])
                    avg_vol = float(avg_vol_s.iloc[-1])
                    atr = float(atr_s.iloc[-1])
                    orb_high = opening_range["high"]
                    orb_low = opening_range["low"]
                    orb_range_pct = (orb_high - orb_low) / orb_low if orb_low > 0 else 0
                    if orb_range_pct < config.MIN_ORB_RANGE_PCT:
                        continue
                    # VIX beta gate — only short fragile names
                    sym_beta = self._vix_ranker.get_beta(sym)
                    if sym_beta < config.SHORT_VIX_BETA_MIN:
                        continue
                    c1 = price < orb_low
                    c2 = price < vwap
                    c3 = avg_vol > 0 and volume > config.VOLUME_MULTIPLIER * avg_vol
                    if not (c1 and c2 and c3):
                        continue
                    # MTF daily trend filter — short only if symbol BELOW its 20d MA (downtrend)
                    if self.cfg.mode == StrategyMode.LONG_SHORT_MTF_TREND:
                        if _symbol_in_uptrend(self._symbol_trends, sym, trading_day):
                            continue
                    if gap_required:
                        sym_open = float(day_bars[sym].iloc[0]["open"])
                        prior_c = prior_closes.get(sym)
                        if prior_c is None or prior_c <= 0:
                            continue
                        gap = (sym_open - prior_c) / prior_c
                        if gap > -config.GAP_ALIGNMENT_THRESHOLD:
                            continue
                    stop = max(
                        vwap,
                        orb_low * (1 + config.STOP_BUFFER_PCT),
                        price + atr * config.ATR_STOP_MULTIPLIER,
                    )
                    if stop <= price:
                        continue
                    rps = stop - price
                    target = round(price - config.TAKE_PROFIT_R * rps, 2)
                    if target >= price or target <= 0:
                        continue
                    realized_vol = ind.calculate_realized_vol(
                        daily_returns.get(sym, pd.Series(dtype=float)).dropna()
                    )
                    vol_mult = ind.vol_adjusted_size_multiplier(realized_vol)
                    risk_pct = (
                        config.RISK_PER_TRADE_PCT
                        * regime_state.size_factor * vvix_f.size_multiplier
                        * sent.size_multiplier * vol_mult
                    )
                    risk_amount = self.equity * risk_pct
                    qty = int(risk_amount / rps) if rps > 0 else 0
                    if qty <= 0:
                        continue
                    entry_fill = price * (1 - self.cfg.slippage_pct)
                    open_positions[sym] = {
                        "symbol": sym, "date": trading_day, "entry_time": ts,
                        "entry_price": entry_fill, "stop_price": stop, "target_price": target,
                        "qty": qty, "risk_per_share": max(stop - entry_fill, 0.0001),
                        "regime": regime_state.regime.value,
                        "vix_beta": sym_beta,
                        "side": "short",
                        "setup": "short_orb",
                    }
                    entered_today.add(sym)
                    trades_today += 1

        # Force close any remaining positions at EOD
        for sym, pos in list(open_positions.items()):
            db = day_bars.get(sym, pd.DataFrame())
            slip_dir = 1 if pos.get("side") == "short" else -1   # short cover pays slippage; long sell loses it
            fill = float(db.iloc[-1]["close"]) * (1 + slip_dir * self.cfg.slippage_pct) if not db.empty else pos["entry_price"]
            exit_ts = db.index[-1] if not db.empty else None
            t = self._close(pos, fill, "EOD_CLOSE", exit_ts)
            day_trades.append(t); daily_pnl += t["pnl"]; self.equity += t["pnl"]

        self.trades.extend(day_trades)

        if day_trades:
            wins = [t for t in day_trades if t["pnl"] > 0]
            self.daily_summaries.append({
                "date": str(trading_day),
                "regime": regime_state.regime.value,
                "trades": len(day_trades),
                "wins": len(wins),
                "losses": len(day_trades) - len(wins),
                "gross_pnl": round(daily_pnl, 2),
                "win_rate": len(wins) / len(day_trades),
                "daily_return_pct": round(daily_pnl / daily_start_equity * 100, 4),
                "equity": round(self.equity, 2),
            })
            logger.info(
                f"[BT {self.cfg.mode.value}] {trading_day} | "
                f"{len(day_trades)} trades | P&L ${daily_pnl:+,.2f} | "
                f"equity=${self.equity:,.2f} | regime={regime_state.regime.value}"
            )

    @staticmethod
    def _trading_days(bars_by_symbol: dict) -> list:
        all_dates: set = set()
        for df in bars_by_symbol.values():
            if not df.empty:
                all_dates.update(df.index.date)
        return sorted(all_dates)

    @staticmethod
    def _close(pos: dict, exit_price: float, reason: str, exit_time) -> dict:
        side = pos.get("side", "long")
        if side == "short":
            pnl = (pos["entry_price"] - exit_price) * pos["qty"]
            r = (pos["entry_price"] - exit_price) / pos["risk_per_share"]
        else:
            pnl = (exit_price - pos["entry_price"]) * pos["qty"]
            r = (exit_price - pos["entry_price"]) / pos["risk_per_share"]
        return {
            "date": str(pos["date"]),
            "symbol": pos["symbol"],
            "side": side,
            "setup": pos.get("setup", "orb"),
            "entry_time": str(pos["entry_time"]),
            "exit_time": str(exit_time),
            "entry_price": round(pos["entry_price"], 4),
            "stop_price": round(pos["stop_price"], 4),
            "target_price": round(pos["target_price"], 4),
            "exit_price": round(exit_price, 4),
            "qty": pos["qty"],
            "pnl": round(pnl, 2),
            "r_multiple": round(r, 3),
            "result": "WIN" if pnl > 0 else "LOSS",
            "regime": pos.get("regime", ""),
            "vix_beta": round(pos.get("vix_beta", 0.0), 4),
            "reason": reason,
            "regime_size": "",
            "vol_mult": "",
            "atr": "",
            "vwap": "",
            "orb_high": "",
            "notes": "",
        }


# ── Three-way comparison runner ───────────────────────────────────────────────

DEFAULT_COMPARISON_MODES: list = [
    StrategyMode.PLAIN_ORB,
    StrategyMode.ORB_VIX_BETA,
    StrategyMode.FULL_SYSTEM,
    StrategyMode.VWAP_FULL_SYSTEM,
]

LONG_SHORT_COMPARISON_MODES: list = [
    StrategyMode.FULL_SYSTEM,                # baseline: long-only
    StrategyMode.LONG_SHORT_FULL_SYSTEM,     # +shorts in B/C
    StrategyMode.LONG_SHORT_GAP_ALIGNED,     # +shorts +gap-direction filter (all regimes)
    StrategyMode.LONG_SHORT_GAP_REGIME,      # +shorts +gap filter only in GAP_ALIGNMENT_REGIMES (default A)
    StrategyMode.LONG_SHORT_GAP_A_SHORTS,    # regime-aware + shorts ALSO fire in Regime A
    StrategyMode.LONG_SHORT_MTF_TREND,       # regime-aware + per-symbol daily trend filter (MTF)
]

# Focused 2-way head-to-head — does MTF stack add value on top of regime-aware?
MTF_HEAD_TO_HEAD_MODES: list = [
    StrategyMode.LONG_SHORT_GAP_REGIME,      # current best
    StrategyMode.LONG_SHORT_MTF_TREND,       # current best + MTF trend filter
]


def run_three_way_comparison(
    bars_by_symbol: dict,
    vol_df: pd.DataFrame,
    spy_daily: pd.DataFrame,
    pc_series: pd.Series,
    daily_returns_by_sym: dict,
    initial_equity: float = config.INITIAL_EQUITY,
    save_to_dir: str = None,
    modes: list = None,
) -> dict:
    """
    Run a set of strategies on the same data and print a side-by-side comparison.
    Defaults to the four long-only strategies; pass `modes=LONG_SHORT_COMPARISON_MODES`
    to compare long-only vs long+short vs long+short+gap-aligned.
    Returns dict of {strategy_name: metrics}.
    """
    if save_to_dir:
        os.makedirs(save_to_dir, exist_ok=True)

    if modes is None:
        modes = DEFAULT_COMPARISON_MODES

    results = {}
    for mode in modes:
        trades_file = os.path.join(save_to_dir, f"trades_{mode.value}.csv") if save_to_dir else ""
        bt_cfg = BacktestConfig(
            mode=mode,
            initial_equity=initial_equity,
            save_trades=bool(save_to_dir),
            trades_file=trades_file,
        )
        engine = BacktestEngine(bt_cfg)
        metrics = engine.run(bars_by_symbol, vol_df, spy_daily, pc_series, daily_returns_by_sym)
        results[mode.value] = metrics

    _print_comparison_table(results, initial_equity)
    return results


def _print_comparison_table(results: dict, initial_equity: float):
    """Print a side-by-side comparison of all strategies (dynamic column count)."""
    cols = list(results.keys())
    labels = {
        "plain_orb":                       "1. Plain ORB",
        "orb_vix_beta":                    "2. ORB+VIX Beta",
        "full_system":                     "3. ORB Full Sys",
        "vwap_full_system":                "4. VWAP Full Sys",
        "long_short_full_system":          "5. L+S Full Sys",
        "long_short_gap_aligned":          "6. L+S Gap All",
        "long_short_gap_regime_aware":     "7. L+S Gap A-only",
        "long_short_gap_a_shorts":         "8. L+S +A-Shorts",
        "long_short_mtf_trend":            "9. L+S +MTF Trend",
    }
    name_w = 18
    col_w = 17
    total_w = name_w + col_w * len(cols)
    print(f"\n{'='*total_w}\n  STRATEGY COMPARISON (same data, same period)\n{'='*total_w}")
    header_row = f"{'Metric':<{name_w}}" + "".join(f"{labels.get(c, c):<{col_w}}" for c in cols)
    print(header_row)
    print("-" * total_w)
    rows = [
        ("Trades",        "total_trades",    "{:.0f}"),
        ("Win Rate",      "win_rate",        "{:.1%}"),
        ("Total P&L",     "total_pnl",       "${:,.2f}"),
        ("Return",        None,              None),
        ("Profit Factor", "profit_factor",   "{:.2f}"),
        ("Avg R",         "avg_r_multiple",  "{:.2f}R"),
        ("Max Drawdown",  "max_drawdown_pnl","${:,.2f}"),
        ("Sharpe",        "sharpe",          "{:.2f}"),
    ]
    for label, key, fmt in rows:
        if key is None:
            vals = []
            for c in cols:
                ret = results.get(c, {}).get("total_pnl", 0) / initial_equity * 100
                vals.append(f"{ret:+.2f}%")
            print(f"{'Return':<{name_w}}" + "".join(f"{v:<{col_w}}" for v in vals))
        else:
            vals = []
            for c in cols:
                raw = results.get(c, {}).get(key, 0)
                try:
                    vals.append("∞" if raw == float("inf") else fmt.format(raw))
                except Exception:
                    vals.append(str(raw))
            print(f"{label:<{name_w}}" + "".join(f"{v:<{col_w}}" for v in vals))
    print("=" * total_w)
