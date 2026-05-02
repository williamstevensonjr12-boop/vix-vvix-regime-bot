"""
build_universe_pool.py — Phase 1 of the universe rebuild.

Builds a candidate pool of US small/mid-cap names that the dynamic scanner will
filter and rank from each pre-market. Sources:
  1. S&P MidCap 400 components (Wikipedia)
  2. S&P SmallCap 600 components (Wikipedia)
  3. Current MOMENTUM_UNIVERSE (preserve continuity)
  4. Curated list of popular momentum/gap names not in S&P indices

Output: universe_pool.json — sorted list of unique tickers + metadata.

This is the *upper bound* of what the scanner can pick. Actual daily selection
applies $-volume floor, price floor, and gap filter at scan time.
"""
from __future__ import annotations
import json
import os
import sys

from io import StringIO

import pandas as pd
import requests

OUT_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "universe_pool.json")

# ── Curated momentum names not in S&P 400/600 ────────────────────────────────
# Mostly mega/large-cap-by-now growth + meme + crypto-adjacent names that
# small-cap scanners catch on gap days. Many overlap with MOMENTUM_UNIVERSE.
CURATED_MOMENTUM = [
    # Fintech
    "SOFI", "AFRM", "HOOD", "UPST", "PYPL", "COIN",
    # Crypto miners / treasury
    "RIOT", "MARA", "CLSK", "BITF", "HUT", "MSTR", "WULF", "CIFR",
    # EV / clean
    "RIVN", "LCID", "NIO", "XPEV", "LI", "RUN", "ENPH", "FSLR", "PLUG", "BLNK", "CHPT",
    # AI / semis (mostly mid-cap)
    "SMCI", "AI", "BBAI", "SOUN", "PATH", "PLTR",
    # Biotech / health
    "MRNA", "CRSP", "BEAM", "EDIT", "NTLA", "TDOC", "VRTX", "RXRX",
    # Space / defense
    "RKLB", "ASTS", "ACHR", "JOBY", "SPCE", "LUNR",
    # Quantum / specialty
    "IONQ", "QBTS", "RGTI",
    # Misc gap-prone
    "DKNG", "OPEN", "ROKU", "GME", "AMC", "BBBY",
    # Growth tech (large cap but gap-prone)
    "TSLA", "NVDA", "AMD", "META", "AMZN", "AAPL", "MSFT", "QQQ", "SPY",
    # Sector ETFs (defensive rotation universe)
    "XLU", "XLP", "XLV", "XLK", "XLF", "XLE", "GLD", "JNJ", "PG", "KO", "COST",
]


UA = {"User-Agent": "Mozilla/5.0 (universe-pool-builder)"}


def _scrape_index(url: str, label: str) -> list:
    print(f"  fetching {label} from Wikipedia...")
    resp = requests.get(url, headers=UA, timeout=30)
    resp.raise_for_status()
    tables = pd.read_html(StringIO(resp.text))
    for t in tables:
        cols_lower = [str(c).lower() for c in t.columns]
        if any("symbol" in c or "ticker" in c for c in cols_lower):
            idx = next(i for i, c in enumerate(cols_lower) if "symbol" in c or "ticker" in c)
            sym_col = t.columns[idx]
            tickers = t[sym_col].astype(str).str.strip().tolist()
            tickers = [s for s in tickers if s and s.isalpha() and len(s) <= 5]
            print(f"  → {len(tickers)} {label} tickers")
            return tickers
    raise RuntimeError(f"Could not find {label} ticker column")


def fetch_sp400() -> list:
    return _scrape_index("https://en.wikipedia.org/wiki/List_of_S%26P_400_companies", "S&P 400")


def fetch_sp600() -> list:
    return _scrape_index("https://en.wikipedia.org/wiki/List_of_S%26P_600_companies", "S&P 600")


def main():
    print("Building universe pool from multiple sources...\n")

    sources = {}
    try:
        sources["sp400"] = fetch_sp400()
    except Exception as e:
        print(f"  ⚠ S&P 400 fetch failed: {e}")
        sources["sp400"] = []

    try:
        sources["sp600"] = fetch_sp600()
    except Exception as e:
        print(f"  ⚠ S&P 600 fetch failed: {e}")
        sources["sp600"] = []

    sources["curated"] = CURATED_MOMENTUM

    # Pull current MOMENTUM_UNIVERSE for continuity
    try:
        import config
        sources["current_universe"] = list(config.MOMENTUM_UNIVERSE)
        print(f"  → {len(sources['current_universe'])} tickers from current MOMENTUM_UNIVERSE")
    except Exception as e:
        print(f"  ⚠ Failed to import config.MOMENTUM_UNIVERSE: {e}")
        sources["current_universe"] = []

    # Build dedup pool with provenance
    pool = {}
    for source_name, tickers in sources.items():
        for sym in tickers:
            sym = sym.upper().strip()
            if not sym or not sym.replace(".", "").replace("-", "").isalnum():
                continue
            if sym not in pool:
                pool[sym] = {"symbol": sym, "sources": []}
            if source_name not in pool[sym]["sources"]:
                pool[sym]["sources"].append(source_name)

    pool_sorted = sorted(pool.values(), key=lambda x: x["symbol"])

    # ── Summary ────────────────────────────────────────────────────────────
    print(f"\n{'='*60}")
    print(f"UNIVERSE POOL — {len(pool_sorted)} unique tickers")
    print(f"{'='*60}")
    by_source_count = {s: 0 for s in sources}
    for t in pool_sorted:
        for s in t["sources"]:
            by_source_count[s] += 1
    for s, c in by_source_count.items():
        print(f"  {s:<20} {c:>4} tickers")

    overlap_400_600 = sum(1 for t in pool_sorted if "sp400" in t["sources"] and "sp600" in t["sources"])
    print(f"  S&P 400 ∩ S&P 600   {overlap_400_600:>4} (should be 0; sanity check)")
    in_curated_only = sum(1 for t in pool_sorted if t["sources"] == ["curated"])
    print(f"  curated-only        {in_curated_only:>4} (not in S&P indices)")

    # Sample
    print(f"\nFirst 10 (sorted): {[t['symbol'] for t in pool_sorted[:10]]}")
    print(f"Last 10 (sorted):  {[t['symbol'] for t in pool_sorted[-10:]]}")

    # ── Save ────────────────────────────────────────────────────────────────
    out = {
        "version": 1,
        "total": len(pool_sorted),
        "by_source": by_source_count,
        "tickers": pool_sorted,
    }
    with open(OUT_PATH, "w") as f:
        json.dump(out, f, indent=2)
    print(f"\nSaved → {OUT_PATH}")


if __name__ == "__main__":
    main()
