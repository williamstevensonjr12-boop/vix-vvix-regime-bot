"""
tracker.py — Paper trading performance dashboard.

Shows rolling stats against go-live criteria:
  ✅ Win rate >= 52%
  ✅ Profit factor >= 1.1
  ✅ No kill-switch day in the window

Usage:
  python main.py tracker           # last 30 trading days
  python main.py tracker --days 60
"""
from __future__ import annotations
import csv
import os
from collections import defaultdict
from datetime import datetime, date

import config

GOAL_WIN_RATE = 0.52
GOAL_PROFIT_FACTOR = 1.10

GREEN = "\033[92m"
RED   = "\033[91m"
YELLOW= "\033[93m"
BOLD  = "\033[1m"
RESET = "\033[0m"


def _check(passed: bool) -> str:
    return f"{GREEN}✅{RESET}" if passed else f"{RED}❌{RESET}"


def _pct(v: float) -> str:
    return f"{v:.1%}"


def _load_trades(path: str) -> list[dict]:
    if not os.path.exists(path):
        return []
    with open(path, newline="") as f:
        return list(csv.DictReader(f))


def _load_performance(path: str) -> list[dict]:
    if not os.path.exists(path):
        return []
    with open(path, newline="") as f:
        return list(csv.DictReader(f))


def run_dashboard(window_days: int = 30):
    trades = _load_trades(config.TRADES_CSV)
    perf   = _load_performance(config.PERFORMANCE_CSV)

    if not trades:
        print(f"\n{YELLOW}No trades found in {config.TRADES_CSV}. Start paper trading first.{RESET}\n")
        print("  python main.py paper\n")
        return

    # Sort and window
    trades.sort(key=lambda t: t.get("date", ""))
    unique_days = sorted({t["date"] for t in trades if t.get("date")})
    windowed_days = set(unique_days[-window_days:])
    window_trades = [t for t in trades if t.get("date") in windowed_days]

    if not window_trades:
        print(f"{YELLOW}No trades in the last {window_days} trading days.{RESET}")
        return

    # Core metrics
    wins   = [t for t in window_trades if t.get("result") == "WIN"]
    losses = [t for t in window_trades if t.get("result") == "LOSS"]
    total  = len(window_trades)
    win_rate = len(wins) / total if total else 0

    gross_win  = sum(float(t.get("pnl", 0)) for t in wins)
    gross_loss = abs(sum(float(t.get("pnl", 0)) for t in losses))
    profit_factor = gross_win / gross_loss if gross_loss > 0 else float("inf")

    total_pnl   = sum(float(t.get("pnl", 0)) for t in window_trades)
    avg_win     = gross_win  / len(wins)   if wins   else 0
    avg_loss    = gross_loss / len(losses) if losses else 0

    # Kill switch days (daily loss > 3%)
    daily_pnl: dict[str, float] = defaultdict(float)
    for t in window_trades:
        daily_pnl[t["date"]] += float(t.get("pnl", 0))

    perf_map = {p["date"]: p for p in perf if p.get("date") in windowed_days}
    kill_days = []
    for day, dpnl in daily_pnl.items():
        p = perf_map.get(day, {})
        eq = float(p.get("equity", config.INITIAL_EQUITY)) if p else config.INITIAL_EQUITY
        if eq > 0 and abs(dpnl) / eq >= config.KILL_SWITCH_LOSS_PCT:
            kill_days.append(day)

    # Regime breakdown
    regime_counts: dict[str, int] = defaultdict(int)
    for t in window_trades:
        regime_counts[t.get("regime", "UNKNOWN")] += 1

    # Running equity curve (from perf log)
    perf_window = sorted(
        [p for p in perf if p.get("date") in windowed_days],
        key=lambda p: p["date"]
    )
    start_eq = float(perf_window[0].get("equity", config.INITIAL_EQUITY)) if perf_window else config.INITIAL_EQUITY
    end_eq   = float(perf_window[-1].get("equity", config.INITIAL_EQUITY)) if perf_window else config.INITIAL_EQUITY

    # Max drawdown in window
    running = config.INITIAL_EQUITY
    peak = running
    max_dd = 0.0
    for p in perf_window:
        eq = float(p.get("equity", running))
        peak = max(peak, eq)
        dd = peak - eq
        max_dd = max(max_dd, dd)

    # Go-live criteria checks
    ok_wr  = win_rate >= GOAL_WIN_RATE
    ok_pf  = profit_factor >= GOAL_PROFIT_FACTOR
    ok_ks  = len(kill_days) == 0
    go_live = ok_wr and ok_pf and ok_ks

    # ── Print dashboard ────────────────────────────────────────────────────
    now = datetime.now().strftime("%Y-%m-%d %H:%M")
    print(f"\n{BOLD}{'='*60}{RESET}")
    print(f"{BOLD}  PAPER TRADING DASHBOARD — {now}{RESET}")
    print(f"  Window: last {len(windowed_days)} trading days  |  {min(windowed_days)} → {max(windowed_days)}")
    print(f"{BOLD}{'='*60}{RESET}")

    print(f"\n{BOLD}── PERFORMANCE ──────────────────────────────────────{RESET}")
    print(f"  Total trades    : {total}  ({len(wins)}W / {len(losses)}L)")
    print(f"  Win rate        : {_pct(win_rate)}")
    print(f"  Profit factor   : {profit_factor:.2f}")
    print(f"  Avg win         : ${avg_win:,.2f}")
    print(f"  Avg loss        : ${avg_loss:,.2f}")
    print(f"  Total P&L       : ${total_pnl:+,.2f}")
    print(f"  Max drawdown    : ${max_dd:,.2f}")

    print(f"\n{BOLD}── REGIME BREAKDOWN ─────────────────────────────────{RESET}")
    for regime, count in sorted(regime_counts.items()):
        bar = "█" * (count * 20 // max(regime_counts.values(), default=1))
        pct = count / total
        print(f"  {regime:<22} {bar:<20} {count:>3} ({pct:.0%})")

    print(f"\n{BOLD}── GO-LIVE CHECKLIST ────────────────────────────────{RESET}")
    print(f"  {_check(ok_wr)} Win rate ≥ 52%         actual: {_pct(win_rate):<8}  target: 52%")
    print(f"  {_check(ok_pf)} Profit factor ≥ 1.10   actual: {profit_factor:<8.2f}  target: 1.10")
    print(f"  {_check(ok_ks)} Zero kill-switch days   actual: {len(kill_days)} day(s)")

    if kill_days:
        for d in kill_days:
            print(f"      {RED}↳ kill switch fired: {d}{RESET}")

    print()
    if go_live:
        print(f"  {GREEN}{BOLD}🚀 GO-LIVE CRITERIA MET — ready to consider real money{RESET}")
    else:
        remaining = []
        if not ok_wr:
            remaining.append(f"win rate needs +{(GOAL_WIN_RATE - win_rate)*100:.1f}pp")
        if not ok_pf:
            remaining.append(f"profit factor needs +{GOAL_PROFIT_FACTOR - profit_factor:.2f}")
        if not ok_ks:
            remaining.append(f"eliminate kill-switch days ({len(kill_days)} this window)")
        print(f"  {YELLOW}Still needed: {' | '.join(remaining)}{RESET}")

    print(f"\n{BOLD}── RECENT DAYS ──────────────────────────────────────{RESET}")
    recent = sorted(daily_pnl.items())[-10:]
    for d, dpnl in recent:
        regime = perf_map.get(d, {}).get("regime", "?")
        color = GREEN if dpnl >= 0 else RED
        bar = ("+" if dpnl >= 0 else "-") * min(int(abs(dpnl) / 100), 20)
        print(f"  {d}  {color}{bar:<22}{RESET}  ${dpnl:+8,.2f}  [{regime}]")

    print(f"\n{BOLD}{'='*60}{RESET}\n")
