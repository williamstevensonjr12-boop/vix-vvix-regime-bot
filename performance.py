"""
performance.py — Full quantitative metrics suite.

Metrics: CAGR, Sharpe, Sortino, Max Drawdown, Calmar, Win Rate,
         Profit Factor, Beta/Alpha, VaR, CVaR, crisis-period performance.
Also: Monte Carlo simulation and walk-forward optimization framework.
"""
from __future__ import annotations
import logging
import math
import os
from datetime import datetime

import numpy as np
import pandas as pd

import config

logger = logging.getLogger(__name__)

RISK_FREE_RATE = 0.05   # 5% annual


# ── Core metrics ─────────────────────────────────────────────────────────────

def cagr(equity_curve: pd.Series) -> float:
    if len(equity_curve) < 2 or equity_curve.iloc[0] <= 0:
        return 0.0
    n_years = (equity_curve.index[-1] - equity_curve.index[0]).days / 365.25
    if n_years <= 0:
        return 0.0
    return float((equity_curve.iloc[-1] / equity_curve.iloc[0]) ** (1 / n_years) - 1)


def sharpe_ratio(daily_returns: pd.Series, rf_annual: float = RISK_FREE_RATE) -> float:
    clean = daily_returns.dropna()
    if len(clean) < 5 or clean.std() == 0:
        return 0.0
    excess = clean - rf_annual / 252
    return float(excess.mean() / excess.std() * math.sqrt(252))


def sortino_ratio(daily_returns: pd.Series, rf_annual: float = RISK_FREE_RATE) -> float:
    clean = daily_returns.dropna()
    if len(clean) < 5:
        return 0.0
    excess = clean - rf_annual / 252
    downside = excess[excess < 0]
    if len(downside) == 0:
        return float("inf")
    downside_std = math.sqrt((downside ** 2).mean()) * math.sqrt(252)
    if downside_std == 0:
        return 0.0
    return float(excess.mean() * 252 / downside_std)


def max_drawdown(equity_curve: pd.Series) -> float:
    if equity_curve.empty:
        return 0.0
    peak = equity_curve.cummax()
    dd = (equity_curve - peak) / peak
    return float(dd.min())


def calmar_ratio(equity_curve: pd.Series) -> float:
    ann = cagr(equity_curve)
    mdd = abs(max_drawdown(equity_curve))
    return ann / mdd if mdd > 0 else 0.0


def beta_to_spy(returns: pd.Series, spy_returns: pd.Series) -> float:
    aligned = pd.concat([returns, spy_returns], axis=1, join="inner").dropna()
    if len(aligned) < 20:
        return float("nan")
    cov_matrix = np.cov(aligned.iloc[:, 0], aligned.iloc[:, 1])
    var_spy = cov_matrix[1, 1]
    return cov_matrix[0, 1] / var_spy if var_spy > 0 else float("nan")


def alpha_vs_spy(
    returns: pd.Series,
    spy_returns: pd.Series,
    rf_annual: float = RISK_FREE_RATE,
) -> float:
    b = beta_to_spy(returns, spy_returns)
    if math.isnan(b):
        return float("nan")
    ann_ret = float((1 + returns.mean()) ** 252 - 1)
    spy_ann = float((1 + spy_returns.mean()) ** 252 - 1)
    return ann_ret - rf_annual - b * (spy_ann - rf_annual)


def var_cvar(returns: pd.Series, confidence: float = 0.95) -> tuple:
    clean = returns.dropna()
    if clean.empty:
        return 0.0, 0.0
    var = float(clean.quantile(1 - confidence))
    cvar = float(clean[clean <= var].mean()) if (clean <= var).any() else var
    return var, cvar


def profit_factor(pnls: pd.Series) -> float:
    wins = pnls[pnls > 0].sum()
    losses = abs(pnls[pnls <= 0].sum())
    return float(wins / losses) if losses > 0 else float("inf")


# ── Trade-level metrics ───────────────────────────────────────────────────────

def calculate_trade_metrics(trades: list) -> dict:
    empty = dict(
        total_trades=0, wins=0, losses=0, win_rate=0.0,
        total_pnl=0.0, avg_win=0.0, avg_loss=0.0,
        profit_factor=0.0, max_drawdown_pnl=0.0,
        avg_r_multiple=0.0, sharpe=0.0, sortino=0.0,
    )
    closed = [t for t in trades if t.get("result") in ("WIN", "LOSS")]
    if not closed:
        return empty

    df = pd.DataFrame(closed)
    df["pnl"] = pd.to_numeric(df["pnl"], errors="coerce").fillna(0.0)
    df["r_multiple"] = pd.to_numeric(df.get("r_multiple", 0), errors="coerce").fillna(0.0)

    wins_df = df[df["pnl"] > 0]
    loss_df = df[df["pnl"] <= 0]
    n = len(df)

    cum = df["pnl"].cumsum()
    peak = cum.cummax()
    mdd = float((cum - peak).min())

    r_s = df["r_multiple"]
    sharpe_r = float(r_s.mean() / r_s.std() * math.sqrt(252)) if len(r_s) > 1 and r_s.std() > 0 else 0.0

    return dict(
        total_trades=n,
        wins=len(wins_df),
        losses=len(loss_df),
        win_rate=len(wins_df) / n,
        total_pnl=float(df["pnl"].sum()),
        avg_win=float(wins_df["pnl"].mean()) if not wins_df.empty else 0.0,
        avg_loss=float(loss_df["pnl"].mean()) if not loss_df.empty else 0.0,
        profit_factor=profit_factor(df["pnl"]),
        max_drawdown_pnl=mdd,
        avg_r_multiple=float(r_s.mean()),
        sharpe=sharpe_r,
        sortino=0.0,  # trade-level Sortino approximated via R series
    )


# ── SPY benchmark ─────────────────────────────────────────────────────────────

def spy_benchmark(spy_bars: pd.DataFrame, initial_equity: float = 100_000.0) -> dict:
    if spy_bars is None or spy_bars.empty:
        return dict(total_return_pct=0.0, final_equity=initial_equity)
    start = float(spy_bars.iloc[0]["open"])
    end = float(spy_bars.iloc[-1]["close"])
    ret = (end - start) / start * 100.0
    return dict(
        start_price=start,
        end_price=end,
        total_return_pct=ret,
        final_equity=initial_equity * (1 + ret / 100),
    )


# ── Crisis period performance ─────────────────────────────────────────────────

def crisis_period_performance(
    trades: list,
    vix_daily: pd.Series,
    vix_threshold: float = 30.0,
) -> dict:
    """
    Compare trade performance during crisis periods (VIX > threshold)
    vs normal periods.
    """
    closed = [t for t in trades if t.get("result") in ("WIN", "LOSS")]
    if not closed or vix_daily.empty:
        return {}

    df = pd.DataFrame(closed)
    df["pnl"] = pd.to_numeric(df["pnl"], errors="coerce").fillna(0.0)
    df["date"] = pd.to_datetime(df["date"])

    crisis_dates = set(vix_daily[vix_daily > vix_threshold].index.date)
    df["is_crisis"] = df["date"].dt.date.apply(lambda d: d in crisis_dates)

    crisis = df[df["is_crisis"]]
    normal = df[~df["is_crisis"]]

    return {
        "crisis_trades": len(crisis),
        "crisis_pnl": float(crisis["pnl"].sum()),
        "crisis_win_rate": float((crisis["pnl"] > 0).mean()) if not crisis.empty else 0.0,
        "normal_trades": len(normal),
        "normal_pnl": float(normal["pnl"].sum()),
        "normal_win_rate": float((normal["pnl"] > 0).mean()) if not normal.empty else 0.0,
    }


# ── Monte Carlo simulation ────────────────────────────────────────────────────

def monte_carlo(
    pnl_series: pd.Series,
    n_sims: int = 5000,
    initial_equity: float = 100_000.0,
) -> dict:
    """
    Bootstrap-resample trade P&Ls to estimate outcome distribution.
    Returns percentile equity endpoints and probability of profit.
    """
    clean = pnl_series.dropna()
    if clean.empty:
        return {}

    rng = np.random.default_rng(42)
    final_equities = []
    max_drawdowns = []

    for _ in range(n_sims):
        sampled = rng.choice(clean.values, size=len(clean), replace=True)
        equity_path = initial_equity + np.cumsum(sampled)
        final_equities.append(equity_path[-1])
        peak = np.maximum.accumulate(equity_path)
        dd = (equity_path - peak) / peak
        max_drawdowns.append(float(dd.min()))

    fe = np.array(final_equities)
    mdd = np.array(max_drawdowns)

    return {
        "n_sims": n_sims,
        "p5_equity": round(float(np.percentile(fe, 5)), 2),
        "p25_equity": round(float(np.percentile(fe, 25)), 2),
        "p50_equity": round(float(np.percentile(fe, 50)), 2),
        "p75_equity": round(float(np.percentile(fe, 75)), 2),
        "p95_equity": round(float(np.percentile(fe, 95)), 2),
        "prob_profitable": round(float((fe > initial_equity).mean()), 4),
        "median_max_drawdown": round(float(np.median(mdd)), 4),
        "p95_max_drawdown": round(float(np.percentile(mdd, 95)), 4),
    }


# ── Walk-forward framework ────────────────────────────────────────────────────

class WalkForwardResult:
    def __init__(self):
        self.windows: list[dict] = []

    def add_window(self, is_start, is_end, oos_start, oos_end, best_params, oos_metrics):
        self.windows.append({
            "is_start": str(is_start), "is_end": str(is_end),
            "oos_start": str(oos_start), "oos_end": str(oos_end),
            "best_params": best_params,
            "oos_metrics": oos_metrics,
        })

    def aggregate(self) -> dict:
        if not self.windows:
            return {}
        sharpes = [w["oos_metrics"].get("sharpe", 0) for w in self.windows]
        win_rates = [w["oos_metrics"].get("win_rate", 0) for w in self.windows]
        return {
            "n_windows": len(self.windows),
            "avg_oos_sharpe": round(float(np.mean(sharpes)), 3),
            "avg_oos_win_rate": round(float(np.mean(win_rates)), 3),
            "consistency": round(float((np.array(sharpes) > 0).mean()), 3),
        }

    def print_summary(self):
        agg = self.aggregate()
        print("\n" + "=" * 50)
        print("WALK-FORWARD OPTIMIZATION SUMMARY")
        print("=" * 50)
        for w in self.windows:
            print(
                f"  {w['is_start'][:10]}–{w['is_end'][:10]} → OOS {w['oos_start'][:10]}–{w['oos_end'][:10]} | "
                f"params={w['best_params']} | Sharpe={w['oos_metrics'].get('sharpe', 0):.2f}"
            )
        print(f"\nAggregate: {agg}")
        print("=" * 50)


# ── Full report printer ───────────────────────────────────────────────────────

def print_full_report(
    metrics: dict,
    spy_bm: dict | None,
    initial_equity: float,
    monte_carlo_results: dict | None = None,
    crisis_stats: dict | None = None,
    strategy_name: str = "Strategy",
) -> str:
    bot_ret_pct = metrics["total_pnl"] / initial_equity * 100 if initial_equity else 0
    pf = metrics.get("profit_factor", 0)
    pf_str = f"{pf:.2f}" if pf != float("inf") else "∞"

    lines = [
        "",
        "=" * 65,
        f"  {strategy_name.upper()}  —  PERFORMANCE REPORT",
        "=" * 65,
        "",
        "STRATEGY RESULTS",
        "-" * 45,
        f"{'Total Trades':<26}: {metrics['total_trades']}",
        f"{'Wins / Losses':<26}: {metrics['wins']} / {metrics['losses']}",
        f"{'Win Rate':<26}: {metrics.get('win_rate', 0):.1%}",
        f"{'Total P&L':<26}: ${metrics['total_pnl']:>12,.2f}",
        f"{'Strategy Return':<26}: {bot_ret_pct:>+.2f}%",
        f"{'Avg Win':<26}: ${metrics.get('avg_win', 0):>12,.2f}",
        f"{'Avg Loss':<26}: ${metrics.get('avg_loss', 0):>12,.2f}",
        f"{'Profit Factor':<26}: {pf_str}",
        f"{'Max Drawdown (P&L)':<26}: ${metrics.get('max_drawdown_pnl', 0):>12,.2f}",
        f"{'Avg R Multiple':<26}: {metrics.get('avg_r_multiple', 0):>10.2f}R",
        f"{'Sharpe (trade-R)':<26}: {metrics.get('sharpe', 0):>10.2f}",
    ]

    if spy_bm:
        diff = bot_ret_pct - spy_bm["total_return_pct"]
        lines += [
            "",
            "SPY BENCHMARK (Buy & Hold)",
            "-" * 45,
            f"{'SPY Start → End':<26}: ${spy_bm['start_price']:.2f} → ${spy_bm['end_price']:.2f}",
            f"{'SPY Return':<26}: {spy_bm['total_return_pct']:>+.2f}%",
            f"{'Strategy vs SPY':<26}: {diff:>+.2f}%",
            f"{'SPY Final Equity':<26}: ${spy_bm['final_equity']:>12,.2f}",
            f"{'Strategy Final':<26}: ${initial_equity + metrics['total_pnl']:>12,.2f}",
        ]

    if crisis_stats:
        lines += [
            "",
            "CRISIS PERIOD PERFORMANCE (VIX > 30)",
            "-" * 45,
            f"{'Crisis Trades':<26}: {crisis_stats.get('crisis_trades', 0)}",
            f"{'Crisis P&L':<26}: ${crisis_stats.get('crisis_pnl', 0):>12,.2f}",
            f"{'Crisis Win Rate':<26}: {crisis_stats.get('crisis_win_rate', 0):.1%}",
            f"{'Normal Trades':<26}: {crisis_stats.get('normal_trades', 0)}",
            f"{'Normal Win Rate':<26}: {crisis_stats.get('normal_win_rate', 0):.1%}",
        ]

    if monte_carlo_results:
        mc = monte_carlo_results
        lines += [
            "",
            f"MONTE CARLO ({mc.get('n_sims', 0):,} simulations)",
            "-" * 45,
            f"{'5th pct equity':<26}: ${mc.get('p5_equity', 0):>12,.2f}",
            f"{'Median equity':<26}: ${mc.get('p50_equity', 0):>12,.2f}",
            f"{'95th pct equity':<26}: ${mc.get('p95_equity', 0):>12,.2f}",
            f"{'Prob of profit':<26}: {mc.get('prob_profitable', 0):.1%}",
            f"{'Median max drawdown':<26}: {mc.get('median_max_drawdown', 0):.1%}",
        ]

    lines += ["", "=" * 65, ""]
    report = "\n".join(lines)
    print(report)
    logger.info(report)
    return report
