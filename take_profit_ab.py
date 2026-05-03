"""
take_profit_ab.py — Phase 4: take-profit-R sweep.

Question: does extending or removing the take-profit cap unlock more right-tail
return, or just add variance? ORB literature (Zarattini et al.) says the edge
lives in the trend-day runners that 2R cuts off. This A/B tests that claim on
our actual data.

Variants:
    TP_2R    : TAKE_PROFIT_R = 2.0  (current live config)
    TP_5R    : TAKE_PROFIT_R = 5.0  (longer hold, capture more tail)
    TP_TRAIL : TAKE_PROFIT_R = 100.0 (effectively unreachable; trade exits via
               stop or the 3:55 PM EOD force-close)

Usage:
    python take_profit_ab.py                          # all 4 windows, full_system
    python take_profit_ab.py --windows 2024H2         # one window
    python take_profit_ab.py --modes plain_orb full_system

Designed for overnight runs. ~9 min/sim × 4 windows × 3 variants × 1 mode
= ~108 min for the default config.
"""
from __future__ import annotations
import argparse
import logging
import os
from datetime import datetime

import config
import data as mkt_data
from backtest import BacktestConfig, BacktestEngine, StrategyMode

ALL_WINDOWS = [
    ("2023H1", "2023-01-03", "2023-06-30"),
    ("2023H2", "2023-07-03", "2023-12-29"),
    ("2024H1", "2024-01-02", "2024-06-28"),
    ("2024H2", "2024-07-01", "2024-12-31"),
]

# (label, TAKE_PROFIT_R value)
VARIANTS = [
    ("TP_2R",    2.0),
    ("TP_5R",    5.0),
    ("TP_TRAIL", 100.0),   # effectively unreachable — trade rides until stop or EOD
]

SLIPPAGE = 0.0010   # 0.10% per side


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


def run_one(mode, take_profit_r, data_tuple, equity):
    saved = config.TAKE_PROFIT_R
    try:
        config.TAKE_PROFIT_R = take_profit_r
        bars, vol, spy, pc, dr = data_tuple
        bt_cfg = BacktestConfig(
            mode=mode,
            initial_equity=equity,
            slippage_pct=SLIPPAGE,
            save_trades=False,
            trades_file="",
        )
        engine = BacktestEngine(bt_cfg)
        metrics = engine.run(bars, vol, spy, pc, dr) or {}
        metrics["return_pct"] = (
            (metrics.get("total_pnl", 0) / equity * 100) if equity > 0 else 0.0
        )
        return metrics
    finally:
        config.TAKE_PROFIT_R = saved


def main():
    parser = argparse.ArgumentParser(description="Take-profit-R A/B harness")
    parser.add_argument(
        "--windows",
        nargs="+",
        choices=[w[0] for w in ALL_WINDOWS],
        default=[w[0] for w in ALL_WINDOWS],
    )
    parser.add_argument(
        "--modes",
        nargs="+",
        choices=["plain_orb", "full_system"],
        default=["full_system"],
    )
    parser.add_argument(
        "--variants",
        nargs="+",
        choices=[v[0] for v in VARIANTS],
        default=[v[0] for v in VARIANTS],
    )
    parser.add_argument(
        "--out",
        default=os.path.join(config.BACKTEST_RESULTS_DIR, "take_profit_ab.log"),
    )
    args = parser.parse_args()

    selected_windows = [w for w in ALL_WINDOWS if w[0] in args.windows]
    selected_modes = [StrategyMode[m.upper()] for m in args.modes]
    selected_variants = [v for v in VARIANTS if v[0] in args.variants]

    logging.getLogger().setLevel(logging.WARNING)
    for noisy in ("backtest", "regime", "vix_factor", "vvix_filter", "data", "calendar_filter",
                  "sentiment", "sector_rotation", "performance"):
        logging.getLogger(noisy).setLevel(logging.WARNING)

    config.USE_FIB_RETRACEMENT_ENTRY = True

    equity = config.INITIAL_EQUITY
    os.makedirs(config.BACKTEST_RESULTS_DIR, exist_ok=True)

    logf = open(args.out, "w", buffering=1)
    def out(msg=""):
        print(msg)
        logf.write(msg + "\n")

    started = datetime.now()
    out("=" * 100)
    out("TAKE-PROFIT A/B — does extending the cap unlock more right-tail return?")
    out(f"  windows  : {[w[0] for w in selected_windows]}")
    out(f"  modes    : {[m.value for m in selected_modes]}")
    out(f"  variants : {[v[0] for v in selected_variants]}")
    out(f"  slippage : {SLIPPAGE * 100:.2f}% per side")
    out(f"  equity   : ${equity:,.0f}")
    out(f"  started  : {started.isoformat()}")
    out(f"  total runs: {len(selected_windows) * len(selected_modes) * len(selected_variants)}")
    out("=" * 100)

    # results[(mode, window_label, variant_label)] = metrics dict
    results: dict = {}

    for label, start, end in selected_windows:
        out(f"\n── Window {label}  ({start} → {end}) ──────────────────")
        out("  fetching data...")
        data_tuple = fetch_window(start, end)
        for mode in selected_modes:
            for v_label, tp_r in selected_variants:
                out(f"  [{mode.value}] {v_label} (TAKE_PROFIT_R={tp_r})...")
                m = run_one(mode, tp_r, data_tuple, equity)
                results[(mode, label, v_label)] = m
                out(
                    f"    → trades={m.get('total_trades', 0):4d}  "
                    f"win_rate={m.get('win_rate', 0):.1%}  "
                    f"return={m.get('return_pct', 0):+.2f}%  "
                    f"Sharpe={m.get('sharpe', 0):+.2f}  "
                    f"PF={m.get('profit_factor', 0):.2f}  "
                    f"avgR={m.get('avg_r_multiple', 0):.2f}R  "
                    f"maxDD=${m.get('max_drawdown_pnl', 0):,.0f}"
                )

    # ── Summary tables (one per mode) ─────────────────────────────────────
    out("\n" + "=" * 100)
    for mode in selected_modes:
        out(f"\n━━━ {mode.value.upper()} — TAKE-PROFIT COMPARISON ━━━")
        out(
            f"{'Window':<8} {'Variant':<10} "
            f"{'Trades':>7} {'WR':>7} {'Return':>9} {'Sharpe':>8} {'PF':>6} {'AvgR':>7} {'MaxDD$':>10}"
        )
        out("-" * 90)
        for label, _, _ in selected_windows:
            for v_label, _ in selected_variants:
                m = results.get((mode, label, v_label), {})
                out(
                    f"{label:<8} {v_label:<10} "
                    f"{m.get('total_trades', 0):>7d} "
                    f"{m.get('win_rate', 0):>6.1%} "
                    f"{m.get('return_pct', 0):>+8.2f}% "
                    f"{m.get('sharpe', 0):>+7.2f} "
                    f"{m.get('profit_factor', 0):>6.2f} "
                    f"{m.get('avg_r_multiple', 0):>+6.2f}R "
                    f"${m.get('max_drawdown_pnl', 0):>+9,.0f}"
                )
            out("-" * 90)
        # Aggregate over selected windows by variant
        out("  Σ over windows:")
        for v_label, _ in selected_variants:
            agg_ret = sum(
                results.get((mode, w[0], v_label), {}).get("return_pct", 0)
                for w in selected_windows
            )
            avg_sharpe = sum(
                results.get((mode, w[0], v_label), {}).get("sharpe", 0)
                for w in selected_windows
            ) / max(1, len(selected_windows))
            total_trades = sum(
                results.get((mode, w[0], v_label), {}).get("total_trades", 0)
                for w in selected_windows
            )
            out(
                f"    {v_label:<10} sum_return={agg_ret:+.2f}%  "
                f"avg_sharpe={avg_sharpe:+.2f}  total_trades={total_trades}"
            )

    finished = datetime.now()
    out("\n" + "=" * 100)
    out(f"  Started:  {started}")
    out(f"  Finished: {finished}")
    out(f"  Runtime:  {finished - started}")
    out("=" * 100)
    logf.close()


if __name__ == "__main__":
    main()
