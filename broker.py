"""
broker.py — Alpaca paper trading wrapper.
paper=True is hardcoded. Live trading is blocked at both config and constructor level.
"""
from __future__ import annotations
import logging
import time
from zoneinfo import ZoneInfo

from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

from alpaca.trading.client import TradingClient
from alpaca.trading.requests import (
    MarketOrderRequest,
    LimitOrderRequest,
    StopOrderRequest,
    GetOrdersRequest,
    TakeProfitRequest,
    StopLossRequest,
)
from alpaca.trading.enums import OrderSide, TimeInForce, OrderClass, QueryOrderStatus

import config

logger = logging.getLogger(__name__)
ET = ZoneInfo(config.TIMEZONE)

_CONNECT_TIMEOUT = 20   # seconds to establish TCP connection
_READ_TIMEOUT    = 30   # seconds to wait for a response


class _TimeoutAdapter(HTTPAdapter):
    """HTTPAdapter that enforces connect + read timeouts on every request."""

    def send(self, request, **kwargs):
        kwargs.setdefault("timeout", (_CONNECT_TIMEOUT, _READ_TIMEOUT))
        return super().send(request, **kwargs)


def _make_retry_adapter() -> _TimeoutAdapter:
    retry = Retry(
        total=3,
        backoff_factor=2,
        status_forcelist=[429, 500, 502, 503, 504],
        allowed_methods=["GET", "POST", "DELETE"],
    )
    return _TimeoutAdapter(max_retries=retry)


class AlpacaBroker:
    """Paper-only trading client. Raises RuntimeError if live keys detected."""

    def __init__(self):
        if not config.PAPER_TRADING:
            raise RuntimeError("PAPER_TRADING must be True. Live trading is not supported.")
        self.client = TradingClient(
            api_key=config.ALPACA_API_KEY,
            secret_key=config.ALPACA_SECRET_KEY,
            paper=True,
        )
        adapter = _make_retry_adapter()
        self.client._session.mount("https://", adapter)
        self.client._session.mount("http://", adapter)

        for attempt in range(1, 4):
            try:
                acct = self.client.get_account()
                logger.info(
                    f"Alpaca PAPER account connected | "
                    f"equity=${float(acct.equity):,.2f} | "
                    f"buying_power=${float(acct.buying_power):,.2f}"
                )
                break
            except Exception as e:
                if attempt == 3:
                    raise RuntimeError(f"Alpaca API unreachable after 3 attempts: {e}") from e
                logger.warning(f"Alpaca connect attempt {attempt} failed: {e} — retrying in {2**attempt}s")
                time.sleep(2 ** attempt)

    # ── Account ──────────────────────────────────────────────────────────────

    def get_account(self):
        return self.client.get_account()

    def get_equity(self) -> float:
        return float(self.client.get_account().equity)

    def get_buying_power(self) -> float:
        return float(self.client.get_account().buying_power)

    # ── Clock ─────────────────────────────────────────────────────────────────

    def is_market_open(self) -> bool:
        return self.client.get_clock().is_open

    def get_next_open(self):
        return self.client.get_clock().next_open

    # ── Positions ─────────────────────────────────────────────────────────────

    def get_positions(self) -> dict:
        positions = self.client.get_all_positions()
        return {
            pos.symbol: {
                "symbol": pos.symbol,
                "qty": int(float(pos.qty)),
                "avg_entry_price": float(pos.avg_entry_price),
                "current_price": float(pos.current_price) if pos.current_price else None,
                "unrealized_pl": float(pos.unrealized_pl) if pos.unrealized_pl else 0.0,
            }
            for pos in positions
        }

    # ── Orders ────────────────────────────────────────────────────────────────

    def get_open_orders(self) -> list:
        return self.client.get_orders(filter=GetOrdersRequest(status=QueryOrderStatus.OPEN))

    def get_todays_closed_orders(self) -> list:
        """Return all filled orders from today, sorted by fill time."""
        from datetime import datetime, timezone, timedelta
        from zoneinfo import ZoneInfo
        et = ZoneInfo("America/New_York")
        today_et = datetime.now(et).date()
        day_start = datetime(today_et.year, today_et.month, today_et.day,
                             tzinfo=et).astimezone(timezone.utc)
        try:
            orders = self.client.get_orders(filter=GetOrdersRequest(
                status=QueryOrderStatus.CLOSED,
                after=day_start,
                limit=200,
            ))
            return [o for o in orders if str(o.status) in ("filled", "OrderStatus.filled")]
        except Exception as e:
            logger.error(f"Failed to fetch today's orders: {e}")
            return []

    def submit_bracket_order(
        self,
        symbol: str,
        qty: int,
        stop_price: float,
        take_profit_price: float,
    ):
        try:
            order = self.client.submit_order(MarketOrderRequest(
                symbol=symbol,
                qty=qty,
                side=OrderSide.BUY,
                time_in_force=TimeInForce.DAY,
                order_class=OrderClass.BRACKET,
                stop_loss=StopLossRequest(stop_price=round(stop_price, 2)),
                take_profit=TakeProfitRequest(limit_price=round(take_profit_price, 2)),
            ))
            logger.info(
                f"ORDER ▶ {symbol} qty={qty} stop={stop_price:.2f} "
                f"target={take_profit_price:.2f} | id={order.id}"
            )
            return order
        except Exception as e:
            logger.error(f"Order failed {symbol}: {e}")
            return None

    def close_position(self, symbol: str) -> bool:
        try:
            self.client.close_position(symbol)
            logger.info(f"CLOSED: {symbol}")
            return True
        except Exception as e:
            logger.error(f"Close failed {symbol}: {e}")
            return False

    def close_all_positions(self) -> bool:
        try:
            self.client.close_all_positions(cancel_orders=True)
            logger.info("ALL POSITIONS CLOSED (EOD)")
            return True
        except Exception as e:
            logger.error(f"Close-all failed: {e}")
            return False

    def cancel_all_orders(self) -> bool:
        try:
            self.client.cancel_orders()
            logger.info("ALL ORDERS CANCELLED")
            return True
        except Exception as e:
            logger.error(f"Cancel-all failed: {e}")
            return False

    def submit_market_buy(self, symbol: str, qty: int):
        try:
            order = self.client.submit_order(MarketOrderRequest(
                symbol=symbol,
                qty=qty,
                side=OrderSide.BUY,
                time_in_force=TimeInForce.DAY,
            ))
            logger.info(f"MARKET BUY ▶ {symbol} qty={qty} | id={order.id}")
            return order
        except Exception as e:
            logger.error(f"Market buy failed {symbol}: {e}")
            return None

    def submit_stop_order(self, symbol: str, qty: int, stop_price: float):
        try:
            order = self.client.submit_order(StopOrderRequest(
                symbol=symbol,
                qty=qty,
                side=OrderSide.SELL,
                time_in_force=TimeInForce.DAY,
                stop_price=round(stop_price, 2),
            ))
            logger.info(f"STOP ▶ {symbol} qty={qty} stop={stop_price:.2f} | id={order.id}")
            return order
        except Exception as e:
            logger.error(f"Stop order failed {symbol}: {e}")
            return None

    def submit_limit_sell(self, symbol: str, qty: int, limit_price: float):
        try:
            order = self.client.submit_order(LimitOrderRequest(
                symbol=symbol,
                qty=qty,
                side=OrderSide.SELL,
                time_in_force=TimeInForce.DAY,
                limit_price=round(limit_price, 2),
            ))
            logger.info(f"LIMIT SELL ▶ {symbol} qty={qty} limit={limit_price:.2f} | id={order.id}")
            return order
        except Exception as e:
            logger.error(f"Limit sell failed {symbol}: {e}")
            return None

    def cancel_order(self, order_id: str) -> bool:
        try:
            self.client.cancel_order_by_id(order_id)
            logger.info(f"CANCELLED order {order_id}")
            return True
        except Exception as e:
            logger.warning(f"Cancel order {order_id} failed: {e}")
            return False

    def get_order_status(self, order_id: str) -> str:
        try:
            order = self.client.get_order_by_id(order_id)
            return str(order.status)
        except Exception as e:
            logger.warning(f"get_order_status {order_id} failed: {e}")
            return "unknown"

    def is_tradable(self, symbol: str) -> bool:
        try:
            asset = self.client.get_asset(symbol)
            return bool(asset.tradable) and str(asset.status) == "AssetStatus.active"
        except Exception as e:
            logger.warning(f"is_tradable check failed for {symbol}: {e}")
            return True  # fail-open
