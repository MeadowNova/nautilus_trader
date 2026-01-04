"""
Risk Configuration for Moomoo Paper Trading System

This module defines risk limits and constraints for the options trading system.
All limits are enforced by the risk monitor and pre-trade checks.
"""

from dataclasses import dataclass
from datetime import datetime
from typing import Dict, Optional


@dataclass
class RiskLimits:
    """Core risk limits for the trading system."""

    # Position sizing constraints
    max_contracts_per_option: int = 5  # Maximum contracts per single option position
    max_total_positions: int = 5  # Maximum concurrent option positions

    # Capital constraints
    max_notional_exposure: float = 10_000.00  # Max notional value across all options
    max_daily_loss: float = 1_000.00  # Max loss before stopping trading
    max_account_risk_percent: float = 1.0  # Max percent of account per trade

    # Premium and execution constraints
    min_premium_width: float = 0.01  # Minimum bid-ask spread in premium
    max_premium_paid_per_contract: float = 500.00  # Max premium per contract

    # Expiration constraints
    min_days_to_expiration: int = 2  # Don't trade within this many days of expiration
    max_days_to_expiration: int = 60  # Don't trade options expiring beyond this

    # Stop loss constraints
    stop_loss_percent: float = 50.0  # Stop loss as % of premium paid
    take_profit_percent: float = 200.0  # Take profit target as % of premium paid

    # Order rate limiting
    max_orders_per_30_seconds: int = 15  # Rate limit for Moomoo API

    # Greeks exposure limits
    max_net_delta: float = 100.0  # Maximum net delta exposure
    max_gamma_per_position: float = 0.10  # Max gamma per position

    # Account parameters
    account_size: float = 100_000.00  # Paper trading account size
    min_buying_power_buffer: float = 0.20  # Keep 20% buying power reserve

    def __post_init__(self):
        """Validate configuration after initialization."""
        assert self.max_contracts_per_option > 0, "max_contracts_per_option must be positive"
        assert self.max_total_positions > 0, "max_total_positions must be positive"
        assert self.max_notional_exposure > 0, "max_notional_exposure must be positive"
        assert self.max_daily_loss > 0, "max_daily_loss must be positive"
        assert self.stop_loss_percent > 0, "stop_loss_percent must be positive"
        assert self.take_profit_percent > 0, "take_profit_percent must be positive"
        assert 0 < self.max_account_risk_percent <= 5, "max_account_risk_percent should be 0-5%"
        assert 0 <= self.min_days_to_expiration < 30, "min_days_to_expiration should be 0-30 days"

    def calculate_position_size(
        self,
        current_notional: float,
        new_notional: float
    ) -> bool:
        """Check if adding new position would exceed notional limit.

        Args:
            current_notional: Current total notional exposure
            new_notional: Notional value of new position

        Returns:
            True if position is allowed, False otherwise
        """
        return (current_notional + new_notional) <= self.max_notional_exposure

    def get_position_risk_amount(self, account_size: float) -> float:
        """Calculate risk amount per trade in dollars.

        Args:
            account_size: Current account size

        Returns:
            Maximum risk amount per trade
        """
        return account_size * (self.max_account_risk_percent / 100.0)

    def get_contracts_allowed(
        self,
        current_contracts: int
    ) -> int:
        """Calculate maximum additional contracts allowed.

        Args:
            current_contracts: Current number of contracts

        Returns:
            Number of additional contracts allowed
        """
        return max(0, self.max_contracts_per_option - current_contracts)


@dataclass
class TradeConstraints:
    """Constraints for individual trades."""

    symbol: str
    option_type: str  # 'CALL' or 'PUT'
    strike_price: float
    expiration_date: datetime

    def days_to_expiration(self) -> float:
        """Calculate days until expiration."""
        return (self.expiration_date - datetime.now()).days

    def is_valid_expiration(self, risk_limits: RiskLimits) -> tuple[bool, str]:
        """Validate expiration against risk limits.

        Args:
            risk_limits: RiskLimits instance

        Returns:
            Tuple of (is_valid, reason_if_invalid)
        """
        dte = self.days_to_expiration()

        if dte < risk_limits.min_days_to_expiration:
            return False, f"Too close to expiration: {dte} DTE < {risk_limits.min_days_to_expiration} min"

        if dte > risk_limits.max_days_to_expiration:
            return False, f"Too far from expiration: {dte} DTE > {risk_limits.max_days_to_expiration} max"

        return True, ""


@dataclass
class RiskAlert:
    """Risk alert triggered when limits approached or exceeded."""

    alert_type: str  # 'WARNING' or 'CRITICAL'
    metric: str  # Which metric triggered the alert
    current_value: float
    limit_value: float
    percent_of_limit: float
    message: str
    timestamp: datetime

    def __str__(self) -> str:
        """Format alert as readable string."""
        return (
            f"[{self.alert_type}] {self.metric}: {self.current_value:.2f} / {self.limit_value:.2f} "
            f"({self.percent_of_limit:.1f}%)\n{self.message}"
        )


class RiskMonitorConfig:
    """Configuration for the risk monitoring system."""

    # Alert thresholds
    WARNING_THRESHOLD_PERCENT = 80.0  # Warn when 80% of limit reached
    CRITICAL_THRESHOLD_PERCENT = 95.0  # Critical when 95% of limit reached

    # Monitoring intervals
    MONITOR_INTERVAL_SECONDS = 30  # Check risk every 30 seconds

    # Log settings
    LOG_FILE_PATH = "/home/ajk/Nautilus/nautilus_trader/logs/risk_monitor.log"
    POSITION_LOG_PATH = "/home/ajk/Nautilus/nautilus_trader/logs/positions.log"
    TRADE_LOG_PATH = "/home/ajk/Nautilus/nautilus_trader/logs/trades.log"

    # Moomoo API settings
    MOOMOO_CHECK_INTERVAL = 30  # Seconds between position checks

    # Performance tracking
    DAILY_PNL_RESET_HOUR = 0  # Reset daily P&L at midnight
    R_MULTIPLE_TRACKING = True  # Track all trades in R-multiples


# Default configuration instance
DEFAULT_RISK_LIMITS = RiskLimits(
    max_contracts_per_option=5,
    max_total_positions=5,
    max_notional_exposure=10_000.00,
    max_daily_loss=1_000.00,
    max_account_risk_percent=1.0,
    account_size=100_000.00,
)


def load_risk_config(config_path: Optional[str] = None) -> RiskLimits:
    """Load risk configuration from file or use defaults.

    Args:
        config_path: Optional path to custom config file

    Returns:
        RiskLimits instance
    """
    # TODO: Implement loading from YAML/JSON config if provided
    return DEFAULT_RISK_LIMITS


if __name__ == "__main__":
    # Test configuration
    config = DEFAULT_RISK_LIMITS
    print(f"Risk Configuration Loaded:")
    print(f"  Max Position Size: {config.max_contracts_per_option} contracts")
    print(f"  Max Total Exposure: ${config.max_notional_exposure:,.2f}")
    print(f"  Max Daily Loss: ${config.max_daily_loss:,.2f}")
    print(f"  Account Size: ${config.account_size:,.2f}")
    print(f"  Min Days to Expiration: {config.min_days_to_expiration} days")
    print(f"  Stop Loss: {config.stop_loss_percent}% of premium")
