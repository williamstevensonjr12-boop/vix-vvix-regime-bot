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


def quote(symbol: str) -> str:
    try:
        with _SilenceYFinance():
            t = yf.Ticker(symbol)
            info = t.info or {}
        prev = info.get("regularMarketPreviousClose") or info.get("previousClose")
        pre_px = info.get("preMarketPrice")
        pre_chg = info.get("preMarketChangePercent")

        if pre_px is None and prev:
            return f"- {symbol}: no pre-market quote (prev close ${prev:.2f})"
        if pre_px is None:
            return f"- {symbol}: no quote available"

        if pre_chg is None and prev:
            pre_chg = (pre_px - prev) / prev * 100
        chg_str = f"{pre_chg:+.2f}%" if pre_chg is not None else "n/a"
        prev_str = f" vs prev close ${prev:.2f}" if prev else ""
        return f"- {symbol}: pre ${pre_px:.2f} ({chg_str}){prev_str}"
    except Exception as e:
        return f"- {symbol}: fetch error ({type(e).__name__})"


def main() -> int:
    lines = [quote(sym) for sym in config.MOMENTUM_UNIVERSE]
    print("\n".join(lines))
    return 0


if __name__ == "__main__":
    sys.exit(main())
