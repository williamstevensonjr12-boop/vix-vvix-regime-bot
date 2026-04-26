"""
vvix_filter.py — VVIX (vol-of-vol) filter module.

VVIX measures implied volatility of VIX options.
Spikes in VVIX signal tail-risk hedging demand — a leading stress indicator.

Rules:
  VVIX > 110 : reduce risk (0.5x sizing)
  VVIX > 120 : no new ORB entries
  VVIX +10% intraday : emergency risk-off mode
"""
from __future__ import annotations
import logging
from dataclasses import dataclass
from datetime import datetime
from zoneinfo import ZoneInfo

import pandas as pd

import config

logger = logging.getLogger(__name__)
ET = ZoneInfo(config.TIMEZONE)


@dataclass
class VVIXFilterResult:
    can_trade: bool
    size_multiplier: float       # 1.0 = normal, 0.5 = caution, 0.0 = blocked
    emergency_mode: bool
    vvix_level: float
    vvix_open: float
    intraday_change_pct: float
    reason: str


def get_vvix(vol_snapshot: dict) -> float:
    """Extract current VVIX level from a data snapshot dict."""
    return float(vol_snapshot.get("vvix", 100.0))


def detect_vol_of_vol_spikes(
    vvix_intraday: pd.Series,
    spike_threshold_pct: float = None,
) -> bool:
    """
    True if VVIX has risen > spike_threshold_pct from today's open.
    vvix_intraday: Series of VVIX values indexed by timestamp (today's bars).
    """
    spike_threshold_pct = spike_threshold_pct or config.VVIX_SPIKE_PCT
    if vvix_intraday.empty or len(vvix_intraday) < 2:
        return False
    open_val = float(vvix_intraday.iloc[0])
    current_val = float(vvix_intraday.iloc[-1])
    if open_val <= 0:
        return False
    change_pct = (current_val - open_val) / open_val
    return change_pct >= spike_threshold_pct


def regime_filter(
    vvix_level: float,
    vvix_open: float | None = None,
) -> VVIXFilterResult:
    """
    Main VVIX filter called before any trade entry.

    Returns VVIXFilterResult with can_trade flag, size multiplier, and reason.
    Also used as a false-breakout filter: high VVIX means breakouts are more
    likely to be noise (hedging flow, not directional conviction).
    """
    vvix_open = vvix_open or vvix_level
    intraday_chg = (vvix_level - vvix_open) / vvix_open if vvix_open > 0 else 0.0
    emergency = intraday_chg >= config.VVIX_SPIKE_PCT

    if emergency:
        return VVIXFilterResult(
            can_trade=False,
            size_multiplier=0.0,
            emergency_mode=True,
            vvix_level=vvix_level,
            vvix_open=vvix_open,
            intraday_change_pct=intraday_chg,
            reason=(
                f"EMERGENCY RISK-OFF: VVIX spiked {intraday_chg:.1%} intraday "
                f"(open={vvix_open:.1f} → current={vvix_level:.1f})"
            ),
        )

    if vvix_level >= config.VVIX_NO_TRADE:
        return VVIXFilterResult(
            can_trade=False,
            size_multiplier=0.0,
            emergency_mode=False,
            vvix_level=vvix_level,
            vvix_open=vvix_open,
            intraday_change_pct=intraday_chg,
            reason=f"VVIX={vvix_level:.1f} >= {config.VVIX_NO_TRADE} — no new ORB entries",
        )

    if vvix_level >= config.VVIX_CAUTION:
        return VVIXFilterResult(
            can_trade=True,
            size_multiplier=0.5,
            emergency_mode=False,
            vvix_level=vvix_level,
            vvix_open=vvix_open,
            intraday_change_pct=intraday_chg,
            reason=f"VVIX={vvix_level:.1f} >= {config.VVIX_CAUTION} — reduced risk (0.5x)",
        )

    return VVIXFilterResult(
        can_trade=True,
        size_multiplier=1.0,
        emergency_mode=False,
        vvix_level=vvix_level,
        vvix_open=vvix_open,
        intraday_change_pct=intraday_chg,
        reason=f"VVIX={vvix_level:.1f} — normal",
    )


def is_false_breakout_risk(vvix_level: float, vix_level: float) -> bool:
    """
    Elevated VVIX during a VIX spike increases false breakout risk.
    Returns True if we should be extra cautious about ORB validity.
    """
    return vvix_level > config.VVIX_CAUTION and vix_level > config.VIX_REGIME_B_MAX
