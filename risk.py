"""
risk.py — Position sizing, dynamic stops, daily limits, and kill switch.

Sizing hierarchy (multiplicative):
  base_risk_pct × regime_size_factor × vvix_size_factor × sentiment_size_factor
  × vol_adjusted_multiplier  (target_vol / realized_vol)
  = final_risk_pct

ATR-based stops replace fixed % stops for more dynamic sizing.
Portfolio exposure cap prevents over-concentration.
"""
from __future__ import annotations
import logging
from dataclasses import dataclass

import config
from indicators import vol_adjusted_size_multiplier

logger = logging.getLogger(__name__)

_KILL_SWITCH_TRIGGERED: bool = False


# ── Kill switch ───────────────────────────────────────────────────────────────

def is_kill_switch_active() -> bool:
    return _KILL_SWITCH_TRIGGERED


def trigger_kill_switch(reason: str) -> None:
    global _KILL_SWITCH_TRIGGERED
    _KILL_SWITCH_TRIGGERED = True
    logger.critical(f"KILL SWITCH ACTIVATED: {reason}")
    # Push urgent alert. Import inside to avoid a circular import at module load.
    try:
        import notifications as _notify
        _notify.alert(f"KILL SWITCH ACTIVATED — {reason}")
    except Exception as e:
        logger.warning(f"kill-switch notification failed: {e}")


def reset_kill_switch() -> None:
    global _KILL_SWITCH_TRIGGERED
    _KILL_SWITCH_TRIGGERED = False
    logger.info("Kill switch reset")


# ── Position sizing ───────────────────────────────────────────────────────────

@dataclass
class SizingResult:
    qty: int
    risk_amount: float
    final_risk_pct: float
    stop_price: float
    target_price: float
    risk_per_share: float
    vol_multiplier: float
    breakdown: dict


def calculate_position_size(
    account_equity: float,
    entry_price: float,
    stop_price: float,
    regime_size_factor: float = 1.0,
    vvix_size_factor: float = 1.0,
    sentiment_size_factor: float = 1.0,
    realized_vol: float | None = None,
    take_profit_r: float = None,
    side: str = "long",
    orb_range: float | None = None,
) -> SizingResult:
    """
    Full vol-adjusted, regime-aware position sizing.
    For longs: stop_price < entry_price, target above entry.
    For shorts: stop_price > entry_price, target below entry.
    Returns qty = 0 if risk_per_share is non-positive or sizing fails.

    If config.USE_FIB_TARGET is True and orb_range is provided, the take-profit
    target is computed as entry ± FIB_EXTENSION_LEVEL × orb_range instead of the
    fixed take_profit_r × risk_per_share. Otherwise falls back to fixed-R behavior.
    """
    if take_profit_r is None:
        take_profit_r = config.TAKE_PROFIT_R

    if side == "short":
        risk_per_share = stop_price - entry_price
    else:
        risk_per_share = entry_price - stop_price
    if risk_per_share <= 0:
        return SizingResult(0, 0, 0, stop_price, entry_price, 0, 1.0, {})

    # Vol adjustment
    vol_mult = vol_adjusted_size_multiplier(realized_vol) if realized_vol else 1.0

    # Composite risk %
    final_risk_pct = (
        config.RISK_PER_TRADE_PCT
        * regime_size_factor
        * vvix_size_factor
        * sentiment_size_factor
        * vol_mult
    )
    final_risk_pct = min(final_risk_pct, config.RISK_PER_TRADE_PCT * 2.0)  # cap at 2x base

    risk_amount = account_equity * final_risk_pct
    qty = int(risk_amount / risk_per_share)

    if qty <= 0:
        return SizingResult(0, 0, final_risk_pct, stop_price, entry_price, risk_per_share, vol_mult, {})

    use_fib = getattr(config, "USE_FIB_TARGET", False) and orb_range is not None and orb_range > 0
    if use_fib:
        fib_dist = config.FIB_EXTENSION_LEVEL * orb_range
        if side == "short":
            target_price = round(entry_price - fib_dist, 2)
        else:
            target_price = round(entry_price + fib_dist, 2)
    elif side == "short":
        target_price = round(entry_price - take_profit_r * risk_per_share, 2)
    else:
        target_price = round(entry_price + take_profit_r * risk_per_share, 2)

    return SizingResult(
        qty=qty,
        risk_amount=round(qty * risk_per_share, 2),
        final_risk_pct=round(final_risk_pct, 6),
        stop_price=round(stop_price, 2),
        target_price=target_price,
        risk_per_share=round(risk_per_share, 4),
        vol_multiplier=round(vol_mult, 3),
        breakdown={
            "base_risk_pct": config.RISK_PER_TRADE_PCT,
            "regime_factor": regime_size_factor,
            "vvix_factor": vvix_size_factor,
            "sentiment_factor": sentiment_size_factor,
            "vol_mult": vol_mult,
        },
    )


def check_portfolio_exposure(
    open_positions: dict,
    new_qty: int,
    new_price: float,
    account_equity: float,
) -> tuple[bool, str]:
    """
    Returns (can_add: bool, reason: str).
    Rejects if adding new position would breach the portfolio exposure cap.
    """
    current_exposure = sum(
        p.get("qty", 0) * (p.get("current_price") or p.get("avg_entry_price", 0))
        for p in open_positions.values()
    )
    new_notional = new_qty * new_price
    total_after = current_exposure + new_notional
    cap = account_equity * config.PORTFOLIO_EXPOSURE_CAP

    if total_after > cap:
        return False, (
            f"Portfolio cap breach: current={current_exposure:,.0f} "
            f"+ new={new_notional:,.0f} > cap={cap:,.0f}"
        )
    return True, ""


def check_daily_limits(
    trades_today: int,
    daily_pnl: float,
    daily_start_equity: float,
) -> tuple[bool, str]:
    """Returns (can_trade, reason). Hard-stops if kill switch or limits hit."""
    if is_kill_switch_active():
        return False, "Kill switch is active"

    if trades_today >= config.MAX_TRADES_PER_DAY:
        return False, f"Max trades/day ({config.MAX_TRADES_PER_DAY}) reached"

    max_loss = daily_start_equity * config.DAILY_MAX_LOSS_PCT
    kill_loss = daily_start_equity * config.KILL_SWITCH_LOSS_PCT

    if daily_pnl < -kill_loss:
        trigger_kill_switch(f"Daily P&L ${daily_pnl:.2f} breached kill threshold ${-kill_loss:.2f}")
        return False, "Kill switch triggered"

    if daily_pnl < -max_loss:
        return False, f"Daily max-loss hit (limit=${max_loss:.2f}, P&L=${daily_pnl:.2f})"

    return True, ""


# PDT (Pattern Day Trader) thresholds
PDT_EQUITY_FLOOR = 25_000.0       # FINRA rule — under this, flagged accounts are locked
PDT_SAFETY_BUFFER = 500.0         # additional buffer above floor before we hard-block
PDT_WARNING_COUNT = 5             # log a warning when count reaches this in 5-day window


def check_pdt_constraints(account) -> tuple[bool, str]:
    """
    Returns (can_trade, reason) based on Alpaca account's PDT state.

    The FINRA Pattern Day Trader rule: 4+ day-trades in any rolling 5-business-day
    window flags the account. While flagged, equity must stay above $25,000 or the
    account is locked from day trading for 90 days.

    Logic:
      - If account isn't flagged, no restriction (any equity, any count)
      - If flagged AND equity is within $500 of the $25K floor AND we'd be taking
        another day-trade, hard-block to prevent crossing
      - Otherwise, log a warning if count climbs past 5 (situational awareness)

    Pass the Alpaca account object directly (from broker.get_account()).
    """
    if account is None:
        return True, ""
    try:
        equity = float(getattr(account, "equity", 0))
        is_flagged = bool(getattr(account, "pattern_day_trader", False))
        dt_count = int(getattr(account, "daytrade_count", 0))
    except (TypeError, ValueError):
        # If we can't read the account state, don't block — let other guards run
        return True, ""

    if is_flagged and equity < (PDT_EQUITY_FLOOR + PDT_SAFETY_BUFFER):
        return False, (
            f"PDT lockout risk: flagged account, equity ${equity:,.2f} within "
            f"buffer of ${PDT_EQUITY_FLOOR:,.0f} floor (count={dt_count})"
        )

    if dt_count >= PDT_WARNING_COUNT:
        logger.warning(
            f"PDT day-trade count at {dt_count} (rolling 5-day) — "
            f"flagged={is_flagged}, equity=${equity:,.2f}. "
            f"Lockout triggers if equity drops below ${PDT_EQUITY_FLOOR:,.0f}."
        )

    return True, ""


def validate_order(
    symbol: str,
    entry: float,
    stop: float,
    target: float,
    qty: int,
    side: str = "long",
) -> tuple[bool, str]:
    if qty <= 0:
        return False, f"qty={qty} not positive"
    if any(p <= 0 for p in [entry, stop, target]):
        return False, "all prices must be positive"
    if side == "short":
        if stop <= entry:
            return False, f"short stop {stop:.2f} <= entry {entry:.2f}"
        if target >= entry:
            return False, f"short target {target:.2f} >= entry {entry:.2f}"
    else:
        if stop >= entry:
            return False, f"stop {stop:.2f} >= entry {entry:.2f}"
        if target <= entry:
            return False, f"target {target:.2f} <= entry {entry:.2f}"
    return True, ""
