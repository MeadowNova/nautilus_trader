# Risk Management System - Moomoo Paper Trading

Complete risk control framework for the hybrid Moomoo options trading system. This system provides real-time position monitoring, pre-trade validation, and comprehensive risk reporting with R-multiple tracking.

## System Architecture

### Components

1. **Risk Configuration** (`config/options_risk_config.py`)
   - Centralized risk limits and constraints
   - Dataclass-based configuration with validation
   - Modular design for easy customization

2. **Pre-Trade Checks** (`scripts/pre_trade_checks.py`)
   - 10-point validation framework
   - Rate limiting (15 orders per 30 seconds)
   - Buying power verification
   - Expiration date validation

3. **Risk Monitor** (`scripts/risk_monitor.py`)
   - Real-time position tracking
   - Alert generation (Warning/Critical)
   - Greeks exposure calculation
   - Comprehensive reporting

4. **Risk Reporter** (`scripts/risk_reporter.py`)
   - R-multiple tracking for objective performance measurement
   - Trade statistics and expectancy calculation
   - Greeks estimation (Delta, Gamma, Theta)
   - Daily P&L tracking

5. **Integration Layer** (`scripts/integration_example.py`)
   - Unified risk management interface
   - Workflow orchestration
   - Data export capabilities

---

## Risk Configuration

### Default Limits (Paper Trading Account)

```python
from config.options_risk_config import DEFAULT_RISK_LIMITS

# Limits
max_contracts_per_option: 5           # Max contracts per single option
max_total_positions: 5                # Max concurrent positions
max_notional_exposure: $10,000        # Max total notional value
max_daily_loss: $1,000                # Daily loss limit
max_account_risk_percent: 1.0%        # Max risk per trade (% of account)
min_buying_power_buffer: 20%          # Keep 20% buying power in reserve

# Expiration constraints
min_days_to_expiration: 2 days        # Don't trade within 2 days of expiration
max_days_to_expiration: 60 days       # Don't trade options beyond 60 DTE

# Stop/Take Profit
stop_loss_percent: 50%                # Stop loss at 50% of premium paid
take_profit_percent: 200%             # Take profit target at 200% of premium

# Rate limiting
max_orders_per_30_seconds: 15         # Moomoo API rate limit
```

### Loading Custom Configuration

```python
from config.options_risk_config import load_risk_config

# Use defaults
config = load_risk_config()

# Or customize
from config.options_risk_config import RiskLimits

custom_config = RiskLimits(
    max_contracts_per_option=3,
    max_notional_exposure=5_000.00,
    max_daily_loss=500.00,
)
```

---

## Pre-Trade Validation

### 10-Point Validation Checklist

Every order is validated against these checks before submission:

1. **Rate Limiting** - Ensures compliance with Moomoo API limits
2. **Daily Loss Limit** - Prevents trading after hitting daily loss threshold
3. **Position Count** - Doesn't exceed max concurrent positions
4. **Notional Exposure** - Total exposure stays within limit
5. **Contract Limit** - Per-option contract limit not exceeded
6. **Expiration Date** - Must be between min/max DTE
7. **Buying Power** - Sufficient funds available for execution
8. **Account Risk** - Position risk doesn't exceed account risk limit
9. **Premium Width** - Minimum premium threshold met
10. **Premium Cap** - Individual contract premium below limit

### Example: Validating an Order

```python
from pre_trade_checks import OrderRequest, PreTradeChecker
from config.options_risk_config import DEFAULT_RISK_LIMITS
from datetime import datetime, timedelta

# Create checker
checker = PreTradeChecker(
    risk_limits=DEFAULT_RISK_LIMITS,
    account_balance=100_000.00
)

# Create order
order = OrderRequest(
    symbol="SPY",
    option_type="CALL",
    quantity=2,
    price=2.50,
    strike_price=500.0,
    expiration_date=datetime.now() + timedelta(days=10)
)

# Validate
is_valid, errors = checker.check_order(order)

if is_valid:
    print("Order passed all checks")
else:
    for error in errors:
        print(f"Validation failed: {error}")

# Get position sizing recommendation
recommended_qty = checker.get_position_sizing_recommendation(price=2.50)
print(f"Recommended position size: {recommended_qty} contracts")
```

---

## Risk Monitoring

### Real-Time Position Monitoring

```python
from risk_monitor import RiskMonitor
from config.options_risk_config import DEFAULT_RISK_LIMITS

# Initialize monitor
monitor = RiskMonitor(risk_limits=DEFAULT_RISK_LIMITS)

# Update positions from Moomoo
positions_data = {
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
}

monitor.update_positions(positions_data, account_balance=99_900.0)

# Check risk limits
alerts = monitor.check_risk_limits()

# Get portfolio metrics
metrics = monitor.get_portfolio_metrics()
print(f"Notional exposure: ${metrics.total_notional_exposure:,.2f}")
print(f"Utilization: {metrics.percent_of_notional_limit:.1f}%")
print(f"Net delta: {metrics.net_delta:.2f}")
print(f"Total P&L: ${metrics.total_pnl:,.2f}")

# Generate report
report = monitor.generate_risk_report()
print(report)

# Save report
monitor.save_report(report)
```

### Alert Types

- **WARNING**: Metric at 80%+ of limit
- **CRITICAL**: Metric at 95%+ of limit or limit exceeded

Alerts are generated for:
- Notional exposure
- Daily loss
- Position count
- Delta concentration
- Days to expiration

---

## Performance Tracking with R-Multiples

### R-Multiple Analysis

The system uses R-multiple analysis for objective, consistent performance measurement.

**R-Multiple = (Profit or Loss) / Risk Per Trade**

Where: Risk Per Trade = (Entry Price - Stop Loss) × Quantity × 100

Example:
- Entry: $2.50
- Stop Loss: $1.25 (50% of premium)
- Risk per contract: $1.25
- Exit: $3.50
- Profit per contract: $1.00
- R-Multiple: 1.00 / 1.25 = 0.80R

### Trade Tracking

```python
from risk_reporter import RMultipleTracker, TradeRecord
from datetime import datetime

# Initialize tracker
tracker = RMultipleTracker(account_size=100_000.0)

# Create trade record
trade = TradeRecord(
    order_id="ORD-001",
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
    status="CLOSED"
)

tracker.add_trade(trade)

# Get statistics
stats = tracker.get_trade_statistics()
print(f"Total trades: {stats['total_trades']}")
print(f"Win rate: {stats['win_rate_percent']:.1f}%")
print(f"Expectancy: ${stats['expectancy']:.2f} per trade")
print(f"Profit factor: {stats['profit_factor']:.2f}x")
print(f"Avg R-multiple: {stats['avg_r_multiple']:.2f}R")

# Export trades
tracker.export_trades_csv(Path("trades.csv"))
tracker.export_trades_json(Path("trades.json"))
```

### Trade Statistics Provided

- **Win Rate** - Percentage of winning trades
- **Expectancy** - Expected profit per trade: (Win% × Avg Win) - (Loss% × Avg Loss)
- **Profit Factor** - Ratio of total wins to total losses
- **Average R-Multiple** - Average return in R terms
- **Consecutive Streaks** - Longest win/loss streaks

---

## Greeks Exposure Estimation

### Delta Tracking

```python
from risk_reporter import GreeksCalculator

# Estimate delta for a position
delta = GreeksCalculator.estimate_delta(
    option_type="CALL",
    strike=500.0,
    spot=510.0,
    dte=10,
    volatility=0.25  # 25% IV
)
print(f"Delta: {delta:.2f}")  # 0.65 = 65 delta call

# Portfolio delta
net_delta = GreeksCalculator.calculate_portfolio_delta(positions)
print(f"Net portfolio delta: {net_delta:.2f}")
```

### Gamma & Theta

```python
# Estimate gamma
gamma = GreeksCalculator.estimate_gamma(
    strike=500.0,
    spot=510.0,
    dte=10,
    volatility=0.25
)

# Estimate theta (time decay per day)
theta = GreeksCalculator.estimate_theta(
    option_type="CALL",
    strike=500.0,
    spot=510.0,
    dte=10,
    premium=3.50,
    volatility=0.25
)
print(f"Theta decay per day: ${theta:.2f}")
```

---

## Daily P&L Tracking

```python
from risk_reporter import DailyPnLTracker

# Initialize tracker
daily_tracker = DailyPnLTracker()

# Record daily metrics
daily_tracker.record_pnl(
    realized_pnl=150.00,
    unrealized_pnl=200.00,
    positions_count=2,
    notes="Morning session: 2 winning trades"
)

# Get summary
summary = daily_tracker.get_daily_summary()
print(f"Date: {summary['date']}")
print(f"Realized P&L: ${summary['total_realized']:,.2f}")
print(f"Unrealized P&L: ${summary['total_unrealized']:,.2f}")
print(f"Total P&L: ${summary['total_pnl']:,.2f}")

# Export to CSV
daily_tracker.export_daily_pnl_csv(Path("daily_pnl.csv"))
```

---

## Integrated Workflow

### Complete Example

```python
from integration_example import IntegratedRiskManager
from pre_trade_checks import OrderRequest
from datetime import datetime, timedelta

# Initialize manager
manager = IntegratedRiskManager(account_id="MOOMOO-1252643")

# Step 1: Validate order
order = OrderRequest(
    symbol="SPY",
    option_type="CALL",
    quantity=2,
    price=2.50,
    strike_price=500.0,
    expiration_date=datetime.now() + timedelta(days=10)
)

is_valid, errors = manager.validate_order(order)

if is_valid:
    # Step 2: Execute order
    manager.execute_order(order, order_id="ORD-001")

    # Step 3: Update positions
    positions = {"SPY_500C": {...}}
    manager.update_positions_from_moomoo({"positions": positions, "balance": 99_900})

    # Step 4: Log closed trade
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
        exit_time=datetime.now().isoformat()
    )

    # Step 5: Generate reports
    report = manager.generate_daily_report()
    manager.save_daily_report(report)

    # Step 6: Export data
    csv_path, json_path = manager.export_trade_data()
```

---

## Moomoo API Integration Points

The risk system interfaces with Moomoo at these points:

1. **Pre-Order** - Validate before submitting
2. **Order Submission** - Rate limit enforcement
3. **Position Monitoring** - Query positions every 30 seconds
4. **Account Balance** - Query for buying power verification
5. **Trade Logging** - Log confirmed orders to local database

### Expected Moomoo Position Data Format

```python
{
    "positions": {
        "symbol_key": {
            "type": "CALL" | "PUT",
            "strike": float,
            "expiration": "YYYY-MM-DD",
            "quantity": int,
            "entry_price": float,
            "mark_price": float,
            "notional": float,
            "unrealized_pnl": float,
            "unrealized_pnl_pct": float,
            "dte": int
        }
    },
    "balance": float
}
```

---

## Logging and Reporting

### Log Files Generated

- **`risk_monitor.log`** - Real-time monitoring events
- **`positions.log`** - Position change history
- **`trades.log`** - All executed trades (JSON format)
- **`risk_report_TIMESTAMP.txt`** - Daily risk reports
- **`daily_report_YYYYMMDD.txt`** - Daily comprehensive report
- **`trades.csv`** - Trade data export
- **`trades.json`** - Trade data with statistics
- **`daily_pnl.csv`** - Daily P&L history

### Report Contents

**Risk Monitor Report includes:**
- Portfolio summary (positions, exposure, P&L)
- Account status (balance, buying power)
- Greeks exposure
- Active positions with mark-to-market
- Risk alerts

**Performance Report includes:**
- Trade statistics (win rate, expectancy)
- R-multiple analysis
- Consecutive streaks
- Daily P&L summary

---

## Best Practices

### Position Sizing

1. Start with account risk percentage (1% default)
2. Use Kelly criterion variant for dynamic sizing
3. Never exceed max contracts per option
4. Check notional exposure before entry
5. Get position sizing recommendation from checker

```python
# Position sizing formula
recommended_qty = checker.get_position_sizing_recommendation(
    option_premium=2.50,
    account_size=100_000.00
)
```

### Risk Discipline

1. Always check limits before trading
2. Set stops at 50% of premium paid
3. Take profits at 200% of premium
4. Never average down losing positions
5. Track all trades with R-multiples
6. Review daily reports consistently

### Monitoring Routine

1. Check positions every 30 seconds
2. Review risk alerts immediately
3. Monitor daily loss limit
4. Track expiration dates
5. Generate daily reports
6. Export trade data weekly

---

## Configuration Customization

To modify default limits, edit `/home/ajk/Nautilus/nautilus_trader/config/options_risk_config.py`:

```python
DEFAULT_RISK_LIMITS = RiskLimits(
    max_contracts_per_option=5,      # Increase to 10 for higher risk
    max_total_positions=5,            # Increase to 10 for more positions
    max_notional_exposure=10_000.00,  # Adjust based on account
    max_daily_loss=1_000.00,          # Adjust loss tolerance
    max_account_risk_percent=1.0,     # Typical: 0.5% to 2%
    min_days_to_expiration=2,         # Never decrease below 2
    account_size=100_000.00,          # Update with actual account size
)
```

---

## File Locations

- Configuration: `/home/ajk/Nautilus/nautilus_trader/config/options_risk_config.py`
- Pre-Trade Checks: `/home/ajk/Nautilus/nautilus_trader/scripts/pre_trade_checks.py`
- Risk Monitor: `/home/ajk/Nautilus/nautilus_trader/scripts/risk_monitor.py`
- Risk Reporter: `/home/ajk/Nautilus/nautilus_trader/scripts/risk_reporter.py`
- Integration: `/home/ajk/Nautilus/nautilus_trader/scripts/integration_example.py`
- Documentation: `/home/ajk/Nautilus/nautilus_trader/docs/RISK_MANAGEMENT.md`
- Logs: `/home/ajk/Nautilus/nautilus_trader/logs/`

---

## Testing the System

Run the integration example to test all components:

```bash
cd /home/ajk/Nautilus/nautilus_trader
python scripts/integration_example.py
```

This will:
1. Validate a sample order
2. Update mock positions
3. Generate risk report
4. Log a closed trade with R-multiple
5. Export trade data
6. Display all reports

---

## Troubleshooting

**Orders being rejected by pre-trade checks:**
- Check daily loss limit hasn't been exceeded
- Verify buying power is available
- Confirm expiration date is valid (2-60 DTE)
- Check order rate limiting

**High alerts appearing:**
- Monitor notional exposure against limit
- Check daily P&L against daily loss limit
- Review position count
- Analyze Greeks concentration

**Missing trades in reports:**
- Ensure trades are being logged via `log_trade_close()`
- Check log file permissions
- Verify export path is accessible
- Check for date/time sync issues

---

## Performance Expectations

With proper risk management:
- **Expected Win Rate**: 45-55% (sustainable with positive expectancy)
- **Profit Factor**: 1.5x-2.0x (wins 1.5-2x losses)
- **Expectancy**: Positive per trade
- **Max Drawdown**: Stay below 20% of account

Monitor these metrics weekly and adjust strategy as needed.
