# VIX / VVIX Regime Alpha Bot

> **⚠️ PAPER TRADING ONLY — NOT FINANCIAL ADVICE — DO NOT USE WITH REAL MONEY**

A production-quality quantitative trading system that combines a **Python regime engine** with a **Claude Code autonomous agent** (based on the Nate Herk Opus 4.7 Setup Guide methodology).

---

## What It Does

The bot detects volatility regimes using VIX, VVIX, VIX term structure, put/call ratio, and SPY trend — then rotates its trading universe, adjusts position sizing, and applies ORB + VWAP execution accordingly.

**Three regimes:**

| Regime | VIX Level | Universe | Sizing | Strategy |
|--------|-----------|----------|--------|----------|
| A — Low Vol Trend | <20 | SPY, QQQ, AAPL, MSFT, NVDA, AMZN, META, TSLA, AMD | 1.0× | Momentum ORB breakouts |
| B — Elevated Vol | 20–25 | XLU, XLP, XLV, GLD, MSFT, JNJ, PG | 0.5× | Fear-resilient names only |
| C — Stress / Crisis | >25 or VVIX>120 | XLU, XLP, XLV, GLD | 0.25× | Defensive rotation + crisis alpha |

**VVIX rules:** >110 = reduce risk, >120 = no new entries, +10% intraday = emergency close all.

---

## Architecture

Two layers working together:

```
Python Quant Engine                Claude Code Autonomous Agent
──────────────────────             ───────────────────────────
config.py          regime.py       CLAUDE.md        (auto-loaded)
data.py            vix_factor.py   routines/        (cloud cron jobs)
indicators.py      vvix_filter.py  memory/          (persistent state in Git)
strategy.py        sentiment.py    scripts/         (bash API wrappers)
risk.py            sector_rotation.py
broker.py          market_neutral.py
backtest.py        performance.py
```

---

## Project Structure

```
VIX_VVIX_Regime_Alpha_Bot/
├── CLAUDE.md              — Agent rulebook (auto-loaded every session)
├── env.template           — Template for .env (never commit actual .env)
├── .gitignore
├── requirements.txt
│
├── main.py                — CLI: paper | backtest | regime-status
├── config.py              — All settings
├── data.py                — Alpaca + yfinance data fetcher
├── regime.py              — Core VIX/VVIX regime engine
├── vix_factor.py          — VIX beta rolling factor + ranker
├── vvix_filter.py         — VVIX false-breakout and risk filter
├── sentiment.py           — Put/call ratio sentiment overlay
├── sector_rotation.py     — Post-spike sector rotation scoring
├── market_neutral.py      — Long/short crisis alpha sleeve
├── indicators.py          — VWAP, ORB, ATR, avg volume
├── strategy.py            — Regime-aware ORB + VWAP signal generator
├── risk.py                — Vol-adjusted sizing, ATR stops, kill switch
├── broker.py              — Alpaca paper trading wrapper
├── journal.py             — CSV trade logging
├── performance.py         — Full metrics: Sharpe, Sortino, Monte Carlo, etc.
├── backtest.py            — 3-strategy comparative backtest
│
├── scripts/
│   ├── alpaca.sh          — All Alpaca API calls (account, orders, positions)
│   └── clickup.sh         — ClickUp chat notifications
│
├── routines/              — Cloud routine prompts (paste into Claude Code cron)
│   ├── pre-market.md
│   ├── market-open.md
│   ├── midday.md
│   ├── daily-summary.md
│   └── weekly-review.md
│
└── memory/                — Persistent agent state (committed to Git)
    ├── TRADING-STRATEGY.md
    ├── TRADE-LOG.md
    ├── RESEARCH-LOG.md
    ├── WEEKLY-REVIEW.md
    └── PROJECT-CONTEXT.md
```

---

## Setup

### 1. Prerequisites

- Python 3.10+
- Alpaca paper trading account: https://app.alpaca.markets
- (Optional) ClickUp account for daily notifications

### 2. Install dependencies

```bash
cd VIX_VVIX_Regime_Alpha_Bot
python -m venv .venv
source .venv/bin/activate       # Windows: .venv\Scripts\activate
pip install -r requirements.txt
```

### 3. Configure credentials

```bash
cp env.template .env
```

Edit `.env` with your **paper** Alpaca keys:
```
ALPACA_API_KEY=PK...
ALPACA_SECRET_KEY=...
PAPER_TRADING=true
```

### 4. Smoke test

```bash
# Check current regime
python main.py regime-status

# Test the Alpaca connection
bash scripts/alpaca.sh account
```

---

## Running a Backtest

Compare all 3 strategies (plain ORB / ORB+VIX beta / full system) on the same data:

```bash
python main.py backtest --start 2024-01-02 --end 2024-06-28
```

Backtest output:
- Side-by-side strategy comparison table
- Full performance report for each strategy (Sharpe, Sortino, drawdown, crisis performance)
- Monte Carlo simulation (2,000 runs)
- Individual `trades_<strategy>.csv` files in `backtest_results/`

**Backtest assumptions:** 0.03% slippage per trade, no commissions, no lookahead bias, one entry per symbol per day.

---

## Running Paper Trading

```bash
python main.py paper
```

The bot will:
1. Download VIX/VVIX/VIX3M data and compute the current regime
2. Fit rolling VIX betas for all symbols and rank by fear resilience
3. Wait for market open, then scan every 60 seconds
4. Apply VVIX filter, sentiment filter, and VIX beta ranking
5. Submit bracket orders (stop loss + take profit) via Alpaca
6. Monitor regime intraday — close positions if regime shifts to C
7. Force-close everything at 3:55 PM ET
8. Log all trades to `trades.csv` and `performance.csv`

---

## Cloud Routines (Autonomous Agent Mode)

To run this as a fully autonomous agent using Claude Code cloud routines:

### Five cron jobs (America/New_York)

| Routine | Schedule | Action |
|---------|----------|--------|
| Pre-market | `0 6 * * 1-5` | Research, regime assessment, trade ideas |
| Market-open | `35 9 * * 1-5` | Execute planned trades |
| Midday | `0 12 * * 1-5` | Scan positions, regime change check |
| Daily-summary | `0 16 * * 1-5` | EOD snapshot + ClickUp notification |
| Weekly-review | `30 16 * * 5` | Weekly stats, grade, strategy update |

### Setup checklist (from Nate Herk's guide)

1. ☐ Create private GitHub repo and push this project
2. ☐ Add `.env` to `.gitignore` ✓ (already done)
3. ☐ Install Claude GitHub App on your repo
4. ☐ Create cloud routine in Claude Code UI
5. ☐ Select your repo, branch: `main`
6. ☐ **Enable "Allow unrestricted branch pushes"** (critical — without this, git push silently fails)
7. ☐ Set env vars on the routine (NOT in a .env file): all vars from `env.template`
8. ☐ Paste the prompt from `routines/<name>.md` verbatim into the routine
9. ☐ Hit "Run now" once to verify before scheduling
10. ☐ Repeat for all 5 routines

---

## Performance Metrics

The backtest and paper trading sessions produce:

| Metric | Description |
|--------|-------------|
| CAGR | Compound annual growth rate |
| Sharpe | Annualized (trade-level R multiples) |
| Sortino | Downside-deviation adjusted return |
| Max Drawdown | Peak-to-trough equity loss |
| Calmar | CAGR / Max Drawdown |
| Win Rate | % of closed trades profitable |
| Profit Factor | Gross wins / Gross losses |
| Beta to SPY | Correlation with market |
| Alpha | Jensen's alpha vs SPY |
| VaR / CVaR | 95% tail risk |
| Crisis Performance | Returns during VIX >30 periods |
| Monte Carlo | 2,000-run bootstrap equity distribution |

---

## Safety Checks

| Check | Where |
|-------|-------|
| `PAPER_TRADING=true` required | `config.py` (raises at import) |
| `paper=True` hardcoded | `broker.py` (TradingClient constructor) |
| Kill switch at 3% daily loss | `risk.py` (stops all trading) |
| Portfolio exposure cap 50% | `risk.py` (per-order check) |
| VVIX >120 blocks all entries | `vvix_filter.py` |
| VVIX +10% intraday = close all | `vvix_filter.py` |
| Regime C = no momentum trades | `strategy.py` universe check |

---

## Disclaimer

For educational and research purposes only. Past performance in backtests does not guarantee future results. This is not financial advice. Trading involves substantial risk of loss.
