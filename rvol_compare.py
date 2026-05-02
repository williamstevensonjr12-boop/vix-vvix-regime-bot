"""
rvol_compare.py — Phase 2 audit comparison: legacy 20-bar avg vs same-time-of-day RVOL.

Question being answered: does switching the volume baseline from a rolling-20
mix-of-time-of-day average to a same-time-of-day median (as the published ORB
literature uses) improve, hold, or degrade returns / Sharpe / trade count?

Same 4 windows + 2 modes as slippage_stress, single slippage assumption
(0.10% — realistic for small-cap limit-order fills), variable is RVOL metric.

Output: a single side-by-side table.

Usage:  python rvol_compare.py
"""
from __future__ import annotations
import argparse
import logging
import os
import sys
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

# 0.10% per side — realistic for small-cap limit-order fills (matches the
# realized 0.08% slippage from the 2 live limit-order fills we have so far,
# rounded up)
SLIPPAGE = 0.0010
MODES = [StrategyMode.PLAIN_ORB, StrategyMode.FULL_SYSTEM]

# False = legacy 20-bar simple rolling avg
# True  = same-time-of-day median over prior 14 days
RVOL_SETTINGS = [False, True]

OUT_LOG = os.path.join(config.BACKTEST_RESULTS_DIR, "rvol_compare.log")


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


def run_one(mode, rvol_on, data_tuple, equity):
    bars, vol, spy, pc, dr = data_tuple
    config.USE_TIME_OF_DAY_RVOL = rvol_on    # flag set before engine.run
    bt_cfg = BacktestConfig(
        mode=mode,
        initial_equity=equity,
        slippage_pct=SLIPPAGE,
        save_trades=False,
        trades_file="",
    )
    engine = BacktestEngine(bt_cfg)
    metrics = engine.run(bars, vol, spy, pc, dr) or {}
    # Engine returns total_pnl + max_drawdown_pnl (not pre-computed pct).
    # Compute return % from total_pnl / initial_equity for consistency with
    # how other backtest scripts (limit_order_backtest, slippage_stress) report.
    metrics["return_pct"] = (metrics.get("total_pnl", 0) / equity * 100) if equity > 0 else 0.0
    return metrics


def main():
    parser = argparse.ArgumentParser(description="RVOL legacy-vs-time-of-day backtest comparison")
    parser.add_argument(
        "--windows",
        nargs="+",
        choices=[w[0] for w in ALL_WINDOWS],
        default=[w[0] for w in ALL_WINDOWS],
        help="Subset of windows to run (default: all 4). Use a single window like '2023H1' for a fast sanity check.",
    )
    parser.add_argument(
        "--out",
        default=OUT_LOG,
        help="Output log path (default: backtest_results/rvol_compare.log)",
    )
    args = parser.parse_args()

    selected = [w for w in ALL_WINDOWS if w[0] in args.windows]

    # Suppress noisy backtest internals — we only want the summary
    logging.getLogger().setLevel(logging.WARNING)
    for noisy in ("backtest", "regime", "vix_factor", "vvix_filter", "data", "calendar_filter",
                  "sentiment", "sector_rotation", "performance"):
        logging.getLogger(noisy).setLevel(logging.WARNING)

    # Match the validated config that produced the prior backtest numbers
    config.USE_FIB_RETRACEMENT_ENTRY = True

    equity = config.INITIAL_EQUITY
    os.makedirs(config.BACKTEST_RESULTS_DIR, exist_ok=True)

    # Open the log file in line-buffered mode, mirror to stdout
    logf = open(args.out, "w", buffering=1)
    def out(msg=""):
        print(msg)
        logf.write(msg + "\n")

    started = datetime.now()
    out("=" * 100)
    out(f"RVOL COMPARE — same-time-of-day median vs legacy rolling-20 avg")
    out(f"  windows : {[w[0] for w in selected]}")
    out(f"  modes   : {[m.value for m in MODES]}")
    out(f"  slippage: {SLIPPAGE * 100:.2f}% per side")
    out(f"  equity  : ${equity:,.0f}")
    out(f"  started : {started.isoformat()}")
    out("=" * 100)

    # results[(mode, window_label, rvol_on)] = metrics dict
    results: dict = {}

    for label, start, end in selected:
        out(f"\n── Window {label}  ({start} → {end}) ─────────────────────────────")
        out("  fetching data...")
        data_tuple = fetch_window(start, end)
        for mode in MODES:
            for rvol_on in RVOL_SETTINGS:
                tag = f"{mode.value} | rvol_tod={'ON' if rvol_on else 'OFF'}"
                out(f"  running: {tag}...")
                m = run_one(mode, rvol_on, data_tuple, equity)
                results[(mode, label, rvol_on)] = m
                out(
                    f"    → trades={m.get('total_trades', 0):4d}  "
                    f"win_rate={m.get('win_rate', 0):.1%}  "
                    f"return={m.get('return_pct', 0):+.2f}%  "
                    f"Sharpe={m.get('sharpe', 0):+.2f}  "
                    f"PF={m.get('profit_factor', 0):.2f}  "
                    f"maxDD=${m.get('max_drawdown_pnl', 0):,.0f}"
                )

    # ── Summary table ────────────────────────────────────────────────────────
    out("\n" + "=" * 100)
    for mode in MODES:
        out(f"\n━━━ {mode.value.upper()} — {SLIPPAGE * 100:.2f}% slippage ━━━")
        out(
            f"{'Window':<8} {'rvol_tod':<10} "
            f"{'Trades':>7} {'WR':>7} {'Return':>9} {'Sharpe':>8} {'PF':>6} {'MaxDD$':>10}"
        )
        out("-" * 80)
        for label, _, _ in WINDOWS:
            for rvol_on in RVOL_SETTINGS:
                m = results.get((mode, label, rvol_on), {})
                tag = "ON" if rvol_on else "OFF"
                out(
                    f"{label:<8} {tag:<10} "
                    f"{m.get('total_trades', 0):>7d} "
                    f"{m.get('win_rate', 0):>6.1%} "
                    f"{m.get('return_pct', 0):>+8.2f}% "
                    f"{m.get('sharpe', 0):>+7.2f} "
                    f"{m.get('profit_factor', 0):>6.2f} "
                    f"${m.get('max_drawdown_pnl', 0):>+9,.0f}"
                )
        out("-" * 80)
        # Aggregate over selected windows (sum of per-window returns is approximate)
        agg_off = sum(results.get((mode, w[0], False), {}).get("return_pct", 0) for w in selected)
        agg_on = sum(results.get((mode, w[0], True), {}).get("return_pct", 0) for w in selected)
        out(f"  Σ over {len(selected)} window(s): OFF {agg_off:+.2f}%   ON {agg_on:+.2f}%   Δ {agg_on - agg_off:+.2f}pp")

    finished = datetime.now()
    out("\n" + "=" * 100)
    out(f"  Started:  {started}")
    out(f"  Finished: {finished}")
    out(f"  Runtime:  {finished - started}")
    out("=" * 100)
    logf.close()


if __name__ == "__main__":
    main()
