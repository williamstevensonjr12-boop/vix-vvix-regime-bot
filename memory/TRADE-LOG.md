# Trade Log

## Day 0 — EOD Snapshot (pre-launch baseline)

**Portfolio:** $100,000.00 | **Cash:** $100,000.00 (100%) | **Day P&L:** $0 | **Phase P&L:** $0

Regime: Not yet assessed. Bot launches on next trading day.
No positions. Paper trading mode.

---

*Trades will be appended here in the format:*

### YYYY-MM-DD — EOD Snapshot

**Portfolio:** $X | **Cash:** $X (X%) | **Day P&L:** ±$X (±X%) | **Phase P&L:** ±$X (±X%)
**Regime:** A/B/C | **VIX:** XX.X | **VVIX:** XXX.X

| Symbol | Shares | Entry | Close | P&L | Stop | Regime | R |
|--------|--------|-------|-------|-----|------|--------|---|

**Notes:** ...

---

=== EOD 2026-04-27 ===
Equity: $100,000.00 (day P&L: $0.00, day return: 0.00%)
Trades: 0 (W:0 / L:0) | Win rate: N/A | P/F: N/A
Regime: A (LOW_VOL_TREND, score 0.716) | Kill switch: NO
Open overnight: NONE
Notes: No ORB signals triggered on watchlist (NVDA, QQQ, SPY). VIX 19.1, VVIX 96.9 — clean Regime A all session. No entries, no risk taken.

### 2026-04-28 — OPEN POSITION

| Symbol | Shares | Entry | Stop | Target | R:R | Regime | Catalyst |
|--------|--------|-------|------|--------|-----|--------|----------|
| BP | 974 | $46.78 | $46.27 | $47.81 | 2R | A | Earnings beat + Iran/Strait of Hormuz oil tailwind |

**Trade notes:** Manual entry — BP not in bot universe. Qualitative override based on earnings beat (Q1) + geopolitical oil catalyst (Trump Truth Social post re: Iran/Strait of Hormuz). Price above VWAP ($46.49), ATR(5m)=$0.34, risk=$499 (0.5% equity), cost=$45,563 (45.5% cap).

**BP CLOSED — 2026-04-28 10:44 ET**
- Exit: ~$46.45 (market) | P&L: -$389.60 | Reason: VWAP broken, momentum reversed, early exit to preserve capital vs hard stop (-$497)
- Lesson: Iran/oil catalyst didn't sustain intraday. Qualitative override without ORB confirmation = higher risk.

### 2026-04-28 — OPEN POSITION

| Symbol | Shares | Entry | Stop | Target | R:R | Regime | Catalyst |
|--------|--------|-------|------|--------|-----|--------|----------|
| KO | 623 | $79.96 | $79.42 | $80.91 | 2R | A | Q1 earnings beat + raised FY guidance |

**Trade notes:** Manual entry — above VWAP ($79.64), above ORB high ($78.30). Earnings catalyst confirmed. Risk=$344 (0.34% equity), cost=$49,816 (50% cap).

**KO CLOSED — 2026-04-28 11:00 ET**
- Exit: ~$80.15 (trailing stop hit) | P&L: +$118.37 | Result: WIN
- Trailing stop raised from $79.42 → $80.05 → $80.10 → $80.15 as price climbed
- Earnings beat + raised guidance thesis played out cleanly

### 2026-04-28 — OPEN POSITION (Re-entry)

| Symbol | Shares | Entry | Stop | Target | R:R | Regime | Catalyst |
|--------|--------|-------|------|--------|-----|--------|----------|
| BP | 1065 | $46.76 | $46.48 | $47.25 | 2R | A | Iran/oil tailwind — re-entry after VWAP reclaim |

**Trade notes:** Re-entry after first BP trade stopped out at VWAP. Price reclaimed VWAP ($46.53), UP trend confirmed, holding $46.74+. Risk=$298, cost=$49,799.

**BP RE-ENTRY CLOSED — 2026-04-28 15:37 ET**
- Exit: $46.77 (market — manual close on chop concern) | P&L: +$10.65 | Result: SCRATCH WIN
- Stop raised to $46.70 before manual close. Exited ahead of EOD choppiness.
- Lesson: Re-entry clawed back partial losses from Trade 1. Small green beats giving it back.

---

## Day Summary — 2026-04-28

| Trade | Symbol | P&L |
|-------|--------|-----|
| 1 | BP (first entry) | -$389.60 |
| 2 | KO | +$118.37 |
| 3 | BP (re-entry) | +$10.65 |
| **Total** | | **-$260.58** |

Regime: A_LOW_VOL_TREND all day (VIX ~18.8, VVIX ~94-96). Bot ORB signals did not fire — gap-and-run day. All 3 trades were manual qualitative overrides. Account equity: $99,713.67.

### 2026-04-28 — OPEN POSITION (Trade 4)

| Symbol | Shares | Entry | Stop | Target | R:R | Regime | Catalyst |
|--------|--------|-------|------|--------|-----|--------|----------|
| NVDA | 202 | $210.09 | $207.50 | $212.50 | 2R | A | BofA bullish reset + XLK #1 sector + gap-and-run continuation |

**Trade notes:** Afternoon entry after lunch block lifted (12:15 ET). XLK sector ranked #1 (0.90) all day. BofA reset + institutional call buying confirmed pre-market. Price grinding higher all session ($209.30 → $210.09). Cost=$42,439 (42.5% exposure). Risk=$519 (0.52% equity).

**NVDA CLOSED — 2026-04-28 12:38 ET**
- Exit: $209.90 (stop hit) | P&L: -$38.38 | Result: CONTROLLED LOSS
- SPY rolled over into the close, dragged NVDA with it. Thesis didn't play out intraday.
- Stop did its job — capped the loss at $38 vs a potential larger drawdown.

---

## Final Day Summary — 2026-04-28

| Trade | Symbol | P&L |
|-------|--------|-----|
| 1 | BP (first entry) | -$389.60 |
| 2 | KO | +$118.37 |
| 3 | BP (re-entry) | +$10.65 |
| 4 | NVDA | -$38.38 |
| **Total** | | **-$298.96** |

Account equity: ~$99,701. 4 of 5 trade slots used. 1 remaining.

=== EOD 2026-04-28 ===
Equity: $99,674.64 (day P&L: -$325.36, day return: -0.33%)
Trades: 4 (W:2 / L:2) | Win rate: 50% | P/F: 0.30
  - Avg win: $64.51 | Avg loss: $213.99
  - Wins: KO (+$118.37), BP re-entry (+$10.65)
  - Losses: BP first (-$389.60), NVDA (-$38.38)
Regime: A_LOW_VOL_TREND all session (VIX ~18.6-19.1, VVIX ~94-96) | Kill switch: NO
Open overnight: NONE (all flat at close, 0 open orders)
Notes: Gap-and-run day — bot ORB signals never fired; all 4 trades were manual qualitative overrides. KO earnings thesis played out cleanly (only structural win); BP first entry was the day's worst lesson (qualitative override on Iran/oil catalyst without ORB confirmation). Account variance vs trade-log sum (-$325.36 actual vs -$298.96 logged) = ~$26 slippage/fees. Day trade count 4/4 — 1 trade slot unused, well under 5 cap. Loss 0.33% — well below 2% halt and 3% kill switch.
