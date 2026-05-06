"""
calendar_filter.py — High-impact economic event filter.

Blocks entries on FOMC decision days, CPI release days, and BLS NFP release
days. These events create explosive moves that stop out new positions
immediately. See calendar_feed.TIER_1_TITLE_PATTERNS for the exact match list
(narrowly scoped — Fed-speaker events do NOT block).

Date source (preferred): ForexFactory weekly JSON feed via calendar_feed.py.
Date source (fallback): hardcoded `_HIGH_IMPACT_DATES` below — used only when
the FF feed is unreachable. The hardcoded list is left in place as a safety
net so the filter never goes silent.
"""
from __future__ import annotations
import logging
from datetime import date

logger = logging.getLogger(__name__)

# Imported lazily so calendar_filter remains usable even if calendar_feed
# itself raises on import (e.g., during partial-deploy states).
try:
    from calendar_feed import high_impact_dates_set as _ff_dates
    from calendar_feed import event_name_for_date as _ff_event_name
except Exception:  # pragma: no cover
    _ff_dates = None
    _ff_event_name = None

# FOMC decision days, CPI release days, NFP release days
# These are the three highest-impact scheduled macro events.
# All dates verified from Fed calendar and BLS release schedule.
_HIGH_IMPACT_DATES: set[str] = {
    # ── FOMC 2023 ─────────────────────────────────────────────────────────
    "2023-02-01", "2023-03-22", "2023-05-03", "2023-06-14",
    "2023-07-26", "2023-09-20", "2023-11-01", "2023-12-13",
    # ── CPI 2023 ─────────────────────────────────────────────────────────
    "2023-01-12", "2023-02-14", "2023-03-14", "2023-04-12",
    "2023-05-10", "2023-06-13", "2023-07-12", "2023-08-10",
    "2023-09-13", "2023-10-12", "2023-11-14", "2023-12-12",
    # ── NFP 2023 ─────────────────────────────────────────────────────────
    "2023-01-06", "2023-02-03", "2023-03-10", "2023-04-07",
    "2023-05-05", "2023-06-02", "2023-07-07", "2023-08-04",
    "2023-09-01", "2023-10-06", "2023-11-03", "2023-12-08",
    # ── FOMC 2024 ─────────────────────────────────────────────────────────
    "2024-01-31", "2024-03-20", "2024-05-01", "2024-06-12",
    "2024-07-31", "2024-09-18", "2024-11-07", "2024-12-18",
    # ── CPI 2024 ─────────────────────────────────────────────────────────
    "2024-01-11", "2024-02-13", "2024-03-12", "2024-04-10",
    "2024-05-15", "2024-06-12", "2024-07-11", "2024-08-14",
    "2024-09-11", "2024-10-10", "2024-11-13", "2024-12-11",
    # ── NFP 2024 ─────────────────────────────────────────────────────────
    "2024-01-05", "2024-02-02", "2024-03-08", "2024-04-05",
    "2024-05-03", "2024-06-07", "2024-07-05", "2024-08-02",
    "2024-09-06", "2024-10-04", "2024-11-01", "2024-12-06",
    # ── FOMC 2025 ─────────────────────────────────────────────────────────
    "2025-01-29", "2025-03-19", "2025-05-07", "2025-06-18",
    "2025-07-30", "2025-09-17", "2025-10-29", "2025-12-10",
    # ── CPI 2025 ─────────────────────────────────────────────────────────
    "2025-01-15", "2025-02-12", "2025-03-12", "2025-04-10",
    "2025-05-13", "2025-06-11", "2025-07-15", "2025-08-13",
    "2025-09-10", "2025-10-15", "2025-11-13", "2025-12-10",
    # ── NFP 2025 ─────────────────────────────────────────────────────────
    "2025-01-10", "2025-02-07", "2025-03-07", "2025-04-04",
    "2025-05-02", "2025-06-06", "2025-07-03", "2025-08-01",
    "2025-09-05", "2025-10-03", "2025-11-07", "2025-12-05",
    # ── FOMC 2026 ─────────────────────────────────────────────────────────
    "2026-01-28", "2026-03-18", "2026-04-29", "2026-06-17",
    "2026-07-29", "2026-09-16", "2026-10-28", "2026-12-09",
    # ── CPI 2026 ─────────────────────────────────────────────────────────
    "2026-01-14", "2026-02-11", "2026-03-11", "2026-04-14",
    "2026-05-13", "2026-06-10", "2026-07-15", "2026-08-12",
    "2026-09-10", "2026-10-14", "2026-11-12", "2026-12-10",
    # ── NFP 2026 ─────────────────────────────────────────────────────────
    "2026-01-09", "2026-02-06", "2026-03-06", "2026-04-03",
    "2026-05-08", "2026-06-05", "2026-07-02", "2026-08-07",
    "2026-09-04", "2026-10-02", "2026-11-06", "2026-12-04",
}


def is_high_impact_day(trading_day) -> bool:
    """
    Return True if trading_day is a known high-impact macro event day.

    Consults ForexFactory feed first; falls back to hardcoded list if the
    feed is unreachable or doesn't have the date in scope.
    """
    if isinstance(trading_day, date):
        key = trading_day.isoformat()
    else:
        key = str(trading_day)[:10]

    # Try the live feed first (covers any FOMC/CPI/NFP/GDP/ISM the hardcoded
    # list might be missing or have wrong).
    if _ff_dates is not None:
        try:
            ff_set = _ff_dates()
            if key in ff_set:
                return True
        except Exception as e:
            logger.debug(f"FF feed lookup failed, falling back to static list: {e}")

    # Fallback to hardcoded list. The FF feed only carries the current week,
    # so backtest dates and dates beyond the current week always come from here.
    return key in _HIGH_IMPACT_DATES


class EarningsCalendar:
    """Pre-fetches and caches earnings dates per symbol for backtest + live use.

    Failure-mode contract:
      A yfinance prefetch failure is recorded in `self._failed` and emits a
      WARNING. The cache for the failed symbol is also set to an empty set,
      which means `is_earnings_day()` will return False for that symbol —
      trades get through. This preserves the prior behavior (loud-but-soft
      failure) so a yfinance rate-limit doesn't block all trading; the
      WARNING is what makes it audit-able after the fact. Use
      `prefetch_failures()` to surface the unprotected symbols in EOD reports.
    """

    def __init__(self):
        self._cache: dict[str, set] = {}
        self._failed: set[str] = set()
        self._fetched = False

    def prefetch(self, symbols: list) -> None:
        import yfinance as yf
        for sym in symbols:
            try:
                ed = yf.Ticker(sym).earnings_dates
                if ed is not None and not ed.empty:
                    dates = set()
                    for ts in ed.index:
                        try:
                            d = ts.date() if hasattr(ts, "date") else ts
                            dates.add(d)
                        except Exception:
                            pass
                    self._cache[sym] = dates
                    self._failed.discard(sym)
                else:
                    self._cache[sym] = set()
                    self._failed.discard(sym)
            except Exception as e:
                self._cache[sym] = set()
                self._failed.add(sym)
                logger.warning(
                    f"earnings prefetch failed for {sym}: {e!s}. "
                    f"Earnings-day filter will pass through (no protection) for this symbol "
                    f"until next successful prefetch."
                )
        self._fetched = True
        if self._failed:
            logger.warning(
                f"earnings prefetch summary: {len(self._failed)} unprotected symbol(s): "
                f"{sorted(self._failed)}"
            )

    def is_earnings_day(self, symbol: str, trading_day) -> bool:
        if not self._fetched:
            return False
        if hasattr(trading_day, "date"):
            trading_day = trading_day.date() if callable(trading_day.date) else trading_day
        elif isinstance(trading_day, str):
            from datetime import date as _date
            trading_day = _date.fromisoformat(str(trading_day)[:10])
        return trading_day in self._cache.get(symbol, set())

    def prefetch_failures(self) -> set[str]:
        """Symbols whose earnings data couldn't be fetched (no protection).

        Surface this in EOD reports so unprotected trades through earnings days
        are visible after the fact rather than silent.
        """
        return set(self._failed)


def event_name(trading_day) -> str:
    """
    Return the event type for a given BLOCKED day, or empty string.

    This intentionally only returns labels for days where is_high_impact_day()
    is True (FOMC/CPI/NFP). For broader situational awareness (GDP, ISM, retail,
    etc.) use calendar_feed.events_for_date() directly — those events surface
    in the brief/dashboard but don't block entries.
    """
    if isinstance(trading_day, date):
        key = trading_day.isoformat()
    else:
        key = str(trading_day)[:10]

    if not is_high_impact_day(trading_day):
        return ""

    # If the day is blocked, prefer FF for a specific label (e.g. distinguishes
    # "FOMC Statement" from "Federal Funds Rate" within the same FOMC bucket).
    if _ff_event_name is not None:
        try:
            ff_name = _ff_event_name(trading_day if isinstance(trading_day, date) else key)
            if ff_name:
                return ff_name
        except Exception:
            pass

    if key not in _HIGH_IMPACT_DATES:
        return ""
    # Identify type from month-day pattern for labeling
    for tag, dates in [
        ("FOMC", {"01-31","03-20","05-01","06-12","07-31","09-18","11-07","12-18",
                  "02-01","03-22","05-03","06-14","07-26","09-20","11-01","12-13",
                  "01-29","03-19","05-07","06-18","07-30","09-17","10-29","12-10",
                  "01-28","03-18","04-29","06-17","07-29","09-16","10-28","12-09"}),
        ("CPI",  {"01-11","02-13","03-12","04-10","05-15","06-12","07-11","08-14",
                  "09-11","10-10","11-13","12-11","01-12","02-14","03-14","04-12",
                  "05-10","06-13","07-12","08-10","09-13","10-12","11-14","12-12",
                  "01-15","02-12","03-12","04-10","05-13","06-11","07-15","08-13",
                  "09-10","10-15","11-13","12-10",
                  "01-14","02-11","03-11","04-14","05-13","06-10","07-15","08-12",
                  "09-10","10-14","11-12","12-10"}),
    ]:
        md = key[5:]
        if md in dates:
            return tag
    return "NFP"
