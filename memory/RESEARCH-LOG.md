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

---
## 2026-04-28 — Pre-Market Research

**Volatility**
- VIX: 18.43 (+2.28%)
- VVIX: 93.86 (-3.42%)
- VIX3M: 20.77

**Universe Prices**
  SPY: $715.17 (+0.17%)
  QQQ: $664.23 (+0.05%)
  NVDA: $216.61 (+4.00%)
  AMD: $334.63 (-3.79%)
  AMZN: $261.12 (-1.09%)
  META: $678.62 (+0.53%)
  MSFT: $424.82 (+0.05%)
  AAPL: $267.61 (-1.27%)
  TSLA: $378.67 (+0.63%)

**Headlines**

**GOOGLE_NEWS_MARKET**
- S&P 500 futures slip after benchmark posts another record: Live updates - CNBC
- Stock market today: S&P 500, Nasdaq notch fresh records, oil edges higher as markets weigh Iran peace odds - Yahoo Finance
- Stock Market Today: Futures Mostly Lower to Start Busy Day of Earnings; Oil Rises Further; 2-Day Fed Meeting Kicks Off Today - Investopedia
- US Stock Market Today S&P 500 Futures Dip On Rising Inflation And Oil Concerns - Yahoo Finance
- Nasdaq Set to Open Down Amid Iran Peace Fears - Barron's
- Stock Market Today: Nasdaq Futures Fall, Oil Extends Gains — Live Updates - WSJ
- Stock Market Today: S&P 500, Dow and Nasdaq set for mixed start as AI-linked stocks slip on OpenAI concerns, and after reports that Trump is unhappy with Iran's proposal to end war - MarketWatch
- Tech Drags Stocks Lower as Brent Tops $110 Again: Markets Wrap - Bloomberg
- Stock Market Today: Dow Dips But Nasdaq, Nvidia Gain; Microsoft Up After This OpenAI Deal (Live Coverage) - Investor's Business Daily
- Warren Buffett has stark message for investors on stock market - thestreet.com

**GOOGLE_NVDA**
- Bank of America resets Nvidia stock forecast - thestreet.com
- Why Nvidia (NVDA) Stock Is Trading Up Today - Yahoo Finance
- Nvidia, Intel call buyers defy the dip in chip stocks - CNBC
- Stocks Inch to New Records as Nvidia Strength Overcomes Consumer Weakness - WSJ
- Stock Market Today: Dow Dips But Nasdaq, Nvidia Gain; Microsoft Up After This OpenAI Deal (Live Coverage) - Investor's Business Daily

**GOOGLE_AMD**
- Top Analyst Downgrades AMD Stock Despite Strong Near-Term Outlook — Here’s Why - TipRanks
- Nvidia Stock Falls. What’s Hitting AMD, Broadcom and the AI Chip Players. - Barron's
- Oracle, AMD, Intel, BP, Bed Bath & Beyond, and More Stock Market Movers - Barron's
- Advanced Micro Devices (AMD) Stock Sinks As Market Gains: Here's Why - Yahoo Finance
- As Chip Stocks Soar, This Options Spread Trade On AMD Almost Always Makes A Profit - Investor's Business Daily

**GOOGLE_AMZN**
- Amazon (AMZN) Reports Earnings Tomorrow: What To Expect - StockStory
- Amazon Is About to Report Q1 Earnings. Do Options Traders Expect a Major Move in AMZN Stock? - Yahoo Finance
- Amazon Q1: $200B In FY26 CapEx For A $15B Run-Rate Story (NASDAQ:AMZN) - Seeking Alpha
- AMD Stock Sold by Cathie Wood’s Ark. It Buys Amazon in Strategy Shift. - Barron's
- Where Will Amazon Stock Be in 5 Years? - The Motley Fool

**GOOGLE_META**
- Meta's Stock May Plunge Following Results (NASDAQ:META) - Seeking Alpha
- Prediction: This Will Be Meta's Stock Price in 5 Years - Yahoo Finance
- Evercore Stays Bullish on Meta Platforms Stock, Expects ‘Very Modest Beat & Bracket Q1’ - TipRanks
- Meta Q1: AI Ad Thesis Getting Stronger (NASDAQ:META) - Seeking Alpha
- China Halts Meta’s $2 Billion Deal for Manus - Yahoo Finance

**GOOGLE_SPY**
- S&P 500 Movers | Winners: | Losers: - Trefis
- Stock Market Today: SPY Hits Record High as U.S.-Iran Talks Stall ahead of Busy Earnings Week - TipRanks
- SPY 260427 710.00P (SPY260427P710000) Stock Options Chain | Quotes & News - Moomoo
- Breadth Stays Positive, but Monday Shows Some Fatigue - ChartMill
- "LIVE: Stock Market Spy SPX Mag 7 — Options Flow Breakdown" (RDmovNGq2b) - Fathom Journal

**YAHOO_NVDA**
- The only number that matters for 'Magnificent 7' earnings this week: Morning Brief
- Nvidia could be undervalued by at least 30%: BofA analyst on Mag 7
- Stocks' strong April gains come with 1 potential downside
- The $600 Billion Question Hanging Over Big Tech This Earnings Season
- Microsoft vs. Amazon: Which AI Stock Is the Better Buy?
- 3 Green Energy Stocks for Investors Playing the Long Game in 2026

**YAHOO_AMD**
- Google, Meta, Microsoft, Amazon, Apple earnings: What to expect
- Will Nvidia's explosive rally end soon?
- Tech’s ‘New Normal’ Trade Pair: Long Chip Stock, Short Software
- OpenAI Worries Spark Tech Stocks Selloff
- These Stocks Are Today’s Movers: Oracle, AMD, Intel, BP, Bed Bath & Beyond, and More
- OpenAI-Linked Stocks Slump on Report of Startup Missing Targets

**YAHOO_AMZN**
- The only number that matters for 'Magnificent 7' earnings this week: Morning Brief
- AWS exec. expands on productivity benefits of training AI agents
- Google, Meta, Microsoft, Amazon, Apple earnings: What to expect
- The $600 Billion Question Hanging Over Big Tech This Earnings Season
- Microsoft vs. Amazon: Which AI Stock Is the Better Buy?
- Big Tech investors to gauge payoff as AI spending set to hit $600 billion

**YAHOO_META**
- The only number that matters for 'Magnificent 7' earnings this week: Morning Brief
- Google, Meta, Microsoft, Amazon, Apple earnings: What to expect
- Amazon's 2026 CapEx spend: What Polymarket is predicting
- The $600 Billion Question Hanging Over Big Tech This Earnings Season
- Reliance and Meta's joint venture signals India's shift from AI ambition to enterprise deployment
- Tech’s ‘New Normal’ Trade Pair: Long Chip Stock, Short Software

**YAHOO_SPY**
- S&P 500 Holding Pattern: Mag 7 Earnings Collide With Oil Surge and Fed Fears
- Exchange-Traded Funds Down, Equity Futures Mixed Pre-Bell Monday Amid Hormuz Uncertainty, Corporate Earnings
- EXCLUSIVE: Ryan Detrick Shares A Political Trend For 2026 That Has Produced 'Some Really Solid Returns'
- Gunman likely targeted Trump administration, acting US attorney general says
- Buy, Hold, or Sell VOO at $650?
- The VIX Dips Below 19. Here’s What That Means for Your Portfolio.

**MARKETWATCH**
- UPS leaves full-year outlook intact even as quarterly earnings top target, and stock falls
- Here are 21 stocks to keep powering the tech rally, say these analysts.
- ‘I hope to retire early’: I’m 56 and have 80% in a traditional IRA and 20% in a Roth. Am I in trouble?
- Bill Ackman is placing a bet on individual investors with dual Pershing Square public offerings
- ‘We believe it’s real’: My mom received a check from a class-action lawsuit. It bounced. Could this be a scam?
- SoftBank shares dive, U.S. tech stocks under pressure on report of missed goals at OpenAI
- A second China shock is hitting Europe. These stocks are most vulnerable, strategist says.
- Global oil contract tops $110 after reports that Trump unhappy with proposal from Iran to end war

**SEEKING_ALPHA**
- First Commonwealth Financial Non-GAAP EPS of $0.37 misses by $0.03, revenue of $133.7M misses by $0.62M
- S&amp;P Global Non-GAAP EPS of $4.97 beats by $0.15, revenue of $4.17B beats by $100M
- Sportradar GAAP EPS of -€0.02, revenue of €346.52M; reaffirms FY26 outlook
- Asbury Automotive Non-GAAP EPS of $5.37 misses by $0.25, revenue of $4.1B misses by $270M
- LGI Homes Non-GAAP EPS of $0.24 beats by $0.37, revenue of $319.74M misses by $3.19M
- CECO Environmental Non-GAAP EPS of $0.36 beats by $0.21, revenue of $205.9M beats by $7.02M
- Coca-Cola rallies after organic sales smash estimates; PEP and KDP also gain

**WSJ_MARKETS**
- Stocks Sink in Broad AI Rout Sparked by China's DeepSeek
- Comex Gold, Silver Settle Lower
- DeepSeek Won't Sink U.S. AI Titans
- Financial Services Roundup: Market Talk
- Arabica Coffee Prices Hit Record on U.S., Colombia Tariff Spat
- Swiss franc, Japanese yen Rise as DeepSeek News Boosts Safe Havens
- Natural Gas Falls on Shifting Weather Forecasts
- Building-Products Distributor QXO Launches Hostile Bid for Beacon


### 🤖 AI TRADING INTELLIGENCE BRIEF
⚠️ ANTHROPIC_API_KEY not set — skipping AI brief.

---

---
## 2026-04-28 — Pre-Market Research

**Volatility**
- VIX: 18.45 (+2.39%)
- VVIX: 93.86 (-3.42%)
- VIX3M: 20.77

**Universe Prices**
  SPY: $715.17 (+0.17%)
  QQQ: $664.23 (+0.05%)
  NVDA: $216.61 (+4.00%)
  AMD: $334.63 (-3.79%)
  AMZN: $261.12 (-1.09%)
  META: $678.62 (+0.53%)
  MSFT: $424.82 (+0.05%)
  AAPL: $267.61 (-1.27%)
  TSLA: $378.67 (+0.63%)

**Headlines**

**GOOGLE_NEWS_MARKET**
- S&P 500 futures slip after benchmark posts another record: Live updates - CNBC
- Stock market today: S&P 500, Nasdaq notch fresh records, oil edges higher as markets weigh Iran peace odds - Yahoo Finance
- Stock Market Today: Futures Mostly Lower to Start Busy Day of Earnings; Oil Rises Further; 2-Day Fed Meeting Kicks Off Today - Investopedia
- US Stock Market Today S&P 500 Futures Dip On Rising Inflation And Oil Concerns - Yahoo Finance
- Nasdaq Set to Open Down Amid Iran Peace Fears - Barron's
- Stock Market Today: Nasdaq Futures Fall, Oil Extends Gains — Live Updates - WSJ
- Stock Market Today: S&P 500, Dow and Nasdaq set for mixed start as AI-linked stocks slip on OpenAI concerns, and after reports that Trump is unhappy with Iran's proposal to end war - MarketWatch
- Tech Drags Stocks Lower as Brent Tops $110 Again: Markets Wrap - Bloomberg
- Stock Market Today: Dow Dips But Nasdaq, Nvidia Gain; Microsoft Up After This OpenAI Deal (Live Coverage) - Investor's Business Daily
- Warren Buffett has stark message for investors on stock market - thestreet.com

**GOOGLE_NVDA**
- Bank of America resets Nvidia stock forecast - thestreet.com
- Why Nvidia (NVDA) Stock Is Trading Up Today - Yahoo Finance
- Nvidia, Intel call buyers defy the dip in chip stocks - CNBC
- Stocks Inch to New Records as Nvidia Strength Overcomes Consumer Weakness - WSJ
- Stock Market Today: Dow Dips But Nasdaq, Nvidia Gain; Microsoft Up After This OpenAI Deal (Live Coverage) - Investor's Business Daily

**GOOGLE_AMD**
- Top Analyst Downgrades AMD Stock Despite Strong Near-Term Outlook — Here’s Why - TipRanks
- Nvidia Stock Falls. What’s Hitting AMD, Broadcom and the AI Chip Players. - Barron's
- Oracle, AMD, Intel, BP, Bed Bath & Beyond, and More Stock Market Movers - Barron's
- Advanced Micro Devices (AMD) Stock Sinks As Market Gains: Here's Why - Yahoo Finance
- As Chip Stocks Soar, This Options Spread Trade On AMD Almost Always Makes A Profit - Investor's Business Daily

**GOOGLE_AMZN**
- Amazon (AMZN) Reports Earnings Tomorrow: What To Expect - StockStory
- Amazon Is About to Report Q1 Earnings. Do Options Traders Expect a Major Move in AMZN Stock? - Yahoo Finance
- Amazon Q1: $200B In FY26 CapEx For A $15B Run-Rate Story (NASDAQ:AMZN) - Seeking Alpha
- AMD Stock Sold by Cathie Wood’s Ark. It Buys Amazon in Strategy Shift. - Barron's
- Where Will Amazon Stock Be in 5 Years? - The Motley Fool

**GOOGLE_META**
- Meta's Stock May Plunge Following Results (NASDAQ:META) - Seeking Alpha
- Prediction: This Will Be Meta's Stock Price in 5 Years - Yahoo Finance
- Evercore Stays Bullish on Meta Platforms Stock, Expects ‘Very Modest Beat & Bracket Q1’ - TipRanks
- Meta Q1: AI Ad Thesis Getting Stronger (NASDAQ:META) - Seeking Alpha
- China Halts Meta’s $2 Billion Deal for Manus - Yahoo Finance

**GOOGLE_SPY**
- S&P 500 Movers | Winners: | Losers: - Trefis
- Stock Market Today: SPY Hits Record High as U.S.-Iran Talks Stall ahead of Busy Earnings Week - TipRanks
- SPY 260427 710.00P (SPY260427P710000) Stock Options Chain | Quotes & News - Moomoo
- Breadth Stays Positive, but Monday Shows Some Fatigue - ChartMill
- "LIVE: Stock Market Spy SPX Mag 7 — Options Flow Breakdown" (RDmovNGq2b) - Fathom Journal

**YAHOO_NVDA**
- The only number that matters for 'Magnificent 7' earnings this week: Morning Brief
- Nvidia could be undervalued by at least 30%: BofA analyst on Mag 7
- Stocks' strong April gains come with 1 potential downside
- The $600 Billion Question Hanging Over Big Tech This Earnings Season
- Microsoft vs. Amazon: Which AI Stock Is the Better Buy?
- 3 Green Energy Stocks for Investors Playing the Long Game in 2026

**YAHOO_AMD**
- Google, Meta, Microsoft, Amazon, Apple earnings: What to expect
- Will Nvidia's explosive rally end soon?
- Tech’s ‘New Normal’ Trade Pair: Long Chip Stock, Short Software
- OpenAI Worries Spark Tech Stocks Selloff
- These Stocks Are Today’s Movers: Oracle, AMD, Intel, BP, Bed Bath & Beyond, and More
- OpenAI-Linked Stocks Slump on Report of Startup Missing Targets

**YAHOO_AMZN**
- The only number that matters for 'Magnificent 7' earnings this week: Morning Brief
- AWS exec. expands on productivity benefits of training AI agents
- Google, Meta, Microsoft, Amazon, Apple earnings: What to expect
- The $600 Billion Question Hanging Over Big Tech This Earnings Season
- Microsoft vs. Amazon: Which AI Stock Is the Better Buy?
- Big Tech investors to gauge payoff as AI spending set to hit $600 billion

**YAHOO_META**
- The only number that matters for 'Magnificent 7' earnings this week: Morning Brief
- Google, Meta, Microsoft, Amazon, Apple earnings: What to expect
- Amazon's 2026 CapEx spend: What Polymarket is predicting
- The $600 Billion Question Hanging Over Big Tech This Earnings Season
- Reliance and Meta's joint venture signals India's shift from AI ambition to enterprise deployment
- Tech’s ‘New Normal’ Trade Pair: Long Chip Stock, Short Software

**YAHOO_SPY**
- S&P 500 Holding Pattern: Mag 7 Earnings Collide With Oil Surge and Fed Fears
- Exchange-Traded Funds Down, Equity Futures Mixed Pre-Bell Monday Amid Hormuz Uncertainty, Corporate Earnings
- EXCLUSIVE: Ryan Detrick Shares A Political Trend For 2026 That Has Produced 'Some Really Solid Returns'
- Gunman likely targeted Trump administration, acting US attorney general says
- Buy, Hold, or Sell VOO at $650?
- The VIX Dips Below 19. Here’s What That Means for Your Portfolio.

**MARKETWATCH**
- UPS leaves full-year outlook intact even as quarterly earnings top target, and stock falls
- Here are 21 stocks to keep powering the tech rally, say these analysts.
- ‘I hope to retire early’: I’m 56 and have 80% in a traditional IRA and 20% in a Roth. Am I in trouble?
- Bill Ackman is placing a bet on individual investors with dual Pershing Square public offerings
- ‘We believe it’s real’: My mom received a check from a class-action lawsuit. It bounced. Could this be a scam?
- SoftBank shares dive, U.S. tech stocks under pressure on report of missed goals at OpenAI
- A second China shock is hitting Europe. These stocks are most vulnerable, strategist says.
- Global oil contract tops $110 after reports that Trump unhappy with proposal from Iran to end war

**SEEKING_ALPHA**
- reAlpha Tech GAAP EPS of -$0.03 beats by $0.01, revenue of $0.84M misses by $0.44M
- Amber International GAAP EPADS of $0.01, revenue of $16.3M
- Stepan Non-GAAP EPS of $0.45 beats by $0.06, revenue of $604.51M misses by $7.74M
- First Commonwealth Financial Non-GAAP EPS of $0.37 misses by $0.03, revenue of $133.7M misses by $0.62M
- S&P Global Non-GAAP EPS of $4.97 beats by $0.15, revenue of $4.17B beats by $100M
- Sportradar GAAP EPS of -€0.02, revenue of €346.52M; reaffirms FY26 outlook
- Asbury Automotive Non-GAAP EPS of $5.37 misses by $0.25, revenue of $4.1B misses by $270M

**WSJ_MARKETS**
- Stocks Sink in Broad AI Rout Sparked by China's DeepSeek
- Comex Gold, Silver Settle Lower
- DeepSeek Won't Sink U.S. AI Titans
- Financial Services Roundup: Market Talk
- Arabica Coffee Prices Hit Record on U.S., Colombia Tariff Spat
- Swiss franc, Japanese yen Rise as DeepSeek News Boosts Safe Havens
- Natural Gas Falls on Shifting Weather Forecasts
- Building-Products Distributor QXO Launches Hostile Bid for Beacon


### 🤖 AI TRADING INTELLIGENCE BRIEF
⚠️ anthropic package not installed — run: pip install anthropic

---

---
## 2026-04-28 — Pre-Market Research

**Volatility**
- VIX: 18.47 (+2.50%)
- VVIX: 93.86 (-3.42%)
- VIX3M: 20.77

**Universe Prices**
  SPY: $715.17 (+0.17%)
  QQQ: $664.23 (+0.05%)
  NVDA: $216.61 (+4.00%)
  AMD: $334.63 (-3.79%)
  AMZN: $261.12 (-1.09%)
  META: $678.62 (+0.53%)
  MSFT: $424.82 (+0.05%)
  AAPL: $267.61 (-1.27%)
  TSLA: $378.67 (+0.63%)

**Headlines**

**GOOGLE_NEWS_MARKET**
- S&P 500 futures slip after benchmark posts another record: Live updates - CNBC
- Stock market today: S&P 500, Nasdaq notch fresh records, oil edges higher as markets weigh Iran peace odds - Yahoo Finance
- Stock Market Today: Futures Mostly Lower to Start Busy Day of Earnings; Oil Rises Further; 2-Day Fed Meeting Kicks Off Today - Investopedia
- US Stock Market Today S&P 500 Futures Dip On Rising Inflation And Oil Concerns - Yahoo Finance
- Nasdaq Set to Open Down Amid Iran Peace Fears - Barron's
- Stock Market Today: Nasdaq Futures Fall, Oil Extends Gains — Live Updates - WSJ
- Stock Market Today: S&P 500, Dow and Nasdaq set for mixed start as AI-linked stocks slip on OpenAI concerns, and after reports that Trump is unhappy with Iran's proposal to end war - MarketWatch
- Tech Drags Stocks Lower as Brent Tops $110 Again: Markets Wrap - Bloomberg
- Stock Market Today: Dow Dips But Nasdaq, Nvidia Gain; Microsoft Up After This OpenAI Deal (Live Coverage) - Investor's Business Daily
- Warren Buffett has stark message for investors on stock market - thestreet.com

**GOOGLE_NVDA**
- Bank of America resets Nvidia stock forecast - thestreet.com
- Why Nvidia (NVDA) Stock Is Trading Up Today - Yahoo Finance
- Nvidia, Intel call buyers defy the dip in chip stocks - CNBC
- Stocks Inch to New Records as Nvidia Strength Overcomes Consumer Weakness - WSJ
- Stock Market Today: Dow Dips But Nasdaq, Nvidia Gain; Microsoft Up After This OpenAI Deal (Live Coverage) - Investor's Business Daily

**GOOGLE_AMD**
- Top Analyst Downgrades AMD Stock Despite Strong Near-Term Outlook — Here’s Why - TipRanks
- Nvidia Stock Falls. What’s Hitting AMD, Broadcom and the AI Chip Players. - Barron's
- Oracle, AMD, Intel, BP, Bed Bath & Beyond, and More Stock Market Movers - Barron's
- Advanced Micro Devices (AMD) Stock Sinks As Market Gains: Here's Why - Yahoo Finance
- As Chip Stocks Soar, This Options Spread Trade On AMD Almost Always Makes A Profit - Investor's Business Daily

**GOOGLE_AMZN**
- Amazon (AMZN) Reports Earnings Tomorrow: What To Expect - StockStory
- Amazon Is About to Report Q1 Earnings. Do Options Traders Expect a Major Move in AMZN Stock? - Yahoo Finance
- Amazon Q1: $200B In FY26 CapEx For A $15B Run-Rate Story (NASDAQ:AMZN) - Seeking Alpha
- AMD Stock Sold by Cathie Wood’s Ark. It Buys Amazon in Strategy Shift. - Barron's
- Where Will Amazon Stock Be in 5 Years? - The Motley Fool

**GOOGLE_META**
- Meta's Stock May Plunge Following Results (NASDAQ:META) - Seeking Alpha
- Prediction: This Will Be Meta's Stock Price in 5 Years - Yahoo Finance
- Evercore Stays Bullish on Meta Platforms Stock, Expects ‘Very Modest Beat & Bracket Q1’ - TipRanks
- Meta Q1: AI Ad Thesis Getting Stronger (NASDAQ:META) - Seeking Alpha
- China Halts Meta’s $2 Billion Deal for Manus - Yahoo Finance

**GOOGLE_SPY**
- S&P 500 Movers | Winners: | Losers: - Trefis
- Stock Market Today: SPY Hits Record High as U.S.-Iran Talks Stall ahead of Busy Earnings Week - TipRanks
- SPY 260427 710.00P (SPY260427P710000) Stock Options Chain | Quotes & News - Moomoo
- Breadth Stays Positive, but Monday Shows Some Fatigue - ChartMill
- "LIVE: Stock Market Spy SPX Mag 7 — Options Flow Breakdown" (RDmovNGq2b) - Fathom Journal

**YAHOO_NVDA**
- The only number that matters for 'Magnificent 7' earnings this week: Morning Brief
- Nvidia could be undervalued by at least 30%: BofA analyst on Mag 7
- Stocks' strong April gains come with 1 potential downside
- The $600 Billion Question Hanging Over Big Tech This Earnings Season
- Microsoft vs. Amazon: Which AI Stock Is the Better Buy?
- 3 Green Energy Stocks for Investors Playing the Long Game in 2026

**YAHOO_AMD**
- Google, Meta, Microsoft, Amazon, Apple earnings: What to expect
- Will Nvidia's explosive rally end soon?
- Tech’s ‘New Normal’ Trade Pair: Long Chip Stock, Short Software
- OpenAI Worries Spark Tech Stocks Selloff
- These Stocks Are Today’s Movers: Oracle, AMD, Intel, BP, Bed Bath & Beyond, and More
- OpenAI-Linked Stocks Slump on Report of Startup Missing Targets

**YAHOO_AMZN**
- The only number that matters for 'Magnificent 7' earnings this week: Morning Brief
- AWS exec. expands on productivity benefits of training AI agents
- Google, Meta, Microsoft, Amazon, Apple earnings: What to expect
- The $600 Billion Question Hanging Over Big Tech This Earnings Season
- Microsoft vs. Amazon: Which AI Stock Is the Better Buy?
- Big Tech investors to gauge payoff as AI spending set to hit $600 billion

**YAHOO_META**
- The only number that matters for 'Magnificent 7' earnings this week: Morning Brief
- Google, Meta, Microsoft, Amazon, Apple earnings: What to expect
- Amazon's 2026 CapEx spend: What Polymarket is predicting
- The $600 Billion Question Hanging Over Big Tech This Earnings Season
- Reliance and Meta's joint venture signals India's shift from AI ambition to enterprise deployment
- Tech’s ‘New Normal’ Trade Pair: Long Chip Stock, Short Software

**YAHOO_SPY**
- S&P 500 Holding Pattern: Mag 7 Earnings Collide With Oil Surge and Fed Fears
- Exchange-Traded Funds Down, Equity Futures Mixed Pre-Bell Monday Amid Hormuz Uncertainty, Corporate Earnings
- EXCLUSIVE: Ryan Detrick Shares A Political Trend For 2026 That Has Produced 'Some Really Solid Returns'
- Gunman likely targeted Trump administration, acting US attorney general says
- Buy, Hold, or Sell VOO at $650?
- The VIX Dips Below 19. Here’s What That Means for Your Portfolio.

**MARKETWATCH**
- UPS leaves full-year outlook intact even as quarterly earnings top target, and stock falls
- Here are 21 stocks to keep powering the tech rally, say these analysts.
- ‘I hope to retire early’: I’m 56 and have 80% in a traditional IRA and 20% in a Roth. Am I in trouble?
- Bill Ackman is placing a bet on individual investors with dual Pershing Square public offerings
- ‘We believe it’s real’: My mom received a check from a class-action lawsuit. It bounced. Could this be a scam?
- SoftBank shares dive, U.S. tech stocks under pressure on report of missed goals at OpenAI
- A second China shock is hitting Europe. These stocks are most vulnerable, strategist says.
- Global oil contract tops $110 after reports that Trump unhappy with proposal from Iran to end war

**SEEKING_ALPHA**
- reAlpha Tech GAAP EPS of -$0.03 beats by $0.01, revenue of $0.84M misses by $0.44M
- Amber International GAAP EPADS of $0.01, revenue of $16.3M
- Stepan Non-GAAP EPS of $0.45 beats by $0.06, revenue of $604.51M misses by $7.74M
- First Commonwealth Financial Non-GAAP EPS of $0.37 misses by $0.03, revenue of $133.7M misses by $0.62M
- S&P Global Non-GAAP EPS of $4.97 beats by $0.15, revenue of $4.17B beats by $100M
- Sportradar GAAP EPS of -€0.02, revenue of €346.52M; reaffirms FY26 outlook
- Asbury Automotive Non-GAAP EPS of $5.37 misses by $0.25, revenue of $4.1B misses by $270M

**WSJ_MARKETS**
- Stocks Sink in Broad AI Rout Sparked by China's DeepSeek
- Comex Gold, Silver Settle Lower
- DeepSeek Won't Sink U.S. AI Titans
- Financial Services Roundup: Market Talk
- Arabica Coffee Prices Hit Record on U.S., Colombia Tariff Spat
- Swiss franc, Japanese yen Rise as DeepSeek News Boosts Safe Havens
- Natural Gas Falls on Shifting Weather Forecasts
- Building-Products Distributor QXO Launches Hostile Bid for Beacon


### 🤖 AI TRADING INTELLIGENCE BRIEF
# AI TRADING INTELLIGENCE BRIEF
**Date:** Pre-Market | **VIX:** 18.47 | **VVIX:** 93.86

---

## 1. MARKET SENTIMENT
**Neutral to Bearish** — Record highs met with profit-taking as oil spikes above $110 on Iran deal collapse fears, while OpenAI concerns drag AI/tech names.

---

## 2. KEY MACRO RISKS
- **Oil surge above $110:** Trump reportedly unhappy with Iran proposal; Brent spike pressuring risk assets and raising inflation concerns
- **Fed meeting kicks off today:** 2-day FOMC begins amid rising inflation expectations from energy costs
- **Mag 7 earnings concentration:** AMZN, META reporting this week with $600B AI capex scrutiny

---

## 3. CATALYSTS BY SYMBOL
- **NVDA (+4.0% PM):** BofA resets price target bullish; call buyers active despite sector weakness — positive momentum divergence
- **AMD (-3.8% PM):** Top analyst downgrade despite near-term outlook; Cathie Wood selling — clear negative catalyst
- **AMZN (-1.1% PM):** Reports Q1 earnings tomorrow; options pricing major move; $200B FY26 capex focus
- **META (+0.5% PM):** Q1 earnings imminent; China blocks $2B Manus deal; mixed analyst sentiment

---

## 4. REGIME RECOMMENDATION
**Regime B (Elevated Volatility)** — VIX at 18.47 rising +2.5% with compressed VVIX suggests directional moves likely; favor momentum plays with tighter stops and reduced position size.

---

## 5. PRIORITY LIST

**TRADE:**
- NVDA — Strong pre-market momentum (+4%), positive flow, clear relative strength
- SPY — Record high context provides clear ORB levels; liquid for quick exits

**AVOID:**
- AMD — Downgrade overhang + negative momentum; don't catch falling knife
- AMZN/META — Pre-earnings volatility makes ORB setups unreliable; wait for post-report clarity

---

---
## 2026-04-28 — Pre-Market Research

**Volatility**
- VIX: 18.56 (+3.00%)
- VVIX: 93.86 (-3.42%)
- VIX3M: 20.77

**Universe Prices**
  SPY: $715.17 (+0.17%)
  QQQ: $664.23 (+0.05%)
  NVDA: $216.61 (+4.00%)
  AMD: $334.63 (-3.79%)
  AMZN: $261.12 (-1.09%)
  META: $678.62 (+0.53%)
  MSFT: $424.82 (+0.05%)
  AAPL: $267.61 (-1.27%)
  TSLA: $378.67 (+0.63%)

**Headlines**

**GOOGLE_NEWS_MARKET**
- S&P 500 futures slip after benchmark posts another record: Live updates - CNBC
- Stock market today: S&P 500, Nasdaq notch fresh records, oil edges higher as markets weigh Iran peace odds - Yahoo Finance
- Stock Market Today: Futures Mostly Lower to Start Busy Day of Earnings; Oil Rises Further; 2-Day Fed Meeting Kicks Off Today - Investopedia
- US Stock Market Today S&P 500 Futures Dip On Rising Inflation And Oil Concerns - Yahoo Finance
- Nasdaq Set to Open Down Amid Iran Peace Fears - Barron's
- Stock Market Today: S&P 500, Dow and Nasdaq set for mixed start as AI-linked stocks slip on OpenAI concerns, and after reports that Trump is unhappy with Iran's proposal to end war - MarketWatch
- Stock Market Today: Nasdaq Futures Fall, Oil Extends Gains — Live Updates - WSJ
- Tech Drags Stocks Lower as Brent Tops $110 Again: Markets Wrap - Bloomberg
- Stock Market Today: Dow Dips But Nasdaq, Nvidia Gain; Microsoft Up After This OpenAI Deal (Live Coverage) - Investor's Business Daily
- Warren Buffett has stark message for investors on stock market - thestreet.com

**GOOGLE_NVDA**
- Bank of America resets Nvidia stock forecast - thestreet.com
- Why Nvidia (NVDA) Stock Is Trading Up Today - Yahoo Finance
- Nvidia, Intel call buyers defy the dip in chip stocks - CNBC
- Stocks Inch to New Records as Nvidia Strength Overcomes Consumer Weakness - WSJ
- Stock Market Today: Dow Dips But Nasdaq, Nvidia Gain; Microsoft Up After This OpenAI Deal (Live Coverage) - Investor's Business Daily

**GOOGLE_AMD**
- Top Analyst Downgrades AMD Stock Despite Strong Near-Term Outlook — Here’s Why - TipRanks
- Nvidia Stock Falls. What’s Hitting AMD, Broadcom and the AI Chip Players. - Barron's
- Oracle, AMD, Intel, BP, Bed Bath & Beyond, and More Stock Market Movers - Barron's
- Advanced Micro Devices (AMD) Stock Sinks As Market Gains: Here's Why - Yahoo Finance
- Why I'm Still Very Bullish Into AMD Earnings - Seeking Alpha

**GOOGLE_AMZN**
- Amazon (AMZN) Reports Earnings Tomorrow: What To Expect - StockStory
- Amazon Is About to Report Q1 Earnings. Do Options Traders Expect a Major Move in AMZN Stock? - Yahoo Finance
- Amazon Q1: $200B In FY26 CapEx For A $15B Run-Rate Story (NASDAQ:AMZN) - Seeking Alpha
- AMD Stock Sold by Cathie Wood’s Ark. It Buys Amazon in Strategy Shift. - Barron's
- Where Will Amazon Stock Be in 5 Years? - The Motley Fool

**GOOGLE_META**
- Meta's Stock May Plunge Following Results (NASDAQ:META) - Seeking Alpha
- Prediction: This Will Be Meta's Stock Price in 5 Years - Yahoo Finance
- Evercore Stays Bullish on Meta Platforms Stock, Expects ‘Very Modest Beat & Bracket Q1’ - TipRanks
- Meta Q1: AI Ad Thesis Getting Stronger (NASDAQ:META) - Seeking Alpha
- China Halts Meta’s $2 Billion Deal for Manus - Yahoo Finance

**GOOGLE_SPY**
- S&P 500 Movers | Winners: | Losers: - Trefis
- Stock Market Today: SPY Hits Record High as U.S.-Iran Talks Stall ahead of Busy Earnings Week - TipRanks
- SPY 260427 710.00P (SPY260427P710000) Stock Options Chain | Quotes & News - Moomoo
- Breadth Stays Positive, but Monday Shows Some Fatigue - ChartMill
- "LIVE: Stock Market Spy SPX Mag 7 — Options Flow Breakdown" (RDmovNGq2b) - Fathom Journal

**YAHOO_NVDA**
- The only number that matters for 'Magnificent 7' earnings this week: Morning Brief
- Nvidia could be undervalued by at least 30%: BofA analyst on Mag 7
- Stocks' strong April gains come with 1 potential downside
- The $600 Billion Question Hanging Over Big Tech This Earnings Season
- Microsoft vs. Amazon: Which AI Stock Is the Better Buy?
- 3 Green Energy Stocks for Investors Playing the Long Game in 2026

**YAHOO_AMD**
- Google, Meta, Microsoft, Amazon, Apple earnings: What to expect
- Will Nvidia's explosive rally end soon?
- Tech’s ‘New Normal’ Trade Pair: Long Chip Stock, Short Software
- OpenAI Worries Spark Tech Stocks Selloff
- These Stocks Are Today’s Movers: Oracle, AMD, Intel, BP, Bed Bath & Beyond, and More
- OpenAI-Linked Stocks Slump on Report of Startup Missing Targets

**YAHOO_AMZN**
- The only number that matters for 'Magnificent 7' earnings this week: Morning Brief
- Elon Musk vs. Sam Altman: What to know about the OpenAI case
- Amazon's 2026 CapEx spend: What Polymarket is predicting
- Stocks' strong April gains come with 1 potential downside
- The $600 Billion Question Hanging Over Big Tech This Earnings Season
- Microsoft vs. Amazon: Which AI Stock Is the Better Buy?

**YAHOO_META**
- The only number that matters for 'Magnificent 7' earnings this week: Morning Brief
- Amazon's 2026 CapEx spend: What Polymarket is predicting
- The $600 Billion Question Hanging Over Big Tech This Earnings Season
- Reliance and Meta's joint venture signals India's shift from AI ambition to enterprise deployment
- Tech’s ‘New Normal’ Trade Pair: Long Chip Stock, Short Software
- Meta (META) Q1 Earnings: What To Expect

**YAHOO_SPY**
- S&P 500 Holding Pattern: Mag 7 Earnings Collide With Oil Surge and Fed Fears
- Exchange-Traded Funds Down, Equity Futures Mixed Pre-Bell Monday Amid Hormuz Uncertainty, Corporate Earnings
- EXCLUSIVE: Ryan Detrick Shares A Political Trend For 2026 That Has Produced 'Some Really Solid Returns'
- Gunman likely targeted Trump administration, acting US attorney general says
- Buy, Hold, or Sell VOO at $650?
- The VIX Dips Below 19. Here’s What That Means for Your Portfolio.

**MARKETWATCH**
- Here are 21 stocks to keep powering the tech rally, say these analysts
- UPS leaves full-year outlook intact even as quarterly earnings top target, and stock falls
- ‘I hope to retire early’: I’m 56 and have 80% in a traditional IRA and 20% in a Roth. Am I in trouble?
- Bill Ackman is placing a bet on individual investors with dual Pershing Square public offerings
- ‘We believe it’s real’: My mom received a check from a class-action lawsuit. It bounced. Could this be a scam?
- SoftBank shares dive, U.S. tech stocks under pressure on report of missed goals at OpenAI
- A second China shock is hitting Europe. These stocks are most vulnerable, strategist says.
- Global oil contract tops $110 after reports that Trump unhappy with proposal from Iran to end war

**SEEKING_ALPHA**
- Ares Capital Q1 earnings miss amid lower transaction activity
- China lifts ban on purchases of BHP's portside iron ore cargoes
- UPS tops logistics valuation rankings while shares slip on unchanged outlook
- Coca-Cola in charts: Q1 shows broad-based revenue acceleration across regions
- reAlpha Tech GAAP EPS of -$0.03 beats by $0.01, revenue of $0.84M misses by $0.44M
- Amber International GAAP EPADS of $0.01, revenue of $16.3M
- Stepan Non-GAAP EPS of $0.45 beats by $0.06, revenue of $604.51M misses by $7.74M

**WSJ_MARKETS**
- Stocks Sink in Broad AI Rout Sparked by China's DeepSeek
- Comex Gold, Silver Settle Lower
- DeepSeek Won't Sink U.S. AI Titans
- Financial Services Roundup: Market Talk
- Arabica Coffee Prices Hit Record on U.S., Colombia Tariff Spat
- Swiss franc, Japanese yen Rise as DeepSeek News Boosts Safe Havens
- Natural Gas Falls on Shifting Weather Forecasts
- Building-Products Distributor QXO Launches Hostile Bid for Beacon


### 🤖 AI TRADING INTELLIGENCE BRIEF
# AI TRADING INTELLIGENCE BRIEF
**Date:** Pre-Market | **Regime:** A_LOW_VOL_TREND (0.746)

---

## 1. MARKET SENTIMENT
**Neutral-to-Cautious** — Record highs on SPY/QQQ conflict with rising oil ($110 Brent), OpenAI-linked selloff concerns, and mixed futures heading into heavy Mag-7 earnings week.

---

## 2. KEY MACRO RISKS
- **Oil surge / Iran uncertainty:** Brent topping $110 on stalled U.S.-Iran talks; inflationary pressure risk
- **OpenAI contagion:** Reports of missed targets triggering broad AI/tech profit-taking
- **Fed meeting kickoff:** 2-day FOMC begins today; any hawkish signals amplify volatility

---

## 3. CATALYSTS BY SYMBOL
- **NVDA:** BofA price target reset (bullish); call buying defying chip dip; +4% pre-market strength
- **AMD:** Analyst downgrade despite near-term outlook; Cathie Wood selling; -3.8% pre-market weakness
- **AMZN:** Q1 earnings tomorrow; options traders pricing significant move; CapEx focus ($200B FY26)
- **META:** Q1 earnings imminent; mixed analyst sentiment (Evercore bullish, Seeking Alpha warns plunge risk)

---

## 4. REGIME RECOMMENDATION
**Regime A (Low Vol Trend)** remains favored — VIX at 18.56 with declining VVIX (93.86) supports trend-following ORB setups, but tighten stops given headline-driven cross-currents.

---

## 5. PRIORITY LIST

**TRADE:**
- **NVDA** — Strong pre-market momentum, positive analyst action, call flow support
- **META** — Earnings catalyst with defined risk; ORB can capture directional move
- **SPY/QQQ** — Clean regime signal; use as hedge or core trend vehicle

**AVOID:**
- **AMD** — Downgrade overhang + negative pre-market; no edge until sentiment stabilizes
- **AMZN** — Earnings tomorrow creates gamma trap; wait for post-report clarity
- **AAPL** — No catalyst, -1.27% drag; dead money today

---

---
## 2026-04-28 — Pre-Market Research

**Volatility**
- VIX: 18.87 (+4.72%)
- VVIX: 93.86 (-3.42%)
- VIX3M: 20.77

**Universe Prices**
  SPY: $715.17 (+0.17%)
  QQQ: $664.23 (+0.05%)
  NVDA: $216.61 (+4.00%)
  AMD: $334.63 (-3.79%)
  AMZN: $261.12 (-1.09%)
  META: $678.62 (+0.53%)
  MSFT: $424.82 (+0.05%)
  AAPL: $267.61 (-1.27%)
  TSLA: $378.67 (+0.63%)

**Headlines**

**GOOGLE_NEWS_MARKET**
- S&P 500 futures slip as oil rises, Nasdaq futures slide on OpenAI report: Live updates - CNBC
- Stock Market Today: Nasdaq Futures Fall, Oil Extends Gains — Live Updates - WSJ
- Stock Market Today: Futures Point Mostly Lower to Start Busy Day of Earnings; Oil Rises Further; 2-Day Fed Meeting Kicks Off Today - Investopedia
- US Stock Market Today S&P 500 Futures Dip On Rising Inflation And Oil Concerns - Yahoo Finance
- Nasdaq Set to Open Down Amid Iran Peace Fears - Barron's
- Stock Market Today: S&P 500, Dow and Nasdaq set for mixed start as AI-linked stocks slip on OpenAI concerns, and after reports that Trump is unhappy with Iran's proposal to end war - MarketWatch
- Stock Market Today: Dow Dips But Nasdaq, Nvidia Gain; Microsoft Up After This OpenAI Deal (Live Coverage) - Investor's Business Daily
- Warren Buffett has stark message for investors on stock market - thestreet.com
- Stocks are back at records, but one CIO says investors are overlooking a major change in the post-Iran-war market - Business Insider
- Stock Market Today, April 27: Rally Stalls at Midday as Iran Talks Falter - The Motley Fool

**GOOGLE_NVDA**
- Why Nvidia (NVDA) Stock Is Trading Up Today - Yahoo Finance
- Bank of America resets Nvidia stock forecast - thestreet.com
- Nvidia Stock Falls. What’s Hitting AMD, Broadcom and the AI Chip Players. - Barron's
- Stocks Inch to New Records as Nvidia Strength Overcomes Consumer Weakness - WSJ
- Nvidia, Intel call buyers defy the dip in chip stocks - CNBC

**GOOGLE_AMD**
- AMD Is Surging Into Earnings. Is This Your Last Chance to Buy Before May 5? - The Motley Fool
- Top Analyst Downgrades AMD Stock Despite Strong Near-Term Outlook — Here’s Why - TipRanks
- Nvidia Stock Falls. What’s Hitting AMD, Broadcom and the AI Chip Players. - Barron's
- Oracle, AMD, Intel, BP, Bed Bath & Beyond, and More Stock Market Movers - Barron's
- Advanced Micro Devices (AMD) Stock Sinks As Market Gains: Here's Why - Yahoo Finance

**GOOGLE_AMZN**
- Amazon Is About to Report Q1 Earnings. Do Options Traders Expect a Major Move in AMZN Stock? - Yahoo Finance
- Amazon (AMZN) Reports Earnings Tomorrow: What To Expect - StockStory
- Should You Buy, Sell or Hold Amazon Stock Before Q1 Earnings? - Zacks Investment Research
- AMD Stock Sold by Cathie Wood’s Ark. It Buys Amazon in Strategy Shift. - Barron's
- Where Will Amazon Stock Be in 5 Years? - The Motley Fool

**GOOGLE_META**
- Meta's Stock May Plunge Following Results (NASDAQ:META) - Seeking Alpha
- Prediction: This Will Be Meta's Stock Price in 5 Years - Yahoo Finance
- Evercore Stays Bullish on Meta Platforms Stock, Expects ‘Very Modest Beat & Bracket Q1’ - TipRanks
- Meta Q1: AI Ad Thesis Getting Stronger (NASDAQ:META) - Seeking Alpha
- China Halts Meta’s $2 Billion Deal for Manus - Yahoo Finance

**GOOGLE_SPY**
- S&P 500 Movers | Winners: | Losers: - Trefis
- Stock Market Today: SPY Hits Record High as U.S.-Iran Talks Stall ahead of Busy Earnings Week - TipRanks
- SPY 260427 710.00P (SPY260427P710000) Stock Options Chain | Quotes & News - Moomoo
- Breadth Stays Positive, but Monday Shows Some Fatigue - ChartMill
- Stock Outperformance Isn’t About Value, Growth, Biz Model, Or Execution (NYSEARCA:SPY) - Seeking Alpha

**YAHOO_NVDA**
- The only number that matters for 'Magnificent 7' earnings this week: Morning Brief
- Nvidia could be undervalued by at least 30%: BofA analyst on Mag 7
- Stocks' strong April gains come with 1 potential downside
- Microsoft in the Crosshairs as the Musk-Altman Courtroom Battle Gets Underway
- OpenAI Hit a Speed Bump. Here’s Why Nvidia’s Long-Term Story Is Still Intact
- The Mag 7 Earnings Gauntlet Begins: Four Reports That Could Reset the Market

**YAHOO_AMD**
- Google, Meta, Microsoft, Amazon, Apple earnings: What to expect
- Will Nvidia's explosive rally end soon?
- Tech’s ‘New Normal’ Trade Pair: Long Chip Stock, Short Software
- OpenAI Worries Spark Tech Stocks Selloff
- These Stocks Are Today’s Movers: Oracle, AMD, Intel, BP, Bed Bath & Beyond, and More
- OpenAI-Linked Stocks Slump on Report of Startup Missing Targets

**YAHOO_AMZN**
- The only number that matters for 'Magnificent 7' earnings this week: Morning Brief
- Elon Musk vs. Sam Altman: What to know about the OpenAI case
- Amazon's 2026 CapEx spend: What Polymarket is predicting
- Stocks' strong April gains come with 1 potential downside
- OpenAI Hit a Speed Bump. Here’s Why Nvidia’s Long-Term Story Is Still Intact
- The Mag 7 Earnings Gauntlet Begins: Four Reports That Could Reset the Market

**YAHOO_META**
- The only number that matters for 'Magnificent 7' earnings this week: Morning Brief
- Amazon's 2026 CapEx spend: What Polymarket is predicting
- OpenAI Hit a Speed Bump. Here’s Why Nvidia’s Long-Term Story Is Still Intact
- The Mag 7 Earnings Gauntlet Begins: Four Reports That Could Reset the Market
- The $600 Billion Question Hanging Over Big Tech This Earnings Season
- Reliance and Meta's joint venture signals India's shift from AI ambition to enterprise deployment

**YAHOO_SPY**
- Investors Worry About Mounting Debt — 7 S&P 500 Companies Owe Most
- S&P 500 Holding Pattern: Mag 7 Earnings Collide With Oil Surge and Fed Fears
- Exchange-Traded Funds Down, Equity Futures Mixed Pre-Bell Monday Amid Hormuz Uncertainty, Corporate Earnings
- EXCLUSIVE: Ryan Detrick Shares A Political Trend For 2026 That Has Produced 'Some Really Solid Returns'
- Gunman likely targeted Trump administration, acting US attorney general says
- Buy, Hold, or Sell VOO at $650?

**MARKETWATCH**
- Watch for these 21 best-in-class stocks to keep powering the tech rally, analysts advise
- UPS leaves full-year outlook intact even as quarterly earnings top target, and stock falls
- ‘I hope to retire early’: I’m 56 and have 80% in a traditional IRA and 20% in a Roth. Am I in trouble?
- Bill Ackman is placing a bet on individual investors with dual Pershing Square public offerings
- ‘We believe it’s real’: My mom received a check from a class-action lawsuit. It bounced. Could this be a scam?
- SoftBank shares dive, U.S. tech stocks under pressure on report of missed goals at OpenAI
- A second China shock is hitting Europe. These stocks are most vulnerable, strategist says.
- Global oil contract tops $110 after reports that Trump unhappy with proposal from Iran to end war

**SEEKING_ALPHA**
- Hope Bancorp GAAP EPS of $0.23 beats by $0.01, revenue of $141.02M misses by $4.28M
- Ping An Insurance reports Q1 results
- Ares Capital in charts: Strong Q1 dividends offset fee contraction; interest income from investments rises Y/Y
- Kiniksa Pharmaceuticals International, plc GAAP EPS of $0.27 beats by $0.09, revenue of $214.3M beats by $8.21M
- Earnings Snapshot: Corning beats Q1 expectations, but guidance disappoints
- Wave Life Sciences GAAP EPS of -$0.13 beats by $0.19, revenue of $38.25M beats by $30.33M
- Rithm Capital stock edges up on strong Q1 segment revenues

**WSJ_MARKETS**
- Stocks Sink in Broad AI Rout Sparked by China's DeepSeek
- Comex Gold, Silver Settle Lower
- DeepSeek Won't Sink U.S. AI Titans
- Financial Services Roundup: Market Talk
- Arabica Coffee Prices Hit Record on U.S., Colombia Tariff Spat
- Swiss franc, Japanese yen Rise as DeepSeek News Boosts Safe Havens
- Natural Gas Falls on Shifting Weather Forecasts
- Building-Products Distributor QXO Launches Hostile Bid for Beacon


### 🤖 AI TRADING INTELLIGENCE BRIEF
# AI TRADING INTELLIGENCE BRIEF
**Date: April 28, 2025 | Pre-Market**

---

## 1. MARKET SENTIMENT
**Neutral-to-Bearish** — Mixed futures with rising oil ($110+ on Iran deal rejection), OpenAI concerns dragging AI names, and elevated VIX (+4.72%) signal caution despite SPY near record highs.

---

## 2. KEY MACRO RISKS
- **Oil spike / Iran uncertainty**: Trump reportedly unhappy with Iran proposal; Hormuz concerns could escalate and pressure risk assets
- **Mag 7 earnings gauntlet**: AMZN, META reporting this week — high IV, potential for violent moves
- **OpenAI negative headlines**: SoftBank -7%, spillover selling hitting AI/chip complex pre-market

---

## 3. CATALYSTS BY SYMBOL
- **NVDA**: Positive — BofA reset with bullish outlook; call buying despite sector weakness; +4% pre-market strength
- **AMD**: Negative — Analyst downgrade despite near-term outlook; -3.79% pre-market; earnings May 5 overhang
- **AMZN**: Earnings tomorrow — Options pricing major move; Cathie Wood rotation into name signals institutional positioning
- **META**: Earnings this week — Seeking Alpha warns of potential plunge; China halted $2B Manus deal

---

## 4. REGIME RECOMMENDATION
**Regime B (Elevated Volatility)** — VIX 18.87 above 15 threshold with rising trend (+4.72%), VVIX declining suggests vol-of-vol compression; favor tighter stops and reduced position sizing.

---

## 5. PRIORITY LIST

**TRADE:**
- NVDA (positive momentum, strong pre-market, clear institutional support)
- SPY (range-bound near highs, clean ORB setups likely)

**AVOID:**
- AMD (downgrade overhang, negative pre-market gap, earnings uncertainty)
- AMZN, META (binary earnings risk within 48hrs — ORB signals unreliable with elevated IV)
- TSLA (no catalyst, likely to chop)

---

### INTRADAY UPDATE — 2026-04-28 09:35 ET

**Trump Truth Social post — Iran/Strait of Hormuz collapse warning**
- Posted ~9:30 ET open; geopolitical escalation on top of existing Brent $110+ tension
- Crude futures risk: Strait of Hormuz closure = ~20% global oil supply disruption
- Impact on watchlist:
  - BP: double catalyst (earnings beat + oil spike tailwind) — priority elevated
  - NVDA/tech: risk-off headwind if crude rips; don't chase further pre-market gains
  - SPY: watch for chop/pullback if crude moves sharply
- Bot action: live VIX/VVIX gates handle regime shift automatically; if VIX approaches 21+ consider Regime B rules
- Qualitative bias: lean BP over NVDA if oil spike confirms at open

---

### MIDDAY SCAN — 2026-04-28 (11:46 ET)

**Regime check:** A_LOW_VOL_TREND — NO CHANGE | score=0.742 | VIX=18.6 | VVIX=94.5 | P/C=0.90 | size=1.00x
**Positions:** Flat (3 trades closed) | **Slots remaining:** 2 of 5 | **Equity:** $99,713.67
**Exposure cap available:** ~$49,857 (50%) — split evenly = ~$24,900 per position

**Afternoon watchlist (live quotes):**
| Symbol | Bid | Ask | Mid | Notes |
|--------|-----|-----|-----|-------|
| NVDA | $209.29 | $209.32 | $209.30 | Top pick — tight spread, holding gap gains |
| AAPL | $270.05 | $270.08 | $270.07 | Regime A name, XLK sector, clean |
| MSFT | $426.55 | $426.66 | $426.60 | Strong but high price, sizing constrained |
| SPY | $709.75 | $709.89 | $709.82 | Gap-and-run, broad market holding |
| QQQ | $654.49 | $654.55 | $654.52 | Tech broad, following SPY |
| BP | $46.79 | $46.81 | $46.80 | Already traded 2x today — SKIP |
| KO | $80.03 | $80.04 | $80.04 | Already traded today — SKIP |
| NUE | $209.76 | $224.43 | — | Wide spread, illiquid — SKIP |
| AMD | $318.09 | $330.00 | — | Wide spread + morning AVOID — SKIP |

**Top 2 afternoon setups (enter after 12:15 ET):**

1. **NVDA — $209.30** | XLK sector #1 | BofA bullish + call buying still active
   - Entry trigger: VWAP reclaim + hold above $209.50 on volume after lunch lull
   - Stop: ~$207.50 (1.5x ATR, est.) | Target: $212.50+ (2R)
   - Size: ~119 shares (~$24,900, 25% exposure)

2. **AAPL — $270.07** | Clean Regime A momentum, no negative catalysts
   - Entry trigger: VWAP reclaim + hold above $270.50 after 12:15
   - Stop: ~$268.00 (1.5x ATR, est.) | Target: $273.50+ (2R)
   - Size: ~92 shares (~$24,900, 25% exposure)

**Gates to confirm at entry time:**
- [ ] VVIX still <110?
- [ ] Price above VWAP (check live at 12:15)?
- [ ] Volume picking up from lunch lull?
- [ ] Both positions together ≤ 50% exposure cap?

---

### MIDDAY SCAN (scheduled re-check) — 2026-04-28 (12:01 ET)

**Regime:** A_LOW_VOL_TREND — NO CHANGE | score=0.742 | VIX=18.6 | VVIX=94.5 | term=0.886 | P/C=0.90 | size=1.00x
**Positions:** FLAT | **Open orders:** NONE | **Equity:** $99,713.67

**Risk gates:**
- VVIX <110: ✅ (94.5)
- VVIX <120: ✅ (no entry block)
- No VVIX +10% intraday spike: ✅
- No regime shift since open: ✅

**Action taken:** NONE. No positions to manage; no stop triggers; no regime-driven rotation needed. Afternoon plan from 11:46 scan (NVDA/AAPL after 12:15 ET) remains valid pending live VWAP/volume confirmation at entry time.

---
## 2026-04-29 — Pre-Market Research

**Volatility**
- VIX: 17.95 (+0.67%)
- VVIX: 91.03 (-3.02%)
- VIX3M: 20.49

**Universe Prices + Pre-Market Gaps**
  SPY: $711.69 (-0.49%) | pre=$711.69 gap=0.0%
  QQQ: $657.55 (-1.01%) | pre=$657.55 gap=0.0%
  NVDA: $213.17 (-1.59%) | pre=$213.17 gap=0.0%
  AMD: $323.21 (-3.41%) | pre=$323.21 gap=0.0%
  AMZN: $259.7 (-0.54%) | pre=$259.7 gap=0.0%
  META: $671.34 (-1.07%) | pre=$671.34 gap=0.0%
  MSFT: $429.25 (+1.04%) | pre=$429.25 gap=0.0%
  AAPL: $270.71 (+1.16%) | pre=$270.71 gap=0.0%
  TSLA: $376.02 (-0.70%) | pre=$376.02 gap=0.0%
  XLK: $157.85 (-1.69%) | pre=$157.85 gap=0.0%

**Gap-Aligned Candidates (≥0.5% threshold)**
- Gap UP (long ORB pairing): (none)
- Gap DOWN (short ORB pairing, B/C only): (none)

**Headlines**

**GOOGLE_NEWS_MARKET**
- S&P 500 pulls back from record Tuesday, Nasdaq closes lower as chip stocks sell off: Live updates - CNBC
- S&P 500 futures edge higher as Wall Street looks ahead to ‘Mag 7’ earnings and Fed decision: Live updates - CNBC
- Stock market today: Dow, S&P 500, Nasdaq drop as chip stocks sink on OpenAI report, oil rises - Yahoo Finance
- Stock Market Today: Futures Little Changed Ahead of Tech Earnings, Fed Decision; Oil Jumps on Report Trump Says to Prepare for Extended Iran Blockade - Investopedia
- US Stock Market Today S&P 500 Futures Edge Higher As Fed Decision Looms - simplywall.st
- US Stock Market Today S&P 500 Futures Flat As Traders Await Fed Decision - Yahoo Finance
- Stock Market News From April 28, 2026: Dow, S&P 500, Nasdaq Down; Nvidia, Oracle, AMD, Intel, More Movers - Barron's
- Stock Market Today: Dow, S&P 500 and Nasdaq set to rise ahead of host of tech earnings; Fed interest-rate decision due - MarketWatch
- Stock Market Today: Nasdaq Beat Up After OpenAI Report; Nvidia, Palantir Drop (Live Coverage) - Investor's Business Daily
- Stock Market Today, April 28: BigBear.ai Rises on Heavy Volume Ahead of Earnings as AI Defense Stocks See Increased Trading Activity - The Motley Fool

**GOOGLE_NVDA**
- Traders bet Nvidia's stock will return to record highs soon - CNBC
- Bank of America resets Nvidia stock forecast - thestreet.com
- Nvidia (NVDA) Stock Trades Down, Here Is Why - Yahoo Finance
- Stock Market Today: Nasdaq Beat Up After OpenAI Report; Nvidia, Palantir Drop (Live Coverage) - Investor's Business Daily
- Will Nvidia's explosive rally end soon? - Yahoo Finance

**GOOGLE_AMD**
- Arm Holdings, AMD, Intel Crater in CPU Stock Shock - 24/7 Wall St.
- Advanced Micro Devices (AMD) Stock Sinks As Market Gains: Here's Why - Yahoo Finance
- Nvidia Stock Struggles After OpenAI Panic. How AMD, Broadcom Are Trading. - Barron's
- Oracle, AMD, and CoreWeave stocks sink after report says OpenAI missed sales, user targets - Yahoo Finance
- AMD Supplier Up 65% This Month Soars On Earnings Beat - Investor's Business Daily

**GOOGLE_AMZN**
- Amazon Reports Earnings on Wednesday—Here's How Much the Stock Is Expected to Move - Investopedia
- AMD Stock Sold by Cathie Wood’s Ark. It Buys Amazon in Strategy Shift. - Barron's
- Amazon To Rally More Than 24%? Here Are 10 Top Analyst Forecasts For Tuesday - Benzinga
- At $265: How Amazon Stock Is Getting Rerated - Trefis
- Amazon Earnings Preview: All Eyes on AWS As Investors Want AI Payoff - Business Insider

**GOOGLE_META**
- Meta shares look 'iffy' into earnings. How to trade it - CNBC
- How Much Is Meta Stock Expected to Move After Earnings? - Investopedia
- Meta's Stock May Plunge Following Results (NASDAQ:META) - Seeking Alpha
- Prediction: This Will Be Meta's Stock Price in 5 Years - Yahoo Finance
- META Stock Earns Hold Rating ahead of Q1 Earnings as Analyst Flags Higher Future Spending - TipRanks

**GOOGLE_SPY**
- Goldman’s Flood Says Brace for Near-Term Selloff, Buy Stocks Dip - Bloomberg.com
- Stock Market Today: SPY, QQQ Lose Steam on AI Jitters ahead of Fed Rate Decision - TipRanks
- Morgan Stanley’s Slimmon Says Be Ready to Buy Short-Term Pullback in Stocks - Bloomberg.com
- Stock Outperformance Isn’t About Value, Growth, Biz Model, Or Execution (NYSEARCA:SPY) - Seeking Alpha
- A Stock Pullback May Be Coming – Goldman Sachs Strategist Explains Why - TipRanks

**YAHOO_NVDA**
- Big Tech: What this strategist is looking for on earnings calls
- OpenAI miss sparks sell-off for Oracle, Nvidia, CoreWeave stocks
- 4 Dates for Disney Stock Investors to Circle in May
- Billionaire Gold Bug Eric Sprott Just Extended His Hycroft Mining Buying Spree
- Social Buzz: Wallstreetbets Stocks Mixed Pre-Bell Wednesday; Micron to Rise, Robinhood to Fall
- 2 Top Bargain Stocks Ready for a Bull Run

**YAHOO_AMD**
- Tech stocks today: Oracle, AMD, and other AI-driven names sink, with Big Tech earnings on deck
- Social Buzz: Wallstreetbets Stocks Mixed Pre-Bell Wednesday; Micron to Rise, Robinhood to Fall
- Nvidia Stock Struggles to Recover From OpenAI Panic. How AMD, Broadcom Are Trading.
- AMD (AMD) Stock Trades Down, Here Is Why
- Northland Securities Flags Rising Competition for Advanced Micro Devices (AMD)
- Nasdaq, S&P 500 end lower on renewed AI growth worries

**YAHOO_AMZN**
- Market mayhem? Powell's last stand, Big Tech earnings in focus
- Mag 7 earnings, Fed day, Warsh confirmation vote: What to Watch
- I'll die with my Apple stock: Polcari
- Brace for eye-popping AI spending plans when 'Magnificent 7' earnings roll in
- A blue-collar worker says he makes $10,000 per month from Amazon in just 20 hours of work — how you can do it, too
- Dow Jones Futures: Seagate, Bloom Energy, Teradyne Lead Earnings Movers; Tech Titans On Tap

**YAHOO_META**
- Market mayhem? Powell's last stand, Big Tech earnings in focus
- Big Tech: What this strategist is looking for on earnings calls
- Dow Jones Futures: Seagate, Bloom Energy, Teradyne Lead Earnings Movers; Tech Titans On Tap
- Market Rally Rides OpenAI Shock Ahead of Fed Decision, Big Tech Earnings. Stock Futures Rise.
- Hyperscaler results pose major test for AI-driven US stock market
- US Has More Natural Gas Than It Can Use as War Chokes Global Supply

**YAHOO_SPY**
- Intel Stock Is Up 92% in April. How to Safeguard Your Gains.
- ETF Fund Flows as of April 28, 2026
- When April Delivers 5% Gains, the Rest of the Year Has Never Been Negative. Here’s What History Says About May
- Exchange-Traded Funds Lower, Equity Futures Mixed Pre-Bell Tuesday Amid Higher Oil Prices, Earnings Deluge
- Investors Worry About Mounting Debt — 7 S&P 500 Companies Owe Most
- S&P 500 Holding Pattern: Mag 7 Earnings Collide With Oil Surge and Fed Fears

**MARKETWATCH**
- ‘I’m not interested in long-term care insurance’: I’d like to retire at 55. How much will I have to pay for healthcare?
- SoFi just set a slew of lending records, but here’s why its stock is falling
- Why this Soros alum is betting on copper and cables over AI chips
- Can Shake Shack’s new sandwich challenge the McRib, one of the most celebrated items in fast-food history?
- $200 oil – and two other scenarios – could tip the world into a recession, says this global bank
- The key reasons why one bank now says U.S. stocks will outperform European equities
- ‘I am her scapegoat’: My mother-in-law squandered all her money. Do we buy her a house so she’s not homeless?
- Actor Patrick Dempsey recalls fond memories of his tiny home town in Maine

**SEEKING_ALPHA**
- Garmin Non-GAAP EPS of $2.08 beats by $0.24, revenue of $1.75B beats by $40M
- Luckin Coffee Non-GAAP EPS of $0.32, revenue of $1.74B
- Vulcan Materials Non-GAAP EPS of $1.35 beats by $0.25, revenue of $1.75B beats by $130M
- Ionis Pharmaceuticals beats top-line and bottom-line estimates; introduces FY26 outlook
- Yum! Brands Non-GAAP EPS of $1.50 beats by $0.11, revenue of $2.06B beats by $20M
- Avis Budget GAAP EPS of -$8.01 misses by $0.51, revenue of $2.53B beats by $90M
- Humana 2026 outlook unchanged due to Star ratings decline

**WSJ_MARKETS**
- Stocks Sink in Broad AI Rout Sparked by China's DeepSeek
- Comex Gold, Silver Settle Lower
- DeepSeek Won't Sink U.S. AI Titans
- Financial Services Roundup: Market Talk
- Arabica Coffee Prices Hit Record on U.S., Colombia Tariff Spat
- Swiss franc, Japanese yen Rise as DeepSeek News Boosts Safe Havens
- Natural Gas Falls on Shifting Weather Forecasts
- Building-Products Distributor QXO Launches Hostile Bid for Beacon


### 🤖 AI TRADING INTELLIGENCE BRIEF
# AI TRADING INTELLIGENCE BRIEF
**Date:** April 29, 2026 | **Pre-Market**

---

## 1. MARKET SENTIMENT
**Bearish-to-Neutral** — Chip stocks sold off hard on OpenAI revenue miss headlines; Fed decision looms today alongside Mag 7 earnings (META, MSFT after close), creating two-way headline risk.

---

## 2. KEY MACRO RISKS
- **Fed Decision Today:** No cut expected, but Powell's tone on tariff inflation vs. growth slowdown will drive volatility
- **OpenAI Revenue Miss Contagion:** AI capex narrative under pressure; semis and hyperscalers vulnerable to further de-rating
- **Oil Spike:** Trump Iran blockade comments pushing crude higher; stagflation fears resurface

---

## 3. CATALYSTS BY SYMBOL
| Symbol | Prior Close Δ | Catalyst |
|--------|---------------|----------|
| **AMD** | -3.41% | Direct hit from OpenAI miss report; competition concerns (Northland downgrade) |
| **NVDA** | -1.59% | OpenAI panic spillover; BofA reset forecast |
| **XLK** | -1.69% | Sector drag from semi weakness |
| **QQQ** | -1.01% | Broad tech de-risking ahead of earnings/Fed |
| **META** | -1.07% | Pre-earnings jitters; analyst flags spending concerns |
| **MSFT** | +1.04% | Relative safety bid; earnings tonight |
| **AAPL** | +1.16% | Defensive rotation within tech |

---

## 4. GAP-UP WATCH (Long ORB Pairing)
**No qualifying gaps (≥0.5%)** — MSFT and AAPL closed green but show 0% pre-market gap. No actionable long setups via gap criteria.

---

## 5. GAP-DOWN WATCH (Short ORB Pairing — Regime B/C Only)
**No qualifying gaps (≥0.5%)** — Prior session moves are NOT reflected in pre-market gaps. AMD's -3.41% was yesterday's close, not today's gap. Pre-market data shows flat gaps across board.

⚠️ **Data Integrity Flag:** Pre-market prices equal prior close for all symbols — likely stale/placeholder data. Verify live gaps at 9:00 AM ET.

---

## 6. PRIORITY LIST

**LONG TRADE:**

---
