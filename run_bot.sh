#!/bin/bash
# run_bot.sh — Persistent auto-restart wrapper for python main.py paper.
# Restarts on ANY exit (crash or clean EOD), so the bot stays alive across days.
# After clean EOD, Python's startup loop blocks on broker.is_market_open() until
# the next session.
# Usage: bash run_bot.sh > /tmp/bot_output_$(date +%Y%m%d).log 2>&1 &
# To stop: pkill -f run_bot.sh

cd "/Users/prestonteel/Desktop/Cowork Homebase/02 Projects/Trading Bot Project/repo"
source .venv/bin/activate
set -a; source .env; set +a

echo "$(date): Bot starting..."

while true; do
    python main.py paper
    EXIT_CODE=$?

    if [ $EXIT_CODE -eq 0 ]; then
        # Clean exit — usually EOD shutdown. Pause briefly then restart so the
        # bot is ready to wait on tomorrow's market open.
        echo "$(date): Bot exited cleanly (EOD). Restarting in 60 seconds for next session..."
        sleep 60
    else
        # Crash or network error — short restart delay.
        echo "$(date): Bot crashed (exit $EXIT_CODE). Restarting in 30 seconds..."
        sleep 30
    fi
done
