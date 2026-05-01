# Trading Strategy

## Mission
Beat SPY over the challenge window using volatility regime intelligence.
Stocks only — no options, ever. Paper trading until edge is proven.

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
5. Stop = lower of VWAP, ORB high −0.25%, or entry − 1.5×ATR
6. Take profit = 2R (2× risk distance)
7. Daily max loss 2% → halt all entries
8. Kill switch at 3% daily loss → stop everything
9. No entries after 3:30 PM ET
10. Close everything by 3:55 PM ET
11. Portfolio exposure cap: 50% equity

## Entry Checklist (Long ORB)
- Regime determined?
- Symbol in active universe?
- VVIX filter passed?
- Put/call sentiment allows entries?
- VIX beta rank: top 50%?
- ORB high broken?
- Price above VWAP?
- Volume >1.5× 20-bar average?
- ATR stop calculated and valid?
- Sizing respects vol-adjustment?
- Exposure cap respected?

## Short Entry Checklist (Regime B/C only)
- Regime is B or C?
- Symbol is in SHORT_UNIVERSE (high-VIX-beta names: QQQ, XLK, NVDA, AMD, TSLA, META, AMZN)?
- Symbol VIX beta > 0 (fragile in vol spikes)?
- VVIX filter passed?
- ORB low broken (price < ORB low)?
- Price below VWAP?
- Volume >1.5× 20-bar average?
- ATR-based stop ABOVE entry (max of VWAP, ORB low + buffer, entry + ATR×1.5)?
- Target = entry − 2R (below entry)?
- Same 0.5% base risk × regime size factor (B=0.5×, C=0.25×)?

## Gap Continuation Long (off by default — pending EOW review)
- Flag: `ENABLE_GAP_CONTINUATION` in config
- Regime A only
- Open price gaps >1.0% above prior close
- Last 2 bars close above the open (gap level held)
- Volume >2.0× avg (higher bar than ORB)
- Stop = lower of gap level or ATR stop; Target = 2R

## VIX Beta Factor
Rank symbols daily by rolling 60-day VIX beta.
- Regime A: prefer lowest VIX beta (momentum names)
- Regime B/C: prefer most negative VIX beta (defensive names)
Trade only top 50% of universe by regime-appropriate ranking.

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
