#!/usr/bin/env python3
"""
hang_watchdog.py — Detect and recover from a silent bot hang.

Background: 4/30 had an incident where the bot's Python process stayed alive
but stopped scanning for 16 minutes (15:29 → 15:45 ET). The run_bot.sh wrapper
auto-restarts on crash but not on hang — a hung Python process consuming a
Slack network-read with no exception isn't a "crash" from the wrapper's view.

This watchdog runs every 60s (via launchd) and:
  1. Checks if we're inside market hours (9:30-16:00 ET, weekday).
  2. Finds the latest /tmp/bot_output_*.log.
  3. Reads the most recent `Scan HH:MM` line and parses its timestamp.
  4. If last scan is older than HANG_THRESHOLD_SEC during market hours,
     SIGTERMs the bot's Python process. The run_bot.sh wrapper catches the
     exit and restarts within 30s.
  5. Logs the action to /tmp/trading-bot-hang-watchdog.log.

Safe-no-ops:
  - Outside market hours: do nothing.
  - Bot process not running: do nothing (wrapper or other automation handles it).
  - Bot just started (recent log entries within grace window): do nothing.
  - Log file not found: do nothing (bot hasn't started yet today).
"""
from __future__ import annotations
import glob
import os
import re
import signal
import subprocess
import sys
import time
from datetime import datetime, time as dtime
from pathlib import Path
from zoneinfo import ZoneInfo

ET = ZoneInfo("America/New_York")

# Tunables
HANG_THRESHOLD_SEC = 180   # 3 minutes — bot scans every ~60s; 3x is generous
GRACE_WINDOW_SEC   = 120   # don't act on a fresh process that just started
MARKET_OPEN  = dtime(9, 30)
MARKET_CLOSE = dtime(16, 0)

LOG_PATH = Path("/tmp/trading-bot-hang-watchdog.log")
SCAN_LINE = re.compile(
    r"^(\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2})\b.*\bScan \d{2}:\d{2}\b"
)


def log(msg: str) -> None:
    stamp = datetime.now(ET).strftime("%Y-%m-%d %H:%M:%S ET")
    line = f"{stamp}  {msg}\n"
    LOG_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(LOG_PATH, "a") as f:
        f.write(line)
    print(line.rstrip(), flush=True)


def in_market_hours() -> bool:
    now = datetime.now(ET)
    if now.weekday() >= 5:  # Sat/Sun
        return False
    return MARKET_OPEN <= now.time() <= MARKET_CLOSE


def find_latest_bot_log() -> Path | None:
    candidates = sorted(glob.glob("/tmp/bot_output_*.log"), reverse=True)
    if not candidates:
        return None
    # Most recently modified file (handles cross-day boundaries cleanly)
    return Path(max(candidates, key=lambda p: os.path.getmtime(p)))


def latest_scan_age(log_file: Path) -> float | None:
    """Return seconds since the last `Scan HH:MM` line, or None if no scan found."""
    try:
        with open(log_file) as f:
            tail = f.readlines()[-500:]
    except Exception as e:
        log(f"WARN: could not read {log_file}: {e}")
        return None
    for line in reversed(tail):
        m = SCAN_LINE.match(line)
        if m:
            try:
                ts = datetime.strptime(m.group(1), "%Y-%m-%d %H:%M:%S").replace(tzinfo=ET)
                return (datetime.now(ET) - ts).total_seconds()
            except ValueError:
                continue
    return None


def find_bot_pids() -> list[int]:
    """Return PIDs of `python ... main.py paper` processes."""
    try:
        out = subprocess.check_output(
            ["pgrep", "-f", "main.py paper"], stderr=subprocess.DEVNULL
        ).decode()
        return [int(x) for x in out.strip().split() if x.strip().isdigit()]
    except subprocess.CalledProcessError:
        return []


def process_age_sec(pid: int) -> float | None:
    """Return seconds since process started, or None if pid is gone."""
    try:
        out = subprocess.check_output(
            ["ps", "-o", "etime=", "-p", str(pid)], stderr=subprocess.DEVNULL
        ).decode().strip()
    except subprocess.CalledProcessError:
        return None
    # ps etime format: [[DD-]HH:]MM:SS
    parts = out.replace("-", ":").split(":")
    parts = [int(p) for p in parts]
    if len(parts) == 2:
        return parts[0] * 60 + parts[1]
    if len(parts) == 3:
        return parts[0] * 3600 + parts[1] * 60 + parts[2]
    if len(parts) == 4:
        return parts[0] * 86400 + parts[1] * 3600 + parts[2] * 60 + parts[3]
    return None


def kill_bot(pids: list[int]) -> None:
    for pid in pids:
        try:
            os.kill(pid, signal.SIGTERM)
            log(f"SIGTERM sent to bot PID {pid} (wrapper will restart)")
        except ProcessLookupError:
            pass
        except PermissionError:
            log(f"WARN: no permission to kill PID {pid}")


def main() -> int:
    if not in_market_hours():
        return 0
    log_file = find_latest_bot_log()
    if log_file is None:
        return 0  # Bot hasn't started today; nothing to watchdog
    age = latest_scan_age(log_file)
    if age is None:
        return 0  # No scan lines yet — bot may still be initializing
    pids = find_bot_pids()
    if not pids:
        # Bot process gone — wrapper or other supervisor handles restart
        return 0
    # Skip if any bot process is younger than the grace window
    youngest = min((process_age_sec(p) or 0) for p in pids)
    if youngest < GRACE_WINDOW_SEC:
        return 0
    if age > HANG_THRESHOLD_SEC:
        log(f"HANG DETECTED: last scan {age:.0f}s ago (threshold {HANG_THRESHOLD_SEC}s); "
            f"PID(s) {pids} alive; killing.")
        kill_bot(pids)
    return 0


if __name__ == "__main__":
    sys.exit(main())
