#!/usr/bin/env python3
"""
signal_density.py — When/where does Cameron VWAP-Bounce fire, and how much
                     would it have made?

Walks historical 5-min bars over the past N trading days, applies the 6
Cameron setup gates + stop-distance guardrail (exactly the checks in
strategy.py), and reports:

  PART A — signal density by time-of-day, day-of-week, symbol, side
  PART B — P&L simulation: enter at fire-bar close, bracket at stop / 2R,
            walk forward bar-by-bar to exit. Honors MAX_OPEN_POSITIONS=3
            and MAX_TRADES_PER_DAY=5 globally; force-close at 15:55 ET.

Caveats:
  - No slippage / commission modeled (paper account has none).
  - Same-bar stop+target: if both reach within one bar, assume stop fills
    first (conservative — matches Alpaca bracket OCO worst case).
  - Skips operational pre-gates (calendar, earnings, lunch filter) so the
    setup signal isn't masked by exogenous blockers.
  - This is a directional read, not audit-grade. Per the no-config-changes-
    without-evidence rule, don't tweak parameters from one backtest run.

Usage:
    python3 scripts/signal_density.py            # last 30 trading days
    python3 scripts/signal_density.py --days 60
    python3 scripts/signal_density.py --no-sim   # density only, skip sim
"""
from __future__ import annotations
import argparse
import os
import sys
from collections import Counter, defaultdict
from datetime import datetime, timedelta
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO))
os.chdir(REPO)

import pandas as pd  # noqa: E402

import config  # noqa: E402
import data as data_mod  # noqa: E402
import indicators as ind  # noqa: E402
import strategy as strat  # noqa: E402
from data import ET  # noqa: E402


def evaluate_day(symbol: str, bars: pd.DataFrame) -> list[dict]:
    """Walk a single day's bars; emit a fire-event dict for each bar where all
    Cameron setup gates + stop guardrail pass on long or short side. Each
    fire carries the entry/stop/target prices needed for P&L simulation."""
    fires: list[dict] = []
    if bars.empty or len(bars) < max(config.MIN_BARS_FOR_SIGNAL, config.STOP_LOOKBACK_BARS + 1):
        return fires

    vwap_s = ind.calculate_vwap(bars)
    ema_fast_s = ind.calculate_ema(bars["close"], config.EMA_FAST_PERIOD)
    ema_mid_s = ind.calculate_ema(bars["close"], config.EMA_MID_PERIOD)
    ema_slow_s = ind.calculate_ema(bars["close"], config.EMA_SLOW_PERIOD)
    atr_s = ind.calculate_atr(bars)
    rvol_s = ind.calculate_relative_volume(bars)

    if any(s.empty for s in (vwap_s, ema_fast_s, ema_mid_s, ema_slow_s, atr_s, rvol_s)):
        return fires

    start_idx = max(config.MIN_BARS_FOR_SIGNAL, config.STOP_LOOKBACK_BARS + 1)
    for i in range(start_idx, len(bars)):
        bar = bars.iloc[i]
        prior = bars.iloc[i - 1]
        price = float(bar["close"])
        vwap = float(vwap_s.iloc[i])
        ema_fast = float(ema_fast_s.iloc[i])
        ema_mid = float(ema_mid_s.iloc[i])
        ema_slow = float(ema_slow_s.iloc[i])
        atr = float(atr_s.iloc[i])
        rvol_raw = rvol_s.iloc[i]
        rvol = float(rvol_raw) if pd.notna(rvol_raw) else 0.0
        if atr <= 0:
            continue

        slice_bars = bars.iloc[: i + 1]
        slice_vwap = vwap_s.iloc[: i + 1]

        # ── LONG ─────────────────────────────────────────────────────────
        long_setup = (
            price > vwap
            and price > ema_slow
            and ema_fast > ema_mid
            and price > float(prior["close"])
            and rvol >= config.CAMERON_VOLUME_MULTIPLIER
        )
        if long_setup:
            pulled, _ = strat._recent_pullback_to_vwap(
                slice_bars, slice_vwap, side="long",
                lookback=config.VWAP_PULLBACK_LOOKBACK_BARS,
                tolerance_pct=config.VWAP_PULLBACK_TOLERANCE_PCT,
            )
            if pulled:
                prior_lows = bars["low"].iloc[i - config.STOP_LOOKBACK_BARS:i]
                stop = float(prior_lows.min())
                risk = price - stop
                if 0 < risk <= config.ATR_GUARDRAIL_MULT * atr:
                    target = round(price + config.TAKE_PROFIT_R * risk, 2)
                    fires.append({
                        "ts": bar.name, "symbol": symbol, "side": "long",
                        "entry": price, "stop": round(stop, 2), "target": target,
                        "rvol": rvol, "risk_atr": risk / atr, "bar_idx": i,
                    })

        # ── SHORT ────────────────────────────────────────────────────────
        short_setup = (
            price < vwap
            and price < ema_slow
            and ema_fast < ema_mid
            and price < float(prior["close"])
            and rvol >= config.CAMERON_VOLUME_MULTIPLIER
        )
        if short_setup:
            pulled, _ = strat._recent_pullback_to_vwap(
                slice_bars, slice_vwap, side="short",
                lookback=config.VWAP_PULLBACK_LOOKBACK_BARS,
                tolerance_pct=config.VWAP_PULLBACK_TOLERANCE_PCT,
            )
            if pulled:
                prior_highs = bars["high"].iloc[i - config.STOP_LOOKBACK_BARS:i]
                stop = float(prior_highs.max())
                risk = stop - price
                if 0 < risk <= config.ATR_GUARDRAIL_MULT * atr:
                    target = round(price - config.TAKE_PROFIT_R * risk, 2)
                    fires.append({
                        "ts": bar.name, "symbol": symbol, "side": "short",
                        "entry": price, "stop": round(stop, 2), "target": target,
                        "rvol": rvol, "risk_atr": risk / atr, "bar_idx": i,
                    })

    return fires


# ── P&L simulation ───────────────────────────────────────────────────────────

def _simulate_exit(side: str, entry: float, stop: float, target: float,
                   forward_bars: pd.DataFrame) -> tuple[float, str, pd.Timestamp]:
    """Walk bar-by-bar from one bar after entry until stop, target, or 15:55
    EOD force-close. Returns (exit_price, reason, exit_ts).

    Same-bar both-touch resolution: stop wins (conservative — matches OCO
    bracket worst case where the stop side fills first)."""
    for ts, b in forward_bars.iterrows():
        hi, lo, close = float(b["high"]), float(b["low"]), float(b["close"])
        if side == "long":
            if lo <= stop:
                return stop, "stop", ts
            if hi >= target:
                return target, "target", ts
        else:
            if hi >= stop:
                return stop, "stop", ts
            if lo <= target:
                return target, "target", ts
        # 15:55 force close (use bar at or after CLOSE_ALL_TIME)
        ts_str = ts.strftime("%H:%M")
        if ts_str >= config.CLOSE_ALL_TIME:
            return close, "eod", ts
    # Ran out of bars without exit (shouldn't happen with intra-day cutoff)
    last = forward_bars.iloc[-1]
    return float(last["close"]), "eod", last.name


def simulate_pnl(fires: list[dict], bars_by_symbol: dict[str, pd.DataFrame],
                 start_equity: float = 100_000.0) -> dict:
    """Sequential simulator. Honors MAX_OPEN_POSITIONS, MAX_TRADES_PER_DAY,
    no-doubling-up-on-symbol. Equity-aware sizing per Cameron 0.75% risk."""
    fires = sorted(fires, key=lambda f: f["ts"])
    equity = start_equity
    open_positions: dict[str, dict] = {}  # symbol → trade dict
    trades_today: int = 0
    last_day = None
    closed: list[dict] = []
    equity_curve: list[tuple[pd.Timestamp, float]] = [(fires[0]["ts"], equity)] if fires else []

    def close_open_at(ts: pd.Timestamp):
        """Resolve any open positions whose exit happens at or before ts."""
        nonlocal equity
        to_pop = []
        for sym, tr in open_positions.items():
            if tr["exit_ts"] <= ts:
                pnl = tr["pnl"]
                equity += pnl
                tr["equity_after"] = equity
                closed.append(tr)
                equity_curve.append((tr["exit_ts"], equity))
                to_pop.append(sym)
        for s in to_pop:
            open_positions.pop(s)

    for f in fires:
        ts = f["ts"]
        day = ts.date()
        if day != last_day:
            # Close any positions that should have exited intraday on the previous day
            if last_day is not None:
                close_open_at(ts)
            trades_today = 0
            last_day = day

        # Resolve any open trades that exited before this fire's timestamp
        close_open_at(ts)

        # Operational gates (mirroring strategy.py)
        if ts.strftime("%H:%M") >= config.LAST_ENTRY_TIME:
            continue
        if trades_today >= config.MAX_TRADES_PER_DAY:
            continue
        if len(open_positions) >= config.MAX_OPEN_POSITIONS:
            continue
        if f["symbol"] in open_positions:
            continue

        entry = f["entry"]
        stop = f["stop"]
        target = f["target"]
        side = f["side"]
        risk_per_share = abs(entry - stop)
        if risk_per_share <= 0:
            continue

        # Sizing: 0.75% risk × equity, capped at 2× base
        risk_dollars = equity * config.RISK_PER_TRADE_PCT
        qty = int(risk_dollars / risk_per_share)
        if qty <= 0:
            continue

        # Walk forward to find exit
        sym_bars = bars_by_symbol[f["symbol"]]
        future = sym_bars[sym_bars.index > ts]
        # Restrict to the same trading day
        future = future[future.index.map(lambda t: t.date() == day)]
        if future.empty:
            continue
        exit_price, exit_reason, exit_ts = _simulate_exit(side, entry, stop, target, future)
        if side == "long":
            pnl = (exit_price - entry) * qty
        else:
            pnl = (entry - exit_price) * qty

        trade = {
            "entry_ts": ts, "exit_ts": exit_ts,
            "symbol": f["symbol"], "side": side,
            "entry": entry, "stop": stop, "target": target,
            "exit": exit_price, "qty": qty,
            "pnl": round(pnl, 2),
            "reason": exit_reason,
            "risk_per_share": round(risk_per_share, 4),
            "r_multiple": round(pnl / (qty * risk_per_share), 3) if qty * risk_per_share > 0 else 0,
        }
        open_positions[f["symbol"]] = trade
        trades_today += 1

    # Final flush — close any positions still open
    if open_positions:
        last_ts = max(tr["exit_ts"] for tr in open_positions.values())
        close_open_at(last_ts + pd.Timedelta(seconds=1))

    return {
        "trades": closed,
        "start_equity": start_equity,
        "end_equity": equity,
        "total_pnl": equity - start_equity,
        "equity_curve": equity_curve,
    }


def time_bucket(ts: pd.Timestamp) -> str:
    """30-min bucket label, e.g. '09:30-10:00'."""
    h = ts.hour
    half = 0 if ts.minute < 30 else 30
    end_h = h + (1 if half == 30 else 0)
    end_m = 0 if half == 30 else 30
    return f"{h:02d}:{half:02d}-{end_h:02d}:{end_m:02d}"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--days", type=int, default=30,
                    help="Trading-day lookback window (default 30)")
    ap.add_argument("--equity", type=float, default=100_000.0,
                    help="Starting equity for the P&L simulation (default 100k)")
    ap.add_argument("--no-sim", action="store_true",
                    help="Skip P&L simulation (density report only)")
    args = ap.parse_args()

    end_date = datetime.now(ET).date()
    # Pad calendar days × 1.6 to cover weekends + holidays
    start_date = end_date - timedelta(days=int(args.days * 1.6))

    client = data_mod.get_data_client()
    print(f"Pulling {args.days} trading days of 5-min bars for "
          f"{len(config.MOMENTUM_UNIVERSE)} symbols...")
    print(f"  Date range: {start_date} → {end_date}")

    all_fires: list[dict] = []
    bars_by_symbol: dict[str, pd.DataFrame] = {}

    for sym in config.MOMENTUM_UNIVERSE:
        bars = data_mod.get_historical_bars(client, sym, start_date.isoformat(), end_date.isoformat())
        if bars.empty:
            print(f"  {sym}: no bars")
            continue
        # Restrict to last `args.days` unique trading days
        unique_days = sorted({b.date() for b in bars.index})
        keep_days = set(unique_days[-args.days:])
        bars = bars[bars.index.map(lambda t: t.date() in keep_days)]
        bars_by_symbol[sym] = bars

        sym_fires = []
        for day in sorted(keep_days):
            day_bars = bars[bars.index.map(lambda t: t.date() == day)]
            sym_fires.extend(evaluate_day(sym, day_bars))
        all_fires.extend(sym_fires)
        print(f"  {sym}: {len(bars)} bars across {len(keep_days)} days, {len(sym_fires)} fires")

    n = len(all_fires)
    if n == 0:
        print("\nNo fires found in the window. Check data availability.")
        return

    print(f"\n{'='*64}")
    print(f"  CAMERON VWAP-BOUNCE — SIGNAL DENSITY  (last {args.days} trading days)")
    print(f"  Total fires: {n}  |  Avg per day: {n / args.days:.1f}")
    print(f"{'='*64}\n")

    # ── By time-of-day (30-min buckets) ──────────────────────────────────
    bucket_counts = Counter(time_bucket(f["ts"]) for f in all_fires)
    bucket_long = Counter(time_bucket(f["ts"]) for f in all_fires if f["side"] == "long")
    bucket_short = Counter(time_bucket(f["ts"]) for f in all_fires if f["side"] == "short")
    print("── BY TIME OF DAY (ET) ──────────────────────────────────────────")
    print(f"  {'Bucket':<14}  {'Total':>6}  {'L':>4}  {'S':>4}  {'%':>5}  bar")
    max_b = max(bucket_counts.values())
    for bucket in sorted(bucket_counts):
        c = bucket_counts[bucket]
        l = bucket_long.get(bucket, 0)
        s = bucket_short.get(bucket, 0)
        pct = c / n * 100
        bar = "█" * (c * 30 // max_b)
        print(f"  {bucket:<14}  {c:>6}  {l:>4}  {s:>4}  {pct:>4.1f}%  {bar}")

    # ── By day of week ───────────────────────────────────────────────────
    dow_counts = Counter(f["ts"].day_name() for f in all_fires)
    dow_order = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday"]
    print("\n── BY DAY OF WEEK ───────────────────────────────────────────────")
    print(f"  {'Day':<12}  {'Fires':>6}  {'%':>5}")
    for d in dow_order:
        c = dow_counts.get(d, 0)
        pct = c / n * 100 if n else 0
        print(f"  {d:<12}  {c:>6}  {pct:>4.1f}%")

    # ── By symbol ────────────────────────────────────────────────────────
    sym_counts = Counter(f["symbol"] for f in all_fires)
    sym_long = Counter(f["symbol"] for f in all_fires if f["side"] == "long")
    sym_short = Counter(f["symbol"] for f in all_fires if f["side"] == "short")
    print("\n── BY SYMBOL ────────────────────────────────────────────────────")
    print(f"  {'Symbol':<8}  {'Total':>6}  {'L':>4}  {'S':>4}  {'%':>5}")
    for sym, c in sorted(sym_counts.items(), key=lambda x: -x[1]):
        l = sym_long.get(sym, 0)
        s = sym_short.get(sym, 0)
        pct = c / n * 100
        print(f"  {sym:<8}  {c:>6}  {l:>4}  {s:>4}  {pct:>4.1f}%")

    # ── Side breakdown ───────────────────────────────────────────────────
    side_counts = Counter(f["side"] for f in all_fires)
    print("\n── BY SIDE ──────────────────────────────────────────────────────")
    for side, c in side_counts.items():
        print(f"  {side:<8}  {c:>6}  {c/n*100:>4.1f}%")

    # ── Top 5 hottest single-day-symbols ─────────────────────────────────
    day_sym = defaultdict(int)
    for f in all_fires:
        day_sym[(f["ts"].date(), f["symbol"])] += 1
    print("\n── HOTTEST DAY × SYMBOL (top 5) ─────────────────────────────────")
    for (d, s), c in sorted(day_sym.items(), key=lambda x: -x[1])[:5]:
        print(f"  {d}  {s:<6}  {c} fires")

    if args.no_sim:
        print()
        return

    # ─────────────────────────────────────────────────────────────────────
    # PART B — P&L simulation
    # ─────────────────────────────────────────────────────────────────────
    print(f"\n{'='*64}")
    print(f"  P&L SIMULATION  (start equity: ${args.equity:,.0f})")
    print(f"{'='*64}\n")

    sim = simulate_pnl(all_fires, bars_by_symbol, start_equity=args.equity)
    trades = sim["trades"]
    if not trades:
        print("  No trades executed (all fires blocked by daily/position caps).")
        return

    wins = [t for t in trades if t["pnl"] > 0]
    losses = [t for t in trades if t["pnl"] <= 0]
    total_pnl = sim["total_pnl"]
    win_rate = len(wins) / len(trades) if trades else 0
    gross_win = sum(t["pnl"] for t in wins)
    gross_loss = abs(sum(t["pnl"] for t in losses))
    profit_factor = gross_win / gross_loss if gross_loss > 0 else float("inf")
    avg_win = gross_win / len(wins) if wins else 0
    avg_loss = -gross_loss / len(losses) if losses else 0
    avg_r = sum(t["r_multiple"] for t in trades) / len(trades)

    # Drawdown on the equity curve
    peak = sim["start_equity"]
    max_dd = 0.0
    for _, eq in sim["equity_curve"]:
        peak = max(peak, eq)
        max_dd = max(max_dd, peak - eq)

    print(f"  Total trades       : {len(trades)}  ({len(wins)}W / {len(losses)}L)")
    print(f"  Win rate           : {win_rate:.1%}")
    print(f"  Profit factor      : {profit_factor:.2f}")
    print(f"  Avg win            : ${avg_win:+,.2f}")
    print(f"  Avg loss           : ${avg_loss:+,.2f}")
    print(f"  Avg R-multiple     : {avg_r:+.2f}R")
    print(f"  Total P&L          : ${total_pnl:+,.2f}  ({total_pnl/args.equity*100:+.2f}%)")
    print(f"  Max drawdown       : ${max_dd:,.2f}  ({max_dd/args.equity*100:.2f}%)")
    print(f"  End equity         : ${sim['end_equity']:,.2f}")
    print(f"  Trades blocked     : {len(all_fires) - len(trades)} (caps / dup symbol / past 15:30)")

    # Exit-reason breakdown
    by_reason = Counter(t["reason"] for t in trades)
    print(f"\n  Exit reasons:")
    for reason, c in by_reason.most_common():
        pct = c / len(trades) * 100
        print(f"    {reason:<8}  {c:>3}  ({pct:.1f}%)")

    # Win-rate by side
    long_t = [t for t in trades if t["side"] == "long"]
    short_t = [t for t in trades if t["side"] == "short"]
    if long_t:
        wr_l = sum(1 for t in long_t if t["pnl"] > 0) / len(long_t)
        pnl_l = sum(t["pnl"] for t in long_t)
        print(f"\n  Long  : {len(long_t)} tr  WR {wr_l:.1%}  P&L ${pnl_l:+,.2f}")
    if short_t:
        wr_s = sum(1 for t in short_t if t["pnl"] > 0) / len(short_t)
        pnl_s = sum(t["pnl"] for t in short_t)
        print(f"  Short : {len(short_t)} tr  WR {wr_s:.1%}  P&L ${pnl_s:+,.2f}")

    # P&L by time-of-day bucket
    bucket_pnl: dict[str, float] = defaultdict(float)
    bucket_n: dict[str, int] = defaultdict(int)
    for t in trades:
        b = time_bucket(t["entry_ts"])
        bucket_pnl[b] += t["pnl"]
        bucket_n[b] += 1
    print(f"\n  P&L by entry time:")
    print(f"    {'Bucket':<14}  {'Tr':>3}  {'P&L':>12}")
    for b in sorted(bucket_pnl):
        print(f"    {b:<14}  {bucket_n[b]:>3}  ${bucket_pnl[b]:>+10,.2f}")

    # Top 5 best & worst trades
    print(f"\n  Top 5 winners:")
    for t in sorted(trades, key=lambda x: -x["pnl"])[:5]:
        print(f"    {t['entry_ts'].strftime('%Y-%m-%d %H:%M')}  {t['symbol']:<6} "
              f"{t['side']:<5}  ${t['pnl']:>+9,.2f}  ({t['r_multiple']:+.2f}R, {t['reason']})")
    print(f"\n  Top 5 losers:")
    for t in sorted(trades, key=lambda x: x["pnl"])[:5]:
        print(f"    {t['entry_ts'].strftime('%Y-%m-%d %H:%M')}  {t['symbol']:<6} "
              f"{t['side']:<5}  ${t['pnl']:>+9,.2f}  ({t['r_multiple']:+.2f}R, {t['reason']})")

    print()


if __name__ == "__main__":
    main()
