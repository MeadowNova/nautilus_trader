#!/usr/bin/env python3
"""
Risk Dashboard for Moomoo RL Paper Trading System

This module provides real-time monitoring of trading system health,
risk metrics, and position exposure.

Metrics Tracked:
- Data flow (quotes/sec, bars/min, data latency)
- Order execution (fill time, rejection rate)
- Position metrics (P&L, drawdown, correlation)
- Risk limits (portfolio heat, max drawdown, Kelly criterion)
- Strategy performance (win rate, profit factor, Sharpe ratio)
"""

from __future__ import annotations
from dataclasses import dataclass, field
from datetime import datetime
from collections import deque
from decimal import Decimal
import numpy as np
from typing import Optional

from nautilus_trader.model.currency import Currency
from nautilus_trader.model.identifiers import InstrumentId, Venue
from nautilus_trader.model.objects import Money, Price


@dataclass
class DataFlowMetrics:
    """Monitor market data flow health."""
    quotes_received: int = 0
    ticks_received: int = 0
    bars_published: int = 0
    data_latency_ms: deque = field(default_factory=lambda: deque(maxlen=100))  # Last 100 measurements

    # Targets
    target_quotes_per_sec: int = 3
    target_ticks_per_sec: int = 5
    target_bars_per_min: int = 1
    target_latency_ms: int = 100

    # Alerts
    alert_quotes_per_sec: int = 1
    alert_ticks_per_sec: int = 2
    alert_latency_ms: int = 500

    def __str__(self) -> str:
        avg_latency = np.mean(list(self.data_latency_ms)) if self.data_latency_ms else 0
        status = "OK" if avg_latency < self.target_latency_ms else "WARNING"
        return (
            f"[{status}] Data Flow:\n"
            f"  Quotes: {self.quotes_received} received\n"
            f"  Ticks: {self.ticks_received} received\n"
            f"  Bars: {self.bars_published} published\n"
            f"  Latency: {avg_latency:.1f}ms (target: {self.target_latency_ms}ms)"
        )


@dataclass
class ExecutionMetrics:
    """Monitor order execution health."""
    orders_submitted: int = 0
    orders_filled: int = 0
    orders_rejected: int = 0
    orders_cancelled: int = 0
    fill_times_ms: deque = field(default_factory=lambda: deque(maxlen=100))

    # Targets and alerts
    target_fill_time_ms: int = 2000  # 2 seconds
    alert_fill_time_ms: int = 5000   # 5 seconds
    target_rejection_rate: float = 0.05  # 5%
    alert_rejection_rate: float = 0.10  # 10%

    @property
    def fill_rate(self) -> float:
        """Percentage of submitted orders that were filled."""
        if self.orders_submitted == 0:
            return 0.0
        return self.orders_filled / self.orders_submitted

    @property
    def rejection_rate(self) -> float:
        """Percentage of submitted orders that were rejected."""
        if self.orders_submitted == 0:
            return 0.0
        return self.orders_rejected / self.orders_submitted

    @property
    def avg_fill_time_ms(self) -> float:
        """Average time from submission to fill."""
        if not self.fill_times_ms:
            return 0.0
        return np.mean(list(self.fill_times_ms))

    def __str__(self) -> str:
        status = "OK"
        if self.rejection_rate > self.target_rejection_rate:
            status = "WARNING"
        if self.avg_fill_time_ms > self.alert_fill_time_ms:
            status = "ALERT"

        return (
            f"[{status}] Execution:\n"
            f"  Submitted: {self.orders_submitted}\n"
            f"  Filled: {self.orders_filled}\n"
            f"  Rejected: {self.orders_rejected} ({self.rejection_rate:.1%})\n"
            f"  Avg Fill Time: {self.avg_fill_time_ms:.1f}ms (target: {self.target_fill_time_ms}ms)"
        )


@dataclass
class PositionMetrics:
    """Monitor open positions and exposure."""
    open_positions: int = 0
    total_pnl: Decimal = Decimal(0)
    unrealised_pnl: Decimal = Decimal(0)
    realised_pnl: Decimal = Decimal(0)

    # Per-position tracking
    position_pnls: dict[InstrumentId, Decimal] = field(default_factory=dict)
    position_quantities: dict[InstrumentId, Decimal] = field(default_factory=dict)
    max_position_mfe: dict[InstrumentId, Decimal] = field(default_factory=dict)  # Max Favorable Excursion
    max_position_mae: dict[InstrumentId, Decimal] = field(default_factory=dict)  # Max Adverse Excursion

    # Drawdown tracking
    peak_value: Decimal = Decimal(0)
    max_drawdown: Decimal = Decimal(0)
    current_drawdown: Decimal = Decimal(0)

    # Risk limits
    max_position_size_usd: Decimal = Decimal(10000)  # Max $10K per position
    max_portfolio_heat_pct: float = 0.06  # 6% of portfolio at risk

    def calculate_portfolio_heat(self, total_portfolio_value: Decimal) -> float:
        """Calculate total portfolio heat (capital at risk)."""
        total_at_risk = Decimal(0)

        for instrument_id, pnl in self.position_pnls.items():
            if pnl < 0:  # Losing positions are at risk
                total_at_risk += abs(pnl)

        if total_portfolio_value <= 0:
            return 0.0

        return float(total_at_risk / total_portfolio_value)

    def __str__(self) -> str:
        status = "OK"
        if self.current_drawdown > Decimal(0.05):  # > 5% drawdown
            status = "WARNING"
        if self.current_drawdown > Decimal(0.10):  # > 10% drawdown
            status = "ALERT"

        return (
            f"[{status}] Positions:\n"
            f"  Open: {self.open_positions}\n"
            f"  Total P&L: ${float(self.total_pnl):,.2f}\n"
            f"  Unrealised: ${float(self.unrealised_pnl):,.2f}\n"
            f"  Realised: ${float(self.realised_pnl):,.2f}\n"
            f"  Drawdown: {float(self.current_drawdown):.2%} (max: {float(self.max_drawdown):.2%})"
        )


@dataclass
class StrategyMetrics:
    """Monitor strategy performance metrics."""
    strategy_name: str = ""
    trades_completed: int = 0
    winning_trades: int = 0
    losing_trades: int = 0
    total_pnl: Decimal = Decimal(0)

    # Trade tracking
    trade_pnls: list[Decimal] = field(default_factory=list)
    trade_holding_bars: list[int] = field(default_factory=list)
    trade_captures: list[float] = field(default_factory=list)  # Profit capture ratio

    # Performance metrics
    @property
    def win_rate(self) -> float:
        """Percentage of winning trades."""
        if self.trades_completed == 0:
            return 0.0
        return self.winning_trades / self.trades_completed

    @property
    def profit_factor(self) -> float:
        """Gross profit / Gross loss."""
        gross_profit = sum(pnl for pnl in self.trade_pnls if pnl > 0)
        gross_loss = abs(sum(pnl for pnl in self.trade_pnls if pnl < 0))

        if gross_loss == 0:
            return float('inf') if gross_profit > 0 else 0.0
        return float(gross_profit / gross_loss)

    @property
    def avg_win(self) -> Decimal:
        """Average win size."""
        wins = [pnl for pnl in self.trade_pnls if pnl > 0]
        if not wins:
            return Decimal(0)
        return sum(wins) / len(wins)

    @property
    def avg_loss(self) -> Decimal:
        """Average loss size."""
        losses = [pnl for pnl in self.trade_pnls if pnl < 0]
        if not losses:
            return Decimal(0)
        return sum(losses) / len(losses)

    @property
    def expectancy(self) -> Decimal:
        """(Win% * Avg Win) - (Loss% * Avg Loss)"""
        if self.trades_completed == 0:
            return Decimal(0)

        win_pct = Decimal(self.win_rate)
        loss_pct = Decimal(1) - win_pct

        return (win_pct * self.avg_win) - (loss_pct * abs(self.avg_loss))

    @property
    def sharpe_ratio(self) -> float:
        """Sharpe ratio of returns (assuming 0% risk-free rate)."""
        if len(self.trade_pnls) < 2:
            return 0.0

        returns = [float(pnl) for pnl in self.trade_pnls]
        mean_return = np.mean(returns)
        std_return = np.std(returns)

        if std_return == 0:
            return 0.0

        # Annualize: assume 250 trading days, ~20 trades per day
        return (mean_return * 250 * 20) / (std_return * np.sqrt(250 * 20))

    @property
    def avg_capture_ratio(self) -> float:
        """Average % of max favorable excursion captured."""
        if not self.trade_captures:
            return 0.0
        return np.mean(self.trade_captures)

    @property
    def avg_holding_bars(self) -> float:
        """Average bars held per trade."""
        if not self.trade_holding_bars:
            return 0.0
        return np.mean(self.trade_holding_bars)

    def __str__(self) -> str:
        status = "OK"
        if self.win_rate < 0.40:
            status = "WARNING"
        if self.profit_factor < 1.0:
            status = "ALERT"

        return (
            f"[{status}] {self.strategy_name}:\n"
            f"  Trades: {self.trades_completed} ({self.win_rate:.1%} win rate)\n"
            f"  Total P&L: ${float(self.total_pnl):,.2f}\n"
            f"  Profit Factor: {self.profit_factor:.2f}\n"
            f"  Expectancy: ${float(self.expectancy):.2f} per trade\n"
            f"  Sharpe Ratio: {self.sharpe_ratio:.2f}\n"
            f"  Avg Capture: {self.avg_capture_ratio:.1%}\n"
            f"  Avg Holding: {self.avg_holding_bars:.1f} bars"
        )


@dataclass
class PortfolioRiskMetrics:
    """High-level portfolio risk monitoring."""
    account_value: Decimal = Decimal(0)
    cash: Decimal = Decimal(0)
    position_value: Decimal = Decimal(0)

    # Risk limits
    max_position_size_pct: float = 0.02  # 2% max per position
    max_portfolio_heat_pct: float = 0.06  # 6% total at risk
    max_drawdown_pct: float = 0.10  # 10% max drawdown

    # Correlation tracking (positions shouldn't be too correlated)
    position_correlations: dict[tuple[InstrumentId, InstrumentId], float] = field(default_factory=dict)
    max_correlation_allowed: float = 0.7

    def check_kelly_criterion(
        self,
        win_rate: float,
        avg_win: Decimal,
        avg_loss: Decimal,
        current_position_pct: float,
    ) -> tuple[bool, str]:
        """
        Verify position sizing doesn't exceed Kelly Criterion.

        Kelly Fraction = (win% * avg_win - loss% * avg_loss) / avg_win

        Safe position size = Kelly Fraction / 2 (half-Kelly for safety)
        """
        if avg_win <= 0:
            return True, "Invalid win amount"

        loss_pct = 1 - win_rate
        kelly_fraction = (win_rate * float(avg_win) - loss_pct * float(abs(avg_loss))) / float(avg_win)
        safe_fraction = kelly_fraction / 2.0

        is_safe = current_position_pct <= safe_fraction

        msg = (
            f"Kelly: {kelly_fraction:.2%}, Safe: {safe_fraction:.2%}, "
            f"Current: {current_position_pct:.2%}"
        )

        return is_safe, msg

    def __str__(self) -> str:
        util_pct = float(self.position_value / self.account_value) if self.account_value > 0 else 0.0
        status = "OK"

        if util_pct > 0.80:
            status = "WARNING"
        if util_pct > 0.95:
            status = "ALERT"

        return (
            f"[{status}] Portfolio:\n"
            f"  Account Value: ${float(self.account_value):,.2f}\n"
            f"  Cash: ${float(self.cash):,.2f}\n"
            f"  Position Value: ${float(self.position_value):,.2f}\n"
            f"  Utilization: {util_pct:.1%}\n"
            f"  Max Heat Allowed: {self.max_portfolio_heat_pct:.1%}\n"
            f"  Max Drawdown Allowed: {self.max_drawdown_pct:.1%}"
        )


class RiskDashboard:
    """Main risk dashboard for the trading system."""

    def __init__(self, account_value: Decimal = Decimal(100000)):
        self.account_value = account_value
        self.data_flow = DataFlowMetrics()
        self.execution = ExecutionMetrics()
        self.positions = PositionMetrics()
        self.strategies: dict[str, StrategyMetrics] = {}
        self.portfolio = PortfolioRiskMetrics(account_value=account_value, cash=account_value)
        self.start_time = datetime.utcnow()

    def register_strategy(self, strategy_name: str) -> StrategyMetrics:
        """Register a strategy for monitoring."""
        metrics = StrategyMetrics(strategy_name=strategy_name)
        self.strategies[strategy_name] = metrics
        return metrics

    def print_dashboard(self) -> None:
        """Print full risk dashboard to console."""
        elapsed = (datetime.utcnow() - self.start_time).total_seconds()
        hours = int(elapsed) // 3600
        mins = (int(elapsed) % 3600) // 60
        secs = int(elapsed) % 60

        print("\n" + "=" * 80)
        print(f"RISK DASHBOARD - Elapsed: {hours}h {mins}m {secs}s")
        print("=" * 80)
        print(self.data_flow)
        print()
        print(self.execution)
        print()
        print(self.positions)
        print()
        print(self.portfolio)

        if self.strategies:
            print("\n" + "-" * 80)
            print("STRATEGY PERFORMANCE:")
            print("-" * 80)
            for strategy in self.strategies.values():
                print(strategy)
                print()

        print("=" * 80 + "\n")

    def export_metrics(self) -> dict:
        """Export all metrics as a dictionary (for logging/persistence)."""
        return {
            'timestamp': datetime.utcnow().isoformat(),
            'elapsed_seconds': (datetime.utcnow() - self.start_time).total_seconds(),
            'data_flow': {
                'quotes_received': self.data_flow.quotes_received,
                'ticks_received': self.data_flow.ticks_received,
                'bars_published': self.data_flow.bars_published,
                'avg_latency_ms': float(np.mean(list(self.data_flow.data_latency_ms))) if self.data_flow.data_latency_ms else 0,
            },
            'execution': {
                'orders_submitted': self.execution.orders_submitted,
                'orders_filled': self.execution.orders_filled,
                'orders_rejected': self.execution.orders_rejected,
                'fill_rate': self.execution.fill_rate,
                'rejection_rate': self.execution.rejection_rate,
                'avg_fill_time_ms': self.execution.avg_fill_time_ms,
            },
            'positions': {
                'open_count': self.positions.open_positions,
                'total_pnl': float(self.positions.total_pnl),
                'unrealised_pnl': float(self.positions.unrealised_pnl),
                'realised_pnl': float(self.positions.realised_pnl),
                'current_drawdown': float(self.positions.current_drawdown),
                'max_drawdown': float(self.positions.max_drawdown),
            },
            'strategies': {
                name: {
                    'trades': metrics.trades_completed,
                    'win_rate': metrics.win_rate,
                    'profit_factor': metrics.profit_factor,
                    'expectancy': float(metrics.expectancy),
                    'sharpe_ratio': metrics.sharpe_ratio,
                    'total_pnl': float(metrics.total_pnl),
                }
                for name, metrics in self.strategies.items()
            },
            'portfolio': {
                'account_value': float(self.portfolio.account_value),
                'cash': float(self.portfolio.cash),
                'position_value': float(self.portfolio.position_value),
            },
        }


# ================================================================================================
# USAGE EXAMPLE
# ================================================================================================

if __name__ == "__main__":
    # Create dashboard
    dashboard = RiskDashboard(account_value=Decimal(100000))

    # Register strategies
    pairs_metrics = dashboard.register_strategy("RLPairsTradingStrategy")
    momentum_metrics = dashboard.register_strategy("RLMomentumBreakoutStrategy")

    # Simulate some data
    dashboard.data_flow.quotes_received = 1250
    dashboard.data_flow.ticks_received = 3456
    dashboard.data_flow.bars_published = 45
    dashboard.data_flow.data_latency_ms.extend([85.3, 92.1, 78.5, 105.2, 89.7])

    dashboard.execution.orders_submitted = 12
    dashboard.execution.orders_filled = 11
    dashboard.execution.orders_rejected = 1
    dashboard.execution.fill_times_ms.extend([1250, 1850, 980, 2100, 1650, 2050, 1200, 1680, 1920, 1420])

    dashboard.positions.open_positions = 2
    dashboard.positions.total_pnl = Decimal(850)
    dashboard.positions.unrealised_pnl = Decimal(250)
    dashboard.positions.realised_pnl = Decimal(600)
    dashboard.positions.current_drawdown = Decimal(-0.025)
    dashboard.positions.max_drawdown = Decimal(-0.035)

    pairs_metrics.trades_completed = 8
    pairs_metrics.winning_trades = 5
    pairs_metrics.losing_trades = 3
    pairs_metrics.trade_pnls = [Decimal(125), Decimal(85), Decimal(-50), Decimal(200),
                                Decimal(-75), Decimal(110), Decimal(95), Decimal(-40)]
    pairs_metrics.trade_captures = [0.85, 0.92, 0.0, 0.88, 0.0, 0.90, 0.87, 0.0]
    pairs_metrics.trade_holding_bars = [24, 18, 5, 32, 8, 22, 20, 6]
    pairs_metrics.total_pnl = Decimal(550)

    momentum_metrics.trades_completed = 4
    momentum_metrics.winning_trades = 2
    momentum_metrics.losing_trades = 2
    momentum_metrics.trade_pnls = [Decimal(200), Decimal(-120), Decimal(150), Decimal(-50)]
    momentum_metrics.trade_captures = [0.75, 0.0, 0.82, 0.0]
    momentum_metrics.trade_holding_bars = [15, 8, 12, 6]
    momentum_metrics.total_pnl = Decimal(180)

    dashboard.portfolio.position_value = Decimal(20000)
    dashboard.portfolio.cash = Decimal(80000)

    # Print dashboard
    dashboard.print_dashboard()

    # Export metrics
    import json
    metrics = dashboard.export_metrics()
    print("Metrics JSON:")
    print(json.dumps(metrics, indent=2, default=str))
