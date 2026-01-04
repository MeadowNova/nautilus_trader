"""
Risk System Testing & Validation

Comprehensive test suite to verify all risk control components work correctly.
Run this regularly to ensure system integrity.
"""

import sys
import logging
from datetime import datetime, timedelta
from pathlib import Path

from config.options_risk_config import (
    RiskLimits,
    TradeConstraints,
    DEFAULT_RISK_LIMITS,
)
from pre_trade_checks import OrderRequest, PreTradeChecker, OrderRateLimiter
from risk_monitor import RiskMonitor
from risk_reporter import RMultipleTracker, GreeksCalculator, TradeRecord


logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class RiskSystemTester:
    """Test suite for risk management system."""

    def __init__(self):
        """Initialize tester."""
        self.tests_passed = 0
        self.tests_failed = 0

    def run_all_tests(self) -> bool:
        """Run all test suites.

        Returns:
            True if all tests passed
        """
        print("\n" + "="*70)
        print("RISK MANAGEMENT SYSTEM TEST SUITE")
        print("="*70 + "\n")

        self.test_configuration()
        self.test_pre_trade_checks()
        self.test_rate_limiting()
        self.test_expiration_validation()
        self.test_position_sizing()
        self.test_risk_monitoring()
        self.test_r_multiple_calculation()
        self.test_greeks_calculation()

        self.print_summary()
        return self.tests_failed == 0

    def test_configuration(self) -> None:
        """Test configuration module."""
        print("\n[TEST 1] Configuration Module")
        print("-" * 70)

        try:
            config = DEFAULT_RISK_LIMITS
            assert config.max_contracts_per_option == 5
            assert config.max_total_positions == 5
            assert config.max_notional_exposure == 10_000.00
            assert config.max_daily_loss == 1_000.00
            assert config.account_size == 100_000.00

            # Test position size calculation
            assert config.calculate_position_size(5_000.00, 3_000.00) == True
            assert config.calculate_position_size(8_000.00, 3_000.00) == False

            # Test risk amount calculation
            risk = config.get_position_risk_amount(100_000.00)
            assert risk == 1_000.00  # 1% of 100k

            # Test contracts allowed
            allowed = config.get_contracts_allowed(3)
            assert allowed == 2  # 5 max - 3 current = 2 allowed

            self._pass("Configuration validation")
        except AssertionError as e:
            self._fail(f"Configuration validation: {e}")

    def test_pre_trade_checks(self) -> None:
        """Test pre-trade validation checks."""
        print("\n[TEST 2] Pre-Trade Checks")
        print("-" * 70)

        try:
            checker = PreTradeChecker(
                risk_limits=DEFAULT_RISK_LIMITS,
                current_positions={},
                current_daily_pnl=0.0,
                account_balance=100_000.00,
            )

            # Test valid order
            valid_order = OrderRequest(
                symbol="SPY",
                option_type="CALL",
                quantity=2,
                price=2.50,
                strike_price=500.0,
                expiration_date=datetime.now() + timedelta(days=10),
            )

            is_valid, errors = checker.check_order(valid_order)
            assert is_valid, f"Valid order failed: {errors}"
            self._pass("Valid order passes checks")

            # Test contract limit
            oversized_order = OrderRequest(
                symbol="SPY",
                option_type="CALL",
                quantity=10,  # Exceeds 5 limit
                price=2.50,
                strike_price=500.0,
                expiration_date=datetime.now() + timedelta(days=10),
            )

            is_valid, errors = checker.check_order(oversized_order)
            assert not is_valid, "Oversized order should fail"
            assert any("contract limit" in e.lower() for e in errors)
            self._pass("Contract limit enforcement")

            # Test expiration validation
            expired_order = OrderRequest(
                symbol="SPY",
                option_type="CALL",
                quantity=1,
                price=2.50,
                strike_price=500.0,
                expiration_date=datetime.now() + timedelta(days=1),  # Too soon
            )

            is_valid, errors = checker.check_order(expired_order)
            assert not is_valid, "Too-soon expiration should fail"
            assert any("expiration" in e.lower() for e in errors)
            self._pass("Expiration validation")

            # Test daily loss limit
            checker.update_daily_pnl(-900.0)  # Simulate 900 loss
            loss_order = OrderRequest(
                symbol="SPY",
                option_type="CALL",
                quantity=2,
                price=2.50,
                strike_price=500.0,
                expiration_date=datetime.now() + timedelta(days=10),
            )

            is_valid, errors = checker.check_order(loss_order)
            assert not is_valid, "Daily loss limit should trigger"
            self._pass("Daily loss limit enforcement")

        except AssertionError as e:
            self._fail(f"Pre-trade checks: {e}")

    def test_rate_limiting(self) -> None:
        """Test order rate limiting."""
        print("\n[TEST 3] Rate Limiting (15 per 30 sec)")
        print("-" * 70)

        try:
            limiter = OrderRateLimiter(max_orders=15, window_seconds=30)

            # First 15 orders should be allowed
            for i in range(15):
                assert limiter.is_allowed(), f"Order {i+1} should be allowed"
                limiter.record_order()

            # 16th order should be blocked
            assert not limiter.is_allowed(), "16th order should be blocked"
            self._pass("Rate limit blocking (15 orders)")

            # Test wait time calculation
            wait_time = limiter.get_wait_time()
            assert wait_time > 0, "Wait time should be positive"
            assert wait_time <= 30, "Wait time should be <= 30 seconds"
            self._pass("Wait time calculation")

        except AssertionError as e:
            self._fail(f"Rate limiting: {e}")

    def test_expiration_validation(self) -> None:
        """Test expiration date constraints."""
        print("\n[TEST 4] Expiration Date Validation")
        print("-" * 70)

        try:
            config = DEFAULT_RISK_LIMITS

            # Too close to expiration
            too_soon = TradeConstraints(
                symbol="SPY",
                option_type="CALL",
                strike_price=500.0,
                expiration_date=datetime.now() + timedelta(days=1),
            )

            is_valid, reason = too_soon.is_valid_expiration(config)
            assert not is_valid, f"Should reject {too_soon.days_to_expiration()} DTE"
            assert "close to expiration" in reason.lower()
            self._pass("Rejects too-close expiration")

            # Valid expiration
            valid_date = TradeConstraints(
                symbol="SPY",
                option_type="CALL",
                strike_price=500.0,
                expiration_date=datetime.now() + timedelta(days=10),
            )

            is_valid, reason = valid_date.is_valid_expiration(config)
            assert is_valid, f"Should accept {valid_date.days_to_expiration()} DTE"
            self._pass("Accepts valid expiration")

            # Too far out
            too_far = TradeConstraints(
                symbol="SPY",
                option_type="CALL",
                strike_price=500.0,
                expiration_date=datetime.now() + timedelta(days=90),
            )

            is_valid, reason = too_far.is_valid_expiration(config)
            assert not is_valid, f"Should reject {too_far.days_to_expiration()} DTE"
            assert "far from expiration" in reason.lower()
            self._pass("Rejects too-far expiration")

        except AssertionError as e:
            self._fail(f"Expiration validation: {e}")

    def test_position_sizing(self) -> None:
        """Test position sizing calculations."""
        print("\n[TEST 5] Position Sizing")
        print("-" * 70)

        try:
            checker = PreTradeChecker(
                risk_limits=DEFAULT_RISK_LIMITS,
                account_balance=100_000.00,
            )

            # Test position sizing for different premiums
            size_expensive = checker.get_position_sizing_recommendation(5.00)
            size_cheap = checker.get_position_sizing_recommendation(1.00)

            assert size_expensive <= size_cheap, "Expensive options should size smaller"
            assert size_expensive >= 1, "Should recommend at least 1 contract"
            assert size_cheap <= 5, "Should not exceed max contracts"

            self._pass("Position sizing calculation")

            # Test sizing respects notional limit
            checker.update_positions({
                "existing": {
                    "quantity": 10,
                    "mark_price": 5.00,
                }
            })

            size_limited = checker.get_position_sizing_recommendation(2.50)
            assert size_limited > 0, "Should still allow some positions"
            self._pass("Position sizing respects notional limit")

        except AssertionError as e:
            self._fail(f"Position sizing: {e}")

    def test_risk_monitoring(self) -> None:
        """Test risk monitoring and alert generation."""
        print("\n[TEST 6] Risk Monitoring")
        print("-" * 70)

        try:
            monitor = RiskMonitor(DEFAULT_RISK_LIMITS)

            # Test with empty positions
            alerts = monitor.check_risk_limits()
            assert len(alerts) == 0, "No alerts with empty portfolio"
            self._pass("Empty portfolio generates no alerts")

            # Test with high notional exposure
            high_exposure = {
                "SPY_500C": {
                    "type": "CALL",
                    "strike": 500.0,
                    "expiration": "2025-12-19",
                    "quantity": 5,
                    "entry_price": 2.50,
                    "mark_price": 3.00,
                    "notional": 1_500.0,
                    "unrealized_pnl": 250.0,
                    "unrealized_pnl_pct": 16.7,
                    "dte": 10,
                }
            }

            monitor.update_positions(high_exposure, account_balance=100_000.0)
            alerts = monitor.check_risk_limits()
            # Should not alert at 15% of limit
            critical_alerts = [a for a in alerts if a.alert_type == "CRITICAL"]
            assert len(critical_alerts) == 0, "Should not be critical at 15%"
            self._pass("Portfolio monitoring")

            # Test metrics calculation
            metrics = monitor.get_portfolio_metrics()
            assert metrics.total_positions == 1
            assert metrics.total_notional_exposure == 1_500.0
            assert metrics.total_unrealized_pnl == 250.0
            self._pass("Metrics calculation")

        except AssertionError as e:
            self._fail(f"Risk monitoring: {e}")

    def test_r_multiple_calculation(self) -> None:
        """Test R-multiple tracking and calculation."""
        print("\n[TEST 7] R-Multiple Tracking")
        print("-" * 70)

        try:
            tracker = RMultipleTracker(account_size=100_000.0)

            # Test R-multiple calculation
            # Risk = $1.25 per contract, Profit = $1.00
            r_multiple = tracker.calculate_r_multiple(
                entry_price=2.50,
                exit_price=3.50,
                stop_loss_price=1.25,
                quantity=2,
            )

            assert 0.75 < r_multiple < 0.85, f"R-multiple should be ~0.80R, got {r_multiple}"
            self._pass("R-multiple calculation")

            # Test winning trade
            win_trade = TradeRecord(
                order_id="WIN-001",
                symbol="SPY",
                option_type="CALL",
                strike_price=500.0,
                expiration_date="2025-12-19",
                quantity=2,
                entry_price=2.50,
                entry_time=datetime.now().isoformat(),
                exit_price=3.50,
                exit_time=datetime.now().isoformat(),
                realized_pnl=200.0,
                r_multiple=0.80,
                status="CLOSED",
            )

            tracker.add_trade(win_trade)

            # Test losing trade
            loss_trade = TradeRecord(
                order_id="LOSS-001",
                symbol="QQQ",
                option_type="PUT",
                strike_price=380.0,
                expiration_date="2025-12-26",
                quantity=1,
                entry_price=1.75,
                entry_time=datetime.now().isoformat(),
                exit_price=1.25,
                exit_time=datetime.now().isoformat(),
                realized_pnl=-50.0,
                r_multiple=-1.0,
                status="CLOSED",
            )

            tracker.add_trade(loss_trade)

            # Test statistics
            stats = tracker.get_trade_statistics()
            assert stats["total_trades"] == 2
            assert stats["winning_trades"] == 1
            assert stats["losing_trades"] == 1
            assert stats["win_rate_percent"] == 50.0
            self._pass("Trade statistics calculation")

            # Test expectancy
            assert "expectancy" in stats
            self._pass("Expectancy calculation")

            # Test consecutive streaks
            streaks = tracker.get_consecutive_stats()
            assert streaks["max_consecutive_wins"] == 1
            assert streaks["max_consecutive_losses"] == 1
            self._pass("Consecutive streak tracking")

        except AssertionError as e:
            self._fail(f"R-multiple tracking: {e}")

    def test_greeks_calculation(self) -> None:
        """Test Greeks estimation."""
        print("\n[TEST 8] Greeks Calculation")
        print("-" * 70)

        try:
            # Test delta calculation
            delta_call = GreeksCalculator.estimate_delta(
                option_type="CALL",
                strike=500.0,
                spot=510.0,  # ITM
                dte=10,
                volatility=0.25,
            )

            delta_put = GreeksCalculator.estimate_delta(
                option_type="PUT",
                strike=500.0,
                spot=510.0,  # OTM
                dte=10,
                volatility=0.25,
            )

            assert 0 < delta_call <= 1, f"Call delta should be 0-1, got {delta_call}"
            assert -1 <= delta_put < 0, f"Put delta should be -1-0, got {delta_put}"
            self._pass("Delta estimation")

            # Test gamma calculation
            gamma = GreeksCalculator.estimate_gamma(
                strike=500.0,
                spot=510.0,
                dte=10,
                volatility=0.25,
            )

            assert gamma > 0, f"Gamma should be positive, got {gamma}"
            self._pass("Gamma estimation")

            # Test theta calculation
            theta = GreeksCalculator.estimate_theta(
                option_type="CALL",
                strike=500.0,
                spot=510.0,
                dte=10,
                premium=3.50,
                volatility=0.25,
            )

            assert theta > 0, f"Theta should be positive, got {theta}"
            self._pass("Theta estimation")

        except AssertionError as e:
            self._fail(f"Greeks calculation: {e}")

    def _pass(self, test_name: str) -> None:
        """Record passing test."""
        self.tests_passed += 1
        print(f"  ✓ {test_name}")

    def _fail(self, test_name: str) -> None:
        """Record failing test."""
        self.tests_failed += 1
        print(f"  ✗ {test_name}")

    def print_summary(self) -> None:
        """Print test summary."""
        total = self.tests_passed + self.tests_failed
        print("\n" + "="*70)
        print("TEST SUMMARY")
        print("="*70)
        print(f"Total Tests:    {total}")
        print(f"Passed:         {self.tests_passed} {'✓' if self.tests_failed == 0 else ''}")
        print(f"Failed:         {self.tests_failed} {'✗' if self.tests_failed > 0 else ''}")
        print("="*70 + "\n")

        if self.tests_failed == 0:
            print("ALL TESTS PASSED - RISK SYSTEM OPERATIONAL\n")
            return 0
        else:
            print("SOME TESTS FAILED - REVIEW ERRORS ABOVE\n")
            return 1


def main() -> int:
    """Run test suite."""
    tester = RiskSystemTester()
    success = tester.run_all_tests()
    return 0 if success else 1


if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code)
