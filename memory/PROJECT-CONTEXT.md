# Project Context

## Overview
- **What:** VIX/VVIX Regime Alpha Bot — quantitative paper trading system
- **Starting capital:** $100,000 (paper)
- **Platform:** Alpaca paper trading
- **Strategy:** ORB + VWAP with volatility regime overlay
- **Goal:** Outperform SPY via regime-aware positioning

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
bash scripts/perplexity.sh "query" # market research
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
