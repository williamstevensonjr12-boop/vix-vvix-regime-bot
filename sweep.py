"""
sweep.py — VWAP parameter sweep for the 2024 backtest.
Tests combinations of VWAP_VOL_MULTIPLIER and TAKE_PROFIT_R, compares each
against the current ORB full_system baseline, saves a ranked summary.

Usage:
  python sweep.py --start 2024-01-02 --end 2024-12-31
"""
from __future__ import annotations
import argparse
import logging
import os
import json
from datetime import datetime

import config
import data as mkt_data
from backtest import BacktestConfig, BacktestEngine, StrategyMode

logging.basicConfig(
    level=logging.WARNING,
    format="%(asctime)s | %(levelname)-8s | %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)

SWEEP_PARAMS = [
    {"VWAP_VOL_MULTIPLIER": 1.5, "TAKE_PROFIT_R": 1.5},
    {"VWAP_VOL_MULTIPLIER": 1.5, "TAKE_PROFIT_R": 2.0},
    {"VWAP_VOL_MULTIPLIER": 1.5, "TAKE_PROFIT_R": 2.5},
    {"VWAP_VOL_MULTIPLIER": 2.0, "TAKE_PROFIT_R": 1.5},
    {"VWAP_VOL_MULTIPLIER": 2.0, "TAKE_PROFIT_R": 2.0},
    {"VWAP_VOL_MULTIPLIER": 2.0, "TAKE_PROFIT_R": 2.5},
    {"VWAP_VOL_MULTIPLIER": 2.5, "TAKE_PROFIT_R": 1.5},
    {"VWAP_VOL_MULTIPLIER": 2.5, "TAKE_PROFIT_R": 2.0},
    {"VWAP_VOL_MULTIPLIER": 2.5, "TAKE_PROFIT_R": 2.5},
    {"VWAP_VOL_MULTIPLIER": 3.0, "TAKE_PROFIT_R": 2.0},
    {"VWAP_VOL_MULTIPLIER": 3.0, "TAKE_PROFIT_R": 2.5},
]


def run_single(mode: StrategyMode, data: dict, params: dict, initial_equity: float) -> dict:
    config.VWAP_VOL_MULTIPLIER = params.get("VWAP_VOL_MULTIPLIER", config.VWAP_VOL_MULTIPLIER)
    config.TAKE_PROFIT_R = params.get("TAKE_PROFIT_R", config.TAKE_PROFIT_R)

    bt_cfg = BacktestConfig(mode=mode, initial_equity=initial_equity, save_trades=False)
    engine = BacktestEngine(bt_cfg)
    metrics = engine.run(
        data["bars"], data["vol_df"], data["spy_daily"], data["pc_series"], data["daily_returns"]
    )
    return metrics


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--start", default="2024-01-02")
    parser.add_argument("--end", default="2024-12-31")
    parser.add_argument("--equity", type=float, default=config.INITIAL_EQUITY)
    args = parser.parse_args()

    print(f"\nVWAP Parameter Sweep | {args.start} → {args.end}")
    print("Downloading market data (once)...")

    data_client = mkt_data.get_data_client()
    all_symbols = list(dict.fromkeys(config.ALL_SYMBOLS + ["SPY"]))
    data = {
        "bars":          mkt_data.get_multiple_symbols_bars(data_client, all_symbols, args.start, args.end),
        "vol_df":        mkt_data.get_vix_history(args.start, args.end),
        "spy_daily":     mkt_data.get_spy_daily(args.start, args.end),
        "pc_series":     mkt_data.get_put_call_history(args.start, args.end),
        "daily_returns": {s: mkt_data.get_symbol_daily_returns(data_client, s, args.start, args.end)
                          for s in config.ALL_SYMBOLS},
    }
    print("Data ready. Running baseline (ORB full_system)...")

    # Baseline: current ORB full system
    baseline_params = {"VWAP_VOL_MULTIPLIER": 2.5, "TAKE_PROFIT_R": 2.0}
    baseline = run_single(StrategyMode.FULL_SYSTEM, data, baseline_params, args.equity)

    results = []
    total = len(SWEEP_PARAMS)
    for i, params in enumerate(SWEEP_PARAMS, 1):
        label = f"VWAP vol={params['VWAP_VOL_MULTIPLIER']}x R={params['TAKE_PROFIT_R']}"
        print(f"[{i}/{total}] {label} ...", end=" ", flush=True)
        m = run_single(StrategyMode.VWAP_FULL_SYSTEM, data, params, args.equity)
        results.append({"params": params, "metrics": m, "label": label})
        ret = m.get("total_pnl", 0) / args.equity * 100
        wr = m.get("win_rate", 0)
        sharpe = m.get("sharpe", 0)
        print(f"return={ret:+.2f}%  win_rate={wr:.1%}  sharpe={sharpe:.2f}")

    # Rank by Sharpe then return
    results.sort(key=lambda x: (x["metrics"].get("sharpe", -99), x["metrics"].get("total_pnl", 0)), reverse=True)

    print("\n" + "=" * 80)
    print("SWEEP RESULTS — VWAP FULL SYSTEM (ranked by Sharpe)")
    print(f"Baseline ORB Full System: return={baseline.get('total_pnl',0)/args.equity*100:+.2f}%  "
          f"win_rate={baseline.get('win_rate',0):.1%}  sharpe={baseline.get('sharpe',0):.2f}  "
          f"drawdown=${baseline.get('max_drawdown_pnl',0):,.0f}")
    print("-" * 80)
    print(f"{'Rank':<5} {'Label':<35} {'Return':>8} {'WinRate':>8} {'Sharpe':>8} {'Drawdown':>12} {'PF':>6}")
    print("-" * 80)
    for rank, r in enumerate(results, 1):
        m = r["metrics"]
        ret = m.get("total_pnl", 0) / args.equity * 100
        print(
            f"{rank:<5} {r['label']:<35} {ret:>+8.2f}% {m.get('win_rate',0):>8.1%} "
            f"{m.get('sharpe',0):>8.2f} ${m.get('max_drawdown_pnl',0):>10,.0f} "
            f"{m.get('profit_factor',0):>6.2f}"
        )
    print("=" * 80)

    # Save JSON
    out = {
        "run_at": datetime.now().isoformat(),
        "period": f"{args.start} → {args.end}",
        "baseline_orb_full_system": baseline,
        "vwap_sweep": results,
    }
    os.makedirs(config.BACKTEST_RESULTS_DIR, exist_ok=True)
    out_path = os.path.join(config.BACKTEST_RESULTS_DIR, "vwap_sweep_results.json")
    with open(out_path, "w") as f:
        json.dump(out, f, indent=2, default=str)
    print(f"\nFull results saved to {out_path}")


if __name__ == "__main__":
    main()
