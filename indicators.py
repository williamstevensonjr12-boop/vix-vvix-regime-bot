"""
indicators.py — Technical indicators for the VWAP-Bounce strategy.
All functions are pure (no side effects).
"""
from __future__ import annotations

import numpy as np
import pandas as pd

import config


def calculate_vwap(bars: pd.DataFrame) -> pd.Series:
    """Intraday VWAP anchored to the first bar of the session."""
    if bars.empty:
        return pd.Series(dtype=float, name="vwap")
    tp = (bars["high"] + bars["low"] + bars["close"]) / 3
    vwap = (tp * bars["volume"]).cumsum() / bars["volume"].cumsum()
    vwap.name = "vwap"
    return vwap


def calculate_ema(close: pd.Series, period: int) -> pd.Series:
    """Exponential moving average. Cameron VWAP-Bounce uses 9 / 20 / 200 on 5-min closes:
        - 200 EMA: regime filter (no longs below, no shorts above)
        - 9 > 20 stack: trend confirmation for direction
    """
    if close.empty:
        return pd.Series(dtype=float, name=f"ema_{period}")
    ema = close.ewm(span=period, adjust=False).mean()
    ema.name = f"ema_{period}"
    return ema


def calculate_atr(bars: pd.DataFrame, period: int = None) -> pd.Series:
    """Average True Range over `period` bars (default config.ATR_PERIOD).

    Used by the stop-distance guardrail: skip the trade when
    (entry - prior_5bar_low) > config.ATR_GUARDRAIL_MULT × ATR.
    """
    period = period or config.ATR_PERIOD
    if bars.empty or len(bars) < 2:
        return pd.Series(dtype=float, name="atr")
    high, low, prev_close = bars["high"], bars["low"], bars["close"].shift(1)
    tr = pd.concat(
        [high - low, (high - prev_close).abs(), (low - prev_close).abs()], axis=1
    ).max(axis=1)
    atr = tr.ewm(span=period, adjust=False).mean()
    atr.name = "atr"
    return atr


def calculate_avg_volume(bars: pd.DataFrame, lookback: int = None) -> pd.Series:
    """Rolling average volume over `lookback` bars (default config.VOLUME_LOOKBACK_BARS)."""
    lookback = lookback or config.VOLUME_LOOKBACK_BARS
    if bars.empty:
        return pd.Series(dtype=float, name="avg_volume")
    avg = bars["volume"].rolling(window=lookback, min_periods=1).mean()
    avg.name = "avg_volume"
    return avg


def calculate_relative_volume(bars: pd.DataFrame, lookback: int = None) -> pd.Series:
    """Per-bar volume / trailing avg-volume ratio (rvol).

    Cameron's bounce confirmation requires rvol >= config.CAMERON_VOLUME_MULTIPLIER
    on the bounce bar — institutional participation, not just price reclaim.
    """
    lookback = lookback or config.VOLUME_LOOKBACK_BARS
    if bars.empty:
        return pd.Series(dtype=float, name="rvol")
    avg = calculate_avg_volume(bars, lookback)
    rvol = bars["volume"] / avg.replace(0, np.nan)
    rvol.name = "rvol"
    return rvol


def calculate_realized_vol(
    daily_returns: pd.Series,
    lookback: int = None,
    annualize: bool = True,
) -> float:
    """Annualized realized volatility from daily returns."""
    lookback = lookback or config.REALIZED_VOL_LOOKBACK
    clean = daily_returns.dropna().tail(lookback)
    if len(clean) < 5:
        return config.TARGET_ANNUALIZED_VOL
    rv = float(clean.std())
    return rv * np.sqrt(252) if annualize else rv


def vol_adjusted_size_multiplier(
    realized_vol: float,
    target_vol: float = None,
    floor: float = 0.25,
    cap: float = 2.0,
) -> float:
    """Scale position size inversely with realized vol vs target vol.

    Used by risk.calculate_position_size as a multiplicative factor on the
    base risk-per-trade. Floored/capped to prevent extreme sizes during
    low/high vol regimes.
    """
    target_vol = target_vol or config.TARGET_ANNUALIZED_VOL
    if realized_vol <= 0:
        return 1.0
    raw = target_vol / realized_vol
    return max(floor, min(cap, raw))
