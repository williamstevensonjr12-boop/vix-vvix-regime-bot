# Trading Strategy

## Mission
Build, paper-trade, and honestly evaluate a real intraday strategy from end to end.
Learn quantitative trading rigorously — slippage modeling, walk-forward validation,
regime classification, infra resilience. The goal is durable skill, not a return number.
Stocks only — no options, ever. Paper trading until edge is proven.

See `PROJECT-CONTEXT.md` → Realistic Expectations for target Sharpe / hit-rate / R-multiple bands.
Mission updated 2026-05-02 after honest audit; "beat SPY" framing dropped because the
backtest doesn't support it and the goal-misalignment was distorting which experiments
got prioritized.

## Capital & Constraints
- Platform: Alpaca (paper)
- Instruments: Stocks ONLY
- Bar size: 5-minute

## Regime Rules

### Regime A — Low Vol Trend (VIX <20, VVIX <100, SPY above 50d MA)
- Trade momentum universe (30-ticker small/mid-cap basket, switched 2026-04-29 after 4-period backtest validation):
  SOFI, PLTR, RIOT, UPST, HOOD, DKNG, AFRM, PLUG, RKLB, IONQ, RIVN, LCID, NIO,
  ENPH, RUN, FSLR, MRNA, CRSP, BEAM, TDOC, SMCI, AI, BBAI, MARA, COIN, MSTR,
  ROKU, OPEN, ASTS, ACHR
- Mega-cap basket (SPY, QQQ, AAPL, MSFT, NVDA, AMZN, META, TSLA, AMD) is preserved in config as MEGA_CAP_UNIVERSE — not active
- Source of truth = `config.py` MOMENTUM_UNIVERSE; this doc must mirror it
- Full position sizing (1.0× base)
- ORB + VWAP breakouts with volume confirmation

### Regime B — Elevated Vol (VIX 20-25)
- Trade fear-resilient universe: XLU, XLP, XLV, GLD, MSFT, JNJ, PG, COST
- Reduce sizing 50% (0.5× base)
- Avoid pure momentum breakouts
- **Short sleeve enabled** — ORB-breakdown shorts on high-VIX-beta names

### Regime C — Stress / Crisis (VIX >25 or VVIX >120)
- Rotate into defensive: XLU, XLP, XLV, GLD
- Reduce sizing 75% (0.25× base)
- Enable crisis alpha sleeve (long defensives)
- No new momentum breakout entries
- **Short sleeve enabled** — ORB-breakdown shorts on high-VIX-beta names

## VVIX Rules
- VVIX >110: reduce risk 50%
- VVIX >120: no new ORB entries
- VVIX +10% intraday: emergency risk-off, close all positions

## Core Trading Rules
1. NO OPTIONS — ever
2. Max 3 open positions simultaneously
3. Max 5 trades per day
4. Risk 0.5% equity per trade (vol-adjusted via ATR)
5. Stop = lower of VWAP, ORB high − 0.4% (STOP_BUFFER_PCT), or entry − 1.5×ATR
6. Take profit = 2R (2× risk distance) — *under audit; A/B planned vs 5R / trail-to-EOD*
7. Daily max loss 2% → halt all entries
8. Kill switch at 3% daily loss → stop everything
9. No entries after 3:30 PM ET
10. Close everything by 3:55 PM ET
11. Portfolio exposure cap: 50% equity

## Entry Checklist (Long ORB)
- Regime determined?
- Symbol in active universe?
- VVIX filter passed?
- ~~Put/call sentiment allows entries?~~ *(DEAD — yfinance dropped ^PCALL 2026-04-30; filter is silently neutral. Re-add if a real data source returns.)*
- SPY + IWM both above 50d MA (trend gate)?
- Gap alignment: ≥ +0.8% gap vs prior close (Regime A only)?
- VIX beta rank: top 50%?
- ORB high broken?
- Price above VWAP?
- Volume > 2.0× 20-bar average? *(NOTE: 20-bar baseline includes lunch chop bars, so this is effectively ~1.2–1.4× vs same-time-of-day. Phase 2 audit will fix the baseline.)*
- ATR expansion confirmed (`ENABLE_ATR_EXPANSION_FILTER=True`)?
- ORB range ≥ 0.3% of price (`MIN_ORB_RANGE_PCT`)?
- Calendar / earnings day clear?
- ATR stop calculated and valid?
- Sizing respects vol-adjustment?
- Exposure cap respected?

## Short Entry Checklist (Regime B/C only)
- Regime is B or C?
- Symbol is in SHORT_UNIVERSE (high-VIX-beta names: QQQ, XLK, NVDA, AMD, TSLA, META, AMZN)?
- Symbol VIX beta > 0 (fragile in vol spikes)?
- Gap alignment: ≤ −0.8% gap vs prior close (Regime A only — gap filter off in B/C)?
- VVIX filter passed?
- ORB low broken (price < ORB low)?
- Price below VWAP?
- Volume > 2.0× 20-bar average?
- ATR-based stop ABOVE entry (max of VWAP, ORB low + buffer, entry + ATR×1.5)?
- Target = entry − 2R (below entry)?
- Same 0.5% base risk × regime size factor (B=0.5×, C=0.25×)?

*Forward live-tested: 0 trades. Module is wired, regimes haven't materialized in live paper since launch.*

## Gap Continuation Long (off by default — pending EOW review)
- Flag: `ENABLE_GAP_CONTINUATION` in config (currently False)
- Regime A only
- Open price gaps ≥ 1.0% above prior close
- Last 2 bars close above the open (gap level held)
- Volume > 2.0× 20-bar avg (same baseline caveat as the long ORB path)
- Stop = lower of gap level or ATR stop; Target = 2R

## VIX Beta Factor
Rank symbols daily by rolling 60-day VIX beta.
- Regime A: prefer **most negative** VIX beta within the universe (highest fear-resilience score)
- Regime B/C: prefer most negative VIX beta (defensive names)
Trade only top 50% of universe by regime-appropriate ranking.

*Open audit question (2026-05-02):* the Regime A universe is explicitly **high-beta momentum**
names, but this filter then picks the most **fear-resilient** (least-momentum) names within it —
the two filters work against each other. Phase 2/3 will A/B test (a) inverting the filter to
prefer highest VIX-beta in Regime A, or (b) moving the rank from entry gate to position-size
weighting. Don't change the logic until tested.

## Sector Rotation Post-Spike
After VIX spike (>20pt rise in 3 days), rotate toward:
1. XLU (Utilities)
2. XLP (Staples)
3. XLV (Healthcare)
4. GLD (Gold)

## Risk Escalation Ladder
| Trigger | Action |
|---------|--------|
| VVIX >110 | 0.5× sizing |
| VVIX >120 | No new entries |
| VVIX +10% intraday | Emergency risk-off |
| Daily loss >2% | Halt entries |
| Daily loss >3% | Kill switch |
| VIX >25 | Force Regime C |
