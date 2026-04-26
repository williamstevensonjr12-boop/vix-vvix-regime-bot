# Research Log

Daily pre-market research entries appended here.

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
