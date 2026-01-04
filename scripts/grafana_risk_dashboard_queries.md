# Grafana Risk Dashboard Queries for Multi-Factor Strategy

This document contains PromQL queries for visualizing real-time risk metrics in Grafana.

## Dashboard Setup

1. Data Source: Prometheus (http://localhost:9090)
2. Refresh rate: 30 seconds
3. Time range: Last 1 hour (with zoom capability)
4. Alerts: Connected to alert rules in prometheus_alert_rules.yml

---

## 1. PORTFOLIO OVERVIEW ROW

### Portfolio Value (Gauge + Time Series)

```promql
# Current Portfolio Value
nautilus_portfolio_value

# Portfolio Value Over Time
nautilus_portfolio_value
```

**Panel Type**: Graph with discrete line
**Units**: $ USD
**Thresholds**: Warning at -2% daily, Critical at -5%

### Daily P&L (Gauge)

```promql
# Daily Profit/Loss in dollars
nautilus_daily_pnl
```

**Panel Type**: Gauge
**Units**: $ USD
**Color**: Green if positive, Red if negative

### Daily Loss % (Gauge with Thresholds)

```promql
# Daily loss as percentage
nautilus_daily_loss_pct * 100
```

**Panel Type**: Gauge
**Units**: %
**Thresholds**:
- Green: 0-2%
- Yellow: 2-5% (Warning)
- Red: 5-100% (Critical - Stop Trading)

### Return YTD (Single Value)

```promql
# Year-to-date return
(nautilus_portfolio_value - on() group_left nautilus_ytd_start_value) / on() group_left nautilus_ytd_start_value
```

---

## 2. DRAWDOWN & CIRCUIT BREAKER ROW

### Current Drawdown % (Gauge)

```promql
# Percentage drawdown from peak
nautilus_drawdown_pct * 100
```

**Panel Type**: Gauge
**Units**: %
**Thresholds**:
- Green: 0-5%
- Yellow: 5-10% (Warning)
- Orange: 10-20%
- Red: 20-100% (Critical - Circuit Breaker)

### Max Drawdown (Time Series)

```promql
# Rolling maximum drawdown
max(nautilus_drawdown_pct) over (1h)
```

**Panel Type**: Graph with area
**Units**: %

### Circuit Breaker Status (Alert Box)

```promql
# Alert if circuit breaker is active
nautilus_circuit_breaker_active
```

**Panel Type**: Status (custom visualization)
**Status**:
- 0 = Green (Normal)
- 1 = Red (Halted)

### Daily Loss Alert State

```promql
# Alert if daily loss exceeds limits
nautilus_daily_loss_pct > 0.05
```

---

## 3. POSITION MANAGEMENT ROW

### Open Positions Count (Single Value)

```promql
# Number of currently open positions
nautilus_num_open_positions
```

**Panel Type**: Single Value
**Units**: Count

### Total Notional Exposure (Gauge)

```promql
# Total position notional value
nautilus_total_notional
```

**Panel Type**: Gauge
**Units**: $ USD

### Leverage Ratio (Gauge)

```promql
# Portfolio leverage (notional / equity)
nautilus_leverage_ratio
```

**Panel Type**: Gauge
**Units**: x
**Thresholds**:
- Green: 0-1.5x
- Yellow: 1.5-2.0x (Elevated)
- Orange: 2.0-2.5x
- Red: 2.5-3.0x (Critical)

### Max Position Concentration (Gauge)

```promql
# Largest single position as % of portfolio
nautilus_max_position_pct * 100
```

**Panel Type**: Gauge
**Units**: %
**Thresholds**:
- Green: 0-3%
- Yellow: 3-5% (Target)
- Orange: 5-7.5%
- Red: 7.5-100% (Warning)

### Position Size Distribution (Bar Chart)

```promql
# All positions ranked by size
sort_desc(nautilus_position_notional{symbol!=""})
```

**Panel Type**: Bar chart (horizontal)
**Group by**: Symbol
**Units**: $ USD

---

## 4. RISK METRICS ROW

### Portfolio Volatility (Annualized) (Gauge)

```promql
# Annualized portfolio volatility
nautilus_portfolio_volatility * 100
```

**Panel Type**: Gauge
**Units**: %
**Thresholds**:
- Green: 0-15%
- Yellow: 15-25%
- Orange: 25-50%
- Red: 50-100%

### Value at Risk 95% (Gauge)

```promql
# VaR at 95% confidence level
nautilus_var_95_pct * 100
```

**Panel Type**: Gauge
**Units**: %
**Interpretation**: "5% probability of loss exceeding X%"

### Conditional Value at Risk (CVaR 95%)

```promql
# Expected Shortfall - mean loss beyond VaR
nautilus_cvar_95_pct * 100
```

**Panel Type**: Single Value
**Units**: %

### Portfolio Beta (Gauge)

```promql
# Beta relative to market index
nautilus_portfolio_beta
```

**Panel Type**: Gauge
**Units**: (unitless)
**Interpretation**:
- 1.0 = market neutral
- >1.0 = more volatile than market
- <1.0 = less volatile than market

### Correlation Matrix Heatmap

```promql
# Correlation between all open positions
nautilus_correlation_matrix{symbol1!="", symbol2!=""}
```

**Panel Type**: Heatmap
**Show**: Correlation values between position pairs

---

## 5. TRADE PERFORMANCE ROW

### Win Rate - Last 20 Trades (Gauge)

```promql
# Percentage of winning trades in rolling 20
nautilus_win_rate_20trades * 100
```

**Panel Type**: Gauge
**Units**: %
**Thresholds**:
- Green: 50-100%
- Yellow: 35-50%
- Red: 0-35% (Below acceptable threshold)

### Trade Expectancy (Single Value)

```promql
# Expected return per trade in R-multiples
nautilus_trade_expectancy
```

**Panel Type**: Single Value
**Units**: R
**Interpretation**:
- >0.5R = Profitable on average
- 0 to 0.5R = Marginal
- <0 = Losing on average

### Consecutive Wins/Losses (Table)

```promql
# Current streak of wins or losses
{__name__=~"nautilus_consecutive_wins|nautilus_consecutive_losses"}
```

**Panel Type**: Table
**Columns**: Metric, Value

### Avg Win vs Avg Loss (Bar Chart)

```promql
{__name__=~"nautilus_avg_win_r|nautilus_avg_loss_r"}
```

**Panel Type**: Bar chart
**Units**: R-multiples

### Profit Factor (Single Value)

```promql
# Gross profit / abs(Gross loss)
nautilus_profit_factor
```

**Panel Type**: Single Value
**Threshold**: >1.5 is good

### Total Trades Count (Single Value)

```promql
nautilus_total_trades_all_time
```

---

## 6. PORTFOLIO HEAT & CAPITAL ALLOCATION ROW

### Heat Usage % (Gauge)

```promql
# Risk capital used vs. available
nautilus_heat_used_pct * 100
```

**Panel Type**: Gauge
**Units**: %
**Thresholds**:
- Green: 0-50%
- Yellow: 50-75% (Elevated)
- Orange: 75-95%
- Red: 95-100% (Nearly Exhausted)

### Available Heat in $ (Single Value)

```promql
# Remaining risk capital available
nautilus_available_heat_dollars
```

**Panel Type**: Single Value
**Units**: $ USD

### Heat Usage Over Time (Area Chart)

```promql
# Historical heat usage
nautilus_heat_used_pct * 100
```

**Panel Type**: Area chart
**Stack**: True

### Cash Position (Gauge)

```promql
# Current cash available for trades
nautilus_cash_available
```

**Panel Type**: Gauge
**Units**: $ USD

---

## 7. MARKET CONDITIONS ROW

### Market Regime (Status)

```promql
# Current detected regime
nautilus_regime_type
```

**Panel Type**: Status indicator
**Values**:
- 0 = Trending (Blue)
- 1 = Mean Reverting (Green)
- 2 = Choppy (Yellow)
- 3 = Volatile (Red)

### Regime Confidence (Gauge)

```promql
# Confidence in regime detection
nautilus_regime_confidence * 100
```

**Panel Type**: Gauge
**Units**: %

### Historical Volatility (Time Series)

```promql
# Volatility over time
nautilus_portfolio_volatility * 100
```

**Panel Type**: Area chart
**Units**: %

### Correlation Heatmap (Recent)

```promql
# Real-time correlation matrix
nautilus_correlation_pair
```

**Panel Type**: Heatmap

---

## 8. ALERTS & WARNINGS ROW

### Active Alerts Status Table

```promql
# All active alerts
ALERTS{alertstate="firing", strategy="multi_factor"}
```

**Panel Type**: Table
**Columns**: Alert Name, Severity, Value, Timestamp

### Alert Count by Severity

```promql
count by(severity) (ALERTS{alertstate="firing", strategy="multi_factor"})
```

**Panel Type**: Pie chart

### Warning Log (Recent 10)

```promql
# Query alert history from logs if available
```

---

## 9. PERFORMANCE ATTRIBUTION ROW

### PnL by Entry Regime (Bar Chart)

```promql
# Cumulative PnL by regime at entry
sum by(entry_regime) (nautilus_trade_pnl)
```

**Panel Type**: Bar chart
**Units**: $ USD

### Win Rate by Signal Type (Table)

```promql
# Win rate breakdown by signal
avg by(signal_type) (nautilus_signal_win_rate)
```

**Panel Type**: Table

### Average Holding Period (Gauge)

```promql
nautilus_avg_holding_period_minutes
```

**Panel Type**: Single Value
**Units**: minutes

### MAE/MFE Analysis

```promql
# Maximum Adverse/Favorable Excursion
{__name__=~"nautilus_avg_mae|nautilus_avg_mfe"}
```

**Panel Type**: Bar chart
**Units**: %

---

## 10. CORRELATION & HEDGING ROW

### High Correlation Pairs (Table)

```promql
# All pairs with correlation > 0.80
nautilus_correlation_pair{value > 0.80}
```

**Panel Type**: Table
**Columns**: Symbol1, Symbol2, Correlation

### Portfolio Delta Exposure (Gauge)

```promql
# Total portfolio directional exposure
nautilus_portfolio_delta
```

**Panel Type**: Gauge
**Units**: (unitless delta)
**Target**: 0.0 for market neutral

### Active Hedges Count (Single Value)

```promql
nautilus_num_active_hedges
```

**Panel Type**: Single Value

### Hedge Notional (Gauge)

```promql
nautilus_total_hedge_notional
```

**Panel Type**: Gauge
**Units**: $ USD

---

## QUERY TEMPLATE FORMAT

For custom panels, use this template:

```promql
# Component: [Component Name]
# Purpose: [What metric this shows]
# Thresholds: [Alert thresholds if any]
# Interpretation: [What the numbers mean]

# PromQL Query:
[query_here]
```

---

## DASHBOARD LAYOUT RECOMMENDATIONS

### Screen 1: Executive Summary (60 seconds)
- Portfolio Value (large)
- Daily P&L
- Daily Loss %
- Drawdown %
- Win Rate (last 20)
- Leverage

### Screen 2: Risk & Position Management (2 minutes)
- Heat Usage
- Position Concentration
- Leverage Ratio
- Open Positions Count
- VaR 95%
- Portfolio Volatility

### Screen 3: Trade Analysis (3 minutes)
- Win Rate + consecutive wins/losses
- Expectancy
- Profit Factor
- Avg Win vs Loss
- Trade distribution over time
- MAE/MFE analysis

### Screen 4: Alerts & Warnings (1 minute)
- Circuit breaker status
- Active alerts
- Alert history
- Risk status summary

---

## ALERT RULE INTEGRATION

Connect these queries to the alert rules in `prometheus_alert_rules.yml`:

```yaml
- Daily Loss: nautilus_daily_loss_pct > 0.02 (warning), > 0.05 (critical)
- Drawdown: nautilus_drawdown_pct > 0.10 (warning), > 0.20 (critical)
- Win Rate: nautilus_win_rate_20trades < 0.35 (warning)
- Concentration: nautilus_max_position_pct > 0.075 (warning)
- Leverage: nautilus_leverage_ratio > 2.0 (warning), > 2.5 (critical)
- Heat: nautilus_heat_used_pct > 0.75 (warning), > 0.95 (critical)
```

---

## TESTING QUERIES

Use these to test metric collection:

```promql
# Check if metrics are being collected
up{job="risk_manager"}

# Show all risk metrics
{job="risk_manager"}

# Find any NaN values (gaps)
nautilus_portfolio_value

# Check for stale data
time() - nautilus_last_update_timestamp > 60

# Verify alert firing
ALERTS{job="risk_manager"}
```

---

## PERFORMANCE TIPS

1. **Avoid high-cardinality queries**: Use specific labels
2. **Use recording rules** for frequently accessed aggregations
3. **Set appropriate scrape intervals**: 30 seconds is typical for risk metrics
4. **Cache dashboards** for 5+ minute time ranges
5. **Use `by()` not `without()`** for better label handling
