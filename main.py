"""
main.py — Entry point for VIX_VVIX_Regime_Alpha_Bot.

╔══════════════════════════════════════════════════════════════╗
║   VIX / VVIX REGIME ALPHA BOT  —  PAPER TRADING ONLY        ║
║   ⚠  NOT FINANCIAL ADVICE  ⚠  DO NOT USE WITH REAL MONEY    ║
╚══════════════════════════════════════════════════════════════╝

Usage:
  python main.py paper                          # live paper trading
  python main.py backtest --start 2024-01-02 --end 2024-06-28
  python main.py backtest --start 2024-01-02 --end 2024-06-28 --equity 50000
  python main.py regime-status                  # print current regime and exit
"""
from __future__ import annotations
import argparse
import logging
import time
from datetime import datetime
from zoneinfo import ZoneInfo

import config  # safety check happens at import

import data as mkt_data
from regime import RegimeEngine
from vix_factor import VIXBetaRanker
import vvix_filter as vvix
import sentiment as sent_mod
from sector_rotation import get_rotation_universe, rotation_summary
from market_neutral import MarketNeutralOverlay
import strategy
import risk as rsk
from broker import AlpacaBroker
import journal
import performance as perf

logger = logging.getLogger(__name__)
ET = ZoneInfo(config.TIMEZONE)

BANNER = """
╔══════════════════════════════════════════════════════════════╗
║        VIX / VVIX REGIME ALPHA BOT  —  v1.0                 ║
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


# ── Regime status (standalone command) ───────────────────────────────────────

def cmd_regime_status(debug: bool = False):
    setup_logging(debug)
    print(BANNER)
    snapshot = mkt_data.get_current_vol_snapshot()
    data_client = mkt_data.get_data_client()
    spy_df = mkt_data.get_spy_daily(
        start_date=(datetime.now(ET).date().replace(day=1)).isoformat(),
        end_date=datetime.now(ET).date().isoformat(),
    )

    import pandas as pd
    vix_s = pd.Series([snapshot["vix"]])
    spy_s = spy_df["close"] if not spy_df.empty and "close" in spy_df else pd.Series([400.0])

    engine = RegimeEngine()
    state = engine.compute(
        vix_series=vix_s,
        vvix_level=snapshot["vvix"],
        put_call_ratio=snapshot["put_call_ratio"],
        spy_series=spy_s,
        vix3m_level=snapshot["vix3m"],
    )
    print(f"\n{state.summary()}")
    print(rotation_summary(state))

    vvix_f = vvix.regime_filter(snapshot["vvix"])
    print(f"\nVVIX Filter: {vvix_f.reason}")

    pc_s = import_pd().Series([snapshot["put_call_ratio"]])
    sent_state = sent_mod.classify_put_call(pc_s)
    print(f"Sentiment  : {sent_state.reason}")


def import_pd():
    import pandas as pd
    return pd


# ── Paper trading ─────────────────────────────────────────────────────────────

def cmd_paper(debug: bool = False):
    import pandas as pd

    setup_logging(debug)
    print(BANNER)
    logger.info("Mode: PAPER TRADING")

    broker = AlpacaBroker()
    data_client = mkt_data.get_data_client()
    regime_engine = RegimeEngine()
    vix_ranker = VIXBetaRanker()
    neutral_overlay = MarketNeutralOverlay(vix_ranker, paper_mode=True)

    # Wait for market open
    if not broker.is_market_open():
        next_open = broker.get_next_open()
        logger.info(f"Market closed. Next open: {next_open}. Waiting...")
        while not broker.is_market_open():
            time.sleep(30)

    # ── Pre-market setup ──────────────────────────────────────────────────
    logger.info("Computing pre-market regime...")
    snapshot = mkt_data.get_current_vol_snapshot()
    today = datetime.now(ET).date()
    start_str = (today.replace(day=max(1, today.day - 90))).isoformat()
    end_str = today.isoformat()

    vol_df = mkt_data.get_vix_history(start_str, end_str)
    spy_df = mkt_data.get_spy_daily(start_str, end_str)
    pc_series = mkt_data.get_put_call_history(start_str, end_str)

    vix_s = vol_df["vix"].dropna() if not vol_df.empty and "vix" in vol_df else pd.Series([snapshot["vix"]])
    spy_s = spy_df["close"].dropna() if not spy_df.empty else pd.Series([400.0])
    pc_val = float(pc_series.dropna().iloc[-1]) if not pc_series.empty else 0.9

    regime_state = regime_engine.compute(
        vix_series=vix_s,
        vvix_level=snapshot["vvix"],
        put_call_ratio=pc_val,
        spy_series=spy_s,
        vix3m_level=snapshot["vix3m"],
    )
    logger.info(regime_state.summary())

    # VIX beta pre-fit
    logger.info("Fitting VIX beta factors...")
    all_sym_bars = mkt_data.get_multiple_symbols_bars(
        data_client, config.ALL_SYMBOLS, start_str, end_str
    )
    daily_returns = {
        sym: mkt_data.get_symbol_daily_returns(data_client, sym, start_str, end_str)
        for sym in config.ALL_SYMBOLS
    }
    vix_ranker.fit(daily_returns, vix_s)
    logger.info(vix_ranker.summary_table().to_string(index=False))

    # Determine active universe
    active_universe = vix_ranker.rank(
        regime_state.active_universe,
        regime_mode="defensive" if regime_state.regime.value.startswith("C") else "momentum",
    )
    logger.info(f"Active universe: {active_universe}")
    logger.info(rotation_summary(regime_state))

    # Daily state
    account = broker.get_account()
    daily_start_equity = float(account.equity)
    trades_today = 0
    rsk.reset_kill_switch()

    logger.info(f"Market OPEN | equity=${daily_start_equity:,.2f} | regime={regime_state.regime.value}")

    # ── Trading loop ──────────────────────────────────────────────────────
    while True:
        now = datetime.now(ET)
        current_time = now.strftime("%H:%M")

        # EOD
        if current_time >= config.CLOSE_ALL_TIME:
            logger.info(f"EOD: closing all positions")
            broker.close_all_positions()
            _save_daily_summary(broker, daily_start_equity, today, regime_state.regime.value)
            logger.info("Session complete.")
            break

        if current_time < config.ORB_END_TIME:
            time.sleep(30)
            continue

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

        # Refresh VVIX intraday
        fresh_snap = mkt_data.get_current_vol_snapshot()
        vvix_filter_result = vvix.regime_filter(fresh_snap["vvix"])
        pc_series_live = pd.Series([fresh_snap["put_call_ratio"]])
        sent_state = sent_mod.classify_put_call(pc_series_live)

        logger.info(
            f"Scan {current_time} | equity=${equity:,.2f} P&L=${daily_pnl:+,.2f} | "
            f"pos={len(open_positions)}/{config.MAX_OPEN_POSITIONS} | "
            f"trades={trades_today}/{config.MAX_TRADES_PER_DAY} | "
            f"VVIX={fresh_snap['vvix']:.0f} {vvix_filter_result.reason[:30]}"
        )

        can_trade, limit_reason = rsk.check_daily_limits(trades_today, daily_pnl, daily_start_equity)
        if not can_trade:
            logger.warning(f"Trading halted: {limit_reason}")
            time.sleep(60)
            continue

        # Crisis alpha sleeve
        if neutral_overlay.should_activate(regime_state):
            current_prices = {sym: float(broker.get_account().equity) for sym in config.CRISIS_ALPHA_LONG}
            neutral_overlay.build_portfolio(regime_state, equity, current_prices)

        # Scan symbols
        for sym in active_universe:
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
                    regime_state=regime_state,
                    vvix_filter=vvix_filter_result,
                    sentiment_state=sent_state,
                    vix_beta=vix_ranker.get_beta(sym),
                    daily_returns=sym_daily_ret,
                )

                if sig is None:
                    continue

                journal.log_signal(sym, sig, taken=True)
                order = broker.submit_bracket_order(
                    symbol=sym,
                    qty=sig.qty,
                    stop_price=sig.stop_price,
                    take_profit_price=sig.target_price,
                )

                if order:
                    trades_today += 1
                    journal.log_trade_open(sig)
                    journal.save_trade(
                        journal.build_trade_record(sig, str(order.id), today, now.strftime("%H:%M:%S"))
                    )

            except Exception as e:
                logger.error(f"Error processing {sym}: {e}", exc_info=True)

        time.sleep(60)


def _save_daily_summary(broker, daily_start_equity, today, regime):
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
        "date": str(today), "regime": regime,
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


# ── Cloud scan (GitHub Actions morning job) ───────────────────────────────────

def cmd_scan(debug: bool = False):
    """Enter trades with bracket orders then exit. Alpaca manages stops/targets."""
    import pandas as pd

    setup_logging(debug)
    logger.info("Mode: SCAN (cloud morning entry)")

    broker = AlpacaBroker()
    if not broker.is_market_open():
        logger.info("Market closed — nothing to do.")
        return

    data_client = mkt_data.get_data_client()
    regime_engine = RegimeEngine()
    vix_ranker = VIXBetaRanker()

    today = datetime.now(ET).date()
    start_str = (today.replace(day=max(1, today.day - 90))).isoformat()
    end_str = today.isoformat()

    snapshot = mkt_data.get_current_vol_snapshot()
    vol_df = mkt_data.get_vix_history(start_str, end_str)
    spy_df = mkt_data.get_spy_daily(start_str, end_str)
    pc_series = mkt_data.get_put_call_history(start_str, end_str)

    vix_s = vol_df["vix"].dropna() if not vol_df.empty and "vix" in vol_df else pd.Series([snapshot["vix"]])
    spy_s = spy_df["close"].dropna() if not spy_df.empty else pd.Series([400.0])
    pc_val = float(pc_series.dropna().iloc[-1]) if not pc_series.empty else 0.9

    regime_state = regime_engine.compute(
        vix_series=vix_s,
        vvix_level=snapshot["vvix"],
        put_call_ratio=pc_val,
        spy_series=spy_s,
        vix3m_level=snapshot["vix3m"],
    )
    logger.info(regime_state.summary())

    daily_returns = {
        sym: mkt_data.get_symbol_daily_returns(data_client, sym, start_str, end_str)
        for sym in config.ALL_SYMBOLS
    }
    vix_ranker.fit(daily_returns, vix_s)

    active_universe = vix_ranker.rank(
        regime_state.active_universe,
        regime_mode="defensive" if regime_state.regime.value.startswith("C") else "momentum",
    )

    account = broker.get_account()
    daily_start_equity = float(account.equity)
    trades_today = 0
    gap_size_factor = 1.0  # reduced if large gap detected
    rsk.reset_kill_switch()

    # ── Opening gap safety ────────────────────────────────────────────────────
    try:
        spy_bars_today = mkt_data.get_today_bars(data_client, "SPY")
        if not spy_bars_today.empty and not spy_s.empty:
            spy_prev_close = float(spy_s.iloc[-1])
            spy_open = float(spy_bars_today["open"].iloc[0])
            gap_pct = abs(spy_open - spy_prev_close) / spy_prev_close
            if gap_pct >= config.GAP_SKIP_PCT:
                logger.warning(f"Opening gap {gap_pct:.1%} >= {config.GAP_SKIP_PCT:.0%} — skipping trading day.")
                _save_daily_summary(broker, daily_start_equity, today, "GAP_SKIP")
                return
            elif gap_pct >= config.GAP_REDUCE_PCT:
                gap_size_factor = 0.5
                logger.warning(f"Opening gap {gap_pct:.1%} — reducing position size 50%.")
    except Exception as e:
        logger.warning(f"Gap check failed: {e} — proceeding normally.")

    logger.info(f"Scan start | equity=${daily_start_equity:,.2f} | regime={regime_state.regime.value} | universe={active_universe}")

    # Wait for ORB to complete
    while datetime.now(ET).strftime("%H:%M") < config.ORB_END_TIME:
        logger.info("Waiting for ORB window to close...")
        time.sleep(30)

    # Scan until entry cutoff
    while True:
        now = datetime.now(ET)
        current_time = now.strftime("%H:%M")

        if current_time >= config.LAST_ENTRY_TIME:
            logger.info(f"Entry window closed ({config.LAST_ENTRY_TIME}). Scan complete.")
            _save_daily_summary(broker, daily_start_equity, today, regime_state.regime.value)
            break

        if rsk.is_kill_switch_active():
            logger.critical("Kill switch active — halting scan.")
            break

        account = broker.get_account()
        equity = float(account.equity)
        daily_pnl = equity - daily_start_equity
        open_positions = broker.get_positions()

        fresh_snap = mkt_data.get_current_vol_snapshot()
        vvix_filter_result = vvix.regime_filter(fresh_snap["vvix"])
        sent_state = sent_mod.classify_put_call(pd.Series([fresh_snap["put_call_ratio"]]))

        can_trade, limit_reason = rsk.check_daily_limits(trades_today, daily_pnl, daily_start_equity)
        if not can_trade:
            logger.warning(f"Trading halted: {limit_reason}")
            break

        for sym in active_universe:
            try:
                bars = mkt_data.get_today_bars(data_client, sym)
                if bars.empty:
                    continue

                sig = strategy.check_entry_signal(
                    symbol=sym,
                    bars=bars,
                    account_equity=equity,
                    open_positions=open_positions,
                    trades_today=trades_today,
                    daily_pnl=daily_pnl,
                    daily_start_equity=daily_start_equity,
                    regime_state=regime_state,
                    vvix_filter=vvix_filter_result,
                    sentiment_state=sent_state,
                    vix_beta=vix_ranker.get_beta(sym),
                    daily_returns=daily_returns.get(sym, pd.Series(dtype=float)),
                )
                if sig is None:
                    continue

                journal.log_signal(sym, sig, taken=True)
                adjusted_qty = max(1, int(sig.qty * gap_size_factor))
                order = broker.submit_bracket_order(
                    symbol=sym,
                    qty=adjusted_qty,
                    stop_price=sig.stop_price,
                    take_profit_price=sig.target_price,
                )
                if order:
                    trades_today += 1
                    journal.log_trade_open(sig)
                    journal.save_trade(
                        journal.build_trade_record(sig, str(order.id), today, now.strftime("%H:%M:%S"))
                    )
            except Exception as e:
                logger.error(f"Error processing {sym}: {e}", exc_info=True)

        time.sleep(60)


# ── Cloud close (GitHub Actions EOD job) ─────────────────────────────────────

def cmd_close(debug: bool = False):
    """Close all open positions and cancel pending orders. Runs at 3:50 PM ET."""
    setup_logging(debug)
    logger.info("Mode: CLOSE (EOD cloud job)")

    broker = AlpacaBroker()
    account = broker.get_account()
    daily_start_equity = float(account.equity)
    today = datetime.now(ET).date()

    positions = broker.get_positions()
    if positions:
        logger.info(f"Closing {len(positions)} open position(s)...")
        broker.close_all_positions()
    else:
        logger.info("No open positions.")

    _save_daily_summary(broker, daily_start_equity, today, "EOD_CLOSE")
    logger.info("EOD close complete.")


# ── Daily research (GitHub Actions 6 AM job) ──────────────────────────────────

def cmd_research(debug: bool = False):
    """Pull Yahoo Finance news for all universe symbols + VIX/SPY. Save markdown report."""
    import os
    import yfinance as yf

    setup_logging(debug)
    logger.info("Mode: RESEARCH")

    today = datetime.now(ET).date()
    tickers = ["SPY", "QQQ", "^VIX", "^VVIX"] + config.ALL_SYMBOLS

    seen_titles: set = set()
    sections: dict = {}

    for ticker in tickers:
        try:
            news = yf.Ticker(ticker).news or []
        except Exception:
            news = []

        items = []
        for item in news[:5]:
            title = item.get("title", "").strip()
            link = item.get("link", "")
            publisher = item.get("publisher", "")
            if title and title not in seen_titles:
                seen_titles.add(title)
                items.append(f"- [{title}]({link}) — *{publisher}*")

        if items:
            sections[ticker] = items

    # Current regime snapshot
    try:
        snapshot = mkt_data.get_current_vol_snapshot()
        regime_line = (
            f"**VIX:** {snapshot['vix']:.1f}  |  "
            f"**VVIX:** {snapshot['vvix']:.1f}  |  "
            f"**VIX3M:** {snapshot['vix3m']:.1f}"
        )
    except Exception:
        regime_line = "VIX data unavailable"

    # Build markdown report
    lines = [
        f"# Daily Market Research — {today}",
        "",
        "## Volatility Snapshot",
        regime_line,
        "",
        "## News by Symbol",
        "",
    ]
    for ticker, items in sections.items():
        lines.append(f"### {ticker}")
        lines.extend(items)
        lines.append("")

    report = "\n".join(lines)

    os.makedirs("reports", exist_ok=True)
    path = f"reports/{today}-research.md"
    with open(path, "w") as f:
        f.write(report)

    logger.info(f"Research report saved: {path}")
    print(report)


# ── Weekly review (GitHub Actions Friday job) ─────────────────────────────────

def cmd_weekly(debug: bool = False):
    """Generate weekly P&L review from journal + Alpaca. Save markdown report."""
    import os
    from datetime import timedelta
    import yfinance as yf

    setup_logging(debug)
    logger.info("Mode: WEEKLY REVIEW")

    today = datetime.now(ET).date()
    week_start = today - timedelta(days=today.weekday())  # Monday
    week_end = today

    # Load trade journal
    all_trades = journal.load_trades()
    week_trades = [
        t for t in all_trades
        if week_start.isoformat() <= t.get("date", "") <= week_end.isoformat()
    ]

    # Load daily performance
    all_perf = journal.load_daily_performance()
    week_perf = [
        p for p in all_perf
        if week_start.isoformat() <= p.get("date", "") <= week_end.isoformat()
    ]

    # Metrics
    total_pnl = sum(float(t.get("pnl", 0)) for t in week_trades)
    wins = [t for t in week_trades if t.get("result") == "WIN"]
    losses = [t for t in week_trades if t.get("result") == "LOSS"]
    win_rate = len(wins) / len(week_trades) * 100 if week_trades else 0
    gross_profit = sum(float(t.get("pnl", 0)) for t in wins)
    gross_loss = abs(sum(float(t.get("pnl", 0)) for t in losses))
    profit_factor = gross_profit / gross_loss if gross_loss > 0 else 0

    # Best / worst trades
    sorted_trades = sorted(week_trades, key=lambda t: float(t.get("pnl", 0)), reverse=True)
    best = sorted_trades[:3] if sorted_trades else []
    worst = sorted_trades[-3:] if len(sorted_trades) >= 3 else []

    # Regime distribution
    regime_counts: dict = {}
    for p in week_perf:
        r = p.get("regime", "UNKNOWN")
        regime_counts[r] = regime_counts.get(r, 0) + 1

    # SPY weekly return
    try:
        spy_data = yf.download("SPY", start=week_start.isoformat(), end=(week_end + timedelta(days=1)).isoformat(), progress=False)
        if not spy_data.empty:
            if isinstance(spy_data.columns, __import__("pandas").MultiIndex):
                spy_data.columns = spy_data.columns.get_level_values(0)
            spy_data.columns = [c.lower() for c in spy_data.columns]
            spy_open = float(spy_data["close"].iloc[0])
            spy_close = float(spy_data["close"].iloc[-1])
            spy_ret = (spy_close - spy_open) / spy_open * 100
            spy_line = f"SPY this week: {spy_ret:+.2f}%"
        else:
            spy_line = "SPY data unavailable"
    except Exception:
        spy_line = "SPY data unavailable"

    # All-time P&L from journal
    all_time_pnl = sum(float(t.get("pnl", 0)) for t in all_trades)

    # Current vol
    try:
        snapshot = mkt_data.get_current_vol_snapshot()
        vix_line = f"VIX: {snapshot['vix']:.1f} | VVIX: {snapshot['vvix']:.1f}"
    except Exception:
        vix_line = "VIX data unavailable"

    # News headlines for weekly context
    seen: set = set()
    headlines = []
    for ticker in ["SPY", "QQQ", "^VIX"]:
        try:
            news = yf.Ticker(ticker).news or []
            for item in news[:3]:
                title = item.get("title", "").strip()
                link = item.get("link", "")
                if title and title not in seen:
                    seen.add(title)
                    headlines.append(f"- [{title}]({link})")
        except Exception:
            pass

    # Build markdown
    def _trade_row(t: dict) -> str:
        return (
            f"  - {t.get('symbol','?')} {t.get('date','')} "
            f"P&L=${float(t.get('pnl',0)):+,.2f} ({t.get('result','?')})"
        )

    lines = [
        f"# Weekly Review — {week_start} to {week_end}",
        "",
        "## Performance Summary",
        f"| Metric | Value |",
        f"|---|---|",
        f"| Trades | {len(week_trades)} |",
        f"| Win Rate | {win_rate:.1f}% |",
        f"| Total P&L | ${total_pnl:+,.2f} |",
        f"| Profit Factor | {profit_factor:.2f} |",
        f"| All-Time P&L | ${all_time_pnl:+,.2f} |",
        f"| {spy_line} | — |",
        "",
        "## Volatility",
        vix_line,
        "",
        "## Regime Distribution This Week",
    ]
    for regime, count in regime_counts.items():
        lines.append(f"- {regime}: {count} day(s)")

    lines += ["", "## Best Trades"]
    lines += [_trade_row(t) for t in best] or ["  - No trades this week"]

    lines += ["", "## Worst Trades"]
    lines += [_trade_row(t) for t in worst] or ["  - No trades this week"]

    lines += ["", "## Market Headlines"]
    lines += headlines or ["  - No headlines available"]

    lines += ["", "---", f"*Generated {datetime.now(ET).strftime('%Y-%m-%d %H:%M ET')}*"]

    report = "\n".join(lines)

    os.makedirs("reports", exist_ok=True)
    path = f"reports/{today}-weekly.md"
    with open(path, "w") as f:
        f.write(report)

    logger.info(f"Weekly review saved: {path}")
    print(report)


# ── Daily brief (runs after EOD close) ───────────────────────────────────────

def cmd_daily_brief(debug: bool = False):
    """Pull today's filled orders from Alpaca and print a formatted P&L brief."""
    import os

    setup_logging(debug)
    logger.info("Mode: DAILY BRIEF")

    broker = AlpacaBroker()
    account = broker.get_account()
    today = datetime.now(ET).date()
    equity = float(account.equity)

    orders = broker.get_todays_closed_orders()

    # Pair entries (BUY) with exits (SELL) by symbol
    buys: dict = {}
    sells: dict = {}
    for o in orders:
        sym = o.symbol
        side = str(o.side)
        filled_price = float(o.filled_avg_price) if o.filled_avg_price else 0.0
        qty = float(o.filled_qty) if o.filled_qty else 0.0
        if qty == 0 or filled_price == 0:
            continue
        if "buy" in side.lower():
            buys[sym] = {"price": filled_price, "qty": qty}
        elif "sell" in side.lower():
            sells[sym] = {"price": filled_price, "qty": qty}

    trades = []
    for sym, buy in buys.items():
        if sym in sells:
            sell = sells[sym]
            qty = min(buy["qty"], sell["qty"])
            pnl = (sell["price"] - buy["price"]) * qty
            trades.append({
                "symbol": sym,
                "entry": buy["price"],
                "exit": sell["price"],
                "qty": int(qty),
                "pnl": pnl,
                "result": "WIN" if pnl > 0 else "LOSS",
            })

    # Regime snapshot
    try:
        snapshot = mkt_data.get_current_vol_snapshot()
        regime_line = f"VIX={snapshot['vix']:.1f}  VVIX={snapshot['vvix']:.1f}  VIX3M={snapshot['vix3m']:.1f}"
    except Exception:
        regime_line = "VIX data unavailable"

    total_pnl = sum(t["pnl"] for t in trades)
    wins = [t for t in trades if t["result"] == "WIN"]
    losses = [t for t in trades if t["result"] == "LOSS"]
    win_rate = len(wins) / len(trades) * 100 if trades else 0
    gross_profit = sum(t["pnl"] for t in wins)
    gross_loss = abs(sum(t["pnl"] for t in losses))
    profit_factor = gross_profit / gross_loss if gross_loss > 0 else 0

    # All-time P&L from journal (what we have)
    all_trades = journal.load_trades()
    all_time_pnl = sum(float(t.get("pnl", 0)) for t in all_trades if t.get("pnl"))

    SEP = "=" * 55

    lines = [
        SEP,
        f"  DAILY BRIEF — {today}",
        SEP,
        "",
        f"  Volatility   {regime_line}",
        f"  Equity       ${equity:,.2f}",
        "",
    ]

    if trades:
        lines += [
            f"  {'Symbol':<8} {'Entry':>8} {'Exit':>8} {'Qty':>5} {'P&L':>10}  Result",
            "  " + "-" * 53,
        ]
        for t in sorted(trades, key=lambda x: x["pnl"], reverse=True):
            pnl_str = f"${t['pnl']:+,.2f}"
            lines.append(
                f"  {t['symbol']:<8} ${t['entry']:>7.2f} ${t['exit']:>7.2f} "
                f"{t['qty']:>5} {pnl_str:>10}  {t['result']}"
            )
        lines += [
            "  " + "-" * 53,
            f"  {'TOTAL':<8} {'':>8} {'':>8} {'':>5} ${total_pnl:>+9,.2f}",
            "",
            f"  Trades       {len(trades)} ({len(wins)}W / {len(losses)}L)",
            f"  Win Rate     {win_rate:.1f}%",
            f"  Profit Factor {profit_factor:.2f}",
        ]
    else:
        lines.append("  No trades today.")

    lines += [
        "",
        f"  All-Time P&L (journal) ${all_time_pnl:+,.2f}",
        "",
        SEP,
    ]

    brief = "\n".join(lines)
    print(brief)

    os.makedirs("reports", exist_ok=True)
    path = f"reports/{today}-daily.md"
    with open(path, "w") as f:
        f.write(f"```\n{brief}\n```\n")

    logger.info(f"Daily brief saved: {path}")


# ── Backtest ──────────────────────────────────────────────────────────────────

def cmd_backtest(start: str, end: str, equity: float, debug: bool = False):
    import pandas as pd
    import os
    from backtest import run_three_way_comparison

    setup_logging(debug)
    print(BANNER)
    logger.info(f"Mode: BACKTEST | {start} → {end} | equity=${equity:,.0f}")

    data_client = mkt_data.get_data_client()
    all_symbols = list(dict.fromkeys(config.ALL_SYMBOLS + ["SPY"]))

    logger.info(f"Downloading bars for {len(all_symbols)} symbols...")
    bars_by_symbol = mkt_data.get_multiple_symbols_bars(data_client, all_symbols, start, end)

    logger.info("Downloading volatility data (VIX, VVIX, VIX3M)...")
    vol_df = mkt_data.get_vix_history(start, end)

    logger.info("Downloading SPY daily...")
    spy_daily = mkt_data.get_spy_daily(start, end)

    logger.info("Downloading put/call ratio...")
    pc_series = mkt_data.get_put_call_history(start, end)

    logger.info("Computing daily returns for VIX beta factor...")
    daily_returns = {
        sym: mkt_data.get_symbol_daily_returns(data_client, sym, start, end)
        for sym in config.ALL_SYMBOLS
    }

    os.makedirs(config.BACKTEST_RESULTS_DIR, exist_ok=True)
    run_three_way_comparison(
        bars_by_symbol=bars_by_symbol,
        vol_df=vol_df,
        spy_daily=spy_daily,
        pc_series=pc_series,
        daily_returns_by_sym=daily_returns,
        initial_equity=equity,
        save_to_dir=config.BACKTEST_RESULTS_DIR,
    )
    logger.info(f"Results saved to {config.BACKTEST_RESULTS_DIR}/")


# ── CLI ───────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description="VIX/VVIX Regime Alpha Bot")
    parser.add_argument("--debug", action="store_true")
    sub = parser.add_subparsers(dest="mode", required=True)

    sub.add_parser("paper", help="Live paper trading (long-running, local use)")
    sub.add_parser("scan", help="Morning entry scan with bracket orders, then exit (cloud)")
    sub.add_parser("close", help="Close all positions and cancel orders (cloud EOD)")
    sub.add_parser("daily-brief", help="Pull today's Alpaca fills and print P&L summary")
    sub.add_parser("research", help="Pull Yahoo Finance news and save daily report")
    sub.add_parser("weekly", help="Generate weekly P&L review and save report")
    sub.add_parser("regime-status", help="Print current regime and exit")

    bt = sub.add_parser("backtest", help="Historical 3-strategy comparison backtest")
    bt.add_argument("--start", required=True, metavar="YYYY-MM-DD")
    bt.add_argument("--end", required=True, metavar="YYYY-MM-DD")
    bt.add_argument("--equity", type=float, default=config.INITIAL_EQUITY)

    args = parser.parse_args()

    if args.mode == "paper":
        cmd_paper(args.debug)
    elif args.mode == "scan":
        cmd_scan(args.debug)
    elif args.mode == "close":
        cmd_close(args.debug)
    elif args.mode == "daily-brief":
        cmd_daily_brief(args.debug)
    elif args.mode == "research":
        cmd_research(args.debug)
    elif args.mode == "weekly":
        cmd_weekly(args.debug)
    elif args.mode == "regime-status":
        cmd_regime_status(args.debug)
    elif args.mode == "backtest":
        cmd_backtest(args.start, args.end, args.equity, args.debug)


if __name__ == "__main__":
    main()
