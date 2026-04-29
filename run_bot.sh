#!/bin/bash
# run_bot.sh — Auto-restart wrapper for python main.py paper
# If the bot crashes (wifi drop, API error, etc.) it restarts after 30 seconds.
# Usage: bash run_bot.sh

cd "/Users/prestonteel/Desktop/Cowork Homebase/02 Projects/Trading Bot Project /repo"
source .venv/bin/activate
set -a; source .env; set +a

echo "$(date): Bot starting..."

while true; do
    python main.py paper
    EXIT_CODE=$?

    # Clean exit (EOD shutdown at 3:55) — don't restart
    if [ $EXIT_CODE -eq 0 ]; then
        echo "$(date): Bot exited cleanly. Session complete."
        break
    fi

    # Crash or network error — restart after 30s
    echo "$(date): Bot crashed (exit $EXIT_CODE). Restarting in 30 seconds..."
    sleep 30
done
