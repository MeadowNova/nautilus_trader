# Moomoo Integration Code Snippets

Ready-to-use code snippets for integrating the risk management system with Moomoo API.

---

## 1. Basic Setup

### Import All Components

```python
import asyncio
import logging
from datetime import datetime, timedelta
from pathlib import Path

from config.options_risk_config import DEFAULT_RISK_LIMITS
from pre_trade_checks import OrderRequest, PreTradeChecker
from risk_monitor import RiskMonitor
from risk_reporter import RMultipleTracker, DailyPnLTracker
from integration_example import IntegratedRiskManager

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)
```

### Initialize Risk Manager (Once at startup)

```python
class TradingBot:
    def __init__(self, account_id="MOOMOO-1252643"):
        self.account_id = account_id
        self.risk_manager = IntegratedRiskManager(account_id)
        self.running = True
        logger.info(f"Trading Bot initialized for {account_id}")

    async def startup(self):
        """Initialize system on startup"""
        # Start position monitor
        monitor_task = asyncio.create_task(self.monitor_positions())
        return monitor_task
```

---

## 2. Order Submission

### Validate and Submit Order

```python
async def place_option_trade(self, symbol: str, option_type: str,
                           quantity: int, strike: float,
                           expiration_date: datetime,
                           premium_bid: float, premium_ask: float) -> dict:
    """
    Place option trade with risk validation.

    Args:
        symbol: Underlying symbol (e.g., 'SPY')
        option_type: 'CALL' or 'PUT'
        quantity: Number of contracts
        strike: Strike price
        expiration_date: Expiration datetime
        premium_bid: Bid price
        premium_ask: Ask price

    Returns:
        Dict with order result
    """
    # Get mid-price
    mid_price = (premium_bid + premium_ask) / 2

    # Create order request
    order = OrderRequest(
        symbol=symbol,
        option_type=option_type,
        quantity=quantity,
        price=mid_price,
        strike_price=strike,
        expiration_date=expiration_date,
    )

    # Validate order
    is_valid, errors = self.risk_manager.validate_order(order)

    if not is_valid:
        logger.warning(f"Order validation failed for {symbol}:")
        for error in errors:
            logger.warning(f"  - {error}")
        return {
            "success": False,
            "order_id": None,
            "errors": errors
        }

    # Get position sizing recommendation
    recommended_qty = self.risk_manager.get_position_sizing_recommendation(mid_price)
    logger.info(f"Position sizing: {quantity} requested, {recommended_qty} recommended")

    # Submit to Moomoo
    try:
        order_id = await self.moomoo_api.place_order(
            symbol=symbol,
            option_type=option_type,
            quantity=quantity,
            price=mid_price,
            strike=strike,
            expiration=expiration_date.strftime("%Y-%m-%d")
        )

        # Execute order
        self.risk_manager.execute_order(order, order_id)

        logger.info(f"Order placed: {order_id} - {symbol} {option_type} {quantity}x @ ${mid_price:.2f}")

        return {
            "success": True,
            "order_id": order_id,
            "errors": []
        }

    except Exception as e:
        logger.error(f"Moomoo API error: {e}")
        return {
            "success": False,
            "order_id": None,
            "errors": [str(e)]
        }
```

### Quick Order with Pre-Trade Check

```python
async def quick_buy_call(self, symbol: str, strike: float,
                        expiration: datetime, contracts: int,
                        max_price: float) -> bool:
    """Quick call buy with validation."""
    result = await self.place_option_trade(
        symbol=symbol,
        option_type="CALL",
        quantity=contracts,
        strike=strike,
        expiration_date=expiration,
        premium_bid=max_price * 0.99,
        premium_ask=max_price
    )
    return result["success"]

async def quick_buy_put(self, symbol: str, strike: float,
                       expiration: datetime, contracts: int,
                       max_price: float) -> bool:
    """Quick put buy with validation."""
    result = await self.place_option_trade(
        symbol=symbol,
        option_type="PUT",
        quantity=contracts,
        strike=strike,
        expiration_date=expiration,
        premium_bid=max_price * 0.99,
        premium_ask=max_price
    )
    return result["success"]
```

---

## 3. Position Monitoring

### Background Position Monitor (Run Every 30 Seconds)

```python
async def monitor_positions(self):
    """Monitor positions and check risk limits continuously."""
    while self.running:
        try:
            # Get positions from Moomoo
            moomoo_data = await self.moomoo_api.get_account_data()

            # Update risk manager
            self.risk_manager.update_positions_from_moomoo(moomoo_data)

            # Check for critical alerts
            alerts = self.risk_manager.risk_monitor.alerts

            for alert in alerts:
                if alert.alert_type == "CRITICAL":
                    await self.handle_critical_alert(alert)
                elif alert.alert_type == "WARNING":
                    logger.warning(f"Risk Alert: {alert}")

        except Exception as e:
            logger.error(f"Position monitoring error: {e}")

        # Wait 30 seconds before next check
        await asyncio.sleep(30)

async def handle_critical_alert(self, alert):
    """Handle critical risk alerts."""
    logger.critical(f"CRITICAL ALERT: {alert}")

    # Check if daily loss limit hit
    if "daily loss" in alert.metric.lower():
        logger.critical("STOPPING ALL NEW TRADES - DAILY LOSS LIMIT EXCEEDED")
        await self.stop_new_trades()

    # Notify operator
    await self.notify_operator(alert)
```

### Get Current Position Summary

```python
def get_position_summary(self) -> dict:
    """Get current position summary."""
    metrics = self.risk_manager.risk_monitor.get_portfolio_metrics()

    return {
        "positions": len(metrics.total_positions),
        "notional_exposure": f"${metrics.total_notional_exposure:,.2f}",
        "notional_limit": f"${DEFAULT_RISK_LIMITS.max_notional_exposure:,.2f}",
        "notional_pct": f"{metrics.percent_of_notional_limit:.1f}%",
        "unrealized_pnl": f"${metrics.total_unrealized_pnl:,.2f}",
        "daily_pnl": f"${metrics.daily_realized_pnl:,.2f}",
        "account_balance": f"${metrics.account_balance:,.2f}",
        "buying_power": f"${metrics.buying_power_available:,.2f}",
        "net_delta": f"{metrics.net_delta:.2f}",
    }

def display_position_summary(self):
    """Display position summary to console."""
    summary = self.get_position_summary()
    print("\n" + "="*70)
    print("POSITION SUMMARY")
    print("="*70)
    for key, value in summary.items():
        print(f"{key:.<30} {value:>15}")
    print("="*70 + "\n")
```

---

## 4. Trade Closing

### Close Position and Log Trade

```python
async def close_position(self, symbol: str, option_type: str,
                        strike: float, quantity: int,
                        exit_price: float,
                        entry_order_id: str, entry_price: float,
                        entry_time: datetime) -> dict:
    """
    Close option position and log trade.

    Args:
        symbol: Underlying symbol
        option_type: 'CALL' or 'PUT'
        strike: Strike price
        quantity: Number of contracts
        exit_price: Exit premium price
        entry_order_id: Original entry order ID
        entry_price: Entry premium price
        entry_time: Entry timestamp

    Returns:
        Dict with close result
    """
    try:
        # Submit exit order to Moomoo
        exit_order_id = await self.moomoo_api.place_order(
            symbol=symbol,
            option_type=option_type,
            quantity=quantity,
            price=exit_price,
            order_type="SELL"
        )

        exit_time = datetime.now()
        realized_pnl = (exit_price - entry_price) * quantity * 100.0

        # Log closed trade with R-multiple tracking
        self.risk_manager.log_trade_close(
            order_id=entry_order_id,
            symbol=symbol,
            option_type=option_type,
            strike=strike,
            expiration=None,  # You'd get this from original entry
            quantity=quantity,
            entry_price=entry_price,
            exit_price=exit_price,
            entry_time=entry_time.isoformat(),
            exit_time=exit_time.isoformat()
        )

        logger.info(
            f"Position closed: {symbol} {option_type} {quantity}x - "
            f"P&L: ${realized_pnl:,.2f}"
        )

        return {
            "success": True,
            "exit_order_id": exit_order_id,
            "realized_pnl": realized_pnl
        }

    except Exception as e:
        logger.error(f"Error closing position: {e}")
        return {
            "success": False,
            "exit_order_id": None,
            "error": str(e)
        }
```

### Auto-Close at Profit Target

```python
async def check_and_close_profit_targets(self):
    """Check if any positions hit profit targets and close them."""
    positions = self.risk_manager.risk_monitor.positions

    for symbol, position in positions.items():
        # Get entry price (from your tracking)
        entry_price = position.entry_price
        current_price = position.current_price

        # Calculate return
        pnl_per_contract = current_price - entry_price
        pnl_pct = (pnl_per_contract / entry_price) * 100

        # Take profit at 200% of premium
        take_profit_price = entry_price * 3.0  # 200% profit

        if current_price >= take_profit_price:
            logger.info(f"PROFIT TARGET HIT: {symbol} at {pnl_pct:.0f}%")
            await self.close_position(
                symbol=symbol,
                option_type=position.option_type,
                strike=position.strike_price,
                quantity=position.quantity,
                exit_price=current_price,
                entry_order_id="XXX",  # From your tracking
                entry_price=entry_price,
                entry_time=datetime.now()  # From your tracking
            )
```

### Auto-Close at Stop Loss

```python
async def check_and_close_stops(self):
    """Check if any positions hit stop losses and close them."""
    positions = self.risk_manager.risk_monitor.positions

    for symbol, position in positions.items():
        # Get entry price
        entry_price = position.entry_price
        current_price = position.current_price

        # Stop loss at 50% of premium
        stop_loss_price = entry_price * 0.5

        if current_price <= stop_loss_price:
            logger.warning(f"STOP LOSS HIT: {symbol} at ${current_price:.2f}")
            await self.close_position(
                symbol=symbol,
                option_type=position.option_type,
                strike=position.strike_price,
                quantity=position.quantity,
                exit_price=current_price,
                entry_order_id="XXX",  # From your tracking
                entry_price=entry_price,
                entry_time=datetime.now()  # From your tracking
            )
```

---

## 5. Daily Reporting

### Generate and Save Daily Report

```python
async def end_of_day_procedures(self):
    """Run end-of-day reporting and analysis."""
    logger.info("Starting end-of-day procedures...")

    # Generate comprehensive report
    report = self.risk_manager.generate_daily_report()
    print("\n" + report)

    # Save report
    report_path = self.risk_manager.save_daily_report(report)
    logger.info(f"Daily report saved to: {report_path}")

    # Export trade data
    csv_path, json_path = self.risk_manager.export_trade_data()
    logger.info(f"Trade data exported to:")
    logger.info(f"  CSV: {csv_path}")
    logger.info(f"  JSON: {json_path}")

    # Close positions near expiration
    await self.close_near_expiration_positions()

    logger.info("End-of-day procedures complete")

async def close_near_expiration_positions(self):
    """Close positions with less than 3 days to expiration."""
    positions = self.risk_manager.risk_monitor.positions

    for symbol, position in positions.items():
        if position.days_to_expiration <= 3:
            logger.info(f"Closing {symbol} - {position.days_to_expiration} DTE")
            await self.close_position(
                symbol=symbol,
                option_type=position.option_type,
                strike=position.strike_price,
                quantity=position.quantity,
                exit_price=position.current_price,
                entry_order_id="XXX",
                entry_price=position.entry_price,
                entry_time=datetime.now()
            )
```

### Weekly Performance Review

```python
def weekly_performance_review(self):
    """Generate weekly performance review."""
    stats = self.risk_manager.r_tracker.get_trade_statistics()
    streaks = self.risk_manager.r_tracker.get_consecutive_stats()

    review = f"""
{'='*70}
WEEKLY PERFORMANCE REVIEW
{datetime.now().strftime('%Y-%m-%d')}
{'='*70}

TRADE STATISTICS
{'='*70}
Total Trades:              {stats['total_trades']:.0f}
Winning Trades:            {stats['winning_trades']:.0f}
Losing Trades:             {stats['losing_trades']:.0f}
Win Rate:                  {stats['win_rate_percent']:.1f}%

P&L ANALYSIS
{'='*70}
Total P&L:                 ${stats['total_pnl']:,.2f}
Average P&L:               ${stats['average_pnl']:,.2f}
Best Trade:                ${stats['max_win']:,.2f}
Worst Trade:               ${stats['max_loss']:,.2f}
Average Win:               ${stats['avg_win']:,.2f}
Average Loss:              ${stats['avg_loss']:,.2f}

PERFORMANCE METRICS
{'='*70}
Expectancy per Trade:      ${stats['expectancy']:,.2f}
Profit Factor:             {stats['profit_factor']:.2f}x
Average R-Multiple:        {stats['avg_r_multiple']:.2f}R
Max Consecutive Wins:      {streaks['max_consecutive_wins']}
Max Consecutive Losses:    {streaks['max_consecutive_losses']}

{'='*70}
"""
    print(review)
    return review
```

---

## 6. Moomoo API Wrapper Template

### Create Moomoo API Wrapper Class

```python
class MoomooAPI:
    """Wrapper for Moomoo trading API."""

    def __init__(self, account_id: str):
        self.account_id = account_id
        # Initialize your Moomoo API client here
        # self.client = moomoo_client(account_id)
        logger.info(f"MoomooAPI initialized for {account_id}")

    async def get_account_data(self) -> dict:
        """
        Get current account data from Moomoo.

        Returns:
            Dict with positions and balance
        """
        # Call your Moomoo API
        # This should return data in the expected format
        return {
            "positions": {
                # Position data here
            },
            "balance": 0.0  # Account balance
        }

    async def place_order(self, symbol: str, option_type: str,
                         quantity: int, price: float,
                         strike: float = None,
                         expiration: str = None,
                         order_type: str = "BUY") -> str:
        """
        Place option order on Moomoo.

        Args:
            symbol: Underlying symbol
            option_type: 'CALL' or 'PUT'
            quantity: Number of contracts
            price: Limit price
            strike: Strike price (for new orders)
            expiration: Expiration date (for new orders)
            order_type: 'BUY' or 'SELL'

        Returns:
            Order ID
        """
        # Call your Moomoo API
        # return order_id
        pass

    async def cancel_order(self, order_id: str) -> bool:
        """Cancel order by ID."""
        # Call your Moomoo API
        # return success
        pass

    async def get_position(self, symbol: str) -> dict:
        """Get specific position details."""
        # Call your Moomoo API
        # return position_data
        pass

    async def get_quote(self, symbol: str) -> dict:
        """Get current quote for symbol."""
        # Call your Moomoo API
        # return quote_data
        pass
```

### Initialize Moomoo and Start Bot

```python
async def main():
    """Main entry point."""
    # Initialize Moomoo API
    moomoo = MoomooAPI(account_id="MOOMOO-1252643")

    # Create trading bot
    bot = TradingBot(account_id="MOOMOO-1252643")
    bot.moomoo_api = moomoo

    # Start background tasks
    monitor_task = await bot.startup()

    try:
        # Keep bot running
        while bot.running:
            await asyncio.sleep(1)

    except KeyboardInterrupt:
        logger.info("Shutting down...")
        bot.running = False
        monitor_task.cancel()

        # Run end-of-day procedures
        await bot.end_of_day_procedures()

if __name__ == "__main__":
    asyncio.run(main())
```

---

## 7. Configuration Customization

### Adjust Risk Limits at Runtime

```python
def adjust_risk_limits(daily_loss_limit: float = None,
                      max_notional: float = None,
                      max_contracts: int = None):
    """Adjust risk limits dynamically."""
    from config.options_risk_config import RiskLimits

    config = DEFAULT_RISK_LIMITS

    if daily_loss_limit:
        config.max_daily_loss = daily_loss_limit
        logger.info(f"Daily loss limit updated to ${daily_loss_limit:,.2f}")

    if max_notional:
        config.max_notional_exposure = max_notional
        logger.info(f"Max notional updated to ${max_notional:,.2f}")

    if max_contracts:
        config.max_contracts_per_option = max_contracts
        logger.info(f"Max contracts updated to {max_contracts}")

    return config
```

### Reduce Risk After Losses

```python
def reduce_risk_after_loss(current_daily_pnl: float):
    """Reduce risk limits if experiencing losses."""
    loss = abs(current_daily_pnl)

    if loss > 500:  # 50% of daily limit
        logger.warning("Large loss detected - reducing risk limits")
        adjust_risk_limits(
            daily_loss_limit=500.0,      # Reduce from 1000
            max_notional=5_000.0,        # Reduce from 10000
            max_contracts=2               # Reduce from 5
        )

    elif loss > 250:  # 25% of daily limit
        logger.warning("Moderate loss detected - tightening stops")
        # Recommend closing smallest losing position
```

---

## 8. Error Handling

### Graceful Error Handling Template

```python
async def safe_place_order(self, *args, **kwargs) -> dict:
    """Place order with comprehensive error handling."""
    try:
        return await self.place_option_trade(*args, **kwargs)

    except ValueError as e:
        logger.error(f"Validation error: {e}")
        return {"success": False, "error": str(e)}

    except ConnectionError as e:
        logger.error(f"Connection error: {e}")
        await self.notify_operator(f"Connection lost: {e}")
        return {"success": False, "error": "Connection error"}

    except Exception as e:
        logger.error(f"Unexpected error: {e}")
        await self.notify_operator(f"Unexpected error: {e}")
        return {"success": False, "error": str(e)}

async def notify_operator(self, message: str):
    """Send notification to operator."""
    logger.critical(f"OPERATOR ALERT: {message}")
    # Implement your notification method here
    # email, Slack, SMS, etc.
```

---

## 9. Logging Configuration

### Setup Comprehensive Logging

```python
def setup_logging(log_dir: Path = None):
    """Setup logging for trading system."""
    if log_dir is None:
        log_dir = Path("/home/ajk/Nautilus/nautilus_trader/logs")

    log_dir.mkdir(parents=True, exist_ok=True)

    # Root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(logging.DEBUG)

    # File handler (all logs)
    fh = logging.FileHandler(log_dir / "trading_system.log")
    fh.setLevel(logging.DEBUG)

    # Console handler (warnings and above)
    ch = logging.StreamHandler()
    ch.setLevel(logging.WARNING)

    # Formatter
    formatter = logging.Formatter(
        "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    )
    fh.setFormatter(formatter)
    ch.setFormatter(formatter)

    root_logger.addHandler(fh)
    root_logger.addHandler(ch)

    return root_logger
```

---

## 10. Testing Integration

### Integration Test Template

```python
async def test_integration():
    """Test complete integration."""
    logger.info("Starting integration test...")

    # Test 1: Risk limits
    logger.info("Test 1: Risk configuration")
    config = DEFAULT_RISK_LIMITS
    assert config.max_daily_loss == 1_000.00
    logger.info("  PASS - Risk limits correct")

    # Test 2: Order validation
    logger.info("Test 2: Order validation")
    bot = TradingBot()
    order = OrderRequest(
        symbol="SPY",
        option_type="CALL",
        quantity=2,
        price=2.50,
        strike_price=500.0,
        expiration_date=datetime.now() + timedelta(days=10)
    )
    is_valid, errors = bot.risk_manager.validate_order(order)
    assert is_valid
    logger.info("  PASS - Order validation working")

    # Test 3: Report generation
    logger.info("Test 3: Report generation")
    report = bot.risk_manager.generate_daily_report()
    assert len(report) > 0
    logger.info("  PASS - Report generation working")

    logger.info("Integration test complete - all tests passed")

if __name__ == "__main__":
    asyncio.run(test_integration())
```

---

## Quick Integration Summary

1. **Copy snippets** into your trading application
2. **Update Moomoo API** calls in MoomooAPI class
3. **Initialize** TradingBot with your account ID
4. **Start** with `asyncio.run(main())`
5. **Monitor** position updates every 30 seconds
6. **Place trades** using `place_option_trade()`
7. **Close positions** using `close_position()`
8. **Review** daily with end-of-day procedures

---

## Important Notes

- All paths are absolute (`/home/ajk/Nautilus/...`)
- Risk validation runs on every order
- Positions monitored every 30 seconds
- Daily reports saved automatically
- Trade data exported as CSV and JSON
- All trades tracked with R-multiples
- Alerts logged for manual review

Ready to integrate with your Moomoo platform!
