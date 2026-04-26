"""
market_neutral.py — Long/short market-neutral crisis alpha sleeve.

When Regime C is active:
  LONG  : top 3 defensive / positive fear-resilience names (XLU, XLP, XLV, GLD)
  SHORT : bottom 3 highest-VIX-beta names (weakest in vol spikes)
          → In PAPER TRADING: shorts are logged but NOT submitted (Alpaca margin rules)
          → In BACKTEST: full long/short simulation with slippage

Portfolio is dollar-neutral: long notional = short notional.
Target: generate positive alpha when SPY sells off.
"""
from __future__ import annotations
import logging
from dataclasses import dataclass, field

import numpy as np
import pandas as pd

from regime import Regime, RegimeState
from vix_factor import VIXBetaRanker
import config

logger = logging.getLogger(__name__)


@dataclass
class NeutralLeg:
    symbol: str
    side: str          # "long" or "short"
    notional: float
    qty: int
    vix_beta: float
    fear_resilience: float


@dataclass
class MarketNeutralPortfolio:
    longs: list[NeutralLeg] = field(default_factory=list)
    shorts: list[NeutralLeg] = field(default_factory=list)
    total_long_notional: float = 0.0
    total_short_notional: float = 0.0
    net_exposure: float = 0.0       # target: ~0
    gross_exposure: float = 0.0
    is_paper_mode: bool = True

    def summary(self) -> str:
        long_syms = [f"{l.symbol}({l.notional:,.0f})" for l in self.longs]
        short_syms = [f"{s.symbol}({s.notional:,.0f})" for s in self.shorts]
        return (
            f"MN Portfolio | net={self.net_exposure:+.0f} gross={self.gross_exposure:,.0f} | "
            f"LONG={long_syms} SHORT={short_syms}"
        )


class MarketNeutralOverlay:
    """
    Builds and manages the market-neutral crisis alpha sleeve.

    In paper trading: submits long legs only (short legs flagged/logged).
    In backtest: full long/short simulation.
    """

    def __init__(self, ranker: VIXBetaRanker, paper_mode: bool = True):
        self.ranker = ranker
        self.paper_mode = paper_mode
        self._active_portfolio: MarketNeutralPortfolio | None = None

    def should_activate(self, regime_state: RegimeState) -> bool:
        return regime_state.regime == Regime.C and regime_state.crisis_alpha_enabled

    def build_portfolio(
        self,
        regime_state: RegimeState,
        account_equity: float,
        current_prices: dict[str, float],
        n_longs: int = 3,
        n_shorts: int = 3,
        exposure_pct: float = 0.15,   # 15% of equity per leg
    ) -> MarketNeutralPortfolio:
        """
        Construct a dollar-neutral long/short book.
        exposure_pct: fraction of equity allocated to each leg.
        """
        leg_notional = account_equity * exposure_pct

        # Long leg: top fear-resilient names
        crisis_longs = self.ranker.get_crisis_longs(n=n_longs)
        crisis_shorts = self.ranker.get_crisis_shorts(n=n_shorts)

        long_legs = []
        for sym in crisis_longs:
            price = current_prices.get(sym, 0)
            if price <= 0:
                continue
            qty = max(1, int(leg_notional / price))
            long_legs.append(NeutralLeg(
                symbol=sym,
                side="long",
                notional=qty * price,
                qty=qty,
                vix_beta=self.ranker.get_beta(sym),
                fear_resilience=self.ranker.get_resilience(sym),
            ))

        short_legs = []
        for sym in crisis_shorts:
            price = current_prices.get(sym, 0)
            if price <= 0:
                continue
            qty = max(1, int(leg_notional / price))
            short_legs.append(NeutralLeg(
                symbol=sym,
                side="short",
                notional=qty * price,
                qty=qty,
                vix_beta=self.ranker.get_beta(sym),
                fear_resilience=self.ranker.get_resilience(sym),
            ))

        total_long = sum(l.notional for l in long_legs)
        total_short = sum(s.notional for s in short_legs)

        portfolio = MarketNeutralPortfolio(
            longs=long_legs,
            shorts=short_legs,
            total_long_notional=total_long,
            total_short_notional=total_short,
            net_exposure=total_long - total_short,
            gross_exposure=total_long + total_short,
            is_paper_mode=self.paper_mode,
        )
        self._active_portfolio = portfolio
        logger.info(portfolio.summary())

        if self.paper_mode and short_legs:
            logger.warning(
                "PAPER MODE: short legs NOT submitted to Alpaca. "
                f"Shorts logged only: {[s.symbol for s in short_legs]}"
            )

        return portfolio

    def simulate_pnl(
        self,
        portfolio: MarketNeutralPortfolio,
        exit_prices: dict[str, float],
    ) -> float:
        """
        Compute P&L for the neutral book at exit prices.
        Used in backtest simulation.
        """
        pnl = 0.0
        for leg in portfolio.longs:
            ep = exit_prices.get(leg.symbol, 0)
            if ep > 0:
                entry_p = leg.notional / leg.qty if leg.qty > 0 else ep
                pnl += (ep - entry_p) * leg.qty

        for leg in portfolio.shorts:
            ep = exit_prices.get(leg.symbol, 0)
            if ep > 0:
                entry_p = leg.notional / leg.qty if leg.qty > 0 else ep
                pnl -= (ep - entry_p) * leg.qty   # short: profit when price falls

        return round(pnl, 2)
