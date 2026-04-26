"""
config.py — All settings for VIX_VVIX_Regime_Alpha_Bot.
No API keys hardcoded. All loaded from .env.
"""
from __future__ import annotations
import os
from dotenv import load_dotenv

load_dotenv()

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
ORB_END_TIME = "09:45"
LAST_ENTRY_TIME = "12:00"   # data shows 9AM+11AM profitable, 12PM+ consistently loses money
CLOSE_ALL_TIME = "15:55"
BAR_SIZE_MINUTES = 5
ORB_DURATION_MINUTES = 15

# ── Asset universes ──────────────────────────────────────────────────────────
# Regime A: momentum / trend-following
MOMENTUM_UNIVERSE: list = [
    "SPY", "QQQ", "AAPL", "MSFT", "NVDA", "AMZN", "META", "TSLA", "AMD"
]
# Regime B: fear-resilient (low VIX-beta, quality)
FEAR_RESILIENT_UNIVERSE: list = [
    "XLU", "XLP", "XLV", "GLD", "MSFT", "JNJ", "PG", "COST"
]
# Regime C: full defensive
DEFENSIVE_UNIVERSE: list = ["XLU", "XLP", "XLV", "GLD"]

# Crisis alpha
CRISIS_ALPHA_LONG: list = ["XLU", "XLP", "XLV", "GLD"]
CRISIS_ALPHA_SHORT_BACKTEST: list = ["XLK", "QQQ", "AMD", "NVDA"]  # backtest only

# Sector ETF map
SECTOR_ETF_MAP: dict = {
    "utilities": "XLU",
    "staples": "XLP",
    "healthcare": "XLV",
    "energy": "XLE",
    "financials": "XLF",
    "tech": "XLK",
    "gold": "GLD",
    "quality": "QUAL",
}
ALL_SYMBOLS: list = list(dict.fromkeys(
    MOMENTUM_UNIVERSE + FEAR_RESILIENT_UNIVERSE + DEFENSIVE_UNIVERSE
))

# ── Volatility regime thresholds ─────────────────────────────────────────────
VIX_LOW_THRESHOLD: float = 15.0
VIX_REGIME_A_MAX: float = 20.0
VIX_REGIME_B_MAX: float = 25.0
VIX_REGIME_C_MIN: float = 25.0

VVIX_CAUTION: float = 110.0
VVIX_NO_TRADE: float = 120.0
VVIX_SPIKE_PCT: float = 0.10   # 10% intraday spike = emergency risk-off

VIX_TERM_BACKWARDATION: float = 1.05   # VIX/VIX3M > this = stress

# ── Regime factor weights (must sum to 1.0) ──────────────────────────────────
REGIME_WEIGHTS: dict = {
    "vix_level":      0.30,
    "vix_trend":      0.15,
    "vvix_level":     0.25,
    "put_call":       0.10,
    "spy_trend":      0.10,
    "term_structure": 0.10,
}
REGIME_A_THRESHOLD: float = 0.65
REGIME_B_THRESHOLD: float = 0.40

# ── VIX beta factor ───────────────────────────────────────────────────────────
VIX_BETA_LOOKBACK: int = 60
VIX_BETA_MIN_OBS: int = 30
TOP_SYMBOLS_FRACTION: float = 0.33   # trade top ~33% by fear resilience (top 3 of 9)

# ── Risk management ───────────────────────────────────────────────────────────
RISK_PER_TRADE_PCT: float = 0.005     # 0.5% base
TARGET_ANNUALIZED_VOL: float = 0.15   # vol targeting denominator
REALIZED_VOL_LOOKBACK: int = 20       # days

ATR_PERIOD: int = 14
ATR_STOP_MULTIPLIER: float = 1.5
TAKE_PROFIT_R: float = 3.0
STOP_BUFFER_PCT: float = 0.0025

REGIME_B_SIZE_FACTOR: float = 0.50
REGIME_C_SIZE_FACTOR: float = 0.25

PORTFOLIO_EXPOSURE_CAP: float = 0.50
MAX_OPEN_POSITIONS: int = 3
MAX_TRADES_PER_DAY: int = 5

DAILY_MAX_LOSS_PCT: float = 0.02
KILL_SWITCH_LOSS_PCT: float = 0.03    # hard stop all trading

VOLUME_LOOKBACK_BARS: int = 20
VOLUME_MULTIPLIER: float = 2.0
MIN_ORB_RANGE_PCT: float = 0.003   # skip flat opens (ORB range < 0.3% of price)

# ── Opening gap safety ────────────────────────────────────────────────────────
GAP_SKIP_PCT: float = 0.02        # skip day entirely if SPY gaps >2% up or down
GAP_REDUCE_PCT: float = 0.01      # cut position size 50% if SPY gaps 1-2%

# ── Optional filters ──────────────────────────────────────────────────────────
ENABLE_BREADTH_FILTER: bool = False
ENABLE_ATR_EXPANSION_FILTER: bool = True
SPY_TREND_FILTER: bool = True         # block Regime A entries when SPY < 20d MA
SPY_TREND_MA_PERIOD: int = 20
STOCK_TREND_FILTER: bool = False
STOCK_TREND_MA_PERIOD: int = 20
BREAKEVEN_STOP: bool = False
ATR_EXPANSION_MULTIPLIER: float = 1.2
REALIZED_VOL_BREAKOUT_MULTIPLIER: float = 1.3

# ── Backtest ──────────────────────────────────────────────────────────────────
SLIPPAGE_PCT: float = 0.0003
INITIAL_EQUITY: float = 100_000.0

# Walk-forward
WF_IN_SAMPLE_DAYS: int = 252
WF_OUT_SAMPLE_DAYS: int = 63

# ── Output ────────────────────────────────────────────────────────────────────
TRADES_CSV: str = "trades.csv"
PERFORMANCE_CSV: str = "performance.csv"
LOG_FILE: str = "trading_bot.log"
BACKTEST_RESULTS_DIR: str = "backtest_results"
