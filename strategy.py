"""
strategy.py — Regime-aware ORB + VWAP entry signal generation.

Signal pipeline:
  1. Timing guards (ORB window, last entry, EOD)
  2. Regime filter (universe eligibility, size factor)
  3. VVIX filter (false-breakout risk, emergency mode)
  4. Sentiment filter (P/C overlay)
  5. VIX beta rank filter (only top-ranked names in regime)
  6. ORB + VWAP + volume confirmation
  7. ATR-based stop + dynamic sizing
  8. Portfolio/daily limit checks
"""
from __future__ import annotations
import logging
from dataclasses import dataclass, field
from datetime import datetime
from zoneinfo import ZoneInfo

import pandas as pd

import config
import indicators as ind
from calendar_filter import is_high_impact_day, event_name, EarningsCalendar

_earnings_cal = EarningsCalendar()
from regime import Regime, RegimeState
from vvix_filter import VVIXFilterResult
from sentiment import SentimentState
import risk as rsk

logger = logging.getLogger(__name__)
ET = ZoneInfo(config.TIMEZONE)


@dataclass
class TradeSignal:
    symbol: str
    entry_price: float
    stop_price: float
    target_price: float
    qty: int
    risk_amount: float
    risk_per_share: float
    regime: str
    vix_beta: float
    regime_size_factor: float
    vol_multiplier: float
    orb_high: float
    orb_low: float
    vwap: float
    atr: float
    reason: str
    sizing_breakdown: dict = field(default_factory=dict)


def check_entry_signal(
    symbol: str,
    bars: pd.DataFrame,
    account_equity: float,
    open_positions: dict,
    trades_today: int,
    daily_pnl: float,
    daily_start_equity: float,
    regime_state: RegimeState,
    vvix_filter: VVIXFilterResult,
    sentiment_state: SentimentState,
    vix_beta: float = 0.0,
    daily_returns: pd.Series | None = None,
    spy_uptrend: bool = True,
) -> TradeSignal | None:
    """
    Full regime-aware signal check. Returns TradeSignal or None.
    All inputs are from the current bar forward (no lookahead).
    """
    if bars.empty or len(bars) < 5:
        return None

    now = datetime.now(ET)
    current_time = now.strftime("%H:%M")
    today = now.date()

    # ── 0. Calendar + earnings filter ────────────────────────────────────
    if is_high_impact_day(today):
        logger.info(f"{symbol}: skipping — {event_name(today)} day (calendar filter)")
        return None
    if not _earnings_cal._fetched:
        _earnings_cal.prefetch([symbol])
    if _earnings_cal.is_earnings_day(symbol, today):
        logger.info(f"{symbol}: skipping — earnings day")
        return None

    # ── 1. Timing ─────────────────────────────────────────────────────────
    if current_time < config.ORB_END_TIME:
        return None
    if current_time >= config.LAST_ENTRY_TIME:
        return None
    if config.ENABLE_LUNCH_FILTER and config.LUNCH_BLOCK_START <= current_time < config.LUNCH_BLOCK_END:
        logger.info(f"{symbol}: lunch chop window — no entries {config.LUNCH_BLOCK_START}–{config.LUNCH_BLOCK_END}")
        return None

    # ── 2. Kill switch / daily limits ─────────────────────────────────────
    can_trade, limit_reason = rsk.check_daily_limits(trades_today, daily_pnl, daily_start_equity)
    if not can_trade:
        logger.info(f"{symbol}: halted — {limit_reason}")
        return None

    # ── 3. Regime universe check ───────────────────────────────────────────
    if symbol not in regime_state.active_universe:
        logger.debug(f"{symbol}: not in {regime_state.regime.value} universe")
        return None

    if symbol in open_positions:
        return None
    if len(open_positions) >= config.MAX_OPEN_POSITIONS:
        return None

    # ── 4. VVIX filter ────────────────────────────────────────────────────
    if not vvix_filter.can_trade:
        logger.info(f"{symbol}: VVIX blocked — {vvix_filter.reason}")
        return None

    # ── 5a. SPY daily trend gate ──────────────────────────────────────────
    if (
        config.SPY_TREND_FILTER
        and regime_state.regime == Regime.A
        and not spy_uptrend
    ):
        logger.debug(f"{symbol}: blocked — SPY below 20d MA, no Regime A entries")
        return None

    # ── 5b. Sentiment filter ──────────────────────────────────────────────
    # In Regime A, skip momentum entries when sentiment is extreme fear
    if regime_state.regime == Regime.A and not sentiment_state.allow_momentum_longs:
        logger.debug(f"{symbol}: sentiment blocks momentum — {sentiment_state.reason}")
        return None

    # ── 6. Indicators ────────────────────────────────────────────────────
    opening_range = ind.calculate_opening_range(bars, today)
    if opening_range is None:
        return None

    vwap_series = ind.calculate_vwap(bars)
    avg_vol_series = ind.calculate_avg_volume(bars)
    atr_series = ind.calculate_atr(bars)

    if vwap_series.empty or avg_vol_series.empty or atr_series.empty:
        return None

    bar = bars.iloc[-1]
    price = float(bar["close"])
    volume = float(bar["volume"])
    vwap = float(vwap_series.iloc[-1])
    avg_vol = float(avg_vol_series.iloc[-1])
    atr = float(atr_series.iloc[-1])
    orb_high = opening_range["high"]
    orb_low = opening_range["low"]

    # ── 7. ORB + VWAP + volume conditions ────────────────────────────────
    # Skip flat opens — not enough range to trade
    orb_range_pct = (orb_high - orb_low) / orb_low if orb_low > 0 else 0
    if orb_range_pct < config.MIN_ORB_RANGE_PCT:
        logger.debug(f"{symbol}: ORB range {orb_range_pct:.4f} too narrow, skipping")
        return None

    c1_orb = price > orb_high
    c2_vwap = price > vwap
    c3_vol = avg_vol > 0 and volume > config.VOLUME_MULTIPLIER * avg_vol

    # Optional: ATR expansion filter
    if config.ENABLE_ATR_EXPANSION_FILTER:
        c4_atr = ind.is_atr_expanding(atr_series)
    else:
        c4_atr = True

    if not (c1_orb and c2_vwap and c3_vol and c4_atr):
        logger.debug(
            f"{symbol}: ORB={c1_orb} VWAP={c2_vwap} VOL={c3_vol} ATR={c4_atr} "
            f"price={price:.2f} orb_high={orb_high:.2f} vwap={vwap:.2f}"
        )
        return None

    # ── 8. ATR-based stop ────────────────────────────────────────────────
    # Stop = lower of: VWAP, ORB high - buffer, or entry - ATR*mult
    stop_vwap = vwap
    stop_orb = orb_high * (1 - config.STOP_BUFFER_PCT)
    stop_atr = ind.atr_stop_price(price, atr)
    stop_price = min(stop_vwap, stop_orb, stop_atr)

    if stop_price >= price:
        logger.debug(f"{symbol}: stop {stop_price:.2f} >= price {price:.2f}")
        return None

    # ── 9. Vol-adjusted sizing ────────────────────────────────────────────
    realized_vol = None
    if daily_returns is not None and not daily_returns.empty:
        realized_vol = ind.calculate_realized_vol(daily_returns)

    sizing = rsk.calculate_position_size(
        account_equity=account_equity,
        entry_price=price,
        stop_price=stop_price,
        regime_size_factor=regime_state.size_factor,
        vvix_size_factor=vvix_filter.size_multiplier,
        sentiment_size_factor=sentiment_state.size_multiplier,
        realized_vol=realized_vol,
    )

    if sizing.qty <= 0:
        return None

    # ── 10. Portfolio exposure cap ────────────────────────────────────────
    can_add, exp_reason = rsk.check_portfolio_exposure(
        open_positions, sizing.qty, price, account_equity
    )
    if not can_add:
        logger.info(f"{symbol}: {exp_reason}")
        return None

    valid, err = rsk.validate_order(symbol, price, stop_price, sizing.target_price, sizing.qty)
    if not valid:
        logger.warning(f"{symbol}: invalid order — {err}")
        return None

    vol_ratio = volume / avg_vol if avg_vol > 0 else 0
    reason = (
        f"ORB break {orb_high:.2f} | VWAP {vwap:.2f} | vol {vol_ratio:.1f}x | "
        f"ATR {atr:.3f} | {regime_state.regime.value}"
    )

    logger.info(
        f"SIGNAL ▶ {symbol} | entry={price:.2f} stop={stop_price:.2f} "
        f"target={sizing.target_price:.2f} qty={sizing.qty} | {reason}"
    )

    return TradeSignal(
        symbol=symbol,
        entry_price=price,
        stop_price=stop_price,
        target_price=sizing.target_price,
        qty=sizing.qty,
        risk_amount=sizing.risk_amount,
        risk_per_share=sizing.risk_per_share,
        regime=regime_state.regime.value,
        vix_beta=vix_beta,
        regime_size_factor=regime_state.size_factor,
        vol_multiplier=sizing.vol_multiplier,
        orb_high=orb_high,
        orb_low=orb_low,
        vwap=vwap,
        atr=atr,
        reason=reason,
        sizing_breakdown=sizing.breakdown,
    )
