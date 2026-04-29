"""
journal.py — Append-only trade and performance CSV logging.
"""
from __future__ import annotations
import csv
import logging
import os
from datetime import datetime
from zoneinfo import ZoneInfo

import config

logger = logging.getLogger(__name__)
ET = ZoneInfo(config.TIMEZONE)

TRADE_FIELDS = [
    "date", "symbol", "side", "setup", "entry_time", "exit_time",
    "entry_price", "stop_price", "target_price", "exit_price",
    "qty", "pnl", "r_multiple", "result",
    "regime", "vix_beta", "regime_size", "vol_mult",
    "atr", "vwap", "orb_high", "reason", "notes",
]

PERFORMANCE_FIELDS = [
    "date", "regime", "trades", "wins", "losses",
    "gross_pnl", "win_rate", "avg_win", "avg_loss",
    "profit_factor", "daily_return_pct", "equity",
]


def log_signal(symbol: str, signal, taken: bool = True):
    status = "TAKEN" if taken else "SKIPPED"
    logger.info(
        f"[SIGNAL {status}] {symbol} | "
        f"entry={getattr(signal, 'entry_price', '?'):.2f} "
        f"stop={getattr(signal, 'stop_price', '?'):.2f} "
        f"target={getattr(signal, 'target_price', '?'):.2f} "
        f"qty={getattr(signal, 'qty', 0)} | {getattr(signal, 'reason', '')}"
    )


def log_trade_open(signal):
    now = datetime.now(ET).strftime("%Y-%m-%d %H:%M:%S")
    logger.info(
        f"[TRADE OPEN] {now} | {signal.symbol} | "
        f"entry={signal.entry_price:.2f} qty={signal.qty} "
        f"regime={signal.regime}"
    )


def log_trade_close(trade: dict):
    logger.info(
        f"[TRADE CLOSE] {trade.get('symbol')} | "
        f"exit={float(trade.get('exit_price', 0)):.2f} | "
        f"P&L=${float(trade.get('pnl', 0)):.2f} | "
        f"R={float(trade.get('r_multiple', 0)):.2f} | "
        f"{trade.get('result', '')} | {trade.get('reason', '')}"
    )


def save_trade(trade: dict, filepath: str = None):
    filepath = filepath or config.TRADES_CSV
    exists = os.path.isfile(filepath)
    with open(filepath, "a", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=TRADE_FIELDS, extrasaction="ignore")
        if not exists:
            writer.writeheader()
        writer.writerow({k: trade.get(k, "") for k in TRADE_FIELDS})


def save_daily_performance(perf: dict, filepath: str = None):
    filepath = filepath or config.PERFORMANCE_CSV
    exists = os.path.isfile(filepath)
    with open(filepath, "a", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=PERFORMANCE_FIELDS, extrasaction="ignore")
        if not exists:
            writer.writeheader()
        writer.writerow({k: perf.get(k, "") for k in PERFORMANCE_FIELDS})


def load_trades(filepath: str = None) -> list:
    filepath = filepath or config.TRADES_CSV
    if not os.path.isfile(filepath):
        return []
    with open(filepath, "r") as f:
        return list(csv.DictReader(f))


def build_trade_record(signal, order_id: str, today, entry_time: str) -> dict:
    return {
        "date": str(today),
        "symbol": signal.symbol,
        "side": getattr(signal, "side", "long"),
        "setup": getattr(signal, "setup", "orb"),
        "entry_time": entry_time,
        "exit_time": "",
        "entry_price": signal.entry_price,
        "stop_price": signal.stop_price,
        "target_price": signal.target_price,
        "exit_price": "",
        "qty": signal.qty,
        "pnl": "",
        "r_multiple": "",
        "result": "OPEN",
        "regime": signal.regime,
        "vix_beta": round(signal.vix_beta, 4),
        "regime_size": signal.regime_size_factor,
        "vol_mult": signal.vol_multiplier,
        "atr": signal.atr,
        "vwap": signal.vwap,
        "orb_high": signal.orb_high,
        "reason": signal.reason,
        "notes": f"order_id={order_id}",
    }
