# Research Log

Daily pre-market research entries appended here.

---

### 2026-04-27 — Pre-market Research (inline — no prior entry)

**Account:** Equity $100,000.00 | Cash $100,000.00 (100%) | Buying Power $200,000.00

**Volatility Snapshot:**
- VIX: 19.1 (trending: flat — near prior Apr average ~19.3)
- VVIX: 96.9 (normal range — no risk reduction triggered)
- VIX3M: 21.3 | Term ratio: 0.897 (backwardation — slight concern, spot > 3M)
- Put/Call ratio: 0.90 | Sentiment: neutral

**Regime Assessment:** A — LOW_VOL_TREND | score=0.716
- Active universe: SPY, QQQ, AAPL, MSFT, NVDA, AMZN, META, TSLA, AMD
- Size factor: 1.0× (full)
- Crisis alpha: disabled
- Sector rotation priority: XLK > XLF > QUAL > XLE > XLV

**Market Context:**
- Quotes at 9:43 ET: SPY $713.82, QQQ $662.52, NVDA $209.78, GLD $430.94
- Big earnings week (Apr 28: KO, V, SBUX, UPS, BP pre-market)
- VIX3M term ratio 0.897 indicates slight backwardation — mild structural caution

**Trade Ideas:**
1. NVDA — AI momentum, top Regime A name, XLK sector leader; ORB entry above 9:30-9:45 range high, stop -1.5×ATR, target 2R; regime fit: ✓
2. QQQ — Regime A momentum ETF; ORB/VWAP breakout, stop below ORB low, target 2R; regime fit: ✓
3. SPY — Broad market, regime-aligned; VWAP breakout entry; regime fit: ✓

**Risk Factors:**
- VIX3M backwardation (term ratio 0.897) — elevated mean-reversion risk
- P/C 0.90 — slightly above neutral, watch for put hedging increase
- Apr 28 earnings gap risk (V, KO, SBUX, UPS)
- No entries after 3:30 PM; close all by 3:55 PM

**VIX Beta Rankings (top 5):**
| Symbol | VIX Beta | Fear Resilience |
|--------|----------|-----------------|
| GLD    | Negative | High            |
| QQQ    | Low-med  | Medium          |
| SPY    | Low-med  | Medium          |
| MSFT   | Low-med  | Medium-high     |
| NVDA   | High     | Low             |

**Decision:** TRADE — Regime A confirmed, VVIX clean, accounts live. Watch NVDA and QQQ for ORB signals at 9:45.

---

## Template

### YYYY-MM-DD — Pre-market Research

**Account:** Equity $X | Cash $X | Buying Power $X

**Volatility Snapshot:**
- VIX: XX.X (trending: up/flat/down)
- VVIX: XXX.X
- VIX3M: XX.X | Term ratio: X.XX (contango/backwardation)
- Put/Call ratio: X.XX | Sentiment: neutral/fear/complacency

**Regime Assessment:** A / B / C
- Active universe: [...]
- Size factor: X.Xx
- Crisis alpha: enabled/disabled

**Market Context:**
- S&P 500 futures:
- Oil (WTI/Brent):
- Economic calendar:
- Earnings today:
- Key sector moves:

**Trade Ideas:**
1. SYMBOL — catalyst, entry $X, stop $X, target $X, R:R X:1, regime fit: ✓/✗
2. ...

**Risk Factors:**
-

**VIX Beta Rankings (top 5):**
| Symbol | VIX Beta | Fear Resilience |
|--------|----------|-----------------|

**Decision:** TRADE / HOLD (default HOLD — patience > activity)

---

### 2026-04-26 — Pre-market Research

**Account:** Equity $100,000.00 | Cash $100,000.00 (100%) | Buying Power $100,000.00
*(Alpaca API unavailable — env vars missing this run. Baseline paper account assumed.)*

**Volatility Snapshot:**
- VIX: ~18.71 (Apr 24 close); avg ~19.31 in April — trending: flat/slightly down
- VVIX: N/A — API unavailable (estimated normal range ~85-95 given VIX level)
- VIX3M: N/A | Term ratio: N/A (assumed contango — no spike conditions)
- Put/Call ratio: N/A | Sentiment: cautious optimism (AI tailwinds vs geopolitical risk)

**Regime Assessment:** A (borderline — VIX <20, SPY at record highs)
- Active universe: SPY, QQQ, AAPL, MSFT, NVDA, AMZN, META, TSLA, AMD (Regime A momentum)
- Size factor: 1.0× (full, but watch VIX proximity to 20 threshold)
- Crisis alpha: disabled
- Note: Iran conflict + Trump security scare are tail-risk factors; could tip to B quickly

**Market Context:**
- S&P 500 futures: 7,194.75 (opened at 7,143.00 Sunday — +0.72% from prior close; SPY hit record 7,165 on Apr 25)
- Oil: Elevated due to Iran conflict disrupting trade routes
- Economic calendar: Big earnings week (Apr 28 heavy — KO, V, SBUX, UPS, BP pre-market)
- Earnings today (Apr 26): Sunday — no pre-market earnings
- Key sector moves: Tech/AI +11% MTD; Staples +15% YTD; Defensives strengthening as geopolitical hedge

**Trade Ideas:**
1. NVDA — AI infrastructure momentum, tech sector leading +11% MTD; entry ~pullback to VWAP at open, stop -1.5×ATR, target 2R; regime fit: ✓ (Regime A momentum name)
2. GLD — Geopolitical hedge (Iran conflict, oil disruption), negative VIX beta, defensive; entry ~breakout above prior high, stop -1×ATR, target 2R; regime fit: ✓/borderline (Regime A/B crossover hedge)
3. XLV — Healthcare defensive with AI/biotech catalyst tailwinds, low VIX beta; entry VWAP support, stop -1×ATR, target 2R; regime fit: ✓ if VIX moves toward 20

**Risk Factors:**
- VIX at 18.71 is close to Regime B threshold (20) — one bad print could flip regime
- Iran conflict: geopolitical shock risk is elevated; energy prices already moving
- Trump security scare (Washington gunfire event) — political uncertainty premium
- Alpaca/Perplexity API keys not available this run — data from WebSearch fallback (less precise)
- April 28 earnings heavy slate could introduce gap risk overnight (V, KO, SBUX, UPS)

**VIX Beta Rankings (top 5):**
| Symbol | VIX Beta | Fear Resilience |
|--------|----------|-----------------|
| GLD    | Negative | High            |
| XLU    | Negative | High            |
| XLV    | Low      | High            |
| MSFT   | Low-med  | Medium          |
| NVDA   | High     | Low             |

**Decision:** HOLD
- Regime A confirmed but VIX borderline at ~19. Iran + political risk = elevated tail risk.
- No Alpaca data to confirm current positions or live regime — safe default is HOLD.
- Revisit at market open once live VIX/VVIX confirmed. If VIX holds <20 and VVIX <100, NVDA ORB setup is primary watch.

*Note: This run used WebSearch fallback — Perplexity API key not available in environment. Alpaca account/position data also unavailable. All figures estimated from public sources.*

---

### 2026-04-27 — Pre-market Research

**Account:** Equity $100,000.00 | Cash $100,000.00 (100%) | Buying Power $200,000.00 (2× margin)
*(Paper account — Alpaca paper-api confirmed active, no open positions)*

**Volatility Snapshot:**
- VIX: 19.0 (+1.71% pre-market) — live via regime-status
- VVIX: 96.9 — normal (below 100 risk-reduction threshold)
- VIX3M term ratio: 0.896 — slight backwardation (near-term vol mildly elevated vs deferred)
- Put/Call ratio: 0.90 — neutral sentiment
- Regime score: 0.717

**Regime Assessment:** A — LOW_VOL_TREND (confirmed live, unchanged from Apr 26)
- Active universe: SPY, QQQ, AAPL, MSFT, NVDA, AMZN, META, TSLA, AMD (Regime A momentum)
- Size factor: 1.00× (full sizing — VVIX <100)
- Crisis alpha: disabled
- Sector rotation leader: XLK (0.90 score), then XLF, QUAL, XLE, XLV
- VVIX filter: PASS — no entry restriction
- Note: VIX at 19.0 is 5% below Regime B threshold. One bad print or Iran escalation flips us to B.

**Market Context:**
- S&P 500 futures: +0.03% | Nasdaq 100: +0.21% | Dow: -0.16% — flat open
- Iran/Strait of Hormuz: Iran submitted new proposal to reopen strait; oil climbed on stalled talks; partial de-escalation signal but risk not cleared
- FOMC: Meeting Tue/Wed next week — 100% probability of hold; gasoline spike limiting cut optionality
- Mega-cap earnings: AAPL, AMZN, GOOGL, META, MSFT all report Wed–Thu — major binary event risk
- AM earnings today (Apr 27): VZ (Verizon), DPZ (Domino's) — low systemic impact
- Friday movers: NVDA +4.45% (sustained AI chip demand), AMZN +3.18%, CRM +2.33%
- Defensive rotation: XLU and XLP >3 SD above MA — institutional caution signal despite Regime A

**Trade Ideas:**
1. NVDA — AI chip demand momentum, sector leader, +4.45% Friday close; entry: ORB above 9:30 high with volume >1.5× avg, stop -1.5×ATR, target 2R; regime fit: ✓ (top Regime A momentum name); risk: earnings overhang Wed-Thu = overnight gap risk, do not hold overnight
2. QQQ — XLK sector leader in Regime A, Nasdaq futures slightly positive; entry: VWAP bounce or ORB breakout, stop -1×ATR, target 2R; regime fit: ✓; cleaner than single-stock risk pre-earnings
3. GLD — Iran/Strait geopolitical uncertainty not resolved; negative VIX beta; entry: above prior session high on volume, stop -1×ATR, target 2R; regime fit: ✓ borderline (better fit if VIX flips to 20+)

**Risk Factors:**
- VIX at 19.0 — single catalyst from Regime B flip (20 threshold); monitor intraday
- Term structure inverted (0.896) — near-term vol concern, not crisis but worth watching
- FOMC + mega-cap earnings this week: do NOT hold momentum positions overnight Wed/Thu
- Iran/Strait: proposal emerged but not resolved — energy price volatility remains
- AM earnings VZ/DPZ: minor, but any miss in telecom/consumer adds to cautious tone
- Defensive sector overextension (XLU, XLP >3 SD) suggests institutional hedging = not a pure bull tape

**VIX Beta Rankings (top 5 — Regime A, prefer low VIX beta for momentum):**
| Symbol | VIX Beta | Fear Resilience |
|--------|----------|-----------------|
| GLD    | Negative | High            |
| XLU    | Negative | High            |
| XLV    | Low      | High            |
| MSFT   | Low-med  | Medium          |
| NVDA   | High     | Low (momentum)  |

**Decision:** HOLD at open — reassess 9:35 ET
- Regime A confirmed live. But flat futures + inverted term structure + earnings binary risk this week = patience.
- If VIX holds <19.5 and VVIX stays <100 at 9:35: NVDA ORB is primary watch (intraday only, no overnight).
- If VIX spikes above 20 at open → flip to Regime B, shift universe to XLU/XLP/XLV/GLD, reduce to 0.5× size.

*Alpaca keys confirmed live this run (paper endpoint). VVIX/VIX data via Python regime-status.*
