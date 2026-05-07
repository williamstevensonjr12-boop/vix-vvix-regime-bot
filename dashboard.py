"""
dashboard.py — Generates dashboard.html from trades.csv + performance.csv.
Run: python main.py dashboard
Then open dashboard.html in your browser.
"""
from __future__ import annotations
import csv
import json
import os
from collections import defaultdict
from datetime import datetime

import config

DASHBOARD_HTML = "dashboard.html"


def _load_csv(path: str) -> list[dict]:
    if not os.path.exists(path):
        return []
    with open(path, newline="") as f:
        return list(csv.DictReader(f))


def _to_float(v, default: float = 0.0) -> float:
    # csv.DictReader returns "" for empty cells; dict.get's default only fires
    # when the key is missing, so empty strings sneak through and crash float().
    if v is None or v == "":
        return default
    try:
        return float(v)
    except (TypeError, ValueError):
        return default


def build_dashboard():
    trades = _load_csv(config.TRADES_CSV)
    perf   = _load_csv(config.PERFORMANCE_CSV)

    # ── Metrics ───────────────────────────────────────────────────────────
    wins   = [t for t in trades if t.get("result") == "WIN"]
    losses = [t for t in trades if t.get("result") == "LOSS"]
    total  = len(trades)
    win_rate = len(wins) / total if total else 0
    gross_win  = sum(_to_float(t.get("pnl")) for t in wins)
    gross_loss = abs(sum(_to_float(t.get("pnl")) for t in losses))
    profit_factor = gross_win / gross_loss if gross_loss > 0 else 0
    total_pnl = sum(_to_float(t.get("pnl")) for t in trades)
    avg_win  = gross_win  / len(wins)   if wins   else 0
    avg_loss = gross_loss / len(losses) if losses else 0

    # Daily P&L
    daily_pnl: dict[str, float] = defaultdict(float)
    for t in trades:
        daily_pnl[t.get("date", "")] += _to_float(t.get("pnl"))

    # Equity curve from performance.csv
    perf_sorted = sorted(perf, key=lambda p: p.get("date", ""))
    equity_dates  = [p["date"] for p in perf_sorted]
    equity_values = [_to_float(p.get("equity"), config.INITIAL_EQUITY) for p in perf_sorted]

    # Kill switch days
    kill_days = []
    for p in perf_sorted:
        ret = _to_float(p.get("daily_return_pct"))
        if ret <= -config.KILL_SWITCH_LOSS_PCT * 100:
            kill_days.append(p["date"])

    ok_wr = win_rate >= 0.52
    ok_pf = profit_factor >= 1.10
    ok_ks = len(kill_days) == 0
    go_live = ok_wr and ok_pf and ok_ks

    # Recent trades table (last 20)
    recent_trades = sorted(trades, key=lambda t: (t.get("date",""), t.get("time","")))[-20:]

    # Daily bar chart data
    daily_sorted = sorted(daily_pnl.items())
    bar_labels = [d for d, _ in daily_sorted]
    bar_values = [round(v, 2) for _, v in daily_sorted]
    bar_colors = ["rgba(52,211,153,0.8)" if v >= 0 else "rgba(248,113,113,0.8)" for v in bar_values]

    now = datetime.now().strftime("%Y-%m-%d %H:%M")

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
  .go-live.no  {{ background: rgba(251,191,36,0.1); color: #fbbf24; border: 1px solid rgba(251,191,36,0.3); }}
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

<h1>Cameron VWAP-Bounce Bot</h1>
<div class="subtitle">Paper Trading Dashboard &nbsp;·&nbsp; Updated {now} &nbsp;·&nbsp; Equity start: ${config.INITIAL_EQUITY:,.0f}</div>

<!-- KPI Cards -->
<div class="grid">
  <div class="card">
    <div class="label">Total P&amp;L</div>
    <div class="value {'green' if total_pnl >= 0 else 'red'}">${total_pnl:+,.2f}</div>
  </div>
  <div class="card">
    <div class="label">Win Rate</div>
    <div class="value {'green' if ok_wr else 'red'}">{win_rate:.1%}</div>
  </div>
  <div class="card">
    <div class="label">Profit Factor</div>
    <div class="value {'green' if ok_pf else 'red'}">{profit_factor:.2f}</div>
  </div>
  <div class="card">
    <div class="label">Total Trades</div>
    <div class="value">{total}</div>
  </div>
  <div class="card">
    <div class="label">Avg Win</div>
    <div class="value green">${avg_win:,.2f}</div>
  </div>
  <div class="card">
    <div class="label">Avg Loss</div>
    <div class="value red">${avg_loss:,.2f}</div>
  </div>
  <div class="card">
    <div class="label">Kill-Switch Days</div>
    <div class="value {'red' if kill_days else 'green'}">{len(kill_days)}</div>
  </div>
  <div class="card">
    <div class="label">Current Equity</div>
    <div class="value">${(config.INITIAL_EQUITY + total_pnl):,.2f}</div>
  </div>
</div>

<!-- Charts row -->
<div class="two-col" style="margin-bottom:20px;">
  <div class="section">
    <h2>Equity Curve</h2>
    <div class="chart-wrap"><canvas id="equityChart"></canvas></div>
  </div>
  <div class="section">
    <h2>Daily P&amp;L</h2>
    <div class="chart-wrap"><canvas id="dailyChart"></canvas></div>
  </div>
</div>

<!-- Go-live row -->
<div class="section" style="margin-bottom:20px;">
  <h2>Go-Live Checklist</h2>
  <ul class="checklist">
    <li>
      <span class="badge {'pass' if ok_wr else 'fail'}">{'✓' if ok_wr else '✗'}</span>
      Win rate ≥ 52% &nbsp;<span style="color:#94a3b8">{win_rate:.1%}</span>
    </li>
    <li>
      <span class="badge {'pass' if ok_pf else 'fail'}">{'✓' if ok_pf else '✗'}</span>
      Profit factor ≥ 1.10 &nbsp;<span style="color:#94a3b8">{profit_factor:.2f}</span>
    </li>
    <li>
      <span class="badge {'pass' if ok_ks else 'fail'}">{'✓' if ok_ks else '✗'}</span>
      Zero kill-switch days &nbsp;<span style="color:#94a3b8">{len(kill_days)}</span>
    </li>
  </ul>
  <div class="go-live {'yes' if go_live else 'no'}">
    {'🚀 GO-LIVE CRITERIA MET' if go_live else '⏳ Keep paper trading'}
  </div>
</div>

<!-- Recent Trades -->
<div class="section">
  <h2>Recent Trades (last 20)</h2>
  {'<p style="color:#64748b;font-size:0.8rem;">No trades yet — bot is running.</p>' if not recent_trades else ''}
  {'<table><thead><tr><th>Date</th><th>Time</th><th>Symbol</th><th>Side</th><th>Entry</th><th>Stop</th><th>Target</th><th>Qty</th><th>Result</th><th>P&L</th></tr></thead><tbody>' if recent_trades else ''}
  {''.join(f"""<tr>
    <td>{t.get('date','')}</td>
    <td>{t.get('time','')[:5]}</td>
    <td><b>{t.get('symbol','')}</b></td>
    <td>{t.get('side','')}</td>
    <td>${_to_float(t.get('entry_price')):.2f}</td>
    <td>${_to_float(t.get('stop_price')):.2f}</td>
    <td>${_to_float(t.get('target_price')):.2f}</td>
    <td>{t.get('qty','')}</td>
    <td class="{'win' if t.get('result')=='WIN' else 'loss'}">{t.get('result','')}</td>
    <td class="{'win' if _to_float(t.get('pnl'))>=0 else 'loss'}">${_to_float(t.get('pnl')):+.2f}</td>
  </tr>""" for t in reversed(recent_trades)) if recent_trades else ''}
  {'</tbody></table>' if recent_trades else ''}
</div>

<script>
const chartDefaults = {{
  color: '#94a3b8',
  borderColor: '#2d3748',
  plugins: {{ legend: {{ labels: {{ color: '#94a3b8', font: {{ family: 'SF Mono, monospace', size: 11 }} }} }} }},
  scales: {{
    x: {{ ticks: {{ color: '#64748b', font: {{ size: 10 }} }}, grid: {{ color: '#1e2330' }} }},
    y: {{ ticks: {{ color: '#64748b', font: {{ size: 10 }} }}, grid: {{ color: '#2d3748' }} }}
  }}
}};

// Equity curve
new Chart(document.getElementById('equityChart'), {{
  type: 'line',
  data: {{
    labels: {json.dumps(equity_dates)},
    datasets: [{{
      label: 'Equity',
      data: {json.dumps(equity_values)},
      borderColor: '#34d399',
      backgroundColor: 'rgba(52,211,153,0.08)',
      fill: true,
      tension: 0.3,
      pointRadius: 2,
    }}]
  }},
  options: {{ ...chartDefaults, responsive: true, maintainAspectRatio: false }}
}});

// Daily P&L bars
new Chart(document.getElementById('dailyChart'), {{
  type: 'bar',
  data: {{
    labels: {json.dumps(bar_labels)},
    datasets: [{{
      label: 'Daily P&L',
      data: {json.dumps(bar_values)},
      backgroundColor: {json.dumps(bar_colors)},
    }}]
  }},
  options: {{ ...chartDefaults, responsive: true, maintainAspectRatio: false }}
}});
</script>
</body>
</html>"""

    with open(DASHBOARD_HTML, "w") as f:
        f.write(html)

    print(f"Dashboard saved → {os.path.abspath(DASHBOARD_HTML)}")
    import subprocess
    subprocess.Popen(["open", DASHBOARD_HTML])
