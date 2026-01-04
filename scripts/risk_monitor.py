"""
Risk Monitor for Moomoo Paper Trading System

Real-time monitoring of positions, exposures, and risk metrics.
Alerts when limits are approached or exceeded.
"""

import json
import logging
import time
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional, Any
from dataclasses import asdict, dataclass

from config.options_risk_config import (
    RiskLimits,
    RiskAlert,
    RiskMonitorConfig,
    DEFAULT_RISK_LIMITS,
)


# Setup logging
def setup_logging() -> logging.Logger:
    """Setup logging for risk monitor."""
    log_dir = Path(RiskMonitorConfig.LOG_FILE_PATH).parent
    log_dir.mkdir(parents=True, exist_ok=True)

    logger = logging.getLogger("RiskMonitor")
    logger.setLevel(logging.INFO)

    # File handler
    fh = logging.FileHandler(RiskMonitorConfig.LOG_FILE_PATH)
    fh.setLevel(logging.INFO)

    # Console handler
    ch = logging.StreamHandler()
    ch.setLevel(logging.WARNING)

    # Formatter
    formatter = logging.Formatter(
        "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    )
    fh.setFormatter(formatter)
    ch.setFormatter(formatter)

    logger.addHandler(fh)
    logger.addHandler(ch)

    return logger


logger = setup_logging()


@dataclass
class PositionSnapshot:
    """Snapshot of a single option position."""

    symbol: str
    option_type: str  # 'CALL' or 'PUT'
    strike_price: float
    expiration_date: str  # ISO format: "2025-12-19"
    quantity: int
    entry_price: float  # Premium paid
    current_price: float  # Current mark price
    notional_value: float  # Current notional (price * qty * 100)
    unrealized_pnl: float
    unrealized_pnl_percent: float
    days_to_expiration: int
    timestamp: str  # ISO timestamp when captured

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return asdict(self)


@dataclass
class PortfolioMetrics:
    """Aggregated portfolio risk metrics."""

    total_positions: int
    total_notional_exposure: float
    total_unrealized_pnl: float
    daily_realized_pnl: float
    total_pnl: float
    account_balance: float
    buying_power_available: float
    net_delta: float  # Aggregated delta
    max_gamma: float  # Largest gamma exposure
    percent_of_notional_limit: float
    percent_of_daily_loss_limit: float
    timestamp: str

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return asdict(self)


class RiskMonitor:
    """Main risk monitoring system for options trading."""

    def __init__(
        self,
        risk_limits: RiskLimits = DEFAULT_RISK_LIMITS,
        account_id: str = "MOOMOO-1252643",
    ):
        """Initialize risk monitor.

        Args:
            risk_limits: Risk configuration
            account_id: Moomoo account ID
        """
        self.risk_limits = risk_limits
        self.account_id = account_id

        self.positions: Dict[str, PositionSnapshot] = {}
        self.alerts: List[RiskAlert] = []
        self.daily_pnl_log: List[Dict[str, Any]] = []
        self.trade_log: List[Dict[str, Any]] = []

        self.last_check_time = None
        self.daily_loss = 0.0
        self.realized_pnl = 0.0
        self.account_balance = risk_limits.account_size
        self.session_start_balance = self.account_balance
        self.session_start_time = datetime.now()

    def update_positions(
        self,
        positions: Dict[str, Dict[str, Any]],
        account_balance: float,
    ) -> None:
        """Update positions from Moomoo API.

        Args:
            positions: Dict of positions keyed by symbol
            account_balance: Current account balance
        """
        self.account_balance = account_balance
        self.positions.clear()

        for symbol, pos_data in positions.items():
            snapshot = PositionSnapshot(
                symbol=symbol,
                option_type=pos_data.get("type", "UNKNOWN"),
                strike_price=float(pos_data.get("strike", 0.0)),
                expiration_date=pos_data.get("expiration", ""),
                quantity=int(pos_data.get("quantity", 0)),
                entry_price=float(pos_data.get("entry_price", 0.0)),
                current_price=float(pos_data.get("mark_price", 0.0)),
                notional_value=float(pos_data.get("notional", 0.0)),
                unrealized_pnl=float(pos_data.get("unrealized_pnl", 0.0)),
                unrealized_pnl_percent=float(pos_data.get("unrealized_pnl_pct", 0.0)),
                days_to_expiration=int(pos_data.get("dte", 0)),
                timestamp=datetime.now().isoformat(),
            )
            self.positions[symbol] = snapshot

        self.last_check_time = datetime.now()
        self._check_risk_limits()

    def check_risk_limits(self) -> List[RiskAlert]:
        """Check all risk limits and generate alerts.

        Returns:
            List of RiskAlert objects
        """
        self.alerts.clear()

        metrics = self.get_portfolio_metrics()

        # Check 1: Notional exposure
        notional_percent = metrics.percent_of_notional_limit
        if notional_percent >= RiskMonitorConfig.CRITICAL_THRESHOLD_PERCENT:
            self.alerts.append(
                RiskAlert(
                    alert_type="CRITICAL",
                    metric="Notional Exposure",
                    current_value=metrics.total_notional_exposure,
                    limit_value=self.risk_limits.max_notional_exposure,
                    percent_of_limit=notional_percent,
                    message=f"Notional exposure at {notional_percent:.1f}% of limit",
                    timestamp=datetime.now(),
                )
            )
        elif notional_percent >= RiskMonitorConfig.WARNING_THRESHOLD_PERCENT:
            self.alerts.append(
                RiskAlert(
                    alert_type="WARNING",
                    metric="Notional Exposure",
                    current_value=metrics.total_notional_exposure,
                    limit_value=self.risk_limits.max_notional_exposure,
                    percent_of_limit=notional_percent,
                    message=f"Notional exposure at {notional_percent:.1f}% of limit",
                    timestamp=datetime.now(),
                )
            )

        # Check 2: Daily loss limit
        loss_percent = metrics.percent_of_daily_loss_limit
        if loss_percent >= 100:
            self.alerts.append(
                RiskAlert(
                    alert_type="CRITICAL",
                    metric="Daily Loss",
                    current_value=abs(self.daily_loss),
                    limit_value=self.risk_limits.max_daily_loss,
                    percent_of_limit=100.0,
                    message=f"Daily loss limit exceeded: ${abs(self.daily_loss):.2f}",
                    timestamp=datetime.now(),
                )
            )
        elif loss_percent >= RiskMonitorConfig.CRITICAL_THRESHOLD_PERCENT:
            self.alerts.append(
                RiskAlert(
                    alert_type="CRITICAL",
                    metric="Daily Loss",
                    current_value=abs(self.daily_loss),
                    limit_value=self.risk_limits.max_daily_loss,
                    percent_of_limit=loss_percent,
                    message=f"Daily loss at {loss_percent:.1f}% of limit",
                    timestamp=datetime.now(),
                )
            )
        elif loss_percent >= RiskMonitorConfig.WARNING_THRESHOLD_PERCENT:
            self.alerts.append(
                RiskAlert(
                    alert_type="WARNING",
                    metric="Daily Loss",
                    current_value=abs(self.daily_loss),
                    limit_value=self.risk_limits.max_daily_loss,
                    percent_of_limit=loss_percent,
                    message=f"Daily loss at {loss_percent:.1f}% of limit",
                    timestamp=datetime.now(),
                )
            )

        # Check 3: Position count
        if metrics.total_positions >= self.risk_limits.max_total_positions:
            self.alerts.append(
                RiskAlert(
                    alert_type="WARNING",
                    metric="Position Count",
                    current_value=float(metrics.total_positions),
                    limit_value=float(self.risk_limits.max_total_positions),
                    percent_of_limit=100.0,
                    message=f"Max positions reached: {metrics.total_positions}",
                    timestamp=datetime.now(),
                )
            )

        # Check 4: Delta concentration
        if abs(metrics.net_delta) > self.risk_limits.max_net_delta:
            self.alerts.append(
                RiskAlert(
                    alert_type="WARNING",
                    metric="Net Delta",
                    current_value=metrics.net_delta,
                    limit_value=self.risk_limits.max_net_delta,
                    percent_of_limit=(abs(metrics.net_delta) / self.risk_limits.max_net_delta)
                    * 100,
                    message=f"Net delta exposure high: {metrics.net_delta:.2f}",
                    timestamp=datetime.now(),
                )
            )

        # Check 5: Days to expiration
        for pos in self.positions.values():
            if pos.days_to_expiration <= self.risk_limits.min_days_to_expiration:
                self.alerts.append(
                    RiskAlert(
                        alert_type="WARNING",
                        metric="Expiration Risk",
                        current_value=float(pos.days_to_expiration),
                        limit_value=float(self.risk_limits.min_days_to_expiration),
                        percent_of_limit=0.0,
                        message=f"{pos.symbol} expiring in {pos.days_to_expiration} days",
                        timestamp=datetime.now(),
                    )
                )

        return self.alerts

    def _check_risk_limits(self) -> None:
        """Internal method to check limits and generate alerts."""
        self.check_risk_limits()

        # Log critical alerts
        for alert in self.alerts:
            if alert.alert_type == "CRITICAL":
                logger.critical(str(alert))
            elif alert.alert_type == "WARNING":
                logger.warning(str(alert))

    def get_portfolio_metrics(self) -> PortfolioMetrics:
        """Calculate and return aggregated portfolio metrics.

        Returns:
            PortfolioMetrics object
        """
        total_notional = 0.0
        total_unrealized_pnl = 0.0
        net_delta = 0.0
        max_gamma = 0.0

        for pos in self.positions.values():
            total_notional += pos.notional_value
            total_unrealized_pnl += pos.unrealized_pnl

            # Simple delta approximation (would need actual Greeks from Moomoo)
            delta_per_contract = 0.5  # Placeholder
            if pos.option_type == "PUT":
                net_delta -= pos.quantity * delta_per_contract * 100
            else:
                net_delta += pos.quantity * delta_per_contract * 100

            # Simple gamma placeholder
            max_gamma = max(max_gamma, 0.05)  # Placeholder

        # Calculate P&L
        self.daily_loss = min(0.0, total_unrealized_pnl)  # Track losses only
        percent_notional = (total_notional / self.risk_limits.max_notional_exposure) * 100
        percent_daily_loss = (
            (abs(self.daily_loss) / self.risk_limits.max_daily_loss) * 100
            if self.daily_loss < 0
            else 0.0
        )

        return PortfolioMetrics(
            total_positions=len(self.positions),
            total_notional_exposure=total_notional,
            total_unrealized_pnl=total_unrealized_pnl,
            daily_realized_pnl=self.realized_pnl,
            total_pnl=total_unrealized_pnl + self.realized_pnl,
            account_balance=self.account_balance,
            buying_power_available=self.account_balance
            * (1 - self.risk_limits.min_buying_power_buffer),
            net_delta=net_delta,
            max_gamma=max_gamma,
            percent_of_notional_limit=percent_notional,
            percent_of_daily_loss_limit=percent_daily_loss,
            timestamp=datetime.now().isoformat(),
        )

    def log_trade(
        self,
        symbol: str,
        option_type: str,
        strike: float,
        expiration: str,
        quantity: int,
        price: float,
        trade_type: str,  # 'BUY' or 'SELL'
        order_id: str,
    ) -> None:
        """Log a completed trade.

        Args:
            symbol: Underlying symbol
            option_type: 'CALL' or 'PUT'
            strike: Strike price
            expiration: Expiration date
            quantity: Number of contracts
            price: Premium paid/received
            trade_type: 'BUY' or 'SELL'
            order_id: Order ID from Moomoo
        """
        trade = {
            "timestamp": datetime.now().isoformat(),
            "order_id": order_id,
            "symbol": symbol,
            "option_type": option_type,
            "strike": strike,
            "expiration": expiration,
            "quantity": quantity,
            "price": price,
            "notional": quantity * price * 100,
            "trade_type": trade_type,
            "account_id": self.account_id,
        }

        self.trade_log.append(trade)

        # Log to file
        trade_log_path = Path(RiskMonitorConfig.TRADE_LOG_PATH)
        trade_log_path.parent.mkdir(parents=True, exist_ok=True)
        with open(trade_log_path, "a") as f:
            f.write(json.dumps(trade) + "\n")

        logger.info(f"Trade logged: {trade_type} {quantity} {symbol} ${price:.2f}")

    def generate_risk_report(self) -> str:
        """Generate a comprehensive risk report.

        Returns:
            Formatted risk report string
        """
        metrics = self.get_portfolio_metrics()
        alerts = self.check_risk_limits()

        report = f"""
{'='*70}
RISK MONITOR REPORT - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
Account: {self.account_id}
{'='*70}

PORTFOLIO SUMMARY
{'-'*70}
Total Positions:              {metrics.total_positions:>3}
Total Notional Exposure:      ${metrics.total_notional_exposure:>12,.2f}
  Limit:                      ${self.risk_limits.max_notional_exposure:>12,.2f}
  Utilization:                {metrics.percent_of_notional_limit:>12.1f}%

Daily P&L:
  Realized:                   ${metrics.daily_realized_pnl:>12,.2f}
  Unrealized:                 ${metrics.total_unrealized_pnl:>12,.2f}
  Total:                      ${metrics.total_pnl:>12,.2f}

Daily Loss Tracking:
  Current Daily Loss:         ${abs(self.daily_loss):>12,.2f}
  Daily Loss Limit:           ${self.risk_limits.max_daily_loss:>12,.2f}
  Utilization:                {metrics.percent_of_daily_loss_limit:>12.1f}%

ACCOUNT STATUS
{'-'*70}
Account Balance:              ${metrics.account_balance:>12,.2f}
Buying Power Available:       ${metrics.buying_power_available:>12,.2f}
Session Start Balance:        ${self.session_start_balance:>12,.2f}
Session P&L:                  ${metrics.total_pnl:>12,.2f}

GREEKS & EXPOSURE
{'-'*70}
Net Delta Exposure:           {metrics.net_delta:>14.2f}
  Limit:                      {self.risk_limits.max_net_delta:>14.2f}
Max Gamma:                    {metrics.max_gamma:>14.2f}
  Limit:                      {self.risk_limits.max_gamma_per_position:>14.2f}

ACTIVE POSITIONS
{'-'*70}
"""

        if self.positions:
            report += f"{'Symbol':<12} {'Type':<6} {'Strike':<10} {'DTE':<5} {'Qty':<5} {'Entry':<8} {'Current':<8} {'P&L':<10} {'P&L%':<8}\n"
            report += "-" * 82 + "\n"

            for pos in self.positions.values():
                report += (
                    f"{pos.symbol:<12} {pos.option_type:<6} "
                    f"${pos.strike_price:<9.2f} {pos.days_to_expiration:<5} "
                    f"{pos.quantity:<5} ${pos.entry_price:<7.2f} ${pos.current_price:<7.2f} "
                    f"${pos.unrealized_pnl:<9,.2f} {pos.unrealized_pnl_percent:<7.1f}%\n"
                )
        else:
            report += "No active positions\n"

        report += f"\n{'ALERTS':<70}\n{'-'*70}\n"

        if alerts:
            for alert in alerts:
                report += f"{alert}\n\n"
        else:
            report += "No active alerts\n"

        report += f"{'='*70}\n"

        return report

    def save_report(self, report: str) -> None:
        """Save report to file.

        Args:
            report: Report string to save
        """
        log_dir = Path(RiskMonitorConfig.LOG_FILE_PATH).parent
        log_dir.mkdir(parents=True, exist_ok=True)

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        report_path = log_dir / f"risk_report_{timestamp}.txt"

        with open(report_path, "w") as f:
            f.write(report)

        logger.info(f"Risk report saved: {report_path}")


def create_mock_positions() -> Dict[str, Dict[str, Any]]:
    """Create mock positions for testing.

    Returns:
        Dictionary of mock positions
    """
    return {
        "SPY_CALL_500": {
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
        },
        "QQQ_PUT_380": {
            "type": "PUT",
            "strike": 380.0,
            "expiration": "2025-12-26",
            "quantity": 1,
            "entry_price": 1.75,
            "mark_price": 1.50,
            "notional": 150.0,
            "unrealized_pnl": -25.0,
            "unrealized_pnl_pct": -14.3,
            "dte": 17,
        },
    }


if __name__ == "__main__":
    # Test the risk monitor
    monitor = RiskMonitor(DEFAULT_RISK_LIMITS)

    # Simulate positions
    mock_positions = create_mock_positions()
    monitor.update_positions(mock_positions, account_balance=100_000.0)

    # Generate and print report
    report = monitor.generate_risk_report()
    print(report)

    # Save report
    monitor.save_report(report)

    # Log a test trade
    monitor.log_trade(
        symbol="SPY",
        option_type="CALL",
        strike=500.0,
        expiration="2025-12-19",
        quantity=2,
        price=2.50,
        trade_type="BUY",
        order_id="ORD-001",
    )

    print("\nMock position update completed. Check logs directory for reports.")
