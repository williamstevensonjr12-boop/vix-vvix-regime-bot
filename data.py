"""
data.py — Alpaca 5-minute equity bars for the Cameron VWAP-Bounce bot.

_SilenceYFinance is exported here for the pre-market quotes script
(scripts/premarket_quotes.py) which is the only remaining yfinance consumer.
"""
from __future__ import annotations
import logging
from datetime import datetime
from zoneinfo import ZoneInfo

import pandas as pd
from alpaca.data.historical import StockHistoricalDataClient
from alpaca.data.requests import StockBarsRequest
from alpaca.data.timeframe import TimeFrame, TimeFrameUnit

import config
from net_utils import install_default_timeout, with_retry

logger = logging.getLogger(__name__)
ET = ZoneInfo(config.TIMEZONE)

_data_client: StockHistoricalDataClient | None = None


class _SilenceYFinance:
    """Context manager that suppresses yfinance's noisy ERROR-level output.

    yfinance emits ERROR logs for benign cases (e.g., a same-day request before
    a daily bar exists) which spammed our log on every restart. Callers handle
    empty DataFrames already, so the ERROR is misleading.
    """

    def __enter__(self):
        self._yf_log = logging.getLogger("yfinance")
        self._prev_level = self._yf_log.level
        self._yf_log.setLevel(logging.CRITICAL)
        return self

    def __exit__(self, *exc):
        self._yf_log.setLevel(self._prev_level)
        return False


def get_data_client() -> StockHistoricalDataClient:
    global _data_client
    if _data_client is None:
        _data_client = StockHistoricalDataClient(
            api_key=config.ALPACA_API_KEY,
            secret_key=config.ALPACA_SECRET_KEY,
        )
        install_default_timeout(_data_client)
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
        result = with_retry(f"get_stock_bars[{symbol}]", client.get_stock_bars, request)
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


def get_symbol_daily_returns(client, symbol: str, start_date: str, end_date: str) -> pd.Series:
    """Daily percentage returns derived from 5-minute bars (last close of each day)."""
    bars = get_historical_bars(client, symbol, start_date, end_date)
    if bars.empty:
        return pd.Series(dtype=float, name=symbol)
    daily_close = bars.groupby(bars.index.date)["close"].last()
    daily_close.index = pd.to_datetime(daily_close.index).tz_localize("UTC").tz_convert(ET)
    return daily_close.pct_change().dropna().rename(symbol)
