"""
volume_threshold_sweep.py — Head-to-head test of VOLUME_MULTIPLIER values.

Question being answered: should we revert from 2.0x (current, set in session 5)
to 1.5x (original), or hold? 4/30 retrospective showed the 2.0x change cost
~3pp/window in backtest — but Sharpe / drawdown effects weren't measured
cleanly. This isolates VOLUME_MULTIPLIER as the single variable.

Same plumbing as slippage_stress.py: 4 windows × 2 strategies, but here we
sweep the volume multiplier {1.5, 1.7, 2.0} and pin slippage at 0.10%
(slightly above the 0.08% realized 4/30, conservative side).

Usage:  python volume_threshold_sweep.py
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

VOL_MULTIPLIERS = [1.5, 1.7, 2.0]
SLIPPAGE_PCT = 0.0010   # 0.10% — slightly conservative vs realized 0.08%
MODES = [StrategyMode.PLAIN_ORB, StrategyMode.FULL_SYSTEM]

OUT_LOG = os.path.join(config.BACKTEST_RESULTS_DIR, "volume_threshold_sweep.log")


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


def run_one(mode, vol_mult, data_tuple, equity):
    bars, vol, spy, pc, dr = data_tuple
    config.VOLUME_MULTIPLIER = vol_mult
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

    # Match the live config that produced our headline numbers
    config.USE_FIB_RETRACEMENT_ENTRY = True

    original_vol_mult = config.VOLUME_MULTIPLIER  # restore at end (defense-in-depth)
    equity = config.INITIAL_EQUITY
    os.makedirs(config.BACKTEST_RESULTS_DIR, exist_ok=True)

    started = datetime.now()
    print(f"=== Volume threshold sweep — started {started.strftime('%Y-%m-%d %H:%M:%S')} ===")
    print(f"  Sweeping VOLUME_MULTIPLIER ∈ {VOL_MULTIPLIERS}")
    print(f"  Slippage pinned at {SLIPPAGE_PCT*100:.2f}%")
    print(f"  Universe: {len(config.MOMENTUM_UNIVERSE)} small-caps, fib retracement entry: ON")
    print()

    results: dict = {}  # results[window][mode][vol_mult] = metrics
    for win_label, start, end in WINDOWS:
        print(f"\n[{win_label}] {start} → {end}")
        data_tuple = fetch_window(start, end)
        results[win_label] = {}
        for mode in MODES:
            results[win_label][mode.value] = {}
            for vm in VOL_MULTIPLIERS:
                print(f"  running {mode.value} @ vol={vm}x...", flush=True)
                m = run_one(mode, vm, data_tuple, equity)
                results[win_label][mode.value][vm] = m
                tr = m.get("total_pnl", 0) / equity * 100 if equity else 0
                sh = m.get("sharpe", 0)
                tc = m.get("total_trades", 0)
                print(f"    → return={tr:+.2f}%  Sharpe={sh:+.2f}  trades={tc}")

    config.VOLUME_MULTIPLIER = original_vol_mult

    # Summary
    lines = []
    lines.append("=" * 100)
    lines.append("VOLUME THRESHOLD SWEEP")
    lines.append(f"  Slippage pinned: {SLIPPAGE_PCT*100:.2f}%")
    lines.append(f"  Sweep: VOLUME_MULTIPLIER ∈ {VOL_MULTIPLIERS}")
    lines.append(f"  Universe: {len(config.MOMENTUM_UNIVERSE)} small-caps, fib retracement: ON")
    lines.append("=" * 100)

    for mode in MODES:
        lines.append("")
        lines.append(f"━━━ {mode.value.upper()} ━━━")

        # Returns table
        header = f"{'Window':<10}" + "".join(f"{'vol='+str(v)+'x':<14}" for v in VOL_MULTIPLIERS)
        lines.append(header)
        lines.append("-" * len(header))
        for win_label, _, _ in WINDOWS:
            row = f"{win_label:<10}"
            for vm in VOL_MULTIPLIERS:
                m = results[win_label][mode.value].get(vm) or {}
                pnl = m.get("total_pnl", 0)
                ret = pnl / equity * 100 if equity else 0
                row += f"{ret:+.2f}%        "[:14]
            lines.append(row)

        # 24-mo total
        lines.append("")
        lines.append(f"  24-mo total return:")
        for vm in VOL_MULTIPLIERS:
            total = sum(((results[w[0]][mode.value].get(vm)) or {}).get("total_pnl", 0) for w in WINDOWS)
            ret = total / equity * 100
            lines.append(f"    vol={vm}x   {ret:+.2f}%")

        # Sharpe per window per multiplier
        lines.append("")
        lines.append(f"  Sharpe by window:")
        for vm in VOL_MULTIPLIERS:
            row = f"    vol={vm}x   "
            for win_label, _, _ in WINDOWS:
                m = results[win_label][mode.value].get(vm) or {}
                sh = m.get("sharpe", 0)
                row += f"{win_label}: {sh:+.2f}   "
            lines.append(row)

        # Trade counts
        lines.append("")
        lines.append(f"  Trade count by window:")
        for vm in VOL_MULTIPLIERS:
            row = f"    vol={vm}x   "
            for win_label, _, _ in WINDOWS:
                m = results[win_label][mode.value].get(vm) or {}
                tc = m.get("total_trades", 0)
                row += f"{win_label}: {tc:>4}   "
            lines.append(row)

        # Max drawdown
        lines.append("")
        lines.append(f"  Max drawdown $ by window:")
        for vm in VOL_MULTIPLIERS:
            row = f"    vol={vm}x   "
            for win_label, _, _ in WINDOWS:
                m = results[win_label][mode.value].get(vm) or {}
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
