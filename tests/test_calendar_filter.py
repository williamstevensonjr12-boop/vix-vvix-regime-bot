"""
test_calendar_filter.py — unit tests for the calendar / earnings filter.

Focused on the prefetch failure-mode fix (2026-05-02 audit). Prior behavior
silently set the cache to empty on yfinance failure, turning earnings-day
blocking into "no protection" without any error signal. The fix tracks
failures explicitly, logs a WARNING, and exposes the failed-symbols set
via prefetch_failures().
"""
from __future__ import annotations
import logging
import os
import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

import pandas as pd
import pytest

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO))
os.chdir(REPO)

from calendar_filter import EarningsCalendar


class TestEarningsPrefetchFailureMode:
    def _ticker_factory(self, fail_for: set[str], dates_for: dict[str, list[str]] | None = None):
        """Build a fake yf.Ticker that raises for `fail_for` symbols and returns
        a DataFrame with `dates_for` for the rest."""
        dates_for = dates_for or {}

        def _factory(sym):
            t = MagicMock()
            if sym in fail_for:
                # Accessing the property raises — mirrors yfinance rate-limit / network errors
                type(t).earnings_dates = property(
                    lambda self_: (_ for _ in ()).throw(RuntimeError("yfinance rate-limited"))
                )
                return t
            d = dates_for.get(sym, [])
            if d:
                idx = pd.DatetimeIndex([pd.Timestamp(s, tz="UTC") for s in d])
                t.earnings_dates = pd.DataFrame(index=idx, data={"event": ["earnings"] * len(idx)})
            else:
                t.earnings_dates = pd.DataFrame()
            return t
        return _factory

    def test_failed_symbols_are_tracked(self):
        cal = EarningsCalendar()
        with patch("yfinance.Ticker", side_effect=self._ticker_factory(fail_for={"BADSYM"})):
            cal.prefetch(["BADSYM", "GOODSYM"])
        assert "BADSYM" in cal.prefetch_failures()
        assert "GOODSYM" not in cal.prefetch_failures()

    def test_failed_symbol_logs_warning(self, caplog):
        cal = EarningsCalendar()
        with caplog.at_level(logging.WARNING, logger="calendar_filter"):
            with patch("yfinance.Ticker", side_effect=self._ticker_factory(fail_for={"BADSYM"})):
                cal.prefetch(["BADSYM"])
        # At least one record mentions the failed symbol + "no protection"
        assert any("BADSYM" in r.message and "no protection" in r.message
                   for r in caplog.records), \
            "expected per-symbol WARNING with 'no protection' wording"

    def test_failure_summary_warning_lists_all_failed(self, caplog):
        cal = EarningsCalendar()
        with caplog.at_level(logging.WARNING, logger="calendar_filter"):
            with patch("yfinance.Ticker",
                       side_effect=self._ticker_factory(fail_for={"AAA", "BBB"})):
                cal.prefetch(["AAA", "BBB", "CCC"])
        # A summary line should mention both failed symbols
        summary_logs = [r.message for r in caplog.records if "unprotected symbol" in r.message]
        assert summary_logs, "expected a 'unprotected symbol(s)' summary warning"
        assert "AAA" in summary_logs[-1] and "BBB" in summary_logs[-1]

    def test_no_warning_when_all_succeed(self, caplog):
        cal = EarningsCalendar()
        with caplog.at_level(logging.WARNING, logger="calendar_filter"):
            with patch("yfinance.Ticker",
                       side_effect=self._ticker_factory(
                           fail_for=set(),
                           dates_for={"GOODSYM": ["2024-04-15 12:00"]})):
                cal.prefetch(["GOODSYM"])
        assert not cal.prefetch_failures()
        # No "no protection" warnings
        assert not any("no protection" in r.message for r in caplog.records)

    def test_recovery_clears_failed_flag(self):
        """If a symbol fails on first prefetch but succeeds on a retry, the failed
        flag should be cleared — the symbol is now protected again."""
        cal = EarningsCalendar()
        # First prefetch fails
        with patch("yfinance.Ticker", side_effect=self._ticker_factory(fail_for={"FLAKY"})):
            cal.prefetch(["FLAKY"])
        assert "FLAKY" in cal.prefetch_failures()
        # Second prefetch succeeds
        with patch("yfinance.Ticker",
                   side_effect=self._ticker_factory(
                       fail_for=set(),
                       dates_for={"FLAKY": ["2024-04-15 12:00"]})):
            cal.prefetch(["FLAKY"])
        assert "FLAKY" not in cal.prefetch_failures()

    def test_is_earnings_day_unchanged_for_failed_symbol(self):
        """Behavior contract: `is_earnings_day()` returns False for failed symbols
        (preserves prior behavior — failures don't block trades, just become loud)."""
        cal = EarningsCalendar()
        with patch("yfinance.Ticker", side_effect=self._ticker_factory(fail_for={"BADSYM"})):
            cal.prefetch(["BADSYM"])
        from datetime import date
        assert cal.is_earnings_day("BADSYM", date(2024, 4, 15)) is False
