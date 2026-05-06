"""
strategy.py — Cameron VWAP-Bounce entry-signal generation.

Setup B only (VWAP Bounce). No Setup A breakout, no Setup C micro-pullback.

Long signal triggers when ALL of:
  1. close > VWAP                                      (above the line)
  2. close > 200 EMA                                   (regime filter)
  3. 9 EMA > 20 EMA                                    (trend confirmation)
  4. within last VWAP_PULLBACK_LOOKBACK_BARS, at least
     one bar's low touched VWAP within tolerance        (pullback signal)
  5. close > prior close                               (bounce signal)
  6. relative volume >= CAMERON_VOLUME_MULTIPLIER       (volume confirmation)

Short signal: full mirror.

Stop: min(prior 5 bar lows) for long, max for short. Skip the trade if
stop distance > ATR_GUARDRAIL_MULT × ATR (chop conditions, bad R:R).
Target: entry ± TAKE_PROFIT_R × risk_per_share (2R default).
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
import risk as rsk

_earnings_cal = EarningsCalendar()

logger = logging.getLogger(__name__)
ET = ZoneInfo(config.TIMEZONE)


@dataclass
class TradeSignal:
    symbol: str
    side: str                                  # "long" or "short"
    entry_price: float
    stop_price: float
    target_price: float
    qty: int
    risk_amount: float
    risk_per_share: float
    vwap: float
    ema_fast: float
    ema_mid: float
    ema_slow: float
    atr: float
    rvol: float
    reason: str
    sizing_breakdown: dict = field(default_factory=dict)
    setup: str = "vwap_bounce"
    limit_price: float | None = None           # set when USE_LIMIT_ORDER_ENTRIES; otherwise market


# ── Pullback detection ────────────────────────────────────────────────────────

def _recent_pullback_to_vwap(
    bars: pd.DataFrame,
    vwap_series: pd.Series,
    side: str,
    lookback: int,
    tolerance_pct: float,
) -> tuple[bool, float | None]:
    """Did at least one of the last `lookback` bars (excluding the current
    entry bar) touch VWAP within `tolerance_pct`?

    For long: bar.low came down to within tolerance of VWAP from above.
    For short: bar.high came up to within tolerance of VWAP from below.

    Returns (touched, touch_level).
    """
    if len(bars) < lookback + 1 or vwap_series.empty:
        return False, None

    recent_bars = bars.iloc[-(lookback + 1):-1]
    recent_vwap = vwap_series.iloc[-(lookback + 1):-1]

    if side == "long":
        threshold = recent_vwap * (1 + tolerance_pct)
        mask = recent_bars["low"] <= threshold
        if not mask.any():
            return False, None
        return True, float(recent_bars.loc[mask, "low"].min())

    if side == "short":
        threshold = recent_vwap * (1 - tolerance_pct)
        mask = recent_bars["high"] >= threshold
        if not mask.any():
            return False, None
        return True, float(recent_bars.loc[mask, "high"].max())

    return False, None


# ── Common gates ─────────────────────────────────────────────────────────────

def _gates_pass(
    symbol: str,
    open_positions: dict,
    trades_today: int,
    daily_pnl: float,
    daily_start_equity: float,
) -> tuple[bool, str]:
    now = datetime.now(ET)
    current_time = now.strftime("%H:%M")
    today = now.date()

    if is_high_impact_day(today):
        return False, f"calendar: {event_name(today)} day"
    if symbol not in _earnings_cal._cache:
        _earnings_cal.prefetch([symbol])
    if _earnings_cal.is_earnings_day(symbol, today):
        return False, "earnings day"

    if current_time >= config.LAST_ENTRY_TIME:
        return False, f"past LAST_ENTRY_TIME ({config.LAST_ENTRY_TIME})"
    if config.ENABLE_LUNCH_FILTER and config.LUNCH_BLOCK_START <= current_time < config.LUNCH_BLOCK_END:
        return False, f"lunch chop window {config.LUNCH_BLOCK_START}–{config.LUNCH_BLOCK_END}"

    can_trade, limit_reason = rsk.check_daily_limits(trades_today, daily_pnl, daily_start_equity)
    if not can_trade:
        return False, limit_reason

    if symbol in open_positions:
        return False, "already in open positions"
    if len(open_positions) >= config.MAX_OPEN_POSITIONS:
        return False, f"max open positions ({config.MAX_OPEN_POSITIONS}) reached"
    if symbol not in config.MOMENTUM_UNIVERSE:
        return False, "symbol not in MOMENTUM_UNIVERSE"

    return True, ""


# ── Entry signal — long ──────────────────────────────────────────────────────

def check_entry_signal(
    symbol: str,
    bars: pd.DataFrame,
    account_equity: float,
    open_positions: dict,
    trades_today: int,
    daily_pnl: float,
    daily_start_equity: float,
    daily_returns: pd.Series | None = None,
) -> TradeSignal | None:
    """VWAP-Bounce LONG signal."""
    if bars.empty or len(bars) < config.MIN_BARS_FOR_SIGNAL:
        return None

    ok, reason = _gates_pass(symbol, open_positions, trades_today, daily_pnl, daily_start_equity)
    if not ok:
        logger.info(f"{symbol} long: gate blocked — {reason}")
        return None

    vwap_series = ind.calculate_vwap(bars)
    ema_fast_s = ind.calculate_ema(bars["close"], config.EMA_FAST_PERIOD)
    ema_mid_s = ind.calculate_ema(bars["close"], config.EMA_MID_PERIOD)
    ema_slow_s = ind.calculate_ema(bars["close"], config.EMA_SLOW_PERIOD)
    atr_series = ind.calculate_atr(bars)
    rvol_series = ind.calculate_relative_volume(bars)

    if any(s.empty for s in (vwap_series, ema_fast_s, ema_mid_s, ema_slow_s, atr_series, rvol_series)):
        return None

    bar = bars.iloc[-1]
    prior = bars.iloc[-2]
    price = float(bar["close"])
    vwap = float(vwap_series.iloc[-1])
    ema_fast = float(ema_fast_s.iloc[-1])
    ema_mid = float(ema_mid_s.iloc[-1])
    ema_slow = float(ema_slow_s.iloc[-1])
    atr = float(atr_series.iloc[-1])
    rvol = float(rvol_series.iloc[-1]) if pd.notna(rvol_series.iloc[-1]) else 0.0

    c1 = price > vwap
    c2 = price > ema_slow
    c3 = ema_fast > ema_mid
    c5 = price > float(prior["close"])
    c6 = rvol >= config.CAMERON_VOLUME_MULTIPLIER
    c4, _ = _recent_pullback_to_vwap(
        bars, vwap_series,
        side="long",
        lookback=config.VWAP_PULLBACK_LOOKBACK_BARS,
        tolerance_pct=config.VWAP_PULLBACK_TOLERANCE_PCT,
    )

    if not (c1 and c2 and c3 and c4 and c5 and c6):
        logger.info(
            f"{symbol} long: setup incomplete | >VWAP={c1} >200EMA={c2} 9>20={c3} "
            f"pullback={c4} bounce={c5} rvol≥{config.CAMERON_VOLUME_MULTIPLIER}={c6} "
            f"(price={price:.2f} vwap={vwap:.2f} rvol={rvol:.2f})"
        )
        return None

    if len(bars) < config.STOP_LOOKBACK_BARS + 1:
        return None
    prior_lows = bars["low"].iloc[-(config.STOP_LOOKBACK_BARS + 1):-1]
    stop_price = float(prior_lows.min())
    if stop_price <= 0:
        return None
    risk_per_share = price - stop_price
    if risk_per_share <= 0:
        return None
    if risk_per_share > config.ATR_GUARDRAIL_MULT * atr:
        logger.info(
            f"{symbol} long: SKIP — stop distance ${risk_per_share:.2f} > "
            f"{config.ATR_GUARDRAIL_MULT}×ATR ${config.ATR_GUARDRAIL_MULT * atr:.2f} (chop)"
        )
        return None

    sizing = rsk.calculate_position_size(
        account_equity=account_equity,
        entry_price=price,
        stop_price=stop_price,
        side="long",
        realized_vol=ind.calculate_realized_vol(daily_returns) if daily_returns is not None else None,
    )
    if sizing.qty <= 0:
        return None

    notional = price * sizing.qty
    current_exposure = sum(p.get("qty", 0) * p.get("entry_price", 0) for p in open_positions.values())
    cap_ok, cap_reason = rsk.check_exposure_cap(account_equity, current_exposure, notional)
    if not cap_ok:
        logger.info(f"{symbol} long: exposure cap blocked — {cap_reason}")
        return None

    limit_price = price * (1 + config.LIMIT_ORDER_BUFFER_PCT) if config.USE_LIMIT_ORDER_ENTRIES else None

    return TradeSignal(
        symbol=symbol,
        side="long",
        entry_price=price,
        stop_price=stop_price,
        target_price=sizing.target_price,
        qty=sizing.qty,
        risk_amount=sizing.risk_amount,
        risk_per_share=risk_per_share,
        vwap=vwap,
        ema_fast=ema_fast,
        ema_mid=ema_mid,
        ema_slow=ema_slow,
        atr=atr,
        rvol=rvol,
        reason=(
            f"VWAP-Bounce long | price ${price:.2f} > VWAP ${vwap:.2f}, "
            f"9EMA > 20EMA > 200EMA stack, rvol {rvol:.2f}× | "
            f"stop ${stop_price:.2f} (5-bar low), risk ${risk_per_share:.2f}/sh "
            f"({risk_per_share / atr:.2f}×ATR)"
        ),
        sizing_breakdown=sizing.breakdown,
        limit_price=limit_price,
    )


# ── Entry signal — short ─────────────────────────────────────────────────────

def check_short_signal(
    symbol: str,
    bars: pd.DataFrame,
    account_equity: float,
    open_positions: dict,
    trades_today: int,
    daily_pnl: float,
    daily_start_equity: float,
    daily_returns: pd.Series | None = None,
) -> TradeSignal | None:
    """VWAP-Bounce SHORT signal (mirror of long)."""
    if bars.empty or len(bars) < config.MIN_BARS_FOR_SIGNAL:
        return None

    ok, reason = _gates_pass(symbol, open_positions, trades_today, daily_pnl, daily_start_equity)
    if not ok:
        logger.info(f"{symbol} short: gate blocked — {reason}")
        return None

    vwap_series = ind.calculate_vwap(bars)
    ema_fast_s = ind.calculate_ema(bars["close"], config.EMA_FAST_PERIOD)
    ema_mid_s = ind.calculate_ema(bars["close"], config.EMA_MID_PERIOD)
    ema_slow_s = ind.calculate_ema(bars["close"], config.EMA_SLOW_PERIOD)
    atr_series = ind.calculate_atr(bars)
    rvol_series = ind.calculate_relative_volume(bars)

    if any(s.empty for s in (vwap_series, ema_fast_s, ema_mid_s, ema_slow_s, atr_series, rvol_series)):
        return None

    bar = bars.iloc[-1]
    prior = bars.iloc[-2]
    price = float(bar["close"])
    vwap = float(vwap_series.iloc[-1])
    ema_fast = float(ema_fast_s.iloc[-1])
    ema_mid = float(ema_mid_s.iloc[-1])
    ema_slow = float(ema_slow_s.iloc[-1])
    atr = float(atr_series.iloc[-1])
    rvol = float(rvol_series.iloc[-1]) if pd.notna(rvol_series.iloc[-1]) else 0.0

    c1 = price < vwap
    c2 = price < ema_slow
    c3 = ema_fast < ema_mid
    c5 = price < float(prior["close"])
    c6 = rvol >= config.CAMERON_VOLUME_MULTIPLIER
    c4, _ = _recent_pullback_to_vwap(
        bars, vwap_series,
        side="short",
        lookback=config.VWAP_PULLBACK_LOOKBACK_BARS,
        tolerance_pct=config.VWAP_PULLBACK_TOLERANCE_PCT,
    )

    if not (c1 and c2 and c3 and c4 and c5 and c6):
        logger.info(
            f"{symbol} short: setup incomplete | <VWAP={c1} <200EMA={c2} 9<20={c3} "
            f"pullback={c4} rejection={c5} rvol≥{config.CAMERON_VOLUME_MULTIPLIER}={c6} "
            f"(price={price:.2f} vwap={vwap:.2f} rvol={rvol:.2f})"
        )
        return None

    if len(bars) < config.STOP_LOOKBACK_BARS + 1:
        return None
    prior_highs = bars["high"].iloc[-(config.STOP_LOOKBACK_BARS + 1):-1]
    stop_price = float(prior_highs.max())
    risk_per_share = stop_price - price
    if risk_per_share <= 0:
        return None
    if risk_per_share > config.ATR_GUARDRAIL_MULT * atr:
        logger.info(
            f"{symbol} short: SKIP — stop distance ${risk_per_share:.2f} > "
            f"{config.ATR_GUARDRAIL_MULT}×ATR ${config.ATR_GUARDRAIL_MULT * atr:.2f} (chop)"
        )
        return None

    sizing = rsk.calculate_position_size(
        account_equity=account_equity,
        entry_price=price,
        stop_price=stop_price,
        side="short",
        realized_vol=ind.calculate_realized_vol(daily_returns) if daily_returns is not None else None,
    )
    if sizing.qty <= 0:
        return None

    notional = price * sizing.qty
    current_exposure = sum(p.get("qty", 0) * p.get("entry_price", 0) for p in open_positions.values())
    cap_ok, cap_reason = rsk.check_exposure_cap(account_equity, current_exposure, notional)
    if not cap_ok:
        logger.info(f"{symbol} short: exposure cap blocked — {cap_reason}")
        return None

    limit_price = price * (1 - config.LIMIT_ORDER_BUFFER_PCT) if config.USE_LIMIT_ORDER_ENTRIES else None

    return TradeSignal(
        symbol=symbol,
        side="short",
        entry_price=price,
        stop_price=stop_price,
        target_price=sizing.target_price,
        qty=sizing.qty,
        risk_amount=sizing.risk_amount,
        risk_per_share=risk_per_share,
        vwap=vwap,
        ema_fast=ema_fast,
        ema_mid=ema_mid,
        ema_slow=ema_slow,
        atr=atr,
        rvol=rvol,
        reason=(
            f"VWAP-Bounce short | price ${price:.2f} < VWAP ${vwap:.2f}, "
            f"9EMA < 20EMA, price < 200EMA, rvol {rvol:.2f}× | "
            f"stop ${stop_price:.2f} (5-bar high), risk ${risk_per_share:.2f}/sh "
            f"({risk_per_share / atr:.2f}×ATR)"
        ),
        sizing_breakdown=sizing.breakdown,
        limit_price=limit_price,
    )
