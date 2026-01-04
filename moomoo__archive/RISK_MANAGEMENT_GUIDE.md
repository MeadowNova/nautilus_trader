# Risk Management Framework for NautilusTrader
## Paper Trading System - US Equities & Options

This document describes a production-ready risk management framework designed for NautilusTrader paper trading with Moomoo, covering position-level and portfolio-level controls, expectancy calculations, and monitoring requirements.

---

## Architecture Overview

### Components

1. **Risk Framework** (`risk_management_framework.py`)
   - Core risk calculation engines
   - Position and portfolio metrics
   - R-multiple tracking
   - Monte Carlo simulation

2. **Risk Management Actor** (`risk_management_actor.py`)
   - NautilusTrader Actor component
   - Real-time monitoring and alerts
   - Custom data type publishing
   - Risk report generation

3. **Integration Points**
   - Strategy layer: Position entry/exit signals
   - Portfolio layer: Account state monitoring
   - Data layer: Custom risk alerts and metrics

---

## 1. POSITION-LEVEL CONTROLS

### 1.1 Maximum Position Size

#### Configuration
```python
PositionRiskConfig(
    max_position_size_usd=25000.0,  # Max $25k per position
    max_position_size_pct_account=0.05,  # Max 5% of account
)
```

#### Logic
- Hard stop at whichever is most restrictive
- Applied at order submission time
- Example for $500k account:
  - Absolute limit: $25,000
  - Percentage limit: $25,000 (5% of $500k)
  - Effective limit: $25,000

### 1.2 Stop-Loss Calculation

#### ATR-Based (Recommended)
```python
from risk_management_framework import StopLossEngine

# Example: TSLA at $250, ATR = $5
stop_price = StopLossEngine.atr_based(
    entry_price=250.0,
    atr_value=5.0,
    atr_multiple=2.0,  # 2x ATR
    direction="LONG"
)
# Returns: $240 (2x$5 stop below entry)
```

**Why ATR-Based?**
- Adjusts to market volatility
- Avoids stops too tight (whipsaws) or too wide (excessive risk)
- Standard practice in professional trading

#### Alternative: Percentage-Based
```python
stop_price = StopLossEngine.percentage_based(
    entry_price=250.0,
    stop_loss_pct=0.02,  # 2% stop
    direction="LONG"
)
# Returns: $245
```

#### Alternative: Swing Point
```python
stop_price = StopLossEngine.swing_point(
    recent_lows=[242, 243, 241, 244, 240],
    entry_price=250.0,
    direction="LONG"
)
# Returns: $240 (lowest recent price)
```

### 1.3 Take-Profit Levels

#### Risk-to-Reward Ratio (Core Method)
```python
from risk_management_framework import TakeProfitEngine

# Setup
entry = 250.0
stop = 240.0  # $10 risk
rr_ratio = 2.0  # 2:1 target

tp = TakeProfitEngine.risk_reward_based(
    entry_price=entry,
    stop_loss_price=stop,
    rr_ratio=rr_ratio,
    direction="LONG"
)
# Returns: $270 (2x$10 reward above entry)
# Risk: $10 per share, Reward: $20 per share
```

**Why 2:1?**
- Requires only 33% win rate to be profitable
- Professional standard: (0.33 × $20) - (0.67 × $10) = $6.60 - $6.70 = ~$0 expectancy
- With proper win rate > 35%: positive expectancy

#### Alternative: ATR-Based
```python
tp = TakeProfitEngine.atr_based(
    entry_price=250.0,
    atr_value=5.0,
    atr_multiple=4.0,  # 4x ATR target
    direction="LONG"
)
# Returns: $270 (entry + 4x$5)
```

### 1.4 R-Multiple Tracking

Each trade is normalized to "R" (Risk units) for consistent performance measurement:

```python
# Trade Setup
entry_price = 100.0
stop_loss_price = 95.0
r_value = abs(100.0 - 95.0) = $5.00 per share
position_size = 1000 shares
total_risk = $5,000 (1R)

# Trade Outcomes
Scenario A: Close at $105
  Profit = $5,000 (1000 × $5)
  R-Multiple = +1.0R (break-even with perfect risk/reward)

Scenario B: Close at $110
  Profit = $10,000 (1000 × $5)
  R-Multiple = +2.0R (2x risk amount gained)

Scenario C: Close at $95 (hit stop)
  Loss = -$5,000 (1000 × $5)
  R-Multiple = -1.0R (lost entire risk)
```

**Benefits of R-Multiple Tracking:**
- Normalize wins/losses across different position sizes
- Measure strategy edge consistently
- Calculate expectancy independent of trade size
- Compare trades fairly (large vs. small positions)

---

## 2. PORTFOLIO-LEVEL CONTROLS

### 2.1 Exposure Limits

#### Gross Exposure
Sum of absolute values of all positions regardless of direction.

```python
PortfolioRiskConfig(
    max_gross_exposure=1.0,  # 100% of account
)

# Example: $500k account
# 2 LONG positions: $250k, $150k
# 1 SHORT position: $100k
# Gross: $250k + $150k + $100k = $500k (100%)
# Status: OK
```

**Use Case:**
- Prevent over-leveraging
- Ensure position liquidity on exit
- Margin availability check

#### Net Exposure
Sum of signed position values (LONG positive, SHORT negative).

```python
PortfolioRiskConfig(
    max_net_exposure=0.75,  # 75% net directional bias
)

# Example with same positions above:
# Net: $250k + $150k - $100k = $300k (60%)
# Status: OK
```

**Use Case:**
- Hedge directional risk
- Balanced portfolio
- Prevent single-direction crash risk

### 2.2 Sector Concentration

Prevent over-exposure to correlated instruments:

```python
PortfolioRiskConfig(
    max_single_sector_exposure=0.30,  # 30% per sector
)

# Example: Tech sector
# AAPL:    $100k
# MSFT:    $75k
# NVDA:    $50k
# Total:   $225k / $500k = 45% (BREACH)
```

**Sectors to Track:**
- Technology
- Healthcare
- Financials
- Consumer Discretionary
- Energy
- Industrials
- Materials
- Real Estate
- Utilities
- Communications

### 2.3 Daily Loss Limits

Hard stop-loss for the trading day:

```python
PortfolioRiskConfig(
    max_daily_loss_pct=0.05,  # 5% daily stop
)

# Example: $500k account
# Daily stop at: $500k × 0.05 = $25k loss
# If losses reach -$25k: CIRCUIT BREAKER (halt new trades)
```

**Circuit Breaker Actions:**
1. No new position entries
2. Close losing positions (oldest first)
3. Manual review required to resume

### 2.4 Maximum Drawdown

Track account peak and prevent catastrophic losses:

```python
PortfolioRiskConfig(
    max_drawdown_pct=0.10,  # 10% max drawdown
)

# Example
# Peak equity:  $500k
# Current:      $450k
# Drawdown:     10%
# Status:       AT LIMIT
```

**Implementation:**
- Update peak equity after every profitable day
- Monitor drawdown in real-time
- Reduce position sizes if approaching limit

---

## 3. TRADE TRACKING & EXPECTANCY

### 3.1 R-Multiple Performance Record

Track all trades in standardized R format:

```python
from risk_management_framework import RMeasurement

r_measurement = RMeasurement()

# After 20 trades
r_measurement.winning_trades = 8
r_measurement.losing_trades = 12
r_measurement.total_r_gained = 16.5  # Sum of all winning R's
r_measurement.total_r_lost = 12.0    # Sum of all losing R's

# Calculate metrics
win_rate = 8 / 20 = 0.40 (40%)
avg_win = 16.5 / 8 = 2.06R
avg_loss = 12.0 / 12 = 1.0R

expectancy = (0.40 × 2.06) - (0.60 × 1.0)
           = 0.824 - 0.600
           = 0.224R (22.4 cents per R risked)
```

### 3.2 Expectancy Calculation

Expectancy tells you how much you expect to win per trade on average:

```python
def calculate_expectancy(
    win_rate: float,
    avg_win_r: float,
    avg_loss_r: float,
) -> float:
    """
    Expectancy = (Win% × Avg Win) - (Loss% × Avg Loss)

    Interpretation:
    - Positive > 0.0: Strategy is profitable long-term
    - Zero = 0.0: Break-even strategy
    - Negative < 0.0: Strategy loses money long-term

    Minimum viable: Expectancy >= 0.05R (5% edge)
    """
    return (win_rate * avg_win_r) - ((1 - win_rate) * avg_loss_r)
```

**Example Scenarios:**

Scenario A: Consistent Strategy
```
Win Rate: 40%, Avg Win: 2R, Avg Loss: 1R
Expectancy = (0.40 × 2) - (0.60 × 1) = +0.20R ✓ Viable
```

Scenario B: High Win Rate, Low Win Size
```
Win Rate: 60%, Avg Win: 1R, Avg Loss: 1.5R
Expectancy = (0.60 × 1) - (0.40 × 1.5) = 0R ✗ Break-even
```

Scenario C: Low Win Rate, High Win Size
```
Win Rate: 30%, Avg Win: 3R, Avg Loss: 1R
Expectancy = (0.30 × 3) - (0.70 × 1) = +0.20R ✓ Viable
```

### 3.3 Profit Factor

Ratio of total wins to total losses:

```python
profit_factor = total_r_gained / total_r_lost

# Example:
# Total wins:  $10,000
# Total losses: $6,000
# Profit Factor = 10,000 / 6,000 = 1.67x

# Interpretation:
# > 1.5: Excellent (make $1.50 for every $1 lost)
# 1.2-1.5: Good
# 1.0-1.2: Marginal (risky)
# < 1.0: Unprofitable
```

### 3.4 Win Rate Threshold

Minimum win rate needed to break even at different R-multiples:

```
If targeting 2:1 RR ratio (Risk:Reward):
  Min Win Rate = Risk / (Risk + Reward)
               = 1 / (1 + 2)
               = 33%

If targeting 3:1 RR ratio:
  Min Win Rate = 1 / (1 + 3) = 25%

If targeting 1.5:1 RR ratio:
  Min Win Rate = 1 / (1 + 1.5) = 40%
```

---

## 4. POSITION SIZING

### 4.1 Fixed Fractional Sizing (Core Method)

Risk a fixed percentage of account per trade:

```python
from risk_management_framework import PositionSizer

size = PositionSizer.fixed_fraction(
    account_size=500000.0,
    risk_per_trade_pct=0.02,  # Risk 2% per trade
    entry_price=100.0,
    stop_loss_price=95.0,
)
# Risk per trade = $500k × 0.02 = $10,000
# Price risk = $5 (100 - 95)
# Position size = $10,000 / $5 = 2,000 shares
```

**Sizing Strategy by Win Rate:**

Conservative (Win Rate < 40%):
```
Risk 1% per trade
Drawdown protection: Can lose 14 consecutive trades before 10% drawdown
```

Moderate (Win Rate 40-50%):
```
Risk 2% per trade
Drawdown protection: Can lose 7 consecutive trades before 10% drawdown
```

Aggressive (Win Rate > 50%, High Expectancy):
```
Risk 3% per trade
Use only after proven strategy
```

### 4.2 Kelly Criterion Sizing

Optimal position sizing based on your edge:

```python
kelly_pct = PositionSizer.kelly_criterion(
    win_rate=0.45,
    avg_win_r=2.0,
    avg_loss_r=1.0,
    kelly_multiplier=0.25,  # Use fractional Kelly
)
# Full Kelly = 0.225 (22.5%)
# Fractional Kelly (1/4) = 0.05625 (5.6%)
# Recommended position size = account × 5.6%
```

**Why Fractional Kelly?**
- Full Kelly is optimal theoretically but dangerous in practice
- Single drawdown can wipe out gains
- 1/4 Kelly provides 96% of growth with 25% of volatility
- Recommended: 1/4 to 1/2 Kelly for paper trading

### 4.3 Volatility-Adjusted Sizing

Reduce size when volatility is high:

```python
size = PositionSizer.volatility_adjusted(
    account_size=500000.0,
    atr_value=10.0,  # Current ATR
    entry_price=100.0,
    atr_multiple=2.0,
    risk_pct=0.02,  # 2% risk
)
# High ATR (volatile) = larger stop = smaller position
# Low ATR (stable) = smaller stop = larger position
```

---

## 5. MONITORING REQUIREMENTS

### 5.1 Real-Time P&L Tracking

Each position tracks:

```python
PositionMetrics(
    pnl_unrealized=5000.0,      # Current P&L
    pnl_realized=2500.0,        # Closed trades P&L
    pnl_pct=2.5,                # Return % on position
    r_multiple=1.5,             # Current R-multiple
    max_favorable_move=3500.0,  # Best during holding
    max_adverse_move=-1200.0,   # Worst during holding
    bars_held=42,               # Duration
)
```

**Update Frequency:**
- On every price tick
- On every trade execution
- Minimum every 1 minute (for daily reports)

### 5.2 Margin Utilization (Options)

Track margin requirements:

```python
PortfolioMetrics(
    margin_used=125000.0,        # Current margin
    margin_available=375000.0,   # Available margin
)

margin_pct = margin_used / (margin_used + margin_available)
# 25% utilization = OK (limit 80%)
```

**Margin Sources:**
- Equity short positions: 30% of notional
- Cash-secured puts: 100% of strike × quantity
- Spreads: Reduced margin (credit spreads: difference only)

### 5.3 Options Greeks Aggregation

Sum Greeks across all options positions:

```python
PortfolioMetrics(
    portfolio_delta=0.35,    # 35% directional exposure
    portfolio_gamma=0.05,    # 5% gamma per 1% move
    portfolio_vega=50.0,     # +$50 per 1% IV increase
    portfolio_theta=-100.0,  # -$100 per day decay
)
```

**Greeks Monitoring:**

Delta:
- Monitor directional exposure
- Limit: Keep under 30% per GreeksConfig
- Action: Add hedge if approaching limit

Gamma:
- Measures delta acceleration
- High gamma in short options = risk
- Limit: Keep under 5% per GreeksConfig

Vega:
- Volatility exposure
- Long calls/puts: positive vega (want IV to rise)
- Short options: negative vega (want IV to fall)
- Limit: Keep under 25 vega per GreeksConfig

Theta:
- Time decay exposure
- Long options: negative theta (time works against)
- Short options: positive theta (time helps)
- Monitor daily theta decay vs. P&L target

---

## 6. RISK ALERTS & CIRCUIT BREAKERS

### 6.1 Alert Levels

| Level | Trigger | Action |
|-------|---------|--------|
| OK | All checks pass | Continue normal trading |
| WARNING | 1-2 limits approaching | Log alert, consider reduction |
| CRITICAL | 3+ limits exceeded | Reduce position sizes |
| BREACH | Hard limit crossed | Circuit breaker: halt new trades |

### 6.2 Circuit Breaker Logic

```python
# Daily loss limit breach
if daily_pnl < account_size * max_daily_loss_pct:
    HALT_NEW_TRADES = True
    CLOSE_OLDEST_LOSERS = True
    REQUIRE_MANUAL_OVERRIDE = True

# Drawdown limit breach
if (peak_equity - current_equity) / peak_equity > max_drawdown_pct:
    HALT_NEW_TRADES = True
    REDUCE_GROSS_EXPOSURE = True

# Losing streak limit
if consecutive_losses > max_losing_streak:
    HALT_NEW_TRADES = True
    REVIEW_STRATEGY = True
```

### 6.3 Risk Alert Hierarchy

```
LEVEL 1 - Position Size Breach
  Issue: Single position > max allowed
  Action: Reduce position to within limits

LEVEL 2 - Exposure Breach
  Issue: Gross/net exposure exceeded
  Action: Reduce positions (oldest first)

LEVEL 3 - Sector Concentration
  Issue: Sector concentration > limit
  Action: Close correlated positions

LEVEL 4 - Daily Loss Limit
  Issue: Daily loss >= threshold
  Action: CIRCUIT BREAKER ENGAGED

LEVEL 5 - Drawdown Limit
  Issue: Drawdown >= threshold
  Action: Reduce size 50%, manual review required
```

---

## 7. IMPLEMENTATION CHECKLIST

### Phase 1: Core Risk Framework
- [ ] Implement `PositionRiskConfig` with your parameters
- [ ] Implement `PortfolioRiskConfig` with your limits
- [ ] Implement `GreeksConfig` for options monitoring
- [ ] Create position sizing calculator

### Phase 2: Position Tracking
- [ ] Add `TradeEntry` recording on order execution
- [ ] Track `PositionMetrics` (P&L, R-multiple, Greeks)
- [ ] Calculate stop-loss on entry (ATR-based)
- [ ] Calculate take-profit on entry (2:1 RR)

### Phase 3: Portfolio Monitoring
- [ ] Implement `RMeasurement` for all trades
- [ ] Calculate expectancy after minimum 20 trades
- [ ] Monitor win rate and profit factor
- [ ] Track cumulative R-gains/losses

### Phase 4: Real-Time Risk Checks
- [ ] Implement position-level risk check (5-min intervals)
- [ ] Implement portfolio-level risk check (5-min intervals)
- [ ] Generate risk alerts (publish as custom data)
- [ ] Log warnings and breaches

### Phase 5: Advanced Monitoring
- [ ] Aggregate Greeks across options positions
- [ ] Monitor margin utilization
- [ ] Track daily loss and drawdown
- [ ] Implement circuit breaker logic

### Phase 6: Reporting & Analysis
- [ ] Generate position reports (15-min intervals)
- [ ] Generate portfolio snapshots (15-min intervals)
- [ ] Publish risk alerts (real-time)
- [ ] Build risk dashboard

### Phase 7: Stress Testing
- [ ] Run Monte Carlo drawdown simulations
- [ ] Simulate price paths (30 days, 1000 paths)
- [ ] Test strategy under adverse scenarios
- [ ] Verify position sizing under different win rates

---

## 8. EXAMPLE USAGE

### Creating the Risk Management Actor

```python
from risk_management_actor import RiskManagementActor, RiskManagementActorConfig

# Configure risk parameters
config = RiskManagementActorConfig(
    actor_id=ActorId("RISK-MGR-001"),

    # Position limits
    position_max_size_usd=25000.0,
    position_max_pct_account=0.05,
    position_stop_loss_atr_multiple=2.0,
    position_take_profit_rr=2.0,
    position_max_losing_streak=3,
    position_min_win_rate=0.35,

    # Portfolio limits
    portfolio_max_gross_exposure=1.0,
    portfolio_max_net_exposure=0.75,
    portfolio_max_sector_exposure=0.30,
    portfolio_max_daily_loss_pct=0.05,
    portfolio_max_drawdown_pct=0.10,
    portfolio_margin_limit=0.80,

    # Options Greeks
    greeks_delta_limit=0.30,
    greeks_gamma_limit=0.05,
    greeks_vega_limit=0.25,

    # Monitoring frequency
    risk_check_interval_minutes=5,
    report_interval_minutes=15,
)

# Create actor
risk_actor = RiskManagementActor(config)
```

### Recording a Trade

```python
# Strategy enters position
trade_entry = TradeEntry(
    instrument_id="TSLA.NASDAQ",
    entry_price=250.0,
    entry_size=100,
    entry_time=datetime.now(),
    r_value=5.0,  # $5 risk per share = $500 total risk
    stop_loss_price=245.0,
    take_profit_price=260.0,
)

# Add to position tracker
position.trades.append(trade_entry)
```

### Checking Position Risk

```python
from risk_management_framework import RiskMonitor

risk_level, issues = risk_monitor.check_position_risk(
    position,
    account_size=500000.0
)

if risk_level == RiskLevel.BREACH:
    # Reduce position immediately
    print(f"BREACH: {issues}")
elif risk_level == RiskLevel.CRITICAL:
    # Warn user
    print(f"CRITICAL: {issues}")
```

### Calculating Position Size

```python
from risk_management_framework import PositionSizer

size = PositionSizer.fixed_fraction(
    account_size=500000.0,
    risk_per_trade_pct=0.02,
    entry_price=250.0,
    stop_loss_price=245.0,
)
print(f"Recommended position size: {size} shares")
```

### Generating Reports

```python
from risk_management_framework import RiskReporter

# Position report
pos_report = RiskReporter.generate_position_report(position, account_size)
print(f"Position P&L: {pos_report['pnl_unrealized']}")
print(f"R-Multiple: {pos_report['r_multiple']}")

# Portfolio report
port_report = RiskReporter.generate_portfolio_report(portfolio)
print(f"Expectancy: {port_report['expectancy']}R")
print(f"Profit Factor: {port_report['profit_factor']}")

# Expectancy report
exp_report = RiskReporter.generate_expectancy_report(r_measurement)
print(f"Win Rate: {exp_report['win_rate']}%")
print(f"Kelly %: {exp_report['kelly_percentage']}%")
```

### Monte Carlo Stress Testing

```python
from risk_management_framework import MonteCarloSimulator

# Test strategy with current metrics
sim_results = MonteCarloSimulator.simulate_drawdown(
    win_rate=0.42,
    avg_win_r=2.1,
    avg_loss_r=1.0,
    num_trades=100,
    num_simulations=1000,
)

print(f"Expected final capital: {sim_results['expected_final_capital']}")
print(f"Worst case (95th %ile): {sim_results['best_case_capital']}")
print(f"Avg max drawdown: {sim_results['avg_max_drawdown_pct']}%")
```

---

## 9. CONFIGURATION RECOMMENDATIONS

### Conservative (Learning Phase)
```python
PositionRiskConfig(
    max_position_size_usd=10000.0,      # Small positions
    max_position_size_pct_account=0.02,  # 2% max
    stop_loss_atr_multiple=2.5,         # Wider stops
)

PortfolioRiskConfig(
    max_gross_exposure=0.5,             # 50% exposure
    max_net_exposure=0.40,              # 40% net
    max_daily_loss_pct=0.03,            # 3% daily stop
    max_drawdown_pct=0.07,              # 7% max DD
)
```

### Moderate (Proven Strategy)
```python
PositionRiskConfig(
    max_position_size_usd=25000.0,      # Moderate positions
    max_position_size_pct_account=0.05,  # 5% max
    stop_loss_atr_multiple=2.0,         # Standard stops
)

PortfolioRiskConfig(
    max_gross_exposure=1.0,             # 100% exposure
    max_net_exposure=0.75,              # 75% net
    max_daily_loss_pct=0.05,            # 5% daily stop
    max_drawdown_pct=0.10,              # 10% max DD
)
```

### Aggressive (High Confidence)
```python
PositionRiskConfig(
    max_position_size_usd=50000.0,      # Large positions
    max_position_size_pct_account=0.10,  # 10% max
    stop_loss_atr_multiple=1.5,         # Tighter stops
)

PortfolioRiskConfig(
    max_gross_exposure=1.5,             # 150% exposure
    max_net_exposure=1.0,               # 100% net
    max_daily_loss_pct=0.07,            # 7% daily stop
    max_drawdown_pct=0.15,              # 15% max DD
)
```

---

## 10. TROUBLESHOOTING

### Q: How do I know if my strategy has edge?
A: Calculate expectancy after minimum 20-30 trades:
   - Positive expectancy > 0 = Edge exists
   - Expectancy > 0.05R (5%) = Healthy edge
   - Profit factor > 1.5 = Excellent

### Q: Stop losses keep hitting (whipsawed)
A: Increase ATR multiple from 2.0 to 2.5 or 3.0

### Q: Need higher win rate
A: Improve entry timing, add filters (trend confirmation, momentum, etc.)

### Q: Trying to size up but hitting limits
A: Ensure min 0.35 win rate before increasing position size

### Q: Options position too risky
A: Monitor delta/gamma/vega limits, reduce position or add hedges

### Q: Margin getting too high
A: Reduce options positions or close some trades

---

## 11. FILES PROVIDED

1. **risk_management_framework.py** (800+ lines)
   - Core risk calculation engines
   - Position and portfolio metrics
   - R-multiple measurement
   - Position sizing calculators
   - Risk monitoring engine
   - Stop/profit calculators
   - Risk reporter
   - Monte Carlo simulator

2. **risk_management_actor.py** (450+ lines)
   - NautilusTrader Actor integration
   - Real-time monitoring
   - Alert publishing
   - Report generation
   - Event handlers

3. **RISK_MANAGEMENT_GUIDE.md** (this file)
   - Comprehensive documentation
   - Configuration examples
   - Best practices
   - Usage examples

---

## 12. NEXT STEPS

1. Customize `PositionRiskConfig` for your strategy
2. Customize `PortfolioRiskConfig` based on your account size
3. Integrate `RiskManagementActor` into your NautilusTrader application
4. Implement position entry signals with automated stop/profit calculation
5. Track all trades in R-multiples via `RMeasurement`
6. Monitor alerts and reports in real-time
7. Measure expectancy after 20+ trades
8. Adjust position sizing based on actual win rate
9. Run Monte Carlo simulations before increasing size
10. Review framework monthly and adjust limits as needed
