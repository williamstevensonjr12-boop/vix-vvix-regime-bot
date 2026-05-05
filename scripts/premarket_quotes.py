#!/usr/bin/env python3
"""
premarket_quotes.py — Live pre-market quotes for the 8 mega-caps via yfinance.

Used by the pre-market routine (STEP 3.5) to populate per-symbol notes with
actual gap % instead of stale indexed snapshots from WebSearch.

Outputs markdown bullets to stdout, one line per symbol:
    - AAPL: pre $282.50 (+0.83%) vs prev close $280.19
    - MSFT: pre $415.10 (+0.17%) vs prev close $414.40
    ...

Usage:  python3 scripts/premarket_quotes.py
"""
from __future__ import annotations
import os
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO))
os.chdir(REPO)

import config  # noqa: E402
from data import _SilenceYFinance  # noqa: E402

import yfinance as yf  # noqa: E402


def _last_regular_close(t) -> float | None:
    """Most reliable source for last regular-session close: history's final
    daily bar. The `regularMarketPreviousClose` quoteSummary field is
    misleading — Yahoo defines it as "the close BEFORE the most recent
    close" (two trading days ago), not yesterday's close. `regularMarketPrice`
    works while market is closed but updates live during regular hours.
    History always reflects the last completed daily bar. 2026-05-04 fix.
    """
    try:
        from datetime import date
        hist = t.history(period="7d", auto_adjust=False)
        if hist.empty:
            return None
        today = date.today()
        # Drop today's row — Yahoo creates a partial daily bar during pre-market
        # whose Close is the live pre-market price, not yesterday's close.
        past = hist[hist.index.date < today]
        if not past.empty:
            return float(past["Close"].iloc[-1])
    except Exception:
        pass
    return None


def quote(symbol: str) -> str:
    try:
        with _SilenceYFinance():
            t = yf.Ticker(symbol)
            info = t.info or {}
            prev = _last_regular_close(t)
        # Yahoo populates preMarketPrice during early pre-market hours, then
        # rolls pre-market activity into regularMarketPrice closer to the open
        # (preMarketPrice goes None ~30 min before bell). Fall back to
        # regularMarketPrice when the dedicated field is unavailable —
        # before market opens, regularMarketPrice tracks pre-market levels.
        pre_px = info.get("preMarketPrice")
        used_regular_market_fallback = False
        if pre_px is None:
            pre_px = info.get("regularMarketPrice")
            used_regular_market_fallback = True

        if pre_px is None and prev:
            return f"- {symbol}: no pre-market quote (prev close ${prev:.2f})"
        if pre_px is None:
            return f"- {symbol}: no quote available"

        # If preMarketPrice is empty AND regularMarketPrice equals prev close,
        # there's been no real pre-market activity yet — Yahoo is just echoing
        # yesterday's close. Don't lie with "+0.00%"; report the empty-quote
        # state explicitly. 2026-05-05 fix.
        if used_regular_market_fallback and prev and abs(pre_px - prev) < 0.01:
            return f"- {symbol}: no pre-market quote yet (prev close ${prev:.2f})"

        # Always compute change% locally from prev_close. yfinance's
        # preMarketChangePercent uses a different reference (often last
        # extended-hours trade) and was reporting values inconsistent with
        # the displayed prev close (e.g., AAPL pre $279.26 / prev $271.24
        # showed -0.35% from yfinance, actual is +2.96%). 2026-05-04 fix.
        if prev:
            pre_chg = (pre_px - prev) / prev * 100
            chg_str = f"{pre_chg:+.2f}%"
            prev_str = f" vs prev close ${prev:.2f}"
            return f"- {symbol}: pre ${pre_px:.2f} ({chg_str}){prev_str}"
        return f"- {symbol}: pre ${pre_px:.2f} (no prev close to compute %)"
    except Exception as e:
        return f"- {symbol}: fetch error ({type(e).__name__})"


def main() -> int:
    lines = [quote(sym) for sym in config.MOMENTUM_UNIVERSE]
    print("\n".join(lines))
    return 0


if __name__ == "__main__":
    sys.exit(main())
