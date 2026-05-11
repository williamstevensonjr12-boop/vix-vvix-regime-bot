"""
gap_go_live.py — Gap & Go live scanner and trader.

Validated config (from backtest):
  Gap ≥ 4% overnight | RVOL ≥ 1.5× at ORB | EMA20 on prev close | IWM > 20d EMA
  Risk 1.5% per trade | Entry window 9:45–11:00 AM ET | Force close 3:45 PM ET
  ORB breakout (9:30–9:44) → Fibonacci pullback entry → bracket order (stop + T1 target)
  Long-only (broker supports BUY brackets only)

Scan timing: two-phase
  Phase 1 (~9:32 AM): yfinance daily history → prev_close, EMA20 pre-filter
  Phase 2 (~9:32 AM): yfinance 1-min intraday → today's open → gap% calculation
  Phase 3 (9:45 AM): ORB RVOL check from Alpaca intraday bars
"""
from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import datetime, time as dt_time
from zoneinfo import ZoneInfo

import numpy as np
import pandas as pd
import yfinance as yf

from gap_go_universe import UNIVERSE

logger = logging.getLogger(__name__)
ET = ZoneInfo("America/New_York")

# ── Live parameters ───────────────────────────────────────────────────────────
MIN_GAP_PCT       = 4.0    # minimum overnight gap-up (%)
MIN_RVOL          = 1.5    # minimum relative volume at ORB vs 20-day avg scaled to 15 min
MIN_PRICE         = 2.0
MAX_PRICE         = 500.0
MAX_FLOAT_SHARES  = 100_000_000  # 100M shares — matches backtest config
RISK_PCT          = 0.015  # 1.5% of equity per trade
DAILY_LOSS_LIMIT  = 0.03   # halt entries if down 3% on the day
ORB_END_TIME      = "09:45"
ENTRY_END_TIME    = "11:00"
FORCE_CLOSE_TIME  = "15:45"
FIB_TOLERANCE     = 0.003  # 0.3% — price within this band of Fib entry level triggers
PULLBACK_VOL_MAX  = 0.40   # pullback bar vol must be < 40% of breakout bar vol
BREAKOUT_VOL_MULT = 1.5    # breakout bar must be ≥ 1.5× avg ORB bar vol
MAX_CANDIDATES    = 10     # top N gappers to scan intraday (sorted by gap%)
MAX_POSITIONS     = 3      # max concurrent positions
MIN_RR            = 2.0    # minimum risk:reward (entry→T1 / entry→stop) to enter
BAR_MINUTES       = 1      # 1-min bars for ORB / entry precision

# Fibonacci retracements and extensions
_FIB_RET = [0.236, 0.382, 0.500, 0.618, 0.786]
_FIB_EXT = [1.000, 1.272, 1.618, 2.000, 2.618]


# ── Fibonacci helpers ─────────────────────────────────────────────────────────

def _fib_levels(low: float, high: float) -> dict:
    rng = high - low
    ret = {f"r{int(f*1000)}": high - rng * f for f in _FIB_RET}
    ext = {f"e{int(f*1000)}": low  + rng * f for f in _FIB_EXT}
    return {**ret, **ext}


def _entry_key(rvol: float, gap_pct: float) -> str:
    if rvol >= 5 or gap_pct >= 8:
        return "r382"
    if rvol >= 3:
        return "r500"
    return "r618"


def _stop_key(entry_key: str) -> str:
    return {"r382": "r500", "r500": "r618", "r618": "r786"}.get(entry_key, "r786")


def _vwap(df: pd.DataFrame) -> pd.Series:
    typical = (df["high"] + df["low"] + df["close"]) / 3
    return (typical * df["volume"]).cumsum() / df["volume"].cumsum().replace(0, np.nan)


# ── Candidate state ───────────────────────────────────────────────────────────

@dataclass
class GapGoCandidate:
    symbol: str
    gap_pct: float
    rvol: float             # updated to actual ORB RVOL after 9:45
    prev_close: float
    today_open: float
    ema20_prev: float
    avg_daily_vol: float    # 20-day avg daily volume — used for ORB RVOL check
    premarket_rvol: float = 0.0   # pre-market volume vs avg daily (ranking signal)
    has_catalyst: bool = False    # confirmed news catalyst today
    # Populated after ORB closes (9:45)
    orb_high: float = 0.0
    orb_low: float = 0.0
    avg_orb_vol: float = 0.0
    # Populated after breakout confirmed
    breakout_confirmed: bool = False
    breakout_price: float = 0.0  # high of the breakout candle (B anchor)
    breakout_vol: float = 0.0
    fibs: dict = field(default_factory=dict)
    entry_key: str = ""
    entry_level: float = 0.0
    entry_price: float = 0.0     # actual fill price (set after entry)
    stop_level: float = 0.0
    target1: float = 0.0         # T1: 127.2% extension
    t2: float = 0.0              # T2: 161.8% extension
    t3: float = 0.0              # T3: 261.8% extension
    # Partial exit state
    qty_t1: int = 0
    qty_t2: int = 0
    qty_t3: int = 0
    stop_order_id: str = ""
    t1_order_id: str = ""
    t2_order_id: str = ""
    t3_order_id: str = ""
    t1_filled: bool = False
    t2_filled: bool = False
    # Runtime
    in_position: bool = False
    failed: bool = False           # price blew through r786 — abort setup


# ── IWM market filter ─────────────────────────────────────────────────────────

def check_iwm_filter() -> bool:
    """
    True (ok to trade) if IWM is above its 20-day EMA.
    Fail-open on data errors — don't block trading due to a fetch failure.
    """
    try:
        raw = yf.download("IWM", period="30d", interval="1d", progress=False)
        if isinstance(raw.columns, pd.MultiIndex):
            raw.columns = raw.columns.get_level_values(0)
        raw.columns = [c.lower() for c in raw.columns]
        if len(raw) < 21:
            logger.warning("IWM: insufficient history, allowing trades")
            return True
        ema20  = float(raw["close"].ewm(span=20, adjust=False).mean().iloc[-1])
        last   = float(raw["close"].iloc[-1])
        passes = last > ema20
        logger.info(
            f"IWM filter: close={last:.2f} ema20={ema20:.2f} → "
            f"{'PASS' if passes else 'SKIP (bearish small-cap regime)'}"
        )
        return passes
    except Exception as e:
        logger.warning(f"IWM filter error ({e}) — allowing trades (fail-open)")
        return True


# ── Pre-market gapper scan ────────────────────────────────────────────────────

def scan_gapper_candidates() -> list[GapGoCandidate]:
    """
    Two-phase scan:
      Phase 1: daily history (30d) for prev_close, EMA20, avg_daily_vol — pre-filter.
      Phase 2: 1-min intraday for pre-filtered symbols — get today's 9:30 open.
    RVOL is NOT checked here (daily volume is meaningless at 9:32 AM).
    ORB RVOL is checked later in update_candidate_state() after 9:45 AM.
    Returns top MAX_CANDIDATES by gap%, long-only.
    """
    today = datetime.now(ET).date()

    # ── Phase 1: daily history ────────────────────────────────────────────────
    logger.info(f"Fetching daily history for {len(UNIVERSE)} symbols...")
    try:
        daily_raw = yf.download(
            UNIVERSE,
            period="30d",
            interval="1d",
            progress=False,
            group_by="ticker",
            auto_adjust=False,
        )
    except Exception as e:
        logger.error(f"Daily download failed: {e}")
        return []

    # Pre-filter: price in range, prev close above EMA20
    prefiltered: list[dict] = []

    for sym in UNIVERSE:
        try:
            if isinstance(daily_raw.columns, pd.MultiIndex):
                if sym not in daily_raw.columns.get_level_values(0):
                    continue
                df = daily_raw[sym].copy()
            else:
                df = daily_raw.copy()

            if df is None or df.empty:
                continue

            df.columns = [c.lower() for c in df.columns]
            df = df.dropna(subset=["close", "volume"])

            # Use only completed trading days (exclude today's partial bar if present)
            df.index = pd.to_datetime(df.index)
            df_hist = df[df.index.date < today]
            if len(df_hist) < 21:
                continue

            prev_close    = float(df_hist.iloc[-1]["close"])
            avg_daily_vol = float(df_hist["volume"].tail(20).mean())
            ema20_prev    = float(df_hist["close"].ewm(span=20, adjust=False).mean().iloc[-1])

            if not (MIN_PRICE <= prev_close <= MAX_PRICE):
                continue
            if prev_close < ema20_prev:  # long-only: prev close must be above EMA20
                continue

            prefiltered.append({
                "symbol":       sym,
                "prev_close":   prev_close,
                "avg_daily_vol": avg_daily_vol,
                "ema20_prev":   ema20_prev,
            })
        except Exception:
            continue

    if not prefiltered:
        logger.warning("No symbols passed daily pre-filter")
        return []

    logger.info(f"  {len(prefiltered)} symbols passed EMA20/price pre-filter → applying float filter")

    # ── Float filter: < 100M shares (matches backtest config) ────────────────
    float_passed = []
    for p in prefiltered:
        try:
            shares = getattr(yf.Ticker(p["symbol"]).fast_info, "shares", None)
            if shares is None or shares < MAX_FLOAT_SHARES:
                float_passed.append(p)
            else:
                logger.debug(f"{p['symbol']}: float {shares / 1e6:.0f}M > 100M — skipped")
        except Exception:
            float_passed.append(p)  # fail-open on data error
    prefiltered = float_passed
    logger.info(f"  {len(prefiltered)} symbols passed float filter (<100M shares) → fetching today's opens")

    # ── Phase 2: today's intraday open (1-min, RTH only) ─────────────────────
    syms_to_check = [p["symbol"] for p in prefiltered]
    try:
        intra_raw = yf.download(
            syms_to_check,
            period="1d",
            interval="1m",
            progress=False,
            group_by="ticker",
            prepost=True,  # include pre-market for volume check
        )
    except Exception as e:
        logger.warning(f"Intraday open fetch failed ({e}) — using daily open as fallback")
        intra_raw = None

    def _get_intra(sym: str) -> pd.DataFrame | None:
        """Return full 1-min intraday df for symbol (pre-market + RTH)."""
        if intra_raw is None or intra_raw.empty:
            return None
        try:
            if isinstance(intra_raw.columns, pd.MultiIndex):
                if sym not in intra_raw.columns.get_level_values(0):
                    return None
                df = intra_raw[sym].copy()
            else:
                df = intra_raw.copy()
            df.columns = [c.lower() for c in df.columns]
            return df
        except Exception:
            return None

    def _get_today_open(sym: str) -> float | None:
        """Extract the 9:30 AM opening price from 1-min intraday data."""
        intra = _get_intra(sym)
        if intra is not None:
            try:
                rth_bars = intra[
                    (intra.index.hour > 9) |
                    ((intra.index.hour == 9) & (intra.index.minute >= 30))
                ]
                if not rth_bars.empty:
                    return float(rth_bars.iloc[0]["open"])
            except Exception:
                pass
        # Fallback: daily data's today bar
        try:
            if isinstance(daily_raw.columns, pd.MultiIndex):
                if sym not in daily_raw.columns.get_level_values(0):
                    return None
                df = daily_raw[sym].copy()
            else:
                df = daily_raw.copy()
            df.columns = [c.lower() for c in df.columns]
            df.index = pd.to_datetime(df.index)
            today_rows = df[df.index.date == today]
            if today_rows.empty:
                return None
            return float(today_rows.iloc[0]["open"])
        except Exception:
            return None

    def _get_premarket_rvol(sym: str, avg_daily_vol: float) -> float:
        """Pre-market volume (4 AM–9:29 AM) as ratio of avg daily volume."""
        intra = _get_intra(sym)
        if intra is None or avg_daily_vol <= 0:
            return 0.0
        try:
            pm = intra[
                (intra.index.hour >= 4) &
                ((intra.index.hour < 9) | ((intra.index.hour == 9) & (intra.index.minute < 30)))
            ]
            return float(pm["volume"].sum()) / avg_daily_vol if not pm.empty else 0.0
        except Exception:
            return 0.0

    def _check_catalyst(sym: str) -> bool:
        """True if yfinance news shows a relevant catalyst published today."""
        try:
            news = yf.Ticker(sym).news
            if not news:
                return False
            keywords = {
                "earnings", "fda", "approval", "approved", "trial", "data", "results",
                "merger", "acquisition", "acquired", "buyout", "partnership", "guidance",
                "beat", "beats", "raised", "upgrade", "upgraded", "contract", "deal",
            }
            for item in news[:5]:
                title = (item.get("title") or "").lower()
                pub_time = item.get("providerPublishTime", 0)
                # Only count news from today
                from datetime import timezone
                import time as _time
                if _time.time() - pub_time < 86400:  # within 24 hours
                    if any(kw in title for kw in keywords):
                        return True
        except Exception:
            pass
        return False

    # ── Build candidates ──────────────────────────────────────────────────────
    candidates: list[GapGoCandidate] = []

    for p in prefiltered:
        sym        = p["symbol"]
        prev_close = p["prev_close"]
        today_open = _get_today_open(sym)

        if today_open is None or today_open <= 0:
            continue
        if not (MIN_PRICE <= today_open <= MAX_PRICE):
            continue

        gap_pct = (today_open - prev_close) / prev_close * 100
        if gap_pct < MIN_GAP_PCT:
            continue  # long-only: require gap-up

        pm_rvol = _get_premarket_rvol(sym, p["avg_daily_vol"])
        catalyst = _check_catalyst(sym)

        candidates.append(GapGoCandidate(
            symbol=sym,
            gap_pct=round(gap_pct, 2),
            rvol=0.0,               # set in update_candidate_state after ORB
            prev_close=prev_close,
            today_open=today_open,
            ema20_prev=p["ema20_prev"],
            avg_daily_vol=p["avg_daily_vol"],
            premarket_rvol=round(pm_rvol, 2),
            has_catalyst=catalyst,
        ))

    # Sort: catalyst first, then by gap% + pre-market RVOL combined score
    candidates.sort(
        key=lambda c: (c.has_catalyst, c.gap_pct + c.premarket_rvol * 2),
        reverse=True,
    )
    top = candidates[:MAX_CANDIDATES]

    logger.info(f"  {len(candidates)} gap-up candidates → scanning top {len(top)}:")
    for c in top:
        logger.info(
            f"    {c.symbol:6s}  gap={c.gap_pct:+.1f}%  pm_rvol={c.premarket_rvol:.2f}x"
            f"  catalyst={'YES' if c.has_catalyst else 'no'}  open=${c.today_open:.2f}"
        )
    return top


# ── ORB / breakout / Fibonacci state machine ──────────────────────────────────

def update_candidate_state(cand: GapGoCandidate, intraday: pd.DataFrame) -> None:
    """
    Advance GapGoCandidate state from latest 1-min Alpaca bars. Safe to call repeatedly.
    State advances only forward: ORB check → RVOL gate → breakout detected → (failed).
    """
    if cand.failed or cand.in_position or intraday.empty:
        return

    # RTH only: 9:30–15:59
    rth = intraday[
        (intraday.index.hour > 9) |
        ((intraday.index.hour == 9) & (intraday.index.minute >= 30))
    ]
    rth = rth[rth.index.hour < 16].copy()
    if len(rth) < 5:
        return

    # ── ORB: 9:30–9:44 ───────────────────────────────────────────────────────
    orb = rth[(rth.index.hour == 9) & (rth.index.minute >= 30) & (rth.index.minute < 45)]
    if orb.empty:
        return

    cand.orb_high    = float(orb["high"].max())
    cand.orb_low     = float(orb["low"].min())
    cand.avg_orb_vol = float(orb["volume"].mean())

    # ── ORB RVOL gate (replaces pre-market RVOL check) ───────────────────────
    # Only run once (when rvol is still 0.0 — not yet computed)
    if cand.rvol == 0.0 and cand.avg_daily_vol > 0:
        orb_total_vol  = float(orb["volume"].sum())
        expected_15min = cand.avg_daily_vol * (15.0 / 390.0)  # 15 min / 390 RTH min
        orb_rvol       = orb_total_vol / expected_15min if expected_15min > 0 else 0.0
        cand.rvol      = round(orb_rvol, 2)
        if orb_rvol < MIN_RVOL:
            logger.info(
                f"{cand.symbol}: ORB RVOL {orb_rvol:.1f}× < {MIN_RVOL}× — skipping"
            )
            cand.failed = True
            return
        logger.info(f"{cand.symbol}: ORB RVOL={orb_rvol:.1f}×  orb_high={cand.orb_high:.2f}")

    if cand.breakout_confirmed:
        # Check if setup failed: long price closed below r786 retracement
        last_close = float(rth.iloc[-1]["close"])
        if "r786" in cand.fibs and last_close < cand.fibs["r786"]:
            logger.info(
                f"{cand.symbol}: setup FAILED — closed below r786={cand.fibs['r786']:.2f}"
            )
            cand.failed = True
        return

    # ── Entry window: 9:45–11:00 ─────────────────────────────────────────────
    rth.loc[:, "vwap"] = _vwap(rth)
    entry_start = dt_time(9, 45)
    entry_end   = dt_time(11, 0)
    entry_bars  = rth[
        (rth.index.time >= entry_start) &
        (rth.index.time <= entry_end)
    ]
    if entry_bars.empty:
        return

    bars_list = list(entry_bars.iterrows())

    for i, (ts, bar) in enumerate(bars_list):
        close = float(bar["close"])
        vol   = float(bar["volume"])
        vwap  = float(bar["vwap"]) if not pd.isna(bar["vwap"]) else close

        # Long breakout: close > ORB high, above VWAP, volume surge
        if close <= cand.orb_high:
            continue
        if close <= vwap:
            continue
        if cand.avg_orb_vol > 0 and vol < cand.avg_orb_vol * BREAKOUT_VOL_MULT:
            continue

        # False-breakout filter: next bar must not close back below ORB high
        if i + 1 < len(bars_list):
            next_close = float(bars_list[i + 1][1]["close"])
            if next_close <= cand.orb_high:
                continue

        # Confirmed breakout — compute Fibonacci levels
        cand.breakout_confirmed = True
        cand.breakout_price     = float(bar["high"])  # B anchor = breakout candle high
        cand.breakout_vol       = vol

        fibs = _fib_levels(cand.orb_low, cand.breakout_price)
        ek   = _entry_key(cand.rvol, cand.gap_pct)
        sk   = _stop_key(ek)
        buf  = max(0.05, abs(fibs[ek] - fibs[sk]) * 0.05)

        cand.fibs        = fibs
        cand.entry_key   = ek
        cand.entry_level = fibs[ek]
        cand.stop_level  = fibs[sk] - buf
        cand.target1 = fibs.get("e1272") or fibs.get("e1618") or (cand.breakout_price * 1.10)
        cand.t2      = fibs.get("e1618") or fibs.get("e2000") or (cand.breakout_price * 1.20)
        cand.t3      = fibs.get("e2618") or (cand.breakout_price * 1.35)

        logger.info(
            f"{cand.symbol}: BREAKOUT {close:.2f} (orb_high={cand.orb_high:.2f}) "
            f"→ entry={cand.entry_level:.2f} ({ek})  stop={cand.stop_level:.2f}  "
            f"t1={cand.target1:.2f}  rvol={cand.rvol:.1f}×"
        )
        break


def should_enter(cand: GapGoCandidate, intraday: pd.DataFrame) -> bool:
    """
    True if the latest bar is at the Fibonacci pullback entry level with declining volume
    AND we are still inside the entry window (before 11:00 AM).
    """
    if not cand.breakout_confirmed or cand.failed or cand.in_position:
        return False
    if intraday.empty:
        return False

    # Time gate: no entries at or after 11:00 AM
    now = datetime.now(ET)
    if now.time() >= dt_time(11, 0):
        return False

    bar   = intraday.iloc[-1]
    close = float(bar["close"])
    low   = float(bar["low"])
    vol   = float(bar["volume"])

    # Must still be above stop level
    if close <= cand.stop_level:
        return False

    # Volume must be declining (pullback condition)
    if cand.breakout_vol > 0 and vol > cand.breakout_vol * PULLBACK_VOL_MAX:
        return False

    # Price must be near entry Fib level (within tolerance or wicked through it and recovered)
    tol      = abs(cand.entry_level) * FIB_TOLERANCE
    at_level = (
        abs(close - cand.entry_level) <= tol
        or (low <= cand.entry_level and close > cand.entry_level)
    )
    if at_level:
        logger.info(
            f"{cand.symbol}: FIB ENTRY ZONE  close={close:.2f}  "
            f"level={cand.entry_level:.2f} ({cand.entry_key})"
        )
    return at_level


# ── Position sizing ───────────────────────────────────────────────────────────

def calculate_position_size(equity: float, entry_price: float, stop_price: float) -> int:
    """Risk 1.5% of equity per trade. Returns share count (0 if invalid stop)."""
    stop_dist = abs(entry_price - stop_price)
    if stop_dist <= 0:
        return 0
    return max(1, int(equity * RISK_PCT / stop_dist))
