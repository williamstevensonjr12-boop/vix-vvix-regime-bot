#!/usr/bin/env python3
"""
health.py — One-shot bot health check.

Prints a 10-line GREEN/YELLOW/RED status snapshot covering everything that
matters: bot process, scan freshness, watcher daemons, routine perms, account
health, today's research brief, background tasks. Run from anywhere.

Usage:
    python3 scripts/health.py

Exit codes:
    0  all green or yellow
    1  at least one red
"""
from __future__ import annotations
import glob
import json
import os
import re
import subprocess
import sys
from datetime import datetime, time as dtime, timedelta
from pathlib import Path
from zoneinfo import ZoneInfo

REPO = Path(__file__).resolve().parent.parent
ET = ZoneInfo("America/New_York")

# ANSI color codes
GREEN = "\033[92m"
YELLOW = "\033[93m"
RED = "\033[91m"
DIM = "\033[2m"
BOLD = "\033[1m"
RESET = "\033[0m"


def _ok(msg: str) -> str:    return f"  {GREEN}✓{RESET}  {msg}"
def _warn(msg: str) -> str:  return f"  {YELLOW}⚠{RESET}  {msg}"
def _fail(msg: str) -> str:  return f"  {RED}✗{RESET}  {msg}"
def _info(msg: str) -> str:  return f"  {DIM}·{RESET}  {msg}"


def in_market_hours(now: datetime) -> bool:
    if now.weekday() >= 5:
        return False
    return dtime(9, 30) <= now.time() <= dtime(16, 0)


def check_bot_process():
    """Find python ... main.py paper process. Return (pid, etime_sec) or None."""
    try:
        out = subprocess.check_output(["pgrep", "-f", "main.py paper"],
                                      stderr=subprocess.DEVNULL).decode().strip()
        pids = [int(p) for p in out.split() if p.isdigit()]
        if not pids:
            return None
        # Pick the youngest by etime to avoid stale wrapper-only matches
        results = []
        for pid in pids:
            try:
                etime = subprocess.check_output(
                    ["ps", "-o", "etime=", "-p", str(pid)],
                    stderr=subprocess.DEVNULL).decode().strip()
                results.append((pid, etime))
            except Exception:
                continue
        return results[0] if results else None
    except subprocess.CalledProcessError:
        return None


def check_scan_freshness(now: datetime) -> tuple[str, float]:
    """Returns (status, seconds-since-last-scan). status: 'green'|'yellow'|'red'|'none'"""
    candidates = sorted(glob.glob("/tmp/bot_output_*.log"), reverse=True)
    if not candidates:
        return ("none", 0)
    latest = max(candidates, key=lambda p: os.path.getmtime(p))
    try:
        with open(latest) as f:
            tail = f.readlines()[-300:]
    except Exception:
        return ("none", 0)
    pat = re.compile(r"^(\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2})\b.*\bScan \d{2}:\d{2}\b")
    for line in reversed(tail):
        m = pat.match(line)
        if m:
            ts = datetime.strptime(m.group(1), "%Y-%m-%d %H:%M:%S").replace(tzinfo=ET)
            age = (now - ts).total_seconds()
            if not in_market_hours(now):
                return ("green", age)  # outside market, scan staleness expected
            if age < 90:
                return ("green", age)
            elif age < 240:
                return ("yellow", age)
            else:
                return ("red", age)
    return ("none", 0)


def check_launchd(label: str) -> bool:
    try:
        out = subprocess.check_output(["launchctl", "list"]).decode()
        return label in out
    except Exception:
        return False


def check_routine_perms() -> tuple[int, int]:
    """Returns (matched_routines, routines_with_correct_perms)."""
    expected = {
        "trading-bot-pre-market": {"Read", "Bash", "WebSearch"},
        "trading-bot-market-open": {"Bash", "Read"},
        "trading-bot-midday": {"Bash", "Read"},
        "trading-bot-intraday-scan": {"Bash", "Read"},
        "trading-bot-daily-summary": {"Bash", "Read"},
        "trading-bot-weekly-review": {"Bash", "Read"},
    }
    home = Path.home()
    fps = list((home / "Library/Application Support/Claude/claude-code-sessions").glob(
        "*/*/scheduled-tasks.json"))
    if not fps:
        return (0, 0)
    matched = 0
    correct = 0
    for fp in fps:
        try:
            with open(fp) as f:
                data = json.load(f)
        except Exception:
            continue
        tasks = data if isinstance(data, list) else data.get("tasks", data.get("scheduledTasks", []))
        if isinstance(tasks, dict):
            tasks = list(tasks.values())
        for t in tasks:
            tid = t.get("id")
            if tid in expected:
                matched += 1
                perms = {p.get("toolName") for p in (t.get("approvedPermissions") or [])}
                if perms == expected[tid]:
                    correct += 1
    return (matched, correct)


def check_account():
    """Returns dict with equity, daytrade_count, pdt flag — or None on failure."""
    try:
        os.chdir(REPO)
        sys.path.insert(0, str(REPO))
        import config  # triggers load_dotenv
        from broker import AlpacaBroker
        b = AlpacaBroker()
        acct = b.get_account()
        return {
            "equity": float(acct.equity),
            "daytrade_count": int(acct.daytrade_count),
            "pdt": bool(acct.pattern_day_trader),
        }
    except Exception as e:
        return {"error": str(e)}


def check_research_log_today() -> tuple[bool, str]:
    """Was today's pre-market research entry written?"""
    today = datetime.now(ET).date().isoformat()
    fp = REPO / "memory" / "RESEARCH-LOG.md"
    if not fp.exists():
        return (False, "RESEARCH-LOG.md missing")
    try:
        text = fp.read_text()
    except Exception:
        return (False, "read failed")
    return (today in text, today)


def check_background_tasks():
    """Look for known long-running scripts (sweeps, backtests)."""
    known = ["limit_order_backtest", "atr_threshold_sweep", "volume_threshold_sweep",
             "slippage_stress", "dynamic_backtest"]
    running = []
    try:
        out = subprocess.check_output(["ps", "ax", "-o", "command="]).decode()
        for line in out.splitlines():
            for k in known:
                if k in line and "grep" not in line:
                    running.append(k)
    except Exception:
        pass
    return list(set(running))


def main() -> int:
    now = datetime.now(ET)
    has_red = False
    market_open = in_market_hours(now)

    print()
    print(f"{BOLD}════════════════════════════════════════════════════════════{RESET}")
    print(f"{BOLD}  BOT HEALTH — {now.strftime('%Y-%m-%d %H:%M:%S ET')} "
          f"({'market OPEN' if market_open else 'market closed'}){RESET}")
    print(f"{BOLD}════════════════════════════════════════════════════════════{RESET}")

    # 1. Bot process
    print(f"\n{BOLD}1. Bot process{RESET}")
    proc = check_bot_process()
    if proc:
        print(_ok(f"main.py paper alive — PID {proc[0]}, uptime {proc[1]}"))
    elif market_open:
        print(_fail("main.py paper NOT running during market hours"))
        has_red = True
    else:
        print(_info("main.py paper not running (market closed — expected)"))

    # 2. Scan freshness
    print(f"\n{BOLD}2. Scan freshness{RESET}")
    status, age = check_scan_freshness(now)
    if status == "green":
        if market_open:
            print(_ok(f"last scan {age:.0f}s ago"))
        else:
            print(_info(f"last scan {age/60:.1f}min ago (market closed)"))
    elif status == "yellow":
        print(_warn(f"last scan {age:.0f}s ago — getting stale"))
    elif status == "red":
        print(_fail(f"last scan {age:.0f}s ago — bot may be hung"))
        has_red = True
    else:
        if market_open:
            print(_warn("no scan log today"))
        else:
            print(_info("no scan log today (market closed)"))

    # 3. Watchers
    print(f"\n{BOLD}3. Watchers (launchd){RESET}")
    perms_w = check_launchd("com.preston.trading-bot.routine-perms-watcher")
    hang_w = check_launchd("com.preston.trading-bot.hang-watchdog")
    print(_ok("perms watcher loaded") if perms_w else _fail("perms watcher NOT loaded"))
    print(_ok("hang watchdog loaded") if hang_w else _fail("hang watchdog NOT loaded"))
    if not (perms_w and hang_w):
        has_red = True

    # 4. Routine perms
    print(f"\n{BOLD}4. Routine permissions{RESET}")
    matched, correct = check_routine_perms()
    if matched == 0:
        print(_fail("no scheduled-tasks.json found"))
        has_red = True
    elif correct == matched:
        print(_ok(f"all {matched}/6 routines have correct perms"))
    else:
        print(_warn(f"only {correct}/{matched} routines have correct perms (watcher should auto-fix)"))

    # 5. Account
    print(f"\n{BOLD}5. Alpaca account{RESET}")
    acct = check_account()
    if acct and "error" not in acct:
        eq = acct["equity"]; dc = acct["daytrade_count"]; pdt = acct["pdt"]
        print(_ok(f"equity ${eq:,.2f}"))
        if pdt and eq < 25_500:
            print(_fail(f"PDT flagged + equity ${eq:,.0f} near $25K floor — entries blocked"))
            has_red = True
        elif dc >= 5:
            print(_warn(f"day-trade count {dc} (rolling 5d), pdt={pdt} — watch as count climbs"))
        else:
            print(_ok(f"day-trade count {dc} (rolling 5d), pdt={pdt}"))
    else:
        err = acct.get("error", "unknown") if acct else "unreachable"
        print(_fail(f"account check failed: {err}"))
        has_red = True

    # 6. Today's research brief
    print(f"\n{BOLD}6. Today's research brief{RESET}")
    has, _ = check_research_log_today()
    if has:
        print(_ok("RESEARCH-LOG.md has today's entry"))
    elif now.weekday() >= 5:
        print(_info("weekend — no brief expected"))
    elif now.time() < dtime(7, 0):
        print(_info("pre-6 AM — brief not yet fired"))
    else:
        print(_warn("today's brief not in RESEARCH-LOG.md"))

    # 7. Background tasks
    print(f"\n{BOLD}7. Background tasks{RESET}")
    bg = check_background_tasks()
    if bg:
        for task in bg:
            print(_info(f"running: {task}"))
    else:
        print(_info("no long-running tasks"))

    # Footer
    print()
    print(f"{BOLD}════════════════════════════════════════════════════════════{RESET}")
    if has_red:
        print(f"{RED}{BOLD}  RED — at least one critical issue. Review above.{RESET}")
    else:
        print(f"{GREEN}{BOLD}  GREEN/YELLOW — all critical systems healthy.{RESET}")
    print(f"{BOLD}════════════════════════════════════════════════════════════{RESET}")
    print()

    return 1 if has_red else 0


if __name__ == "__main__":
    sys.exit(main())
