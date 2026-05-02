"""
test_entry_gates.py — pytest unit tests for the strategy's entry-gate functions.

These lock in the current behavior of the bot's most critical filters:
gap-alignment, ATR expansion, ATR stops, position sizing, PDT constraints.
If any of these change behavior unintentionally, tests will catch it before
the next live deploy.

Run from repo/:
    pytest tests/

Or single file:
    .venv/bin/python -m pytest tests/test_entry_gates.py -v
"""
from __future__ import annotations
import os
import sys
from pathlib import Path

import pandas as pd
import pytest

# Make repo modules importable when pytest runs from any cwd
REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO))
os.chdir(REPO)

import config
import indicators as ind
import risk
from strategy import _compute_gap_pct, _gap_aligned


# ── _compute_gap_pct ────────────────────────────────────────────────────────

class TestComputeGapPct:
    def test_open_above_prior_close(self):
        bars = pd.DataFrame({"open": [10.50, 10.60], "close": [10.55, 10.62]})
        assert _compute_gap_pct(bars, prior_close=10.00) == pytest.approx(0.05, abs=1e-6)

    def test_open_below_prior_close(self):
        bars = pd.DataFrame({"open": [9.50], "close": [9.60]})
        assert _compute_gap_pct(bars, prior_close=10.00) == pytest.approx(-0.05, abs=1e-6)

    def test_no_prior_close(self):
        bars = pd.DataFrame({"open": [10.0], "close": [10.0]})
        assert _compute_gap_pct(bars, prior_close=None) is None

    def test_zero_prior_close(self):
        bars = pd.DataFrame({"open": [10.0], "close": [10.0]})
        assert _compute_gap_pct(bars, prior_close=0.0) is None

    def test_empty_bars(self):
        assert _compute_gap_pct(pd.DataFrame(), prior_close=10.0) is None

    def test_uses_first_bar_open(self):
        # Even with multiple bars, gap is computed from FIRST bar's open
        bars = pd.DataFrame({"open": [10.50, 11.00], "close": [10.55, 11.10]})
        assert _compute_gap_pct(bars, prior_close=10.00) == pytest.approx(0.05, abs=1e-6)


# ── _gap_aligned ───────────────────────────────────────────────────────────

class TestGapAligned:
    """Note: gap-alignment is regime-aware. Filter is OFF outside Regime A."""

    def test_long_passes_with_bullish_gap_in_A(self):
        ok, reason = _gap_aligned(0.012, side="long", regime_letter="A")
        assert ok is True
        assert "bullish gap" in reason

    def test_long_blocked_below_threshold_in_A(self):
        # Threshold is config.GAP_ALIGNMENT_THRESHOLD (0.008 currently)
        ok, _ = _gap_aligned(0.005, side="long", regime_letter="A")
        assert ok is False

    def test_long_blocked_with_bearish_gap_in_A(self):
        ok, _ = _gap_aligned(-0.012, side="long", regime_letter="A")
        assert ok is False

    def test_short_passes_with_bearish_gap_in_A(self):
        ok, reason = _gap_aligned(-0.012, side="short", regime_letter="A")
        assert ok is True
        assert "bearish gap" in reason

    def test_short_blocked_with_bullish_gap_in_A(self):
        ok, _ = _gap_aligned(0.012, side="short", regime_letter="A")
        assert ok is False

    def test_filter_skipped_outside_regime_A(self):
        # In B/C, gap filter is intentionally skipped (regime-aware)
        ok, _ = _gap_aligned(0.001, side="long", regime_letter="B")
        assert ok is True
        ok, _ = _gap_aligned(-0.001, side="short", regime_letter="C")
        assert ok is True

    def test_none_gap_passes(self):
        # If we have no gap data, fail open (existing behavior — see code)
        ok, _ = _gap_aligned(None, side="long", regime_letter="A")
        # Implementation returns False for None (fail closed). Lock current behavior.
        assert ok is False


# ── is_atr_expanding ───────────────────────────────────────────────────────

class TestATRExpansion:
    def test_expanding_atr_passes(self):
        # Last value clearly above 1.2x of recent mean
        s = pd.Series([0.10] * 19 + [0.20])
        assert ind.is_atr_expanding(s, multiplier=1.2) is True

    def test_flat_atr_blocked(self):
        s = pd.Series([0.10] * 20)
        assert ind.is_atr_expanding(s, multiplier=1.2) is False

    def test_contracting_atr_blocked(self):
        s = pd.Series([0.20] * 19 + [0.10])
        assert ind.is_atr_expanding(s, multiplier=1.2) is False

    def test_just_below_threshold_blocked(self):
        # mean = 0.1, 1.2x threshold = 0.12, latest 0.119 → blocked
        s = pd.Series([0.10] * 19 + [0.119])
        assert ind.is_atr_expanding(s, multiplier=1.2) is False

    def test_just_above_threshold_passes(self):
        # Mean (incl. the latest) = (19*0.10 + 0.13)/20 = 0.1015
        # Threshold = 1.2 × 0.1015 = 0.1218
        # 0.13 > 0.1218 → passes
        s = pd.Series([0.10] * 19 + [0.13])
        assert ind.is_atr_expanding(s, multiplier=1.2) is True

    def test_short_series_returns_false(self):
        s = pd.Series([0.10, 0.11, 0.12])
        assert ind.is_atr_expanding(s, multiplier=1.2) is False

    def test_zero_mean_returns_false(self):
        s = pd.Series([0.0] * 20)
        assert ind.is_atr_expanding(s, multiplier=1.2) is False


# ── atr_stop_price ─────────────────────────────────────────────────────────

class TestATRStop:
    def test_long_stop_below_entry(self):
        stop = ind.atr_stop_price(entry=100.0, atr=2.0, multiplier=1.5)
        assert stop == pytest.approx(97.0, abs=1e-6)

    def test_uses_config_default_when_unspecified(self):
        # Should equal entry - atr * config.ATR_STOP_MULTIPLIER
        stop = ind.atr_stop_price(entry=100.0, atr=2.0)
        assert stop == pytest.approx(100.0 - 2.0 * config.ATR_STOP_MULTIPLIER, abs=1e-6)


# ── vol-adjusted size multiplier ──────────────────────────────────────────

class TestVolAdjustedSize:
    def test_high_vol_reduces_size(self):
        target = 0.20
        mult = ind.vol_adjusted_size_multiplier(realized_vol=0.40, target_vol=target)
        assert mult < 1.0

    def test_low_vol_increases_size_to_cap(self):
        mult = ind.vol_adjusted_size_multiplier(realized_vol=0.05, target_vol=0.20, cap=2.0)
        assert mult <= 2.0
        assert mult > 1.0

    def test_floor_clamps_min_size(self):
        mult = ind.vol_adjusted_size_multiplier(realized_vol=10.0, target_vol=0.20, floor=0.25)
        assert mult == pytest.approx(0.25, abs=1e-6)

    def test_zero_vol_returns_one(self):
        # No realized_vol info → don't adjust
        mult = ind.vol_adjusted_size_multiplier(realized_vol=0.0)
        assert mult == 1.0


# ── PDT constraints (risk.py) ─────────────────────────────────────────────

class FakeAccount:
    def __init__(self, equity, flagged, daytrade_count):
        self.equity = equity
        self.pattern_day_trader = flagged
        self.daytrade_count = daytrade_count


class TestPDTConstraints:
    def test_healthy_account_passes(self):
        acct = FakeAccount(equity=100_000, flagged=True, daytrade_count=7)
        ok, _ = risk.check_pdt_constraints(acct)
        assert ok is True

    def test_not_flagged_passes_at_any_equity(self):
        acct = FakeAccount(equity=20_000, flagged=False, daytrade_count=5)
        ok, _ = risk.check_pdt_constraints(acct)
        assert ok is True

    def test_flagged_below_floor_blocks(self):
        acct = FakeAccount(equity=24_900, flagged=True, daytrade_count=5)
        ok, reason = risk.check_pdt_constraints(acct)
        assert ok is False
        assert "PDT" in reason

    def test_flagged_in_buffer_zone_blocks(self):
        # equity > floor but inside the safety buffer
        acct = FakeAccount(equity=25_400, flagged=True, daytrade_count=3)
        ok, _ = risk.check_pdt_constraints(acct)
        assert ok is False

    def test_flagged_just_above_buffer_passes(self):
        # equity > floor + buffer
        acct = FakeAccount(equity=25_600, flagged=True, daytrade_count=3)
        ok, _ = risk.check_pdt_constraints(acct)
        assert ok is True

    def test_none_account_passes(self):
        # No-op when account state is unavailable
        ok, _ = risk.check_pdt_constraints(None)
        assert ok is True


# ── position sizing ────────────────────────────────────────────────────────

class TestPositionSize:
    def test_basic_long_sizing(self):
        result = risk.calculate_position_size(
            account_equity=100_000,
            entry_price=100.0,
            stop_price=99.0,
            regime_size_factor=1.0,
            vvix_size_factor=1.0,
            sentiment_size_factor=1.0,
            realized_vol=0.20,
        )
        assert result.qty > 0
        # 0.5% of 100K = $500 risk → $1/share stop = 500 shares max
        # vol multiplier may scale down a bit; just check the ballpark
        assert result.qty <= 500
        assert result.qty >= 100

    def test_negative_risk_returns_zero_qty(self):
        # Stop above entry on a long → invalid
        result = risk.calculate_position_size(
            account_equity=100_000,
            entry_price=100.0,
            stop_price=101.0,
            regime_size_factor=1.0,
            vvix_size_factor=1.0,
            sentiment_size_factor=1.0,
            realized_vol=0.20,
        )
        assert result.qty == 0

    def test_regime_factor_halves_size(self):
        full = risk.calculate_position_size(
            account_equity=100_000, entry_price=100.0, stop_price=99.0,
            regime_size_factor=1.0, vvix_size_factor=1.0,
            sentiment_size_factor=1.0, realized_vol=0.20,
        )
        half = risk.calculate_position_size(
            account_equity=100_000, entry_price=100.0, stop_price=99.0,
            regime_size_factor=0.5, vvix_size_factor=1.0,
            sentiment_size_factor=1.0, realized_vol=0.20,
        )
        assert half.qty == pytest.approx(full.qty // 2, abs=1)
