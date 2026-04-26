"""
sentiment.py — Equity Put/Call ratio sentiment module.

Logic:
  - Extreme fear (P/C >> rolling mean): avoid long breakouts; allow mean-reversion entries
  - Extreme complacency (P/C << rolling mean): caution on new longs (crowded)
  - Neutral zone: no sentiment override

Put/Call interpretation:
  > 1.5 : panic / extreme fear  → potential reversal long entry on confirmation
  1.0–1.5 : elevated fear       → be selective, no momentum chasing
  0.7–1.0 : neutral             → normal trading
  < 0.65  : complacency         → watch for trend exhaustion
"""
from __future__ import annotations
import logging
from dataclasses import dataclass
from enum import Enum

import numpy as np
import pandas as pd

import config

logger = logging.getLogger(__name__)


class SentimentSignal(Enum):
    EXTREME_FEAR = "extreme_fear"
    ELEVATED_FEAR = "elevated_fear"
    NEUTRAL = "neutral"
    COMPLACENCY = "complacency"
    EXTREME_COMPLACENCY = "extreme_complacency"


@dataclass
class SentimentState:
    signal: SentimentSignal
    put_call_ratio: float
    z_score: float            # vs rolling 20d mean/std
    rolling_mean: float
    rolling_std: float
    allow_momentum_longs: bool
    allow_mean_reversion_longs: bool
    size_multiplier: float
    reason: str


_PC_EXTREME_FEAR = 1.40
_PC_ELEVATED_FEAR = 1.10
_PC_COMPLACENCY = 0.70
_PC_EXTREME_COMPLACENCY = 0.55
_PC_LOOKBACK = 20


def classify_put_call(
    pc_series: pd.Series,
    current_pc: float | None = None,
) -> SentimentState:
    """
    Classify current put/call sentiment.

    pc_series  : historical daily P/C ratio values (at least 10)
    current_pc : override for the latest value; defaults to pc_series.iloc[-1]
    """
    clean = pc_series.dropna()
    if current_pc is None:
        current_pc = float(clean.iloc[-1]) if not clean.empty else 0.9

    if len(clean) >= _PC_LOOKBACK:
        window = clean.tail(_PC_LOOKBACK)
    else:
        window = clean

    roll_mean = float(window.mean()) if not window.empty else 0.9
    roll_std = float(window.std()) if len(window) > 1 else 0.1
    z_score = (current_pc - roll_mean) / roll_std if roll_std > 0 else 0.0

    # Classify
    if current_pc >= _PC_EXTREME_FEAR:
        signal = SentimentSignal.EXTREME_FEAR
        allow_momentum = False
        allow_mean_rev = True     # Potential reversal if P/C starts falling
        size_mult = 0.5
        reason = f"P/C={current_pc:.2f} — extreme fear (z={z_score:.1f}), mean-reversion watch"
    elif current_pc >= _PC_ELEVATED_FEAR:
        signal = SentimentSignal.ELEVATED_FEAR
        allow_momentum = False
        allow_mean_rev = False
        size_mult = 0.75
        reason = f"P/C={current_pc:.2f} — elevated fear, avoid momentum longs"
    elif current_pc <= _PC_EXTREME_COMPLACENCY:
        signal = SentimentSignal.EXTREME_COMPLACENCY
        allow_momentum = False
        allow_mean_rev = False
        size_mult = 0.50
        reason = f"P/C={current_pc:.2f} — extreme complacency, crowd is wrong"
    elif current_pc <= _PC_COMPLACENCY:
        signal = SentimentSignal.COMPLACENCY
        allow_momentum = True   # Complacency can persist in trending markets
        allow_mean_rev = False
        size_mult = 0.85
        reason = f"P/C={current_pc:.2f} — complacency zone, monitor"
    else:
        signal = SentimentSignal.NEUTRAL
        allow_momentum = True
        allow_mean_rev = False
        size_mult = 1.0
        reason = f"P/C={current_pc:.2f} — neutral sentiment"

    return SentimentState(
        signal=signal,
        put_call_ratio=current_pc,
        z_score=round(z_score, 2),
        rolling_mean=round(roll_mean, 3),
        rolling_std=round(roll_std, 3),
        allow_momentum_longs=allow_momentum,
        allow_mean_reversion_longs=allow_mean_rev,
        size_multiplier=size_mult,
        reason=reason,
    )


def is_panic_reversal_setup(
    pc_series: pd.Series,
    vix_series: pd.Series,
    lookback: int = 3,
) -> bool:
    """
    True when:
      - Recent P/C was at extreme fear levels (>= 1.3)
      - P/C is now declining (fear peaking and reversing)
      - VIX has also started declining
    This is a mean-reversion entry signal for defensive names.
    """
    if len(pc_series) < lookback + 2 or len(vix_series) < lookback + 2:
        return False

    pc_recent = pc_series.dropna().tail(lookback + 1)
    vix_recent = vix_series.dropna().tail(lookback + 1)

    pc_was_extreme = float(pc_recent.iloc[:-1].max()) >= 1.30
    pc_declining = float(pc_recent.iloc[-1]) < float(pc_recent.iloc[-2])
    vix_declining = float(vix_recent.iloc[-1]) < float(vix_recent.iloc[-2])

    return pc_was_extreme and pc_declining and vix_declining
