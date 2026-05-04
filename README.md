# Cameron VWAP-Bounce Trading Bot

> **⚠️ PAPER TRADING ONLY — NOT FINANCIAL ADVICE — DO NOT USE WITH REAL MONEY**

A focused intraday trading bot that fires a single setup — Cameron's VWAP-Bounce
(Setup B only) — on 1-minute bars across 8 mega-cap names. The bot is autonomous:
a Python wrapper handles entries, brackets, EOD close, and kill-switch logic; a
small set of Claude Code cloud routines provide pre-market context, midday
verification, and EOD reporting.

**Strategy in one paragraph.** Long entry: close > VWAP, close > 200 EMA,
9 EMA > 20 EMA, recent low touched VWAP within 0.15% in the last 3 bars,
current bar close > prior close, relative volume ≥ 1.5×. Short entry is the
full mirror. Stop = min(prior 5 bar lows) for long, max for short. Skip if
stop distance exceeds 1.5 × ATR (chop guardrail). Target = 2R. Risk = 0.75%
of equity per trade. There is **no regime engine, no VIX/VVIX filtering, no
ORB, no gap-alignment, and no sector rotation** — the framework is intentionally
simple.

**Universe:** SPY, QQQ, AAPL, MSFT, NVDA, GOOGL, AMZN, META.

---

## Architecture

Two layers:

```
Python Bot                          Claude Code Cloud Routines
──────────                          ──────────────────────────
config.py        (parameters)       CLAUDE.md       (auto-loaded agent rulebook)
indicators.py    (VWAP, EMA, ATR,   routines/       (5 scheduled prompts)
                  relative volume)  memory/         (state, committed to Git)
strategy.py      (entry signal)     scripts/        (bash API wrappers)
risk.py          (sizing, stops,
                  kill switch)
broker.py        (Alpaca paper)
journal.py       (CSV trade log)
performance.py   (metrics)
backtest.py      (currently STUBBED — Phase 5 rewire pending)
main.py          (CLI: paper | dashboard | tracker)
```

The `main.py paper` loop wraps everything: pulls bars, runs the entry checklist
in `strategy.py`, sizes via `risk.py`, submits bracket orders via `broker.py`,
monitors fills, force-closes at 15:55 ET, and writes `trades.csv` /
`performance.csv` for the dashboard.

---

## Setup

### 1. Prerequisites

- Python 3.10+
- Alpaca paper trading account: https://app.alpaca.markets
- (Optional) ntfy.sh topic for push notifications

### 2. Install dependencies

```bash
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
ANTHROPIC_API_KEY=...           # for the pre-market AI brief in research.py
NTFY_TOPIC=...                  # for push notifications (optional)
```

### 4. Smoke test

```bash
bash scripts/alpaca.sh account     # confirm Alpaca connection
python main.py paper --dry-run     # if implemented; otherwise run pytest
pytest tests/                      # 17/17 should pass
```

---

## Running Paper Trading

```bash
nohup bash run_bot.sh > /tmp/bot_output_$(date +%Y%m%d).log 2>&1 &
```

`run_bot.sh` is the auto-restart wrapper: it relaunches the Python child
on crashes or wifi drops. The bot will:

1. Connect to Alpaca paper, log starting equity.
2. Wait for market open (09:30 ET).
3. From 09:30 to 15:30 ET, scan the 8-name universe every 60 seconds for
   VWAP-Bounce entries (long + short, mirror conditions per symbol).
4. On entry: submit a bracket order (stop + 2R target) and push an `entry`
   ntfy notification.
5. Force-close all positions at 15:55 ET (no overnight holds).
6. Log every fill to `trades.csv`; refresh `performance.csv` daily.

**To stop:** `pkill -f run_bot.sh` (kill wrapper) **then**
`pkill -f "main.py paper"` (kill child). Wrapper-first prevents auto-relaunch.

---

## Hard Rules (enforced in `risk.py` and `strategy.py`)

- **No options, ever.**
- Max **3** open positions at once.
- Max **5** trades per day.
- Risk per trade: **0.75%** of equity.
- Daily max loss: **2%** → halt entries for the day.
- Kill switch at **3%** daily loss → close all positions, no further trading.
- No new entries after **15:30 ET**.
- Force-close everything at **15:55 ET**.
- Portfolio exposure cap: **50%** of equity.

Source of truth for parameter values is `config.py`. If anything in `CLAUDE.md`
or this README drifts from `config.py`, **`config.py` wins**.

---

## Cloud Routines (Autonomous Agent Mode)

Five Claude Code scheduled tasks, plus the live wrapper bot. The routines run
in the cloud / via the Claude Code app's local scheduler and read/write
memory files in `memory/`, then commit and push to keep state on origin.

| Routine | Schedule (ET) | Action |
|---|---|---|
| `pre-market` | 06:00 weekdays | Account snapshot, macro headlines via Perplexity, append RESEARCH-LOG entry |
| `market-open` | 09:35 weekdays | Verify wrapper + child PIDs alive, hard-gate snapshot. No order placement. |
| `midday` | 12:00 weekdays | Drawdown / kill-switch verification, position quality scan. Manual close-all only if kill switch should have fired but didn't. |
| `daily-summary` | 16:00 weekdays | EOD flat verification, day metrics, mandatory ntfy push. |
| `weekly-review` | 16:30 Fridays | Week stats, letter grade, conditional TRADING-STRATEGY.md update on 2+ weeks of evidence. |

The active prompt files live at `~/.claude/scheduled-tasks/<routine>/SKILL.md`
(local to your machine). The repo's `routines/*.md` are documentation/templates;
they may drift slightly from the live SKILL.md. The SKILL.md is the source of
truth for what actually runs.

---

## Performance Metrics

Stored in `trades.csv` + `performance.csv` and surfaced via:

```bash
python main.py tracker --days 30   # rolling-window stats
python main.py dashboard           # HTML dashboard
```

Tracked: day P&L, day return, trade count, win rate, profit factor, average
win/loss, halt and kill-switch event days. The dashboard renders cumulative
equity, per-symbol P&L breakdown, and recent fills.

Backtest validation is **deferred** — `backtest.py` is currently stubbed
(Phase 5 of the strategy swap will rewire it for Cameron). Until that ships,
the bot is trading live without backtest evidence on the new strategy.

---

## Safety Checks

| Check | Where |
|---|---|
| `PAPER_TRADING=true` required | `config.py` (raises at import) |
| `paper=True` hardcoded | `broker.py` (TradingClient constructor) |
| Daily-halt at -2% | `risk.py` (blocks new entries) |
| Kill switch at -3% | `risk.py` (closes all, blocks all) |
| Portfolio exposure cap 50% | `risk.py` (per-order check) |
| Earnings-day block | `calendar_filter.py` (per-symbol) |
| FOMC / CPI / NFP entry block | `calendar_feed.py` (tier-1 macro) |
| EOD force-close at 15:55 ET | `main.py` |

---

## Disclaimer

For educational and research purposes only. Past performance in backtests does
not guarantee future results. This is not financial advice. Trading involves
substantial risk of loss.
