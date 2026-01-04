# -------------------------------------------------------------------------------------------------
#  Reward Calculator for RL Trading Agents
#  Multi-objective reward with "seeing out" bonus for holding winners
# -------------------------------------------------------------------------------------------------

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

import numpy as np

if TYPE_CHECKING:
    from nautilus_trader.model.position import Position


@dataclass
class Trade:
    """Represents a completed trade for reward calculation."""
    instrument_id: str
    entry_price: float
    exit_price: float
    quantity: int
    direction: str  # "LONG" or "SHORT"
    pnl: float
    cost: float
    max_favorable_excursion: float
    max_adverse_excursion: float
    holding_bars: int
    exit_reason: str | None = None


@dataclass
class PortfolioSnapshot:
    """Snapshot of portfolio state for reward calculation."""
    total_value: float
    cash: float
    unrealized_pnl: float
    returns: list[float]
    current_drawdown: float
    peak_value: float


@dataclass
class RewardConfig:
    """Configuration for reward calculation."""
    return_weight: float = 0.4
    sharpe_weight: float = 0.3
    drawdown_weight: float = 0.2
    seeing_out_weight: float = 0.1
    step_reward_scale: float = 0.1
    capture_threshold_full: float = 0.8
    capture_threshold_partial: float = 0.5


class RewardCalculator:
    """
    Multi-objective reward calculation for trading RL.

    Components:
    1. Trade return (risk-adjusted)
    2. Sharpe ratio contribution
    3. Drawdown penalty
    4. "Seeing out" bonus for capturing favorable moves
    """

    def __init__(self, config: RewardConfig | None = None):
        """
        Initialize RewardCalculator.

        Parameters
        ----------
        config : RewardConfig, optional
            Configuration for reward weights and thresholds.
        """
        self.config = config or RewardConfig()

    def update_weights(self, adjustments: dict[str, float]) -> None:
        """
        Update reward weights based on feedback.

        Parameters
        ----------
        adjustments : dict[str, float]
            Dictionary with weight names and new values.
        """
        for key, value in adjustments.items():
            if hasattr(self.config, key):
                setattr(self.config, key, value)

    def calculate_step_reward(
        self,
        current_pnl: float,
        previous_pnl: float,
        portfolio_value: float,
    ) -> float:
        """
        Calculate reward for a single step (before trade closes).

        Parameters
        ----------
        current_pnl : float
            Current unrealized P&L.
        previous_pnl : float
            Previous unrealized P&L.
        portfolio_value : float
            Current portfolio value for normalization.

        Returns
        -------
        float
            Step reward.
        """
        if portfolio_value <= 0:
            return 0.0

        # Reward change in P&L, normalized by portfolio
        pnl_change = current_pnl - previous_pnl
        normalized_change = pnl_change / portfolio_value

        return np.tanh(normalized_change * 100) * self.config.step_reward_scale

    def calculate_trade_reward(
        self,
        trade: Trade,
        portfolio_before: PortfolioSnapshot,
        portfolio_after: PortfolioSnapshot,
    ) -> float:
        """
        Calculate reward when a trade closes.

        Parameters
        ----------
        trade : Trade
            The completed trade.
        portfolio_before : PortfolioSnapshot
            Portfolio state before trade.
        portfolio_after : PortfolioSnapshot
            Portfolio state after trade.

        Returns
        -------
        float
            Total reward for the trade.
        """
        # Component 1: Trade return (scaled and bounded)
        trade_return = trade.pnl / trade.cost if trade.cost > 0 else 0.0
        return_reward = np.tanh(trade_return * 10)

        # Component 2: Sharpe ratio contribution
        sharpe_before = self._rolling_sharpe(portfolio_before.returns)
        sharpe_after = self._rolling_sharpe(portfolio_after.returns)
        sharpe_reward = sharpe_after - sharpe_before

        # Component 3: Drawdown penalty
        drawdown_before = portfolio_before.current_drawdown
        drawdown_after = portfolio_after.current_drawdown
        drawdown_penalty = max(0.0, drawdown_after - drawdown_before)

        # Component 4: "Seeing out" bonus
        seeing_out_bonus = self._calculate_seeing_out_bonus(trade)

        # Combine with weights
        reward = (
            self.config.return_weight * return_reward
            + self.config.sharpe_weight * sharpe_reward
            - self.config.drawdown_weight * drawdown_penalty
            + self.config.seeing_out_weight * seeing_out_bonus
        )

        return float(reward)

    def _calculate_seeing_out_bonus(self, trade: Trade) -> float:
        """
        Calculate bonus for holding winning trades to optimal exit.

        This is the key innovation: rewarding agents for capturing
        more of favorable price moves rather than exiting early.

        Parameters
        ----------
        trade : Trade
            The completed trade.

        Returns
        -------
        float
            Seeing out bonus (0.0 to 1.0).
        """
        if trade.pnl <= 0:
            return 0.0

        # Compare actual P&L to max favorable excursion
        optimal_pnl = trade.max_favorable_excursion
        actual_pnl = trade.pnl

        if optimal_pnl <= 0:
            return 0.0

        # Capture ratio: how much of the available move was captured
        capture_ratio = actual_pnl / optimal_pnl

        # Bonus scales with capture ratio
        if capture_ratio >= self.config.capture_threshold_full:
            return 1.0  # Full bonus for capturing 80%+ of move
        elif capture_ratio >= self.config.capture_threshold_partial:
            return 0.5  # Partial bonus for capturing 50-80%
        else:
            return 0.0

    def _rolling_sharpe(self, returns: list[float], periods: int = 252) -> float:
        """
        Calculate rolling Sharpe ratio from returns.

        Parameters
        ----------
        returns : list[float]
            List of returns.
        periods : int
            Annualization factor. Default is 252 for daily.

        Returns
        -------
        float
            Sharpe ratio.
        """
        if len(returns) < 2:
            return 0.0

        returns_arr = np.array(returns)
        mean_return = np.mean(returns_arr)
        std_return = np.std(returns_arr)

        if std_return == 0:
            return 0.0

        return (mean_return * np.sqrt(periods)) / std_return

    def calculate_early_exit_penalty(
        self,
        trade: Trade,
        expected_holding_bars: int,
    ) -> float:
        """
        Penalty for exiting trades too early.

        Parameters
        ----------
        trade : Trade
            The completed trade.
        expected_holding_bars : int
            Expected minimum holding period.

        Returns
        -------
        float
            Penalty value (negative).
        """
        if trade.pnl <= 0:
            return 0.0  # No penalty for cutting losses

        # Penalty if exited before expected holding period
        if trade.holding_bars < expected_holding_bars:
            # Check if there was more move to capture
            remaining_potential = trade.max_favorable_excursion - trade.pnl
            if remaining_potential > 0:
                penalty_ratio = remaining_potential / trade.max_favorable_excursion
                return -0.5 * penalty_ratio

        return 0.0

    def calculate_overheld_penalty(
        self,
        trade: Trade,
        max_holding_bars: int,
    ) -> float:
        """
        Penalty for holding losing trades too long.

        Parameters
        ----------
        trade : Trade
            The completed trade.
        max_holding_bars : int
            Maximum expected holding period.

        Returns
        -------
        float
            Penalty value (negative).
        """
        if trade.pnl >= 0:
            return 0.0  # No penalty for winners

        # Penalty for holding losers past max period
        if trade.holding_bars > max_holding_bars:
            overhold_ratio = (trade.holding_bars - max_holding_bars) / max_holding_bars
            loss_ratio = abs(trade.pnl) / trade.cost if trade.cost > 0 else 0.0
            return -0.3 * overhold_ratio * loss_ratio

        return 0.0
