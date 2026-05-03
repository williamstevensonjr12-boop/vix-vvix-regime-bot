"""
universe_ab.py — universe-switch A/B: mega-cap vs small-cap on the audit
4-window panel (2023H1, 2023H2, 2024H1, 2024H2).

Question: is the strategy unprofitable because the strategy is broken, or
because the 2026-04-29 universe switch (mega-cap → 30 small-caps) was the
wrong call?

Variants:
    SMALL_CAP : current live MOMENTUM_UNIVERSE (30 small-caps)
    MEGA_CAP  : pre-2026-04-29 list (12 names: SPY/QQQ/AAPL/MSFT/NVDA/AMZN/
                META/TSLA/AMD/KO/BP/NUE)

Matches the existing backtest harnesses (filter_ablation, take_profit_ab):
USE_FIB_RETRACEMENT_ENTRY forced True for apples-to-apples comparison with
those prior runs. NOTE: live config has it False — that's a separate
backtest-vs-live drift worth flagging.

Usage:
    python universe_ab.py                          # all 4 windows, full_system
    python universe_ab.py --windows 2024H2         # one window

8 sims (4 windows × 2 variants × 1 mode). Take-profit A/B was 12 sims in
21 min, so ETA ~14 min.
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

SMALL_CAP = list(config.MOMENTUM_UNIVERSE)
MEGA_CAP = ["SPY", "QQQ", "AAPL", "MSFT", "NVDA", "AMZN", "META", "TSLA", "AMD",
            "KO", "BP", "NUE"]

VARIANTS = [
    ("SMALL_CAP", SMALL_CAP),
    ("MEGA_CAP",  MEGA_CAP),
]

SLIPPAGE = 0.0010   # 0.10% per side — match prior harnesses


def union_symbols() -> list:
    """Union of both universe variants + the rest of the symbol pool used by
    the bot (Regime B/C names, SPY for trend, short universe). Pre-fetch once
    per window so swapping MOMENTUM_UNIVERSE between variants is just a config
    flip — no re-download."""
    return list(dict.fromkeys(
        SMALL_CAP + MEGA_CAP
        + config.FEAR_RESILIENT_UNIVERSE + config.DEFENSIVE_UNIVERSE
        + config.SHORT_UNIVERSE + ["SPY"]
    ))


def fetch_window(start: str, end: str):
    data_client = mkt_data.get_data_client()
    symbols = union_symbols()
    print(f"  downloading bars for {len(symbols)} symbols (union of variants)...")
    bars_by_symbol = mkt_data.get_multiple_symbols_bars(data_client, symbols, start, end)
    print("  downloading vol (VIX/VVIX/VIX3M)...")
    vol_df = mkt_data.get_vix_history(start, end)
    print("  downloading SPY daily...")
    spy_daily = mkt_data.get_spy_daily(start, end)
    print("  downloading put/call...")
    pc_series = mkt_data.get_put_call_history(start, end)
    print("  computing daily returns for VIX beta...")
    daily_returns = {
        sym: mkt_data.get_symbol_daily_returns(data_client, sym, start, end)
        for sym in symbols
    }
    return bars_by_symbol, vol_df, spy_daily, pc_series, daily_returns


def run_one(mode, universe, data_tuple, equity):
    saved_universe = list(config.MOMENTUM_UNIVERSE)
    saved_all = list(config.ALL_SYMBOLS)
    try:
        config.MOMENTUM_UNIVERSE = list(universe)
        config.ALL_SYMBOLS = list(dict.fromkeys(
            config.MOMENTUM_UNIVERSE + config.FEAR_RESILIENT_UNIVERSE
            + config.DEFENSIVE_UNIVERSE + config.SHORT_UNIVERSE
        ))
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
        config.MOMENTUM_UNIVERSE = saved_universe
        config.ALL_SYMBOLS = saved_all


def main():
    parser = argparse.ArgumentParser(description="Universe A/B: mega-cap vs small-cap")
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
        default=os.path.join(config.BACKTEST_RESULTS_DIR, "universe_ab.log"),
    )
    args = parser.parse_args()

    selected_windows = [w for w in ALL_WINDOWS if w[0] in args.windows]
    selected_modes = [StrategyMode[m.upper()] for m in args.modes]
    selected_variants = [v for v in VARIANTS if v[0] in args.variants]

    logging.getLogger().setLevel(logging.WARNING)
    for noisy in ("backtest", "regime", "vix_factor", "vvix_filter", "data", "calendar_filter",
                  "sentiment", "sector_rotation", "performance"):
        logging.getLogger(noisy).setLevel(logging.WARNING)

    config.USE_FIB_RETRACEMENT_ENTRY = True   # match filter_ablation / take_profit_ab

    equity = config.INITIAL_EQUITY
    os.makedirs(config.BACKTEST_RESULTS_DIR, exist_ok=True)

    logf = open(args.out, "w", buffering=1)
    def out(msg=""):
        print(msg)
        logf.write(msg + "\n")

    started = datetime.now()
    out("=" * 100)
    out("UNIVERSE A/B — does the 2026-04-29 mega-cap → small-cap switch explain the bleed?")
    out(f"  windows  : {[w[0] for w in selected_windows]}")
    out(f"  modes    : {[m.value for m in selected_modes]}")
    out(f"  variants : {[v[0] for v in selected_variants]}")
    out(f"  small_cap: {SMALL_CAP}")
    out(f"  mega_cap : {MEGA_CAP}")
    out(f"  slippage : {SLIPPAGE * 100:.2f}% per side")
    out(f"  fib_retr : USE_FIB_RETRACEMENT_ENTRY = True (matches prior harnesses)")
    out(f"  equity   : ${equity:,.0f}")
    out(f"  started  : {started.isoformat()}")
    out(f"  total runs: {len(selected_windows) * len(selected_modes) * len(selected_variants)}")
    out("=" * 100)

    results: dict = {}

    for label, start, end in selected_windows:
        out(f"\n── Window {label}  ({start} → {end}) ──────────────────")
        out("  fetching data...")
        data_tuple = fetch_window(start, end)
        for mode in selected_modes:
            for v_label, universe in selected_variants:
                out(f"  [{mode.value}] {v_label} ({len(universe)} symbols)...")
                m = run_one(mode, universe, data_tuple, equity)
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

    out("\n" + "=" * 100)
    for mode in selected_modes:
        out(f"\n━━━ {mode.value.upper()} — UNIVERSE COMPARISON ━━━")
        out(
            f"{'Window':<8} {'Universe':<10} "
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
