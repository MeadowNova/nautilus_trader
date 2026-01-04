# Risk Management Implementation Checklist

## Pre-Deployment Setup

### 1. Environment Setup
- [ ] Python 3.11+ installed with required packages
- [ ] numpy, pandas, dataclasses available
- [ ] Prometheus exporter configured (for metrics)
- [ ] Grafana connected to Prometheus

### 2. Risk Configuration Selection
- [ ] Select risk profile: CONSERVATIVE / MODERATE / AGGRESSIVE
  - [ ] For paper trading: Recommend MODERATE profile
  - [ ] For live trading: Recommend CONSERVATIVE initially
  - [ ] Document profile selection and rationale

### 3. Customize Risk Parameters
Review and adjust for your strategy:

```python
config = {
    # Daily risk limits
    'daily_loss_warning_pct': 0.02,      # 2% (adjust as needed)
    'daily_loss_limit_pct': 0.05,        # 5% hard limit

    # Drawdown limits
    'max_drawdown_warning': 0.10,        # 10%
    'max_drawdown_limit': 0.20,          # 20%

    # Position limits (per symbol)
    'max_position_size_pct': 0.05,       # 5% of portfolio
    'max_sector_exposure_pct': 0.25,     # 25% per sector
    'max_portfolio_heat_pct': 0.02,      # 2% total risk

    # Position sizing
    'kelly_fraction': 0.25,              # Conservative Kelly
    'max_leverage_ratio': 2.0,           # 2x leverage max
    'volatility_target': 0.15,           # 15% annual vol target

    # Stop loss & profit taking
    'atr_multiplier': 2.5,               # ATR stop distance
    'profit_target_multiplier': 3.0,     # 3:1 reward:risk ratio
    'time_stop_bars': 100,               # Max holding period

    # Hedging
    'target_delta': 0.0,                 # Market neutral
    'max_hedge_cost_pct': 0.02,          # 2% max hedge cost
    'rebalance_threshold': 0.15          # Rehedge at 15% delta drift
}
```

---

## Prometheus Integration

### 4. Configure Prometheus Metrics Export

**Create metric exporter script:**
```python
# expose_metrics.py
from prometheus_client import start_http_server, Gauge, Histogram
import time

# Define metrics
portfolio_value = Gauge('nautilus_portfolio_value', 'Total portfolio value')
daily_loss_pct = Gauge('nautilus_daily_loss_pct', 'Daily loss percentage')
leverage_ratio = Gauge('nautilus_leverage_ratio', 'Portfolio leverage')
heat_used_pct = Gauge('nautilus_heat_used_pct', 'Heat usage percentage')
win_rate_20trades = Gauge('nautilus_win_rate_20trades', '20-trade win rate')
drawdown_pct = Gauge('nautilus_drawdown_pct', 'Current drawdown')
circuit_breaker_active = Gauge('nautilus_circuit_breaker_active', 'Circuit breaker status')

# Start HTTP server on port 8000
start_http_server(8000)

# Update metrics in your trading loop
while True:
    # ... update metrics from risk manager
    portfolio_value.set(risk_mgr.portfolio_value)
    daily_loss_pct.set(metrics.daily_loss_pct)
    leverage_ratio.set(metrics.leverage_ratio)
    # ... etc
    time.sleep(1)
```

- [ ] Deploy metrics exporter
- [ ] Verify metrics available at `http://localhost:8000/metrics`

### 5. Deploy Prometheus Alert Rules

```bash
# Copy alert rules to Prometheus rules directory
cp prometheus_alert_rules.yml /etc/prometheus/rules/

# Update prometheus.yml to include rules
# Add to global:
# rule_files:
#   - "/etc/prometheus/rules/prometheus_alert_rules.yml"

# Reload Prometheus
curl -X POST http://localhost:9090/-/reload
```

- [ ] Alert rules deployed
- [ ] Prometheus successfully reloaded
- [ ] Verify alerts in Prometheus UI (Status > Rules)

### 6. Setup Grafana Dashboard

```bash
# Option 1: Create dashboard manually
# - Create new dashboard in Grafana
# - Add 10 rows of panels (see grafana_risk_dashboard_queries.md)
# - Configure PromQL queries for each panel
# - Set refresh rate to 30 seconds
# - Save as "Multi-Factor Strategy Risk Dashboard"

# Option 2: Import dashboard JSON (if available)
# - Grafana > Dashboards > Import
# - Paste JSON from prometheus_alert_generator
```

- [ ] Grafana dashboard created
- [ ] All 10 rows with panels configured
- [ ] Test queries with sample data
- [ ] Set alerts on critical metrics

---

## Risk Management Module Integration

### 7. Initialize Risk Manager in Strategy

**In your strategy initialization:**

```python
from risk_management_layer import PortfolioRiskManager
from risk_config_and_guidelines import RiskProfile, RiskProfileConfig

class MyStrategy:
    def __init__(self, portfolio_value, risk_profile=RiskProfile.MODERATE):
        # Load risk configuration
        config = RiskProfileConfig.get_profile(risk_profile)

        # Initialize risk manager
        self.risk_mgr = PortfolioRiskManager(portfolio_value, config)

        # Initialize position sizer
        from risk_config_and_guidelines import PositionSizer
        self.position_sizer = PositionSizer(portfolio_value, risk_profile)

        # Initialize stop loss calculator
        from risk_config_and_guidelines import StopLossCalculator
        self.stop_calc = StopLossCalculator(
            atr_multiplier=config['atr_multiplier'],
            risk_reward_ratio=config['profit_target_multiplier']
        )
```

- [ ] Risk manager imported and initialized
- [ ] Risk profile configured
- [ ] Position sizer ready
- [ ] Stop loss calculator ready

### 8. Pre-Trade Validation

**Before every trade:**

```python
def enter_position(self, symbol, signal, confidence, entry_price, stop_loss):
    # Step 1: Check circuit breaker
    if self.risk_mgr.circuit_breaker.circuit_breaker_active:
        logger.warning("Circuit breaker active - no new trades")
        return False

    # Step 2: Calculate position size
    volatility = self._get_volatility(symbol)
    sizing = self.position_sizer.calculate_optimal_position_size(
        signal=signal,
        confidence=confidence,
        current_price=entry_price,
        volatility=volatility,
        stop_loss=stop_loss
    )

    # Step 3: Check limits
    risk_dollars = sizing['notional_dollars'] * abs(entry_price - stop_loss) / entry_price
    allowed, reasons = self.risk_mgr.check_pre_trade_limits(
        symbol=symbol,
        notional=sizing['notional_dollars'],
        required_risk=risk_dollars
    )

    if not allowed:
        logger.warning(f"Trade rejected: {reasons}")
        return False

    # Step 4: Record position
    self.risk_mgr.add_position(
        symbol=symbol,
        notional=sizing['notional_dollars'],
        risk=risk_dollars,
        sector=self._get_sector(symbol),
        beta=self._get_beta(symbol)
    )

    # Step 5: Place order
    self._place_order(symbol, sizing['shares'], entry_price)
    return True
```

- [ ] Pre-trade validation implemented
- [ ] Circuit breaker check in place
- [ ] Position sizing calculated
- [ ] Risk limits enforced

### 9. Post-Trade Monitoring

**Update position on every bar:**

```python
def monitor_positions(self, bar_data):
    # Update circuit breaker with current portfolio value
    status = self.risk_mgr.circuit_breaker.update_portfolio(
        self.get_current_portfolio_value()
    )

    if status['alerts']:
        for alert in status['alerts']:
            logger.warning(f"{alert['level']}: {alert['message']}")

    # Update risk metrics
    metrics = self.risk_mgr.calculate_risk_metrics(
        cash=self.get_cash(),
        daily_return=self._calculate_daily_return()
    )

    # Export metrics to Prometheus
    self._export_metrics(metrics)

    # Check for exit conditions
    for position in self.open_positions:
        self._check_exit_conditions(position, bar_data)
```

- [ ] Position monitoring loop implemented
- [ ] Circuit breaker updated regularly
- [ ] Risk metrics calculated
- [ ] Metrics exported to Prometheus

### 10. Trade Exit & Recording

**On position close:**

```python
def exit_position(self, symbol, exit_price, exit_reason):
    # Close position in risk manager
    self.risk_mgr.close_position(symbol, pnl)

    # Record trade for R-multiple analysis
    self.risk_mgr.record_trade(
        trade_id=f"{symbol}_{self.trade_count}",
        symbol=symbol,
        entry_price=entry_price,
        exit_price=exit_price,
        stop_loss=stop_loss,
        shares=shares,
        entry_time=entry_time,
        exit_time=datetime.now(),
        direction=direction
    )

    # Generate R-multiple metrics
    expectancy = self.risk_mgr.r_tracker.calculate_expectancy()
    logger.info(f"Trade recorded. Expectancy: {expectancy['expectancy']:.2f}R")

    # Check if expectancy degraded
    if expectancy['expectancy'] < 0:
        logger.warning("Strategy expectancy is negative - review needed")
```

- [ ] Exit conditions implemented
- [ ] Position properly closed
- [ ] Trade recorded with all metrics
- [ ] R-multiple calculated
- [ ] Expectancy monitored

---

## Testing & Validation

### 11. Unit Testing

```python
# test_risk_management.py
import pytest
from risk_management_layer import PositionLimitManager, RMultipleTracker
from risk_config_and_guidelines import PositionSizer, StopLossCalculator

def test_position_limits():
    limits = PositionLimitManager(1_000_000)
    allowed, _ = limits.check_position_limit('SPY', 50_000)
    assert allowed == True

    allowed, _ = limits.check_position_limit('SPY', 100_000)  # Over limit
    assert allowed == False

def test_r_multiple_calculation():
    tracker = RMultipleTracker()
    trade = tracker.record_trade(
        trade_id='T001',
        entry_price=100.0,
        exit_price=105.0,
        stop_loss=95.0,
        shares=100,
        exit_time=datetime.now(),
        symbol='SPY',
        entry_time=datetime.now(),
        direction=1
    )
    assert trade.r_multiple == 1.0  # 5 points / 5 point risk

def test_position_sizing():
    sizer = PositionSizer(1_000_000)
    size = sizer.calculate_optimal_position_size(
        signal=0.5,
        confidence=0.5,
        current_price=100.0,
        volatility=0.15,
        stop_loss=95.0
    )
    assert size['notional_dollars'] > 0
    assert size['shares'] > 0
```

- [ ] Unit tests written
- [ ] All tests passing
- [ ] Edge cases tested

### 12. Backtest Validation

```python
# Validate on historical data
def backtest_with_risk_management():
    risk_mgr = PortfolioRiskManager(1_000_000, config)

    for bar in historical_data:
        signal = strategy.generate_signal(bar)

        # Risk checks
        if not validate_trade(risk_mgr, signal):
            continue

        # Execute trade
        execute_trade(risk_mgr, signal)

        # Monitor
        update_metrics(risk_mgr, bar)

    # Generate report
    report = risk_mgr.get_risk_report()
    return report
```

- [ ] Historical backtest with risk controls
- [ ] Verify position limits enforced
- [ ] Check circuit breaker triggers
- [ ] Validate expectancy calculation
- [ ] Compare with non-risk-managed backtest

### 13. Paper Trading Validation (Current)

**Paper trading accounts:**
- [ ] Stock Account (1252643): SPY 2 shares @ $684.61
- [ ] Options Account (1252648): SPY Call Dec23 $685 strike

**Test scenarios:**
- [ ] Position entry with size calculation
- [ ] Stop loss trigger on 2% adverse move
- [ ] Profit target on favorable move
- [ ] Daily loss limit at 2%
- [ ] Heat usage tracking
- [ ] Expectancy calculation on closed trades
- [ ] Alert generation in Prometheus
- [ ] Dashboard display in Grafana

```python
# paper_trading_test.py
def test_stock_account():
    # Entry: 2 shares SPY @ $684.61
    # Stop: $670.61 (2% risk)
    # Target: $712.61 (4.1% reward)
    risk_mgr.add_position('SPY', 1_369.22, 28, 'equities', 1.0)
    assert risk_mgr.position_limits.portfolio_heat_used < 0.02

def test_options_account():
    # 1 SPY Call Dec23 $685
    # Track delta exposure and hedge if needed
    risk_mgr.add_position('SPY_CALL', 5_000, 500, 'options', 0.5)
```

- [ ] Stock account trading validated
- [ ] Options account tracked
- [ ] Position limits enforced
- [ ] Alerts firing correctly

---

## Ongoing Monitoring

### 14. Daily Monitoring Checklist

**Each morning:**
- [ ] Review Grafana dashboard
- [ ] Check Prometheus alerts
- [ ] Verify no overnight circuit breaker triggered
- [ ] Confirm cash and heat available
- [ ] Check for high correlations

**During trading hours:**
- [ ] Monitor daily loss vs 2% limit
- [ ] Watch drawdown vs 10% warning level
- [ ] Track win rate over last 20 trades
- [ ] Monitor position concentration
- [ ] Check leverage ratio

**End of day:**
- [ ] Export daily trades to CSV
- [ ] Calculate next day's expectancy
- [ ] Review any alerts triggered
- [ ] Document any manual interventions
- [ ] Check circuit breaker reset

### 15. Weekly Analysis

- [ ] Calculate rolling expectancy (20-50 trades)
- [ ] Analyze win rate by regime
- [ ] Review correlation changes
- [ ] Check if positions are clustered
- [ ] Verify hedge positions effective
- [ ] Assess strategy profitability

### 16. Monthly Reviews

- [ ] Full portfolio performance analysis
- [ ] Risk metric trends (vol, var, drawdown)
- [ ] Compare actual vs target risk levels
- [ ] Review any circuit breaker events
- [ ] Assess position sizing effectiveness
- [ ] Consider parameter adjustments

---

## Troubleshooting Guide

### Issue: Prometheus Metrics Not Appearing

**Checklist:**
- [ ] Metrics exporter running on port 8000
- [ ] Prometheus scrape config includes localhost:8000
- [ ] Check /metrics endpoint directly
- [ ] Verify no firewall blocking 8000

**Fix:**
```bash
# Check if exporter is running
lsof -i :8000

# Check Prometheus scrape config
grep -A5 "localhost:8000" /etc/prometheus/prometheus.yml

# Manually test metrics
curl http://localhost:8000/metrics
```

### Issue: Alerts Not Firing

**Checklist:**
- [ ] Alert rules deployed to /etc/prometheus/rules/
- [ ] Prometheus reloaded with curl -X POST
- [ ] Metrics meeting alert conditions (verify in query)
- [ ] Alert duration met (e.g., 5m for daily loss)

**Fix:**
```bash
# Check alert rules loaded
curl http://localhost:9090/api/v1/rules

# Test a metric manually
curl 'http://localhost:9090/api/v1/query?query=nautilus_daily_loss_pct'

# Check alert history
curl 'http://localhost:9090/api/v1/alerts'
```

### Issue: Risk Manager Rejecting Valid Trades

**Debug:**
```python
allowed, reasons = risk_mgr.check_pre_trade_limits(
    symbol='SPY',
    notional=50_000,
    required_risk=1_000
)
print(f"Allowed: {allowed}")
print(f"Reasons: {reasons}")

# Check individual limits
print(f"Position limit: {risk_mgr.position_limits.max_position_size_pct}")
print(f"Heat used: {risk_mgr.position_limits.portfolio_heat_used}")
print(f"Heat available: {risk_mgr.position_limits.get_available_capital()}")
```

### Issue: Expectancy Calculation Seems Wrong

**Verify:**
```python
# Check if trades recorded correctly
print(f"Total trades: {len(risk_mgr.r_tracker.rolling_trades)}")

# Manually verify a trade
for trade in list(risk_mgr.r_tracker.rolling_trades)[-5:]:
    print(f"Trade: Entry ${trade.entry_price}, Exit ${trade.exit_price}")
    print(f"  Risk: ${trade.initial_risk}, PnL: ${trade.pnl}")
    print(f"  R-multiple: {trade.r_multiple:.2f}")

# Recalculate expectancy
expectancy = risk_mgr.r_tracker.calculate_expectancy()
print(expectancy)
```

---

## Performance Optimization

### 17. Optimize for Production

**Memory usage:**
- [ ] Use fixed-size deques for history (lookback_trades=50)
- [ ] Archive old trades monthly
- [ ] Batch metric exports

**CPU usage:**
- [ ] Reduce metric calculation frequency
- [ ] Cache correlation matrix
- [ ] Use numpy for vectorized operations

**Network:**
- [ ] Batch Prometheus metric updates (every 5 seconds)
- [ ] Use local Prometheus cache
- [ ] Compress trade data exports

---

## Go-Live Checklist

### 18. Before Live Trading

- [ ] All tests passing
- [ ] Paper trading validated
- [ ] Risk limits clearly defined
- [ ] Alerts properly configured
- [ ] Hedging strategy tested
- [ ] Backup and recovery plan
- [ ] Manual intervention procedures documented
- [ ] Team trained on system
- [ ] Runbooks prepared
- [ ] Communication plan for alerts
- [ ] Escalation procedures defined
- [ ] Monitoring 24/5 (market hours)

---

## Files Summary

```
/home/ajk/Nautilus/nautilus_trader/scripts/
├── risk_management_layer.py              # Core module (2000+ lines)
├── risk_config_and_guidelines.py         # Configuration & sizing (800+ lines)
├── prometheus_alert_rules.yml            # 40+ alert rules
├── grafana_risk_dashboard_queries.md     # 100+ PromQL queries
├── RISK_MANAGEMENT_README.md             # Full documentation
└── IMPLEMENTATION_CHECKLIST.md           # This file
```

---

## Quick Reference

### Key Metrics at a Glance

| Metric | Good | Warning | Critical |
|--------|------|---------|----------|
| Daily Loss | <1% | 1-2% | >2% |
| Drawdown | <5% | 5-10% | >10% |
| Leverage | <1.5x | 1.5-2.0x | >2.0x |
| Win Rate | >55% | 35-55% | <35% |
| Expectancy | >0.5R | 0-0.5R | <0R |
| Heat Used | <50% | 50-75% | >75% |
| Concentration | <3% | 3-5% | >5% |
| Position Correlation | <0.70 | 0.70-0.85 | >0.85 |

### Quick Commands

```bash
# Check Prometheus metrics
curl http://localhost:9090/metrics

# Reload Prometheus
curl -X POST http://localhost:9090/-/reload

# Export trades
python3 -c "from risk_management_layer import *; tracker.export_trades('trades.csv')"

# Test alert
curl 'http://localhost:9090/api/v1/alerts'

# View risk report
python3 -c "from risk_management_layer import *; print(risk_mgr.get_risk_report())"
```

---

Status: Ready for Implementation
Last Updated: 2025-12-09
Version: 1.0.0
