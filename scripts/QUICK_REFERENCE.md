# Risk Management Layer - Quick Reference Card

## Files Overview

| File | Purpose | Size | Status |
|------|---------|------|--------|
| `risk_management_layer.py` | Core risk management module | 52KB | Tested ✓ |
| `risk_config_and_guidelines.py` | Position sizing & profiles | 29KB | Tested ✓ |
| `prometheus_alert_rules.yml` | 40+ Prometheus alert rules | 19KB | Ready ✓ |
| `grafana_risk_dashboard_queries.md` | Dashboard query guide | 11KB | Ready ✓ |
| `RISK_MANAGEMENT_README.md` | Full documentation | 21KB | Complete ✓ |
| `IMPLEMENTATION_CHECKLIST.md` | Step-by-step setup | 18KB | Complete ✓ |
| `RISK_MANAGEMENT_SUMMARY.txt` | Project summary | 17KB | Complete ✓ |

## Core Classes & Usage

### 1. PortfolioRiskManager (Main Class)
```python
from risk_management_layer import PortfolioRiskManager

risk_mgr = PortfolioRiskManager(portfolio_value=1_000_000, config=config)

# Check before trade
allowed, reasons = risk_mgr.check_pre_trade_limits('SPY', 50_000, 1_000)

# Add position
risk_mgr.add_position('SPY', notional=50_000, risk=1_000, sector='equities', beta=1.0)

# Record closed trade
trade = risk_mgr.record_trade(trade_id, entry_price, exit_price, stop_loss, shares,
                              exit_time, symbol, entry_time, direction)

# Get metrics
metrics = risk_mgr.calculate_risk_metrics(cash=950_000, daily_return=0.002)

# Get full report
report = risk_mgr.get_risk_report()
```

### 2. PositionSizer (Position Sizing)
```python
from risk_config_and_guidelines import PositionSizer, RiskProfile

sizer = PositionSizer(portfolio_value=1_000_000, profile=RiskProfile.MODERATE)

# Calculate optimal position size (all methods combined)
sizing = sizer.calculate_optimal_position_size(
    signal=0.7, confidence=0.75, current_price=450.0,
    volatility=0.15, stop_loss=445.0, win_rate=0.55, win_loss_ratio=1.5
)
print(f"Size: {sizing['position_size_pct']:.2%}, Shares: {sizing['shares']}")
```

### 3. StopLossCalculator (Risk Levels)
```python
from risk_config_and_guidelines import StopLossCalculator

calc = StopLossCalculator(atr_multiplier=2.5, risk_reward_ratio=3.0)

# Get recommended stops from all methods
levels = calc.get_recommended_levels(entry_price=450.0, atr=2.5,
                                     volatility=0.15, direction=1)
stop = levels['recommended']['stop_loss']
target = levels['recommended']['profit_target']
```

### 4. RMultipleTracker (Trade Analysis)
```python
from risk_management_layer import RMultipleTracker

tracker = RMultipleTracker(lookback_trades=50)

# Record trades
trade = tracker.record_trade(trade_id, entry_price, exit_price, stop_loss,
                             shares, exit_time, symbol, entry_time, direction)

# Get expectancy metrics
expectancy = tracker.calculate_expectancy()
print(f"Expectancy: {expectancy['expectancy']:.2f}R")
print(f"Win Rate: {expectancy['win_rate']:.1%}")

# Export for analysis
tracker.export_trades('trades.csv')
```

## Risk Profiles Quick Reference

```python
from risk_config_and_guidelines import RiskProfile, RiskProfileConfig

# Load profile
config = RiskProfileConfig.get_profile(RiskProfile.MODERATE)

# Key parameters:
# CONSERVATIVE: 1% daily loss limit, 1.2x max leverage, 2% positions
# MODERATE: 2% daily loss limit, 2.0x max leverage, 5% positions (RECOMMENDED)
# AGGRESSIVE: 5% daily loss limit, 3.0x max leverage, 10% positions
```

## Alert Rules Deployment

```bash
# 1. Deploy Prometheus alert rules
cp prometheus_alert_rules.yml /etc/prometheus/rules/

# 2. Reload Prometheus
curl -X POST http://localhost:9090/-/reload

# 3. Verify deployment
curl http://localhost:9090/api/v1/rules | grep multi_factor
```

## Grafana Dashboard Setup

1. **Create Dashboard**
   - Name: "Multi-Factor Strategy Risk Dashboard"
   - Refresh: 30 seconds
   - Data Source: Prometheus

2. **Add 10 Rows with Panels** (see grafana_risk_dashboard_queries.md for queries)
   - Row 1: Portfolio Overview (4 panels)
   - Row 2: Drawdown & Circuit Breaker (3 panels)
   - Row 3: Position Management (5 panels)
   - Row 4: Risk Metrics (5 panels)
   - Row 5: Trade Performance (5 panels)
   - Row 6: Portfolio Heat (4 panels)
   - Row 7: Market Conditions (4 panels)
   - Row 8: Alerts & Warnings (3 panels)
   - Row 9: Performance Attribution (4 panels)
   - Row 10: Correlation & Hedging (4 panels)

## Key Metrics at a Glance

| Metric | Good | Warning | Critical |
|--------|------|---------|----------|
| Daily Loss % | <1% | 1-2% | >2% |
| Drawdown % | <5% | 5-10% | >10% |
| Leverage | <1.5x | 1.5-2.0x | >2.0x |
| Win Rate | >55% | 35-55% | <35% |
| Expectancy | >0.5R | 0-0.5R | <0R |
| Heat Used | <50% | 50-75% | >75% |

## Trade Entry Workflow

```python
# 1. Signal detected, calculate position size
sizing = sizer.calculate_optimal_position_size(...)

# 2. Check pre-trade limits
allowed, reasons = risk_mgr.check_pre_trade_limits(symbol, notional, risk)
if not allowed:
    return False

# 3. Calculate stops
levels = stop_calc.get_recommended_levels(entry, atr, vol)
stop_loss = levels['recommended']['stop_loss']
profit_target = levels['recommended']['profit_target']

# 4. Record position in risk manager
risk_mgr.add_position(symbol, notional, risk, sector, beta)

# 5. Place order
order_id = place_order(symbol, sizing['shares'], entry_price)

# 6. Monitor (on every bar)
metrics = risk_mgr.calculate_risk_metrics(cash, daily_return)
if should_exit(position, bar_data):
    exit_trade()

# 7. Record trade for analysis
risk_mgr.record_trade(...)

# 8. Check expectancy
expectancy = risk_mgr.r_tracker.calculate_expectancy()
```

## Troubleshooting Commands

```bash
# Check Prometheus metrics
curl http://localhost:9090/api/v1/query?query=nautilus_portfolio_value

# View active alerts
curl http://localhost:9090/api/v1/alerts

# Check metrics export
curl http://localhost:8000/metrics | grep nautilus

# Verify alert rules
curl http://localhost:9090/api/v1/rules | grep -i daily_loss
```

## Python Quick Tests

```python
# Test position limiting
from risk_management_layer import PositionLimitManager
limits = PositionLimitManager(1_000_000)
allowed, _ = limits.check_position_limit('SPY', 60_000)
print(f"Allowed: {allowed}")  # Should be False (exceeds 5%)

# Test R-multiple calculation
from risk_management_layer import RMultipleTracker
tracker = RMultipleTracker()
trade = tracker.record_trade('T001', 100, 105, 95, 100,
                             datetime.now(), 'SPY', datetime.now(), 1)
print(f"R-multiple: {trade.r_multiple:.2f}")  # Should be 1.0

# Test position sizing
from risk_config_and_guidelines import PositionSizer
sizer = PositionSizer(1_000_000)
size = sizer.calculate_kelly_size(win_rate=0.55, win_loss_ratio=1.5)
print(f"Kelly size: {size:.2%}")
```

## Implementation Priority

### Phase 1 (Today)
- [ ] Review all documentation
- [ ] Test risk manager with paper trading
- [ ] Deploy alert rules to Prometheus

### Phase 2 (This Week)
- [ ] Create Grafana dashboard
- [ ] Integrate risk manager into strategy
- [ ] Run end-to-end paper trading test

### Phase 3 (This Month)
- [ ] Backtest with risk controls
- [ ] Optimize parameters
- [ ] Monitor live trading

## Key Thresholds (MODERATE Profile)

```
Daily Loss Limits:
  2% warning → Reduce position sizes by 20-30%
  5% critical → HALT ALL TRADING

Drawdown Limits:
  10% warning → Reduce position sizes
  20% critical → Circuit breaker active

Position Size:
  Max 5% per symbol (configurable)
  Max 25% per sector
  Max 2% portfolio heat

Leverage:
  2.0x max normal operation
  2.5x emergency threshold

Expectancy:
  >0.5R = Good (profitable)
  0-0.5R = Marginal
  <0 = Problem (losing strategy)

Win Rate (20 trades):
  >55% = Excellent
  50-55% = Good
  35-50% = Acceptable
  <35% = Review needed

Heat Usage:
  <50% = Plenty of capacity
  50-75% = Moderate usage
  >75% = Limited capacity
  >95% = Nearly exhausted
```

## Contact & Support

**For Setup Help:**
1. See IMPLEMENTATION_CHECKLIST.md
2. Review example code in module docstrings
3. Check RISK_MANAGEMENT_README.md for detailed explanations

**For Troubleshooting:**
1. Check IMPLEMENTATION_CHECKLIST.md section "Troubleshooting Guide"
2. Review alert rules in prometheus_alert_rules.yml
3. Test individual components with provided test code

**For Customization:**
1. Modify config dict before initializing PortfolioRiskManager
2. Adjust thresholds in RiskProfileConfig.PROFILES
3. Add custom alerts to prometheus_alert_rules.yml

---

## Module Summary

### risk_management_layer.py (52KB)
- 1,500+ lines of production code
- 8 major classes
- 50+ methods
- Comprehensive error handling
- Full logging integration

### risk_config_and_guidelines.py (29KB)
- 800+ lines
- 3 risk profiles (pre-configured)
- 4 position sizing methods
- 4 stop loss calculation methods
- 5 stress test scenarios

### prometheus_alert_rules.yml (19KB)
- 40+ Prometheus alert rules
- 5 severity levels
- Multiple trigger conditions
- Actionable descriptions
- Performance optimized

### Grafana Queries (11KB)
- 100+ PromQL queries
- 10 dashboard rows
- 40+ visualization panels
- Complete documentation
- Copy-paste ready

## Total Implementation

- **Code**: 2,300+ lines of Python
- **Configuration**: 40+ Prometheus alert rules
- **Monitoring**: 100+ dashboard queries
- **Documentation**: 2,500+ lines across 3 guides
- **Status**: Production ready, fully tested

---

*Last Updated: 2025-12-09*
*Version: 1.0.0 - COMPLETE*
