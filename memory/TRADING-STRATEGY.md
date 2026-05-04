# Trading Strategy

## Mission

Build, paper-trade, and honestly evaluate a real intraday strategy from end to end.
Learn quantitative trading rigorously — slippage modeling, structured entries, infra
resilience, honest post-trade review. The goal is durable skill, not a return number.
Stocks only — no options, ever. Paper trading until edge is proven.

**2026-05-02 audit** retired the regime-aware ORB strategy after 4-window backtest
evidence showed it was unprofitable in every tested universe.

**2026-05-03 strategy swap** to Cameron VWAP-Bounce (Setup B). Rationale: previous
strategy added complexity (regime detection, sentiment, sector rotation, VIX-beta
filter, gap-alignment, retracement entry) without edge. The Cameron framework is
deliberately simpler and well-documented. Live with zero backtest validation —
Path 1 (learn empirically). Future session will run audit panel to validate.

## Capital & Constraints

- Platform: Alpaca (paper)
- Instruments: Stocks ONLY — no options, ever
- Bar size: 5-minute
- Direction: long AND short (mirror entries)

## Strategy — Cameron VWAP-Bounce (Setup B only)

No Setup A breakout. No Setup C micro-pullback. Just VWAP-Bounce:

**Long entry triggers when ALL of:**
1. close > VWAP (above the line)
2. close > 200 EMA (trend regime filter)
3. 9 EMA > 20 EMA (short-term trend confirmation)
4. Within last 3 bars, at least one bar's low touched VWAP within 0.15% (pullback signal)
5. Current bar close > prior bar close (bounce signal)
6. Relative volume ≥ 1.5× of 20-bar average (volume confirmation)

**Short entry:** full mirror (close < VWAP, close < 200 EMA, 9 < 20, recent high
touched VWAP from below, current bar close < prior close, rvol ≥ 1.5×).

**Stop:** min(prior 5 bar lows) for long, max(prior 5 bar highs) for short.

**Stop guardrail:** skip the trade if stop distance > 1.5 × ATR (chop conditions
where the structural stop is too far for a 2R target to make sense).

**Target:** entry ± TAKE_PROFIT_R × risk_per_share (default 2R).

**Per-trade risk:** 0.75% of account equity (`RISK_PER_TRADE_PCT = 0.0075`).
No regime size factor, no VVIX size factor — single fixed risk %.

## Universe — 8 mega-caps

`config.MOMENTUM_UNIVERSE` (source of truth):

```
SPY, QQQ, AAPL, MSFT, NVDA, GOOGL, AMZN, META
```

Selection rationale:
- TSLA / AMD excluded — mega-cap by market cap but small-cap volatility, generates
  setup-shaped traps.
- COIN / MSTR / PLTR / MARA / etc. excluded — wicks too wide for the structural
  5-bar-low stop logic.
- Mega-caps trend cleanly, fill instantly, VWAP/EMA levels actually hold because of
  institutional volume.

## Hard Rules (non-negotiable)

1. NO OPTIONS — ever
2. Max 3 open positions simultaneously (`MAX_OPEN_POSITIONS`)
3. Max 5 trades per day (`MAX_TRADES_PER_DAY`)
4. Risk 0.75% equity per trade (`RISK_PER_TRADE_PCT`)
5. Stop = min(prior 5 bar lows) for long, max for short. Skip if stop > 1.5 × ATR.
6. Take profit = 2R (entry ± 2 × risk_per_share)
7. Daily max loss 2% (`DAILY_MAX_LOSS_PCT`) → halt all entries for the day
8. Kill switch at 3% daily loss (`KILL_SWITCH_LOSS_PCT`) → stop everything
9. No entries after 3:30 PM ET (`LAST_ENTRY_TIME`)
10. Close everything by 3:55 PM ET (`CLOSE_ALL_TIME`)
11. Portfolio exposure cap: 50% of equity (`PORTFOLIO_EXPOSURE_CAP`)

## Entry Checklist (long, mirror for short)

The bot's `strategy.check_entry_signal` enforces these. Listed for review:

- Symbol in `MOMENTUM_UNIVERSE`?
- Not currently in open_positions?
- Total open positions < 3?
- Trades-today < 5?
- Not within an earnings-day window (`calendar_filter` check)?
- Calendar high-impact day clear (FOMC, CPI, etc.)?
- Lunch filter passes (off by default; flip if backtest shows lunch trades dilutive)?
- Daily P&L not breaching -2% halt or -3% kill switch?
- Bar count ≥ `MIN_BARS_FOR_SIGNAL` (5)?
- close > VWAP?
- close > 200 EMA?
- 9 EMA > 20 EMA?
- Within last 3 bars, at least one bar low touched VWAP within 0.15%?
- Current bar close > prior bar close?
- Relative volume ≥ 1.5× of 20-bar avg?
- Structural stop = min(prior 5 bar lows) > 0?
- Stop distance ≤ 1.5 × ATR (chop guardrail)?
- Position sizing returns qty > 0?
- Adding this position keeps total exposure under 50% cap?
- PDT constraints OK ($25K equity floor + $500 buffer)?

## Risk Escalation Ladder

| Trigger | Action |
|---------|--------|
| Daily loss > 2% (`DAILY_MAX_LOSS_PCT`) | Halt new entries for the day |
| Daily loss > 3% (`KILL_SWITCH_LOSS_PCT`) | Kill switch — no further trading until manual reset |
| Bot wrapper crash | `run_bot.sh` auto-restarts the python child after 30s |
| Network timeout / Alpaca 5xx | `net_utils.with_retry` retries 4× with exponential backoff |
| Earnings prefetch failure | Calendar gate fails open per symbol with WARNING log; trade allowed but logged |

## What This Strategy Deliberately Does NOT Have

The 2026-05-03 swap removed (and these are NOT coming back without backtest evidence):

- **No regime detection** — no Regime A/B/C dispatch, no VIX/VVIX thresholds. Cameron
  framework runs the same rules in any market vol environment. The 200 EMA filter is
  the only "regime" signal.
- **No sentiment filter** — put/call ratio data is dead and the prior filter was
  silently no-op anyway.
- **No VIX-beta ranking** — fear-resilience filter was decorative on the old universe;
  irrelevant on mega-caps where betas cluster.
- **No sector rotation** — single static universe, no rotation logic.
- **No gap-alignment requirement** — entries don't depend on overnight gap direction.
- **No ORB / opening-range breakout** — entries can fire any time after 5 bars print.
- **No retracement entry path** — the previous strategy had a flag for this but it
  was a phantom feature (only in backtest.py, never wired into live).
- **No short-sleeve regime gating** — Cameron longs and shorts use the same universe
  and the same entry mechanics, just mirrored.
- **No market-neutral overlay** — no Regime-C-driven long/short defensive sleeve.

## Methodology Rule (Carried Forward)

**Never change live trading-bot behavior on qualitative argument; require multi-window
backtest evidence.**

This swap to Cameron VWAP-Bounce went live with zero backtest evidence — Preston's
deliberate Path 1 choice after the prior strategy's audit retirement. Treat that as a
**one-time exception**, not a precedent. Future parameter changes (CAMERON_VOLUME_MULTIPLIER,
VWAP_PULLBACK_TOLERANCE_PCT, ATR_GUARDRAIL_MULT, RISK_PER_TRADE_PCT, etc.) require:

1. The backtest engine repointed to VWAP-Bounce (deferred Phase 5)
2. Multi-window evidence (4 windows: 2023H1, 2023H2, 2024H1, 2024H2)
3. Effect size > noise floor (≥ 1pp Σ-return change or ≥ 0.3 Sharpe change)

Without that, no live changes. Validate forward via paper P&L over weeks until backtest
infrastructure is restored.

---

*Source of truth for parameter values: `config.py` in the repo root. This document
describes intent and discipline; if a number drifts between this file and config.py,
**config.py wins** and this file should be updated to match.*
