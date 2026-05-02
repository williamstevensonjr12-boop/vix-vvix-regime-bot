"""
limit_order_backtest.py — v1 backtest of the limit-order entry path.

Compares the current market-order behavior to the proposed limit-order Phase 1
across the standard 4-window suite, on the live 30-name small-cap universe.

Configurations:
  - market@0.10% slip (current live, baseline)
  - market@0.08% slip (matches realized 4/30 sample)
  - limit@5bp buffer
  - limit@10bp buffer
  - limit@15bp buffer

For each config × strategy × window: total return, Sharpe, trade count, missed
entries (limit configs only), max drawdown.

Decision rule from the design doc §12: if limit-order returns are meaningfully
better than market@0.10% (or comparable AND with smaller drawdown), ship Phase 1
behind the live feature flag.

Usage:  python limit_order_backtest.py
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

# (label, use_limit_sim, slippage_pct, buffer_pct)
CONFIGS = [
    ("market@0.10",  False, 0.0010, 0.0010),
    ("market@0.08",  False, 0.0008, 0.0010),
    ("limit@5bp",    True,  0.0010, 0.0005),
    ("limit@10bp",   True,  0.0010, 0.0010),
    ("limit@15bp",   True,  0.0010, 0.0015),
]

MODES = [StrategyMode.PLAIN_ORB, StrategyMode.FULL_SYSTEM]
OUT_LOG = os.path.join(config.BACKTEST_RESULTS_DIR, "limit_order_backtest.log")


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


def run_one(mode, use_limit, slip, buf, data_tuple, equity):
    bars, vol, spy, pc, dr = data_tuple
    bt_cfg = BacktestConfig(
        mode=mode,
        initial_equity=equity,
        slippage_pct=slip,
        save_trades=False,
        trades_file="",
        use_limit_entry_sim=use_limit,
        limit_order_buffer_pct=buf,
    )
    engine = BacktestEngine(bt_cfg)
    metrics = engine.run(bars, vol, spy, pc, dr) or {}
    metrics["missed_entries"] = bt_cfg.missed_entries_count
    return metrics


def main():
    logging.getLogger().setLevel(logging.WARNING)
    for noisy in ("backtest", "regime", "vix_factor", "vvix_filter", "data",
                  "calendar_filter", "sentiment", "sector_rotation", "performance"):
        logging.getLogger(noisy).setLevel(logging.WARNING)

    config.USE_FIB_RETRACEMENT_ENTRY = True
    equity = config.INITIAL_EQUITY
    os.makedirs(config.BACKTEST_RESULTS_DIR, exist_ok=True)

    started = datetime.now()
    print(f"=== Limit-order Phase 1 backtest — started {started.strftime('%Y-%m-%d %H:%M:%S')} ===")
    print(f"  Configs: {[c[0] for c in CONFIGS]}")
    print(f"  Universe: {len(config.MOMENTUM_UNIVERSE)} small-caps, fib retracement: ON")
    print(f"  Total runs: {len(WINDOWS)} × {len(MODES)} × {len(CONFIGS)} = {len(WINDOWS)*len(MODES)*len(CONFIGS)}")
    print()

    results: dict = {}
    for win_label, start, end in WINDOWS:
        print(f"\n[{win_label}] {start} → {end}")
        data_tuple = fetch_window(start, end)
        results[win_label] = {}
        for mode in MODES:
            results[win_label][mode.value] = {}
            for cfg_label, use_limit, slip, buf in CONFIGS:
                print(f"  running {mode.value} @ {cfg_label}...", flush=True)
                m = run_one(mode, use_limit, slip, buf, data_tuple, equity)
                results[win_label][mode.value][cfg_label] = m
                tr = m.get("total_pnl", 0) / equity * 100 if equity else 0
                sh = m.get("sharpe", 0)
                tc = m.get("total_trades", 0)
                miss = m.get("missed_entries", 0)
                print(f"    → return={tr:+.2f}%  Sharpe={sh:+.2f}  trades={tc}  missed={miss}")

    lines = []
    lines.append("=" * 110)
    lines.append("LIMIT-ORDER PHASE 1 BACKTEST")
    lines.append(f"  Universe: {len(config.MOMENTUM_UNIVERSE)} small-caps, fib retracement: ON")
    lines.append(f"  Configs: market@0.10 (current live), market@0.08 (realized), limit@5bp/10bp/15bp")
    lines.append(f"  v1 fill model: limit fills if next bar's high (long) / low (short) crosses limit price")
    lines.append("=" * 110)

    for mode in MODES:
        lines.append("")
        lines.append(f"━━━ {mode.value.upper()} ━━━")

        # Returns table
        header = f"{'Window':<10}" + "".join(f"{c[0]:<14}" for c in CONFIGS)
        lines.append(header)
        lines.append("-" * len(header))
        for win_label, _, _ in WINDOWS:
            row = f"{win_label:<10}"
            for cfg_label, _, _, _ in CONFIGS:
                m = results[win_label][mode.value].get(cfg_label) or {}
                pnl = m.get("total_pnl", 0)
                ret = pnl / equity * 100 if equity else 0
                row += f"{ret:+.2f}%        "[:14]
            lines.append(row)

        lines.append("")
        lines.append(f"  24-mo total return:")
        for cfg_label, _, _, _ in CONFIGS:
            total = sum(((results[w[0]][mode.value].get(cfg_label)) or {}).get("total_pnl", 0) for w in WINDOWS)
            ret = total / equity * 100
            lines.append(f"    {cfg_label:<14} {ret:+.2f}%")

        lines.append("")
        lines.append(f"  Sharpe by window:")
        for cfg_label, _, _, _ in CONFIGS:
            row = f"    {cfg_label:<14}"
            for win_label, _, _ in WINDOWS:
                m = results[win_label][mode.value].get(cfg_label) or {}
                sh = m.get("sharpe", 0)
                row += f"  {win_label}: {sh:+.2f}"
            lines.append(row)

        lines.append("")
        lines.append(f"  Trades / missed:")
        for cfg_label, _, _, _ in CONFIGS:
            row = f"    {cfg_label:<14}"
            for win_label, _, _ in WINDOWS:
                m = results[win_label][mode.value].get(cfg_label) or {}
                tc = m.get("total_trades", 0)
                miss = m.get("missed_entries", 0)
                row += f"  {win_label}: {tc:>3}t/{miss:>3}m"
            lines.append(row)

        lines.append("")
        lines.append(f"  Max drawdown $ by window:")
        for cfg_label, _, _, _ in CONFIGS:
            row = f"    {cfg_label:<14}"
            for win_label, _, _ in WINDOWS:
                m = results[win_label][mode.value].get(cfg_label) or {}
                dd = m.get("max_drawdown_pnl", 0)
                row += f"  {win_label}: ${dd:>7,.0f}"
            lines.append(row)

    finished = datetime.now()
    lines.append("")
    lines.append("=" * 110)
    lines.append(f"  Started:  {started}")
    lines.append(f"  Finished: {finished}")
    lines.append(f"  Runtime:  {finished - started}")
    lines.append("=" * 110)

    summary = "\n".join(lines)
    print("\n" + summary)
    with open(OUT_LOG, "w") as f:
        f.write(summary + "\n")
    print(f"\nSaved → {OUT_LOG}")


if __name__ == "__main__":
    main()
