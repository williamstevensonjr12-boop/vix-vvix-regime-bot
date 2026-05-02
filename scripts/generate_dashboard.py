#!/usr/bin/env python3
"""
generate_dashboard.py — Render dashboard.html from live data.

Reads:
  - repo/trades.csv         (per-trade records; uses TRADE_FIELDS schema, header in
                             the file is stale and ignored)
  - repo/performance.csv    (per-day aggregates; deduped — takes last row per date)
  - Alpaca paper account    (live equity, current positions)
  - repo/config.py          (current regime — re-computed via main regime-status)

Writes:
  - repo/dashboard.html

Usage:  python3 scripts/generate_dashboard.py
"""
from __future__ import annotations
import csv
import os
import sys
from datetime import date, datetime
from pathlib import Path
from collections import OrderedDict

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO))

# Importing config triggers load_dotenv from repo/.env when cwd is repo
os.chdir(REPO)
import config  # noqa: E402

TRADE_FIELDS = [
    "date", "symbol", "side", "setup", "entry_time", "exit_time",
    "entry_price", "stop_price", "target_price", "exit_price",
    "qty", "pnl", "r_multiple", "result",
    "regime", "vix_beta", "regime_size", "vol_mult",
    "atr", "vwap", "orb_high", "reason", "notes",
]

# ─────── load trades ───────
def load_trades():
    fp = REPO / "trades.csv"
    if not fp.exists():
        return []
    rows = []
    with open(fp) as f:
        rdr = csv.reader(f)
        next(rdr, None)  # skip stale header
        for r in rdr:
            if not r or not r[0]:
                continue
            d = {k: (r[i] if i < len(r) else "") for i, k in enumerate(TRADE_FIELDS)}
            rows.append(d)
    return rows

# ─────── load performance (deduped, last row per date) ───────
def load_performance():
    fp = REPO / "performance.csv"
    if not fp.exists():
        return []
    by_date = OrderedDict()
    with open(fp) as f:
        for r in csv.DictReader(f):
            if r.get("date"):
                by_date[r["date"]] = r
    return list(by_date.values())

# ─────── live equity from Alpaca ───────
def live_equity_and_positions():
    try:
        from alpaca.trading.client import TradingClient
        client = TradingClient(
            api_key=config.ALPACA_API_KEY,
            secret_key=config.ALPACA_SECRET_KEY,
            paper=True,
        )
        acct = client.get_account()
        positions = client.get_all_positions()
        return float(acct.equity), float(acct.last_equity), positions
    except Exception as e:
        print(f"  ! live equity fetch failed: {e}", file=sys.stderr)
        return None, None, []

# ─────── current regime ───────
def upcoming_events(days_ahead: int = 14):
    """
    Return tier-1 + tier-2 USD events from now through `days_ahead` days.

    Sources merged:
      1. FF feed (covers current week, has times + forecasts)
      2. Hardcoded `_HIGH_IMPACT_DATES` from calendar_filter (covers all future
         tier-1 dates — fills the gap when FF rolls over)
    """
    try:
        from calendar_feed import usd_watchlist_events, _is_tier_1
        from zoneinfo import ZoneInfo
        ET = ZoneInfo("America/New_York")
        now = datetime.now(ET)
        cutoff = now.timestamp() + days_ahead * 86400
        seen_dates = set()
        out = []

        # Primary: FF feed (this week's events with times + forecasts)
        for ev in usd_watchlist_events():
            ts = ev.get("date") or ""
            try:
                dt_et = datetime.fromisoformat(ts.replace("Z", "+00:00")).astimezone(ET)
            except Exception:
                continue
            if dt_et < now or dt_et.timestamp() > cutoff:
                continue
            tier1 = _is_tier_1(ev.get("title") or "")
            out.append({
                "stamp": dt_et.strftime("%a %m-%d %H:%M ET"),
                "title": ev.get("title"),
                "impact": ev.get("impact"),
                "forecast": ev.get("forecast") or "—",
                "previous": ev.get("previous") or "—",
                "tier1": tier1,
            })
            seen_dates.add(dt_et.date().isoformat())

        # Backfill: hardcoded tier-1 dates beyond FF's reach
        from calendar_filter import _HIGH_IMPACT_DATES, event_name
        from datetime import date, timedelta
        today = now.date()
        for offset in range(1, days_ahead + 1):
            d = today + timedelta(days=offset)
            ds = d.isoformat()
            if ds in _HIGH_IMPACT_DATES and ds not in seen_dates:
                tag = event_name(d) or "Event"
                out.append({
                    "stamp": d.strftime("%a %m-%d (TBD)"),
                    "title": tag,
                    "impact": "High",
                    "forecast": "—",
                    "previous": "—",
                    "tier1": True,
                })
                seen_dates.add(ds)

        # Sort chronologically (FF entries already are; hardcoded sorts by date)
        out.sort(key=lambda e: e["stamp"])
        return out
    except Exception as e:
        print(f"  ! events fetch failed: {e}", file=sys.stderr)
        return []


def todays_events_status():
    """Return (today_events_list, blocking_today_bool, block_titles_list)."""
    try:
        from calendar_feed import events_for_date, usd_blocking_events
        from zoneinfo import ZoneInfo
        ET = ZoneInfo("America/New_York")
        today_et = datetime.now(ET).date()
        today_evs = events_for_date(today_et)
        blocks = []
        for ev in usd_blocking_events():
            ts = ev.get("date") or ""
            try:
                d = datetime.fromisoformat(ts.replace("Z","+00:00")).astimezone(ET).date()
                if d == today_et:
                    blocks.append(ev.get("title"))
            except Exception:
                pass
        return today_evs, len(blocks) > 0, blocks
    except Exception:
        return [], False, []


def current_regime():
    """Parse latest 'Regime <X> | score=<...>' line from today's bot log."""
    import glob, re
    today = date.today().strftime("%Y%m%d")
    candidates = sorted(glob.glob(f"/tmp/bot_output_*.log"), reverse=True)
    pat = re.compile(r"Regime (\w+)\s*\|\s*score=([\d.]+)\s*\|\s*VIX=([\d.]+)\s+VVIX=([\d.]+)")
    for path in candidates:
        try:
            with open(path) as f:
                for line in reversed(f.readlines()):
                    m = pat.search(line)
                    if m:
                        return m.group(1), float(m.group(2)), {
                            "vix": float(m.group(3)),
                            "vvix": float(m.group(4)),
                        }
        except Exception:
            continue
    return "—", 0, {}

# ─────── build dashboard ───────
def build():
    trades = load_trades()
    perf = load_performance()
    equity, prev_eq, positions = live_equity_and_positions()
    regime, regime_score, vol_snap = current_regime()
    today_events, blocking_today, block_titles = todays_events_status()
    upcoming = upcoming_events(14)

    today_str = date.today().isoformat()
    today_trades = [t for t in trades if t["date"] == today_str]
    yest_perf = perf[-1] if perf else {}
    today_perf = next((p for p in perf if p["date"] == today_str), None)

    # Today P&L (prefer perf row, fallback to live equity diff)
    if today_perf:
        today_pnl = float(today_perf.get("gross_pnl") or 0)
    elif equity is not None and prev_eq is not None:
        today_pnl = equity - prev_eq
    else:
        today_pnl = 0.0

    # Today wins/losses
    today_wins = sum(1 for t in today_trades if (t.get("result") or "").upper() == "WIN")
    today_losses = sum(1 for t in today_trades if (t.get("result") or "").upper() == "LOSS")
    today_total = max(1, today_wins + today_losses)
    today_wr = (today_wins / today_total * 100) if (today_wins + today_losses) else 0

    # Avg win / avg loss across all completed trades
    pnls_all = [float(t["pnl"]) for t in trades if t.get("pnl") and t.get("pnl") not in ("0", "0.0", "")]
    wins_all = [p for p in pnls_all if p > 0]
    losses_all = [p for p in pnls_all if p < 0]
    avg_win = sum(wins_all) / len(wins_all) if wins_all else 0
    avg_loss = sum(losses_all) / len(losses_all) if losses_all else 0
    pf = (sum(wins_all) / abs(sum(losses_all))) if losses_all else 0
    overall_wr = (len(wins_all) / (len(wins_all) + len(losses_all)) * 100) if (wins_all or losses_all) else 0

    kill_switch_days = sum(1 for p in perf if float(p.get("daily_return_pct") or 0) <= -3.0)

    equity_label = f"${equity:,.2f}" if equity is not None else "n/a"
    today_pnl_class = "green" if today_pnl > 0 else ("red" if today_pnl < 0 else "yellow")
    today_pnl_str = f"{'+' if today_pnl >= 0 else ''}${today_pnl:,.2f}"

    # Equity curve from perf (deduped)
    eq_dates = [p["date"] for p in perf if p.get("equity")]
    eq_values = [float(p["equity"]) for p in perf if p.get("equity")]

    # Daily P&L bars
    pnl_dates = [p["date"] for p in perf if p.get("gross_pnl") not in (None, "")]
    pnl_values = [float(p.get("gross_pnl") or 0) for p in perf if p.get("gross_pnl") not in (None, "")]
    pnl_colors = ["rgba(52,211,153,0.8)" if v >= 0 else "rgba(248,113,113,0.8)" for v in pnl_values]

    # Regime breakdown
    regime_counts: dict = {}
    for p in perf:
        r = (p.get("regime") or "").split("_")[0] or "?"
        regime_counts[r] = regime_counts.get(r, 0) + 1
    regime_labels = list(regime_counts.keys())
    regime_data = list(regime_counts.values())

    # Recent 20 trades
    recent = list(reversed(trades))[:20]
    rows_html = []
    for t in recent:
        pnl = float(t.get("pnl") or 0)
        result = (t.get("result") or "").upper() or ("OPEN" if t.get("exit_price") in ("", None) else "—")
        cls = "win" if pnl > 0 else ("loss" if pnl < 0 else "")
        pnl_str = f"{'+' if pnl >= 0 else ''}${pnl:,.2f}" if pnl else "—"
        rows_html.append(f"""  <tr>
    <td>{t.get('date','')}</td>
    <td>{t.get('entry_time','')}</td>
    <td><b>{t.get('symbol','')}</b></td>
    <td>${float(t.get('entry_price') or 0):.2f}</td>
    <td>{('$'+format(float(t.get('exit_price') or 0),'.2f')) if t.get('exit_price') else '—'}</td>
    <td>{t.get('qty','')}</td>
    <td>{(t.get('regime') or '').split('_')[0]}</td>
    <td class="{cls}">{result}</td>
    <td class="{cls}">{pnl_str}</td>
  </tr>""")

    # Go-live checklist
    wr_ok = overall_wr >= 52
    pf_ok = pf >= 1.10
    ks_ok = kill_switch_days == 0
    go_live = wr_ok and pf_ok and ks_ok

    def badge(passed):
        return f'<span class="badge {"pass" if passed else "fail"}">{"✓" if passed else "✗"}</span>'

    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8"/>
<meta name="viewport" content="width=device-width, initial-scale=1.0"/>
<title>Trading Bot Dashboard</title>
<script src="https://cdn.jsdelivr.net/npm/chart.js@4.4.0/dist/chart.umd.min.js"></script>
<style>
  * {{ box-sizing: border-box; margin: 0; padding: 0; }}
  body {{ background: #0f1117; color: #e2e8f0; font-family: 'SF Mono', 'Fira Code', monospace; padding: 24px; }}
  h1 {{ font-size: 1.4rem; font-weight: 700; color: #f8fafc; margin-bottom: 4px; }}
  .subtitle {{ color: #64748b; font-size: 0.75rem; margin-bottom: 24px; }}
  .grid {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(160px, 1fr)); gap: 12px; margin-bottom: 24px; }}
  .card {{ background: #1e2330; border-radius: 10px; padding: 16px; border: 1px solid #2d3448; }}
  .card .label {{ font-size: 0.65rem; color: #64748b; text-transform: uppercase; letter-spacing: .08em; margin-bottom: 6px; }}
  .card .value {{ font-size: 1.5rem; font-weight: 700; color: #f8fafc; }}
  .card .value.green {{ color: #34d399; }}
  .card .value.red {{ color: #f87171; }}
  .card .value.yellow {{ color: #fbbf24; }}
  .section {{ background: #1e2330; border-radius: 10px; padding: 20px; border: 1px solid #2d3448; margin-bottom: 20px; }}
  .section h2 {{ font-size: 0.75rem; text-transform: uppercase; letter-spacing: .1em; color: #64748b; margin-bottom: 16px; }}
  .checklist {{ list-style: none; }}
  .checklist li {{ display: flex; align-items: center; gap: 10px; padding: 8px 0; border-bottom: 1px solid #2d3448; font-size: 0.85rem; }}
  .checklist li:last-child {{ border-bottom: none; }}
  .badge {{ display: inline-block; padding: 2px 8px; border-radius: 4px; font-size: 0.7rem; font-weight: 600; }}
  .badge.pass {{ background: rgba(52,211,153,0.15); color: #34d399; }}
  .badge.fail {{ background: rgba(248,113,113,0.15); color: #f87171; }}
  .go-live {{ text-align: center; padding: 16px; border-radius: 8px; font-weight: 700; font-size: 1rem; margin-top: 12px; }}
  .go-live.yes {{ background: rgba(52,211,153,0.1); color: #34d399; border: 1px solid rgba(52,211,153,0.3); }}
  .go-live.no {{ background: rgba(251,191,36,0.1); color: #fbbf24; border: 1px solid rgba(251,191,36,0.3); }}
  table {{ width: 100%; border-collapse: collapse; font-size: 0.75rem; }}
  th {{ text-align: left; color: #64748b; font-weight: 600; padding: 6px 8px; border-bottom: 1px solid #2d3748; }}
  td {{ padding: 6px 8px; border-bottom: 1px solid #1a2035; }}
  tr:last-child td {{ border-bottom: none; }}
  .win {{ color: #34d399; }} .loss {{ color: #f87171; }}
  .chart-wrap {{ position: relative; height: 220px; }}
  .two-col {{ display: grid; grid-template-columns: 1fr 1fr; gap: 16px; }}
  @media (max-width: 640px) {{ .two-col {{ grid-template-columns: 1fr; }} }}
</style>
</head>
<body>

<h1>VIX/VVIX Regime Alpha Bot</h1>
<div class="subtitle">Paper Trading Dashboard &nbsp;·&nbsp; Updated {datetime.now().strftime('%Y-%m-%d %H:%M ET')} &nbsp;·&nbsp; Equity start: ${config.INITIAL_EQUITY:,.0f} &nbsp;·&nbsp; Universe: {len(config.MOMENTUM_UNIVERSE)} small-caps</div>

<div class="grid">
  <div class="card"><div class="label">Today P&amp;L</div><div class="value {today_pnl_class}">{today_pnl_str}</div></div>
  <div class="card"><div class="label">Today Win Rate</div><div class="value">{today_wr:.0f}%</div></div>
  <div class="card"><div class="label">Today Trades</div><div class="value">{len(today_trades)} / {config.MAX_TRADES_PER_DAY}</div></div>
  <div class="card"><div class="label">Current Equity</div><div class="value">{equity_label}</div></div>
  <div class="card"><div class="label">Avg Win</div><div class="value green">${avg_win:.2f}</div></div>
  <div class="card"><div class="label">Avg Loss</div><div class="value red">${avg_loss:.2f}</div></div>
  <div class="card"><div class="label">Open Positions</div><div class="value">{len(positions)} / {config.MAX_OPEN_POSITIONS}</div></div>
  <div class="card"><div class="label">Regime Now</div><div class="value" style="font-size:1rem;color:#818cf8;">{regime}</div></div>
</div>

<div class="two-col" style="margin-bottom:20px;">
  <div class="section"><h2>Equity Curve</h2><div class="chart-wrap"><canvas id="equityChart"></canvas></div></div>
  <div class="section"><h2>Daily P&amp;L</h2><div class="chart-wrap"><canvas id="dailyChart"></canvas></div></div>
</div>

<div class="two-col" style="margin-bottom:20px;">
  <div class="section">
    <h2>Go-Live Checklist</h2>
    <ul class="checklist">
      <li>{badge(wr_ok)}Win rate ≥ 52% &nbsp;<span style="color:#94a3b8">{overall_wr:.1f}%</span></li>
      <li>{badge(pf_ok)}Profit factor ≥ 1.10 &nbsp;<span style="color:#94a3b8">{pf:.2f}</span></li>
      <li>{badge(ks_ok)}Zero kill-switch days &nbsp;<span style="color:#94a3b8">{kill_switch_days}</span></li>
    </ul>
    <div class="go-live {'yes' if go_live else 'no'}">
      {'🚀 GO-LIVE CRITERIA MET' if go_live else '⏳ VALIDATION PHASE'}
    </div>
  </div>
  <div class="section"><h2>Regime Breakdown</h2><div class="chart-wrap"><canvas id="regimeChart"></canvas></div></div>
</div>

<div class="two-col" style="margin-bottom:20px;">
  <div class="section">
    <h2>Today's Macro Events</h2>
    {f'<div class="go-live no" style="margin-bottom:12px;">⚠ ENTRIES BLOCKED: {", ".join(block_titles)}</div>' if blocking_today else ''}
    {('<table><thead><tr><th>Time</th><th>Impact</th><th>Event</th><th>Fcst</th><th>Prev</th></tr></thead><tbody>' +
      ''.join(f'<tr><td>{e.get("et_time","")}</td><td><span class="badge {"fail" if e.get("impact")=="High" else "pass" if e.get("impact")=="Medium" else ""}">{e.get("impact")}</span></td><td>{e.get("title","")}</td><td>{e.get("forecast") or "—"}</td><td>{e.get("previous") or "—"}</td></tr>' for e in today_events) +
      '</tbody></table>') if today_events else '<div style="color:#64748b;font-size:0.85rem;padding:8px 0;">No tier-1/tier-2 USD events today</div>'}
  </div>
  <div class="section">
    <h2>Upcoming Events (next 2 weeks)</h2>
    {('<table><thead><tr><th>When</th><th>Imp.</th><th>Event</th></tr></thead><tbody>' +
      ''.join(f'<tr><td>{e["stamp"]}</td><td>{("⛔" if e["tier1"] else "·")}</td><td><b style="color:{"#f87171" if e["tier1"] else "#e2e8f0"};">{e["title"]}</b></td></tr>' for e in upcoming) +
      '</tbody></table>') if upcoming else '<div style="color:#64748b;font-size:0.85rem;padding:8px 0;">Calendar feed unavailable</div>'}
    <div style="color:#64748b;font-size:0.65rem;margin-top:8px;">⛔ = bot blocks ORB entries on this day (FOMC/CPI/NFP). Source: ForexFactory.</div>
  </div>
</div>

<div class="section">
  <h2>Recent Trades (last {len(recent)})</h2>
  <table>
    <thead><tr><th>Date</th><th>Time</th><th>Symbol</th><th>Entry</th><th>Exit</th><th>Qty</th><th>Regime</th><th>Result</th><th>P&amp;L</th></tr></thead>
    <tbody>
{chr(10).join(rows_html) if rows_html else '  <tr><td colspan="9" style="text-align:center;color:#64748b;padding:20px;">No trades yet</td></tr>'}
    </tbody>
  </table>
</div>

<script>
const chartDefaults = {{
  color: '#94a3b8',
  plugins: {{ legend: {{ labels: {{ color: '#94a3b8', font: {{ family: 'SF Mono, monospace', size: 11 }} }} }} }},
  scales: {{
    x: {{ ticks: {{ color: '#64748b', font: {{ size: 10 }} }}, grid: {{ color: '#1e2330' }} }},
    y: {{ ticks: {{ color: '#64748b', font: {{ size: 10 }} }}, grid: {{ color: '#2d3748' }} }}
  }}
}};

new Chart(document.getElementById('equityChart'), {{
  type: 'line',
  data: {{
    labels: {eq_dates!r},
    datasets: [{{
      label: 'Equity', data: {eq_values!r},
      borderColor: '#34d399', backgroundColor: 'rgba(52,211,153,0.08)',
      fill: true, tension: 0.3, pointRadius: 2,
    }}]
  }},
  options: {{ ...chartDefaults, responsive: true, maintainAspectRatio: false }}
}});

new Chart(document.getElementById('dailyChart'), {{
  type: 'bar',
  data: {{
    labels: {pnl_dates!r},
    datasets: [{{ label: 'Daily P&L', data: {pnl_values!r}, backgroundColor: {pnl_colors!r} }}]
  }},
  options: {{ ...chartDefaults, responsive: true, maintainAspectRatio: false }}
}});

new Chart(document.getElementById('regimeChart'), {{
  type: 'doughnut',
  data: {{
    labels: {regime_labels!r},
    datasets: [{{
      data: {regime_data!r},
      backgroundColor: ['rgba(99,102,241,0.8)','rgba(251,191,36,0.8)','rgba(248,113,113,0.8)','rgba(148,163,184,0.6)'],
      borderColor: '#0f1117', borderWidth: 2,
    }}]
  }},
  options: {{ responsive: true, maintainAspectRatio: false, plugins: {{ legend: {{ position: 'right', labels: {{ color: '#94a3b8', font: {{ size: 11 }} }} }} }} }}
}});
</script>
</body>
</html>
"""

    out = REPO / "dashboard.html"
    out.write_text(html)
    print(f"  ✓ Wrote {out}")
    print(f"  trades: {len(trades)}  perf rows: {len(perf)}  open positions: {len(positions)}  equity: {equity_label}")
    return out

if __name__ == "__main__":
    build()
