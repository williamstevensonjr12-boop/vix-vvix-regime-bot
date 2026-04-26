#!/usr/bin/env bash
# research.sh — Market research via Tavily (free tier: 1,000 searches/month).
# Usage: bash scripts/research.sh "<query>"
# Falls back to yfinance news if TAVILY_API_KEY is unset.

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
ENV_FILE="$ROOT/.env"
if [[ -f "$ENV_FILE" ]]; then
  set -a
  source "$ENV_FILE"
  set +a
fi

query="${1:-}"
if [[ -z "$query" ]]; then
  echo "usage: bash scripts/research.sh \"<query>\"" >&2
  exit 1
fi

# ── Tavily (primary) ──────────────────────────────────────────────────────────
if [[ -n "${TAVILY_API_KEY:-}" ]]; then
  payload="$(python3 -c "
import json, sys
print(json.dumps({
  'api_key': sys.argv[1],
  'query': sys.argv[2],
  'search_depth': 'advanced',
  'include_answer': True,
  'include_raw_content': False,
  'max_results': 5,
  'topic': 'finance',
}))
" "$TAVILY_API_KEY" "$query")"

  curl -fsS https://api.tavily.com/search \
    -H "Content-Type: application/json" \
    -d "$payload"
  echo
  exit 0
fi

# ── yfinance fallback (completely free, no API key needed) ───────────────────
echo "WARNING: TAVILY_API_KEY not set. Falling back to yfinance news." >&2
python3 - "$query" <<'PYEOF'
import sys
import yfinance as yf

query = sys.argv[1]

# Pull news for tickers mentioned in query, plus SPY and VIX as defaults
tickers = ["SPY", "QQQ", "^VIX"]
for word in query.upper().split():
    if 1 < len(word) <= 5 and word.isalpha():
        tickers.append(word)

seen = set()
results = []
for ticker in tickers[:4]:
    try:
        news = yf.Ticker(ticker).news or []
        for item in news[:3]:
            title = item.get("title", "")
            if title and title not in seen:
                seen.add(title)
                results.append(f"[{ticker}] {title}")
    except Exception:
        pass

if results:
    print("\n".join(results[:10]))
else:
    print("No news available via yfinance fallback.")
PYEOF
