"""
build_universe_history.py — Phase 2a of the universe rebuild.

For each trading day in the backtest range, computes the top-20 universe
the dynamic scanner would have selected, given:
  - price > $5
  - 20-day avg $-volume > $20M
  - |gap %| > 2%
  - rank by |gap %| (simple v1 — RVOL added in live integration)

Pulls daily bars for all ~1069 names in universe_pool.json from yfinance,
chunked to be polite. Writes dynamic_universe_history.json keyed by date.

This file is then consumed by Phase 2b (dynamic backtest engine).

Runtime: ~5-15 min depending on yfinance throttling.
"""
from __future__ import annotations
import json
import os
import sys
from datetime import datetime
from io import StringIO

import pandas as pd
import yfinance as yf

REPO = os.path.dirname(os.path.abspath(__file__))
POOL_PATH = os.path.join(REPO, "universe_pool.json")
OUT_PATH = os.path.join(REPO, "dynamic_universe_history.json")

# Range covers the 4 backtest windows + a 30-day pre-window for 20-day rolling
DOWNLOAD_START = "2022-12-01"
DOWNLOAD_END = "2025-01-02"

# Selection params
PRICE_FLOOR = 5.0
DOLLAR_VOL_FLOOR = 20_000_000
GAP_THRESHOLD = 0.02
ROLLING_VOL_DAYS = 20
TOP_N = 20

# Backtest windows we care about — only build history within these
WINDOWS = [
    ("2023-01-03", "2023-06-30"),
    ("2023-07-03", "2023-12-29"),
    ("2024-01-02", "2024-06-28"),
    ("2024-07-01", "2024-12-31"),
]

# yfinance chunk size — too large = timeouts; too small = slow
CHUNK_SIZE = 100


def load_pool():
    with open(POOL_PATH) as f:
        d = json.load(f)
    return [t["symbol"] for t in d["tickers"]]


def download_bars(symbols: list, start: str, end: str) -> dict:
    """
    Returns {symbol: DataFrame} with columns [Open, High, Low, Close, Volume].
    Chunks the request to avoid yfinance failures on large ticker lists.
    """
    all_data: dict = {}
    n_chunks = (len(symbols) + CHUNK_SIZE - 1) // CHUNK_SIZE
    for i in range(0, len(symbols), CHUNK_SIZE):
        chunk = symbols[i:i + CHUNK_SIZE]
        cnum = i // CHUNK_SIZE + 1
        print(f"  chunk {cnum}/{n_chunks}: {len(chunk)} symbols ({chunk[0]}…{chunk[-1]})", flush=True)
        try:
            df = yf.download(
                tickers=chunk,
                start=start,
                end=end,
                interval="1d",
                group_by="ticker",
                progress=False,
                auto_adjust=False,
                threads=True,
            )
        except Exception as e:
            print(f"    ⚠ chunk failed: {e}")
            continue

        if df is None or df.empty:
            print(f"    ⚠ chunk returned empty")
            continue

        # Single-ticker chunks come back without the outer ticker level; multi-ticker do.
        if len(chunk) == 1:
            sym = chunk[0]
            sub = df.dropna(how="all")
            if not sub.empty:
                all_data[sym] = sub
        else:
            for sym in chunk:
                if sym not in df.columns.get_level_values(0):
                    continue
                sub = df[sym].dropna(how="all")
                if sub.empty:
                    continue
                all_data[sym] = sub

    print(f"  → got bars for {len(all_data)} / {len(symbols)} symbols")
    return all_data


def compute_universe_history(bars: dict, windows: list) -> dict:
    """
    For each trading day in any window, compute the top-N dynamic universe.
    Returns {date_iso: [{symbol, open, prior_close, gap_pct, avg_dollar_vol_20d, score}, ...]}
    """
    # Master trading-day list = union of all dates from any symbol's bars (within windows)
    all_days: set = set()
    for sym, df in bars.items():
        all_days.update(df.index.date)

    # Restrict to dates inside any window
    in_window = []
    for d in sorted(all_days):
        for ws, we in windows:
            ws_d = datetime.strptime(ws, "%Y-%m-%d").date()
            we_d = datetime.strptime(we, "%Y-%m-%d").date()
            if ws_d <= d <= we_d:
                in_window.append(d)
                break

    print(f"\nComputing dynamic universe for {len(in_window)} trading days...")

    # Pre-compute helpers per symbol: dollar-volume series (close × volume)
    dollar_vol: dict = {}
    for sym, df in bars.items():
        if "Close" in df.columns and "Volume" in df.columns:
            dv = (df["Close"] * df["Volume"]).rename("dv")
            dollar_vol[sym] = pd.concat([df, dv], axis=1)
        else:
            dollar_vol[sym] = df

    universe_by_day: dict = {}
    skipped_no_data = 0

    for day_idx, day in enumerate(in_window):
        if day_idx % 25 == 0:
            print(f"  day {day_idx+1}/{len(in_window)} ({day})", flush=True)

        candidates = []
        for sym, df in dollar_vol.items():
            try:
                # Need today's open + prior trading day's close + 20 prior days for volume
                tomorrow_or_today_idx = df.index.searchsorted(pd.Timestamp(day))
                if tomorrow_or_today_idx >= len(df):
                    continue
                today_row = df.iloc[tomorrow_or_today_idx]
                if today_row.name.date() != day:
                    continue  # symbol doesn't trade today

                # Prior trading day = the row immediately before today
                if tomorrow_or_today_idx == 0:
                    continue
                prior_row = df.iloc[tomorrow_or_today_idx - 1]

                # 20-day rolling $-volume (uses up through prior day, no lookahead)
                rolling = df.iloc[max(0, tomorrow_or_today_idx - ROLLING_VOL_DAYS):tomorrow_or_today_idx]
                if len(rolling) < 10 or "dv" not in rolling.columns:
                    continue
                avg_dv = float(rolling["dv"].mean())

                today_open = float(today_row["Open"])
                prior_close = float(prior_row["Close"])
                if not (today_open > 0 and prior_close > 0):
                    continue

                # Filters
                if today_open < PRICE_FLOOR:
                    continue
                if avg_dv < DOLLAR_VOL_FLOOR:
                    continue
                gap = (today_open - prior_close) / prior_close
                if abs(gap) < GAP_THRESHOLD:
                    continue

                candidates.append({
                    "symbol": sym,
                    "open": round(today_open, 4),
                    "prior_close": round(prior_close, 4),
                    "gap_pct": round(gap, 5),
                    "avg_dollar_vol_20d": round(avg_dv, 0),
                    "score": round(abs(gap), 5),
                })
            except Exception:
                skipped_no_data += 1
                continue

        candidates.sort(key=lambda x: x["score"], reverse=True)
        top = candidates[:TOP_N]
        universe_by_day[day.isoformat()] = top

    print(f"\n  built {len(universe_by_day)} day-universes (skipped {skipped_no_data} symbol-days for missing data)")
    return universe_by_day


def main():
    print("Loading universe pool...")
    symbols = load_pool()
    print(f"  → {len(symbols)} symbols\n")

    print(f"Downloading daily bars {DOWNLOAD_START} → {DOWNLOAD_END}...")
    bars = download_bars(symbols, DOWNLOAD_START, DOWNLOAD_END)

    if not bars:
        print("FATAL: no bar data downloaded")
        sys.exit(1)

    universe_by_day = compute_universe_history(bars, WINDOWS)

    # Coverage summary
    sizes = [len(u) for u in universe_by_day.values()]
    avg_size = sum(sizes) / len(sizes) if sizes else 0
    full_days = sum(1 for s in sizes if s == TOP_N)
    short_days = sum(1 for s in sizes if 0 < s < TOP_N)
    empty_days = sum(1 for s in sizes if s == 0)

    # Symbol churn — how often does the top-20 actually change?
    all_universes = list(universe_by_day.values())
    if len(all_universes) >= 2:
        all_syms = set()
        for u in all_universes: all_syms.update(t["symbol"] for t in u)

    print(f"\n{'='*60}")
    print(f"DYNAMIC UNIVERSE HISTORY")
    print(f"{'='*60}")
    print(f"  trading days     : {len(universe_by_day)}")
    print(f"  avg universe size: {avg_size:.1f}")
    print(f"  full ({TOP_N}) days   : {full_days}")
    print(f"  short days       : {short_days}")
    print(f"  empty days       : {empty_days}")
    if len(all_universes) >= 2:
        print(f"  unique symbols ever picked: {len(all_syms)}")

    out = {
        "version": 1,
        "params": {
            "price_floor": PRICE_FLOOR,
            "dollar_vol_floor": DOLLAR_VOL_FLOOR,
            "gap_threshold": GAP_THRESHOLD,
            "rolling_vol_days": ROLLING_VOL_DAYS,
            "top_n": TOP_N,
            "ranking": "abs(gap_pct)",
        },
        "windows": WINDOWS,
        "universe_by_day": universe_by_day,
    }
    with open(OUT_PATH, "w") as f:
        json.dump(out, f, indent=2)
    print(f"\nSaved → {OUT_PATH}")


if __name__ == "__main__":
    main()
