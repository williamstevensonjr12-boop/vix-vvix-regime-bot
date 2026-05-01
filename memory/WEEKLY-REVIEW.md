# Weekly Review

Friday reviews appended here. Template below.

---

## Template — Week ending YYYY-MM-DD

### Stats

| Metric | Value |
|--------|-------|
| Starting portfolio | $X |
| Ending portfolio | $X |
| Week return | ±$X (±X%) |
| SPY week return | ±X% |
| Bot vs SPY | ±X% |
| Dominant regime | A/B/C |
| Trades taken | N (W:X / L:Y / open:Z) |
| Win rate | X% |
| Best trade | SYM +X% (R=X.X) |
| Worst trade | SYM -X% |
| Profit factor | X.XX |
| Avg VIX this week | XX.X |
| Regime transitions | X→Y on date |

### Closed Trades

| Date | Symbol | Entry | Exit | P&L | R | Regime | Reason |
|------|--------|-------|------|-----|---|--------|--------|

### Open Positions at Week End

| Symbol | Entry | Close | Unrealized | Stop | Regime |
|--------|-------|-------|------------|------|--------|

### What Worked
-

### What Didn't Work
-

### Key Lessons
-

### Regime Notes
- Was the regime engine correct this week?
- Any false signals from VVIX or put/call?
- Did VIX beta ranking add value?

### Adjustments for Next Week
-

### Overall Grade: X

---

## Week ending 2026-05-01

### Stats

| Metric | Value |
|--------|-------|
| Starting portfolio | $100,000.00 |
| Ending portfolio | $99,621.24 |
| Week return | -$378.76 (-0.38%) |
| SPY week return | +0.94% |
| Bot vs SPY | -1.32% |
| Dominant regime | A_LOW_VOL_TREND (5/5 sessions) |
| Trades taken | 7 (W:3 / L:4 / open:0) |
| Win rate | 42.9% |
| Best trade | KO +$118.37 (R=+0.34) |
| Worst trade | BP (1st entry) -$389.60 (R=-0.78) |
| Profit factor | 0.29 |
| Avg VIX this week | ~18.3 |
| Regime transitions | NONE — Regime A all week |

### Closed Trades

| Date | Symbol | Entry | Exit | P&L | R | Regime | Reason |
|------|--------|-------|------|-----|---|--------|--------|
| 04-28 | BP (1st) | $46.78 | ~$46.45 | -$389.60 | -0.78R | A | Manual exit pre-stop; VWAP broken, momentum reversed |
| 04-28 | KO | $79.96 | ~$80.15 | +$118.37 | +0.34R | A | Trailing stop hit on earnings/raised-guide momentum |
| 04-28 | BP (re-entry) | $46.76 | $46.77 | +$10.65 | +0.04R | A | Manual scratch close on chop concern |
| 04-28 | NVDA | $210.09 | $209.90 | -$38.38 | -0.07R | A | Stop hit; SPY rolled over into close |
| 04-29 | GLD | $418.84 | $417.89 | -$56.13 | -0.58R | A | Manual pre-FOMC scratch; yields up, gold faded |
| 04-30 | RUN | $12.68 | $12.73 | +$16.60 | +0.12R | A | Bot ORB-H; EOD close-all 15:55 ET |
| 04-30 | RKLB | $82.50 | $82.27 | -$13.35 | -0.11R | A | Bot ORB-H; EOD close-all 15:55 ET |

### Open Positions at Week End

NONE — flat into the weekend, 0 open orders.

### What Worked
- KO earnings + raised-guide thesis: only structural win, clean trailing-stop exit
- Risk discipline: worst trade -0.78R, no daily halt or kill switch hit, drawdown -0.38% all week
- Bot infrastructure validated post-universe-switch: ORB-H signals fired on 04-30 (RUN, RKLB) with bracket orders working as designed
- No overnight exposure, no order cleanup needed any morning

### What Didn't Work
- Discretionary BP on Iran/oil catalyst (no ORB+VWAP confirmation) = single biggest loss of the week (-$389.60)
- FOMC-day GLD discretionary long: pre-Fed yield drift killed gold, ate -$56
- 5 of 7 trades were discretionary overrides; only 2 systematic bot fills
- New small/mid-cap basket producing tight R-multiples (RUN +0.12R, RKLB -0.11R) — afternoon ORB entries don't have time to mature before 15:55 EOD close-all

### Key Lessons
- Discretionary entries without ORB+VWAP+volume confirmation carry asymmetric tail risk (BP 1st entry was the textbook example)
- FOMC days: stay flat unless setup is overwhelming. Pre-Fed yield drift compresses everything
- Late-day bot fires (after ~14:30 ET) get truncated by EOD close-all and can't realize 2R targets — entry-timing question for next week
- Tight win/loss R-multiples in the new universe mean win rate must climb above 50% to break even; current 42.9% is below the structural threshold

### Regime Notes
- Regime engine was correct all week — VIX 17-19, VVIX 91-96, term structure healthy, P/C neutral
- Zero false VVIX signals; never crossed 100, never triggered risk-off
- VIX beta ranking value unclear at this sample size (only 7 trades, only 2 systematic)
- No transitions to test the engine on B/C this week

### Adjustments for Next Week
- Hard rule: no discretionary entry without ORB-H + above VWAP + volume >1.5×
- No FOMC-day discretionary trades (next FOMC: check calendar before Monday plan)
- Prioritize morning bot fires (10:00-12:00 ET window) — afternoon ORBs have insufficient runway before EOD close
- Goal: 5+ systematic bot fills next week to start building edge sample
- Keep universe; one week of data isn't enough to second-guess the basket switch

### Overall Grade: C-

Negative week, underperformed SPY by 1.32%, profit factor 0.29. Saved by tight risk control (no day breached 0.4%) and clean infrastructure. Diagnosis: bot too quiet, discretionary too loose. Cleanest path to a green week is reducing the discretionary count and waiting for systematic confirmation.
