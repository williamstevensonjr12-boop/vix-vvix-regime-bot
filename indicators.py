"""
indicators.py — Technical indicators used by the strategy engine.
All functions are pure (no side effects).
"""
from __future__ import annotations
from datetime import datetime
from zoneinfo import ZoneInfo

import numpy as np
import pandas as pd

import config

ET = ZoneInfo(config.TIMEZONE)


def calculate_vwap(bars: pd.DataFrame) -> pd.Series:
    """Intraday VWAP anchored to the first bar."""
    if bars.empty:
        return pd.Series(dtype=float, name="vwap")
    tp = (bars["high"] + bars["low"] + bars["close"]) / 3
    vwap = (tp * bars["volume"]).cumsum() / bars["volume"].cumsum()
    vwap.name = "vwap"
    return vwap


def calculate_opening_range(
    bars: pd.DataFrame,
    trading_day=None,
) -> dict | None:
    """Opening range H/L for the first 15 minutes (9:30–9:44 ET)."""
    if bars.empty:
        return None
    if trading_day is None:
        trading_day = bars.index[0].date()

    orb_start = datetime.combine(
        trading_day, datetime.strptime(config.MARKET_OPEN, "%H:%M").time()
    ).replace(tzinfo=ET)
    orb_cutoff = datetime.combine(
        trading_day, datetime.strptime(config.ORB_END_TIME, "%H:%M").time()
    ).replace(tzinfo=ET)

    orb_bars = bars[(bars.index >= orb_start) & (bars.index < orb_cutoff)]
    if len(orb_bars) < 3:
        return None

    return {"high": float(orb_bars["high"].max()), "low": float(orb_bars["low"].min())}


def calculate_atr(bars: pd.DataFrame, period: int = None) -> pd.Series:
    """Average True Range over period bars."""
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
    """Rolling average volume."""
    lookback = lookback or config.VOLUME_LOOKBACK_BARS
    if bars.empty:
        return pd.Series(dtype=float, name="avg_volume")
    avg = bars["volume"].rolling(window=lookback, min_periods=1).mean()
    avg.name = "avg_volume"
    return avg


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


def atr_stop_price(entry: float, atr: float, multiplier: float = None) -> float:
    """Dynamic stop = entry - ATR * multiplier."""
    multiplier = multiplier or config.ATR_STOP_MULTIPLIER
    return entry - atr * multiplier


def is_atr_expanding(atr_series: pd.Series, multiplier: float = None) -> bool:
    """True if latest ATR > multiplier × rolling 20-period ATR mean (vol expansion)."""
    multiplier = multiplier or config.ATR_EXPANSION_MULTIPLIER
    if len(atr_series) < 5:
        return False
    current_atr = float(atr_series.iloc[-1])
    mean_atr = float(atr_series.tail(20).mean())
    return current_atr > multiplier * mean_atr if mean_atr > 0 else False


def vol_adjusted_size_multiplier(
    realized_vol: float,
    target_vol: float = None,
    floor: float = 0.25,
    cap: float = 2.0,
) -> float:
    """Scale position size inversely with realized vol vs target vol."""
    target_vol = target_vol or config.TARGET_ANNUALIZED_VOL
    if realized_vol <= 0:
        return 1.0
    raw = target_vol / realized_vol
    return max(floor, min(cap, raw))
