"""
broker.py — Alpaca paper trading wrapper.
paper=True is hardcoded. Live trading is blocked at both config and constructor level.
"""
from __future__ import annotations
import logging
from zoneinfo import ZoneInfo

import time as _time

from alpaca.trading.client import TradingClient
from alpaca.trading.requests import (
    MarketOrderRequest,
    LimitOrderRequest,
    GetOrdersRequest,
    TakeProfitRequest,
    StopLossRequest,
)
from alpaca.trading.enums import OrderSide, TimeInForce, OrderClass, QueryOrderStatus

# Quote fetching uses the data SDK (separate from trading SDK)
from alpaca.data.historical import StockHistoricalDataClient
from alpaca.data.requests import StockLatestQuoteRequest

import config
from net_utils import install_default_timeout, with_retry

logger = logging.getLogger(__name__)
ET = ZoneInfo(config.TIMEZONE)


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
        install_default_timeout(self.client)
        # Lazy-init data client for live quotes (limit-order entries need this)
        self._data_client = None
        acct = with_retry("get_account (init)", self.client.get_account)
        logger.info(
            f"Alpaca PAPER account connected | "
            f"equity=${float(acct.equity):,.2f} | "
            f"buying_power=${float(acct.buying_power):,.2f}"
        )

    # ── Account ──────────────────────────────────────────────────────────────

    def get_account(self):
        return with_retry("get_account", self.client.get_account)

    def get_equity(self) -> float:
        return float(with_retry("get_account", self.client.get_account).equity)

    def get_buying_power(self) -> float:
        return float(with_retry("get_account", self.client.get_account).buying_power)

    # ── Clock ─────────────────────────────────────────────────────────────────

    def is_market_open(self) -> bool:
        return with_retry("get_clock", self.client.get_clock).is_open

    def get_next_open(self):
        return with_retry("get_clock", self.client.get_clock).next_open

    # ── Positions ─────────────────────────────────────────────────────────────

    def get_positions(self) -> dict:
        positions = with_retry("get_all_positions", self.client.get_all_positions)
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
        return with_retry(
            "get_orders",
            self.client.get_orders,
            filter=GetOrdersRequest(status=QueryOrderStatus.OPEN),
        )

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

    def submit_short_bracket_order(
        self,
        symbol: str,
        qty: int,
        stop_price: float,
        take_profit_price: float,
    ):
        """Short entry: SELL to open with stop above entry and target below."""
        try:
            order = self.client.submit_order(MarketOrderRequest(
                symbol=symbol,
                qty=qty,
                side=OrderSide.SELL,
                time_in_force=TimeInForce.DAY,
                order_class=OrderClass.BRACKET,
                stop_loss=StopLossRequest(stop_price=round(stop_price, 2)),
                take_profit=TakeProfitRequest(limit_price=round(take_profit_price, 2)),
            ))
            logger.info(
                f"SHORT ▶ {symbol} qty={qty} stop={stop_price:.2f} "
                f"target={take_profit_price:.2f} | id={order.id}"
            )
            return order
        except Exception as e:
            logger.error(f"Short order failed {symbol}: {e}")
            return None

    # ── Limit-order entries (bounded slippage) ───────────────────────────────
    # These are the Phase 1 limit-order entry path. Behind config.USE_LIMIT_ORDER_ENTRIES.
    # Pattern: marketable limit at ask + buffer (long) or bid - buffer (short),
    # with bracket children for stop + target. Time-in-force from config; default IOC.

    def _get_data_client(self):
        if self._data_client is None:
            self._data_client = StockHistoricalDataClient(
                api_key=config.ALPACA_API_KEY,
                secret_key=config.ALPACA_SECRET_KEY,
            )
            install_default_timeout(self._data_client)
        return self._data_client

    def get_latest_quote(self, symbol: str) -> dict | None:
        """
        Return {'bid', 'ask', 'ts', 'age_sec'} or None on failure.

        Used by the limit-order entry path to compute the marketable limit
        price. Caller should check `age_sec` against config.LIMIT_ORDER_QUOTE_MAX_AGE_SEC
        and skip the entry if the quote is stale.
        """
        try:
            from datetime import datetime, timezone
            client = self._get_data_client()
            req = StockLatestQuoteRequest(symbol_or_symbols=symbol)
            quotes = with_retry("get_stock_latest_quote", client.get_stock_latest_quote, req)
            q = quotes.get(symbol) if isinstance(quotes, dict) else getattr(quotes, symbol, None)
            if q is None:
                return None
            bid = float(getattr(q, "bid_price", 0) or 0)
            ask = float(getattr(q, "ask_price", 0) or 0)
            ts = getattr(q, "timestamp", None)
            age = 0.0
            if ts is not None:
                try:
                    now = datetime.now(timezone.utc)
                    age = (now - ts).total_seconds()
                except Exception:
                    age = 0.0
            return {"bid": bid, "ask": ask, "ts": ts, "age_sec": age}
        except Exception as e:
            logger.warning(f"Quote fetch failed for {symbol}: {e}")
            return None

    def submit_bracket_limit_order(
        self,
        symbol: str,
        qty: int,
        limit_price: float,
        stop_price: float,
        take_profit_price: float,
        side: str = "long",
    ):
        """
        Submit a BRACKET LIMIT entry order. Returns the Order object on success,
        or None on failure (including the "limit didn't fill" case for IOC).

        Caller should check `order.status` after submit:
          - filled / partially_filled → entry took
          - canceled / expired (with no fills)→ entry missed (price ran)
          - new / accepted → still pending (DAY tif only — won't happen with IOC)

        IOC bracket parents are accepted by Alpaca paper accounts; if the parent
        cancels unfilled, the bracket children never attach. Clean miss.
        """
        order_side = OrderSide.BUY if side.lower() == "long" else OrderSide.SELL
        tif_str = (getattr(config, "LIMIT_ORDER_TIF", "ioc") or "ioc").lower()
        tif = {
            "ioc": TimeInForce.IOC,
            "fok": TimeInForce.FOK,
            "day": TimeInForce.DAY,
        }.get(tif_str, TimeInForce.IOC)

        try:
            order = self.client.submit_order(LimitOrderRequest(
                symbol=symbol,
                qty=qty,
                side=order_side,
                time_in_force=tif,
                limit_price=round(limit_price, 2),
                order_class=OrderClass.BRACKET,
                stop_loss=StopLossRequest(stop_price=round(stop_price, 2)),
                take_profit=TakeProfitRequest(limit_price=round(take_profit_price, 2)),
            ))
            logger.info(
                f"LIMIT ORDER ▶ {symbol} {side} qty={qty} "
                f"limit={limit_price:.2f} stop={stop_price:.2f} target={take_profit_price:.2f} "
                f"tif={tif_str} | id={order.id}"
            )
            return order
        except Exception as e:
            logger.error(f"Limit order failed {symbol} ({side}): {e}")
            return None

    def get_recent_closing_fill(self, symbol: str, since_dt=None):
        """
        Return (exit_price, exit_time_str, exit_reason) for the most recent CLOSING
        fill (sell-to-close for long, buy-to-cover for short) on `symbol`. Used by
        the scan loop to reconcile position closures into trades.csv.

        `exit_reason` is best-effort: 'TARGET' if filled at limit child, 'STOP' if
        stop-loss child, 'MANUAL' otherwise. None if no matching fill found.
        """
        try:
            from alpaca.trading.requests import GetOrdersRequest
            from alpaca.trading.enums import QueryOrderStatus
            req = GetOrdersRequest(
                status=QueryOrderStatus.CLOSED,
                symbols=[symbol],
                limit=20,
            )
            orders = self.client.get_orders(filter=req)
        except Exception as e:
            logger.warning(f"get_recent_closing_fill({symbol}) failed: {e}")
            return None

        # Walk from most recent to oldest, look for filled close legs
        for o in orders:
            status = str(getattr(o, "status", "")).lower()
            if status != "filled":
                continue
            side = str(getattr(o, "side", "")).lower()
            otype = str(getattr(o, "order_type", "")).lower()
            filled_at = getattr(o, "filled_at", None)
            if since_dt is not None and filled_at is not None:
                try:
                    if filled_at < since_dt:
                        continue
                except Exception:
                    pass
            filled_price = getattr(o, "filled_avg_price", None)
            if filled_price is None:
                continue
            # Classify reason: limit fills → TARGET, stop-related → STOP, else MANUAL
            reason = "MANUAL"
            if "limit" in otype:
                reason = "TARGET"
            elif "stop" in otype:
                reason = "STOP"
            time_str = filled_at.astimezone(ET).strftime("%H:%M:%S") if filled_at else ""
            return (float(filled_price), time_str, reason)
        return None

    def order_filled(self, order, poll_seconds: float = 1.5) -> bool:
        """
        Return True if the order is filled (or partially filled), False otherwise.

        For IOC orders, Alpaca usually settles within a few hundred ms. We poll
        briefly to give it time before declaring a miss.
        """
        if order is None:
            return False
        end = _time.monotonic() + poll_seconds
        order_id = getattr(order, "id", None)
        last_status = str(getattr(order, "status", "")).lower()
        while True:
            if last_status in ("filled", "partially_filled"):
                return True
            if last_status in ("canceled", "expired", "rejected"):
                return False
            if _time.monotonic() >= end or order_id is None:
                return False
            try:
                refreshed = self.client.get_order_by_id(order_id)
                last_status = str(getattr(refreshed, "status", "")).lower()
            except Exception:
                return False
            _time.sleep(0.1)

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
