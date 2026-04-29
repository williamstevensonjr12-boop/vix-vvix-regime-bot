"""
broker.py — Alpaca paper trading wrapper.
paper=True is hardcoded. Live trading is blocked at both config and constructor level.
"""
from __future__ import annotations
import logging
from zoneinfo import ZoneInfo

from alpaca.trading.client import TradingClient
from alpaca.trading.requests import (
    MarketOrderRequest,
    GetOrdersRequest,
    TakeProfitRequest,
    StopLossRequest,
)
from alpaca.trading.enums import OrderSide, TimeInForce, OrderClass, QueryOrderStatus

import config

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
        acct = self.client.get_account()
        logger.info(
            f"Alpaca PAPER account connected | "
            f"equity=${float(acct.equity):,.2f} | "
            f"buying_power=${float(acct.buying_power):,.2f}"
        )

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
