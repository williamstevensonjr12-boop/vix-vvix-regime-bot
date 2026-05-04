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
    "strategy", "vwap", "ema_fast", "ema_mid", "ema_slow",
    "atr", "rvol", "reason", "notes",
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
        f"side={getattr(signal, 'side', 'long')} "
        f"entry={signal.entry_price:.2f} qty={signal.qty} "
        f"setup={getattr(signal, 'setup', 'vwap_bounce')}"
    )


def log_trade_close(trade: dict):
    logger.info(
        f"[TRADE CLOSE] {trade.get('symbol')} | "
        f"exit={float(trade.get('exit_price', 0)):.2f} | "
        f"P&L=${float(trade.get('pnl', 0)):.2f} | "
        f"R={float(trade.get('r_multiple', 0)):.2f} | "
        f"{trade.get('result', '')} | {trade.get('reason', '')}"
    )


def _ensure_header(filepath: str, fields: list[str]) -> None:
    """
    Make sure the CSV at filepath has a header matching `fields`. If the file
    doesn't exist, do nothing (caller will create + write header). If it exists
    with a stale or mismatched header, rewrite the header in place — preserves
    data rows verbatim so we never drop history.
    """
    if not os.path.isfile(filepath):
        return
    try:
        with open(filepath, "r", newline="") as f:
            lines = f.readlines()
    except Exception:
        return
    if not lines:
        return
    expected = ",".join(fields)
    current = lines[0].rstrip("\r\n")
    if current == expected:
        return
    # Header drift detected — rewrite preserving rest of file
    logger.warning(f"{filepath}: header drift detected, rewriting "
                   f"({len(current.split(','))} cols → {len(fields)} cols)")
    with open(filepath, "w", newline="") as f:
        f.write(expected + "\n")
        f.writelines(lines[1:])


def save_trade(trade: dict, filepath: str = None):
    filepath = filepath or config.TRADES_CSV
    _ensure_header(filepath, TRADE_FIELDS)
    exists = os.path.isfile(filepath)
    with open(filepath, "a", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=TRADE_FIELDS, extrasaction="ignore")
        if not exists:
            writer.writeheader()
        writer.writerow({k: trade.get(k, "") for k in TRADE_FIELDS})


def save_daily_performance(perf: dict, filepath: str = None):
    filepath = filepath or config.PERFORMANCE_CSV
    _ensure_header(filepath, PERFORMANCE_FIELDS)
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


def update_trade_close(
    symbol: str,
    trade_date: str,
    exit_time: str,
    exit_price: float,
    reason: str,
    filepath: str = None,
) -> dict | None:
    """
    Find the most recent OPEN row matching (symbol, date) in trades.csv and
    update it with exit data — computes pnl, r_multiple, result.

    Returns the updated trade dict on success (so caller can push notifications),
    None if no matching open row was found.

    Idempotent: rewriting the file is safe (atomic via tmp + rename). Header
    is re-validated via _ensure_header before writing.
    """
    filepath = filepath or config.TRADES_CSV
    if not os.path.isfile(filepath):
        logger.warning(f"trades.csv not found at {filepath}")
        return None

    _ensure_header(filepath, TRADE_FIELDS)

    with open(filepath, "r", newline="") as f:
        reader = csv.DictReader(f)
        rows = list(reader)

    # Match strategy: most recent OPEN row for (symbol, date). Walk in reverse so
    # if there's been more than one entry on this symbol today, we close the latest.
    target_idx = None
    for i in range(len(rows) - 1, -1, -1):
        r = rows[i]
        if (r.get("symbol") == symbol
                and r.get("date") == str(trade_date)
                and (r.get("result") or "").upper() == "OPEN"):
            target_idx = i
            break
    if target_idx is None:
        logger.warning(f"No OPEN row found for {symbol} on {trade_date}")
        return None

    row = rows[target_idx]
    try:
        entry = float(row.get("entry_price") or 0)
        stop = float(row.get("stop_price") or 0)
        qty = int(float(row.get("qty") or 0))
        side = (row.get("side") or "long").lower()
    except (TypeError, ValueError):
        logger.warning(f"Bad numeric data in OPEN row for {symbol}")
        return None

    if side == "short":
        pnl = (entry - exit_price) * qty
        risk_per_share = max(stop - entry, 0.0001)
    else:
        pnl = (exit_price - entry) * qty
        risk_per_share = max(entry - stop, 0.0001)

    r_multiple = (pnl / qty) / risk_per_share if qty > 0 and risk_per_share > 0 else 0.0
    result = "WIN" if pnl > 0 else ("LOSS" if pnl < 0 else "FLAT")

    row["exit_time"] = exit_time
    row["exit_price"] = round(exit_price, 4)
    row["pnl"] = round(pnl, 2)
    row["r_multiple"] = round(r_multiple, 3)
    row["result"] = result
    existing_notes = row.get("notes", "")
    sep = "; " if existing_notes else ""
    row["notes"] = f"{existing_notes}{sep}exit:{reason}"

    # Atomic rewrite: tmp file + rename
    tmp = filepath + ".tmp"
    with open(tmp, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=TRADE_FIELDS, extrasaction="ignore")
        writer.writeheader()
        for r in rows:
            writer.writerow({k: r.get(k, "") for k in TRADE_FIELDS})
    os.replace(tmp, filepath)

    logger.info(
        f"[TRADE CLOSE] {symbol} | entry=${entry:.2f} → exit=${exit_price:.2f} "
        f"| qty={qty} | P&L=${pnl:+.2f} | R={r_multiple:+.2f} | {result} | {reason}"
    )
    return row


def build_trade_record(signal, order_id: str, today, entry_time: str) -> dict:
    return {
        "date": str(today),
        "symbol": signal.symbol,
        "side": getattr(signal, "side", "long"),
        "setup": getattr(signal, "setup", "vwap_bounce"),
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
        "strategy": "VWAP-Bounce",
        "vwap": signal.vwap,
        "ema_fast": getattr(signal, "ema_fast", ""),
        "ema_mid": getattr(signal, "ema_mid", ""),
        "ema_slow": getattr(signal, "ema_slow", ""),
        "atr": signal.atr,
        "rvol": getattr(signal, "rvol", ""),
        "reason": signal.reason,
        "notes": f"order_id={order_id}",
    }
