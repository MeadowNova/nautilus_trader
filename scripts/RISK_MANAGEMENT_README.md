# Comprehensive Risk Management Layer for Multi-Factor Strategy

## Overview

This risk management framework provides institutional-grade protection for the advanced multi-factor strategy deployment. It integrates position limits, R-multiple tracking, hedging strategies, and real-time monitoring with Prometheus/Grafana alerts.

**Key Files:**
- `/home/ajk/Nautilus/nautilus_trader/scripts/risk_management_layer.py` - Core risk management module
- `/home/ajk/Nautilus/nautilus_trader/scripts/risk_config_and_guidelines.py` - Configuration and position sizing
- `/home/ajk/Nautilus/nautilus_trader/scripts/prometheus_alert_rules.yml` - Prometheus alert rules (deploy to Prometheus)
- `/home/ajk/Nautilus/nautilus_trader/scripts/grafana_risk_dashboard_queries.md` - Grafana dashboard queries

---

## Architecture Overview

### Core Components

#### 1. Position Limit Manager
**Purpose:** Control concentration risk and portfolio exposure

**Features:**
- Max position size per symbol (% of portfolio)
- Sector/asset class exposure limits
- Portfolio heat (total risk capital) management
- Correlation-based concentration monitoring

**Default Settings (Moderate Profile):**
```
Max Position Size:     5% per symbol
Max Sector Exposure:   25% per sector
Max Portfolio Heat:    2% (total risk at stake)
Max Leverage Ratio:    2.0x
Max Correlation Sum:   3.0 (sum of abs correlations)
```

**Usage:**
```python
from risk_management_layer import PositionLimitManager

limits = PositionLimitManager(portfolio_value=1_000_000)

# Check if new position is allowed
allowed, reason = limits.check_position_limit(
    symbol='SPY',
    notional=50_000
)

if allowed:
    limits.add_position(
        symbol='SPY',
        notional=50_000,
        risk=1_000,
        sector='equities',
        beta=1.0
    )

# Get concentration report
report = limits.get_concentration_report()
print(f"Total Leverage: {report['portfolio_leverage']:.2f}x")
```

#### 2. R-Multiple Tracker
**Purpose:** Objective trade performance measurement using R-multiples

**Metrics:**
- R-multiple = P&L / Initial Risk (1R)
- Win Rate and consecutive streaks
- Trade Expectancy = (Win% × Avg Win) - (Loss% × Avg Loss)
- Profit Factor and capture ratio

**Example Calculation:**
```
Entry Price:    $100
Stop Loss:      $95
Exit Price:     $105
Risk (1R):      $5 per share

100 shares = $500 total risk (1R)
P&L:        = $500 profit
R-multiple: = $500 / $500 = 1.0R

Expectancy (rolling 20 trades):
Win Rate:   55%
Avg Win:    2.0R
Avg Loss:   2.5R
Expectancy: (0.55 × 2.0) - (0.45 × 2.5) = 0.275R
```

**Usage:**
```python
from risk_management_layer import RMultipleTracker

tracker = RMultipleTracker(lookback_trades=50)

# Record completed trade
trade = tracker.record_trade(
    trade_id='T001',
    entry_price=100.0,
    exit_price=105.0,
    stop_loss=95.0,
    shares=100,
    exit_time=datetime.now(),
    symbol='SPY',
    entry_time=datetime.now() - timedelta(hours=2),
    direction=1
)

# Calculate rolling expectancy
metrics = tracker.calculate_expectancy()
print(f"Expectancy: {metrics['expectancy']:.2f}R")
print(f"Win Rate: {metrics['win_rate']:.1%}")
print(f"Consecutive Wins: {metrics['consecutive_wins']}")
```

#### 3. Hedging Engine
**Purpose:** Portfolio protection and risk reduction

**Strategies:**
- **Delta Hedging:** Use options/shorts to neutralize directional exposure
- **Correlation Hedging:** Add negatively correlated assets when concentrated
- **Tail Risk Hedging:** Buy OTM puts based on VaR
- **Beta Management:** Reduce systematic market risk

**Hedge Recommendations:**
```python
from risk_management_layer import HedgingEngine

hedging = HedgingEngine()

# Get delta hedge recommendation
delta = 0.75  # Long biased
portfolio_value = 1_000_000
recommendation = hedging.recommend_delta_hedge(delta, portfolio_value)
# Returns: {'type': 'delta_hedge', 'action': 'hedge_long_bias', ...}

# Get tail risk hedge
hedge = hedging.recommend_tail_risk_hedge(
    portfolio_value=1_000_000,
    current_var_95=0.06  # 6% downside risk
)
# Returns: {'type': 'tail_risk_hedge', 'action': 'buy_otm_puts', ...}
```

#### 4. Risk Analyzer
**Purpose:** Advanced risk metrics and stress testing

**Metrics:**
- Value at Risk (VaR) at 95% confidence
- Conditional VaR (Expected Shortfall)
- Correlation matrix between positions
- Portfolio Beta
- Monte Carlo simulation

**Usage:**
```python
from risk_management_layer import RiskAnalyzer

analyzer = RiskAnalyzer(lookback_days=252)

# Calculate VaR
portfolio_returns = np.array(daily_returns)
var_95 = analyzer.calculate_var_95(portfolio_returns)
print(f"95% VaR: {var_95:.2%}")  # "5% chance of loss > 3.2%"

# Monte Carlo simulation
sim_results = analyzer.monte_carlo_simulation(
    initial_value=1_000_000,
    daily_returns=returns_array,
    num_simulations=10000,
    horizon_days=20
)
print(f"5th percentile outcome: ${sim_results['percentile_5']:,.0f}")
```

#### 5. Circuit Breaker
**Purpose:** Emergency stop-trading mechanism

**Triggers:**
- Daily loss > 2%: Reduce position size
- Daily loss > 5%: HALT TRADING
- Max drawdown > 10%: Alert and reduce
- Max drawdown > 20%: Circuit breaker active

**Usage:**
```python
from risk_management_layer import CircuitBreaker

breaker = CircuitBreaker(portfolio_value=1_000_000)

# Update with current portfolio value
status = breaker.update_portfolio(current_value=980_000)

if breaker.circuit_breaker_active:
    print("TRADING HALTED - Circuit breaker active")
    for alert in status['alerts']:
        print(f"{alert['level']}: {alert['message']}")

# Reset daily counters at market open
breaker.reset_daily()
```

### Main Orchestrator

**PortfolioRiskManager** integrates all components:

```python
from risk_management_layer import PortfolioRiskManager

# Initialize with portfolio value and config
risk_mgr = PortfolioRiskManager(
    portfolio_value=1_000_000,
    config={
        'max_position_size_pct': 0.05,
        'max_daily_loss_pct': 0.02,
        'max_drawdown_warning': 0.10,
        'lookback_trades': 50
    }
)

# Check pre-trade limits
allowed, reasons = risk_mgr.check_pre_trade_limits(
    symbol='SPY',
    notional=50_000,
    required_risk=1_000
)

# Record trade
if allowed:
    risk_mgr.add_position('SPY', 50_000, 1_000, 'equities', 1.0)

# Calculate comprehensive metrics
metrics = risk_mgr.calculate_risk_metrics(
    cash=950_000,
    daily_return=0.002
)

# Generate full risk report
report = risk_mgr.get_risk_report()
```

---

## Risk Profiles

Three pre-configured profiles balancing growth and safety:

### CONSERVATIVE Profile
- Capital preservation focus
- Max daily loss: 1%
- Max drawdown: 5%
- Max leverage: 1.2x
- Max position: 2% per symbol
- Kelly fraction: 0.15 (very conservative)

**Use Case:** Wealth preservation, risk-averse investors, essential capital

### MODERATE Profile (Recommended)
- Balanced growth and preservation
- Max daily loss: 2%
- Max drawdown: 10%
- Max leverage: 2.0x
- Max position: 5% per symbol
- Kelly fraction: 0.25

**Use Case:** Professional traders, institutional accounts, primary capital

### AGGRESSIVE Profile
- Maximum growth focus
- Max daily loss: 5%
- Max drawdown: 20%
- Max leverage: 3.0x
- Max position: 10% per symbol
- Kelly fraction: 0.35

**Use Case:** Hedge funds, prop trading, dedicated capital

**Load Profile:**
```python
from risk_config_and_guidelines import RiskProfile, RiskProfileConfig

config = RiskProfileConfig.get_profile(RiskProfile.MODERATE)
print(config['max_daily_loss_pct'])  # 0.02 = 2%
```

---

## Position Sizing

### Position Sizer Methods

#### 1. Kelly Criterion
Mathematically optimal position size: `f* = (bp - q) / b`

```python
from risk_config_and_guidelines import PositionSizer, RiskProfile

sizer = PositionSizer(portfolio_value=1_000_000, profile=RiskProfile.MODERATE)

# Calculate Kelly size
kelly_size = sizer.calculate_kelly_size(
    win_rate=0.55,        # 55% historical win rate
    win_loss_ratio=1.5    # Avg win = 1.5x avg loss
)
print(f"Kelly size: {kelly_size:.2%}")  # ~5.5% of capital
```

#### 2. Volatility Scaling
Inverse relationship: Higher volatility = smaller positions

```python
# Volatility scaling
adjusted_size = sizer.calculate_volatility_scaled_size(
    base_size=0.05,         # 5% base
    current_volatility=0.25 # 25% annual vol
)
# Returns smaller position due to high volatility
```

#### 3. Fixed Risk
Define acceptable loss, calculate position size

```python
# Fixed risk: Risk $1,000 per trade
shares = sizer.calculate_fixed_risk_size(
    entry_price=100.0,
    stop_loss=95.0,
    risk_dollars=1_000
)
# Returns 200 shares (200 × $5 = $1,000 risk)
```

#### 4. Optimal Multi-Constraint
Combines all methods, takes minimum (most conservative):

```python
sizing = sizer.calculate_optimal_position_size(
    signal=0.7,                      # Strong signal
    confidence=0.75,                 # High confidence
    current_price=100.0,
    volatility=0.15,                 # 15% annual
    stop_loss=95.0,
    win_rate=0.55,                   # Optional historical
    win_loss_ratio=1.5
)

print(f"Position size: {sizing['position_size_pct']:.2%}")
print(f"Shares: {sizing['shares']}")
print(f"Method: {sizing['method_used']}")
```

---

## Stop Loss & Profit Target Calculation

### Methods Available

```python
from risk_config_and_guidelines import StopLossCalculator

calc = StopLossCalculator(atr_multiplier=2.5, risk_reward_ratio=3.0)

# 1. ATR-based (Recommended)
stop, target = calc.calculate_atr_based(
    entry_price=100.0,
    atr=2.0,
    direction=1  # 1=long, -1=short
)

# 2. Fixed percentage
stop, target = calc.calculate_percentage_based(
    entry_price=100.0,
    stop_pct=0.02,  # 2% risk
    direction=1
)

# 3. Volatility-based
stop, target = calc.calculate_volatility_based(
    entry_price=100.0,
    volatility=0.15,
    std_dev_multiple=1.5,
    direction=1
)

# 4. Support/Resistance
stop, target = calc.calculate_support_resistance(
    entry_price=100.0,
    support=95.0,
    resistance=110.0,
    direction=1
)

# Get comprehensive recommendation
levels = calc.get_recommended_levels(
    entry_price=100.0,
    atr=2.0,
    volatility=0.15,
    direction=1
)

for method, values in levels['methods'].items():
    print(f"{method}: Stop ${values['stop_loss']:.2f}, "
          f"Target ${values['profit_target']:.2f}")
```

---

## Prometheus Alert Rules

Alert rules are configured in `/home/ajk/Nautilus/nautilus_trader/scripts/prometheus_alert_rules.yml`

### Key Alerts

| Alert | Condition | Action |
|-------|-----------|--------|
| Daily Loss Warning | Daily loss > 2% | Monitor, prepare to reduce |
| Daily Loss Critical | Daily loss > 5% | HALT TRADING immediately |
| Drawdown Warning | Drawdown > 10% | Reduce position sizes |
| Drawdown Critical | Drawdown > 20% | Circuit breaker active |
| Low Win Rate | Win rate < 35% | Review signals, reduce size |
| Position Concentration | Single position > 7.5% | Reduce to target 5% |
| High Correlation | Position pairs > 0.85 | Add hedges or diversify |
| High Leverage | Leverage > 2.5x | Reduce immediately |
| Negative Expectancy | Expectancy < 0 | Review strategy, pause trades |
| Heat Exhausted | Heat usage > 95% | Stop new trades |

### Deployment

```bash
# Copy alert rules to Prometheus
cp prometheus_alert_rules.yml /etc/prometheus/rules/

# Reload Prometheus
curl -X POST http://localhost:9090/-/reload
```

### Alert Severity Levels

- **INFO**: Monitoring, no action required
- **WARNING**: Elevated risk, prepare mitigations
- **CRITICAL**: High risk, immediate action required
- **ALERT**: Most severe, manual intervention needed

---

## Grafana Dashboard

### Dashboard Panels (10 rows)

1. **Portfolio Overview**
   - Portfolio Value (gauge)
   - Daily P&L (gauge)
   - Daily Loss % (gauge with thresholds)
   - Return YTD

2. **Drawdown & Circuit Breaker**
   - Current Drawdown %
   - Max Drawdown (time series)
   - Circuit Breaker Status

3. **Position Management**
   - Open Positions Count
   - Total Notional Exposure
   - Leverage Ratio (gauge)
   - Max Position Concentration
   - Position Size Distribution

4. **Risk Metrics**
   - Portfolio Volatility (annualized)
   - Value at Risk (VaR 95%)
   - Conditional VaR (CVaR)
   - Portfolio Beta
   - Correlation Matrix Heatmap

5. **Trade Performance**
   - Win Rate (last 20 trades)
   - Trade Expectancy
   - Consecutive Wins/Losses
   - Avg Win vs Avg Loss
   - Profit Factor

6. **Portfolio Heat & Capital**
   - Heat Usage % (gauge)
   - Available Heat in $
   - Heat Usage Over Time
   - Cash Position

7. **Market Conditions**
   - Current Regime (trending/mean-revert/choppy)
   - Regime Confidence
   - Historical Volatility
   - Correlation Heatmap

8. **Alerts & Warnings**
   - Active Alerts Status Table
   - Alert Count by Severity
   - Warning Log

9. **Performance Attribution**
   - PnL by Entry Regime
   - Win Rate by Signal Type
   - Average Holding Period
   - MAE/MFE Analysis

10. **Correlation & Hedging**
    - High Correlation Pairs
    - Portfolio Delta Exposure
    - Active Hedges Count
    - Hedge Notional Value

### View Queries

See `grafana_risk_dashboard_queries.md` for complete PromQL queries:

```promql
# Example: Portfolio Value over time
nautilus_portfolio_value

# Example: Daily Loss Alert
nautilus_daily_loss_pct > 0.02

# Example: Win Rate (last 20 trades)
nautilus_win_rate_20trades * 100
```

---

## Stress Testing & Scenarios

### Pre-built Scenarios

```python
from risk_config_and_guidelines import ScenarioAnalyzer

positions = {
    'SPY': 500_000,
    'QQQ': 300_000,
    'BND': 200_000
}

# Analyze different scenarios
scenarios = [
    'market_crash',      # S&P 500 -20%
    'volatility_spike',  # VIX to 40+
    'rate_shock',        # 2% rate increase
    'flash_crash',       # Intraday -10%
    'black_swan'         # Extreme -30%
]

for scenario_name in scenarios:
    scenario = ScenarioAnalyzer.STANDARD_SCENARIOS[scenario_name]
    result = ScenarioAnalyzer.analyze_scenario(positions, scenario)
    print(f"{scenario_name}: PnL ${result['total_pnl']:,.0f}")
```

### Custom Scenario

```python
custom_scenario = {
    'description': 'Tech sector selloff',
    'market_moves': {
        'QQQ': -0.15,      # -15%
        'SPY': -0.08,      # -8%
        'BND': 0.02        # +2% (flight to safety)
    },
    'vol_multiplier': 2.5
}

result = ScenarioAnalyzer.analyze_scenario(positions, custom_scenario)
print(f"Portfolio impact: {result['pnl_pct']:.2%}")
```

---

## Integration with Live Trading

### Example: Position Entry with Risk Management

```python
from risk_management_layer import PortfolioRiskManager
from risk_config_and_guidelines import PositionSizer, StopLossCalculator

# Initialize risk manager
risk_mgr = PortfolioRiskManager(portfolio_value=1_000_000)

# Entry signal detected
symbol = 'SPY'
entry_price = 450.0
signal_strength = 0.7
confidence = 0.75
current_volatility = 0.18
atr = 2.5

# Step 1: Calculate position size
sizer = PositionSizer(1_000_000, RiskProfile.MODERATE)
sizing = sizer.calculate_optimal_position_size(
    signal=signal_strength,
    confidence=confidence,
    current_price=entry_price,
    volatility=current_volatility,
    stop_loss=entry_price - atr * 2.5,
    win_rate=0.55,
    win_loss_ratio=1.5
)

# Step 2: Check pre-trade limits
stop_loss = entry_price - atr * 2.5
risk = sizing['notional_dollars'] * abs(entry_price - stop_loss) / entry_price

allowed, reasons = risk_mgr.check_pre_trade_limits(
    symbol=symbol,
    notional=sizing['notional_dollars'],
    required_risk=risk
)

if not allowed:
    print(f"Trade rejected: {reasons}")
    exit()

# Step 3: Calculate stops
calc = StopLossCalculator(atr_multiplier=2.5, risk_reward_ratio=3.0)
levels = calc.get_recommended_levels(entry_price, atr, current_volatility, direction=1)
stop_loss = levels['recommended']['stop_loss']
profit_target = levels['recommended']['profit_target']

# Step 4: Place trade
print(f"ENTER LONG: {symbol}")
print(f"  Shares: {sizing['shares']}")
print(f"  Entry: ${entry_price}")
print(f"  Stop: ${stop_loss}")
print(f"  Target: ${profit_target}")

# Step 5: Record position
risk_mgr.add_position(
    symbol=symbol,
    notional=sizing['notional_dollars'],
    risk=risk,
    sector='equities',
    beta=1.0
)

# Step 6: Monitor and exit
# ... monitor position ...
# On exit:
exit_price = 460.0
pnl = (exit_price - entry_price) * sizing['shares']
risk_mgr.close_position(symbol, pnl)

# Record trade for R-multiple analysis
risk_mgr.record_trade(
    trade_id='T001',
    symbol=symbol,
    entry_price=entry_price,
    exit_price=exit_price,
    stop_loss=stop_loss,
    shares=sizing['shares'],
    entry_time=datetime.now() - timedelta(hours=1),
    exit_time=datetime.now(),
    direction=1
)
```

---

## Performance Monitoring

### Daily Risk Report

```python
# Generate comprehensive daily report
risk_report = risk_mgr.get_risk_report()

print("DAILY RISK REPORT")
print(f"Portfolio Value: ${risk_report['portfolio_value']:,.0f}")
print(f"Expectancy: {risk_report['expectancy_metrics']['expectancy']:.2f}R")
print(f"Win Rate: {risk_report['expectancy_metrics']['win_rate']:.1%}")
print(f"Heat Used: {risk_report['heat_used_pct']:.1%}")
print(f"Leverage: {risk_report['concentration']['portfolio_leverage']:.2f}x")
print(f"Drawdown: {risk_report['circuit_breaker_status']['drawdown_pct']:.2%}")
print(f"Open Positions: {risk_report['num_open_positions']}")

if risk_report['circuit_breaker_status']['active']:
    print("WARNING: Circuit breaker ACTIVE")

for symbol1, symbol2, corr in risk_report['high_correlations']:
    print(f"High Correlation: {symbol1} - {symbol2}: {corr}")
```

### Export Trade Data

```python
# Export all trades to CSV for analysis
risk_mgr.r_tracker.export_trades('trades_2024.csv')

# Analyze in pandas
import pandas as pd
df = pd.read_csv('trades_2024.csv')
print(df.describe())
print(f"Win Rate: {(df['win'].sum() / len(df)):.1%}")
print(f"Avg R-multiple: {df['r_multiple'].mean():.2f}R")
```

---

## Best Practices

### 1. Define Clear Risk Limits
- Start conservative, increase gradually
- Document rationale for limits
- Review quarterly

### 2. Monitor Expectancy
- Minimum 20-30 trades for meaningful analysis
- Expectancy > 0.5R indicates profitable strategy
- < 0 indicates strategy needs improvement

### 3. Respect Heat Limits
- Never exceed portfolio heat allocation
- Reserve heat for high-conviction trades
- Track intra-day heat usage

### 4. Regular Rebalancing
- Monthly position review
- Quarterly correlation check
- Adjust hedge ratios quarterly

### 5. Scenario Planning
- Test strategy under stress scenarios
- Maintain adequate hedges
- Know exit prices in advance

### 6. Continuous Monitoring
- Check daily risk report
- Review Grafana dashboard weekly
- Act on alert thresholds promptly

### 7. Documentation
- Keep trade journal with rationale
- Document position changes
- Log all circuit breaker events

---

## Troubleshooting

### Low Win Rate Alert
**Problem:** Win rate below 35%
**Causes:**
- Market regime change (trends to mean reversion)
- Signal threshold too low
- Market structure changed
**Solutions:**
- Increase signal confidence threshold
- Reduce position sizes
- Add regime filter
- Review backtest assumptions

### High Concentration
**Problem:** Single position > 7.5%
**Causes:**
- Position moved against you (underwater)
- Profitably running trade
- Partial liquidation failed
**Solutions:**
- Set hard position size limits
- Trim winners regularly
- Use trailing stops
- Implement sector limits

### Circuit Breaker Triggered
**Problem:** Daily loss > 5% or drawdown > 20%
**Causes:**
- Unusual market move
- Correlation breakdown
- Risk model failure
**Solutions:**
- Review all positions
- Close highest-risk trades first
- Increase stop-loss width
- Investigate root cause

### Expectancy Negative
**Problem:** Strategy losing on average
**Causes:**
- Win rate < break-even
- Avg loss > avg win
- Slippage not accounted for
**Solutions:**
- Improve signal quality
- Tighten stop losses (reduce avg loss)
- Increase profit targets
- Reduce position size

---

## Files and Locations

| File | Purpose | Location |
|------|---------|----------|
| Risk Management Core | Main risk module | `/home/ajk/Nautilus/nautilus_trader/scripts/risk_management_layer.py` |
| Configuration | Position sizing + profiles | `/home/ajk/Nautilus/nautilus_trader/scripts/risk_config_and_guidelines.py` |
| Prometheus Alerts | Alert rules YAML | `/home/ajk/Nautilus/nautilus_trader/scripts/prometheus_alert_rules.yml` |
| Grafana Queries | Dashboard query guide | `/home/ajk/Nautilus/nautilus_trader/scripts/grafana_risk_dashboard_queries.md` |
| This Document | Full documentation | `/home/ajk/Nautilus/nautilus_trader/scripts/RISK_MANAGEMENT_README.md` |

---

## Support & Further Reading

### Internal Documentation
- Strategy: `/home/ajk/Nautilus/demos/advanced_multi_factor_strategy.py`
- Infrastructure: Prometheus/Grafana setup guide

### External References
- Kelly Criterion: https://en.wikipedia.org/wiki/Kelly_criterion
- Value at Risk: https://en.wikipedia.org/wiki/Value_at_risk
- Position Sizing: https://www.investopedia.com/terms/p/positionsizing.asp

---

## Contact & Updates

For issues, questions, or improvements:
1. Review RISK_MANAGEMENT_README.md (this file)
2. Check example usage in each module
3. Review test outputs for typical behavior

Last Updated: 2025-12-09
Version: 1.0.0
