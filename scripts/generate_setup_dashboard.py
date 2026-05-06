#!/usr/bin/env python3
"""
generate_setup_dashboard.py — Live Cameron VWAP-Bounce setup status per symbol.

For each symbol in MOMENTUM_UNIVERSE, pulls today's 5-min bars, computes the 6
entry gates (LONG and SHORT mirrors), and renders an HTML page showing
PASS/FAIL per gate with the actual indicator values.

Usage:
    python3 scripts/generate_setup_dashboard.py              # one-shot
    python3 scripts/generate_setup_dashboard.py --watch 30   # regenerate every 30s

Output: repo/setup_dashboard.html (open in browser; meta-refreshes every 30s)
"""
from __future__ import annotations
import argparse
import csv
import os
import sys
import time
from datetime import datetime
from html import escape
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO))
os.chdir(REPO)

import pandas as pd  # noqa: E402

import config  # noqa: E402
import data as data_mod  # noqa: E402
import indicators as ind  # noqa: E402
import strategy as strat  # noqa: E402
from broker import AlpacaBroker  # noqa: E402
from data import ET  # noqa: E402

REFRESH_SECONDS = 30
OUTPUT = REPO / "setup_dashboard.html"


def count_trades_today(today_iso: str) -> int:
    """Count rows in trades.csv where date == today (matches journal schema)."""
    path = REPO / "trades.csv"
    if not path.is_file():
        return 0
    try:
        with open(path, "r", newline="") as f:
            return sum(1 for r in csv.DictReader(f) if r.get("date") == today_iso)
    except Exception:
        return 0


def evaluate_symbol(
    client,
    symbol: str,
    account_equity: float,
    open_positions: dict,
    trades_today: int,
    daily_pnl: float,
    daily_start_equity: float,
) -> dict:
    """Compute all gate values for one symbol. Returns dict for templating.

    READY columns (long_ready / short_ready) are derived from the actual
    strategy.check_entry_signal / check_short_signal calls — single source of
    truth with the live bot. Per-gate booleans are computed locally for
    diagnostic visibility but do NOT determine READY.
    """
    out = {"symbol": symbol, "error": None}
    try:
        bars = data_mod.get_today_bars(client, symbol)
    except Exception as e:
        out["error"] = f"fetch error: {e}"
        return out

    if bars.empty:
        out["error"] = "no bars yet (market closed or pre-open)"
        return out

    out["bars_count"] = len(bars)
    out["min_bars_ok"] = len(bars) >= config.MIN_BARS_FOR_SIGNAL

    if len(bars) < config.MIN_BARS_FOR_SIGNAL:
        out["error"] = f"only {len(bars)}/{config.MIN_BARS_FOR_SIGNAL} bars"
        return out

    vwap_s = ind.calculate_vwap(bars)
    ema_fast_s = ind.calculate_ema(bars["close"], config.EMA_FAST_PERIOD)
    ema_mid_s = ind.calculate_ema(bars["close"], config.EMA_MID_PERIOD)
    ema_slow_s = ind.calculate_ema(bars["close"], config.EMA_SLOW_PERIOD)
    atr_s = ind.calculate_atr(bars)
    rvol_s = ind.calculate_relative_volume(bars)

    if any(s.empty for s in (vwap_s, ema_fast_s, ema_mid_s, ema_slow_s, atr_s, rvol_s)):
        out["error"] = "indicator series empty (warming up)"
        return out

    bar = bars.iloc[-1]
    prior = bars.iloc[-2]
    price = float(bar["close"])
    vwap = float(vwap_s.iloc[-1])
    ema_fast = float(ema_fast_s.iloc[-1])
    ema_mid = float(ema_mid_s.iloc[-1])
    ema_slow = float(ema_slow_s.iloc[-1])
    atr = float(atr_s.iloc[-1])
    rvol_raw = rvol_s.iloc[-1]
    rvol = float(rvol_raw) if pd.notna(rvol_raw) else 0.0

    out.update({
        "price": price, "vwap": vwap, "ema_fast": ema_fast, "ema_mid": ema_mid,
        "ema_slow": ema_slow, "atr": atr, "rvol": rvol,
    })

    out["long_above_vwap"] = price > vwap
    out["long_above_200ema"] = price > ema_slow
    out["ema_stack_long"] = ema_fast > ema_mid
    out["bounce_long"] = price > float(prior["close"])
    out["rvol_ok"] = rvol >= config.CAMERON_VOLUME_MULTIPLIER

    pullback_long, _ = strat._recent_pullback_to_vwap(
        bars, vwap_s, side="long",
        lookback=config.VWAP_PULLBACK_LOOKBACK_BARS,
        tolerance_pct=config.VWAP_PULLBACK_TOLERANCE_PCT,
    )
    out["pullback_long"] = pullback_long

    out["short_below_vwap"] = price < vwap
    out["short_below_200ema"] = price < ema_slow
    out["ema_stack_short"] = ema_fast < ema_mid
    out["bounce_short"] = price < float(prior["close"])

    pullback_short, _ = strat._recent_pullback_to_vwap(
        bars, vwap_s, side="short",
        lookback=config.VWAP_PULLBACK_LOOKBACK_BARS,
        tolerance_pct=config.VWAP_PULLBACK_TOLERANCE_PCT,
    )
    out["pullback_short"] = pullback_short

    if len(bars) >= config.STOP_LOOKBACK_BARS + 1:
        prior_lows = bars["low"].iloc[-(config.STOP_LOOKBACK_BARS + 1):-1]
        prior_highs = bars["high"].iloc[-(config.STOP_LOOKBACK_BARS + 1):-1]
        stop_long = float(prior_lows.min())
        stop_short = float(prior_highs.max())
        risk_long = price - stop_long
        risk_short = stop_short - price
        atr_cap = config.ATR_GUARDRAIL_MULT * atr
        out["stop_long"] = stop_long
        out["risk_long"] = risk_long
        out["stop_long_ok"] = risk_long > 0 and risk_long <= atr_cap
        out["stop_short"] = stop_short
        out["risk_short"] = risk_short
        out["stop_short_ok"] = risk_short > 0 and risk_short <= atr_cap
        out["atr_cap"] = atr_cap
    else:
        out["stop_long_ok"] = out["stop_short_ok"] = False
        out["atr_cap"] = config.ATR_GUARDRAIL_MULT * atr

    # Single source of truth: ask strategy.py what the bot would actually do.
    # If check_*_signal returns a TradeSignal, the bot would enter right now.
    long_sig = short_sig = None
    long_block = short_block = ""
    try:
        long_sig = strat.check_entry_signal(
            symbol, bars, account_equity, open_positions,
            trades_today, daily_pnl, daily_start_equity,
        )
    except Exception as e:
        long_block = f"err: {e}"
    try:
        short_sig = strat.check_short_signal(
            symbol, bars, account_equity, open_positions,
            trades_today, daily_pnl, daily_start_equity,
        )
    except Exception as e:
        short_block = f"err: {e}"

    out["long_ready"] = long_sig is not None
    out["short_ready"] = short_sig is not None

    # Derive a human-readable block reason when not ready.
    if not out["long_ready"] and not long_block:
        long_block = _block_reason(out, "long",
            symbol, open_positions, trades_today, daily_pnl, daily_start_equity)
    if not out["short_ready"] and not short_block:
        short_block = _block_reason(out, "short",
            symbol, open_positions, trades_today, daily_pnl, daily_start_equity)
    out["long_block"] = long_block
    out["short_block"] = short_block

    return out


def _block_reason(out: dict, side: str, symbol: str, open_positions: dict,
                  trades_today: int, daily_pnl: float, daily_start_equity: float) -> str:
    """Mirror strategy._gates_pass + setup-gate + stop checks to label what blocked."""
    gates_ok, reason = strat._gates_pass(
        symbol, open_positions, trades_today, daily_pnl, daily_start_equity,
    )
    if not gates_ok:
        return reason
    if side == "long":
        setup_ok = all([out["long_above_vwap"], out["long_above_200ema"],
                        out["ema_stack_long"], out["pullback_long"],
                        out["bounce_long"], out["rvol_ok"]])
        stop_ok = out.get("stop_long_ok", False)
    else:
        setup_ok = all([out["short_below_vwap"], out["short_below_200ema"],
                        out["ema_stack_short"], out["pullback_short"],
                        out["bounce_short"], out["rvol_ok"]])
        stop_ok = out.get("stop_short_ok", False)
    if not setup_ok:
        return "setup incomplete"
    if not stop_ok:
        return "stop > 1.5×ATR (chop)"
    return "sizing/exposure"


def get_account_state():
    try:
        broker = AlpacaBroker()
        acct = broker.get_account()
        equity = float(acct.equity)
        last_equity = float(getattr(acct, "last_equity", equity) or equity)
        positions = broker.get_positions()
        return {
            "equity": equity,
            "last_equity": last_equity,
            "daily_pnl": equity - last_equity,
            "positions": positions,
            "open_positions": len(positions),
            "position_symbols": list(positions.keys()),
            "error": None,
        }
    except Exception as e:
        return {
            "equity": None, "last_equity": None, "daily_pnl": 0.0,
            "positions": {}, "open_positions": None, "position_symbols": [],
            "error": str(e),
        }


def cell(ok: bool, value: str = "") -> str:
    cls = "ok" if ok else "fail"
    mark = "✓" if ok else "✗"
    inner = f"{mark} {escape(value)}" if value else mark
    return f'<td class="{cls}">{inner}</td>'


def render_html(symbol_data: list[dict], account: dict) -> str:
    now_et = datetime.now(ET).strftime("%Y-%m-%d %H:%M:%S ET")
    rows_long, rows_short, rows_err = [], [], []

    for d in symbol_data:
        sym = escape(d["symbol"])
        if d.get("error"):
            rows_err.append(f"<tr><td><b>{sym}</b></td><td>{escape(d['error'])}</td></tr>")
            continue

        price = f"${d['price']:.2f}"
        vwap = f"${d['vwap']:.2f}"
        ema = f"{d['ema_fast']:.2f}/{d['ema_mid']:.2f}/{d['ema_slow']:.2f}"
        rvol_v = f"{d['rvol']:.2f}×"
        atr_v = f"${d['atr']:.2f}"

        ready_long_cls = "ready" if d["long_ready"] else "not-ready"
        ready_long = "READY" if d["long_ready"] else "—"
        long_block = escape(d.get("long_block") or "")
        rows_long.append(
            f'<tr><td><b>{sym}</b></td><td>{price}</td><td>{vwap}</td>'
            + cell(d["long_above_vwap"])
            + cell(d["long_above_200ema"])
            + cell(d["ema_stack_long"], ema)
            + cell(d["pullback_long"])
            + cell(d["bounce_long"])
            + cell(d["rvol_ok"], rvol_v)
            + cell(d["stop_long_ok"], f"risk ${d.get('risk_long', 0):.2f} / cap ${d['atr_cap']:.2f}")
            + f'<td class="{ready_long_cls}"><b>{ready_long}</b></td>'
            + f'<td class="block">{long_block}</td></tr>'
        )

        ready_short_cls = "ready" if d["short_ready"] else "not-ready"
        ready_short = "READY" if d["short_ready"] else "—"
        short_block = escape(d.get("short_block") or "")
        rows_short.append(
            f'<tr><td><b>{sym}</b></td><td>{price}</td><td>{vwap}</td>'
            + cell(d["short_below_vwap"])
            + cell(d["short_below_200ema"])
            + cell(d["ema_stack_short"], ema)
            + cell(d["pullback_short"])
            + cell(d["bounce_short"])
            + cell(d["rvol_ok"], rvol_v)
            + cell(d["stop_short_ok"], f"risk ${d.get('risk_short', 0):.2f} / cap ${d['atr_cap']:.2f}")
            + f'<td class="{ready_short_cls}"><b>{ready_short}</b></td>'
            + f'<td class="block">{short_block}</td></tr>'
        )

    err_section = ""
    if rows_err:
        err_section = (
            "<h2>Ineligible / warming up</h2>"
            "<table><thead><tr><th>Symbol</th><th>Reason</th></tr></thead>"
            f"<tbody>{''.join(rows_err)}</tbody></table>"
        )

    acct_html = ""
    if account.get("error"):
        acct_html = f'<div class="warn">Account fetch failed: {escape(account["error"])}</div>'
    else:
        held = ", ".join(account["position_symbols"]) or "none"
        trades_today = account.get("trades_today", 0)
        daily_pnl = account.get("daily_pnl", 0.0)
        pnl_cls = "ok" if daily_pnl >= 0 else "fail"
        acct_html = (
            f'<div class="account">Equity <b>${account["equity"]:,.2f}</b> · '
            f'Day P&L <b class="{pnl_cls}">${daily_pnl:+,.2f}</b> · '
            f'Open positions <b>{account["open_positions"]}/{config.MAX_OPEN_POSITIONS}</b> ({escape(held)}) · '
            f'Trades today <b>{trades_today}/{config.MAX_TRADES_PER_DAY}</b> · '
            f'Halt <b>{config.DAILY_MAX_LOSS_PCT * 100:.1f}%</b> · '
            f'Kill <b>{config.KILL_SWITCH_LOSS_PCT * 100:.1f}%</b></div>'
        )

    long_header = (
        "<tr><th>Sym</th><th>Price</th><th>VWAP</th>"
        "<th>>VWAP</th><th>>200EMA</th><th>9>20>200</th>"
        f"<th>Pullback ≤{config.VWAP_PULLBACK_TOLERANCE_PCT * 100:.2f}%</th>"
        "<th>Bounce</th>"
        f"<th>rvol ≥{config.CAMERON_VOLUME_MULTIPLIER}×</th>"
        f"<th>Stop ≤{config.ATR_GUARDRAIL_MULT}×ATR</th>"
        "<th>BOT</th><th>Block</th></tr>"
    )
    short_header = (
        "<tr><th>Sym</th><th>Price</th><th>VWAP</th>"
        "<th>&lt;VWAP</th><th>&lt;200EMA</th><th>9&lt;20&lt;200</th>"
        f"<th>Pullback ≤{config.VWAP_PULLBACK_TOLERANCE_PCT * 100:.2f}%</th>"
        "<th>Drop</th>"
        f"<th>rvol ≥{config.CAMERON_VOLUME_MULTIPLIER}×</th>"
        f"<th>Stop ≤{config.ATR_GUARDRAIL_MULT}×ATR</th>"
        "<th>BOT</th><th>Block</th></tr>"
    )

    return f"""<!DOCTYPE html>
<html lang="en"><head>
<meta charset="utf-8">
<meta http-equiv="refresh" content="{REFRESH_SECONDS}">
<title>Cameron VWAP-Bounce — Live Setup</title>
<style>
  body {{ font-family: -apple-system, system-ui, sans-serif; margin: 16px; background: #0f1115; color: #e6e6e6; }}
  h1 {{ font-size: 18px; margin: 0 0 4px; }}
  .meta {{ color: #888; font-size: 12px; margin-bottom: 12px; }}
  .account {{ background: #1a1d24; padding: 8px 12px; border-radius: 6px; margin-bottom: 16px; font-size: 13px; }}
  .warn {{ background: #3a1f1f; padding: 8px 12px; border-radius: 6px; margin-bottom: 16px; }}
  h2 {{ font-size: 14px; margin: 16px 0 6px; color: #aac; }}
  table {{ border-collapse: collapse; width: 100%; font-size: 12px; margin-bottom: 12px; }}
  th, td {{ border: 1px solid #2a2f3a; padding: 4px 8px; text-align: center; }}
  th {{ background: #1a1d24; color: #aac; font-weight: 500; }}
  td.ok {{ background: #14321c; color: #6f6; }}
  td.fail {{ background: #321414; color: #f88; }}
  td.ready {{ background: #2a4a1a; color: #afa; font-size: 13px; }}
  td.not-ready {{ background: #1a1d24; color: #666; }}
  td.block {{ color: #888; font-size: 11px; text-align: left; }}
  b.ok {{ color: #6f6; }}
  b.fail {{ color: #f88; }}
</style>
</head><body>
<h1>Cameron VWAP-Bounce — Live Setup Status</h1>
<div class="meta">Generated {now_et} · Auto-refresh {REFRESH_SECONDS}s · {len(symbol_data)} symbols</div>
{acct_html}
<h2>LONG setups</h2>
<table><thead>{long_header}</thead><tbody>{''.join(rows_long) or '<tr><td colspan="12">no rows</td></tr>'}</tbody></table>
<h2>SHORT setups</h2>
<table><thead>{short_header}</thead><tbody>{''.join(rows_short) or '<tr><td colspan="12">no rows</td></tr>'}</tbody></table>
{err_section}
</body></html>"""


def regenerate():
    client = data_mod.get_data_client()
    account = get_account_state()
    today_iso = datetime.now(ET).date().isoformat()
    trades_today = count_trades_today(today_iso)
    account["trades_today"] = trades_today
    equity = account["equity"] or 0.0
    last_equity = account["last_equity"] or equity
    daily_pnl = account["daily_pnl"]
    positions = account["positions"]
    rows = [
        evaluate_symbol(
            client, sym,
            account_equity=equity,
            open_positions=positions,
            trades_today=trades_today,
            daily_pnl=daily_pnl,
            daily_start_equity=last_equity,
        )
        for sym in config.MOMENTUM_UNIVERSE
    ]
    OUTPUT.write_text(render_html(rows, account))
    ready_long = sum(1 for d in rows if d.get("long_ready"))
    ready_short = sum(1 for d in rows if d.get("short_ready"))
    print(f"  wrote {OUTPUT.name} | LONG ready: {ready_long}/{len(rows)} | SHORT ready: {ready_short}/{len(rows)}")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--watch", type=int, default=0,
                    help="seconds between regenerations; 0 = run once and exit")
    args = ap.parse_args()

    if args.watch <= 0:
        regenerate()
        return

    print(f"Watching {OUTPUT} every {args.watch}s. Ctrl-C to stop.")
    while True:
        try:
            regenerate()
        except KeyboardInterrupt:
            return
        except Exception as e:
            print(f"  error: {e}")
        time.sleep(args.watch)


if __name__ == "__main__":
    main()
