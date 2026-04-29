"""
data.py — Multi-source market data.
Alpaca: 5-minute equity bars.
yfinance: VIX, VVIX, VIX3M, Put/Call ratio, daily SPY.
"""
from __future__ import annotations
import logging
from datetime import datetime, date
from zoneinfo import ZoneInfo

import numpy as np
import pandas as pd
import yfinance as yf
from alpaca.data.historical import StockHistoricalDataClient
from alpaca.data.requests import StockBarsRequest
from alpaca.data.timeframe import TimeFrame, TimeFrameUnit

import config

logger = logging.getLogger(__name__)
ET = ZoneInfo(config.TIMEZONE)

_data_client: StockHistoricalDataClient | None = None


def get_data_client() -> StockHistoricalDataClient:
    global _data_client
    if _data_client is None:
        _data_client = StockHistoricalDataClient(
            api_key=config.ALPACA_API_KEY,
            secret_key=config.ALPACA_SECRET_KEY,
        )
    return _data_client


# ── Alpaca equity bars ────────────────────────────────────────────────────────

def _fetch_alpaca_bars(
    client: StockHistoricalDataClient,
    symbol: str,
    start: datetime,
    end: datetime,
    bar_size_minutes: int = 5,
) -> pd.DataFrame:
    request = StockBarsRequest(
        symbol_or_symbols=symbol,
        timeframe=TimeFrame(bar_size_minutes, TimeFrameUnit.Minute),
        start=start,
        end=end,
        feed="iex",
    )
    try:
        result = client.get_stock_bars(request)
        df = result.df
    except Exception as e:
        logger.error(f"Alpaca fetch error {symbol}: {e}")
        return pd.DataFrame()

    if df is None or df.empty:
        return pd.DataFrame()

    if isinstance(df.index, pd.MultiIndex):
        if symbol in df.index.get_level_values(0):
            df = df.loc[symbol].copy()
        else:
            return pd.DataFrame()

    df.index = (
        df.index.tz_localize("UTC").tz_convert(ET)
        if df.index.tz is None
        else df.index.tz_convert(ET)
    )
    df = df.between_time("09:30", "16:00")
    df.columns = [c.lower() for c in df.columns]
    return df


def get_today_bars(client, symbol: str, trade_date=None) -> pd.DataFrame:
    if trade_date is None:
        trade_date = datetime.now(ET).date()
    start = datetime.combine(trade_date, datetime.strptime("09:25", "%H:%M").time()).replace(tzinfo=ET)
    end = datetime.combine(trade_date, datetime.strptime("16:05", "%H:%M").time()).replace(tzinfo=ET)
    return _fetch_alpaca_bars(client, symbol, start, end)


def get_historical_bars(client, symbol: str, start_date: str, end_date: str) -> pd.DataFrame:
    start = datetime.strptime(start_date, "%Y-%m-%d").replace(hour=9, minute=25, tzinfo=ET)
    end = datetime.strptime(end_date, "%Y-%m-%d").replace(hour=16, minute=5, tzinfo=ET)
    return _fetch_alpaca_bars(client, symbol, start, end)


def get_multiple_symbols_bars(client, symbols: list, start_date: str, end_date: str) -> dict:
    result = {}
    for sym in symbols:
        logger.info(f"  Downloading {sym}...")
        df = get_historical_bars(client, sym, start_date, end_date)
        if not df.empty:
            result[sym] = df
            logger.info(f"  {sym}: {len(df)} bars, {len(set(df.index.date))} days")
        else:
            logger.warning(f"  {sym}: no data")
    return result


# ── yfinance volatility data ──────────────────────────────────────────────────

def _yf_to_et(df: pd.DataFrame) -> pd.DataFrame:
    if df.index.tz is None:
        df.index = pd.to_datetime(df.index).tz_localize("UTC").tz_convert(ET)
    else:
        df.index = df.index.tz_convert(ET)
    return df


def get_vix_history(start_date: str, end_date: str) -> pd.DataFrame:
    """Download VIX, VVIX, VIX3M daily closes into a combined DataFrame."""
    ticker_map = {"vix": "^VIX", "vvix": "^VVIX", "vix3m": "^VIX3M"}
    series = {}
    for col, ticker in ticker_map.items():
        try:
            raw = yf.download(ticker, start=start_date, end=end_date, progress=False, auto_adjust=True)
            if not raw.empty:
                close = raw["Close"]
                if isinstance(close, pd.DataFrame):
                    close = close.iloc[:, 0]
                series[col] = close.rename(col)
                logger.info(f"  {ticker}: {len(raw)} daily bars")
            else:
                logger.warning(f"  {ticker}: no data returned")
        except Exception as e:
            logger.warning(f"  {ticker} fetch failed: {e}")

    if not series:
        return pd.DataFrame()

    combined = pd.concat(series.values(), axis=1)
    combined = _yf_to_et(combined).sort_index().ffill()
    return combined


def get_put_call_history(start_date: str, end_date: str) -> pd.Series:
    """CBOE Equity Put/Call ratio. Returns daily series. Falls back to empty (0.9 proxy)."""
    yf_log = logging.getLogger("yfinance")
    prev_level = yf_log.level
    yf_log.setLevel(logging.CRITICAL)  # suppress known delisted-ticker noise
    try:
        raw = yf.download("^PCALL", start=start_date, end=end_date, progress=False, auto_adjust=True)
        if not raw.empty:
            s = raw["Close"]
            if isinstance(s, pd.DataFrame):
                s = s.iloc[:, 0]
            s = s.rename("put_call_ratio")
            return _yf_to_et(s.to_frame()).iloc[:, 0].sort_index().ffill()
    except Exception as e:
        logger.debug(f"^PCALL unavailable: {e}")
    finally:
        yf_log.setLevel(prev_level)

    logger.debug("Put/call data unavailable; regime will use 0.9 neutral proxy")
    return pd.Series(dtype=float, name="put_call_ratio")


def get_spy_daily(start_date: str, end_date: str) -> pd.DataFrame:
    """Daily SPY OHLCV for benchmark and trend calculations."""
    try:
        raw = yf.download("SPY", start=start_date, end=end_date, progress=False, auto_adjust=True)
        if not raw.empty:
            if isinstance(raw.columns, pd.MultiIndex):
                raw.columns = raw.columns.get_level_values(0)
            raw.columns = [c.lower() for c in raw.columns]
            return _yf_to_et(raw).sort_index()
    except Exception as e:
        logger.error(f"SPY daily fetch failed: {e}")
    return pd.DataFrame()


def get_current_vol_snapshot() -> dict:
    """Delayed VIX/VVIX/VIX3M snapshot for live paper trading."""
    defaults = {"vix": 20.0, "vvix": 100.0, "vix3m": 20.0, "put_call_ratio": 0.9}
    ticker_map = {"vix": "^VIX", "vvix": "^VVIX", "vix3m": "^VIX3M"}
    yf_log = logging.getLogger("yfinance")
    prev_level = yf_log.level
    yf_log.setLevel(logging.CRITICAL)
    try:
        for key, ticker in ticker_map.items():
            try:
                t = yf.Ticker(ticker)
                hist = t.history(period="2d", interval="5m")
                if not hist.empty:
                    defaults[key] = float(hist["Close"].dropna().iloc[-1])
            except Exception as e:
                logger.debug(f"Could not update {ticker}: {e}")
    finally:
        yf_log.setLevel(prev_level)
    return defaults


def get_prior_closes(symbols: list[str], lookback_days: int = 5) -> dict:
    """
    Return prior trading-day close for each symbol via yfinance.
    Used by the gap-continuation signal to compute the gap vs prior close.
    """
    if not symbols:
        return {}
    end = datetime.now(ET).date()
    start = end - pd.Timedelta(days=lookback_days)
    try:
        df = yf.download(
            tickers=" ".join(symbols),
            start=start.isoformat(),
            end=end.isoformat(),
            interval="1d",
            progress=False,
            group_by="ticker",
            auto_adjust=False,
        )
    except Exception as e:
        logger.warning(f"prior closes fetch failed: {e}")
        return {}

    closes: dict[str, float] = {}
    if df.empty:
        return closes
    if len(symbols) == 1:
        col = df["Close"] if "Close" in df else df.iloc[:, 3]
        s = col.dropna()
        if not s.empty:
            closes[symbols[0]] = float(s.iloc[-1])
        return closes

    for sym in symbols:
        try:
            s = df[sym]["Close"].dropna()
            if not s.empty:
                closes[sym] = float(s.iloc[-1])
        except Exception:
            continue
    return closes


def get_symbol_daily_returns(client, symbol: str, start_date: str, end_date: str) -> pd.Series:
    """Daily percentage returns derived from 5-minute bars (last close of each day)."""
    bars = get_historical_bars(client, symbol, start_date, end_date)
    if bars.empty:
        return pd.Series(dtype=float, name=symbol)
    daily_close = bars.groupby(bars.index.date)["close"].last()
    daily_close.index = pd.to_datetime(daily_close.index).tz_localize("UTC").tz_convert(ET)
    return daily_close.pct_change().dropna().rename(symbol)
