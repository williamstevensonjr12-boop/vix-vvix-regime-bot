"""
[C] build_universe_iwm.py — Build gap_go_universe.py from live IWM holdings.

Downloads today's IWM holdings CSV from iShares, filters for equities only,
verifies each ticker via yfinance (active, equity, float < 100M), then
writes the result to gap_go_universe.py.

Run from repo root:
    python3 "[C] build_universe_iwm.py"
"""

import io
import json
import os
import re
import time

import pandas as pd
import requests
import yfinance as yf

HOLDINGS_URL = (
    "https://www.ishares.com/us/products/239710/ishares-russell-2000-etf/"
    "1467271812596.ajax?fileType=csv&fileName=IWM_holdings&dataType=fund"
)
CACHE_FILE = "/tmp/iwm_yf_cache.json"
OUT_FILE = os.path.join(os.path.dirname(__file__), "gap_go_universe.py")
FLOAT_LIMIT = 100_000_000
BATCH = 50
SLEEP = 1.5


def fetch_iwm_tickers() -> list[str]:
    print("Downloading IWM holdings from iShares...")
    resp = requests.get(HOLDINGS_URL, headers={"User-Agent": "Mozilla/5.0"}, timeout=30)
    resp.raise_for_status()
    # iShares CSV has a header block before the actual data — find the real header row
    text = resp.text
    lines = text.splitlines()
    data_start = next(i for i, l in enumerate(lines) if l.startswith("Ticker,"))
    df = pd.read_csv(io.StringIO("\n".join(lines[data_start:])))
    df.columns = [c.strip() for c in df.columns]
    # Keep equities only (Asset Class column)
    df = df[df["Asset Class"].str.strip() == "Equity"]
    tickers = df["Ticker"].str.strip().dropna().tolist()
    # Remove non-standard symbols (warrants, units, rights)
    tickers = [t for t in tickers if re.match(r'^[A-Z]{1,5}$', t)]
    print(f"  {len(tickers)} equity tickers from IWM holdings")
    return tickers


def load_cache() -> dict:
    if os.path.exists(CACHE_FILE):
        with open(CACHE_FILE) as f:
            return json.load(f)
    return {}


def save_cache(cache: dict):
    with open(CACHE_FILE, "w") as f:
        json.dump(cache, f)


def verify_tickers(tickers: list[str]) -> list[str]:
    cache = load_cache()
    # Only keep entries that have quoteType (stale entries without it caused ETF leakage before)
    cache = {k: v for k, v in cache.items() if "quoteType" in v}

    to_fetch = [t for t in tickers if t not in cache]
    print(f"  {len(cache)} cached | {len(to_fetch)} to fetch from yfinance")

    for i in range(0, len(to_fetch), BATCH):
        batch = to_fetch[i:i + BATCH]
        print(f"  Fetching batch {i // BATCH + 1}/{(len(to_fetch) - 1) // BATCH + 1} ({len(batch)} tickers)...")
        try:
            info_batch = yf.Tickers(" ".join(batch))
            for t in batch:
                try:
                    info = info_batch.tickers[t].info
                    cache[t] = {
                        "quoteType": info.get("quoteType", ""),
                        "sharesOutstanding": info.get("sharesOutstanding") or info.get("impliedSharesOutstanding") or 0,
                        "floatShares": info.get("floatShares") or 0,
                        "marketCap": info.get("marketCap") or 0,
                    }
                except Exception:
                    cache[t] = {"quoteType": "ERROR"}
        except Exception as e:
            print(f"  Batch error: {e}")
        save_cache(cache)
        time.sleep(SLEEP)

    valid = []
    for t in tickers:
        entry = cache.get(t, {})
        if entry.get("quoteType") != "EQUITY":
            continue
        float_shares = entry.get("floatShares") or entry.get("sharesOutstanding") or 0
        if float_shares > FLOAT_LIMIT:
            continue
        valid.append(t)

    print(f"  {len(valid)} passed verification (EQUITY + float < 100M)")
    return valid


def write_universe(tickers: list[str]):
    header = '''\
"""
gap_go_universe.py — Universe of small-cap stocks sourced from IWM holdings.
Shared between live trading (gap_go_live.py) and backtests.
No heavy imports — safe to import anywhere.
"""
_RAW = [
'''
    # Write in rows of 8
    rows = []
    for i in range(0, len(tickers), 8):
        chunk = tickers[i:i + 8]
        rows.append("    " + ", ".join(f'"{t}"' for t in chunk) + ",")
    body = "\n".join(rows)
    footer = '''
]

# Deduplicate preserving order
_seen: set = set()
UNIVERSE: list[str] = [x for x in _RAW if not (_seen.__contains__(x) or _seen.add(x))]  # type: ignore[func-returns-value]
'''
    with open(OUT_FILE, "w") as f:
        f.write(header + body + footer)
    print(f"  Written to {OUT_FILE} ({len(tickers)} tickers)")


if __name__ == "__main__":
    tickers = fetch_iwm_tickers()
    verified = verify_tickers(tickers)
    write_universe(verified)
    print(f"\nDone. Universe: {len(verified)} tickers.")
    print("Next: review gap_go_universe.py, then git commit and push.")
