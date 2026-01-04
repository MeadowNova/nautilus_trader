"""
Integration Example: Complete Risk Management Workflow

This example demonstrates how to integrate all risk management components
for the Moomoo paper trading system.
"""

import logging
from datetime import datetime, timedelta
from pathlib import Path

from config.options_risk_config import DEFAULT_RISK_LIMITS, RiskMonitorConfig
from pre_trade_checks import OrderRequest, PreTradeChecker
from risk_monitor import RiskMonitor
from risk_reporter import RMultipleTracker, DailyPnLTracker, TradeRecord


# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


class IntegratedRiskManager:
    """Unified risk management system combining all components."""

    def __init__(self, account_id: str = "MOOMOO-1252643"):
        """Initialize integrated risk manager.

        Args:
            account_id: Moomoo account ID
        """
        self.account_id = account_id
        self.risk_limits = DEFAULT_RISK_LIMITS

        # Initialize components
        self.pre_trade_checker = PreTradeChecker(
            risk_limits=self.risk_limits,
            account_balance=self.risk_limits.account_size,
        )
        self.risk_monitor = RiskMonitor(
            risk_limits=self.risk_limits,
            account_id=account_id,
        )
        self.r_tracker = RMultipleTracker(
            account_size=self.risk_limits.account_size
        )
        self.daily_tracker = DailyPnLTracker()

        logger.info(f"Risk Manager initialized for account {account_id}")

    def validate_order(self, order: OrderRequest) -> tuple[bool, list[str]]:
        """Validate order before submission.

        Args:
            order: OrderRequest to validate

        Returns:
            Tuple of (is_valid, error_list)
        """
        is_valid, errors = self.pre_trade_checker.check_order(order)

        if is_valid:
            logger.info(f"Order PASSED all checks: {order.symbol} {order.quantity}x")
        else:
            logger.warning(f"Order FAILED validation: {order.symbol}")
            for error in errors:
                logger.warning(f"  - {error}")

        return is_valid, errors

    def execute_order(self, order: OrderRequest, order_id: str) -> bool:
        """Execute a validated order.

        Args:
            order: OrderRequest to execute
            order_id: Order ID from execution

        Returns:
            True if execution successful
        """
        # This is where you would call Moomoo API
        # For now, we just simulate and log
        logger.info(
            f"EXECUTING ORDER: {order_id} - {order.symbol} {order.option_type} "
            f"{order.quantity} contracts @ ${order.price:.2f}"
        )

        self.pre_trade_checker.record_order_attempt()

        # Log the trade
        self.risk_monitor.log_trade(
            symbol=order.symbol,
            option_type=order.option_type,
            strike=order.strike_price,
            expiration=order.expiration_date.strftime("%Y-%m-%d"),
            quantity=order.quantity,
            price=order.price,
            trade_type="BUY",
            order_id=order_id,
        )

        return True

    def update_positions_from_moomoo(self, positions_data: dict) -> None:
        """Update position data from Moomoo API.

        Args:
            positions_data: Current positions from Moomoo
        """
        # Extract account balance from API response
        account_balance = positions_data.get("balance", self.risk_limits.account_size)

        # Update all components
        self.pre_trade_checker.update_account_balance(account_balance)
        self.risk_monitor.update_positions(positions_data.get("positions", {}), account_balance)

        logger.info(f"Positions updated: {len(positions_data.get('positions', {}))} open")

    def log_trade_close(
        self,
        order_id: str,
        symbol: str,
        option_type: str,
        strike: float,
        expiration: str,
        quantity: int,
        entry_price: float,
        exit_price: float,
        entry_time: str,
        exit_time: str,
    ) -> None:
        """Log a closed trade with performance metrics.

        Args:
            order_id: Original order ID
            symbol: Underlying symbol
            option_type: 'CALL' or 'PUT'
            strike: Strike price
            expiration: Expiration date
            quantity: Number of contracts
            entry_price: Entry premium
            exit_price: Exit premium
            entry_time: Entry timestamp (ISO)
            exit_time: Exit timestamp (ISO)
        """
        # Calculate P&L and R-multiple
        realized_pnl = (exit_price - entry_price) * quantity * 100.0
        stop_loss = entry_price * (1 - self.risk_limits.stop_loss_percent / 100.0)

        r_multiple = self.r_tracker.calculate_r_multiple(
            entry_price=entry_price,
            exit_price=exit_price,
            stop_loss_price=stop_loss,
            quantity=quantity,
        )

        # Create trade record
        trade = TradeRecord(
            order_id=order_id,
            symbol=symbol,
            option_type=option_type,
            strike_price=strike,
            expiration_date=expiration,
            quantity=quantity,
            entry_price=entry_price,
            entry_time=entry_time,
            exit_price=exit_price,
            exit_time=exit_time,
            realized_pnl=realized_pnl,
            r_multiple=r_multiple,
            stop_loss_level=stop_loss,
            take_profit_level=entry_price * (1 + self.risk_limits.take_profit_percent / 100.0),
            status="CLOSED",
        )

        self.r_tracker.add_trade(trade)

        logger.info(
            f"Trade closed: {symbol} {option_type} {quantity}x - "
            f"P&L: ${realized_pnl:,.2f} ({r_multiple:.2f}R)"
        )

    def generate_daily_report(self) -> str:
        """Generate comprehensive daily risk report.

        Returns:
            Formatted report string
        """
        # Get risk monitor report
        monitor_report = self.risk_monitor.generate_risk_report()

        # Get performance report
        from risk_reporter import generate_performance_report
        perf_report = generate_performance_report(self.r_tracker, self.daily_tracker)

        return f"{monitor_report}\n{perf_report}"

    def save_daily_report(self, report: str) -> Path:
        """Save daily report to file.

        Args:
            report: Report string

        Returns:
            Path to saved report
        """
        log_dir = Path(RiskMonitorConfig.LOG_FILE_PATH).parent
        log_dir.mkdir(parents=True, exist_ok=True)

        timestamp = datetime.now().strftime("%Y%m%d")
        report_path = log_dir / f"daily_report_{timestamp}.txt"

        with open(report_path, "w") as f:
            f.write(report)

        logger.info(f"Daily report saved: {report_path}")
        return report_path

    def export_trade_data(self) -> tuple[Path, Path]:
        """Export trade data to CSV and JSON.

        Returns:
            Tuple of (csv_path, json_path)
        """
        log_dir = Path(RiskMonitorConfig.LOG_FILE_PATH).parent
        csv_path = log_dir / "trades.csv"
        json_path = log_dir / "trades.json"

        self.r_tracker.export_trades_csv(csv_path)
        self.r_tracker.export_trades_json(json_path)

        return csv_path, json_path

    def get_position_sizing_recommendation(
        self,
        option_premium: float,
    ) -> int:
        """Get recommended position size for a new trade.

        Args:
            option_premium: Option premium per contract

        Returns:
            Recommended number of contracts
        """
        recommendation = self.pre_trade_checker.get_position_sizing_recommendation(
            option_premium
        )
        logger.info(f"Position sizing recommendation: {recommendation} contracts")
        return recommendation


def example_workflow():
    """Demonstrate complete risk management workflow."""

    print("\n" + "="*70)
    print("MOOMOO PAPER TRADING - INTEGRATED RISK MANAGEMENT EXAMPLE")
    print("="*70 + "\n")

    # Initialize risk manager
    manager = IntegratedRiskManager()

    # Example 1: Validate a new order
    print("\n[STEP 1] Validating new order...")
    print("-" * 70)

    order = OrderRequest(
        symbol="SPY",
        option_type="CALL",
        quantity=2,
        price=2.50,
        strike_price=500.0,
        expiration_date=datetime.now() + timedelta(days=10),
    )

    is_valid, errors = manager.validate_order(order)

    if is_valid:
        print("✓ Order validation PASSED")
        print(f"\nOrder Details:")
        print(f"  Symbol: {order.symbol} {order.option_type}")
        print(f"  Quantity: {order.quantity} contracts")
        print(f"  Premium: ${order.price:.2f} per contract")
        print(f"  Notional: ${order.notional_value:,.2f}")
        print(f"  Max Risk: ${order.max_loss:,.2f}")

        # Get position sizing recommendation
        recommendation = manager.get_position_sizing_recommendation(order.price)
        print(f"\nPosition Sizing:")
        print(f"  Recommended: {recommendation} contracts")
        print(f"  Max Allowed: {DEFAULT_RISK_LIMITS.max_contracts_per_option} contracts")

    else:
        print("✗ Order validation FAILED")
        for error in errors:
            print(f"  ✗ {error}")

    # Example 2: Simulate position updates
    print("\n[STEP 2] Updating positions from Moomoo...")
    print("-" * 70)

    mock_positions = {
        "positions": {
            "SPY_500C": {
                "type": "CALL",
                "strike": 500.0,
                "expiration": "2025-12-19",
                "quantity": 2,
                "entry_price": 2.50,
                "mark_price": 3.00,
                "notional": 600.0,
                "unrealized_pnl": 100.0,
                "unrealized_pnl_pct": 40.0,
                "dte": 10,
            }
        },
        "balance": 99_900.0,
    }

    manager.update_positions_from_moomoo(mock_positions)
    print("✓ Positions updated")

    # Example 3: Generate daily report
    print("\n[STEP 3] Generating daily risk report...")
    print("-" * 70)

    report = manager.generate_daily_report()
    print(report)

    # Save report
    manager.save_daily_report(report)

    # Example 4: Log a closed trade
    print("\n[STEP 4] Logging closed trade with R-multiple tracking...")
    print("-" * 70)

    manager.log_trade_close(
        order_id="ORD-001",
        symbol="SPY",
        option_type="CALL",
        strike=500.0,
        expiration="2025-12-19",
        quantity=2,
        entry_price=2.50,
        exit_price=3.50,
        entry_time=datetime.now().isoformat(),
        exit_time=datetime.now().isoformat(),
    )

    print("✓ Trade logged with R-multiple analysis")

    # Example 5: Export data
    print("\n[STEP 5] Exporting trade data...")
    print("-" * 70)

    csv_path, json_path = manager.export_trade_data()
    print(f"✓ CSV export: {csv_path}")
    print(f"✓ JSON export: {json_path}")

    print("\n" + "="*70)
    print("WORKFLOW COMPLETE")
    print("="*70 + "\n")


if __name__ == "__main__":
    example_workflow()
