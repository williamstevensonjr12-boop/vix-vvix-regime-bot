"""
calendar_feed.py — ForexFactory economic calendar feed.

Pulls the public weekly JSON feed from ForexFactory and exposes structured
high-impact USD events (FOMC, CPI, NFP, GDP, retail sales, ISM, Fed speak).

Used by:
  - calendar_filter.py — dynamic event-day blocking (replaces stale hardcoded
    FOMC/CPI/NFP date lists)
  - research.py / pre-market routine — surface today's macro events in the brief
  - dashboard — "next 5 high-impact events" panel (optional)

Cache: feed is fetched at most once per hour, persisted at /tmp/ff_calendar_cache.json.
Feed URL: https://nfs.faireconomy.media/ff_calendar_thisweek.json (public, free)

Failure mode: if the feed is unreachable, callers should fall back to whatever
they had before (e.g., hardcoded date sets in calendar_filter.py).
"""
from __future__ import annotations
import json
import logging
import time
import urllib.request
import ssl
from datetime import datetime, date
from pathlib import Path
from zoneinfo import ZoneInfo

logger = logging.getLogger(__name__)
ET = ZoneInfo("America/New_York")

FEED_URL = "https://nfs.faireconomy.media/ff_calendar_thisweek.json"
CACHE_PATH = Path("/tmp/ff_calendar_cache.json")
CACHE_TTL_SECONDS = 60 * 60  # 1 hour

# Country codes that affect US equity trading. USD is primary; we also surface
# major foreign central banks because they can move SPY/QQQ pre-market.
EQUITY_RELEVANT_COUNTRIES = {"USD", "EUR", "GBP", "CNY", "JPY"}

# BLOCKING patterns — events on these days warrant blocking entries.
# Scope: FOMC decision days, CPI, BLS NFP only. Substring "FOMC" alone matches
# every "FOMC Member X Speaks" event (Fed has speakers most weekdays), which
# would block the bot constantly — so patterns are scoped to the actual
# decision titles, with TIER_1_DENY_PATTERNS catching false positives.
TIER_1_TITLE_PATTERNS = (
    "FOMC Statement", "FOMC Press Conference",
    "Federal Funds Rate",
    "CPI", "Core CPI",
    "Non-Farm Employment Change", "Non-Farm Payrolls", "NFP",
)
TIER_1_DENY_PATTERNS = (
    "ADP",                 # ADP NFP preview, not the BLS release
    "FOMC Member",         # Fed speakers, not policy decisions
    "FOMC Meeting Minutes",  # ~3-week-old summary; informational, not a decision
)

# WATCHLIST patterns — events worth surfacing in the brief/dashboard for
# situational awareness, but NOT blocking entries. These move the tape but
# don't reliably create the fake-breakout pattern that justifies a hard block.
# Used by upcoming_events() / events_for_date() — NOT by the blocking helper.
TIER_2_TITLE_PATTERNS = (
    "Core PCE", "PCE Price Index",
    "Unemployment Rate", "Unemployment Claims",
    "GDP", "Retail Sales", "Core Retail Sales",
    "ISM Manufacturing", "ISM Services",
    "Treasury Refunding",
)


def _is_tier_1(title: str) -> bool:
    """Tier-1: events that warrant blocking entries (FOMC decision/CPI/NFP).

    Deny-list runs first so titles like "FOMC Member Bowman Speaks" or
    "ADP Non-Farm Employment Change" don't fall through to the broad pattern.
    """
    t = title.lower()
    if any(d.lower() in t for d in TIER_1_DENY_PATTERNS):
        return False
    return any(pat.lower() in t for pat in TIER_1_TITLE_PATTERNS)


def _is_tier_2(title: str) -> bool:
    """Tier-2: surface in brief/dashboard but don't block entries."""
    return any(pat.lower() in title.lower() for pat in TIER_2_TITLE_PATTERNS)


def _is_watchlist(title: str) -> bool:
    """Anything we surface (tier-1 OR tier-2)."""
    return _is_tier_1(title) or _is_tier_2(title)


def _fetch_raw() -> list[dict]:
    """Fetch the FF JSON feed. Raises on network/parse error."""
    ctx = ssl.create_default_context()
    ctx.check_hostname = False
    ctx.verify_mode = ssl.CERT_NONE
    req = urllib.request.Request(FEED_URL, headers={"User-Agent": "Mozilla/5.0"})
    with urllib.request.urlopen(req, context=ctx, timeout=10) as r:
        return json.loads(r.read())


def fetch_events(force: bool = False) -> list[dict]:
    """
    Return all events from the FF weekly feed (raw schema).

    Each event has: title, country, date (ISO with TZ offset), impact,
    forecast, previous.

    Cached to /tmp for CACHE_TTL_SECONDS to avoid hammering FF on every call.
    Set force=True to bypass cache.
    """
    if not force and CACHE_PATH.exists():
        age = time.time() - CACHE_PATH.stat().st_mtime
        if age < CACHE_TTL_SECONDS:
            try:
                return json.loads(CACHE_PATH.read_text())
            except Exception:
                pass
    try:
        events = _fetch_raw()
        CACHE_PATH.write_text(json.dumps(events))
        return events
    except Exception as e:
        logger.warning(f"FF feed fetch failed: {e}")
        # Try stale cache as fallback
        if CACHE_PATH.exists():
            try:
                return json.loads(CACHE_PATH.read_text())
            except Exception:
                pass
        return []


def _filter_usd(events: list[dict], match) -> list[dict]:
    out = []
    for ev in events:
        if (ev.get("country") or "") != "USD":
            continue
        if match(ev):
            out.append(ev)
    out.sort(key=lambda e: e.get("date") or "")
    return out


def usd_blocking_events(force: bool = False) -> list[dict]:
    """USD events that warrant blocking ORB entries (tier-1: FOMC/CPI/NFP)."""
    return _filter_usd(
        fetch_events(force=force),
        lambda ev: _is_tier_1(ev.get("title") or "")
    )


def usd_watchlist_events(force: bool = False) -> list[dict]:
    """USD events worth surfacing (tier-1 + tier-2 + any High-impact)."""
    return _filter_usd(
        fetch_events(force=force),
        lambda ev: _is_watchlist(ev.get("title") or "") or (ev.get("impact") == "High")
    )


# Backwards-compatibility alias — historical name used by some callers.
def usd_high_impact_events(force: bool = False) -> list[dict]:
    return usd_watchlist_events(force=force)


def high_impact_dates_set(force: bool = False) -> set[str]:
    """
    Return YYYY-MM-DD strings (ET) on which a tier-1 USD event occurs.
    Drop-in compatible with calendar_filter._HIGH_IMPACT_DATES.
    Only includes events that BLOCK entries (FOMC/CPI/NFP) — not the broader
    watchlist that goes into briefs/dashboard.
    """
    out = set()
    for ev in usd_blocking_events(force=force):
        ts = ev.get("date") or ""
        if not ts:
            continue
        try:
            dt = datetime.fromisoformat(ts.replace("Z", "+00:00"))
            dt_et = dt.astimezone(ET)
            out.add(dt_et.date().isoformat())
        except Exception:
            continue
    return out


def events_for_date(target_date, force: bool = False) -> list[dict]:
    """Return USD events occurring on the given date (ET), tier-1 filtered."""
    if isinstance(target_date, str):
        target_date = date.fromisoformat(target_date[:10])
    out = []
    for ev in usd_high_impact_events(force=force):
        ts = ev.get("date") or ""
        try:
            dt_et = datetime.fromisoformat(ts.replace("Z", "+00:00")).astimezone(ET)
            if dt_et.date() == target_date:
                ev_copy = dict(ev)
                ev_copy["et_time"] = dt_et.strftime("%H:%M ET")
                out.append(ev_copy)
        except Exception:
            continue
    return out


def event_name_for_date(target_date) -> str:
    """Return 'FOMC' / 'CPI' / 'NFP' / etc. tag for the given date, or ''."""
    events = events_for_date(target_date)
    if not events:
        return ""
    titles = " ".join(e.get("title", "") for e in events).upper()
    if "FOMC" in titles or "FEDERAL FUNDS" in titles:
        return "FOMC"
    if "CPI" in titles:
        return "CPI"
    if "NON-FARM" in titles or "NFP" in titles:
        return "NFP"
    if "GDP" in titles:
        return "GDP"
    if "RETAIL SALES" in titles:
        return "Retail Sales"
    if "ISM" in titles:
        return "ISM"
    if "UNEMPLOYMENT CLAIMS" in titles:
        return "Jobless Claims"
    return events[0].get("title", "")[:30]


if __name__ == "__main__":
    # Quick CLI: print today's events + this week's high-impact USD events
    today = datetime.now(ET).date()
    print(f"=== Today's USD high-impact events ({today}) ===")
    for ev in events_for_date(today):
        print(f"  {ev.get('et_time'):>8}  [{ev.get('impact'):>6}]  {ev.get('title')}"
              f"  | forecast={ev.get('forecast') or '—'}  prev={ev.get('previous') or '—'}")
    print()
    print("=== This week's USD high-impact events ===")
    for ev in usd_high_impact_events():
        ts = ev.get("date") or ""
        try:
            dt_et = datetime.fromisoformat(ts.replace("Z", "+00:00")).astimezone(ET)
            stamp = dt_et.strftime("%a %m-%d %H:%M ET")
        except Exception:
            stamp = ts
        print(f"  {stamp:<22}  [{ev.get('impact'):>6}]  {ev.get('title')}")
