"""
main.py — Entry point for the Cameron VWAP-Bounce paper-trading bot.

╔══════════════════════════════════════════════════════════════╗
║   CAMERON VWAP-BOUNCE BOT  —  PAPER TRADING ONLY            ║
║   ⚠  NOT FINANCIAL ADVICE  ⚠  DO NOT USE WITH REAL MONEY    ║
╚══════════════════════════════════════════════════════════════╝

Usage:
  python main.py paper                          # live paper trading
  python main.py tracker --days 30              # performance dashboard
  python main.py dashboard                      # generate dashboard.html
  python main.py backtest --start ... --end ... # (Phase 5 will rewire)
"""
from __future__ import annotations
import argparse
import logging
import time
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

import config  # safety check happens at import

import data as mkt_data
import strategy
import risk as rsk
from broker import AlpacaBroker
import journal
import notifications as notify

logger = logging.getLogger(__name__)
ET = ZoneInfo(config.TIMEZONE)

BANNER = """
╔══════════════════════════════════════════════════════════════╗
║        CAMERON VWAP-BOUNCE BOT  —  v2.0                     ║
║                                                              ║
║  ⚠  PAPER TRADING ONLY                                       ║
║  ⚠  NOT FINANCIAL ADVICE                                     ║
║  ⚠  DO NOT USE WITH REAL MONEY                               ║
╚══════════════════════════════════════════════════════════════╝
"""


# ── Logging ──────────────────────────────────────────────────────────────────

def setup_logging(debug: bool = False):
    logging.basicConfig(
        level=logging.DEBUG if debug else logging.INFO,
        format="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
        handlers=[
            logging.StreamHandler(),
            logging.FileHandler(config.LOG_FILE),
        ],
    )


# ── Paper trading ─────────────────────────────────────────────────────────────

def cmd_paper(debug: bool = False):
    import pandas as pd

    setup_logging(debug)
    print(BANNER)
    logger.info("Mode: PAPER TRADING — Cameron VWAP-Bounce")

    broker = AlpacaBroker()
    data_client = mkt_data.get_data_client()

    # Wait for market open
    if not broker.is_market_open():
        next_open = broker.get_next_open()
        logger.info(f"Market closed. Next open: {next_open}. Waiting...")
        while not broker.is_market_open():
            time.sleep(30)

    # ── Pre-market setup ──────────────────────────────────────────────────
    today = datetime.now(ET).date()
    start_str = (today - timedelta(days=60)).isoformat()
    end_str = today.isoformat()

    # Daily returns (per-symbol, 60d window) — used by risk.py for realized_vol
    # in vol-adjusted position sizing. Same lookback as REALIZED_VOL_LOOKBACK
    # plus margin so the rolling window has enough history.
    logger.info("Loading daily returns (for realized-vol sizing)...")
    daily_returns = {
        sym: mkt_data.get_symbol_daily_returns(data_client, sym, start_str, end_str)
        for sym in config.MOMENTUM_UNIVERSE
    }

    # Daily state
    account = broker.get_account()
    daily_start_equity = float(account.equity)
    trades_today = 0
    prior_open_symbols: set[str] = set()
    rsk.reset_kill_switch()

    logger.info(
        f"Market OPEN | equity=${daily_start_equity:,.2f} | "
        f"universe={len(config.MOMENTUM_UNIVERSE)} symbols ({', '.join(config.MOMENTUM_UNIVERSE)})"
    )

    # ── Trading loop ──────────────────────────────────────────────────────
    while True:
        now = datetime.now(ET)
        current_time = now.strftime("%H:%M")

        # EOD
        if current_time >= config.CLOSE_ALL_TIME:
            logger.info("EOD: closing all positions")
            pre_eod_positions = broker.get_positions()
            broker.close_all_positions()
            time.sleep(2)
            for sym_eod in pre_eod_positions.keys():
                try:
                    fill = broker.get_recent_closing_fill(sym_eod)
                    if fill is None:
                        logger.warning(f"EOD: no closing fill found for {sym_eod}")
                        continue
                    exit_price, exit_time_str, _reason = fill
                    updated = journal.update_trade_close(
                        symbol=sym_eod,
                        trade_date=str(today),
                        exit_time=exit_time_str or now.strftime("%H:%M:%S"),
                        exit_price=exit_price,
                        reason="EOD_FORCE_CLOSE",
                    )
                    if updated:
                        notify.exit(
                            symbol=updated.get("symbol"),
                            side=updated.get("side", "long"),
                            entry=float(updated.get("entry_price") or 0),
                            exit_price=float(updated.get("exit_price") or 0),
                            qty=int(float(updated.get("qty") or 0)),
                            pnl=float(updated.get("pnl") or 0),
                            r_multiple=float(updated.get("r_multiple") or 0),
                            reason="EOD force-close",
                        )
                except Exception as e:
                    logger.error(f"EOD reconcile failed for {sym_eod}: {e}", exc_info=True)
            _save_daily_summary(broker, daily_start_equity, today)
            logger.info("Session complete.")
            break

        if current_time >= config.LAST_ENTRY_TIME:
            time.sleep(60)
            continue

        # Kill switch
        if rsk.is_kill_switch_active():
            logger.critical("Kill switch active. No new trades.")
            time.sleep(60)
            continue

        account = broker.get_account()
        equity = float(account.equity)
        daily_pnl = equity - daily_start_equity
        open_positions = broker.get_positions()

        # Detect closures since last scan and reconcile to trades.csv.
        current_open_symbols = set(open_positions.keys())
        closed_syms = prior_open_symbols - current_open_symbols
        for sym_closed in closed_syms:
            try:
                fill = broker.get_recent_closing_fill(sym_closed)
                if fill is None:
                    logger.warning(f"closure detected for {sym_closed} but no fill found")
                    continue
                exit_price, exit_time_str, reason = fill
                updated = journal.update_trade_close(
                    symbol=sym_closed,
                    trade_date=str(today),
                    exit_time=exit_time_str,
                    exit_price=exit_price,
                    reason=reason,
                )
                if updated:
                    notify.exit(
                        symbol=updated.get("symbol"),
                        side=updated.get("side", "long"),
                        entry=float(updated.get("entry_price") or 0),
                        exit_price=float(updated.get("exit_price") or 0),
                        qty=int(float(updated.get("qty") or 0)),
                        pnl=float(updated.get("pnl") or 0),
                        r_multiple=float(updated.get("r_multiple") or 0),
                        reason=reason,
                    )
            except Exception as e:
                logger.error(f"closure reconcile failed for {sym_closed}: {e}", exc_info=True)
        prior_open_symbols = current_open_symbols

        logger.info(
            f"Scan {current_time} | equity=${equity:,.2f} P&L=${daily_pnl:+,.2f} | "
            f"pos={len(open_positions)}/{config.MAX_OPEN_POSITIONS} | "
            f"trades={trades_today}/{config.MAX_TRADES_PER_DAY}"
        )

        can_trade, limit_reason = rsk.check_daily_limits(trades_today, daily_pnl, daily_start_equity)
        if not can_trade:
            logger.warning(f"Trading halted: {limit_reason}")
            time.sleep(60)
            continue

        pdt_ok, pdt_reason = rsk.check_pdt_constraints(account)
        if not pdt_ok:
            logger.warning(f"Trading halted: {pdt_reason}")
            time.sleep(60)
            continue

        # Scan the 8-mega-cap universe for VWAP-Bounce setups (long + short).
        # Cameron's framework allows either direction depending on which side
        # of VWAP / EMA stack the symbol is on; we check both per symbol.
        for sym in config.MOMENTUM_UNIVERSE:
            try:
                bars = mkt_data.get_today_bars(data_client, sym)
                if bars.empty:
                    continue

                sym_daily_ret = daily_returns.get(sym, pd.Series(dtype=float))

                sig = strategy.check_entry_signal(
                    symbol=sym,
                    bars=bars,
                    account_equity=equity,
                    open_positions=open_positions,
                    trades_today=trades_today,
                    daily_pnl=daily_pnl,
                    daily_start_equity=daily_start_equity,
                    daily_returns=sym_daily_ret,
                )
                side = "long"
                if sig is None:
                    sig = strategy.check_short_signal(
                        symbol=sym,
                        bars=bars,
                        account_equity=equity,
                        open_positions=open_positions,
                        trades_today=trades_today,
                        daily_pnl=daily_pnl,
                        daily_start_equity=daily_start_equity,
                        daily_returns=sym_daily_ret,
                    )
                    side = "short"

                if sig is None:
                    continue

                journal.log_signal(sym, sig, taken=True)
                order, filled, miss_reason = _submit_entry(broker, sig, side=side)

                if order and filled:
                    trades_today += 1
                    journal.log_trade_open(sig)
                    journal.save_trade(
                        journal.build_trade_record(sig, str(order.id), today, now.strftime("%H:%M:%S"))
                    )
                    notify.entry(
                        symbol=sym, side=side,
                        entry=sig.entry_price, stop=sig.stop_price, target=sig.target_price,
                        qty=sig.qty,
                        reason=getattr(sig, "reason", ""),
                    )
                elif miss_reason:
                    logger.info(f"ENTRY MISSED {side} {sym}: {miss_reason}")

            except Exception as e:
                logger.error(f"Error processing {sym}: {e}", exc_info=True)

        time.sleep(60)


def _submit_entry(broker, sig, side: str = "long"):
    """Submit entry order. Returns (order, filled, miss_reason).

    USE_LIMIT_ORDER_ENTRIES=False: market bracket; treat creation as fill.
    USE_LIMIT_ORDER_ENTRIES=True : marketable-limit IOC bracket. If parent
    doesn't fill in poll window, returns filled=False with miss_reason.
    """
    if not getattr(config, "USE_LIMIT_ORDER_ENTRIES", False):
        if side == "long":
            order = broker.submit_bracket_order(
                symbol=sig.symbol, qty=sig.qty,
                stop_price=sig.stop_price, take_profit_price=sig.target_price,
            )
        else:
            order = broker.submit_short_bracket_order(
                symbol=sig.symbol, qty=sig.qty,
                stop_price=sig.stop_price, take_profit_price=sig.target_price,
            )
        return order, bool(order), ""

    quote = broker.get_latest_quote(sig.symbol)
    if quote is None:
        return None, False, "quote fetch failed"
    max_age = getattr(config, "LIMIT_ORDER_QUOTE_MAX_AGE_SEC", 2.0)
    if quote["age_sec"] > max_age:
        return None, False, f"stale quote ({quote['age_sec']:.1f}s > {max_age}s)"
    if quote["ask"] <= 0 or quote["bid"] <= 0:
        return None, False, "missing bid/ask"

    buf = getattr(config, "LIMIT_ORDER_BUFFER_PCT", 0.0010)
    if side == "long":
        limit_price = quote["ask"] * (1 + buf)
    else:
        limit_price = quote["bid"] * (1 - buf)
    sig.limit_price = round(limit_price, 2)
    sig.entry_price = sig.limit_price

    order = broker.submit_bracket_limit_order(
        symbol=sig.symbol, qty=sig.qty,
        limit_price=sig.limit_price,
        stop_price=sig.stop_price,
        take_profit_price=sig.target_price,
        side=side,
    )
    if order is None:
        return None, False, "submit failed"

    poll = getattr(config, "LIMIT_ORDER_FILL_POLL_SECONDS", 1.5)
    filled = broker.order_filled(order, poll_seconds=poll)
    if not filled:
        return order, False, f"limit ${sig.limit_price:.2f} not filled in {poll}s window"
    return order, True, ""


def _save_daily_summary(broker, daily_start_equity, today):
    account = broker.get_account()
    final_eq = float(account.equity)
    day_pnl = final_eq - daily_start_equity
    trades = journal.load_trades()
    today_trades = [t for t in trades if t.get("date") == str(today)]
    wins = [t for t in today_trades if t.get("result") == "WIN"]
    losses = [t for t in today_trades if t.get("result") == "LOSS"]
    gp = sum(float(t.get("pnl", 0)) for t in wins)
    gl = abs(sum(float(t.get("pnl", 0)) for t in losses))
    journal.save_daily_performance({
        "date": str(today),
        "trades": len(today_trades), "wins": len(wins), "losses": len(losses),
        "gross_pnl": round(day_pnl, 2),
        "win_rate": len(wins) / len(today_trades) if today_trades else 0,
        "avg_win": gp / len(wins) if wins else 0,
        "avg_loss": -gl / len(losses) if losses else 0,
        "profit_factor": gp / gl if gl > 0 else 0,
        "daily_return_pct": round(day_pnl / daily_start_equity * 100, 4),
        "equity": round(final_eq, 2),
    })
    logger.info(f"Day complete | P&L=${day_pnl:+,.2f} | equity=${final_eq:,.2f}")

    notify.eod(
        date_str=str(today), pnl=day_pnl,
        trades=len(today_trades), wins=len(wins), losses=len(losses),
        equity=final_eq,
        killswitch=rsk.is_kill_switch_active(),
    )


# ── Standalone commands ───────────────────────────────────────────────────────

def cmd_tracker(days: int = 30):
    import tracker
    tracker.run_dashboard(window_days=days)


def cmd_dashboard():
    import dashboard
    dashboard.build_dashboard()


def cmd_backtest(start: str, end: str, equity: float, debug: bool = False):
    """Backtest stub. Phase 5 will add a VWAP-Bounce backtester; until then the
    CLI subcommand exists only so callers don't get an argparse error."""
    setup_logging(debug)
    print(BANNER)
    logger.warning(
        "backtest mode is not implemented — Phase 5 will add a VWAP-Bounce "
        "backtester. No prior backtest engine exists in the repo."
    )


# ── CLI ───────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description="Cameron VWAP-Bounce Bot")
    parser.add_argument("--debug", action="store_true")
    sub = parser.add_subparsers(dest="mode", required=True)

    sub.add_parser("paper", help="Live paper trading")
    sub.add_parser("dashboard", help="Generate HTML dashboard")

    tr = sub.add_parser("tracker", help="Performance dashboard (rolling window)")
    tr.add_argument("--days", type=int, default=30)

    bt = sub.add_parser("backtest", help="(Phase 5) Historical backtest")
    bt.add_argument("--start", required=True, metavar="YYYY-MM-DD")
    bt.add_argument("--end", required=True, metavar="YYYY-MM-DD")
    bt.add_argument("--equity", type=float, default=config.INITIAL_EQUITY)

    args = parser.parse_args()

    if args.mode == "paper":
        cmd_paper(args.debug)
    elif args.mode == "tracker":
        cmd_tracker(args.days)
    elif args.mode == "dashboard":
        cmd_dashboard()
    elif args.mode == "backtest":
        cmd_backtest(args.start, args.end, args.equity, args.debug)


if __name__ == "__main__":
    main()
