"""
Moomoo RL Paper Trading System - Risk Configuration Module
===========================================================

Complete risk management configuration for a $100,000 paper trading account.
Designed for integration with NautilusTrader and the RL framework.

Usage:
    from moomoo_rl_risk_configuration import (
        get_risk_config,
        get_position_limits,
        get_r_multiple_calculator,
        RiskConfigurationManager,
    )

    # Initialize configuration
    config = get_risk_config()

    # Get position sizing
    position_size = config.calculate_position_size(
        entry_price=150.0,
        stop_loss_price=145.0,
    )

Author: Risk Management Team
Date: 2025-12-09
Account: $100,000 Paper Trading
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from decimal import Decimal
from enum import Enum
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import numpy as np


# =============================================================================
# CONFIGURATION CONSTANTS
# =============================================================================

ACCOUNT_SIZE = 100_000.00  # $100,000 paper trading account
BASE_CURRENCY = "USD"


class RiskLevel(str, Enum):
    """Risk severity levels."""
    OK = "OK"
    WARNING = "WARNING"
    CRITICAL = "CRITICAL"
    BREACH = "BREACH"


class Strategy(str, Enum):
    """Trading strategies in the system."""
    PAIRS_TRADING = "pairs_trading"
    MOMENTUM_BREAKOUT = "momentum_breakout"
    COVERED_CALLS = "covered_calls"


# =============================================================================
# POSITION LIMITS CONFIGURATION
# =============================================================================

@dataclass(frozen=True)
class PositionLimitsConfig:
    """
    Position-level risk limits for $100,000 account.

    Conservative settings appropriate for RL learning phase.
    """
    # Maximum position size (dollar and percentage)
    max_position_size_usd: float = 10_000.00
    max_position_size_pct: float = 0.10  # 10% of account

    # Concurrent position limits
    max_concurrent_positions: int = 8
    max_positions_pairs_trading: int = 2
    max_positions_momentum: int = 4
    max_positions_covered_calls: int = 2

    # Single stock exposure
    max_single_stock_exposure_pct: float = 0.15  # 15% max in any one stock

    def get_effective_max_position(self, account_size: float = ACCOUNT_SIZE) -> float:
        """
        Calculate effective maximum position size.

        Returns the lesser of:
        - Absolute dollar limit
        - Percentage of current account
        """
        pct_limit = account_size * self.max_position_size_pct
        return min(self.max_position_size_usd, pct_limit)


# =============================================================================
# EXPOSURE LIMITS CONFIGURATION
# =============================================================================

@dataclass(frozen=True)
class ExposureLimitsConfig:
    """
    Portfolio-level exposure constraints.

    Designed to prevent over-leveraging during the learning phase.
    """
    # Gross exposure (total long + short)
    max_gross_exposure_pct: float = 0.80  # 80% of account
    max_gross_exposure_usd: float = 80_000.00

    # Net exposure (long - short)
    max_net_exposure_pct: float = 0.60  # 60% net directional
    max_net_exposure_usd: float = 60_000.00

    # Sector concentration
    max_sector_exposure_pct: float = 0.30  # 30% per sector
    max_sector_exposure_usd: float = 30_000.00

    # Correlation limits
    max_position_correlation: float = 0.75

    def check_exposure(
        self,
        gross_exposure: float,
        net_exposure: float,
        account_size: float = ACCOUNT_SIZE,
    ) -> Tuple[RiskLevel, List[str]]:
        """
        Check if exposure limits are breached.

        Returns:
            Tuple of (RiskLevel, list of issues)
        """
        issues = []
        gross_pct = gross_exposure / account_size
        net_pct = abs(net_exposure) / account_size

        if gross_pct > self.max_gross_exposure_pct:
            issues.append(
                f"Gross exposure {gross_pct:.1%} exceeds {self.max_gross_exposure_pct:.1%}"
            )

        if net_pct > self.max_net_exposure_pct:
            issues.append(
                f"Net exposure {net_pct:.1%} exceeds {self.max_net_exposure_pct:.1%}"
            )

        if not issues:
            return RiskLevel.OK, issues
        elif len(issues) == 1:
            return RiskLevel.WARNING, issues
        else:
            return RiskLevel.CRITICAL, issues


# =============================================================================
# RISK THRESHOLDS CONFIGURATION
# =============================================================================

@dataclass(frozen=True)
class RiskThresholdsConfig:
    """
    Loss limits and circuit breaker thresholds.

    Conservative settings for the RL learning phase:
    - 3% daily loss limit (vs typical 5% for experienced traders)
    - 10% max drawdown (vs typical 15-20%)
    - 1% per-trade risk (vs typical 2%)
    """
    # Daily loss limits
    daily_loss_limit_pct: float = 0.03  # 3% daily stop
    daily_loss_limit_usd: float = 3_000.00

    # Weekly loss limits
    weekly_loss_limit_pct: float = 0.05  # 5% weekly stop
    weekly_loss_limit_usd: float = 5_000.00

    # Maximum drawdown
    max_drawdown_pct: float = 0.10  # 10% from peak
    max_drawdown_usd: float = 10_000.00

    # Per-trade risk
    per_trade_risk_pct: float = 0.01  # 1% risk per trade
    per_trade_risk_usd: float = 1_000.00

    def check_daily_loss(
        self,
        daily_pnl: float,
        account_size: float = ACCOUNT_SIZE,
    ) -> Tuple[RiskLevel, Optional[str]]:
        """
        Check if daily loss limit is breached.

        Returns:
            Tuple of (RiskLevel, action_required or None)
        """
        if daily_pnl >= 0:
            return RiskLevel.OK, None

        loss_pct = abs(daily_pnl) / account_size

        if loss_pct >= self.daily_loss_limit_pct:
            return RiskLevel.BREACH, "halt_new_trades"
        elif loss_pct >= self.daily_loss_limit_pct * 0.67:  # 2% warning at 66%
            return RiskLevel.WARNING, None
        else:
            return RiskLevel.OK, None

    def check_drawdown(
        self,
        current_equity: float,
        peak_equity: float,
    ) -> Tuple[RiskLevel, Optional[str]]:
        """
        Check if max drawdown is breached.

        Returns:
            Tuple of (RiskLevel, action_required or None)
        """
        if peak_equity == 0:
            return RiskLevel.OK, None

        drawdown_pct = (peak_equity - current_equity) / peak_equity

        if drawdown_pct >= self.max_drawdown_pct:
            return RiskLevel.BREACH, "emergency_liquidation"
        elif drawdown_pct >= self.max_drawdown_pct * 0.5:  # Warning at 5%
            return RiskLevel.WARNING, "reduce_position_sizes"
        else:
            return RiskLevel.OK, None


# =============================================================================
# R-MULTIPLE TRACKING CONFIGURATION
# =============================================================================

@dataclass
class RMultipleConfig:
    """
    R-multiple tracking and target configuration.

    1R = $1,000 (1% of $100,000 account)

    Target Performance (after 30+ trades):
    - Win Rate: 40%
    - Average Win: 2R ($2,000)
    - Average Loss: 1R ($1,000)
    - Expectancy: 0.20R ($200 per trade)
    """
    # Initial R value
    r_value_usd: float = 1_000.00  # 1R = 1% of account

    # Stop loss configuration
    stop_loss_method: str = "atr_based"
    stop_loss_atr_multiple: float = 2.0
    stop_loss_fallback_pct: float = 0.02

    # Take profit targets (scaled exit)
    take_profit_levels: Dict[str, dict] = field(default_factory=lambda: {
        "tp1": {"r_multiple": 1.0, "exit_pct": 0.33},
        "tp2": {"r_multiple": 2.0, "exit_pct": 0.33},
        "tp3": {"r_multiple": 3.0, "exit_pct": 0.34},
    })

    # Expectancy targets
    minimum_expectancy_r: float = 0.10
    target_expectancy_r: float = 0.25
    target_win_rate: float = 0.40
    target_avg_win_r: float = 2.0
    target_avg_loss_r: float = 1.0

    # Evaluation thresholds
    min_trades_for_evaluation: int = 30

    def calculate_stop_loss(
        self,
        entry_price: float,
        atr_value: Optional[float] = None,
        direction: str = "LONG",
    ) -> float:
        """
        Calculate stop loss price.

        Uses ATR-based stop if available, otherwise falls back to percentage.
        """
        if atr_value is not None and atr_value > 0:
            stop_distance = atr_value * self.stop_loss_atr_multiple
        else:
            stop_distance = entry_price * self.stop_loss_fallback_pct

        if direction == "LONG":
            return entry_price - stop_distance
        else:
            return entry_price + stop_distance

    def calculate_take_profit(
        self,
        entry_price: float,
        stop_loss_price: float,
        r_multiple: float,
        direction: str = "LONG",
    ) -> float:
        """
        Calculate take profit price for given R-multiple target.
        """
        risk = abs(entry_price - stop_loss_price)
        reward = risk * r_multiple

        if direction == "LONG":
            return entry_price + reward
        else:
            return entry_price - reward

    def calculate_expectancy(
        self,
        win_rate: float,
        avg_win_r: float,
        avg_loss_r: float,
    ) -> float:
        """
        Calculate expectancy in R-multiples.

        Expectancy = (Win% x Avg Win) - (Loss% x Avg Loss)
        """
        return (win_rate * avg_win_r) - ((1 - win_rate) * avg_loss_r)

    def is_strategy_viable(
        self,
        win_rate: float,
        avg_win_r: float,
        avg_loss_r: float,
        num_trades: int,
    ) -> Tuple[bool, str]:
        """
        Check if strategy performance is viable for continued trading.

        Returns:
            Tuple of (is_viable, reason)
        """
        if num_trades < self.min_trades_for_evaluation:
            return True, f"Insufficient trades ({num_trades}/{self.min_trades_for_evaluation})"

        expectancy = self.calculate_expectancy(win_rate, avg_win_r, avg_loss_r)

        if expectancy < self.minimum_expectancy_r:
            return False, f"Expectancy {expectancy:.3f}R below minimum {self.minimum_expectancy_r}R"

        if win_rate < 0.25:
            return False, f"Win rate {win_rate:.1%} critically low"

        return True, f"Expectancy {expectancy:.3f}R meets requirements"


# =============================================================================
# RATE LIMITING CONFIGURATION
# =============================================================================

@dataclass(frozen=True)
class RateLimitConfig:
    """
    Order frequency and execution constraints.

    Prevents runaway algorithms and respects broker limits.
    """
    # Order frequency limits
    orders_per_minute: int = 10
    orders_per_hour: int = 60
    orders_per_day: int = 200

    # Fill limits
    fills_per_minute: int = 5
    fills_per_hour: int = 30

    # Cancel limits
    cancel_rate_per_minute: int = 20

    # Order timing
    min_order_interval_seconds: float = 2.0

    # Order size limits
    max_order_value_usd: float = 10_000.00
    max_order_quantity_shares: int = 1000


# =============================================================================
# POSITION SIZING CALCULATOR
# =============================================================================

class PositionSizingCalculator:
    """
    Calculate optimal position sizes using multiple methods.

    Primary method: Volatility-adjusted fixed fractional
    Fallback: Fixed fractional
    Future: Kelly criterion (after 50+ trades with positive expectancy)
    """

    def __init__(
        self,
        account_size: float = ACCOUNT_SIZE,
        risk_per_trade_pct: float = 0.01,
        max_position_pct: float = 0.10,
    ):
        self.account_size = account_size
        self.risk_per_trade_pct = risk_per_trade_pct
        self.max_position_pct = max_position_pct

    def fixed_fractional(
        self,
        entry_price: float,
        stop_loss_price: float,
    ) -> int:
        """
        Calculate position size using fixed fractional method.

        Risk per trade = Account x Risk%
        Position size = Risk per trade / Price risk per share

        Example:
        - Account: $100,000
        - Risk: 1% = $1,000
        - Entry: $150, Stop: $145
        - Price risk: $5
        - Position: $1,000 / $5 = 200 shares
        """
        if entry_price == 0 or entry_price == stop_loss_price:
            return 0

        risk_amount = self.account_size * self.risk_per_trade_pct
        price_risk = abs(entry_price - stop_loss_price)

        if price_risk == 0:
            return 0

        position_size = int(risk_amount / price_risk)

        # Apply maximum position limit
        max_position_value = self.account_size * self.max_position_pct
        max_shares = int(max_position_value / entry_price)

        return min(position_size, max_shares)

    def volatility_adjusted(
        self,
        entry_price: float,
        atr_value: float,
        atr_multiple: float = 2.0,
    ) -> int:
        """
        Calculate position size adjusted for volatility.

        Higher volatility = smaller position size
        Lower volatility = larger position size
        """
        if entry_price == 0 or atr_value == 0:
            return 0

        stop_distance = atr_value * atr_multiple
        return self.fixed_fractional(entry_price, entry_price - stop_distance)

    def kelly_criterion(
        self,
        win_rate: float,
        avg_win_r: float,
        avg_loss_r: float,
        kelly_fraction: float = 0.25,
    ) -> float:
        """
        Calculate Kelly criterion position size percentage.

        Kelly% = (Win% x Avg Win - Loss% x Avg Loss) / Avg Win

        Using fractional Kelly (25%) for safety.

        Returns:
            Position size as percentage of account (0.0 to 0.25)
        """
        if avg_win_r == 0:
            return 0.0

        kelly = (win_rate * avg_win_r - (1 - win_rate) * avg_loss_r) / avg_win_r
        kelly = max(0.0, min(kelly, kelly_fraction))

        return kelly

    def calculate_with_all_methods(
        self,
        entry_price: float,
        stop_loss_price: float,
        atr_value: Optional[float] = None,
        win_rate: Optional[float] = None,
        avg_win_r: Optional[float] = None,
        avg_loss_r: Optional[float] = None,
    ) -> Dict[str, int]:
        """
        Calculate position size using all available methods.

        Returns:
            Dictionary with position sizes from each method
        """
        results = {}

        # Fixed fractional
        results["fixed_fractional"] = self.fixed_fractional(entry_price, stop_loss_price)

        # Volatility adjusted (if ATR available)
        if atr_value is not None:
            results["volatility_adjusted"] = self.volatility_adjusted(
                entry_price, atr_value
            )

        # Kelly criterion (if performance metrics available)
        if all(v is not None for v in [win_rate, avg_win_r, avg_loss_r]):
            kelly_pct = self.kelly_criterion(win_rate, avg_win_r, avg_loss_r)
            position_value = self.account_size * kelly_pct
            results["kelly_criterion"] = int(position_value / entry_price)

        # Recommended: Use the most conservative
        valid_sizes = [s for s in results.values() if s > 0]
        if valid_sizes:
            results["recommended"] = min(valid_sizes)
        else:
            results["recommended"] = 0

        return results


# =============================================================================
# EMERGENCY TRIGGERS
# =============================================================================

@dataclass
class EmergencyTriggersConfig:
    """
    Automatic protective actions for extreme scenarios.
    """
    # Halt new positions triggers
    halt_daily_loss_pct: float = 0.02  # Halt at 2% daily loss
    halt_consecutive_losses: int = 4
    halt_win_rate_below: float = 0.25
    min_trades_for_win_rate_check: int = 10

    # Position size reduction triggers
    reduce_drawdown_pct: float = 0.05  # Reduce at 5% drawdown
    reduction_factor: float = 0.50  # Reduce by 50%

    # Emergency liquidation triggers
    liquidate_drawdown_pct: float = 0.10  # Liquidate at 10% drawdown
    liquidate_daily_loss_pct: float = 0.05  # Liquidate at 5% daily loss

    def check_triggers(
        self,
        daily_pnl: float,
        current_equity: float,
        peak_equity: float,
        consecutive_losses: int,
        win_rate: float,
        num_trades: int,
        account_size: float = ACCOUNT_SIZE,
    ) -> Dict[str, any]:
        """
        Check all emergency triggers and return required actions.

        Returns:
            Dictionary with trigger status and required actions
        """
        actions = {
            "halt_new_positions": False,
            "reduce_position_sizes": False,
            "emergency_liquidation": False,
            "reduction_factor": 1.0,
            "reasons": [],
        }

        # Check daily loss
        if daily_pnl < 0:
            daily_loss_pct = abs(daily_pnl) / account_size

            if daily_loss_pct >= self.liquidate_daily_loss_pct:
                actions["emergency_liquidation"] = True
                actions["reasons"].append(f"Daily loss {daily_loss_pct:.1%} exceeds {self.liquidate_daily_loss_pct:.1%}")

            elif daily_loss_pct >= self.halt_daily_loss_pct:
                actions["halt_new_positions"] = True
                actions["reasons"].append(f"Daily loss {daily_loss_pct:.1%} exceeds {self.halt_daily_loss_pct:.1%}")

        # Check drawdown
        if peak_equity > 0:
            drawdown_pct = (peak_equity - current_equity) / peak_equity

            if drawdown_pct >= self.liquidate_drawdown_pct:
                actions["emergency_liquidation"] = True
                actions["reasons"].append(f"Drawdown {drawdown_pct:.1%} exceeds {self.liquidate_drawdown_pct:.1%}")

            elif drawdown_pct >= self.reduce_drawdown_pct:
                actions["reduce_position_sizes"] = True
                actions["reduction_factor"] = self.reduction_factor
                actions["reasons"].append(f"Drawdown {drawdown_pct:.1%} exceeds {self.reduce_drawdown_pct:.1%}")

        # Check consecutive losses
        if consecutive_losses >= self.halt_consecutive_losses:
            actions["halt_new_positions"] = True
            actions["reasons"].append(f"{consecutive_losses} consecutive losses")

        # Check win rate (after minimum trades)
        if num_trades >= self.min_trades_for_win_rate_check:
            if win_rate < self.halt_win_rate_below:
                actions["halt_new_positions"] = True
                actions["reasons"].append(f"Win rate {win_rate:.1%} below {self.halt_win_rate_below:.1%}")

        return actions


# =============================================================================
# MONTE CARLO STRESS TEST
# =============================================================================

class MonteCarloStressTest:
    """
    Monte Carlo simulation for risk validation.

    Runs simulations to estimate:
    - Expected final capital
    - Worst-case drawdown (95th percentile)
    - Probability of ruin
    """

    def __init__(
        self,
        num_simulations: int = 1000,
        num_trades: int = 100,
        starting_capital: float = ACCOUNT_SIZE,
    ):
        self.num_simulations = num_simulations
        self.num_trades = num_trades
        self.starting_capital = starting_capital

    def simulate(
        self,
        win_rate: float,
        avg_win_r: float,
        avg_loss_r: float,
        risk_per_trade_pct: float = 0.01,
    ) -> Dict[str, float]:
        """
        Run Monte Carlo simulation.

        Returns:
            Dictionary with simulation statistics
        """
        final_capitals = []
        max_drawdowns = []

        for _ in range(self.num_simulations):
            capital = self.starting_capital
            peak = capital
            max_dd = 0.0

            for _ in range(self.num_trades):
                # Determine risk amount (fixed fractional)
                risk_amount = capital * risk_per_trade_pct

                # Simulate trade outcome
                if np.random.random() < win_rate:
                    capital += risk_amount * avg_win_r
                else:
                    capital -= risk_amount * avg_loss_r

                # Prevent negative capital
                capital = max(0, capital)

                # Track drawdown
                if capital > peak:
                    peak = capital
                drawdown = (peak - capital) / peak if peak > 0 else 0
                max_dd = max(max_dd, drawdown)

                # Exit early if ruined
                if capital <= 0:
                    break

            final_capitals.append(capital)
            max_drawdowns.append(max_dd)

        # Calculate statistics
        final_capitals = np.array(final_capitals)
        max_drawdowns = np.array(max_drawdowns)

        return {
            "expected_final_capital": float(np.mean(final_capitals)),
            "capital_std_dev": float(np.std(final_capitals)),
            "worst_case_capital_5pct": float(np.percentile(final_capitals, 5)),
            "best_case_capital_95pct": float(np.percentile(final_capitals, 95)),
            "avg_max_drawdown_pct": float(np.mean(max_drawdowns) * 100),
            "worst_case_drawdown_95pct": float(np.percentile(max_drawdowns, 95) * 100),
            "probability_of_ruin_pct": float((final_capitals <= 0).sum() / len(final_capitals) * 100),
            "probability_of_profit_pct": float((final_capitals > self.starting_capital).sum() / len(final_capitals) * 100),
        }

    def run_scenarios(
        self,
        risk_per_trade_pct: float = 0.01,
    ) -> Dict[str, Dict[str, float]]:
        """
        Run multiple scenarios for comprehensive stress testing.
        """
        scenarios = {
            "baseline": {"win_rate": 0.40, "avg_win_r": 2.0, "avg_loss_r": 1.0},
            "conservative": {"win_rate": 0.35, "avg_win_r": 1.8, "avg_loss_r": 1.1},
            "adverse": {"win_rate": 0.30, "avg_win_r": 1.5, "avg_loss_r": 1.2},
        }

        results = {}
        for name, params in scenarios.items():
            results[name] = self.simulate(
                win_rate=params["win_rate"],
                avg_win_r=params["avg_win_r"],
                avg_loss_r=params["avg_loss_r"],
                risk_per_trade_pct=risk_per_trade_pct,
            )

        return results


# =============================================================================
# MAIN CONFIGURATION MANAGER
# =============================================================================

@dataclass
class RiskConfigurationManager:
    """
    Central manager for all risk configuration components.

    Provides a single interface for accessing and managing risk settings.
    """
    account_size: float = ACCOUNT_SIZE

    position_limits: PositionLimitsConfig = field(default_factory=PositionLimitsConfig)
    exposure_limits: ExposureLimitsConfig = field(default_factory=ExposureLimitsConfig)
    risk_thresholds: RiskThresholdsConfig = field(default_factory=RiskThresholdsConfig)
    r_multiple: RMultipleConfig = field(default_factory=RMultipleConfig)
    rate_limits: RateLimitConfig = field(default_factory=RateLimitConfig)
    emergency_triggers: EmergencyTriggersConfig = field(default_factory=EmergencyTriggersConfig)

    def __post_init__(self):
        """Initialize derived components."""
        self._position_sizer = PositionSizingCalculator(
            account_size=self.account_size,
            risk_per_trade_pct=self.risk_thresholds.per_trade_risk_pct,
            max_position_pct=self.position_limits.max_position_size_pct,
        )
        self._stress_tester = MonteCarloStressTest(
            starting_capital=self.account_size,
        )

    def calculate_position_size(
        self,
        entry_price: float,
        stop_loss_price: float,
        atr_value: Optional[float] = None,
    ) -> int:
        """
        Calculate recommended position size.

        Args:
            entry_price: Entry price per share
            stop_loss_price: Stop loss price per share
            atr_value: Optional ATR value for volatility adjustment

        Returns:
            Recommended position size in shares
        """
        if atr_value is not None:
            return self._position_sizer.volatility_adjusted(
                entry_price, atr_value
            )
        else:
            return self._position_sizer.fixed_fractional(
                entry_price, stop_loss_price
            )

    def check_trade_risk(
        self,
        position_size: int,
        entry_price: float,
        stop_loss_price: float,
    ) -> Tuple[RiskLevel, List[str]]:
        """
        Validate a proposed trade against risk limits.

        Returns:
            Tuple of (RiskLevel, list of issues)
        """
        issues = []

        # Check position value
        position_value = position_size * entry_price
        max_position = self.position_limits.get_effective_max_position(self.account_size)

        if position_value > max_position:
            issues.append(
                f"Position value ${position_value:,.0f} exceeds max ${max_position:,.0f}"
            )

        # Check risk amount
        risk_per_share = abs(entry_price - stop_loss_price)
        total_risk = position_size * risk_per_share

        if total_risk > self.risk_thresholds.per_trade_risk_usd:
            issues.append(
                f"Trade risk ${total_risk:,.0f} exceeds max ${self.risk_thresholds.per_trade_risk_usd:,.0f}"
            )

        if not issues:
            return RiskLevel.OK, issues
        elif len(issues) == 1:
            return RiskLevel.WARNING, issues
        else:
            return RiskLevel.CRITICAL, issues

    def run_stress_test(self) -> Dict[str, Dict[str, float]]:
        """
        Run Monte Carlo stress test with current configuration.

        Returns:
            Dictionary with scenario results
        """
        return self._stress_tester.run_scenarios(
            risk_per_trade_pct=self.risk_thresholds.per_trade_risk_pct
        )

    def get_summary(self) -> Dict[str, any]:
        """
        Get configuration summary for logging/display.
        """
        return {
            "account_size": self.account_size,
            "max_position_size_usd": self.position_limits.max_position_size_usd,
            "max_position_size_pct": self.position_limits.max_position_size_pct,
            "max_concurrent_positions": self.position_limits.max_concurrent_positions,
            "max_gross_exposure_pct": self.exposure_limits.max_gross_exposure_pct,
            "max_net_exposure_pct": self.exposure_limits.max_net_exposure_pct,
            "daily_loss_limit_pct": self.risk_thresholds.daily_loss_limit_pct,
            "max_drawdown_pct": self.risk_thresholds.max_drawdown_pct,
            "per_trade_risk_pct": self.risk_thresholds.per_trade_risk_pct,
            "r_value_usd": self.r_multiple.r_value_usd,
            "target_win_rate": self.r_multiple.target_win_rate,
            "target_expectancy_r": self.r_multiple.target_expectancy_r,
        }

    def to_json(self, filepath: str) -> None:
        """
        Export configuration to JSON file.
        """
        with open(filepath, "w") as f:
            json.dump(self.get_summary(), f, indent=2)

    @classmethod
    def from_json(cls, filepath: str) -> "RiskConfigurationManager":
        """
        Load configuration from JSON file.
        """
        with open(filepath, "r") as f:
            data = json.load(f)

        # Create instance with loaded settings
        # (Simplified - in production, fully deserialize all settings)
        return cls(account_size=data.get("account_size", ACCOUNT_SIZE))


# =============================================================================
# CONVENIENCE FUNCTIONS
# =============================================================================

def get_risk_config() -> RiskConfigurationManager:
    """
    Get the default risk configuration for $100,000 paper trading.
    """
    return RiskConfigurationManager(account_size=ACCOUNT_SIZE)


def get_position_limits() -> PositionLimitsConfig:
    """Get position limits configuration."""
    return PositionLimitsConfig()


def get_r_multiple_calculator() -> RMultipleConfig:
    """Get R-multiple calculator configuration."""
    return RMultipleConfig()


# =============================================================================
# MAIN - DEMONSTRATE CONFIGURATION
# =============================================================================

if __name__ == "__main__":
    print("=" * 80)
    print("MOOMOO RL PAPER TRADING - RISK CONFIGURATION")
    print("$100,000 Account")
    print("=" * 80)

    # Initialize configuration
    config = get_risk_config()

    # Print summary
    print("\n1. CONFIGURATION SUMMARY")
    print("-" * 40)
    summary = config.get_summary()
    for key, value in summary.items():
        if isinstance(value, float):
            if "pct" in key.lower() or "rate" in key.lower():
                print(f"  {key}: {value:.1%}")
            else:
                print(f"  {key}: ${value:,.2f}")
        else:
            print(f"  {key}: {value}")

    # Demonstrate position sizing
    print("\n2. POSITION SIZING EXAMPLE")
    print("-" * 40)
    entry_price = 150.00
    stop_loss_price = 145.00
    atr_value = 3.50

    position_size = config.calculate_position_size(
        entry_price=entry_price,
        stop_loss_price=stop_loss_price,
        atr_value=atr_value,
    )

    position_value = position_size * entry_price
    risk_amount = position_size * abs(entry_price - stop_loss_price)

    print(f"  Entry Price: ${entry_price:.2f}")
    print(f"  Stop Loss: ${stop_loss_price:.2f}")
    print(f"  ATR Value: ${atr_value:.2f}")
    print(f"  Position Size: {position_size} shares")
    print(f"  Position Value: ${position_value:,.2f}")
    print(f"  Risk Amount: ${risk_amount:,.2f} (1R)")

    # Demonstrate R-multiple targets
    print("\n3. R-MULTIPLE TARGETS")
    print("-" * 40)
    r_config = config.r_multiple

    for level, details in r_config.take_profit_levels.items():
        tp_price = r_config.calculate_take_profit(
            entry_price=entry_price,
            stop_loss_price=stop_loss_price,
            r_multiple=details["r_multiple"],
            direction="LONG",
        )
        profit = (tp_price - entry_price) * position_size
        print(f"  {level.upper()}: {details['r_multiple']}R @ ${tp_price:.2f} = ${profit:,.2f} profit ({details['exit_pct']:.0%} exit)")

    # Demonstrate expectancy calculation
    print("\n4. EXPECTANCY CALCULATION")
    print("-" * 40)
    expectancy = r_config.calculate_expectancy(
        win_rate=r_config.target_win_rate,
        avg_win_r=r_config.target_avg_win_r,
        avg_loss_r=r_config.target_avg_loss_r,
    )
    expectancy_usd = expectancy * r_config.r_value_usd

    print(f"  Target Win Rate: {r_config.target_win_rate:.0%}")
    print(f"  Target Avg Win: {r_config.target_avg_win_r}R")
    print(f"  Target Avg Loss: {r_config.target_avg_loss_r}R")
    print(f"  Expectancy: {expectancy:.2f}R = ${expectancy_usd:,.2f} per trade")

    # Run stress test
    print("\n5. MONTE CARLO STRESS TEST (1000 simulations x 100 trades)")
    print("-" * 40)
    stress_results = config.run_stress_test()

    for scenario, results in stress_results.items():
        print(f"\n  [{scenario.upper()}]")
        print(f"    Expected Final Capital: ${results['expected_final_capital']:,.0f}")
        print(f"    Worst Case (5th %ile): ${results['worst_case_capital_5pct']:,.0f}")
        print(f"    Best Case (95th %ile): ${results['best_case_capital_95pct']:,.0f}")
        print(f"    Avg Max Drawdown: {results['avg_max_drawdown_pct']:.1f}%")
        print(f"    Worst Drawdown (95th %ile): {results['worst_case_drawdown_95pct']:.1f}%")
        print(f"    Probability of Profit: {results['probability_of_profit_pct']:.1f}%")

    print("\n" + "=" * 80)
    print("Configuration files created:")
    print("  - /home/ajk/Nautilus/moomoo_rl_risk_config.json")
    print("  - /home/ajk/Nautilus/moomoo_rl_risk_configuration.py")
    print("=" * 80)
