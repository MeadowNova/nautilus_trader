"""
Pre-Trade Risk Checks for Moomoo Paper Trading

This module performs all necessary risk validation before submitting orders.
All checks must pass before execution is allowed.
"""

import time
from dataclasses import dataclass
from datetime import datetime
from typing import Optional, Tuple
from collections import deque
import logging

from config.options_risk_config import RiskLimits, TradeConstraints, RiskAlert


logger = logging.getLogger(__name__)


@dataclass
class OrderRequest:
    """Represents an order request for validation."""

    symbol: str
    option_type: str  # 'CALL' or 'PUT'
    quantity: int  # Number of contracts
    price: float  # Option premium
    strike_price: float
    expiration_date: datetime
    order_id: Optional[str] = None
    account_id: str = "MOOMOO-1252643"

    @property
    def notional_value(self) -> float:
        """Calculate notional value of the position.

        For options: price * quantity * 100 (standard contract multiplier)
        """
        return self.price * self.quantity * 100.0

    @property
    def max_loss(self) -> float:
        """Maximum loss for this position (premium paid)."""
        return self.price * self.quantity * 100.0


class OrderRateLimiter:
    """Rate limit orders to Moomoo API (15 per 30 seconds max)."""

    def __init__(self, max_orders: int = 15, window_seconds: int = 30):
        """Initialize rate limiter.

        Args:
            max_orders: Maximum orders allowed in window
            window_seconds: Time window in seconds
        """
        self.max_orders = max_orders
        self.window_seconds = window_seconds
        self.order_times: deque = deque()

    def is_allowed(self) -> bool:
        """Check if an order is allowed under rate limits.

        Returns:
            True if order is allowed, False if rate limited
        """
        now = time.time()

        # Remove old entries outside the window
        while self.order_times and (now - self.order_times[0]) > self.window_seconds:
            self.order_times.popleft()

        # Check if we're under the limit
        return len(self.order_times) < self.max_orders

    def record_order(self) -> None:
        """Record that an order was submitted."""
        self.order_times.append(time.time())

    def get_wait_time(self) -> float:
        """Get seconds to wait before next order is allowed.

        Returns:
            Seconds to wait, or 0 if order can be submitted now
        """
        if self.is_allowed():
            return 0.0

        if not self.order_times:
            return 0.0

        oldest_time = self.order_times[0]
        wait_time = self.window_seconds - (time.time() - oldest_time)
        return max(0.0, wait_time)

    def reset(self) -> None:
        """Reset rate limiter."""
        self.order_times.clear()


class PreTradeChecker:
    """Performs all pre-trade risk validation checks."""

    def __init__(
        self,
        risk_limits: RiskLimits,
        current_positions: Optional[dict] = None,
        current_daily_pnl: float = 0.0,
        account_balance: float = 100_000.00,
    ):
        """Initialize the pre-trade checker.

        Args:
            risk_limits: RiskLimits configuration
            current_positions: Dict of current positions
            current_daily_pnl: Current day's P&L
            account_balance: Current account balance
        """
        self.risk_limits = risk_limits
        self.current_positions = current_positions or {}
        self.current_daily_pnl = current_daily_pnl
        self.account_balance = account_balance
        self.rate_limiter = OrderRateLimiter(
            max_orders=risk_limits.max_orders_per_30_seconds
        )
        self.alerts: list[RiskAlert] = []

    def check_order(self, order: OrderRequest) -> Tuple[bool, list[str]]:
        """Run all pre-trade checks on an order.

        Args:
            order: OrderRequest to validate

        Returns:
            Tuple of (is_valid, list_of_error_messages)
        """
        errors = []

        # Check 1: Rate limiting
        if not self.rate_limiter.is_allowed():
            wait_time = self.rate_limiter.get_wait_time()
            errors.append(f"Rate limited: wait {wait_time:.1f}s (15 orders per 30s)")

        # Check 2: Daily loss limit
        if not self._check_daily_loss(order):
            errors.append(
                f"Daily loss limit exceeded: ${abs(self.current_daily_pnl):.2f} / "
                f"${self.risk_limits.max_daily_loss:.2f}"
            )

        # Check 3: Position count limit
        if not self._check_position_count():
            errors.append(
                f"Max concurrent positions reached: "
                f"{len(self.current_positions)} / {self.risk_limits.max_total_positions}"
            )

        # Check 4: Notional exposure limit
        if not self._check_notional_exposure(order):
            current_notional = self._get_current_notional()
            errors.append(
                f"Notional exposure limit exceeded: "
                f"${current_notional + order.notional_value:.2f} / "
                f"${self.risk_limits.max_notional_exposure:.2f}"
            )

        # Check 5: Contract limit per option
        if not self._check_contract_limit(order):
            errors.append(
                f"Contract limit per option exceeded: "
                f"{order.quantity} > {self.risk_limits.max_contracts_per_option}"
            )

        # Check 6: Expiration date validation
        if not self._check_expiration(order):
            dte = (order.expiration_date - datetime.now()).days
            errors.append(
                f"Invalid expiration: {dte} days to expiration "
                f"(min: {self.risk_limits.min_days_to_expiration}, "
                f"max: {self.risk_limits.max_days_to_expiration})"
            )

        # Check 7: Buying power available
        if not self._check_buying_power(order):
            required = order.notional_value
            available = self.account_balance * (1 - self.risk_limits.min_buying_power_buffer)
            errors.append(
                f"Insufficient buying power: ${required:.2f} required, "
                f"${available:.2f} available"
            )

        # Check 8: Account risk limit (as % of account)
        if not self._check_account_risk(order):
            max_risk = self.risk_limits.get_position_risk_amount(self.account_balance)
            errors.append(
                f"Account risk limit exceeded: ${order.max_loss:.2f} > "
                f"${max_risk:.2f} (max {self.risk_limits.max_account_risk_percent}%)"
            )

        # Check 9: Premium width (bid-ask spread)
        if order.price < self.risk_limits.min_premium_width:
            errors.append(
                f"Premium too low: ${order.price:.4f} < "
                f"${self.risk_limits.min_premium_width:.4f}"
            )

        # Check 10: Premium per contract limit
        if order.price > self.risk_limits.max_premium_paid_per_contract:
            errors.append(
                f"Premium too high: ${order.price:.2f} > "
                f"${self.risk_limits.max_premium_paid_per_contract:.2f} per contract"
            )

        return len(errors) == 0, errors

    def _check_daily_loss(self, order: OrderRequest) -> bool:
        """Check if trade would exceed daily loss limit."""
        potential_loss = self.current_daily_pnl - order.max_loss
        return potential_loss >= -self.risk_limits.max_daily_loss

    def _check_position_count(self) -> bool:
        """Check if adding another position would exceed the limit."""
        return len(self.current_positions) < self.risk_limits.max_total_positions

    def _check_notional_exposure(self, order: OrderRequest) -> bool:
        """Check if notional exposure would exceed limit."""
        current = self._get_current_notional()
        return self.risk_limits.calculate_position_size(current, order.notional_value)

    def _check_contract_limit(self, order: OrderRequest) -> bool:
        """Check if contract quantity exceeds per-option limit."""
        return order.quantity <= self.risk_limits.max_contracts_per_option

    def _check_expiration(self, order: OrderRequest) -> bool:
        """Check if expiration date is within allowed range."""
        constraint = TradeConstraints(
            symbol=order.symbol,
            option_type=order.option_type,
            strike_price=order.strike_price,
            expiration_date=order.expiration_date,
        )
        is_valid, _ = constraint.is_valid_expiration(self.risk_limits)
        return is_valid

    def _check_buying_power(self, order: OrderRequest) -> bool:
        """Check if sufficient buying power is available."""
        required = order.notional_value
        buffer = self.risk_limits.min_buying_power_buffer
        available = self.account_balance * (1 - buffer)
        return required <= available

    def _check_account_risk(self, order: OrderRequest) -> bool:
        """Check if trade risk exceeds account risk limit."""
        max_risk = self.risk_limits.get_position_risk_amount(self.account_balance)
        return order.max_loss <= max_risk

    def _get_current_notional(self) -> float:
        """Calculate current notional exposure from positions."""
        total = 0.0
        for pos in self.current_positions.values():
            # Assuming position dict has 'quantity' and 'mark_price' keys
            if isinstance(pos, dict):
                notional = pos.get("quantity", 0) * pos.get("mark_price", 0) * 100
                total += notional
        return total

    def update_positions(self, positions: dict) -> None:
        """Update current positions snapshot.

        Args:
            positions: Dict of current positions
        """
        self.current_positions = positions

    def update_daily_pnl(self, pnl: float) -> None:
        """Update current daily P&L.

        Args:
            pnl: Current day's realized P&L
        """
        self.current_daily_pnl = pnl

    def update_account_balance(self, balance: float) -> None:
        """Update account balance.

        Args:
            balance: Current account balance
        """
        self.account_balance = balance

    def record_order_attempt(self) -> None:
        """Record that an order was submitted for rate limiting."""
        self.rate_limiter.record_order()

    def get_position_sizing_recommendation(
        self,
        option_premium: float,
        account_size: Optional[float] = None,
    ) -> int:
        """Get recommended contract quantity based on position sizing rules.

        Args:
            option_premium: Option premium per contract
            account_size: Account size (uses current if None)

        Returns:
            Recommended number of contracts to buy
        """
        if account_size is None:
            account_size = self.account_balance

        # Position sizing based on account risk
        risk_amount = self.risk_limits.get_position_risk_amount(account_size)
        contracts_by_risk = int(risk_amount / (option_premium * 100))

        # Limit by max contracts per option
        max_contracts = self.risk_limits.max_contracts_per_option
        recommended = min(contracts_by_risk, max_contracts)

        # Also check notional limit
        current_notional = self._get_current_notional()
        max_additional_notional = (
            self.risk_limits.max_notional_exposure - current_notional
        )
        max_by_notional = int(max_additional_notional / (option_premium * 100))
        recommended = min(recommended, max_by_notional)

        return max(1, recommended)  # Always return at least 1


class RiskCheckResult:
    """Result of a pre-trade risk check."""

    def __init__(
        self,
        is_valid: bool,
        errors: list[str],
        warnings: list[str] = None,
        recommendation: Optional[str] = None,
    ):
        """Initialize result.

        Args:
            is_valid: Whether order passed all checks
            errors: List of validation errors (blocks execution)
            warnings: List of warnings (informational)
            recommendation: Suggested action
        """
        self.is_valid = is_valid
        self.errors = errors
        self.warnings = warnings or []
        self.recommendation = recommendation

    def __str__(self) -> str:
        """Format result as readable string."""
        status = "PASS" if self.is_valid else "FAIL"
        msg = f"\nRisk Check Result: [{status}]\n"

        if self.errors:
            msg += "Errors:\n"
            for error in self.errors:
                msg += f"  - {error}\n"

        if self.warnings:
            msg += "Warnings:\n"
            for warning in self.warnings:
                msg += f"  - {warning}\n"

        if self.recommendation:
            msg += f"Recommendation: {self.recommendation}\n"

        return msg


if __name__ == "__main__":
    # Test pre-trade checks
    from config.options_risk_config import DEFAULT_RISK_LIMITS

    checker = PreTradeChecker(DEFAULT_RISK_LIMITS)

    # Test order
    test_order = OrderRequest(
        symbol="SPY",
        option_type="CALL",
        quantity=2,
        price=2.50,
        strike_price=500.0,
        expiration_date=datetime(2025, 12, 19),  # 10 days out
    )

    is_valid, errors = checker.check_order(test_order)
    print(f"Order Valid: {is_valid}")
    if errors:
        print("Validation Errors:")
        for error in errors:
            print(f"  - {error}")

    recommendation = checker.get_position_sizing_recommendation(2.50)
    print(f"\nRecommended position size: {recommendation} contracts")
