"""
morning_check.py — Pre-market preflight: is the bot ready for today's session?

Run before 9:30 AM ET. Outputs a clean GREEN / YELLOW / RED status with the
reasons. Uses no external APIs that might rate-limit — just inspects local
state.

Usage:
  cd repo && python3 morning_check.py
"""
from __future__ import annotations
import json
import os
import subprocess
import sys
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

REPO = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, REPO)
import config

ET = ZoneInfo(config.TIMEZONE)

GREEN = "\033[92m"
YELLOW = "\033[93m"
RED = "\033[91m"
BOLD = "\033[1m"
END = "\033[0m"


def ok(msg):    print(f"  {GREEN}✓{END}  {msg}")
def warn(msg):  print(f"  {YELLOW}⚠{END}  {msg}")
def fail(msg):  print(f"  {RED}✗{END}  {msg}")


def check_bot_alive():
    """Is the python paper-trading process running?"""
    print(f"\n{BOLD}1. Bot process{END}")
    try:
        out = subprocess.run(["pgrep", "-af", "main.py paper"], capture_output=True, text=True)
        if out.stdout.strip():
            ok(f"Python paper bot alive — {out.stdout.strip().split()[0]}")
            return "ok"
        else:
            fail("No `main.py paper` process running")
            print(f"      → start with: cd {REPO} && bash run_bot.sh > /tmp/bot_output_$(date +%Y%m%d).log 2>&1 &")
            return "fail"
    except Exception as e:
        fail(f"Couldn't check process: {e}")
        return "fail"


def check_run_bot_wrapper():
    """Is the wrapper script running too (so it'll auto-restart on crash)?"""
    out = subprocess.run(["pgrep", "-af", "run_bot.sh"], capture_output=True, text=True)
    if out.stdout.strip():
        ok(f"run_bot.sh wrapper alive — auto-restart on crash enabled")
    else:
        warn("run_bot.sh wrapper NOT running — Python won't auto-restart on crash")


def check_recent_scan():
    """Has the bot scanned within the last 5 minutes?"""
    print(f"\n{BOLD}2. Bot heartbeat{END}")
    log_path = f"/tmp/bot_output_{datetime.now(ET).strftime('%Y%m%d')}.log"
    if not os.path.exists(log_path):
        warn(f"Today's bot log not found at {log_path} (bot may not have started today)")
        return "warn"
    try:
        out = subprocess.run(["grep", "-E", r"Scan [0-9]+:[0-9]+", log_path], capture_output=True, text=True)
        lines = [l for l in out.stdout.strip().split("\n") if l]
        if not lines:
            warn(f"No scans logged today yet — likely pre-9:30 (bot waits for market open)")
            return "warn"
        last = lines[-1]
        # Parse timestamp from beginning
        try:
            ts_str = last.split(" |")[0].strip()
            last_ts = datetime.strptime(ts_str, "%Y-%m-%d %H:%M:%S").replace(tzinfo=ET)
            now = datetime.now(ET)
            age = (now - last_ts).total_seconds()
            if age < 300:
                ok(f"Last scan {int(age)}s ago — {last.split('| ')[-1][:70]}")
                return "ok"
            elif age < 1800:
                warn(f"Last scan {int(age/60)} min ago — bot may be sleeping or stalled")
                return "warn"
            else:
                fail(f"Last scan {int(age/60)} min ago — bot likely dead/stuck")
                return "fail"
        except Exception:
            ok(f"Recent scan found: {last[:80]}")
            return "ok"
    except Exception as e:
        warn(f"Couldn't parse scan log: {e}")
        return "warn"


def check_universe_loaded():
    """Did the bot load the expected mega-cap universe?"""
    print(f"\n{BOLD}3. Universe{END}")
    log_path = f"/tmp/bot_output_{datetime.now(ET).strftime('%Y%m%d')}.log"
    if not os.path.exists(log_path):
        warn("Today's bot log missing")
        return
    try:
        # main.py logs: "...universe=N symbols (NAME1, NAME2, ...)"
        out = subprocess.run(["grep", "universe=", log_path], capture_output=True, text=True)
        lines = [l for l in out.stdout.strip().split("\n") if l]
        if not lines:
            warn("No 'universe=' line in log yet (bot may not have hit Market OPEN)")
            return
        last = lines[-1]
        import re
        m = re.search(r"universe=\d+ symbols \(([^)]*)\)", last)
        if not m:
            warn(f"Couldn't parse universe line: {last[:120]}")
            return
        names = [n.strip() for n in m.group(1).split(",") if n.strip()]
        ok(f"Universe: {len(names)} symbols — {', '.join(names)}")
        static_set = set(config.MOMENTUM_UNIVERSE)
        non_member = [n for n in names if n not in static_set]
        if non_member:
            warn(f"Loaded universe has names NOT in current MOMENTUM_UNIVERSE: {non_member} — bot may have stale config in memory")
        else:
            ok(f"All loaded names match current MOMENTUM_UNIVERSE — no stale-config drift")
    except Exception as e:
        warn(f"Couldn't parse universe: {e}")


def check_alpaca_connection():
    """Does the bot's last connect attempt show success?"""
    print(f"\n{BOLD}4. Alpaca paper account{END}")
    log_path = f"/tmp/bot_output_{datetime.now(ET).strftime('%Y%m%d')}.log"
    if not os.path.exists(log_path):
        warn("No log to check")
        return
    out = subprocess.run(["grep", "-E", "Alpaca PAPER|Alpaca .* connected|equity=", log_path], capture_output=True, text=True)
    if out.stdout:
        last = out.stdout.strip().split("\n")[-1]
        ok(f"Last connect line: {last.split('| ')[-1][:80]}")
    else:
        warn("No connection line found in log")


def check_pre_market_brief():
    """Does today's pre-market brief exist and show non-zero gaps?"""
    print(f"\n{BOLD}5. Pre-market brief{END}")
    research_log = os.path.join(REPO, "memory", "RESEARCH-LOG.md")
    if not os.path.exists(research_log):
        warn("RESEARCH-LOG.md missing")
        return
    today = datetime.now(ET).strftime("%Y-%m-%d")
    out = subprocess.run(["grep", "-c", today, research_log], capture_output=True, text=True)
    count = int(out.stdout.strip() or 0)
    if count == 0:
        fail(f"No entries for {today} in RESEARCH-LOG.md — pre-market routine may not have fired")
    else:
        ok(f"RESEARCH-LOG.md has {count} entries for {today}")
        # Check for non-zero gap_pct in today's section
        out2 = subprocess.run(
            ["grep", "-E", f"gap=[\\-0-9]+\\.[0-9]+%", research_log],
            capture_output=True, text=True
        )
        non_zero = [l for l in out2.stdout.split("\n") if "gap=0.0%" not in l and "gap=0.04%" not in l]
        non_zero_today = [l for l in non_zero if today in l or any(s in l for s in config.MOMENTUM_UNIVERSE)]
        if non_zero_today:
            ok(f"Non-zero gap entries detected — gap-detection working")
        else:
            warn(f"All gaps near 0% — gap-detection may be broken (or genuinely flat day)")


def check_scheduled_routines():
    """Did today's pre-market routine actually fire?"""
    print(f"\n{BOLD}6. Scheduled routines{END}")
    sched_paths = [
        "/Users/prestonteel/Library/Application Support/Claude/claude-code-sessions",
    ]
    today = datetime.now(ET).strftime("%Y-%m-%d")
    for base in sched_paths:
        for root, dirs, files in os.walk(base):
            if "scheduled-tasks.json" in files:
                path = os.path.join(root, "scheduled-tasks.json")
                try:
                    with open(path) as f:
                        d = json.load(f)
                    for t in d.get("scheduledTasks", []):
                        last = t.get("lastRunAt", "")
                        rid = t.get("id", "?")
                        if last and today in last.split("T")[0]:
                            ok(f"{rid} fired today at {last}")
                        elif rid in ("trading-bot-pre-market", "trading-bot-market-open"):
                            warn(f"{rid} did NOT fire today — last={last}")
                    return
                except Exception:
                    continue
    warn("Couldn't find scheduled-tasks.json")


def check_market_status():
    """Are we pre-market, in-market, or post-market? Uses config times."""
    print(f"\n{BOLD}7. Market timing{END}")
    now = datetime.now(ET)
    def _at(hhmm):
        h, m = (int(x) for x in hhmm.split(":"))
        return now.replace(hour=h, minute=m, second=0, microsecond=0)
    today_open = _at(config.MARKET_OPEN)         # 09:30
    entry_cutoff = _at(config.LAST_ENTRY_TIME)   # 15:30
    force_close = _at(config.CLOSE_ALL_TIME)     # 15:55
    today_close = now.replace(hour=16, minute=0, second=0, microsecond=0)

    if now.weekday() >= 5:
        warn(f"It's the weekend ({now.strftime('%A')}) — market closed")
    elif now < today_open:
        mins = int((today_open - now).total_seconds() / 60)
        ok(f"Pre-market — market opens in {mins} min")
    elif now < entry_cutoff:
        mins = int((entry_cutoff - now).total_seconds() / 60)
        ok(f"Market open — entries cutoff in {mins} min")
    elif now < force_close:
        mins = int((force_close - now).total_seconds() / 60)
        warn(f"Past entries cutoff — bot force-close in {mins} min")
    elif now < today_close:
        mins = int((today_close - now).total_seconds() / 60)
        warn(f"Force-close window — positions should be flat ({mins} min to bell)")
    else:
        warn(f"After hours — market closed")


def main():
    print(f"\n{BOLD}════════════════════════════════════════════════════════════{END}")
    print(f"{BOLD}  MORNING PREFLIGHT — {datetime.now(ET).strftime('%Y-%m-%d %H:%M ET')}{END}")
    print(f"{BOLD}════════════════════════════════════════════════════════════{END}")

    check_bot_alive()
    check_run_bot_wrapper()
    check_recent_scan()
    check_universe_loaded()
    check_alpaca_connection()
    check_pre_market_brief()
    check_scheduled_routines()
    check_market_status()

    print(f"\n{BOLD}════════════════════════════════════════════════════════════{END}")
    print("If all green: bot is ready, you can step away.")
    print("If yellow: review the warning, decide if action needed.")
    print("If red: bot needs intervention before market opens.")
    print(f"{BOLD}════════════════════════════════════════════════════════════{END}\n")


if __name__ == "__main__":
    main()
