"""
research.py — AI-powered pre-market research pipeline.

Pipeline:
  1. Pull market data via yfinance (VIX, VVIX, SPY, active universe)
  2. Pull headlines from Google News RSS + FinancialJuice RSS
  3. Send everything to Claude API for AI Trading Intelligence Brief
  4. Append full report to memory/RESEARCH-LOG.md
  5. Push to GitHub

Usage:
  python research.py
"""
from __future__ import annotations
import os
import sys
import json
import logging
from datetime import datetime, date
from zoneinfo import ZoneInfo
from pathlib import Path
import urllib.request
import ssl
import xml.etree.ElementTree as ET

_SSL_CTX = ssl.create_default_context()
_SSL_CTX.check_hostname = False
_SSL_CTX.verify_mode = ssl.CERT_NONE

import pandas as pd
import yfinance as yf

logger = logging.getLogger(__name__)
ET_TZ = ZoneInfo("America/New_York")

REPO_ROOT = Path(__file__).parent
RESEARCH_LOG = REPO_ROOT / "memory" / "RESEARCH-LOG.md"
TRADE_LOG    = REPO_ROOT / "memory" / "TRADE-LOG.md"

# Long-bias universe — pulls from config so it stays in sync with the live trade path
import config as _bot_config
UNIVERSE = list(_bot_config.MOMENTUM_UNIVERSE)
# Short-bias universe (high-VIX-beta names — bot SHORT_UNIVERSE)
SHORT_UNIVERSE = list(_bot_config.SHORT_UNIVERSE)
VOL_TICKERS = {"VIX": "^VIX", "VVIX": "^VVIX", "VIX3M": "^VIX3M"}

# Gap threshold — matches config.GAP_ALIGNMENT_THRESHOLD so the brief reports the
# same "qualifying" gaps that the bot actually trades. (Was hardcoded 0.5% — out
# of sync with bot's 0.8% threshold; fixed 2026-04-30.)
GAP_THRESHOLD_PCT = _bot_config.GAP_ALIGNMENT_THRESHOLD * 100


# ── 1. Market data ────────────────────────────────────────────────────────────

def fetch_market_data() -> dict:
    """Pull price/vol snapshot via yfinance."""
    data = {}

    # Volatility
    for name, ticker in VOL_TICKERS.items():
        try:
            t = yf.Ticker(ticker)
            hist = t.history(period="2d")
            if not hist.empty:
                data[name] = round(float(hist["Close"].iloc[-1]), 2)
                prev = float(hist["Close"].iloc[-2]) if len(hist) > 1 else data[name]
                data[f"{name}_chg_pct"] = round((data[name] - prev) / prev * 100, 2)
        except Exception as e:
            logger.warning(f"Vol fetch failed {name}: {e}")
            data[name] = None

    # Universe prices + pre-market gaps
    stocks = {}
    for sym in UNIVERSE:
        try:
            t = yf.Ticker(sym)
            hist = t.history(period="5d")
            if not hist.empty:
                # `prev` must be the most recent COMPLETED daily close (yesterday).
                # During pre-market, yfinance has no today bar yet → iloc[-1] is
                # already yesterday → using iloc[-2] under-reaches by one day.
                # During RTH, iloc[-1] is today's partial bar. Either way, filter
                # to dates strictly before today (ET) and take the last entry.
                today_et = datetime.now(ET_TZ).date()
                hist_idx = hist.index
                if hist_idx.tz is None:
                    hist_idx = hist_idx.tz_localize("UTC").tz_convert(ET_TZ)
                else:
                    hist_idx = hist_idx.tz_convert(ET_TZ)
                completed_mask = pd.Series(
                    [d.date() < today_et for d in hist_idx],
                    index=hist.index,
                )
                completed = hist[completed_mask]
                if completed.empty:
                    continue
                close = float(hist["Close"].iloc[-1])
                prev  = float(completed["Close"].iloc[-1])
                # Pre-market price — pull 1-min bars with prepost=True and take
                # the last bar BEFORE today's 9:30 ET open. Falls back to fast_info
                # if extended-hours data unavailable. (Bug fix 2026-04-30: was using
                # fast_info.last_price, which during regular hours returns the
                # current quote, not a pre-market price — making "gap" calculation
                # silently meaningless.)
                pre_price = None
                try:
                    today_et = datetime.now(ET_TZ).date()
                    intraday = t.history(period="1d", interval="1m", prepost=True)
                    if not intraday.empty:
                        # Localize to ET if needed
                        if intraday.index.tz is None:
                            intraday.index = intraday.index.tz_localize("UTC").tz_convert(ET_TZ)
                        else:
                            intraday.index = intraday.index.tz_convert(ET_TZ)
                        # Pre-market = bars before 9:30 ET on today's date
                        cutoff = pd.Timestamp(f"{today_et} 09:30:00", tz=ET_TZ)
                        pre_bars = intraday[intraday.index < cutoff]
                        if not pre_bars.empty:
                            pre_price = float(pre_bars["Close"].iloc[-1])
                except Exception:
                    pre_price = None
                # Fallback: fast_info if pre-market data unavailable (still useful
                # during regular hours as "current quote vs prior close" intraday move)
                if not pre_price:
                    try:
                        fi = getattr(t, "fast_info", None)
                        if fi is not None:
                            pre_price = getattr(fi, "last_price", None)
                    except Exception:
                        pre_price = None
                # Gap = (pre_price - PRIOR DAY's close) / PRIOR DAY's close.
                # Bug fix 2026-04-30: was dividing by latest close, which during intraday
                # equals current quote → gap=~0% even on real gap days. Use `prev` instead.
                gap_pct = None
                if pre_price and prev:
                    gap_pct = round((float(pre_price) - prev) / prev * 100, 2)
                # Display price prefers pre-market when available (more current
                # than yesterday's close); chg_pct tracks display price vs prev.
                display_price = float(pre_price) if pre_price else close
                stocks[sym] = {
                    "price": round(display_price, 2),
                    "chg_pct": round((display_price - prev) / prev * 100, 2),
                    "pre_price": round(float(pre_price), 2) if pre_price else None,
                    "gap_pct": gap_pct,
                }
        except Exception as e:
            logger.warning(f"Stock fetch failed {sym}: {e}")

    data["stocks"] = stocks
    return data


def classify_gaps(stocks: dict) -> dict:
    """Bucket symbols into gap-up / gap-down / flat lists for the AI brief."""
    gap_up: list = []
    gap_down: list = []
    flat: list = []
    for sym, d in stocks.items():
        gp = d.get("gap_pct")
        if gp is None:
            continue
        if gp >= GAP_THRESHOLD_PCT:
            gap_up.append((sym, gp))
        elif gp <= -GAP_THRESHOLD_PCT:
            gap_down.append((sym, gp))
        else:
            flat.append((sym, gp))
    gap_up.sort(key=lambda x: -x[1])
    gap_down.sort(key=lambda x: x[1])
    return {"gap_up": gap_up, "gap_down": gap_down, "flat": flat}


# ── 2. News headlines ─────────────────────────────────────────────────────────

def _parse_rss(url: str, max_items: int = 8) -> list[str]:
    """Fetch RSS feed and return list of headline strings."""
    headlines = []
    try:
        req = urllib.request.Request(url, headers={
            "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36",
            "Accept": "application/rss+xml, application/xml, text/xml, */*",
        })
        with urllib.request.urlopen(req, timeout=10, context=_SSL_CTX) as resp:
            raw = resp.read()
        # Strip BOM and non-XML leading content
        raw = raw.lstrip(b'\xef\xbb\xbf').lstrip()
        if not raw.startswith(b'<'):
            # Try to find the start of XML
            idx = raw.find(b'<?xml')
            if idx == -1:
                idx = raw.find(b'<rss')
            if idx != -1:
                raw = raw[idx:]
        tree = ET.fromstring(raw)
        for item in tree.iter("item"):
            title = item.findtext("title", "").strip()
            if title:
                headlines.append(title)
            if len(headlines) >= max_items:
                break
    except Exception as e:
        logger.warning(f"RSS fetch failed {url}: {e}")
    return headlines


def fetch_yahoo_news(symbols: list[str]) -> dict[str, list[str]]:
    """Pull news from Yahoo Finance via yfinance for each symbol."""
    yahoo_news = {}
    for sym in symbols:
        try:
            t = yf.Ticker(sym)
            news = t.news
            if news:
                headlines = []
                for article in news[:6]:
                    content = article.get("content", {})
                    title = content.get("title", "") if isinstance(content, dict) else ""
                    if not title:
                        title = article.get("title", "")
                    if title:
                        headlines.append(title)
                if headlines:
                    yahoo_news[sym] = headlines
        except Exception as e:
            logger.warning(f"Yahoo Finance news failed {sym}: {e}")
    return yahoo_news


def fetch_wire_headlines() -> dict[str, list[str]]:
    """Pull live headlines from MarketWatch, Reuters, and Seeking Alpha RSS feeds."""
    feeds = {
        "marketwatch": "https://feeds.marketwatch.com/marketwatch/topstories/",
        "reuters_markets": "https://feeds.reuters.com/reuters/businessNews",
        "seeking_alpha": "https://seekingalpha.com/market_currents.xml",
        "wsj_markets": "https://feeds.a.dj.com/rss/RSSMarketsMain.xml",
    }
    results = {}
    for name, url in feeds.items():
        headlines = _parse_rss(url, max_items=8)
        if headlines:
            results[name] = headlines
            logger.info(f"  {name}: {len(headlines)} headlines")
        else:
            logger.warning(f"  {name}: no headlines returned")
    return results


def fetch_headlines(symbols: list[str]) -> dict[str, list[str]]:
    """Pull headlines from Google News + Yahoo Finance + FinancialJuice."""
    all_headlines = {}

    # Google News — market overview
    market_feed = "https://news.google.com/rss/search?q=stock+market+today&hl=en-US&gl=US&ceid=US:en"
    gn_market = _parse_rss(market_feed, max_items=10)
    if gn_market:
        all_headlines["google_news_market"] = gn_market

    # Google News — per symbol
    for sym in symbols:
        feed = f"https://news.google.com/rss/search?q={sym}+stock&hl=en-US&gl=US&ceid=US:en"
        headlines = _parse_rss(feed, max_items=5)
        if headlines:
            all_headlines[f"google_{sym}"] = headlines

    # Yahoo Finance — per symbol news feed
    logger.info("Fetching Yahoo Finance news...")
    yahoo = fetch_yahoo_news(symbols)
    for sym, items in yahoo.items():
        all_headlines[f"yahoo_{sym}"] = items

    # Wire feeds — MarketWatch, Reuters, Seeking Alpha, WSJ
    logger.info("Fetching wire feeds (MarketWatch, Reuters, Seeking Alpha, WSJ)...")
    wire = fetch_wire_headlines()
    all_headlines.update(wire)

    return all_headlines


# ── 3. Claude API — AI Trading Intelligence Brief ─────────────────────────────

def generate_brief(market_data: dict, headlines: dict, regime_summary: str) -> str:
    """Call Claude API and return the AI Trading Intelligence Brief."""
    api_key = os.environ.get("ANTHROPIC_API_KEY", "")
    if not api_key:
        return "⚠️ ANTHROPIC_API_KEY not set — skipping AI brief."

    try:
        import anthropic
    except ImportError:
        return "⚠️ anthropic package not installed — run: pip install anthropic"

    client = anthropic.Anthropic(api_key=api_key)

    # Build context payload
    stocks_str = "\n".join(
        f"  {sym}: ${d['price']} ({d['chg_pct']:+.2f}%) | "
        f"pre=${d.get('pre_price', 'n/a')} gap={d.get('gap_pct', 'n/a')}%"
        for sym, d in market_data.get("stocks", {}).items()
    )

    # Today's macro events (from ForexFactory feed). Tier-1 (FOMC/CPI/NFP) → bot
    # blocks entries. Tier-2 (GDP/ISM/retail/PCE/claims) → don't block but warn.
    events_str = "(none scheduled)"
    block_events_today = []
    try:
        from calendar_feed import events_for_date, usd_blocking_events
        today_et = datetime.now(ET_TZ).date()
        all_today = events_for_date(today_et)
        if all_today:
            lines = []
            for ev in all_today:
                tag = "BLOCKS ENTRIES" if any(p.lower() in (ev.get("title") or "").lower()
                    for p in ("FOMC","Federal Funds","Fed Chair","CPI","Non-Farm","NFP")) else "watch"
                lines.append(f"  {ev.get('et_time'):>8}  [{ev.get('impact'):>6}]  {ev.get('title')}"
                             f"  | forecast={ev.get('forecast') or '—'}  prev={ev.get('previous') or '—'}  ({tag})")
            events_str = "\n".join(lines)
        # Track blocking events for the prompt's risk section
        for ev in usd_blocking_events():
            try:
                ts = ev.get("date") or ""
                ev_dt = datetime.fromisoformat(ts.replace("Z","+00:00")).astimezone(ET_TZ)
                if ev_dt.date() == today_et:
                    block_events_today.append(f"{ev.get('title')} @ {ev_dt.strftime('%H:%M ET')}")
            except Exception:
                pass
    except Exception as e:
        logger.warning(f"calendar_feed events fetch failed: {e}")
    vol_str = (
        f"  VIX: {market_data.get('VIX')} ({market_data.get('VIX_chg_pct',0):+.2f}%)\n"
        f"  VVIX: {market_data.get('VVIX')} ({market_data.get('VVIX_chg_pct',0):+.2f}%)\n"
        f"  VIX3M: {market_data.get('VIX3M')}"
    )

    gap_buckets = classify_gaps(market_data.get("stocks", {}))
    gap_up_str = ", ".join(f"{s} ({g:+.2f}%)" for s, g in gap_buckets["gap_up"]) or "(none)"
    gap_down_str = ", ".join(f"{s} ({g:+.2f}%)" for s, g in gap_buckets["gap_down"]) or "(none)"
    short_uni_str = ", ".join(SHORT_UNIVERSE)

    news_str = ""
    for source, items in headlines.items():
        news_str += f"\n[{source.upper()}]\n" + "\n".join(f"  - {h}" for h in items)

    prompt = f"""You are an expert quantitative trading analyst providing a pre-market briefing for a VIX/VVIX regime-based ORB trading bot. The bot now trades both LONG (bullish gap + ORB high break) and SHORT (bearish gap + ORB low break, Regime B/C only on high-VIX-beta names).

VOLATILITY SNAPSHOT:
{vol_str}

UNIVERSE PRICES + PRE-MARKET GAPS (gap = pre-market vs prior close):
{stocks_str}

GAP-ALIGNED CANDIDATES (≥{GAP_THRESHOLD_PCT}% threshold):
- Gap UP (long ORB candidates):  {gap_up_str}
- Gap DOWN (short ORB candidates, only valid in Regime B/C): {gap_down_str}
- Bot SHORT universe: {short_uni_str}

REGIME ENGINE OUTPUT:
{regime_summary}

TODAY'S MACRO EVENTS (from ForexFactory):
{events_str}
{('⚠ BOT WILL BLOCK ENTRIES TODAY due to: ' + ', '.join(block_events_today)) if block_events_today else 'No tier-1 blocking events today.'}

TODAY'S HEADLINES:
{news_str}

Provide a concise AI TRADING INTELLIGENCE BRIEF with exactly these 6 sections:

1. MARKET SENTIMENT: Overall tone (Bullish / Neutral / Bearish) with one sentence rationale.

2. KEY MACRO RISKS: 2-3 bullets of the biggest risks to watch today.

3. CATALYSTS BY SYMBOL: One line per notable mover (gap-up or gap-down). For each name in the gap-up/gap-down lists, name the catalyst or "no clear catalyst — likely sympathy/positioning". Flag any earnings today.

4. GAP-UP WATCH (long ORB pairing): For each gap-up name, rate conviction High/Med/Low based on whether the catalyst supports continuation (vs. likely-fade). Call out any that look like fakes.

5. GAP-DOWN WATCH (short ORB pairing — only fires if regime is B/C): For each gap-down name, rate conviction High/Med/Low and call out any that have likely-bounce setups (oversold dip-buyers, support nearby) where the short would get squeezed.

6. PRIORITY LIST:
   - LONG TRADE: [gap-up names with high-conviction catalyst — bot will pair with ORB-high break]
   - SHORT TRADE (Regime B/C only): [gap-down names with high-conviction catalyst — bot will pair with ORB-low break]
   - AVOID: [symbols where the gap is unreliable, regardless of direction]
   - REGIME: which regime (A/B/C) is favored and why

Be direct, specific, actionable. No fluff. Under 400 words total."""

    message = client.messages.create(
        model="claude-opus-4-5",
        max_tokens=600,
        messages=[{"role": "user", "content": prompt}]
    )

    return message.content[0].text


# ── 4. Write research log ─────────────────────────────────────────────────────

def write_research_log(today: str, market_data: dict, headlines: dict, brief: str):
    """Append today's full research entry to memory/RESEARCH-LOG.md."""
    stocks = market_data.get("stocks", {})
    stocks_str = "\n".join(
        f"  {sym}: ${d['price']} ({d['chg_pct']:+.2f}%) | pre=${d.get('pre_price', 'n/a')} gap={d.get('gap_pct', 'n/a')}%"
        for sym, d in stocks.items()
    )

    gap_buckets = classify_gaps(stocks)
    gap_up_str = ", ".join(f"{s} ({g:+.2f}%)" for s, g in gap_buckets["gap_up"]) or "(none)"
    gap_down_str = ", ".join(f"{s} ({g:+.2f}%)" for s, g in gap_buckets["gap_down"]) or "(none)"

    news_str = ""
    for source, items in headlines.items():
        news_str += f"\n**{source.upper()}**\n" + "\n".join(f"- {h}" for h in items) + "\n"

    # Today's macro events (FF feed)
    events_md = "(none scheduled)"
    block_note = ""
    try:
        from calendar_feed import events_for_date, usd_blocking_events
        today_et = datetime.now(ET_TZ).date()
        evs = events_for_date(today_et)
        if evs:
            lines = []
            for ev in evs:
                lines.append(f"- {ev.get('et_time')}  [{ev.get('impact')}]  **{ev.get('title')}**"
                             f"  forecast: {ev.get('forecast') or '—'}  prev: {ev.get('previous') or '—'}")
            events_md = "\n".join(lines)
        blocks = []
        for ev in usd_blocking_events():
            try:
                ts = ev.get("date") or ""
                d = datetime.fromisoformat(ts.replace("Z","+00:00")).astimezone(ET_TZ)
                if d.date() == today_et:
                    blocks.append(f"{ev.get('title')} @ {d.strftime('%H:%M ET')}")
            except Exception:
                pass
        if blocks:
            block_note = "\n\n⚠️ **Bot will block ORB entries today (tier-1 macro):** " + ", ".join(blocks)
    except Exception:
        pass

    entry = f"""
---
## {today} — Pre-Market Research

**Volatility**
- VIX: {market_data.get('VIX')} ({market_data.get('VIX_chg_pct', 0):+.2f}%)
- VVIX: {market_data.get('VVIX')} ({market_data.get('VVIX_chg_pct', 0):+.2f}%)
- VIX3M: {market_data.get('VIX3M')}

**Today's Macro Events (ForexFactory)**
{events_md}{block_note}

**Universe Prices + Pre-Market Gaps**
{stocks_str}

**Gap-Aligned Candidates (≥{GAP_THRESHOLD_PCT}% threshold)**
- Gap UP (long ORB pairing): {gap_up_str}
- Gap DOWN (short ORB pairing, B/C only): {gap_down_str}

**Headlines**
{news_str}

### 🤖 AI TRADING INTELLIGENCE BRIEF
{brief}

---
"""
    RESEARCH_LOG.parent.mkdir(parents=True, exist_ok=True)
    with open(RESEARCH_LOG, "a") as f:
        f.write(entry)
    logger.info(f"Research log updated → {RESEARCH_LOG}")


# ── 5. Main ───────────────────────────────────────────────────────────────────

def run_research():
    logging.basicConfig(level=logging.INFO, format="%(asctime)s | %(levelname)s | %(message)s")
    today = date.today().isoformat()
    now = datetime.now(ET_TZ).strftime("%H:%M ET")

    logger.info(f"=== Pre-market research {today} {now} ===")

    # Get regime summary from bot
    regime_summary = "Regime engine not available — check main.py regime-status"
    try:
        import subprocess
        result = subprocess.run(
            ["python", "main.py", "regime-status"],
            capture_output=True, text=True, timeout=30,
            cwd=str(REPO_ROOT)
        )
        if result.returncode == 0:
            regime_summary = result.stdout.strip()[:500]
    except Exception as e:
        logger.warning(f"Regime status failed: {e}")

    logger.info("Fetching market data...")
    market_data = fetch_market_data()

    logger.info("Fetching headlines...")
    headlines = fetch_headlines(["NVDA", "AMD", "AMZN", "META", "SPY"])

    logger.info("Generating AI Trading Intelligence Brief...")
    brief = generate_brief(market_data, headlines, regime_summary)

    write_research_log(today, market_data, headlines, brief)

    # Print brief to console
    print("\n" + "="*60)
    print("AI TRADING INTELLIGENCE BRIEF")
    print("="*60)
    print(brief)
    print("="*60 + "\n")

    logger.info("Research complete.")


if __name__ == "__main__":
    run_research()
