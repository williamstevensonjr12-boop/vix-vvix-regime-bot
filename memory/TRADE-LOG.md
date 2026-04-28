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
