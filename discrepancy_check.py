"""
discrepancy_check.py — Reproduce session 5's headline number for 2023H1.

Tests whether USE_FIB_RETRACEMENT_REGIME_GATE = False is the missing flag.
Session 5 reported: 2023H1 Plain ORB +10.64% / Sharpe 2.41 with the small-cap
universe and retracement entry. Tonight's run produced +8.25% with the same
config but USE_FIB_RETRACEMENT_REGIME_GATE = True.

This script runs 2023H1 only, with the gate flipped OFF, at the original 0.03%
slippage. If we land near +10.64%, the gate is the explanation.
"""
from __future__ import annotations
import logging

import config
import data as mkt_data
from backtest import BacktestConfig, BacktestEngine, StrategyMode

START, END = "2023-01-03", "2023-06-30"
EQUITY = config.INITIAL_EQUITY


def main():
    logging.getLogger().setLevel(logging.WARNING)
    for noisy in ("backtest", "regime", "vix_factor", "vvix_filter", "data",
                  "calendar_filter", "sentiment", "sector_rotation", "performance"):
        logging.getLogger(noisy).setLevel(logging.WARNING)

    # Match session 5 Run 8 hypothesis: retracement on, gate OFF, OLD thresholds.
    config.USE_FIB_RETRACEMENT_ENTRY = True
    config.USE_FIB_RETRACEMENT_REGIME_GATE = False
    config.STOP_BUFFER_PCT = 0.0025          # was 0.004
    config.VOLUME_MULTIPLIER = 1.5           # was 2.0
    config.GAP_ALIGNMENT_THRESHOLD = 0.005   # was 0.008

    print(f"Config: retracement ON, regime gate OFF")
    print(f"  STOP_BUFFER_PCT=0.0025 (was 0.004)")
    print(f"  VOLUME_MULTIPLIER=1.5 (was 2.0)")
    print(f"  GAP_ALIGNMENT_THRESHOLD=0.005 (was 0.008)")
    print(f"Window: {START} → {END}, slippage={config.SLIPPAGE_PCT*100:.2f}%, equity=${EQUITY:,.0f}\n")

    print("Downloading data...")
    data_client = mkt_data.get_data_client()
    all_symbols = list(dict.fromkeys(config.ALL_SYMBOLS + ["SPY"]))
    bars = mkt_data.get_multiple_symbols_bars(data_client, all_symbols, START, END)
    vol = mkt_data.get_vix_history(START, END)
    spy = mkt_data.get_spy_daily(START, END)
    pc = mkt_data.get_put_call_history(START, END)
    dr = {sym: mkt_data.get_symbol_daily_returns(data_client, sym, START, END)
          for sym in config.ALL_SYMBOLS}

    print("\n=== Plain ORB (gate OFF) ===")
    cfg = BacktestConfig(mode=StrategyMode.PLAIN_ORB, initial_equity=EQUITY,
                         slippage_pct=config.SLIPPAGE_PCT)
    m_plain = BacktestEngine(cfg).run(bars, vol, spy, pc, dr) or {}

    print("\n=== Full System (gate OFF) ===")
    cfg = BacktestConfig(mode=StrategyMode.FULL_SYSTEM, initial_equity=EQUITY,
                         slippage_pct=config.SLIPPAGE_PCT)
    m_full = BacktestEngine(cfg).run(bars, vol, spy, pc, dr) or {}

    print("\n" + "=" * 80)
    print(f"{'2023H1 RESULT':<30}{'Plain ORB':<20}{'Full System':<20}")
    print("-" * 80)
    print(f"{'Tonight (gate ON, new)':<30}{'+8.25% / 2.84':<20}{'+5.48% / 3.15':<20}")
    print(f"{'Gate OFF, new thresholds':<30}{'+8.56% / 3.28':<20}{'+5.33% / 3.55':<20}")

    pp = m_plain.get("total_pnl", 0)/EQUITY*100
    fp = m_full.get("total_pnl", 0)/EQUITY*100
    ps = m_plain.get("sharpe", 0)
    fs = m_full.get("sharpe", 0)
    pt = m_plain.get("total_trades", 0)
    ft = m_full.get("total_trades", 0)
    print(f"{'Gate OFF + OLD thresholds':<30}{f'{pp:+.2f}% / {ps:.2f}':<20}{f'{fp:+.2f}% / {fs:.2f}':<20}")
    print(f"{'  trade counts':<30}{f'{pt} trades':<20}{f'{ft} trades':<20}")
    print(f"{'Session 5 reported':<30}{'+10.64% / 2.41':<20}{'+8.30% / 3.35':<20}")
    print("=" * 80)


if __name__ == "__main__":
    main()
