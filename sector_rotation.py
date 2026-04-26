"""
sector_rotation.py — Post-VIX-spike sector rotation module.

After volatility shocks, specific sectors historically outperform.
This module scores sectors based on the current regime and recent VIX dynamics,
then returns a ranked list of ETFs to rotate into.

Historical post-spike behavior:
  Utilities (XLU)  : outperform in all stress regimes (rate-sensitivity + defensiveness)
  Staples (XLP)    : stable cash flows, dividend support
  Healthcare (XLV) : non-cyclical demand
  Gold (GLD)       : safe-haven / inflation hedge
  Energy (XLE)     : mixed — outperforms in stagflation, underperforms in deflation risk
  Tech (XLK)       : underperforms in rate-driven spikes, recovers first in liquidity-driven
  Financials (XLF) : underperforms in banking stress, mixed otherwise
"""
from __future__ import annotations
import logging
from dataclasses import dataclass

import numpy as np
import pandas as pd

from regime import Regime, RegimeState
import config

logger = logging.getLogger(__name__)


@dataclass
class SectorScore:
    etf: str
    sector: str
    score: float          # 0 (avoid) to 1 (strongly prefer)
    reason: str


# Static regime-based scoring matrices
# (sector, regime_A_score, regime_B_score, regime_C_score)
_SECTOR_SCORES: list[tuple] = [
    ("utilities",   "XLU", 0.40, 0.75, 0.95),
    ("staples",     "XLP", 0.40, 0.80, 0.90),
    ("healthcare",  "XLV", 0.50, 0.75, 0.85),
    ("gold",        "GLD", 0.35, 0.65, 0.90),
    ("quality",     "QUAL",0.60, 0.70, 0.65),
    ("tech",        "XLK", 0.90, 0.40, 0.15),
    ("energy",      "XLE", 0.55, 0.45, 0.30),
    ("financials",  "XLF", 0.65, 0.35, 0.20),
]


def score_sectors(regime_state: RegimeState) -> list[SectorScore]:
    """
    Score all sector ETFs for the current regime.
    Returns list sorted by score descending.
    """
    regime = regime_state.regime
    vix = regime_state.vix_level
    vvix = regime_state.vvix_level
    term = regime_state.term_ratio

    results = []
    for sector, etf, a_score, b_score, c_score in _SECTOR_SCORES:
        if regime == Regime.A:
            base = a_score
        elif regime == Regime.B:
            base = b_score
        else:
            base = c_score

        # Dynamic adjustments on top of base
        adjustment = 0.0

        # VIX backwardation boosts defensives
        if term > 1.10 and etf in ("XLU", "XLP", "GLD"):
            adjustment += 0.05

        # Extreme VVIX boosts gold further
        if vvix > 115 and etf == "GLD":
            adjustment += 0.05

        # Tech penalty when VIX is spiking
        if etf == "XLK" and vix > 25:
            adjustment -= 0.15

        final_score = max(0.0, min(1.0, base + adjustment))

        reasons = []
        if regime == Regime.C:
            reasons.append("Regime C → defensive preferred")
        if term > config.VIX_TERM_BACKWARDATION:
            reasons.append(f"VIX backwardation (term={term:.2f})")
        if vvix > config.VVIX_CAUTION:
            reasons.append(f"VVIX={vvix:.0f} elevated")

        results.append(SectorScore(
            etf=etf,
            sector=sector,
            score=round(final_score, 3),
            reason="; ".join(reasons) if reasons else "regime-based",
        ))

    results.sort(key=lambda x: x.score, reverse=True)
    return results


def get_rotation_universe(
    regime_state: RegimeState,
    top_n: int = 4,
) -> list[str]:
    """
    Return the top N sector ETFs to trade in the current regime.
    In Regime A, returns the momentum universe.
    In Regime B/C, returns defensive sectors.
    """
    if regime_state.regime == Regime.A:
        return config.MOMENTUM_UNIVERSE[:]

    scored = score_sectors(regime_state)
    selected = [s.etf for s in scored[:top_n]]
    logger.info(
        f"Sector rotation ({regime_state.regime.value}): {selected} | "
        f"top scores: {[f'{s.etf}={s.score:.2f}' for s in scored[:top_n]]}"
    )
    return selected


def post_vix_spike_signal(
    vix_series: pd.Series,
    spike_threshold: float = 20.0,
    lookback: int = 3,
) -> bool:
    """
    True if VIX spiked (>= spike_threshold point rise) within the last `lookback` days.
    Signals a post-spike rotation opportunity into defensives.
    """
    if len(vix_series) < lookback + 1:
        return False
    recent = vix_series.dropna().tail(lookback + 1)
    max_spike = float(recent.diff().dropna().max())
    return max_spike >= spike_threshold


def rotation_summary(regime_state: RegimeState) -> str:
    scored = score_sectors(regime_state)
    lines = [f"Sector Rotation — {regime_state.regime.value}"]
    for s in scored:
        bar = "█" * int(s.score * 10)
        lines.append(f"  {s.etf:<6} {bar:<10} {s.score:.2f}  {s.reason}")
    return "\n".join(lines)
