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

## Trades — 2026-04-29

| # | Time (ET) | Sym | Side | Qty | Entry | Stop | Target | R:R | Regime | Catalyst |
|---|-----------|-----|------|-----|-------|------|--------|-----|--------|----------|
| 1 | 12:23 | GLD | LONG | 59 | $418.84 | $417.20 | $422.40 | 2.0R | A_LOW_VOL_TREND | FOMC-day discretionary override; ORB-H breakout + above VWAP, gold catching macro bid (Iran blockade headlines + stagflation talk + two-way Fed insurance). Hard exit by 1:55 PM ET regardless. Bracket order: stop ~0.39% / target ~0.85%. Risk: 59 × $1.64 = $96.76. Notional $24,711 (within 50% per-trade exposure cap). |

**Trade 1 outcome:** GLD scratched manually at 12:34 ET @ $417.89. **P&L: -$56.13** (-0.23R, -0.06% equity).
Reason: Pre-Fed positioning pushed yields up (TLT -0.20%) → gold faded back through $418 from intraday HOD $419.12 on dying volume. Manual scratch beat full-stop by ~$40. Setup invalidated when GLD lost VWAP momentum and broader market drifted bid-less into Fed decision. Lesson: low-volume mid-day breakout on Fed day = compression risk; pre-Fed yield drift is the gold killer regardless of macro narrative.

| Trade | Symbol | P&L |
|-------|--------|-----|
| 1 | GLD | -$56.13 |
| **Total** | | **-$56.13** |

Account equity: $99,618.07. 1 of 5 trade slots used. 4 remaining.

=== EOD 2026-04-29 ===
Equity: $99,618.07 (day P&L: -$56.57, day return: -0.06%)
Trades: 1 (W:0 / L:1) | Win rate: 0% | P/F: 0.00
  - Avg win: N/A | Avg loss: $56.13
  - Wins: NONE
  - Losses: GLD (-$56.13)
Regime: A_LOW_VOL_TREND all session (VIX 17.95, VVIX 91.03) | Kill switch: NO
Open overnight: NONE (all flat at close, 0 open orders)
Notes: FOMC day — single discretionary GLD long ahead of 2 PM Fed decision; pre-Fed yield drift faded gold off HOD on dying volume, manual scratch at -$56.13 vs full-stop ~$96.76 risk (saved ~$40). Account variance vs trade-log sum: -$56.57 actual vs -$56.13 logged = ~$0.44 slippage/fees. 1 of 5 trade slots used; bot ORB signals never fired (no qualifying gaps pre-market, FOMC compression suppressed momentum). Loss 0.06% — far below 2% halt and 3% kill switch. Day trade count at 5 (PDT cap reached on rolling 5-day window).

## Trades — 2026-04-30

| # | Time (ET) | Sym | Side | Qty | Entry | Stop | Target | R:R | Regime | Catalyst |
|---|-----------|-----|------|-----|-------|------|--------|-----|--------|----------|
| 1 | 14:22 | RUN | LONG | 332 | $12.68 | $12.27 | $13.39 | ~1.7R | A_LOW_VOL_TREND | Bot ORB-H breakout long w/ bracket. Notional $4,210 (4.2% exposure). Risk: 332 × $0.41 = $136.12. |
| 2 | 15:04 | RKLB | LONG | 58 | $82.50 | $80.45 | $86.79 | ~2.1R | A_LOW_VOL_TREND | Bot ORB-H breakout long w/ bracket. Notional $4,785 (4.8% exposure). Risk: 58 × $2.05 = $118.90. |

**Trade 1 outcome (RUN):** EOD close-all at 15:55 ET @ $12.73 (bracket legs auto-canceled). **P&L: +$16.60** (+0.12R).
**Trade 2 outcome (RKLB):** EOD close-all at 15:55 ET @ $82.27 (bracket legs auto-canceled). **P&L: -$13.35** (-0.11R).

Neither hit stop or target — both closed by EOD risk routine. RUN edged green; RKLB edged red.

| Trade | Symbol | P&L |
|-------|--------|-----|
| 1 | RUN | +$16.60 |
| 2 | RKLB | -$13.35 |
| **Total** | | **+$3.25** |

Account equity: $99,621.31. 2 of 5 trade slots used. 3 remaining.

=== EOD 2026-04-30 ===
Equity: $99,621.31 (day P&L: +$3.25, day return: +0.003%)
Trades: 2 (W:1 / L:1) | Win rate: 50% | P/F: 1.24
  - Avg win: $16.60 | Avg loss: $13.35
  - Wins: RUN (+$16.60)
  - Losses: RKLB (-$13.35)
Regime: A_LOW_VOL_TREND all session (VIX 18.81, VVIX 96.02) | Kill switch: NO
Open overnight: NONE (all flat at close, 0 open positions, 0 open orders)
Notes: First day post-universe-switch (small/mid-cap basket active since 2026-04-29) where bot ORB signals actually fired — both trades were systematic, not discretionary. RUN entry 14:22 ET, RKLB entry 15:04 ET. Neither setup had time to mature: both closed at 15:55 ET EOD close-all rather than hitting bracket stop/target. Net $3.25 — essentially flat (one tick each direction). Account variance vs trade-log sum: matches exactly. No-gap pre-market environment (no qualifying gaps ≥0.5%) did not suppress the bot — afternoon ORB-H breakouts triggered on intraday range expansion. Equity unchanged at risk-floor — far below 2% halt and 3% kill switch.


=== EOD 2026-05-01 ===
Equity: $99,621.24 (day P&L: -$0.07, day return: 0.000%)
Trades: 0 (W:0 / L:0) | Win rate: N/A | P/F: N/A
Regime: A_LOW_VOL_TREND all session (VIX 16.77, VVIX ~93.7) | Kill switch: NO
Open overnight: NONE (0 positions, 0 open orders, 0 trades)
Notes: No bot entries despite a heavy gap-up tape (16 universe symbols ≥0.8% gap; ROKU +9.3%, RIOT +4.9%, MSTR +2.9%, FSLR +2.5%, RKLB +2.5%). Bot ran the full session but no ORB-H breakouts cleared the volume + VWAP + ATR gates — gap-and-go open faded into chop, stuck in opening ranges. No discretionary overrides taken. Equity flat at $99,621.24 (-$0.07 vs prior close, rounding/fees). May best month since 2020 backdrop, S&P closed at record highs 04-30; tape strong but bot's intraday breakout setup didn't trigger. Loss far below 2% halt and 3% kill switch. Day trade count 7 on rolling 5-day window (PDT-tagged but well within paper-account margin).


=== AUDIT HALT 2026-05-03 ===

**Live entries halted.** `MAX_TRADES_PER_DAY = 0` (commit d91e293), wrapper restarted PID 79440 → child PID 87873 at 16:26:18 ET. Bot stays alive for monitoring; cannot enter trades until restored.

**Why:** Phase 2 audit on 4-window panel (2023H1, 2023H2, 2024H1, 2024H2) showed strategy unprofitable in every tested universe.

| Universe | Σ Return | Avg Sharpe | Trades |
|---|---|---|---|
| SMALL_CAP (live, 30 names) | -4.29% | -0.35 | 800 |
| MEGA_CAP (legacy 12) | -21.67% | -4.17 | 371 |

Mega-cap is *worse* than small-cap on every individual window — the 2026-04-29 universe switch was directionally correct, just insufficient. Universe revert does NOT fix the strategy.

**Decision tree:** memory/project_universe_ab_decision_tree.md Branch B (locked before reading the numbers). Strategy problem, not universe problem.

**Salvage queue (not committed yet):**
- Re-run the 4-window panel with `USE_FIB_RETRACEMENT_ENTRY=False` to match live config — backtest harnesses force-True it, possible the live bot is less bad than backtest implies
- VOLUME_MULTIPLIER sweep on small-cap (Phase 2c finding: this is the actual lever)
- USE_LIMIT_ORDER_ENTRIES A/B (live True since 2026-05-01, no multi-window evidence)
- SPY_GAP regime-dependence dig (helps in 2024 windows, hurts in 2023H2)

**Restore criterion:** restore `MAX_TRADES_PER_DAY = 5` only after a salvage config produces multi-window backtest evidence of profitability.

Account equity $99,621.24, no open positions, no open orders.



=== PROJECT RETIRED 2026-05-03 ===

**Trading bot retired.** No further development planned on this codebase.

**Reason:** Today's audit confirmed the strategy is unprofitable in every tested universe across the 4-window panel. Live config (retr=OFF, small-cap) sums to **-10.46%** across 2023H1-2024H2; the audit panel (retr=ON) was partly shadow-boxing a phantom feature (retracement entry exists only in `backtest.py`, never wired into live). After dropping decorative filters and confirming the universe switch was directionally correct, no remaining lever has multi-window evidence that would push the strategy positive. Continued tuning is unlikely to find an edge.

**Pivot:** Preston is moving the ORB / gap-continuation thesis to Pine Script + TradingView paper trading. Cheaper iteration, visible debugging, zero operational debt.

**State at retirement:**
- Branch: `preston-filters` at commit `6ae6213`
- Bot wrapper + python child terminated (full stop, no halt-monitor mode)
- Account equity $99,621.24, no open positions, no open orders
- `MAX_TRADES_PER_DAY = 0` (halt) remains in config so any accidental relaunch is gated

**If you ever want to revisit:**
- The audit history with retracement=ON is misleading — those backtests evaluated a strategy that was never wired into live. Re-running anything with `--retracement off` (matches live) is the only valid baseline.
- 9 backtest harnesses still need the `MAX_TRADES_PER_DAY` save/restore patch (see today's daily log Session 3, finding C2). Without it, halt invalidates them silently.
- Notification routines reference the dead `clickup.sh` stack and would need rewriting to `notify.sh` (finding C1).
- The retracement code path in `backtest.py` is a phantom feature — either implement it in `strategy.py`/`main.py` (backtest evidence: +6pp small-cap, +23pp mega-cap) or delete from `backtest.py`. Currently misleading.



=== STRATEGY SWAP — VWAP-BOUNCE LIVE 2026-05-03 ===

**Bot resumed from retirement.** Halt reversed; `MAX_TRADES_PER_DAY = 5` restored.

**New strategy:** Cameron VWAP-Bounce (Setup B only — no Setup A breakout, no Setup C micro-pullback). Wholesale replacement of the retired regime-aware ORB strategy.

**Long entry conditions (mirror for short):**
1. close > VWAP
2. close > 200 EMA (regime filter)
3. 9 EMA > 20 EMA (trend confirmation)
4. Within last 3 bars, at least one bar low touched VWAP within 0.15% (pullback signal)
5. Current bar close > prior bar close (bounce signal)
6. Relative volume ≥ 1.5× of 20-bar average (volume confirmation)

**Stop:** min(prior 5 bar lows) for long, max for short. Skip if stop distance > 1.5 × ATR (chop guardrail).
**Target:** 2R (entry ± 2 × risk_per_share).
**Risk per trade:** 0.75% of equity (bumped from 0.5%).
**Universe:** SPY, QQQ, AAPL, MSFT, NVDA, GOOGL, AMZN, META (8 mega-caps). Old 30-name small-cap basket retired.
**Direction:** both long and short — Cameron framework allows either side per symbol.

**Methodology rule violation acknowledged:** Per `feedback_evidence_before_live_changes.md`, no live changes without multi-window backtest evidence. This swap is going live with **zero backtest evidence**. Decision was made deliberately as Path 1 (live blind, learn empirically). Backtest validation queued as a future session item.

**What was rewritten this session:**
- `indicators.py` (Phase 1, `99934a7`) — added EMA + relative_volume; deleted opening_range, avg_volume_same_time_of_day, atr_stop_price, is_atr_expanding
- `config.py` + `strategy.py` (Phase 2-3, `33df1cb`) — Cameron VWAP-Bounce signal, ~140 lines of dead config removed
- `main.py` (Phase 4, `8d78c6c`) — 720 → 340 lines, regime/sentiment/sector/VIX-beta/VVIX/market-neutral all removed
- 6 dead modules deleted (Phase 6, `af1b24c`): regime, sentiment, sector_rotation, vix_factor, vvix_filter, market_neutral
- 2 dead test files deleted (Phase 7, `edb88e6`): test_entry_gates.py, test_indicators.py
- `journal.py` (`3b99881`) — TradeSignal field reads aligned with new dataclass; bug catch that would have crashed the bot on first trade

**What's deferred (low-impact stale state):**
- `backtest.py` — broken, on old ORB engine. `cmd_backtest` stubbed in main.py. Doesn't affect live.
- 11 broken backtest harness scripts in repo root. Doesn't affect live.
- 5 routine markdown files — still reference old strategy + dead clickup.sh notification path. Cloud-scheduled prompts only; live bot's notifications via notify.sh work fine.
- Bot's CLAUDE.md + memory/TRADING-STRATEGY.md — old rulebook references regime/ORB. Affects future-session context, not live.
- `README.md` — probably stale.

**Live trading context:**
- Branch `preston-filters`, commits past `04cc2fc` snapshot
- Account equity $99,621.24, no open positions, no open orders
- Wrapper restart needed to pick up new strategy (Phase 11 next)


=== EOD 2026-05-04 ===
Equity: $99,639.88 (day P&L: +$18.64, day return: +0.019%)
Trades: 1 (W:1 / L:0 / flat:0) | Win rate: 100% | P/F: ∞ (no losses)
  - Avg win: $18.64 | Avg loss: N/A
  - Wins: MSFT long (+$18.64)
  - Losses: NONE
Halt: NO | Kill switch: NO
Open overnight: NONE (Cameron strategy is intraday-only, EOD flat)
Notes: First successful Cameron VWAP-Bounce trade since strategy swap (2026-05-03). MSFT long entered 10:17 ET @ $417.757, exited 10:32 ET @ $419.621 (10 shares, +$1.864/share = +$18.64). Closed by bot ~13min after entry — no bracket legs visible on Alpaca (both buy and sell orders show as `market` type with `legs=0`); exit mechanism unclear from log but P&L is real and equity matches order math exactly. Bot wrapper auto-closed all (none open) at 3:55 PM ET as expected. Account variance vs trade-log sum: matches exactly ($18.64 = $18.64). Day trade count rolled from 7 → 8 on rolling 5-day window. PDT-flagged but well within paper-account margin. Bot pre-market gap %s buggy this morning (anchored to 2-day-old close); fixed mid-day in commit `7e88e4a` and 3 prior-corrections appended in RESEARCH-LOG. Bug signals to track: (1) `closure detected for MSFT but no fill found` WARNING at 10:32 — journal pipeline didn't capture the round-trip; trades.csv still shows last entry from 2026-04-30 (RKLB). Bot's internal `trades_today` counter also stayed at 0/5 after the closed round-trip — entry-side counter increment may be missing in the new Cameron signal path. Neither halt nor kill-switch tripped; far below 2% / 3% thresholds.
