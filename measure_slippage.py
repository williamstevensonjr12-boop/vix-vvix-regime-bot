"""
measure_slippage.py — Measure realized slippage from actual paper-trading fills.

For each closed trade in trades.csv, computes:
  - Entry slippage:  (entry_price - intended_entry) / intended_entry
                     intended_entry = close of 5-min bar at trade_time (signal bar)
  - Exit slippage:   - WIN  trades: (target_price - exit_price) / target_price
                     - LOSS trades: (exit_price - stop_price)   / stop_price
  Both signed so positive = bad-for-us, negative = good-for-us.

Outputs:
  - Per-trade table: entry_slip%, exit_slip%, total round-trip%
  - Aggregate stats: median / 95th / mean
  - Buckets by symbol + by regime

Compares the realized number against our backtest assumption (0.03%) and the
research-agent estimate (0.10–0.25%).
"""
from __future__ import annotations
import csv
import os
import sys
import statistics
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import config
import data as mkt_data

ET = ZoneInfo(config.TIMEZONE)
TRADES_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "trades.csv")
ASSUMED_SLIP_PCT = config.SLIPPAGE_PCT * 100   # 0.03%

# ── Load trades ──────────────────────────────────────────────────────────────
def load_trades():
    rows = []
    with open(TRADES_PATH) as f:
        reader = csv.DictReader(f)
        for r in reader:
            try:
                r["entry_price"] = float(r["entry_price"])
                r["stop_price"] = float(r["stop_price"])
                r["target_price"] = float(r["target_price"])
                r["exit_price"] = float(r["exit_price"]) if r.get("exit_price") else None
                r["qty"] = int(r["qty"])
                r["pnl"] = float(r["pnl"])
                rows.append(r)
            except (ValueError, KeyError):
                continue
    return rows


def get_bar_at(client, symbol: str, trade_dt: datetime):
    """Pull the 5-min bar containing the given timestamp."""
    start = (trade_dt - timedelta(days=2)).strftime("%Y-%m-%d")
    end = (trade_dt + timedelta(days=1)).strftime("%Y-%m-%d")
    try:
        df = mkt_data.get_historical_bars(client, symbol, start, end)
    except Exception as e:
        return None
    if df is None or df.empty:
        return None
    if df.index.tz is None:
        df.index = df.index.tz_localize("UTC").tz_convert(ET)
    else:
        df.index = df.index.tz_convert(ET)
    # Find the bar whose start <= trade_dt < start + 5min
    for i in range(len(df)):
        bar_start = df.index[i]
        bar_end = bar_start + timedelta(minutes=5)
        if bar_start <= trade_dt < bar_end:
            return df.iloc[i]
    # Fallback — closest bar within 5 min
    deltas = abs((df.index - trade_dt).total_seconds())
    idx = deltas.argmin()
    if deltas[idx] <= 300:
        return df.iloc[idx]
    return None


def compute_slippage(trade, client):
    """Returns dict with entry_slip_pct, exit_slip_pct, valid flags."""
    out = {
        "date": trade["date"],
        "symbol": trade["symbol"],
        "regime": trade["regime"],
        "result": trade["result"],
        "qty": trade["qty"],
        "entry_price": trade["entry_price"],
        "exit_price": trade["exit_price"],
        "stop_price": trade["stop_price"],
        "target_price": trade["target_price"],
        "entry_slip_pct": None,
        "exit_slip_pct": None,
    }

    # Parse trade timestamp
    try:
        dt = datetime.strptime(f"{trade['date']} {trade['time']}", "%Y-%m-%d %H:%M:%S").replace(tzinfo=ET)
    except Exception:
        return out

    # Entry slippage — compare actual fill to bar close at signal time
    bar = get_bar_at(client, trade["symbol"], dt)
    if bar is not None:
        intended = float(bar["close"])
        if intended > 0:
            slip = (trade["entry_price"] - intended) / intended * 100
            out["entry_slip_pct"] = round(slip, 4)
            out["intended_entry"] = round(intended, 4)

    # Exit slippage — compare actual exit to bracket level
    if trade["exit_price"] is not None:
        if trade["result"] == "WIN" and trade["target_price"] > 0:
            slip = (trade["target_price"] - trade["exit_price"]) / trade["target_price"] * 100
            out["exit_slip_pct"] = round(slip, 4)
            out["intended_exit"] = trade["target_price"]
        elif trade["result"] == "LOSS" and trade["stop_price"] > 0:
            slip = (trade["exit_price"] - trade["stop_price"]) / trade["stop_price"] * 100
            # For longs, exit below stop = negative slippage (bad)
            # Sign convention: positive = bad-for-us
            slip = -slip
            out["exit_slip_pct"] = round(slip, 4)
            out["intended_exit"] = trade["stop_price"]
    return out


def get_summary(date_filter: str | None = None) -> dict:
    """
    Return realized slippage stats as a dict. Used by main.py:_save_daily_summary
    to append a slippage line to the EOD log.

    date_filter: 'YYYY-MM-DD' string, or None for all trades.
    Returns: {count, entry_median_pct, entry_mean_pct, exit_median_pct, exit_mean_pct}
             — empty {} if no fills available.
    """
    try:
        trades = load_trades()
    except Exception:
        return {}
    if date_filter:
        trades = [t for t in trades if t.get("date") == date_filter]
    trades = [t for t in trades if t.get("exit_price")]  # filled-and-closed only
    if not trades:
        return {}
    try:
        client = mkt_data.get_data_client()
    except Exception:
        return {}
    entry_slips, exit_slips = [], []
    for t in trades:
        try:
            r = compute_slippage(t, client)
            if r.get("entry_slip_pct") is not None:
                entry_slips.append(r["entry_slip_pct"])
            if r.get("exit_slip_pct") is not None:
                exit_slips.append(r["exit_slip_pct"])
        except Exception:
            continue
    if not entry_slips and not exit_slips:
        return {}
    return {
        "count": len(trades),
        "entry_median_abs_pct": statistics.median(abs(s) for s in entry_slips) if entry_slips else None,
        "entry_mean_signed_pct": statistics.mean(entry_slips) if entry_slips else None,
        "exit_median_abs_pct": statistics.median(abs(s) for s in exit_slips) if exit_slips else None,
        "exit_mean_signed_pct": statistics.mean(exit_slips) if exit_slips else None,
    }


def main():
    trades = load_trades()
    print(f"Loaded {len(trades)} trades from trades.csv\n")
    if not trades:
        print("No trades to analyze."); return

    print("Connecting to Alpaca...")
    client = mkt_data.get_data_client()

    print(f"Pulling bars for each trade (this takes ~30s for {len(trades)} trades)...\n")
    results = []
    for i, t in enumerate(trades):
        try:
            r = compute_slippage(t, client)
            results.append(r)
            print(f"  [{i+1}/{len(trades)}] {t['date']} {t['symbol']} {t['result']:<5} "
                  f"entry_slip={r['entry_slip_pct']}%  exit_slip={r['exit_slip_pct']}%")
        except Exception as e:
            print(f"  [{i+1}] {t['symbol']} ERROR: {e}")

    # ── Aggregate ────────────────────────────────────────────────────────────
    entry_slips = [r["entry_slip_pct"] for r in results if r["entry_slip_pct"] is not None]
    exit_slips  = [r["exit_slip_pct"]  for r in results if r["exit_slip_pct"]  is not None]

    def stats(label, vals):
        if not vals:
            print(f"  {label}: no data"); return
        absvals = sorted(abs(v) for v in vals)
        print(f"  {label} ({len(vals)} samples):")
        print(f"    median |slip|:    {statistics.median(absvals):.4f}%")
        print(f"    mean   |slip|:    {statistics.mean(absvals):.4f}%")
        print(f"    95th pct |slip|:  {absvals[int(len(absvals)*0.95)] if len(absvals)>1 else absvals[0]:.4f}%")
        print(f"    max  |slip|:      {max(absvals):.4f}%")
        print(f"    signed mean:      {statistics.mean(vals):+.4f}%   (positive = bad for us)")

    print(f"\n{'='*70}\nREALIZED SLIPPAGE SUMMARY  (assumption: {ASSUMED_SLIP_PCT:.2f}%)\n{'='*70}")
    stats("Entry slippage", entry_slips)
    print()
    stats("Exit slippage",  exit_slips)

    # By symbol
    print(f"\n{'─'*70}\nBy symbol (median |slip|, n samples):\n{'─'*70}")
    by_sym = {}
    for r in results:
        if r["entry_slip_pct"] is not None:
            by_sym.setdefault(r["symbol"], []).append(abs(r["entry_slip_pct"]))
    for sym, vals in sorted(by_sym.items(), key=lambda x: -statistics.median(x[1]) if x[1] else 0):
        print(f"  {sym:<6}  median {statistics.median(vals):.4f}%   max {max(vals):.4f}%   (n={len(vals)})")

    # Verdict vs assumption
    if entry_slips:
        median_entry = statistics.median(abs(s) for s in entry_slips)
        ratio = median_entry / ASSUMED_SLIP_PCT
        print(f"\n{'='*70}")
        if ratio > 3:
            print(f"VERDICT: Realized entry slippage is {ratio:.1f}× the {ASSUMED_SLIP_PCT}% assumption.")
            print(f"  → Backtest assumption is materially too optimistic. Re-run stress tests at realized levels.")
        elif ratio > 1.5:
            print(f"VERDICT: Realized entry slippage is {ratio:.1f}× the {ASSUMED_SLIP_PCT}% assumption.")
            print(f"  → Backtest assumption is somewhat optimistic. Consider tightening to {median_entry:.3f}%.")
        else:
            print(f"VERDICT: Realized entry slippage ({median_entry:.4f}%) is consistent with the {ASSUMED_SLIP_PCT}% assumption.")
            print(f"  → Backtest assumption is reasonable. Slippage is NOT the bottleneck.")
        print(f"{'='*70}")


if __name__ == "__main__":
    main()
