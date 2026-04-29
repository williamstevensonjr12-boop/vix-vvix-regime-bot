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
from datetime import datetime, timedelta
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
    start_str = (today - timedelta(days=90)).isoformat()
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

    # Short universe (Regime B/C only, ranked by highest VIX beta)
    short_universe: list = []
    if config.ENABLE_SHORT_SLEEVE and regime_state.regime.value[0] in config.SHORT_REGIMES:
        short_universe = vix_ranker.rank(
            config.SHORT_UNIVERSE,
            regime_mode="short",
        )
        logger.info(f"Short universe: {short_universe}")

    # Prior closes for gap-alignment / gap-continuation
    prior_close_universe = list(dict.fromkeys(active_universe + short_universe))
    prior_closes: dict = mkt_data.get_prior_closes(prior_close_universe)
    logger.info(
        f"Prior closes loaded: {len(prior_closes)}/{len(prior_close_universe)} "
        f"symbols (gap-alignment={'on' if config.GAP_ALIGNMENT_REQUIRED else 'off'}, "
        f"gap-continuation={'on' if config.ENABLE_GAP_CONTINUATION else 'off'})"
    )

    # Daily state
    account = broker.get_account()
    daily_start_equity = float(account.equity)
    trades_today = 0
    spy_uptrend = _compute_spy_uptrend(spy_s)
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

        # Scan long universe (ORB + optional gap-continuation)
        for sym in active_universe:
            try:
                bars = mkt_data.get_today_bars(data_client, sym)
                if bars.empty:
                    continue

                sym_daily_ret = daily_returns.get(sym, pd.Series(dtype=float))

                # Try gap-continuation first (fires before ORB window closes)
                sig = None
                if config.ENABLE_GAP_CONTINUATION and prior_closes.get(sym):
                    sig = strategy.check_gap_continuation_signal(
                        symbol=sym,
                        bars=bars,
                        prior_close=prior_closes.get(sym),
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
                        spy_uptrend=spy_uptrend,
                    )

                if sig is None:
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
                        spy_uptrend=spy_uptrend,
                        prior_close=prior_closes.get(sym),
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

        # Scan short universe (Regime B/C only)
        for sym in short_universe:
            try:
                bars = mkt_data.get_today_bars(data_client, sym)
                if bars.empty:
                    continue

                sym_daily_ret = daily_returns.get(sym, pd.Series(dtype=float))

                sig = strategy.check_short_signal(
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
                    prior_close=prior_closes.get(sym),
                )

                if sig is None:
                    continue

                journal.log_signal(sym, sig, taken=True)
                order = broker.submit_short_bracket_order(
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
                logger.error(f"Error processing short {sym}: {e}", exc_info=True)

        time.sleep(60)


def _compute_spy_uptrend(spy_close_series) -> bool:
    """SPY > N-day MA → uptrend (gates Regime A entries)."""
    s = spy_close_series.dropna()
    if s.empty:
        return True
    period = config.SPY_TREND_MA_PERIOD
    if len(s) < period:
        return True
    return float(s.iloc[-1]) > float(s.tail(period).mean())


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


# ── Backtest ──────────────────────────────────────────────────────────────────

def cmd_tracker(days: int = 30):
    import tracker
    tracker.run_dashboard(window_days=days)


def cmd_dashboard():
    import dashboard
    dashboard.build_dashboard()


def cmd_backtest(start: str, end: str, equity: float, debug: bool = False, suite: str = "default"):
    import pandas as pd
    import os
    from backtest import (
        run_three_way_comparison,
        DEFAULT_COMPARISON_MODES,
        LONG_SHORT_COMPARISON_MODES,
        MTF_HEAD_TO_HEAD_MODES,
    )

    setup_logging(debug)
    print(BANNER)
    logger.info(f"Mode: BACKTEST [{suite}] | {start} → {end} | equity=${equity:,.0f}")

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
    if suite == "long_short":
        modes = LONG_SHORT_COMPARISON_MODES
    elif suite == "mtf_head_to_head":
        modes = MTF_HEAD_TO_HEAD_MODES
    else:
        modes = DEFAULT_COMPARISON_MODES
    run_three_way_comparison(
        bars_by_symbol=bars_by_symbol,
        vol_df=vol_df,
        spy_daily=spy_daily,
        pc_series=pc_series,
        daily_returns_by_sym=daily_returns,
        initial_equity=equity,
        save_to_dir=config.BACKTEST_RESULTS_DIR,
        modes=modes,
    )
    logger.info(f"Results saved to {config.BACKTEST_RESULTS_DIR}/")


# ── CLI ───────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description="VIX/VVIX Regime Alpha Bot")
    parser.add_argument("--debug", action="store_true")
    sub = parser.add_subparsers(dest="mode", required=True)

    sub.add_parser("paper", help="Live paper trading")
    sub.add_parser("regime-status", help="Print current regime and exit")
    sub.add_parser("dashboard", help="Generate HTML dashboard and open in browser")

    tr = sub.add_parser("tracker", help="Paper trading performance dashboard")
    tr.add_argument("--days", type=int, default=30, help="Rolling window in trading days")

    bt = sub.add_parser("backtest", help="Historical strategy comparison backtest")
    bt.add_argument("--start", required=True, metavar="YYYY-MM-DD")
    bt.add_argument("--end", required=True, metavar="YYYY-MM-DD")
    bt.add_argument("--equity", type=float, default=config.INITIAL_EQUITY)
    bt.add_argument(
        "--suite",
        choices=["default", "long_short", "mtf_head_to_head"],
        default="default",
        help="default = 4 long-only; long_short = full long+short comparison; mtf_head_to_head = regime-aware vs +MTF (2-way)",
    )

    args = parser.parse_args()

    if args.mode == "paper":
        cmd_paper(args.debug)
    elif args.mode == "regime-status":
        cmd_regime_status(args.debug)
    elif args.mode == "tracker":
        cmd_tracker(args.days)
    elif args.mode == "dashboard":
        cmd_dashboard()
    elif args.mode == "backtest":
        cmd_backtest(args.start, args.end, args.equity, args.debug, args.suite)


if __name__ == "__main__":
    main()
