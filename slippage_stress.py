"""
slippage_stress.py — Stress-test the strategy against realistic small-cap slippage.

Downloads bars once per window, then runs (Plain ORB, ORB Full System) with
USE_FIB_RETRACEMENT_ENTRY=True at slippage = {0.03%, 0.10%, 0.15%} per side.

Question being answered: does the +13.41% / +10.78% 24-month edge survive
slippage assumptions consistent with actual small-cap fills?

Usage:  python slippage_stress.py
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

SLIPPAGE_LEVELS = [0.0003, 0.0010, 0.0015]   # 0.03%, 0.10%, 0.15%
MODES = [StrategyMode.PLAIN_ORB, StrategyMode.FULL_SYSTEM]

OUT_LOG = os.path.join(config.BACKTEST_RESULTS_DIR, "slippage_stress.log")


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


def run_one(mode, slippage, data_tuple, equity):
    bars, vol, spy, pc, dr = data_tuple
    bt_cfg = BacktestConfig(
        mode=mode,
        initial_equity=equity,
        slippage_pct=slippage,
        save_trades=False,
        trades_file="",
    )
    engine = BacktestEngine(bt_cfg)
    metrics = engine.run(bars, vol, spy, pc, dr)
    return metrics or {}


def main():
    # Suppress noisy backtest internals — we only want the summary
    logging.getLogger().setLevel(logging.WARNING)
    for noisy in ("backtest", "regime", "vix_factor", "vvix_filter", "data", "calendar_filter",
                  "sentiment", "sector_rotation", "performance"):
        logging.getLogger(noisy).setLevel(logging.WARNING)

    # Flip retracement entry on for this test — matches the config that produced
    # the headline +13.41%/+10.78% 24-mo numbers we're trying to validate.
    config.USE_FIB_RETRACEMENT_ENTRY = True

    equity = config.INITIAL_EQUITY
    os.makedirs(config.BACKTEST_RESULTS_DIR, exist_ok=True)

    # results[window][mode_name][slip] = metrics
    results = {w[0]: {m.value: {} for m in MODES} for w in WINDOWS}

    started = datetime.now()
    for win_label, start, end in WINDOWS:
        print(f"\n=== {win_label} ({start} → {end}) ===")
        try:
            data_tuple = fetch_window(start, end)
        except Exception as e:
            print(f"  FAILED to download: {e}")
            continue

        for mode in MODES:
            for slip in SLIPPAGE_LEVELS:
                tag = f"{mode.value} | slip={slip*100:.2f}%"
                print(f"  running {tag}...")
                try:
                    m = run_one(mode, slip, data_tuple, equity)
                except Exception as e:
                    print(f"    ERROR: {e}")
                    m = {}
                results[win_label][mode.value][slip] = m

    elapsed = (datetime.now() - started).total_seconds()
    print(f"\nFinished {len(WINDOWS)} windows × {len(MODES)} modes × {len(SLIPPAGE_LEVELS)} slip levels in {elapsed/60:.1f} min")

    # ── Build summary tables ──────────────────────────────────────────────────
    lines = []
    lines.append("=" * 100)
    lines.append("SLIPPAGE STRESS TEST")
    lines.append(f"  config: USE_FIB_RETRACEMENT_ENTRY=True, MOMENTUM_UNIVERSE={len(config.MOMENTUM_UNIVERSE)} small-caps")
    lines.append(f"  equity: ${equity:,.0f}, slippage: {[f'{s*100:.2f}%' for s in SLIPPAGE_LEVELS]}")
    lines.append("=" * 100)

    for mode in MODES:
        lines.append("")
        lines.append(f"━━━ {mode.value.upper()} ━━━")
        header = f"{'Window':<10}" + "".join(f"{'@'+f'{s*100:.2f}%':<14}" for s in SLIPPAGE_LEVELS) + f"{'Δ vs base':<14}"
        lines.append(header)
        lines.append("-" * len(header))
        for win_label, _, _ in WINDOWS:
            row_metrics = results[win_label][mode.value]
            row = f"{win_label:<10}"
            base_pnl = (row_metrics.get(SLIPPAGE_LEVELS[0]) or {}).get("total_pnl", 0)
            base_ret = base_pnl / equity * 100 if equity else 0
            for slip in SLIPPAGE_LEVELS:
                m = row_metrics.get(slip) or {}
                pnl = m.get("total_pnl", 0)
                ret = pnl / equity * 100 if equity else 0
                row += f"{ret:+.2f}%        "[:14]
            stress_pnl = (row_metrics.get(SLIPPAGE_LEVELS[-1]) or {}).get("total_pnl", 0)
            stress_ret = stress_pnl / equity * 100 if equity else 0
            delta = stress_ret - base_ret
            row += f"{delta:+.2f} pp"
            lines.append(row)

        # Sharpe row
        lines.append("")
        lines.append(f"  Sharpe by slippage:")
        for slip in SLIPPAGE_LEVELS:
            row = f"    @{slip*100:.2f}%   "
            for win_label, _, _ in WINDOWS:
                m = (results[win_label][mode.value].get(slip)) or {}
                sh = m.get("sharpe", 0)
                row += f"{win_label}: {sh:+.2f}   "
            lines.append(row)

        # 24-mo sum
        lines.append("")
        lines.append(f"  24-mo total return:")
        for slip in SLIPPAGE_LEVELS:
            total = sum(((results[w[0]][mode.value].get(slip)) or {}).get("total_pnl", 0) for w in WINDOWS)
            ret = total / equity * 100
            lines.append(f"    @{slip*100:.2f}%  {ret:+.2f}%   (sum of 4 window P&L on $%s base)" % f"{equity:,.0f}")

    lines.append("")
    lines.append("=" * 100)
    summary = "\n".join(lines)
    print("\n" + summary)

    with open(OUT_LOG, "w") as f:
        f.write(summary + "\n")
    print(f"\nSaved → {OUT_LOG}")


if __name__ == "__main__":
    main()
