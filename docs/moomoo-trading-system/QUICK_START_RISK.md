# Risk Management Quick Start Guide

## 5-Minute Setup

### 1. Import Risk Components

```python
from config.options_risk_config import DEFAULT_RISK_LIMITS
from pre_trade_checks import OrderRequest, PreTradeChecker
from risk_monitor import RiskMonitor
from risk_reporter import RMultipleTracker
from integration_example import IntegratedRiskManager
```

### 2. Initialize Risk Manager

```python
# Option A: Simple initialization
risk_manager = IntegratedRiskManager(account_id="MOOMOO-1252643")

# Option B: Component-by-component
checker = PreTradeChecker(DEFAULT_RISK_LIMITS, account_balance=100_000)
monitor = RiskMonitor(DEFAULT_RISK_LIMITS)
tracker = RMultipleTracker(account_size=100_000)
```

### 3. Before Every Trade

```python
from datetime import datetime, timedelta

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

if not is_valid:
    print("Order blocked:")
    for error in errors:
        print(f"  - {error}")
    exit()

# Get recommendation
recommended_qty = checker.get_position_sizing_recommendation(2.50)
print(f"Suggested size: {recommended_qty} contracts")

# Execute if valid
execute_trade(order)  # Your Moomoo execution function
```

### 4. Monitor Positions (Every 30 Seconds)

```python
# Get positions from Moomoo API
positions = moomoo_api.get_positions()  # Your API call
balance = moomoo_api.get_account_balance()

# Update risk monitor
monitor.update_positions(positions, account_balance=balance)

# Check alerts
alerts = monitor.check_risk_limits()
if alerts:
    for alert in alerts:
        print(alert)  # Log or notify
        if alert.alert_type == "CRITICAL":
            stop_trading()  # Emergency stop
```

### 5. Log Closed Trades

```python
# When you close a position
tracker.add_trade(TradeRecord(
    order_id="ORD-001",
    symbol="SPY",
    option_type="CALL",
    strike_price=500.0,
    expiration_date="2025-12-19",
    quantity=2,
    entry_price=2.50,
    entry_time=entry_datetime.isoformat(),
    exit_price=3.50,
    exit_time=exit_datetime.isoformat(),
    realized_pnl=200.0,
    r_multiple=0.80,
    status="CLOSED"
))
```

### 6. Generate Daily Report

```python
# At end of day
report = risk_manager.generate_daily_report()
print(report)

risk_manager.save_daily_report(report)
risk_manager.export_trade_data()
```

---

## Key Risk Limits (Paper Account: $100k)

| Metric | Limit | Why |
|--------|-------|-----|
| Max per option | 5 contracts | Prevents concentration |
| Max positions | 5 open | Manages complexity |
| Max notional | $10,000 | 10% of account exposure |
| Daily loss | $1,000 | 1% daily loss stop |
| Per-trade risk | 1% of account | $1,000 per trade max |
| Min expiration | 2 days | Avoids gamma risk |
| Max expiration | 60 days | Avoids time decay loss |
| Stop loss | 50% of premium | Exit on 50% loss |
| Take profit | 200% of premium | 2R target |
| Order rate | 15/30 sec | Moomoo API limit |

---

## Pre-Trade Checklist

Before submitting ANY order, system validates:

1. ✓ **Rate Limit** - Not exceeding 15 orders per 30 seconds
2. ✓ **Daily Loss** - Current loss < $1,000 limit
3. ✓ **Position Count** - < 5 positions open
4. ✓ **Notional** - Total exposure + new < $10,000
5. ✓ **Contracts** - Quantity <= 5 per option
6. ✓ **Expiration** - Between 2-60 days to expiration
7. ✓ **Buying Power** - 20% reserve maintained
8. ✓ **Account Risk** - Trade risk <= 1% of account
9. ✓ **Premium** - Price >= $0.01 per contract
10. ✓ **Premium Cap** - Price <= $500 per contract

**All 10 must pass. System blocks order if ANY fail.**

---

## R-Multiple Quick Reference

### What is R?

R = Unit of risk. If you risk $100 on a trade, that's 1R.

**R-Multiple = Profit / Risk**

- 1R = Break even after fees
- 0.5R = Loss of half your risk
- 2R = Win 2x your risk amount
- -1R = Loss equal to your risk (stopped out)

### Examples

```
Trade 1:
  Entry: $2.50, Exit: $3.50, Stop: $1.25
  Risk = $1.25 per contract = 1R
  Profit = $1.00 per contract
  R-Multiple = 1.00 / 1.25 = 0.80R ✓ Win

Trade 2:
  Entry: $2.50, Exit: $1.25, Stop: $1.25
  Risk = $1.25 per contract = 1R
  Loss = -$1.25 per contract
  R-Multiple = -1.25 / 1.25 = -1.00R ✗ Stop hit
```

### Target Performance

- **Win Rate**: 45%+ (even with 45% win rate, positive expectancy possible)
- **Avg Win**: 1.0R+
- **Avg Loss**: -0.5R or better
- **Expectancy**: Positive (should profit per trade on average)
- **Profit Factor**: 1.5x+ (wins 1.5x losses)

---

## Daily Monitoring Routine

### Morning (Market Open)

```python
# Check overnight positions
report = monitor.generate_risk_report()
print(report)

# Verify all stops are set
# Review expiration dates
# Check overnight P&L
```

### During Market

```python
# Every trade:
#   1. Validate with checker
#   2. Get recommendation
#   3. Execute
#   4. Log in tracker

# Every 30 seconds:
#   1. Update positions from Moomoo
#   2. Check for critical alerts
#   3. Review Greeks exposure
```

### Close of Market

```python
# Generate daily report
daily_report = risk_manager.generate_daily_report()

# Log daily metrics
daily_tracker.record_pnl(
    realized_pnl=realized,
    unrealized_pnl=unrealized,
    positions_count=len(positions)
)

# Export data
risk_manager.export_trade_data()

# Review performance
stats = tracker.get_trade_statistics()
print(f"Win Rate: {stats['win_rate_percent']:.1f}%")
print(f"Expectancy: ${stats['expectancy']:.2f}")
```

---

## Common Issues & Solutions

### "Order blocked by rate limiter"

**Problem**: Submitted too many orders too quickly

**Solution**:
```python
# Check wait time
wait = checker.rate_limiter.get_wait_time()
if wait > 0:
    print(f"Wait {wait:.1f} seconds before next order")
```

### "Insufficient buying power"

**Problem**: Account reserve (20%) being violated

**Solution**:
```python
available = account_balance * 0.80  # 80% usable
position_notional = qty * price * 100

if position_notional > available:
    # Reduce position size
    recommended = checker.get_position_sizing_recommendation(price)
```

### "Daily loss limit exceeded"

**Problem**: Lost more than $1,000 today

**Solution**:
```python
# Stop trading immediately
if abs(daily_loss) >= 1_000:
    print("DAILY LOSS LIMIT HIT - STOP TRADING")
    # Set emergency flag
```

### "Order approaching expiration"

**Problem**: Position has < 2 days to expiration

**Solution**:
```python
# Check DTE before entry
if days_to_expiration < 2:
    print("TOO CLOSE TO EXPIRATION - SKIP THIS TRADE")

# Close positions with < 3 days left
if position.dte <= 3:
    close_position(position)
```

---

## Performance Tracking

### Weekly Checklist

- [ ] Export trade data (`risk_manager.export_trade_data()`)
- [ ] Calculate statistics (`tracker.get_trade_statistics()`)
- [ ] Review win rate (target: 45%+)
- [ ] Check expectancy (must be positive)
- [ ] Analyze largest losses
- [ ] Verify stops are being hit appropriately
- [ ] Review notional exposure levels
- [ ] Check position sizing recommendations

### Monthly Review

- [ ] Calculate drawdown (should be < 20%)
- [ ] Review R-multiple distribution
- [ ] Analyze winning vs losing trades
- [ ] Check Greeks management
- [ ] Review expiration date handling
- [ ] Adjust limits if needed
- [ ] Back up all trade data

---

## Configuration Changes

### Increasing Risk Tolerance

**Only if profitable 3+ months:**

```python
# In options_risk_config.py
DEFAULT_RISK_LIMITS = RiskLimits(
    max_contracts_per_option=7,       # 5 → 7
    max_notional_exposure=15_000.00,  # 10k → 15k
    max_daily_loss=1_500.00,          # 1k → 1.5k
)
```

### Decreasing Risk (After Losses)

**After losing 50%+ of daily limit:**

```python
DEFAULT_RISK_LIMITS = RiskLimits(
    max_contracts_per_option=2,       # 5 → 2
    max_notional_exposure=5_000.00,   # 10k → 5k
    max_daily_loss=500.00,            # 1k → 500
)
```

---

## Emergency Procedures

### Critical Alert Received

```python
if alert.alert_type == "CRITICAL":
    # Notify immediately
    print(f"CRITICAL: {alert.message}")

    # Evaluate positions
    # Consider closing largest loss
    # Review new orders
```

### Daily Loss Limit Hit

```python
if abs(daily_loss) >= max_daily_loss:
    # STOP ALL TRADING
    print("DAILY LOSS LIMIT EXCEEDED - HALT TRADING")

    # Can hold existing positions
    # Can close positions
    # NO NEW ENTRIES
```

### Buying Power Crisis

```python
if available_buying_power < 0:
    # Close smallest winning position first
    # Reduce exposure to restore buffer
    # Do NOT add new positions
```

---

## File Summary

| File | Purpose |
|------|---------|
| `options_risk_config.py` | All risk limits & configuration |
| `pre_trade_checks.py` | Order validation (10-point check) |
| `risk_monitor.py` | Real-time monitoring & alerts |
| `risk_reporter.py` | R-multiple tracking & reporting |
| `integration_example.py` | Complete workflow example |
| `RISK_MANAGEMENT.md` | Full documentation |
| `QUICK_START_RISK.md` | This file |

---

## Support & Maintenance

### Testing

Run integration example weekly:
```bash
python /home/ajk/Nautilus/nautilus_trader/scripts/integration_example.py
```

### Logging

Check logs for issues:
```bash
tail -f /home/ajk/Nautilus/nautilus_trader/logs/risk_monitor.log
```

### Backups

Weekly backup of trade data:
```bash
cp -r /home/ajk/Nautilus/nautilus_trader/logs/ ~/backup/logs_$(date +%Y%m%d)
```

---

## Key Takeaways

1. **Every order** must pass 10-point validation
2. **Position sizing** based on 1% account risk
3. **Track in R-multiples** for objective analysis
4. **Stop at 50%** of premium paid
5. **Target 200%** profit on winners
6. **Monitor every 30 seconds** for alerts
7. **Stop trading** if daily loss > $1,000
8. **Review daily** to improve performance
9. **Never exceed limits** - system enforces them
10. **Risk discipline** is the key to long-term success

---

## Next Steps

1. Read full `RISK_MANAGEMENT.md` for detailed information
2. Test with `integration_example.py`
3. Integrate with your Moomoo trading code
4. Run daily and weekly reviews
5. Adjust limits based on performance
6. Track performance metrics consistently
