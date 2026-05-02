"""
dynamic_backtest.py — Phase 2b/3 of the universe rebuild.

Runs the existing backtest engine with the dynamic per-day universe injected
from dynamic_universe_history.json. For each window × strategy × slippage level,
computes return / Sharpe / trade count and prints a side-by-side comparison
against the static-30 baseline.

Usage:  python dynamic_backtest.py
"""
from __future__ import annotations
import json
import logging
import os
import sys
from datetime import datetime

import config
import data as mkt_data
from backtest import BacktestConfig, BacktestEngine, StrategyMode

REPO = os.path.dirname(os.path.abspath(__file__))
HISTORY_PATH = os.path.join(REPO, "dynamic_universe_history.json")
RESULTS_DIR = config.BACKTEST_RESULTS_DIR
OUT_LOG = os.path.join(RESULTS_DIR, "dynamic_universe_stress.log")

WINDOWS = [
    ("2023H1", "2023-01-03", "2023-06-30"),
    ("2023H2", "2023-07-03", "2023-12-29"),
    ("2024H1", "2024-01-02", "2024-06-28"),
    ("2024H2", "2024-07-01", "2024-12-31"),
]
SLIPPAGE_LEVELS = [0.0003, 0.0010, 0.0015]
MODES = [StrategyMode.PLAIN_ORB, StrategyMode.FULL_SYSTEM]


def load_history() -> dict:
    with open(HISTORY_PATH) as f:
        return json.load(f)


def filter_history_to_window(history: dict, start: str, end: str) -> dict:
    """Subset universe_by_day to dates within the window."""
    start_d = datetime.strptime(start, "%Y-%m-%d").date()
    end_d = datetime.strptime(end, "%Y-%m-%d").date()
    out = {}
    for k, v in history.get("universe_by_day", {}).items():
        d = datetime.strptime(k, "%Y-%m-%d").date()
        if start_d <= d <= end_d:
            out[k] = v
    return out


def union_symbols(window_history: dict) -> list:
    syms = set()
    for picks in window_history.values():
        for p in picks:
            sym = p["symbol"] if isinstance(p, dict) else p
            syms.add(sym)
    return sorted(syms)


def fetch_window_bars(start: str, end: str, dyn_symbols: list):
    """Fetch the bars + vol/spy/p-c needed for the engine.

    The engine needs: bars for every symbol that might trade (dyn universe + SPY +
    short universe + defensive universe), VIX data, SPY daily, put/call.
    """
    data_client = mkt_data.get_data_client()
    # Always include SPY (gap filter), plus existing fear-resilient/defensive
    # so non-momentum modes still have something. Short universe stays static for now.
    extras = ["SPY"] + list(config.FEAR_RESILIENT_UNIVERSE) + list(config.DEFENSIVE_UNIVERSE) + list(config.SHORT_UNIVERSE)
    all_syms = list(dict.fromkeys(dyn_symbols + extras))
    print(f"  downloading 5-min bars for {len(all_syms)} symbols (dyn={len(dyn_symbols)} + extras={len(all_syms)-len(dyn_symbols)})...")
    bars = mkt_data.get_multiple_symbols_bars(data_client, all_syms, start, end)
    print(f"  got bars for {len(bars)} symbols")

    print("  downloading vol (VIX/VVIX/VIX3M)...")
    vol = mkt_data.get_vix_history(start, end)
    print("  downloading SPY daily...")
    spy = mkt_data.get_spy_daily(start, end)
    print("  downloading put/call...")
    pc = mkt_data.get_put_call_history(start, end)
    print("  computing daily returns for VIX beta...")
    dr = {sym: mkt_data.get_symbol_daily_returns(data_client, sym, start, end) for sym in all_syms}
    return bars, vol, spy, pc, dr


def run_one(mode: StrategyMode, slippage: float, dyn_uni: dict, data_tuple, equity: float):
    bars, vol, spy, pc, dr = data_tuple
    cfg = BacktestConfig(
        mode=mode,
        initial_equity=equity,
        slippage_pct=slippage,
        save_trades=False,
        trades_file="",
        dynamic_universe_by_day=dyn_uni,
    )
    engine = BacktestEngine(cfg)
    return engine.run(bars, vol, spy, pc, dr) or {}


def main():
    logging.getLogger().setLevel(logging.WARNING)
    for noisy in ("backtest", "regime", "vix_factor", "vvix_filter", "data",
                  "calendar_filter", "sentiment", "sector_rotation", "performance"):
        logging.getLogger(noisy).setLevel(logging.WARNING)

    if not os.path.exists(HISTORY_PATH):
        print(f"FATAL: {HISTORY_PATH} not found. Run build_universe_history.py first.")
        sys.exit(1)

    print("Loading universe history...")
    history = load_history()
    print(f"  {len(history.get('universe_by_day', {}))} day-universes loaded")
    print(f"  params: {history.get('params', {})}")

    # Match session 5 Run 8 config for an apples-to-apples comparison
    config.USE_FIB_RETRACEMENT_ENTRY = True
    config.USE_FIB_RETRACEMENT_REGIME_GATE = False
    print(f"  USE_FIB_RETRACEMENT_ENTRY=True, REGIME_GATE=False (matches session 5 baseline)")

    equity = config.INITIAL_EQUITY
    os.makedirs(RESULTS_DIR, exist_ok=True)
    started = datetime.now()

    # results[window][mode][slip] = metrics
    results = {w[0]: {m.value: {} for m in MODES} for w in WINDOWS}
    union_sizes = {}

    for win_label, start, end in WINDOWS:
        print(f"\n=== {win_label} ({start} → {end}) ===")
        dyn_uni = filter_history_to_window(history, start, end)
        if not dyn_uni:
            print(f"  ⚠ no universe data for window — skipping")
            continue

        dyn_symbols = union_symbols(dyn_uni)
        union_sizes[win_label] = len(dyn_symbols)
        print(f"  {len(dyn_uni)} day-universes, {len(dyn_symbols)} unique symbols across window")

        try:
            data_tuple = fetch_window_bars(start, end, dyn_symbols)
        except Exception as e:
            print(f"  FAILED to download bars: {e}")
            continue

        for mode in MODES:
            for slip in SLIPPAGE_LEVELS:
                print(f"  running {mode.value} | slip={slip*100:.2f}%...", flush=True)
                try:
                    m = run_one(mode, slip, dyn_uni, data_tuple, equity)
                except Exception as e:
                    print(f"    ERROR: {e}")
                    m = {}
                results[win_label][mode.value][slip] = m

    elapsed = (datetime.now() - started).total_seconds()
    print(f"\nFinished in {elapsed/60:.1f} min")

    # ── Summary ────────────────────────────────────────────────────────────
    lines = []
    lines.append("=" * 110)
    lines.append("DYNAMIC UNIVERSE — SLIPPAGE STRESS TEST")
    lines.append(f"  pool: 1069 names | top-20/day by |gap| with $20M $-vol floor + $5 price floor")
    lines.append(f"  config: USE_FIB_RETRACEMENT_ENTRY=True, REGIME_GATE=False, equity ${equity:,.0f}")
    lines.append("=" * 110)
    lines.append("")
    lines.append(f"Union symbols per window: {union_sizes}")

    # Static-30 baseline (from earlier slippage_stress.log) for side-by-side comparison
    static_baseline = {
        "plain_orb": {
            "2023H1": (8.25, -13.71/4*1, 3.55, 8.25, 3.44, 0.14),  # placeholder — not used
        }
    }
    # Just print the dynamic numbers; user can compare against slippage_stress.log

    for mode in MODES:
        lines.append("")
        lines.append(f"━━━ {mode.value.upper()} (DYNAMIC UNIVERSE) ━━━")
        lines.append(f"{'Window':<10}{'Trades':<10}{'@0.03%':<13}{'@0.10%':<13}{'@0.15%':<13}{'Sh@.03':<10}{'Sh@.10':<10}{'Sh@.15':<10}")
        lines.append("-" * 110)
        totals = {s: 0.0 for s in SLIPPAGE_LEVELS}
        for win_label, _, _ in WINDOWS:
            r03 = results[win_label][mode.value].get(SLIPPAGE_LEVELS[0]) or {}
            r10 = results[win_label][mode.value].get(SLIPPAGE_LEVELS[1]) or {}
            r15 = results[win_label][mode.value].get(SLIPPAGE_LEVELS[2]) or {}
            if not r03:
                continue
            row = f"{win_label:<10}{r03.get('total_trades',0):<10}"
            for s, r in zip(SLIPPAGE_LEVELS, [r03, r10, r15]):
                pnl = r.get("total_pnl", 0)
                ret = pnl / equity * 100
                totals[s] += pnl
                row += f"{ret:+.2f}%       "[:13]
            row += f"{r03.get('sharpe',0):+.2f}      "[:10]
            row += f"{r10.get('sharpe',0):+.2f}      "[:10]
            row += f"{r15.get('sharpe',0):+.2f}      "[:10]
            lines.append(row)
        lines.append("-" * 110)
        row = f"{'24-mo':<10}{'':<10}"
        for s in SLIPPAGE_LEVELS:
            row += f"{totals[s]/equity*100:+.2f}%       "[:13]
        lines.append(row)

    lines.append("")
    lines.append("=" * 110)
    lines.append("Compare with backtest_results/slippage_stress.log (static-30 numbers)")
    lines.append("=" * 110)
    summary = "\n".join(lines)
    print("\n" + summary)
    with open(OUT_LOG, "w") as f:
        f.write(summary + "\n")
    print(f"\nSaved → {OUT_LOG}")


if __name__ == "__main__":
    main()
