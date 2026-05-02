"""
test_indicators.py — pytest unit tests for the indicators module.

Initial coverage focused on calculate_avg_volume_same_time_of_day, which is
the centerpiece of the 2026-05-02 audit's Phase 2 (RVOL fix). The simple
rolling-20 calculate_avg_volume is already covered indirectly via
test_entry_gates.py — not duplicated here.

Run from repo/:
    pytest tests/test_indicators.py -v
"""
from __future__ import annotations
import os
import sys
from pathlib import Path

import pandas as pd
import pytest

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO))
os.chdir(REPO)

import indicators as ind


def _make_bars(specs):
    """Build a 5-min-bars DataFrame from a list of (timestamp_str, volume) tuples."""
    rows = []
    for ts_str, vol in specs:
        ts = pd.Timestamp(ts_str, tz="America/New_York")
        rows.append({"timestamp": ts, "volume": float(vol), "open": 1.0, "high": 1.0, "low": 1.0, "close": 1.0})
    df = pd.DataFrame(rows).set_index("timestamp")
    return df


class TestSameTimeOfDayBaseline:
    def test_empty_returns_empty(self):
        out = ind.calculate_avg_volume_same_time_of_day(pd.DataFrame())
        assert out.empty

    def test_falls_back_when_no_prior_history(self):
        """First day with no history → falls back to rolling-20 simple avg."""
        bars = _make_bars([
            ("2026-04-20 09:30", 1000),
            ("2026-04-20 09:35", 1500),
            ("2026-04-20 09:40", 2000),
        ])
        out = ind.calculate_avg_volume_same_time_of_day(bars, lookback_days=14, min_obs=5)
        # All values should equal the rolling-20 simple avg (which is just cumulative mean here)
        expected = ind.calculate_avg_volume(bars)
        assert list(out.values) == list(expected.values)

    def test_uses_same_tod_median_when_history_sufficient(self):
        """Given 5+ days of history at a given tod, returns median of those days."""
        rows = []
        # 6 days of history at 09:30 with volumes [1000, 1100, 1200, 1300, 1400, 1500] → median 1250
        for i, vol in enumerate([1000, 1100, 1200, 1300, 1400, 1500]):
            day = f"2026-04-{13 + i:02d}"
            rows.append((f"{day} 09:30", vol))
            # noise at other tods to make sure they're ignored
            rows.append((f"{day} 09:35", 999_999 + i))
        # The day we want to evaluate
        rows.append(("2026-04-20 09:30", 9999))   # current — should be excluded from baseline
        bars = _make_bars(rows)

        out = ind.calculate_avg_volume_same_time_of_day(bars, lookback_days=14, min_obs=5)
        # The 09:30 bar on 2026-04-20 should have baseline = median of prior six 09:30 bars = (1200+1300)/2 = 1250
        eval_ts = pd.Timestamp("2026-04-20 09:30", tz="America/New_York")
        assert out.loc[eval_ts] == pytest.approx(1250.0)

    def test_excludes_current_day_from_baseline(self):
        """Baseline must not include the current day's volume — only prior days."""
        rows = []
        # 5 prior days at 09:30 with volume 1000 each
        for i in range(5):
            day = f"2026-04-{14 + i:02d}"
            rows.append((f"{day} 09:30", 1000))
        # Current day 09:30 with anomalous 1_000_000 volume — must NOT pollute baseline
        rows.append(("2026-04-20 09:30", 1_000_000))
        bars = _make_bars(rows)

        out = ind.calculate_avg_volume_same_time_of_day(bars, lookback_days=14, min_obs=5)
        eval_ts = pd.Timestamp("2026-04-20 09:30", tz="America/New_York")
        # Baseline should be 1000 (median of 5 prior 1000's), NOT influenced by the 1M
        assert out.loc[eval_ts] == pytest.approx(1000.0)

    def test_falls_back_below_min_obs(self):
        """If a tod has < min_obs prior observations, fall back to rolling avg."""
        rows = []
        # Only 3 prior days at 09:30 (below min_obs=5)
        for i in range(3):
            day = f"2026-04-{17 + i:02d}"
            rows.append((f"{day} 09:30", 1000))
        rows.append(("2026-04-20 09:30", 5000))
        bars = _make_bars(rows)

        out = ind.calculate_avg_volume_same_time_of_day(bars, lookback_days=14, min_obs=5)
        eval_ts = pd.Timestamp("2026-04-20 09:30", tz="America/New_York")
        # Should equal the rolling-20 fallback at this index
        fallback = ind.calculate_avg_volume(bars)
        assert out.loc[eval_ts] == pytest.approx(float(fallback.loc[eval_ts]))

    def test_different_tods_use_different_baselines(self):
        """A 09:30 bar and a 13:00 bar in the same day should get different baselines."""
        rows = []
        # 6 prior days, each with volume 5000 at 09:30 and volume 500 at 13:00
        for i in range(6):
            day = f"2026-04-{14 + i:02d}"
            rows.append((f"{day} 09:30", 5000))
            rows.append((f"{day} 13:00", 500))
        # Current day's two bars
        rows.append(("2026-04-20 09:30", 9999))
        rows.append(("2026-04-20 13:00", 9999))
        bars = _make_bars(rows)

        out = ind.calculate_avg_volume_same_time_of_day(bars, lookback_days=14, min_obs=5)
        eval_open = pd.Timestamp("2026-04-20 09:30", tz="America/New_York")
        eval_lunch = pd.Timestamp("2026-04-20 13:00", tz="America/New_York")
        assert out.loc[eval_open] == pytest.approx(5000.0)
        assert out.loc[eval_lunch] == pytest.approx(500.0)

    def test_lookback_window_caps_at_lookback_days(self):
        """Baseline ignores days older than lookback_days even if data exists."""
        rows = []
        # 20 days of history at 09:30 — old days have 1, recent days have 1000
        for i in range(20):
            day = pd.Timestamp("2026-04-20") - pd.Timedelta(days=20 - i)
            day_str = day.strftime("%Y-%m-%d")
            vol = 1 if i < 6 else 1000  # first 6 days are 1, last 14 are 1000
            rows.append((f"{day_str} 09:30", vol))
        rows.append(("2026-04-20 09:30", 9999))
        bars = _make_bars(rows).sort_index()

        # lookback_days=14 → only the 14 most recent prior days count → all 1000's → median 1000
        out = ind.calculate_avg_volume_same_time_of_day(bars, lookback_days=14, min_obs=5)
        eval_ts = pd.Timestamp("2026-04-20 09:30", tz="America/New_York")
        assert out.loc[eval_ts] == pytest.approx(1000.0)

    def test_real_world_shape_open_vs_lunch(self):
        """
        End-to-end sanity: simulate 14 trading days where 09:30 volume is consistently
        ~10x the lunch volume. The 09:30 baseline should reflect the high open volume
        and the 13:00 baseline should reflect the low lunch volume — proving the same-tod
        approach distinguishes them, where the simple rolling avg cannot.
        """
        rows = []
        for i in range(14):
            day = pd.Timestamp("2026-04-01") + pd.Timedelta(days=i)
            day_str = day.strftime("%Y-%m-%d")
            rows.append((f"{day_str} 09:30", 50_000))    # heavy open
            rows.append((f"{day_str} 13:00", 5_000))     # lunch chop
        # Current day at lunch — same tod median should be 5000, not the rolling mix
        rows.append(("2026-04-20 13:00", 99_999))
        bars = _make_bars(rows).sort_index()

        out = ind.calculate_avg_volume_same_time_of_day(bars, lookback_days=14, min_obs=5)
        eval_ts = pd.Timestamp("2026-04-20 13:00", tz="America/New_York")
        assert out.loc[eval_ts] == pytest.approx(5_000.0)
        # And the simple rolling-20 baseline mixes both → much higher than 5000
        simple = ind.calculate_avg_volume(bars)
        # Just sanity-check that the simple metric does NOT equal the same-tod median
        assert simple.loc[eval_ts] != pytest.approx(5_000.0, rel=0.1)
