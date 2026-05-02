#!/usr/bin/env bash
# notify.sh — Send a typed push notification via ntfy.sh.
#
# Usage:
#   notify.sh "message"                                # legacy: simple notification
#   notify.sh TYPE "message"                           # typed notification (recommended)
#   notify.sh TYPE "message" "custom-title"            # override title
#
# TYPE controls priority + tag + title prefix:
#   entry    — trade opened          (high prio,  📈)
#   exit     — trade closed          (default,    💰)
#   regime   — regime transition     (high prio,  🚦)
#   alert    — kill switch / urgent  (urgent,     🚨)
#   eod      — end-of-day summary    (default,    📅)
#   info     — informational         (low prio,   ℹ️)
#
# Falls back to appending to DAILY-SUMMARY.md if ntfy is unreachable.
# Self-loads .env so it works from shells, routines, and cron equally.
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
ENV_FILE="$ROOT/.env"
FALLBACK="$ROOT/DAILY-SUMMARY.md"

if [[ -f "$ENV_FILE" ]]; then
  set -a
  # shellcheck disable=SC1090
  source "$ENV_FILE"
  set +a
fi

NTFY_TOPIC="${NTFY_TOPIC:-}"
NTFY_SERVER="${NTFY_SERVER:-https://ntfy.sh}"

# ── arg parsing: detect typed vs legacy form ────────────────────────────────
KNOWN_TYPES="entry exit regime alert eod info"
TYPE=""
MESSAGE=""
TITLE=""
PRIORITY=""
TAGS=""

if [[ $# -ge 2 ]] && [[ " $KNOWN_TYPES " == *" $1 "* ]]; then
  TYPE="$1"
  MESSAGE="$2"
  TITLE="${3:-}"
elif [[ $# -ge 1 ]]; then
  MESSAGE="$1"
  TITLE="${2:-}"
  PRIORITY="${3:-}"   # legacy 3rd arg
fi

if [[ -z "$MESSAGE" ]]; then
  echo "usage:" >&2
  echo "  notify.sh TYPE \"message\" [title]   # TYPE: $KNOWN_TYPES" >&2
  echo "  notify.sh \"message\"                 # legacy" >&2
  exit 1
fi

# ── per-type formatting ─────────────────────────────────────────────────────
case "$TYPE" in
  entry)
    : "${TITLE:=📈 Trade Opened}"; PRIORITY="${PRIORITY:-high}";    TAGS="chart_with_upwards_trend" ;;
  exit)
    : "${TITLE:=💰 Trade Closed}";  PRIORITY="${PRIORITY:-default}"; TAGS="moneybag" ;;
  regime)
    : "${TITLE:=🚦 Regime Change}"; PRIORITY="${PRIORITY:-high}";    TAGS="vertical_traffic_light" ;;
  alert)
    : "${TITLE:=🚨 Bot Alert}";     PRIORITY="${PRIORITY:-urgent}";  TAGS="rotating_light" ;;
  eod)
    : "${TITLE:=📅 EOD Summary}";   PRIORITY="${PRIORITY:-default}"; TAGS="calendar" ;;
  info)
    : "${TITLE:=ℹ️  VIX/VVIX Bot}"; PRIORITY="${PRIORITY:-low}";     TAGS="information_source" ;;
  *)
    : "${TITLE:=VIX/VVIX Regime Bot}"; PRIORITY="${PRIORITY:-default}"; TAGS="chart_with_upwards_trend" ;;
esac

stamp="$(date '+%Y-%m-%d %H:%M %Z')"

# ── send ────────────────────────────────────────────────────────────────────
if [[ -z "$NTFY_TOPIC" ]]; then
  echo "[notify] NTFY_TOPIC not set — falling back to file" >&2
  printf "\n---\n## %s [%s] (ntfy unconfigured)\n%s\n" "$stamp" "${TYPE:-msg}" "$MESSAGE" >> "$FALLBACK"
  exit 0
fi

if curl -fsS \
    -H "Title: ${TITLE}" \
    -H "Priority: ${PRIORITY}" \
    -H "Tags: ${TAGS}" \
    -d "${MESSAGE}" \
    "${NTFY_SERVER}/${NTFY_TOPIC}" > /dev/null 2>&1; then
  echo "[ntfy] [${TYPE:-msg}/${PRIORITY}] pushed to ${NTFY_SERVER}/${NTFY_TOPIC}"
  echo "${MESSAGE}"
  exit 0
fi

echo "[notify] ntfy push failed — falling back to file" >&2
printf "\n---\n## %s [%s] (ntfy push failed)\n%s\n" "$stamp" "${TYPE:-msg}" "$MESSAGE" >> "$FALLBACK"
echo "${MESSAGE}"
exit 0
