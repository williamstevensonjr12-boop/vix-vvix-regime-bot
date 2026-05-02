#!/usr/bin/env python3
"""
Idempotently re-apply approvedPermissions to all trading-bot scheduled routines.

Background: Claude Code's scheduled-tasks.json sometimes drops the
approvedPermissions field from routine entries (mechanism unclear — possibly
on routine edits via the UI, or on some app updates). When that happens, the
next cron fire stalls waiting for a manual permission prompt that nobody
clicks, and the routine silently does nothing.

Run this any time `trading-bot-intraday-scan` (or any other routine) goes
silent during expected hours, or pre-emptively as part of a morning preflight.

Required permissions per routine (matches the routines' actual tool usage):
  pre-market      → Read, Bash, WebSearch
  market-open     → Bash, Read
  midday          → Bash, Read
  intraday-scan   → Bash, Read
  daily-summary   → Bash, Read
  weekly-review   → Bash, Read
"""
from __future__ import annotations
import json
import shutil
import sys
import time
from pathlib import Path

REQUIRED = {
    "trading-bot-pre-market": [
        {"toolName": "Read"}, {"toolName": "Bash"}, {"toolName": "WebSearch"},
    ],
    "trading-bot-market-open":   [{"toolName": "Bash"}, {"toolName": "Read"}],
    "trading-bot-midday":        [{"toolName": "Bash"}, {"toolName": "Read"}],
    "trading-bot-intraday-scan": [{"toolName": "Bash"}, {"toolName": "Read"}],
    "trading-bot-daily-summary": [{"toolName": "Bash"}, {"toolName": "Read"}],
    "trading-bot-weekly-review": [{"toolName": "Bash"}, {"toolName": "Read"}],
}

# cwd must be /repo so Python's load_dotenv() finds .env via cwd, and so
# bash commands resolve relative paths sensibly even if any leak through.
REQUIRED_CWD = "/Users/prestonteel/Desktop/Cowork Homebase/02 Projects/Trading Bot Project/repo"

# scheduled-tasks.json lives under one (or both) of these roots
ROOTS = [
    Path.home() / "Library/Application Support/Claude/claude-code-sessions",
    Path.home() / "Library/Application Support/Claude/local-agent-mode-sessions",
]

def find_files() -> list[Path]:
    out = []
    for root in ROOTS:
        if root.exists():
            out.extend(root.glob("*/*/scheduled-tasks.json"))
    return out

def patch(fp: Path) -> tuple[int, int]:
    with open(fp) as f:
        data = json.load(f)
    tasks = data if isinstance(data, list) else data.get("tasks", data.get("scheduledTasks", []))
    if isinstance(tasks, dict):
        tasks = list(tasks.values())
    matched = changed = 0
    for t in tasks:
        tid = t.get("id")
        if tid in REQUIRED:
            matched += 1
            current = t.get("approvedPermissions") or []
            current_names = {p.get("toolName") for p in current}
            required_names = {p["toolName"] for p in REQUIRED[tid]}
            if current_names != required_names:
                t["approvedPermissions"] = REQUIRED[tid]
                changed += 1
            if t.get("cwd") != REQUIRED_CWD:
                t["cwd"] = REQUIRED_CWD
                changed += 1
    if changed:
        bak = fp.with_suffix(f".bak.{int(time.time())}")
        shutil.copy(fp, bak)
        with open(fp, "w") as f:
            json.dump(data, f, indent=2)
    return matched, changed

def main() -> int:
    files = find_files()
    if not files:
        print("No scheduled-tasks.json found.", file=sys.stderr)
        return 1
    total_changed = 0
    for fp in files:
        matched, changed = patch(fp)
        rel = str(fp).split("Application Support/Claude/", 1)[-1]
        print(f"{rel}: {matched} matched, {changed} updated")
        total_changed += changed
    print(f"\n{'CHANGED' if total_changed else 'OK'} ({total_changed} routines updated)")
    return 0

if __name__ == "__main__":
    sys.exit(main())
