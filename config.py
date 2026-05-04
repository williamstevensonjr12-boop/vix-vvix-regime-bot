"""
config.py — All settings for the Cameron VWAP-Bounce paper-trading bot.
No API keys hardcoded. All loaded from .env.
"""
from __future__ import annotations
import os
from dotenv import load_dotenv

# override=True so .env wins over any stale ALPACA_* vars left in the shell
# environment from prior sessions. Without this, fresh-process backtests
# silently picked up a revoked key and 401'd while the live wrapper (which
# always re-sources .env) worked — see 2026-05-03 universe A/B incident.
load_dotenv(override=True)

# ── Broker ──────────────────────────────────────────────────────────────────
ALPACA_API_KEY: str = os.getenv("ALPACA_API_KEY", "")
ALPACA_SECRET_KEY: str = os.getenv("ALPACA_SECRET_KEY", "")
PAPER_TRADING: bool = os.getenv("PAPER_TRADING", "true").lower() == "true"

if not PAPER_TRADING:
    raise RuntimeError(
        "\n" + "=" * 60 + "\n"
        "SAFETY BLOCK: PAPER_TRADING must be 'true'.\n"
        "This bot does NOT support live trading.\n"
        "=" * 60
    )
if not ALPACA_API_KEY or not ALPACA_SECRET_KEY:
    raise RuntimeError("ALPACA_API_KEY and ALPACA_SECRET_KEY must be set in .env")

# ── Market timing ────────────────────────────────────────────────────────────
TIMEZONE = "America/New_York"
MARKET_OPEN = "09:30"
LAST_ENTRY_TIME = "15:30"
CLOSE_ALL_TIME = "15:55"
BAR_SIZE_MINUTES = 5

# ── Universe ─────────────────────────────────────────────────────────────────
# 8 mega-caps. Chosen for institutional volume (VWAP/EMA levels actually hold)
# and clean trends. TSLA/AMD excluded — mega-cap by market cap but small-cap
# volatility, would generate setup-shaped traps. Crypto/meme names (COIN,
# MSTR, PLTR, MARA) excluded — wicks too wide for the 5-bar-low stop logic.
MOMENTUM_UNIVERSE: list = [
    "SPY", "QQQ", "AAPL", "MSFT", "NVDA", "GOOGL", "AMZN", "META",
]
ALL_SYMBOLS: list = list(MOMENTUM_UNIVERSE)

# ── Cameron VWAP-Bounce signal ───────────────────────────────────────────────
# Setup B (VWAP Bounce only — no breakout, no micro-pullback):
#   Long entry triggers when:
#     1. close > VWAP (above the line)
#     2. close > EMA_SLOW (200 EMA) — regime filter
#     3. EMA_FAST > EMA_MID (9 > 20) — trend confirmation
#     4. Within last VWAP_PULLBACK_LOOKBACK_BARS, at least one bar's low
#        came within VWAP_PULLBACK_TOLERANCE_PCT of VWAP — pullback signal
#     5. Current bar closes higher than previous bar's close — bounce signal
#     6. Current bar's relative volume >= CAMERON_VOLUME_MULTIPLIER — confirmation
#   Short entry: mirror (close < VWAP, close < 200 EMA, 9 < 20, recent high
#   touched VWAP from below, current bar closes lower with rvol confirmation)
EMA_FAST_PERIOD: int = 9
EMA_MID_PERIOD: int = 20
EMA_SLOW_PERIOD: int = 200
VWAP_PULLBACK_TOLERANCE_PCT: float = 0.0015   # 0.15% — how close low must come to VWAP
VWAP_PULLBACK_LOOKBACK_BARS: int = 3           # within last 3 bars must have touched
CAMERON_VOLUME_MULTIPLIER: float = 1.5         # rvol threshold on bounce bar
MIN_BARS_FOR_SIGNAL: int = 5                   # minimum session bars before any signal

# ── Stop logic ───────────────────────────────────────────────────────────────
# Structural: stop = min(prior 5 bar lows) for long, max for short.
# Guardrail: skip the trade if stop distance > ATR_GUARDRAIL_MULT × ATR
# (chop conditions, bad R:R).
STOP_LOOKBACK_BARS: int = 5
ATR_GUARDRAIL_MULT: float = 1.5
STOP_BUFFER_PCT: float = 0.004                 # 0.4% — extra cushion on stop

# ── Risk management ──────────────────────────────────────────────────────────
RISK_PER_TRADE_PCT: float = 0.0075             # 0.75% — bumped from 0.5% for Cameron
TARGET_ANNUALIZED_VOL: float = 0.15            # vol-targeting denominator
REALIZED_VOL_LOOKBACK: int = 20                # days

ATR_PERIOD: int = 14
ATR_STOP_MULTIPLIER: float = 1.5               # used by risk.calculate_position_size as fallback
TAKE_PROFIT_R: float = 2.0                     # 2R target (entry + 2 × risk_per_share)

PORTFOLIO_EXPOSURE_CAP: float = 0.50           # 50% of equity
MAX_OPEN_POSITIONS: int = 3
MAX_TRADES_PER_DAY: int = 5                    # restored from 0 (halt) — Cameron strategy live
DAILY_MAX_LOSS_PCT: float = 0.02               # 2% halt for the day
KILL_SWITCH_LOSS_PCT: float = 0.03             # 3% kill switch (no further entries until manual reset)

VOLUME_LOOKBACK_BARS: int = 20

# ── Limit-order entries ──────────────────────────────────────────────────────
# When True, entries fire as marketable limit orders at ask + buffer (long)
# or bid - buffer (short) instead of market orders. Caps per-fill slippage at
# the buffer; can miss entries when price runs through the limit.
USE_LIMIT_ORDER_ENTRIES: bool = True
LIMIT_ORDER_BUFFER_PCT: float = 0.0010         # 10bp; matches realized slippage
LIMIT_ORDER_TIF: str = "ioc"                   # "ioc" | "fok" | "day"
LIMIT_ORDER_QUOTE_MAX_AGE_SEC: float = 2.0     # skip entry if quote staler than this
LIMIT_ORDER_FILL_POLL_SECONDS: float = 1.5     # how long to poll before declaring miss

# ── Optional time-of-day filter (off by default) ────────────────────────────
# Cameron's setups typically fire in the first hour and last hour. Lunch
# (11:00–12:15) is choppy. Flip this on if backtest shows lunch trades are
# net dilutive.
ENABLE_LUNCH_FILTER: bool = False
LUNCH_BLOCK_START: str = "11:00"
LUNCH_BLOCK_END: str = "12:15"

# ── Backtest ─────────────────────────────────────────────────────────────────
SLIPPAGE_PCT: float = 0.0010                   # 10bp — match LIMIT_ORDER_BUFFER_PCT for live realism
INITIAL_EQUITY: float = 100_000.0

# ── Output ───────────────────────────────────────────────────────────────────
TRADES_CSV: str = "trades.csv"
PERFORMANCE_CSV: str = "performance.csv"
LOG_FILE: str = "trading_bot.log"
BACKTEST_RESULTS_DIR: str = "backtest_results"
