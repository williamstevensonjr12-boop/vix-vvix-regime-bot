"""
filter_ablation.py — Identify which strategy filters are load-bearing.

Phase 2 audit (2026-05-02) follow-up. After confirming the volume gate is
decorative (toggling its baseline produced byte-identical trade count and
return), pivot to the broader question: which gates actually do the work,
and which are dead weight?

For each filter in the ablation set, run the backtest once with that filter
disabled and compare metrics vs the baseline (all filters at current defaults).
Filters that materially change the trade count or return are load-bearing.
Filters that don't are decorative — candidates for removal or simplification.

Usage:
    python filter_ablation.py --windows 2023H1
    python filter_ablation.py --windows 2023H1 --filters ATR_EXPANSION GAP_ALIGNMENT
    python filter_ablation.py --windows 2023H1 --modes plain_orb
    python filter_ablation.py --windows 2023H1 2024H1 --modes plain_orb full_system

Notes:
    - Each ablation toggles ONE filter off vs the live defaults. Combinatorial
      ablations (multiple filters off at once) are intentionally not supported
      here — they multiply runtime and complicate attribution.
    - All filters that have a config flag are togglable. Filters hardcoded
      in strategy.py (calendar, earnings, ORB-break, VWAP-direction) are not
      part of the ablation set; they require code changes to disable.
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

# Map filter label → (config attribute, "off" value).
# When the config attribute is set to "off" value, that filter no longer
# constrains entries.
FILTERS = {
    # Volume threshold is the gate Phase 2c showed is decorative — kept here
    # so the ablation table makes that finding explicit alongside the others.
    "VOLUME":         ("VOLUME_MULTIPLIER", 0.0),
    # Daily SPY+IWM trend gate; blocks Regime A entries when SPY < 50d MA.
    "SPY_TREND":      ("SPY_TREND_FILTER", False),
    # ATR expansion confirmation (current ATR > multiplier × 20-bar mean ATR).
    "ATR_EXPANSION":  ("ENABLE_ATR_EXPANSION_FILTER", False),
    # Gap-alignment: requires a same-direction overnight gap before allowing entry.
    "GAP_ALIGNMENT":  ("GAP_ALIGNMENT_REQUIRED", False),
    # Skip flat opens: rejects entries when ORB range is < N% of price.
    "MIN_ORB_RANGE":  ("MIN_ORB_RANGE_PCT", 0.0),
    # Universe filter: keep top 50% of regime universe by VIX-beta rank.
    "VIX_BETA":       ("ENABLE_VIX_BETA_FILTER", False),
    # SPY-level same-day gap filter (skip days where SPY itself gapped).
    "SPY_GAP":        ("ENABLE_GAP_FILTER", False),
}

SLIPPAGE = 0.0010   # 0.10% per side, realistic for small-cap limit-order fills


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


def run_one(mode, data_tuple, equity, overrides: dict | None = None):
    """Run a single backtest with optional config overrides applied & restored.

    `overrides` maps config attribute name → value to set for the run.
    Original values are saved and restored after the run, so this is safe
    to call repeatedly without leaking state.
    """
    overrides = overrides or {}
    saved = {k: getattr(config, k) for k in overrides}
    try:
        for k, v in overrides.items():
            setattr(config, k, v)
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
        for k, v in saved.items():
            setattr(config, k, v)


def fmt_delta(value: float, baseline: float, fmt: str = "{:+.2f}") -> str:
    delta = value - baseline
    if abs(delta) < 1e-9:
        return "  ·  "
    return fmt.format(delta)


def main():
    parser = argparse.ArgumentParser(description="Filter-ablation backtest harness")
    parser.add_argument(
        "--windows",
        nargs="+",
        choices=[w[0] for w in ALL_WINDOWS],
        default=[w[0] for w in ALL_WINDOWS],
        help="Subset of windows (default: all 4)",
    )
    parser.add_argument(
        "--modes",
        nargs="+",
        choices=["plain_orb", "full_system"],
        default=["full_system"],
        help="Backtest modes (default: full_system, the live mode)",
    )
    parser.add_argument(
        "--filters",
        nargs="+",
        choices=list(FILTERS.keys()),
        default=list(FILTERS.keys()),
        help="Subset of filters to ablate (default: all)",
    )
    parser.add_argument(
        "--out",
        default=os.path.join(config.BACKTEST_RESULTS_DIR, "filter_ablation.log"),
        help="Output log path",
    )
    args = parser.parse_args()

    selected_windows = [w for w in ALL_WINDOWS if w[0] in args.windows]
    selected_modes = [StrategyMode[m.upper()] for m in args.modes]
    selected_filters = args.filters

    # Suppress noisy backtest internals
    logging.getLogger().setLevel(logging.WARNING)
    for noisy in ("backtest", "regime", "vix_factor", "vvix_filter", "data", "calendar_filter",
                  "sentiment", "sector_rotation", "performance"):
        logging.getLogger(noisy).setLevel(logging.WARNING)

    # Match the live config's retracement setting for fair comparison
    config.USE_FIB_RETRACEMENT_ENTRY = True

    equity = config.INITIAL_EQUITY
    os.makedirs(config.BACKTEST_RESULTS_DIR, exist_ok=True)

    logf = open(args.out, "w", buffering=1)
    def out(msg=""):
        print(msg)
        logf.write(msg + "\n")

    started = datetime.now()
    out("=" * 100)
    out("FILTER ABLATION — toggle each filter off, measure delta vs baseline")
    out(f"  windows  : {[w[0] for w in selected_windows]}")
    out(f"  modes    : {[m.value for m in selected_modes]}")
    out(f"  filters  : {selected_filters}")
    out(f"  slippage : {SLIPPAGE * 100:.2f}% per side")
    out(f"  equity   : ${equity:,.0f}")
    out(f"  started  : {started.isoformat()}")
    out(f"  total runs: {len(selected_windows) * len(selected_modes) * (len(selected_filters) + 1)}")
    out("=" * 100)

    # results[(mode, window, ablation_label)] = metrics dict
    # ablation_label is "BASELINE" or a filter name from FILTERS
    results: dict = {}

    for label, start, end in selected_windows:
        out(f"\n── Window {label}  ({start} → {end}) ──────────────────")
        out("  fetching data...")
        data_tuple = fetch_window(start, end)
        for mode in selected_modes:
            # Baseline first — all filters at current live defaults
            out(f"  [{mode.value}] baseline (all filters on)...")
            base = run_one(mode, data_tuple, equity, overrides=None)
            results[(mode, label, "BASELINE")] = base
            out(
                f"    → trades={base.get('total_trades', 0):4d}  "
                f"return={base.get('return_pct', 0):+.2f}%  "
                f"Sharpe={base.get('sharpe', 0):+.2f}"
            )
            # Each filter individually off
            for f in selected_filters:
                attr, off_val = FILTERS[f]
                out(f"  [{mode.value}] {f} OFF (config.{attr} = {off_val})...")
                m = run_one(mode, data_tuple, equity, overrides={attr: off_val})
                results[(mode, label, f)] = m
                out(
                    f"    → trades={m.get('total_trades', 0):4d}  "
                    f"return={m.get('return_pct', 0):+.2f}%  "
                    f"Sharpe={m.get('sharpe', 0):+.2f}  "
                    f"Δtrades={m.get('total_trades', 0) - base.get('total_trades', 0):+d}  "
                    f"Δreturn={m.get('return_pct', 0) - base.get('return_pct', 0):+.2f}pp"
                )

    # ── Summary table ────────────────────────────────────────────────
    out("\n" + "=" * 100)
    for mode in selected_modes:
        for label, _, _ in selected_windows:
            base = results.get((mode, label, "BASELINE"), {})
            base_trades = base.get("total_trades", 0)
            base_ret = base.get("return_pct", 0)
            base_sh = base.get("sharpe", 0)
            out(f"\n━━━ {mode.value.upper()} | Window {label} ━━━")
            out(f"  Baseline: trades={base_trades}, return={base_ret:+.2f}%, Sharpe={base_sh:+.2f}")
            out(f"  {'Filter OFF':<16} {'Trades':>7} {'ΔTrades':>9} {'Return':>9} {'ΔReturn':>10} {'Sharpe':>8} {'ΔSharpe':>9}  Verdict")
            out("-" * 100)
            for f in selected_filters:
                m = results.get((mode, label, f), {})
                trades = m.get("total_trades", 0)
                ret = m.get("return_pct", 0)
                sh = m.get("sharpe", 0)
                d_trades = trades - base_trades
                d_ret = ret - base_ret
                d_sh = sh - base_sh
                # Verdict: load-bearing if trade count moves more than 5% OR return moves more than 0.5pp
                trade_pct = (abs(d_trades) / base_trades * 100) if base_trades > 0 else 0
                if trade_pct < 1 and abs(d_ret) < 0.1:
                    verdict = "DECORATIVE"
                elif trade_pct >= 5 or abs(d_ret) >= 0.5:
                    verdict = "LOAD-BEARING"
                else:
                    verdict = "marginal"
                out(
                    f"  {f:<16} {trades:>7d} {fmt_delta(trades, base_trades, '{:+d}'):>9} "
                    f"{ret:>+8.2f}% {fmt_delta(ret, base_ret, '{:+.2f}pp'):>10} "
                    f"{sh:>+7.2f} {fmt_delta(sh, base_sh):>9}  {verdict}"
                )
            out("-" * 100)

    finished = datetime.now()
    out("\n" + "=" * 100)
    out(f"  Started:  {started}")
    out(f"  Finished: {finished}")
    out(f"  Runtime:  {finished - started}")
    out("=" * 100)
    logf.close()


if __name__ == "__main__":
    main()
