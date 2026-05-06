"""
notifications.py — Typed notification API for the live bot.

Wraps scripts/notify.sh so Python code can push structured ntfy notifications
without composing message strings inline. Each function below corresponds to a
moment in the bot's lifecycle and formats a consistent, useful message.

Usage:
    import notifications as notify
    notify.entry(symbol="AAPL", side="long", entry=275.00, stop=273.50,
                 target=278.00, qty=50, reason="VWAP-Bounce | rvol 1.8x")
    notify.exit(symbol="AAPL", side="long", entry=275.00, exit_price=278.00,
                qty=50, pnl=150.00, r_multiple=2.0, reason="target hit")
    notify.alert("Kill switch tripped — bot halted for the day")
    notify.eod(date_str="2026-05-01", pnl=3.25, trades=2, wins=1, losses=1,
               equity=99624.49)

All calls fail safe: a notification that can't be sent is logged but doesn't
raise. The bot continues regardless.
"""
from __future__ import annotations
import logging
import subprocess
from pathlib import Path

logger = logging.getLogger(__name__)

# Path to notify.sh — relative to this module (i.e. repo/notifications.py →
# repo/scripts/notify.sh). Computed once at import.
_NOTIFY_SH = (Path(__file__).resolve().parent / "scripts" / "notify.sh")


def _send(notif_type: str, message: str, title: str | None = None) -> bool:
    """Invoke notify.sh with the given type + message. Returns True on success."""
    if not _NOTIFY_SH.exists():
        logger.warning(f"notify.sh not found at {_NOTIFY_SH}; skipping notification")
        return False
    cmd = ["bash", str(_NOTIFY_SH), notif_type, message]
    if title:
        cmd.append(title)
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=10)
        if result.returncode != 0:
            logger.warning(f"notify.sh exit {result.returncode}: {result.stderr.strip()}")
            return False
        return True
    except subprocess.TimeoutExpired:
        logger.warning("notify.sh timed out after 10s")
        return False
    except Exception as e:
        logger.warning(f"notify.sh failed: {e}")
        return False


# ── lifecycle notifications ─────────────────────────────────────────────────

def entry(symbol: str, side: str, entry: float, stop: float, target: float,
          qty: int, reason: str = "") -> bool:
    """Trade opened — high priority, push immediately."""
    side_str = "LONG" if side.lower() == "long" else "SHORT"
    risk_dollars = abs(entry - stop) * qty
    target_dollars = abs(target - entry) * qty
    msg = (
        f"{symbol} {side_str} {qty}sh @ ${entry:.2f}\n"
        f"  stop ${stop:.2f}  (-${risk_dollars:.0f} risk)\n"
        f"  target ${target:.2f}  (+${target_dollars:.0f} = {target_dollars/risk_dollars:.1f}R)"
    )
    if reason:
        msg += f"\n  setup: {reason}"
    return _send("entry", msg)


def exit(symbol: str, side: str, entry: float, exit_price: float, qty: int,
         pnl: float, r_multiple: float = 0.0, reason: str = "") -> bool:
    """Trade closed — push P&L and exit reason."""
    side_str = "LONG" if side.lower() == "long" else "SHORT"
    pct = ((exit_price - entry) / entry * 100) if side.lower() == "long" else ((entry - exit_price) / entry * 100)
    sign = "+" if pnl >= 0 else ""
    msg = (
        f"{symbol} {side_str} closed\n"
        f"  entry ${entry:.2f} → exit ${exit_price:.2f} ({sign}{pct:.2f}%)\n"
        f"  P&L: {sign}${pnl:.2f}  ({r_multiple:+.2f}R)"
    )
    if reason:
        msg += f"\n  reason: {reason}"
    return _send("exit", msg)


def alert(message: str) -> bool:
    """Urgent alert — kill switch, VVIX spike, system error. Highest priority."""
    return _send("alert", message)


def eod(date_str: str, pnl: float, trades: int, wins: int, losses: int,
        equity: float, killswitch: bool = False) -> bool:
    """End-of-day summary — once per session at close."""
    sign = "+" if pnl >= 0 else ""
    wr = f"{wins/trades*100:.0f}%" if trades > 0 else "—"
    msg = (
        f"EOD {date_str}\n"
        f"  P&L: {sign}${pnl:.2f}  ({sign}{pnl/equity*100:.2f}%)\n"
        f"  Trades: {trades}  W:{wins}  L:{losses}  WR:{wr}\n"
        f"  Equity: ${equity:,.2f}"
    )
    if killswitch:
        msg += "\n  ⚠ KILL SWITCH TRIPPED"
    return _send("eod", msg)


def info(message: str) -> bool:
    """Informational ping — low priority. Use sparingly."""
    return _send("info", message)
