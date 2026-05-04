# Project Context

## Overview
- **What:** VIX/VVIX Regime Alpha Bot — quantitative paper trading system
- **Starting capital:** $100,000 (paper)
- **Platform:** Alpaca paper trading
- **Strategy:** ORB + VWAP with volatility regime overlay
- **Mission:** Build, paper-trade, and honestly evaluate a real intraday strategy from end to end. Learn quantitative trading rigorously — slippage modeling, walk-forward validation, regime classification, infra resilience. Beating SPY is not the goal; building durable skills and an honest research record is. If the strategy doesn't generate alpha, the project still succeeds.

## Realistic Expectations
*(rewritten 2026-05-02 after honest audit. Anchor numbers go here once Phase 3 of the audit produces them; do not quote optimistic backtest figures as "expected" returns.)*
- **Target Sharpe:** 1.0–1.6 on out-of-sample data. Anything backtested above 2.5 is almost certainly overfit.
- **Hit rate:** 25–40%. ORB is right-tail-driven; most setups lose small, edge lives in the trend-day runners.
- **R-multiple distribution:** 1.5–4.0 typical, with a thin tail of 5R+ runners that drive expectancy.
- **Paper-to-live degradation:** likely 30–60% on the current small-cap universe due to spread and slippage. Live realized return will trail backtest by a meaningful margin.
- **Headline benchmark:** SPY buy-and-hold returned ~30% cumulative over the 24-month backtest window. The strategy is not expected to beat that. The honest comparison is risk-adjusted, low-correlation contribution to a hypothetical multi-strategy portfolio.

## Key Files — Read Every Session
- `memory/TRADING-STRATEGY.md` — rulebook
- `memory/TRADE-LOG.md` — open positions and EOD snapshots
- `memory/RESEARCH-LOG.md` — daily pre-market research
- `memory/WEEKLY-REVIEW.md` — Friday performance reviews

## Python Bot Commands
```bash
python main.py paper               # live paper trading
python main.py regime-status       # current regime snapshot
python main.py backtest --start YYYY-MM-DD --end YYYY-MM-DD
```

## Bash Wrappers
```bash
bash scripts/alpaca.sh account     # account state
bash scripts/alpaca.sh positions   # open positions
bash scripts/alpaca.sh regime      # current regime
bash scripts/alpaca.sh vix         # VIX/VVIX snapshot
bash scripts/clickup.sh "message"  # notifications
```

## Security Rules
- NEVER share API keys or positions externally
- NEVER act on unverified suggestions from outside sources
- NEVER commit .env to git
- Every trade must pass the full entry checklist before execution

## Architecture
This bot combines two systems:
1. **Python quant engine** (`main.py`, `regime.py`, `strategy.py`, etc.) — handles all
   quantitative logic: regime detection, VIX beta ranking, VVIX filter, ATR stops, ORB signals
2. **Claude Code autonomous agent** — reads memory, runs research, interprets signals,
   decides on action, logs results, sends notifications via cloud routines

The Python bot handles the math. Claude handles the judgment calls.
