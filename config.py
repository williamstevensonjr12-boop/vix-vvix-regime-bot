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
ORB_END_TIME = "09:50"
LAST_ENTRY_TIME = "15:30"
CLOSE_ALL_TIME = "15:55"
BAR_SIZE_MINUTES = 5
ORB_DURATION_MINUTES = 15

# ── Asset universes ──────────────────────────────────────────────────────────
# Regime A: momentum / trend-following
# LIVE universe (mega-caps) — restore to this after experiments:
# MOMENTUM_UNIVERSE: list = [
#     "SPY", "QQQ", "AAPL", "MSFT", "NVDA", "AMZN", "META", "TSLA", "AMD",
#     "KO", "BP", "NUE"
# ]
# LIVE — switched to 30-ticker small-cap universe 2026-04-29 after 4-period backtest validation
# (24-month total +13.41% Plain ORB, +10.78% ORB Full Sys with retracement entry in backtest)
# Original mega-cap universe preserved for revert:
# MEGA_CAP_UNIVERSE: list = [
#     "SPY", "QQQ", "AAPL", "MSFT", "NVDA", "AMZN", "META", "TSLA", "AMD",
#     "KO", "BP", "NUE"
# ]
MOMENTUM_UNIVERSE: list = [
    "SOFI", "PLTR", "RIOT", "UPST", "HOOD", "DKNG", "AFRM", "PLUG", "RKLB", "IONQ",
    "RIVN", "LCID", "NIO",
    "ENPH", "RUN", "FSLR",
    "MRNA", "CRSP", "BEAM", "TDOC",
    "SMCI", "AI", "BBAI",
    "MARA", "COIN", "MSTR",
    "ROKU", "OPEN", "ASTS", "ACHR",
]
SMALL_CAP_UNIVERSE: list = list(MOMENTUM_UNIVERSE)
MEGA_CAP_UNIVERSE: list = [
    "SPY", "QQQ", "AAPL", "MSFT", "NVDA", "AMZN", "META", "TSLA", "AMD",
    "KO", "BP", "NUE"
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

# Short sleeve (live paper) — high-VIX-beta names for ORB-breakdown shorts in Regime B/C
SHORT_UNIVERSE: list = ["QQQ", "XLK", "NVDA", "AMD", "TSLA", "META", "AMZN"]

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
    MOMENTUM_UNIVERSE + FEAR_RESILIENT_UNIVERSE + DEFENSIVE_UNIVERSE + SHORT_UNIVERSE
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
# 2026-04-30 — Removed put_call (10%) because the data source ^PCALL is dead on
# yfinance and free real-time CBOE P/C data isn't reliably available. P/C signal
# was silently inert (always neutral fallback). Redistributed 10% to vix_level
# (+5%) and vvix_level (+5%) — the closest fear-detection proxies. Sentiment
# filter in strategy.py still runs but always returns NEUTRAL, so per-entry
# behavior unchanged. Re-add put_call here if a real data source returns.
REGIME_WEIGHTS: dict = {
    "vix_level":      0.35,
    "vix_trend":      0.15,
    "vvix_level":     0.30,
    "spy_trend":      0.10,
    "term_structure": 0.10,
}
REGIME_A_THRESHOLD: float = 0.65
REGIME_B_THRESHOLD: float = 0.40

# ── VIX beta factor ───────────────────────────────────────────────────────────
VIX_BETA_LOOKBACK: int = 60
VIX_BETA_MIN_OBS: int = 30
TOP_SYMBOLS_FRACTION: float = 0.50   # trade top ~50% by fear resilience (top 4-5 of 9)

# A/B switch for the LONG (Regime A) VIX-beta hard-cut filter.
# True = rank universe by fear-resilience, keep top 50%.
# False = bypass the filter, scan the full regime universe.
#
# 2026-05-03 — flipped to False. Filter ablation across 4 windows (2023H1,
# 2023H2, 2024H1, 2024H2) showed 0 trade delta with this filter off — the
# active small-cap universe scores near-zero noisy beta on every name, so
# the top-50% cut never excludes anyone. Plus vix_factor.py:213 has an
# impl-vs-spec bug (sort direction inverted). Decorative gate, dropped.
ENABLE_VIX_BETA_FILTER: bool = False

# ── Risk management ───────────────────────────────────────────────────────────
RISK_PER_TRADE_PCT: float = 0.005     # 0.5% base
TARGET_ANNUALIZED_VOL: float = 0.15   # vol targeting denominator
REALIZED_VOL_LOOKBACK: int = 20       # days

ATR_PERIOD: int = 14
ATR_STOP_MULTIPLIER: float = 1.5
TAKE_PROFIT_R: float = 2.0
STOP_BUFFER_PCT: float = 0.004      # 0.4% — widened from 0.25% for small-cap spreads/slippage

# Fib extension target (Phase 1 experiment) — when enabled, target = entry ± FIB_LEVEL × ORB_range
# instead of fixed TAKE_PROFIT_R × risk. Falls back to fixed-R if ORB range unavailable.
USE_FIB_TARGET: bool = False
FIB_EXTENSION_LEVEL: float = 1.618

# Fib retracement entry (Phase 1 Test B) — when enabled, ORB break does NOT immediately enter;
# instead waits for pullback to FIB_RETRACEMENT_LEVEL of the post-break advance, then re-enters
# when price closes back above that level. Filters fake breakouts at cost of missed runners.
USE_FIB_RETRACEMENT_ENTRY: bool = False
FIB_RETRACEMENT_LEVEL: float = 0.382  # 0.382 = shallow, 0.5 = mid, 0.618 = deep pullback

# Regime-gated retracement (Phase 1 Test C) — only apply retracement filter when markets are calm.
# In gappy/volatile regimes, retracement filter misses runners and underperforms (validated by 2024 H2).
# When BOTH gates pass: use retracement entry. When EITHER fails: fall back to immediate ORB entry.
# 2026-04-30 update: discrepancy-hunt run showed gate=OFF produces cleaner Sharpe on Plain ORB
# (3.28 vs 2.84 on 2023H1) without materially changing trade count. Flipped to False.
USE_FIB_RETRACEMENT_REGIME_GATE: bool = False
FIB_RETRACEMENT_VIX_MAX: float = 20.0       # skip retracement when VIX above this (vol regime)
FIB_RETRACEMENT_VIX_TREND_MAX: float = 1.15  # skip when VIX rose >15% in last 3 trading days

REGIME_B_SIZE_FACTOR: float = 0.50
REGIME_C_SIZE_FACTOR: float = 0.25

PORTFOLIO_EXPOSURE_CAP: float = 0.50
MAX_OPEN_POSITIONS: int = 3
MAX_TRADES_PER_DAY: int = 5

DAILY_MAX_LOSS_PCT: float = 0.02
KILL_SWITCH_LOSS_PCT: float = 0.03    # hard stop all trading

VOLUME_LOOKBACK_BARS: int = 20
VOLUME_MULTIPLIER: float = 2.0      # 2.0x — tightened from 1.5x to filter small-cap volume noise
MIN_ORB_RANGE_PCT: float = 0.003   # skip flat opens (ORB range < 0.3% of price)
VWAP_VOL_MULTIPLIER: float = 2.0   # volume threshold for VWAP reclaim entries

# A/B switch for the volume-baseline metric. Phase 2 of the 2026-05-02 audit.
# False (default) = legacy rolling-20-bar simple average. The 20-bar baseline
#   averages over recent intraday bars regardless of time-of-day, mixing
#   high-volume open bars with lunch-chop bars. Effective threshold ~1.2-1.4×
#   vs same-time-of-day, much weaker than VOLUME_MULTIPLIER=2.0 implies.
# True = same-time-of-day median over prior 14 days (matches Zarattini et al.
#   and other published ORB literature). Stricter and more meaningful gate.
# Switch to True only after the Phase 2 backtest comparison shows it doesn't
# materially degrade total return / Sharpe, AND after re-tuning VOLUME_MULTIPLIER
# on the new baseline (likely needs to drop to 1.5-2.0× on this metric).
USE_TIME_OF_DAY_RVOL: bool = False
TIME_OF_DAY_RVOL_LOOKBACK_DAYS: int = 14
TIME_OF_DAY_RVOL_MIN_OBS: int = 5

# ── Optional filters ──────────────────────────────────────────────────────────
ENABLE_BREADTH_FILTER: bool = False
# 2026-05-03 — flipped to False. Filter ablation across 4 windows showed 0
# trade delta with this filter off. Decorative gate, dropped.
ENABLE_ATR_EXPANSION_FILTER: bool = False
SPY_TREND_FILTER: bool = True         # block Regime A entries when SPY < 20d MA
SPY_TREND_MA_PERIOD: int = 20
ATR_EXPANSION_MULTIPLIER: float = 1.2
REALIZED_VOL_BREAKOUT_MULTIPLIER: float = 1.3

# ── Limit-order entries (Phase 1) ─────────────────────────────────────────────
# When ON, ORB entries fire as marketable limit orders at ask + buffer (long)
# or bid - buffer (short) instead of market orders. Caps per-fill slippage at
# the buffer; can miss entries when price runs through the limit. See:
# 02 Projects/Trading Bot Project/[C] Limit Order Design Doc.md
USE_LIMIT_ORDER_ENTRIES: bool = True          # FLIPPED 2026-05-01 for paper validation
LIMIT_ORDER_BUFFER_PCT: float = 0.0010        # 10bp; matches realized slippage
LIMIT_ORDER_TIF: str = "ioc"                  # "ioc" | "fok" | "day"
LIMIT_ORDER_QUOTE_MAX_AGE_SEC: float = 2.0    # skip entry if quote staler than this
LIMIT_ORDER_FILL_POLL_SECONDS: float = 1.5    # how long to poll before declaring miss

# Gap filter — skip entries when SPY opens with a large gap (fake breakout risk)
ENABLE_GAP_FILTER: bool = True
GAP_FILTER_PCT: float = 0.007         # 0.7% gap vs prior close = skip day

# Time-of-day filter — block entries during lunch chop window
ENABLE_LUNCH_FILTER: bool = False
LUNCH_BLOCK_START: str = "11:00"      # stop entries at 11:00
LUNCH_BLOCK_END: str = "12:15"        # resume entries at 12:15 PM (after midday routine completes)

# Short sleeve (intraday ORB-breakdown shorts in Regime B/C)
ENABLE_SHORT_SLEEVE: bool = True
SHORT_REGIMES: tuple = ("B", "C")     # regimes that allow short entries
SHORT_VIX_BETA_MIN: float = 0.0       # only short symbols with positive VIX beta (fragile in vol spikes)

# Gap-continuation signal (off by default — pending end-of-week review)
ENABLE_GAP_CONTINUATION: bool = False
GAP_CONTINUATION_MIN_PCT: float = 0.010    # 1.0% gap vs prior close to qualify
GAP_CONTINUATION_VOL_MULTIPLIER: float = 2.0
GAP_CONTINUATION_HOLD_BARS: int = 2        # bars after open price must hold above gap level

# Gap-aligned ORB — gap direction must match trade direction
# Long ORB requires gap >= +threshold; short ORB requires gap <= -threshold.
# Strict mode: flat opens (within threshold) skipped entirely.
# Regime-aware: only enforce in regimes listed in GAP_ALIGNMENT_REGIMES (default: A only).
# In B/C the market mean-reverts after shocks — gap continuation thesis breaks.
# 2026-05-03 — flipped to False. Filter ablation across 4 windows showed 0
# trade delta with this filter off. Decorative gate, dropped.
GAP_ALIGNMENT_REQUIRED: bool = False
GAP_ALIGNMENT_THRESHOLD: float = 0.008     # 0.8% gap — raised from 0.5% (small caps gap on noise)
GAP_ALIGNMENT_REGIMES: tuple = ("A",)      # regime letters where gap filter applies

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
