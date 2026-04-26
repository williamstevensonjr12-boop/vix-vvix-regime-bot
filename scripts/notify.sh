#!/usr/bin/env bash
# notify.sh — Send push notification via ntfy.sh
# Usage: bash scripts/notify.sh "message" ["title"] ["priority"]
# Priority: min | low | default | high | urgent
#
# Phone setup: install ntfy app, subscribe to topic in NTFY_TOPIC below

NTFY_TOPIC="${NTFY_TOPIC:-your-topic-here}"
NTFY_SERVER="${NTFY_SERVER:-https://ntfy.sh}"

MESSAGE="${1:-Notification from VIX Bot}"
TITLE="${2:-VIX/VVIX Regime Bot}"
PRIORITY="${3:-default}"

if [[ "$NTFY_TOPIC" == "your-topic-here" ]]; then
  echo "ERROR: set NTFY_TOPIC in .env or as env var" >&2
  exit 1
fi

curl -s \
  -H "Title: ${TITLE}" \
  -H "Priority: ${PRIORITY}" \
  -H "Tags: chart_with_upwards_trend" \
  -d "${MESSAGE}" \
  "${NTFY_SERVER}/${NTFY_TOPIC}" > /dev/null

echo "Notification sent: ${MESSAGE}"
