"""
atr_threshold_sweep.py — Head-to-head test of ATR expansion filter settings.

Question: is the ATR expansion filter (currently on at 1.2x) earning its keep?
Could 1.0x or 1.5x be better, or is the filter outright hurting us?

Configurations swept:
  - OFF (ENABLE_ATR_EXPANSION_FILTER=False) — pure ORB+VWAP+vol, no ATR gate
  - 1.0x (any expansion at all)
  - 1.2x (current live setting — baseline)
  - 1.5x (stricter)

Same plumbing as volume_threshold_sweep.py: 4 windows × 2 strategies × 4 ATR
configs = 32 simulations, slippage pinned at 0.10% (slightly conservative vs
the 0.08% realized so far).

Usage:  python atr_threshold_sweep.py
"""
from __future__ import annotations
import logging
import os
import sys
from datetime import datetime

import config
import data as mkt_data
from backtest import BacktestConfig, BacktestEngine, StrategyMode

WINDOWS = [
    ("2023H1", "2023-01-03", "2023-06-30"),
    ("2023H2", "2023-07-03", "2023-12-29"),
    ("2024H1", "2024-01-02", "2024-06-28"),
    ("2024H2", "2024-07-01", "2024-12-31"),
]

# (label, ENABLE_ATR_EXPANSION_FILTER, ATR_EXPANSION_MULTIPLIER)
ATR_CONFIGS = [
    ("OFF",  False, 1.0),
    ("1.0x", True,  1.0),
    ("1.2x", True,  1.2),
    ("1.5x", True,  1.5),
]

SLIPPAGE_PCT = 0.0010
MODES = [StrategyMode.PLAIN_ORB, StrategyMode.FULL_SYSTEM]
OUT_LOG = os.path.join(config.BACKTEST_RESULTS_DIR, "atr_threshold_sweep.log")


def fetch_window(start: str, end: str):
    data_client = mkt_data.get_data_client()
    all_symbols = list(dict.fromkeys(config.ALL_SYMBOLS + ["SPY"]))
    print(f"  downloading bars for {len(all_symbols)} symbols...")
    bars_by_symbol = mkt_data.get_multiple_symbols_bars(data_client, all_symbols, start, end)
    print("  downloading vol (VIX/VVIX/VIX3M)...")
    vol_df = mkt_data.get_vix_history(start, end)
    print("  downloading SPY daily...")
    spy_daily = mkt_data.get_spy_daily(start, end)
    print("  downloading put/call...")
    pc_series = mkt_data.get_put_call_history(start, end)
    print("  computing daily returns for VIX beta...")
    daily_returns = {
        sym: mkt_data.get_symbol_daily_returns(data_client, sym, start, end)
        for sym in config.ALL_SYMBOLS
    }
    return bars_by_symbol, vol_df, spy_daily, pc_series, daily_returns


def run_one(mode, atr_label, atr_enabled, atr_mult, data_tuple, equity):
    bars, vol, spy, pc, dr = data_tuple
    config.ENABLE_ATR_EXPANSION_FILTER = atr_enabled
    config.ATR_EXPANSION_MULTIPLIER = atr_mult
    bt_cfg = BacktestConfig(
        mode=mode,
        initial_equity=equity,
        slippage_pct=SLIPPAGE_PCT,
        save_trades=False,
        trades_file="",
    )
    engine = BacktestEngine(bt_cfg)
    metrics = engine.run(bars, vol, spy, pc, dr)
    return metrics or {}


def main():
    logging.getLogger().setLevel(logging.WARNING)
    for noisy in ("backtest", "regime", "vix_factor", "vvix_filter", "data",
                  "calendar_filter", "sentiment", "sector_rotation", "performance"):
        logging.getLogger(noisy).setLevel(logging.WARNING)

    config.USE_FIB_RETRACEMENT_ENTRY = True

    orig_enabled = config.ENABLE_ATR_EXPANSION_FILTER
    orig_mult = config.ATR_EXPANSION_MULTIPLIER
    equity = config.INITIAL_EQUITY
    os.makedirs(config.BACKTEST_RESULTS_DIR, exist_ok=True)

    started = datetime.now()
    print(f"=== ATR threshold sweep — started {started.strftime('%Y-%m-%d %H:%M:%S')} ===")
    print(f"  Sweeping ENABLE_ATR_EXPANSION_FILTER + ATR_EXPANSION_MULTIPLIER")
    print(f"  Configs: {[c[0] for c in ATR_CONFIGS]}")
    print(f"  Slippage pinned: {SLIPPAGE_PCT*100:.2f}%")
    print(f"  Universe: {len(config.MOMENTUM_UNIVERSE)} small-caps, fib retracement: ON")
    print()

    results: dict = {}  # results[window][mode][atr_label] = metrics
    for win_label, start, end in WINDOWS:
        print(f"\n[{win_label}] {start} → {end}")
        data_tuple = fetch_window(start, end)
        results[win_label] = {}
        for mode in MODES:
            results[win_label][mode.value] = {}
            for atr_label, atr_enabled, atr_mult in ATR_CONFIGS:
                print(f"  running {mode.value} @ ATR={atr_label}...", flush=True)
                m = run_one(mode, atr_label, atr_enabled, atr_mult, data_tuple, equity)
                results[win_label][mode.value][atr_label] = m
                tr = m.get("total_pnl", 0) / equity * 100 if equity else 0
                sh = m.get("sharpe", 0)
                tc = m.get("total_trades", 0)
                print(f"    → return={tr:+.2f}%  Sharpe={sh:+.2f}  trades={tc}")

    config.ENABLE_ATR_EXPANSION_FILTER = orig_enabled
    config.ATR_EXPANSION_MULTIPLIER = orig_mult

    # Summary
    lines = []
    lines.append("=" * 100)
    lines.append("ATR EXPANSION FILTER SWEEP")
    lines.append(f"  Slippage pinned: {SLIPPAGE_PCT*100:.2f}%")
    lines.append(f"  Configs tested: OFF, 1.0x, 1.2x (current live), 1.5x")
    lines.append(f"  Universe: {len(config.MOMENTUM_UNIVERSE)} small-caps, fib retracement: ON")
    lines.append("=" * 100)

    for mode in MODES:
        lines.append("")
        lines.append(f"━━━ {mode.value.upper()} ━━━")

        # Returns table
        header = f"{'Window':<10}" + "".join(f"{'ATR='+c[0]:<14}" for c in ATR_CONFIGS)
        lines.append(header)
        lines.append("-" * len(header))
        for win_label, _, _ in WINDOWS:
            row = f"{win_label:<10}"
            for atr_label, _, _ in ATR_CONFIGS:
                m = results[win_label][mode.value].get(atr_label) or {}
                pnl = m.get("total_pnl", 0)
                ret = pnl / equity * 100 if equity else 0
                row += f"{ret:+.2f}%        "[:14]
            lines.append(row)

        # 24-mo total
        lines.append("")
        lines.append(f"  24-mo total return:")
        for atr_label, _, _ in ATR_CONFIGS:
            total = sum(((results[w[0]][mode.value].get(atr_label)) or {}).get("total_pnl", 0) for w in WINDOWS)
            ret = total / equity * 100
            lines.append(f"    ATR={atr_label:<6} {ret:+.2f}%")

        # Sharpe
        lines.append("")
        lines.append(f"  Sharpe by window:")
        for atr_label, _, _ in ATR_CONFIGS:
            row = f"    ATR={atr_label:<6} "
            for win_label, _, _ in WINDOWS:
                m = results[win_label][mode.value].get(atr_label) or {}
                sh = m.get("sharpe", 0)
                row += f"{win_label}: {sh:+.2f}   "
            lines.append(row)

        # Trade counts
        lines.append("")
        lines.append(f"  Trade count by window:")
        for atr_label, _, _ in ATR_CONFIGS:
            row = f"    ATR={atr_label:<6} "
            for win_label, _, _ in WINDOWS:
                m = results[win_label][mode.value].get(atr_label) or {}
                tc = m.get("total_trades", 0)
                row += f"{win_label}: {tc:>4}   "
            lines.append(row)

        # Max drawdown
        lines.append("")
        lines.append(f"  Max drawdown $ by window:")
        for atr_label, _, _ in ATR_CONFIGS:
            row = f"    ATR={atr_label:<6} "
            for win_label, _, _ in WINDOWS:
                m = results[win_label][mode.value].get(atr_label) or {}
                dd = m.get("max_drawdown_pnl", 0)
                row += f"{win_label}: ${dd:>7,.0f}   "
            lines.append(row)

    finished = datetime.now()
    lines.append("")
    lines.append("=" * 100)
    lines.append(f"  Started:  {started}")
    lines.append(f"  Finished: {finished}")
    lines.append(f"  Runtime:  {finished - started}")
    lines.append("=" * 100)

    summary = "\n".join(lines)
    print("\n" + summary)
    with open(OUT_LOG, "w") as f:
        f.write(summary + "\n")
    print(f"\nSaved → {OUT_LOG}")


if __name__ == "__main__":
    main()
