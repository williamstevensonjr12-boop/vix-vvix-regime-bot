"""
regime.py — Multi-factor volatility regime classification engine.

Regime A (Low Vol Trend)  : composite >= 0.65 | VIX <20, VVIX calm, SPY bullish
Regime B (Elevated Vol)   : composite 0.40–0.65 | VIX 20-25, reduce sizing 50%
Regime C (Stress / Crisis): composite < 0.40 or VIX >25 | defensive rotation + crisis alpha
"""
from __future__ import annotations
import logging
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from zoneinfo import ZoneInfo

import numpy as np
import pandas as pd

import config

logger = logging.getLogger(__name__)
ET = ZoneInfo(config.TIMEZONE)


class Regime(Enum):
    A = "A_LOW_VOL_TREND"
    B = "B_ELEVATED_VOL"
    C = "C_STRESS_CRISIS"
    UNKNOWN = "UNKNOWN"


@dataclass
class RegimeState:
    regime: Regime
    composite_score: float
    vix_level: float
    vix_trend: float          # MA5 - MA20 (positive = rising)
    vvix_level: float
    put_call_ratio: float
    spy_vs_ma50: float        # fractional distance from 50d MA
    term_ratio: float         # VIX / VIX3M (>1 = backwardation = stress)
    factor_scores: dict = field(default_factory=dict)
    timestamp: datetime = field(default_factory=lambda: datetime.now(ET))
    # Derived trade context
    active_universe: list = field(default_factory=list)
    size_factor: float = 1.0
    crisis_alpha_enabled: bool = False

    def summary(self) -> str:
        return (
            f"Regime {self.regime.value} | score={self.composite_score:.3f} | "
            f"VIX={self.vix_level:.1f} VVIX={self.vvix_level:.1f} "
            f"term={self.term_ratio:.3f} P/C={self.put_call_ratio:.2f} | "
            f"size={self.size_factor:.2f}x crisis={self.crisis_alpha_enabled}"
        )


class RegimeEngine:
    """
    Scores six volatility factors, combines them into a composite [0,1],
    and classifies the market regime. Hard overrides applied last.
    """

    def __init__(self):
        self._last_state: RegimeState | None = None

    @property
    def last_state(self) -> RegimeState | None:
        return self._last_state

    # ── Primary compute method ────────────────────────────────────────────────

    def compute(
        self,
        vix_series: pd.Series,
        vvix_level: float,
        put_call_ratio: float,
        spy_series: pd.Series,
        vix3m_level: float | None = None,
    ) -> RegimeState:
        """
        vix_series  : daily VIX closes (at least 20 values)
        spy_series  : daily SPY closes (at least 50 values)
        vix3m_level : latest VIX3M (VIX term structure numerator)
        """
        vix = float(vix_series.dropna().iloc[-1])
        vvix = float(vvix_level) if vvix_level else 100.0
        pc = float(put_call_ratio) if put_call_ratio else 0.9

        # VIX trend: 5d MA - 20d MA
        v = vix_series.dropna()
        vix_ma5 = float(v.tail(5).mean())
        vix_ma20 = float(v.tail(20).mean()) if len(v) >= 20 else float(v.mean())
        vix_trend = vix_ma5 - vix_ma20

        # SPY vs 50d MA
        s = spy_series.dropna()
        spy_close = float(s.iloc[-1])
        spy_ma50 = float(s.tail(50).mean()) if len(s) >= 50 else spy_close
        spy_vs_ma50 = (spy_close - spy_ma50) / spy_ma50

        # VIX term structure
        vix3m = float(vix3m_level) if vix3m_level and vix3m_level > 0 else vix * 0.95
        term_ratio = vix / vix3m

        # ── Factor scoring (0 = max stress, 1 = max calm) ─────────────────
        scores: dict[str, float] = {}

        # VIX level: 15→1.0, 20→0.67, 25→0.33, 30→0.0
        scores["vix_level"] = max(0.0, min(1.0, (30.0 - vix) / 15.0))

        # VIX trend: rising = stress, falling = calm
        scores["vix_trend"] = max(0.0, min(1.0, 0.5 - vix_trend / 10.0))

        # VVIX: <90→1.0, 100→0.70, 110→0.30, ≥120→0.0
        if vvix >= 120:
            scores["vvix_level"] = 0.0
        elif vvix >= 110:
            scores["vvix_level"] = max(0.0, (120.0 - vvix) / 10.0 * 0.30)
        elif vvix >= 100:
            scores["vvix_level"] = 0.30 + (110.0 - vvix) / 10.0 * 0.40
        else:
            scores["vvix_level"] = 0.70 + min(0.30, (100.0 - vvix) / 10.0 * 0.30)

        # P/C ratio: >1.5→0.15 (extreme fear), 0.8-1.0→0.80, <0.65→0.50 (complacency risk)
        if pc > 1.5:
            scores["put_call"] = 0.15
        elif pc > 1.2:
            scores["put_call"] = 0.15 + (1.5 - pc) / 0.3 * 0.35
        elif pc < 0.65:
            scores["put_call"] = 0.50
        else:
            scores["put_call"] = max(0.50, min(1.0, 0.80 - (pc - 0.80) * 0.60))

        # SPY trend: above 50d MA = bullish
        scores["spy_trend"] = 1.0 if spy_vs_ma50 > 0 else max(0.0, 0.5 + spy_vs_ma50 * 5.0)

        # Term structure: strong contango (term_ratio < 0.90) → 1.0; backwardation → 0.0
        scores["term_structure"] = max(0.0, min(1.0, (1.20 - term_ratio) / 0.30))

        composite = sum(config.REGIME_WEIGHTS[k] * scores[k] for k in config.REGIME_WEIGHTS)

        # ── Hard overrides ─────────────────────────────────────────────────
        if vix > config.VIX_REGIME_C_MIN or vvix > config.VVIX_NO_TRADE:
            regime = Regime.C
        elif composite >= config.REGIME_A_THRESHOLD:
            regime = Regime.A
        elif composite >= config.REGIME_B_THRESHOLD:
            regime = Regime.B
        else:
            regime = Regime.C

        # ── Derive trade context ───────────────────────────────────────────
        if regime == Regime.A:
            active_universe = config.MOMENTUM_UNIVERSE[:]
            size_factor = 1.0
            crisis_alpha = False
        elif regime == Regime.B:
            active_universe = config.FEAR_RESILIENT_UNIVERSE[:]
            size_factor = config.REGIME_B_SIZE_FACTOR
            crisis_alpha = False
        else:
            active_universe = config.DEFENSIVE_UNIVERSE[:]
            size_factor = config.REGIME_C_SIZE_FACTOR
            crisis_alpha = True

        state = RegimeState(
            regime=regime,
            composite_score=round(composite, 4),
            vix_level=vix,
            vix_trend=round(vix_trend, 3),
            vvix_level=vvix,
            put_call_ratio=pc,
            spy_vs_ma50=round(spy_vs_ma50, 4),
            term_ratio=round(term_ratio, 4),
            factor_scores=scores,
            active_universe=active_universe,
            size_factor=size_factor,
            crisis_alpha_enabled=crisis_alpha,
        )
        self._last_state = state
        logger.info(state.summary())
        return state

    # ── Convenience wrapper for backtesting ──────────────────────────────────

    def compute_from_dataframes(
        self,
        vol_df: pd.DataFrame,         # columns: vix, vvix, vix3m
        spy_daily: pd.DataFrame,       # daily SPY with 'close' column
        pc_series: pd.Series,
        as_of: pd.Timestamp,
    ) -> RegimeState:
        """Slice all inputs at as_of date and compute regime. No lookahead."""
        def _slice(df_or_series, as_of):
            if df_or_series.empty or not isinstance(df_or_series.index, pd.DatetimeIndex):
                return df_or_series
            return df_or_series[df_or_series.index <= as_of]

        vol_slice = _slice(vol_df, as_of)
        spy_slice = _slice(spy_daily, as_of)
        pc_slice = _slice(pc_series, as_of)

        if vol_slice.empty:
            return self._fallback_regime()

        vix_s = vol_slice["vix"].dropna() if "vix" in vol_slice else pd.Series([20.0])
        vvix_v = float(vol_slice["vvix"].dropna().iloc[-1]) if "vvix" in vol_slice else 100.0
        vix3m_v = float(vol_slice["vix3m"].dropna().iloc[-1]) if "vix3m" in vol_slice else None
        pc_v = float(pc_slice.dropna().iloc[-1]) if not pc_slice.empty else 0.9

        spy_close_s = spy_slice["close"] if "close" in spy_slice.columns else spy_slice.iloc[:, 0]

        return self.compute(vix_s, vvix_v, pc_v, spy_close_s, vix3m_v)

    @staticmethod
    def _fallback_regime() -> RegimeState:
        return RegimeState(
            regime=Regime.UNKNOWN,
            composite_score=0.5,
            vix_level=20.0,
            vix_trend=0.0,
            vvix_level=100.0,
            put_call_ratio=0.9,
            spy_vs_ma50=0.0,
            term_ratio=1.0,
            active_universe=config.MOMENTUM_UNIVERSE[:],
            size_factor=1.0,
        )
