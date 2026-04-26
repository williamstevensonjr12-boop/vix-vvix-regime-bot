"""
vix_factor.py — VIX beta rotation factor.

Computes rolling VIX beta, fear resilience score, and vol shock outperformance
for each symbol. Used to rank the universe and filter low-quality setups.

VIX beta > 0 : stock suffers during vol spikes (momentum names in calm markets)
VIX beta < 0 : stock benefits during vol spikes (defensive / crisis alpha names)
Fear Resilience Score = -vix_beta (higher = more resilient in stress)
"""
from __future__ import annotations
import logging

import numpy as np
import pandas as pd

import config

logger = logging.getLogger(__name__)


def calculate_rolling_vix_beta(
    symbol_returns: pd.Series,
    vix_changes: pd.Series,
    window: int = None,
) -> pd.Series:
    """
    Rolling OLS: symbol_return = alpha + beta * delta_vix + epsilon.
    Returns a Series of beta values aligned to symbol_returns.index.
    """
    window = window or config.VIX_BETA_LOOKBACK
    min_obs = config.VIX_BETA_MIN_OBS

    # Align on common dates
    aligned = pd.concat([symbol_returns, vix_changes], axis=1, join="inner").dropna()
    if len(aligned) < min_obs:
        return pd.Series(dtype=float, name=f"{symbol_returns.name}_vix_beta")

    ret = aligned.iloc[:, 0].values
    dvix = aligned.iloc[:, 1].values

    betas = np.full(len(aligned), np.nan)
    for i in range(window - 1, len(aligned)):
        r_w = ret[i - window + 1 : i + 1]
        v_w = dvix[i - window + 1 : i + 1]
        if np.std(v_w) < 1e-8:
            continue
        X = np.column_stack([np.ones(window), v_w])
        try:
            coeffs, _, _, _ = np.linalg.lstsq(X, r_w, rcond=None)
            betas[i] = coeffs[1]
        except Exception:
            pass

    result = pd.Series(betas, index=aligned.index, name=f"{symbol_returns.name}_vix_beta")
    return result


def calculate_fear_resilience_score(vix_beta: float | pd.Series) -> float | pd.Series:
    """Fear resilience = -vix_beta. Higher = more resilient."""
    return -vix_beta


def calculate_vol_shock_outperformance(
    symbol_returns: pd.Series,
    vix_changes: pd.Series,
    spike_threshold: float = 5.0,
) -> float:
    """
    Average symbol return on days when VIX spiked > spike_threshold points.
    Positive = symbol tends to hold up or rally during vol shocks.
    """
    aligned = pd.concat([symbol_returns, vix_changes], axis=1, join="inner").dropna()
    if aligned.empty:
        return 0.0
    aligned.columns = ["ret", "dvix"]
    spike_days = aligned[aligned["dvix"] > spike_threshold]
    if spike_days.empty:
        return 0.0
    return float(spike_days["ret"].mean())


class VIXBetaRanker:
    """
    Computes and caches VIX beta metrics for the full symbol universe.

    For backtesting: call precompute() once to build the full beta history,
    then use rank_at_date() per day — avoids recomputing on every bar.

    For live use: call fit() with the latest data snapshot.
    """

    def __init__(self):
        self._betas: dict[str, float] = {}
        self._resilience: dict[str, float] = {}
        self._shock_perf: dict[str, float] = {}
        # Precomputed history for backtest fast-path
        self._beta_history: pd.DataFrame = pd.DataFrame()
        self._shock_history: dict[str, float] = {}

    def precompute(
        self,
        daily_returns_by_symbol: dict[str, pd.Series],
        vix_daily_series: pd.Series,
    ) -> None:
        """
        Pre-compute the full rolling beta series for all symbols in one pass.
        Call once before the backtest day loop; then use rank_at_date() per day.
        """
        vix_changes = vix_daily_series.diff().dropna()
        series_dict: dict[str, pd.Series] = {}

        for symbol, ret_series in daily_returns_by_symbol.items():
            beta_s = calculate_rolling_vix_beta(ret_series, vix_changes)
            if not beta_s.dropna().empty:
                series_dict[symbol] = beta_s
            self._shock_history[symbol] = calculate_vol_shock_outperformance(
                ret_series, vix_changes
            )

        if series_dict:
            self._beta_history = pd.concat(series_dict, axis=1)
        logger.info(f"VIXBetaRanker precomputed {len(series_dict)} symbols")

    def _set_betas_at(self, as_of_date: pd.Timestamp) -> None:
        """Populate _betas/_resilience from precomputed history at as_of_date."""
        if self._beta_history.empty:
            return
        slice_df = self._beta_history[self._beta_history.index <= as_of_date]
        if slice_df.empty:
            return
        latest = slice_df.ffill().iloc[-1]
        self._betas = {sym: float(latest[sym]) for sym in latest.index if not np.isnan(latest[sym])}
        self._resilience = {s: calculate_fear_resilience_score(b) for s, b in self._betas.items()}
        self._shock_perf = {s: self._shock_history.get(s, 0.0) for s in self._betas}

    def rank_at_date(
        self,
        universe: list[str],
        as_of_date: pd.Timestamp,
        top_fraction: float = None,
        regime_mode: str = "momentum",
    ) -> list[str]:
        """Look up pre-computed betas at as_of_date and return ranked universe."""
        self._set_betas_at(as_of_date)
        return self.rank(universe, top_fraction=top_fraction, regime_mode=regime_mode)

    def fit(
        self,
        daily_returns_by_symbol: dict[str, pd.Series],
        vix_daily_series: pd.Series,
        as_of_date: pd.Timestamp | None = None,
    ) -> None:
        """
        Fit betas for all symbols up to as_of_date (live trading use).
        For backtesting prefer precompute() + rank_at_date().
        """
        if as_of_date is not None:
            vix_s = vix_daily_series[vix_daily_series.index <= as_of_date]
        else:
            vix_s = vix_daily_series

        vix_changes = vix_s.diff().dropna()

        self._betas = {}
        self._resilience = {}
        self._shock_perf = {}

        for symbol, ret_series in daily_returns_by_symbol.items():
            if as_of_date is not None:
                ret_s = ret_series[ret_series.index <= as_of_date]
            else:
                ret_s = ret_series

            beta_series = calculate_rolling_vix_beta(ret_s, vix_changes)
            if beta_series.dropna().empty:
                self._betas[symbol] = 0.0
            else:
                self._betas[symbol] = float(beta_series.dropna().iloc[-1])

            self._resilience[symbol] = calculate_fear_resilience_score(self._betas[symbol])
            self._shock_perf[symbol] = calculate_vol_shock_outperformance(ret_s, vix_changes)

        logger.debug(
            f"VIXBetaRanker fit: {len(self._betas)} symbols | "
            f"avg_beta={np.mean(list(self._betas.values())):.3f}"
        )

    def rank(
        self,
        universe: list[str],
        top_fraction: float = None,
        regime_mode: str = "momentum",
    ) -> list[str]:
        """
        Return universe symbols ranked by suitability for the given regime.

        regime_mode='momentum'  : rank by lowest VIX beta (trades that do well in calm)
        regime_mode='defensive' : rank by highest fear resilience (most crisis-proof)
        """
        top_fraction = top_fraction or config.TOP_SYMBOLS_FRACTION
        available = [s for s in universe if s in self._resilience]

        if not available:
            return universe

        if regime_mode == "defensive":
            ranked = sorted(available, key=lambda s: self._resilience[s], reverse=True)
        else:
            # momentum: prefer names with moderate positive VIX beta (ride the trend)
            ranked = sorted(available, key=lambda s: self._betas[s])

        cutoff = max(1, int(len(ranked) * top_fraction))
        selected = ranked[:cutoff]
        logger.debug(f"VIX beta rank ({regime_mode}) top-{cutoff}: {selected}")
        return selected

    def get_beta(self, symbol: str) -> float:
        return self._betas.get(symbol, 0.0)

    def get_resilience(self, symbol: str) -> float:
        return self._resilience.get(symbol, 0.0)

    def get_crisis_longs(self, n: int = 3) -> list[str]:
        """Top N symbols by fear resilience — use as crisis alpha longs."""
        ranked = sorted(self._resilience, key=self._resilience.get, reverse=True)
        return ranked[:n]

    def get_crisis_shorts(self, n: int = 3) -> list[str]:
        """Bottom N symbols by fear resilience — weakest in vol spikes."""
        ranked = sorted(self._resilience, key=self._resilience.get)
        return ranked[:n]

    def summary_table(self) -> pd.DataFrame:
        rows = []
        for sym in self._betas:
            rows.append({
                "symbol": sym,
                "vix_beta": round(self._betas[sym], 4),
                "fear_resilience": round(self._resilience.get(sym, 0), 4),
                "vol_shock_perf": round(self._shock_perf.get(sym, 0), 6),
            })
        return pd.DataFrame(rows).sort_values("fear_resilience", ascending=False).reset_index(drop=True)
