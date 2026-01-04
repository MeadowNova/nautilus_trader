# -------------------------------------------------------------------------------------------------
#  Risk Management Framework for NautilusTrader Paper Trading
#  Comprehensive position-level and portfolio-level risk controls with P&L tracking
# -------------------------------------------------------------------------------------------------

from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING
from enum import Enum
from collections import defaultdict
from datetime import datetime
import numpy as np
import pandas as pd

if TYPE_CHECKING:
    from nautilus_trader.model import InstrumentId, Price, Quantity
    from nautilus_trader.model.data import Bar

# ===== CONFIGURATION & ENUMS =====

class RiskLevel(str, Enum):
    """Risk severity levels for monitoring and alerts."""
    OK = "OK"
    WARNING = "WARNING"
    CRITICAL = "CRITICAL"
    BREACH = "BREACH"


@dataclass(frozen=True)
class PositionRiskConfig:
    """Configuration for position-level risk controls."""
    max_position_size_usd: float
    max_position_size_pct_account: float = 0.05  # 5% max
    stop_loss_atr_multiple: float = 2.0  # 2x ATR from entry
    take_profit_rr_ratio: float = 2.0  # 2:1 risk/reward
    max_losing_streak: int = 3
    min_win_rate: float = 0.35  # 35% minimum for long-term viability


@dataclass(frozen=True)
class PortfolioRiskConfig:
    """Configuration for portfolio-level risk controls."""
    max_gross_exposure: float = 1.0  # 100% of account
    max_net_exposure: float = 0.75  # 75% long/short delta
    max_single_sector_exposure: float = 0.30  # 30% per sector
    max_correlation_basket: float = 0.85  # Max correlation between positions
    max_daily_loss_pct: float = 0.05  # 5% daily stop
    max_drawdown_pct: float = 0.10  # 10% max drawdown
    margin_utilization_limit: float = 0.80  # 80% max for options
    rebalance_interval_mins: int = 60


@dataclass(frozen=True)
class GreeksConfig:
    """Configuration for options Greeks monitoring."""
    portfolio_delta_limit: float = 0.30  # 30% of account notional
    portfolio_gamma_limit: float = 0.05  # 5% gamma per 1% move
    portfolio_vega_limit: float = 0.25  # 25 vega per 1% IV move
    portfolio_theta_daily_limit: float = 100.0  # $100 theta decay risk per day


# ===== POSITION-LEVEL TRACKING =====

@dataclass
class TradeEntry:
    """Tracks a single trade entry point."""
    instrument_id: str
    entry_price: float
    entry_size: int
    entry_time: datetime
    r_value: float  # Risk in dollars per 1R
    stop_loss_price: float
    take_profit_price: float
    max_adverse_move: float = 0.0
    bars_held: int = 0

    @property
    def risk_amount(self) -> float:
        """Calculate risk amount for this entry."""
        return self.r_value

    @property
    def reward_amount(self) -> float:
        """Calculate reward at take-profit."""
        return self.r_value * (self.take_profit_price - self.entry_price) / abs(
            self.entry_price - self.stop_loss_price
        )


@dataclass
class PositionMetrics:
    """Real-time metrics for an open position."""
    instrument_id: str
    entry_price: float
    current_price: float
    quantity: int
    entry_time: datetime
    direction: str  # 'LONG' or 'SHORT'

    trades: list[TradeEntry] = field(default_factory=list)
    pnl_unrealized: float = 0.0
    pnl_realized: float = 0.0
    max_favorable_move: float = 0.0
    max_adverse_move: float = 0.0
    bars_held: int = 0

    # Greeks for options positions
    delta: float = 0.0
    gamma: float = 0.0
    vega: float = 0.0
    theta: float = 0.0

    @property
    def pnl_total(self) -> float:
        """Total P&L (realized + unrealized)."""
        return self.pnl_realized + self.pnl_unrealized

    @property
    def pnl_pct(self) -> float:
        """Return as percentage."""
        if self.entry_price == 0:
            return 0.0
        move = self.current_price - self.entry_price
        if self.direction == 'SHORT':
            move = -move
        return (move / self.entry_price) * 100

    @property
    def r_multiple(self) -> float:
        """Current position in R-multiples relative to stop loss."""
        if not self.trades:
            return 0.0

        risk_per_trade = [t.risk_amount for t in self.trades]
        total_risk = sum(risk_per_trade)

        if total_risk == 0:
            return 0.0

        return self.pnl_unrealized / total_risk


@dataclass
class RMeasurement:
    """Track performance in R-multiples."""
    winning_trades: int = 0
    losing_trades: int = 0
    total_r_gained: float = 0.0
    total_r_lost: float = 0.0
    consecutive_losses: int = 0
    max_consecutive_losses: int = 0

    @property
    def win_count(self) -> int:
        return self.winning_trades

    @property
    def loss_count(self) -> int:
        return self.losing_trades

    @property
    def win_rate(self) -> float:
        total = self.winning_trades + self.losing_trades
        if total == 0:
            return 0.0
        return self.winning_trades / total

    @property
    def expectancy(self) -> float:
        """Calculate expectancy in R-multiples."""
        total_trades = self.winning_trades + self.losing_trades
        if total_trades == 0:
            return 0.0

        avg_win_r = self.total_r_gained / max(self.winning_trades, 1)
        avg_loss_r = self.total_r_lost / max(self.losing_trades, 1)

        return (self.win_rate * avg_win_r) - ((1 - self.win_rate) * avg_loss_r)

    @property
    def profit_factor(self) -> float:
        """Calculate profit factor: Total Wins / Total Losses."""
        if self.total_r_lost == 0:
            return float('inf') if self.total_r_gained > 0 else 0.0
        return self.total_r_gained / self.total_r_lost

    @property
    def kelly_percentage(self) -> float:
        """Calculate Kelly Criterion: (Win% * AvgWin% - Loss% * AvgLoss%) / AvgWin%."""
        if self.total_r_gained == 0:
            return 0.0

        avg_win_r = self.total_r_gained / max(self.winning_trades, 1)
        avg_loss_r = self.total_r_lost / max(self.losing_trades, 1)

        numerator = (self.win_rate * avg_win_r) - ((1 - self.win_rate) * avg_loss_r)
        denominator = avg_win_r

        if denominator == 0:
            return 0.0

        kelly = numerator / denominator
        return max(0.0, min(kelly, 0.25))  # Cap at 25% for safety


# ===== PORTFOLIO-LEVEL TRACKING =====

@dataclass
class SectorExposure:
    """Track sector concentration and correlation."""
    sector: str
    instruments: list[str] = field(default_factory=list)
    total_notional: float = 0.0
    correlation_matrix: dict[str, float] = field(default_factory=dict)

    def exposure_pct(self, account_size: float) -> float:
        """Calculate sector exposure as % of account."""
        if account_size == 0:
            return 0.0
        return (self.total_notional / account_size) * 100


@dataclass
class PortfolioMetrics:
    """Real-time portfolio-level metrics."""
    account_size: float
    pnl_daily: float = 0.0
    pnl_total: float = 0.0
    gross_exposure: float = 0.0  # Sum of absolute position values
    net_exposure: float = 0.0  # Sum of signed position values

    positions: dict[str, PositionMetrics] = field(default_factory=dict)
    sector_exposure: dict[str, SectorExposure] = field(default_factory=dict)

    peak_equity: float = field(default_factory=lambda: 0.0)
    current_drawdown: float = 0.0
    max_drawdown: float = 0.0

    margin_used: float = 0.0
    margin_available: float = 0.0

    r_measurement: RMeasurement = field(default_factory=RMeasurement)

    # Greeks aggregates (options)
    portfolio_delta: float = 0.0
    portfolio_gamma: float = 0.0
    portfolio_vega: float = 0.0
    portfolio_theta: float = 0.0

    @property
    def gross_exposure_pct(self) -> float:
        """Gross exposure as % of account."""
        if self.account_size == 0:
            return 0.0
        return (self.gross_exposure / self.account_size) * 100

    @property
    def net_exposure_pct(self) -> float:
        """Net exposure as % of account."""
        if self.account_size == 0:
            return 0.0
        return (self.net_exposure / self.account_size) * 100

    @property
    def drawdown_pct(self) -> float:
        """Current drawdown as % of peak equity."""
        if self.peak_equity == 0:
            return 0.0
        return (self.current_drawdown / self.peak_equity) * 100

    @property
    def margin_utilization_pct(self) -> float:
        """Margin utilization as %."""
        total_margin = self.margin_used + self.margin_available
        if total_margin == 0:
            return 0.0
        return (self.margin_used / total_margin) * 100


# ===== POSITION SIZING ENGINE =====

class PositionSizer:
    """Calculate optimal position sizes using various methods."""

    @staticmethod
    def fixed_fraction(
        account_size: float,
        risk_per_trade_pct: float,
        entry_price: float,
        stop_loss_price: float,
    ) -> int:
        """
        Fixed Fractional Position Sizing.

        Calculates position size based on:
        - Account size
        - Risk per trade (percentage of account)
        - Entry and stop prices

        Returns:
        -------
        int
            Position size (quantity)
        """
        if entry_price == 0 or entry_price == stop_loss_price:
            return 0

        risk_amount = account_size * risk_per_trade_pct
        price_risk = abs(entry_price - stop_loss_price)
        position_size = risk_amount / price_risk

        return max(1, int(position_size))

    @staticmethod
    def kelly_criterion(
        win_rate: float,
        avg_win_r: float,
        avg_loss_r: float,
        kelly_multiplier: float = 0.25,  # Fractional Kelly for safety
    ) -> float:
        """
        Kelly Criterion Position Sizing.

        Determines optimal fraction of account to risk based on:
        - Win rate
        - Average win size
        - Average loss size
        - Kelly multiplier (safety factor)

        Returns:
        -------
        float
            Percentage of account to risk (0.0 to kelly_multiplier)
        """
        if avg_win_r == 0:
            return 0.0

        kelly = (win_rate * avg_win_r - (1 - win_rate) * avg_loss_r) / avg_win_r
        kelly = max(0.0, min(kelly, kelly_multiplier))

        return kelly

    @staticmethod
    def volatility_adjusted(
        account_size: float,
        atr_value: float,
        entry_price: float,
        atr_multiple: float = 2.0,
        risk_pct: float = 0.02,
    ) -> int:
        """
        Volatility-Adjusted Position Sizing.

        Positions smaller when volatility is high, larger when low.

        Returns:
        -------
        int
            Position size (quantity)
        """
        if entry_price == 0:
            return 0

        # Stop loss is atr_multiple * ATR from entry
        stop_distance = atr_value * atr_multiple
        risk_amount = account_size * risk_pct
        position_size = risk_amount / stop_distance

        return max(1, int(position_size))


# ===== RISK MONITORING ENGINE =====

class RiskMonitor:
    """Monitor positions and portfolio against risk limits."""

    def __init__(
        self,
        position_config: PositionRiskConfig,
        portfolio_config: PortfolioRiskConfig,
        greeks_config: GreeksConfig,
    ):
        self.position_config = position_config
        self.portfolio_config = portfolio_config
        self.greeks_config = greeks_config

        self.alerts: list[dict] = []

    def check_position_risk(
        self,
        position: PositionMetrics,
        account_size: float,
    ) -> tuple[RiskLevel, list[str]]:
        """
        Comprehensive position-level risk check.

        Returns:
        -------
        tuple[RiskLevel, list[str]]
            Risk level and list of issues
        """
        issues = []

        # Check position size
        position_notional = position.quantity * position.current_price
        if position_notional > self.position_config.max_position_size_usd:
            issues.append(
                f"Position size ${position_notional:,.0f} exceeds max "
                f"${self.position_config.max_position_size_usd:,.0f}"
            )

        pct_account = (position_notional / account_size) * 100 if account_size > 0 else 0
        if pct_account > self.position_config.max_position_size_pct_account * 100:
            issues.append(
                f"Position {pct_account:.1f}% of account exceeds "
                f"{self.position_config.max_position_size_pct_account * 100:.1f}%"
            )

        # Check stop loss has been set
        if position.trades:
            for trade in position.trades:
                if trade.stop_loss_price is None:
                    issues.append(f"Trade without stop loss set")

        # Check adverse move
        if position.max_adverse_move > position.pnl_unrealized:
            issues.append(
                f"Position in adverse territory: "
                f"MAM ${position.max_adverse_move:,.0f} vs U/R P&L ${position.pnl_unrealized:,.0f}"
            )

        # Determine risk level
        if not issues:
            return RiskLevel.OK, issues
        elif len(issues) <= 2:
            return RiskLevel.WARNING, issues
        else:
            return RiskLevel.CRITICAL, issues

    def check_portfolio_risk(
        self,
        portfolio: PortfolioMetrics,
    ) -> tuple[RiskLevel, list[str]]:
        """
        Comprehensive portfolio-level risk check.

        Returns:
        -------
        tuple[RiskLevel, list[str]]
            Risk level and list of issues
        """
        issues = []

        # Check gross exposure
        if portfolio.gross_exposure_pct > self.portfolio_config.max_gross_exposure * 100:
            issues.append(
                f"Gross exposure {portfolio.gross_exposure_pct:.1f}% exceeds "
                f"{self.portfolio_config.max_gross_exposure * 100:.1f}%"
            )

        # Check net exposure
        if abs(portfolio.net_exposure_pct) > self.portfolio_config.max_net_exposure * 100:
            issues.append(
                f"Net exposure {abs(portfolio.net_exposure_pct):.1f}% exceeds "
                f"{self.portfolio_config.max_net_exposure * 100:.1f}%"
            )

        # Check sector concentration
        for sector, exposure in portfolio.sector_exposure.items():
            sector_pct = exposure.exposure_pct(portfolio.account_size)
            if sector_pct > self.portfolio_config.max_single_sector_exposure * 100:
                issues.append(
                    f"Sector {sector} {sector_pct:.1f}% exceeds "
                    f"{self.portfolio_config.max_single_sector_exposure * 100:.1f}%"
                )

        # Check daily loss
        if portfolio.pnl_daily < 0:
            daily_loss_pct = abs(portfolio.pnl_daily) / portfolio.account_size * 100
            if daily_loss_pct > self.portfolio_config.max_daily_loss_pct * 100:
                issues.append(
                    f"Daily loss {daily_loss_pct:.2f}% exceeds "
                    f"{self.portfolio_config.max_daily_loss_pct * 100:.2f}%"
                )

        # Check drawdown
        if portfolio.drawdown_pct > self.portfolio_config.max_drawdown_pct * 100:
            issues.append(
                f"Drawdown {portfolio.drawdown_pct:.2f}% exceeds "
                f"{self.portfolio_config.max_drawdown_pct * 100:.2f}%"
            )

        # Check margin utilization
        if portfolio.margin_utilization_pct > self.portfolio_config.margin_utilization_limit * 100:
            issues.append(
                f"Margin utilization {portfolio.margin_utilization_pct:.1f}% exceeds "
                f"{self.portfolio_config.margin_utilization_limit * 100:.1f}%"
            )

        # Check Greeks exposure
        if abs(portfolio.portfolio_delta) > self.greeks_config.portfolio_delta_limit:
            issues.append(
                f"Portfolio delta {portfolio.portfolio_delta:.3f} exceeds "
                f"limit {self.greeks_config.portfolio_delta_limit}"
            )

        if portfolio.portfolio_gamma > self.greeks_config.portfolio_gamma_limit:
            issues.append(
                f"Portfolio gamma {portfolio.portfolio_gamma:.4f} exceeds "
                f"limit {self.greeks_config.portfolio_gamma_limit}"
            )

        if abs(portfolio.portfolio_vega) > self.greeks_config.portfolio_vega_limit:
            issues.append(
                f"Portfolio vega {abs(portfolio.portfolio_vega):.2f} exceeds "
                f"limit {self.greeks_config.portfolio_vega_limit}"
            )

        # Determine risk level
        if not issues:
            return RiskLevel.OK, issues
        elif len(issues) <= 2:
            return RiskLevel.WARNING, issues
        elif len(issues) <= 4:
            return RiskLevel.CRITICAL, issues
        else:
            return RiskLevel.BREACH, issues

    def check_correlation(
        self,
        positions: dict[str, PositionMetrics],
    ) -> tuple[RiskLevel, list[str]]:
        """
        Check correlation concentration between positions.

        Returns:
        -------
        tuple[RiskLevel, list[str]]
            Risk level and list of correlated position pairs
        """
        issues = []

        if len(positions) < 2:
            return RiskLevel.OK, issues

        # In a real implementation, calculate price correlations
        # For now, return placeholder

        return RiskLevel.OK, issues


# ===== STOP LOSS & TAKE PROFIT ENGINE =====

class StopLossEngine:
    """Calculate and manage stop losses using various methods."""

    @staticmethod
    def atr_based(
        entry_price: float,
        atr_value: float,
        atr_multiple: float = 2.0,
        direction: str = "LONG",
    ) -> float:
        """
        Calculate stop loss using Average True Range (ATR).

        Parameters:
        -----------
        entry_price : float
            Price at which position was entered
        atr_value : float
            Current ATR value
        atr_multiple : float
            Number of ATR units for stop distance
        direction : str
            'LONG' or 'SHORT'

        Returns:
        --------
        float
            Stop loss price
        """
        stop_distance = atr_value * atr_multiple

        if direction == "LONG":
            return entry_price - stop_distance
        else:  # SHORT
            return entry_price + stop_distance

    @staticmethod
    def percentage_based(
        entry_price: float,
        stop_loss_pct: float = 0.02,
        direction: str = "LONG",
    ) -> float:
        """
        Calculate stop loss as percentage of entry price.

        Parameters:
        -----------
        entry_price : float
            Entry price
        stop_loss_pct : float
            Percentage stop distance (e.g., 0.02 = 2%)
        direction : str
            'LONG' or 'SHORT'

        Returns:
        --------
        float
            Stop loss price
        """
        stop_distance = entry_price * stop_loss_pct

        if direction == "LONG":
            return entry_price - stop_distance
        else:  # SHORT
            return entry_price + stop_distance

    @staticmethod
    def swing_point(
        recent_lows: list[float],
        entry_price: float,
        direction: str = "LONG",
    ) -> float:
        """
        Calculate stop loss at recent swing point.

        Parameters:
        -----------
        recent_lows : list[float]
            Recent price lows (for LONG) or highs (for SHORT)
        entry_price : float
            Entry price
        direction : str
            'LONG' or 'SHORT'

        Returns:
        --------
        float
            Stop loss price
        """
        if not recent_lows:
            return entry_price * 0.98 if direction == "LONG" else entry_price * 1.02

        if direction == "LONG":
            return min(recent_lows)
        else:  # SHORT
            return max(recent_lows)


class TakeProfitEngine:
    """Calculate and manage take profit levels using various methods."""

    @staticmethod
    def risk_reward_based(
        entry_price: float,
        stop_loss_price: float,
        rr_ratio: float = 2.0,
        direction: str = "LONG",
    ) -> float:
        """
        Calculate take profit based on risk-to-reward ratio.

        Parameters:
        -----------
        entry_price : float
            Entry price
        stop_loss_price : float
            Stop loss price
        rr_ratio : float
            Risk-to-reward ratio (e.g., 2.0 = 2:1)
        direction : str
            'LONG' or 'SHORT'

        Returns:
        --------
        float
            Take profit price
        """
        risk = abs(entry_price - stop_loss_price)
        reward = risk * rr_ratio

        if direction == "LONG":
            return entry_price + reward
        else:  # SHORT
            return entry_price - reward

    @staticmethod
    def atr_based(
        entry_price: float,
        atr_value: float,
        atr_multiple: float = 4.0,
        direction: str = "LONG",
    ) -> float:
        """
        Calculate take profit using ATR multiple.

        Parameters:
        -----------
        entry_price : float
            Entry price
        atr_value : float
            ATR value
        atr_multiple : float
            ATR multiple for target
        direction : str
            'LONG' or 'SHORT'

        Returns:
        --------
        float
            Take profit price
        """
        target_distance = atr_value * atr_multiple

        if direction == "LONG":
            return entry_price + target_distance
        else:  # SHORT
            return entry_price - target_distance


# ===== REPORTING & ANALYTICS =====

class RiskReporter:
    """Generate comprehensive risk reports and analytics."""

    @staticmethod
    def generate_position_report(
        position: PositionMetrics,
        account_size: float,
    ) -> dict:
        """Generate a position-level risk report."""
        return {
            "instrument": position.instrument_id,
            "direction": position.direction,
            "quantity": position.quantity,
            "entry_price": round(position.entry_price, 2),
            "current_price": round(position.current_price, 2),
            "pnl_unrealized": round(position.pnl_unrealized, 2),
            "pnl_pct": round(position.pnl_pct, 2),
            "r_multiple": round(position.r_multiple, 2),
            "bars_held": position.bars_held,
            "max_favorable_move": round(position.max_favorable_move, 2),
            "max_adverse_move": round(position.max_adverse_move, 2),
            "account_pct": round(
                (position.quantity * position.current_price / account_size) * 100, 2
            ),
            "delta": round(position.delta, 3) if position.delta else None,
            "gamma": round(position.gamma, 4) if position.gamma else None,
            "vega": round(position.vega, 2) if position.vega else None,
            "theta": round(position.theta, 2) if position.theta else None,
        }

    @staticmethod
    def generate_portfolio_report(
        portfolio: PortfolioMetrics,
    ) -> dict:
        """Generate a portfolio-level risk report."""
        return {
            "account_size": round(portfolio.account_size, 2),
            "pnl_daily": round(portfolio.pnl_daily, 2),
            "pnl_total": round(portfolio.pnl_total, 2),
            "gross_exposure": round(portfolio.gross_exposure, 2),
            "gross_exposure_pct": round(portfolio.gross_exposure_pct, 2),
            "net_exposure": round(portfolio.net_exposure, 2),
            "net_exposure_pct": round(portfolio.net_exposure_pct, 2),
            "drawdown": round(portfolio.current_drawdown, 2),
            "drawdown_pct": round(portfolio.drawdown_pct, 2),
            "max_drawdown_pct": round(portfolio.max_drawdown * 100 / portfolio.peak_equity, 2)
            if portfolio.peak_equity > 0 else 0.0,
            "margin_utilization_pct": round(portfolio.margin_utilization_pct, 2),
            "positions_count": len(portfolio.positions),
            "win_rate": round(portfolio.r_measurement.win_rate * 100, 2),
            "expectancy": round(portfolio.r_measurement.expectancy, 3),
            "profit_factor": round(portfolio.r_measurement.profit_factor, 2),
            "kelly_percentage": round(portfolio.r_measurement.kelly_percentage * 100, 2),
            "portfolio_delta": round(portfolio.portfolio_delta, 3),
            "portfolio_gamma": round(portfolio.portfolio_gamma, 4),
            "portfolio_vega": round(portfolio.portfolio_vega, 2),
            "portfolio_theta": round(portfolio.portfolio_theta, 2),
        }

    @staticmethod
    def generate_expectancy_report(
        r_measurement: RMeasurement,
    ) -> dict:
        """Generate expectancy and performance metrics."""
        return {
            "winning_trades": r_measurement.winning_trades,
            "losing_trades": r_measurement.losing_trades,
            "total_trades": r_measurement.winning_trades + r_measurement.losing_trades,
            "win_rate": round(r_measurement.win_rate * 100, 2),
            "total_r_gained": round(r_measurement.total_r_gained, 2),
            "total_r_lost": round(r_measurement.total_r_lost, 2),
            "avg_win_r": round(
                r_measurement.total_r_gained / max(r_measurement.winning_trades, 1), 2
            ),
            "avg_loss_r": round(
                r_measurement.total_r_lost / max(r_measurement.losing_trades, 1), 2
            ),
            "expectancy": round(r_measurement.expectancy, 3),
            "profit_factor": round(r_measurement.profit_factor, 2),
            "kelly_percentage": round(r_measurement.kelly_percentage * 100, 2),
            "max_consecutive_losses": r_measurement.max_consecutive_losses,
        }


# ===== MONTE CARLO SIMULATOR =====

class MonteCarloSimulator:
    """Simulate trading scenarios for stress testing."""

    @staticmethod
    def simulate_drawdown(
        win_rate: float,
        avg_win_r: float,
        avg_loss_r: float,
        num_trades: int = 100,
        num_simulations: int = 1000,
        starting_capital: float = 100000.0,
    ) -> dict:
        """
        Monte Carlo simulation of account drawdown.

        Returns:
        --------
        dict
            Drawdown statistics
        """
        max_drawdowns = []
        final_capitals = []

        for _ in range(num_simulations):
            capital = starting_capital
            peak = capital
            max_dd = 0.0

            for _ in range(num_trades):
                # Simulate win/loss
                if np.random.random() < win_rate:
                    capital += capital * avg_win_r
                else:
                    capital -= capital * avg_loss_r

                # Track peak and drawdown
                if capital > peak:
                    peak = capital
                drawdown = (peak - capital) / peak
                max_dd = max(max_dd, drawdown)

            max_drawdowns.append(max_dd)
            final_capitals.append(capital)

        return {
            "expected_final_capital": round(np.mean(final_capitals), 2),
            "capital_std_dev": round(np.std(final_capitals), 2),
            "worst_case_capital": round(np.percentile(final_capitals, 5), 2),
            "best_case_capital": round(np.percentile(final_capitals, 95), 2),
            "avg_max_drawdown_pct": round(np.mean(max_drawdowns) * 100, 2),
            "worst_case_drawdown_pct": round(np.percentile(max_drawdowns, 95) * 100, 2),
        }

    @staticmethod
    def simulate_paths(
        current_price: float,
        annual_return: float,
        annual_volatility: float,
        days_to_simulate: int = 30,
        num_paths: int = 1000,
    ) -> dict:
        """
        Monte Carlo simulation of price paths.

        Returns:
        --------
        dict
            Price path statistics
        """
        daily_return = annual_return / 252
        daily_vol = annual_volatility / np.sqrt(252)

        paths = np.zeros((num_paths, days_to_simulate))
        paths[:, 0] = current_price

        for day in range(1, days_to_simulate):
            random_returns = np.random.normal(
                daily_return, daily_vol, num_paths
            )
            paths[:, day] = paths[:, day - 1] * (1 + random_returns)

        final_prices = paths[:, -1]

        return {
            "expected_price": round(np.mean(final_prices), 2),
            "price_std_dev": round(np.std(final_prices), 2),
            "percentile_5": round(np.percentile(final_prices, 5), 2),
            "percentile_25": round(np.percentile(final_prices, 25), 2),
            "percentile_50": round(np.percentile(final_prices, 50), 2),
            "percentile_75": round(np.percentile(final_prices, 75), 2),
            "percentile_95": round(np.percentile(final_prices, 95), 2),
        }


if __name__ == "__main__":
    # Example usage and testing
    print("Risk Management Framework Loaded Successfully")
    print("\nAvailable Components:")
    print("- PositionRiskConfig: Position-level risk parameters")
    print("- PortfolioRiskConfig: Portfolio-level risk parameters")
    print("- GreeksConfig: Options Greeks monitoring")
    print("- PositionMetrics: Track individual positions")
    print("- PortfolioMetrics: Track portfolio statistics")
    print("- RMeasurement: Track performance in R-multiples")
    print("- PositionSizer: Calculate optimal position sizes")
    print("- RiskMonitor: Check positions against limits")
    print("- StopLossEngine: Calculate stop losses")
    print("- TakeProfitEngine: Calculate take profits")
    print("- RiskReporter: Generate risk reports")
    print("- MonteCarloSimulator: Stress test scenarios")
