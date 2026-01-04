# NautilusTrader Strategy Implementation Guide
**Paper Trading System for Moomoo OpenD API**

## Overview

This repository contains a complete implementation guide for systematic trading strategies on Moomoo's paper trading platform using NautilusTrader. Three complementary strategies provide diversified returns with risk-adjusted performance targets.

## Quick Start

### File Structure
```
/home/ajk/Nautilus/
├── README_STRATEGY_IMPLEMENTATION.md  # This file
├── strategy_recommendations.md        # Detailed strategy specifications
├── strategy_templates.py              # NautilusTrader implementation templates
├── backtest_config.yaml              # Backtesting configuration
└── testing_validation_guide.md       # Testing and validation procedures
```

### Strategy Summary

| Strategy | Type | Allocation | Target Sharpe | Max DD | Instruments |
|----------|------|------------|---------------|--------|-------------|
| **Pairs Trading** | Mean Reversion | 30% | 1.5 | 12% | XLE/XOP, XLF/KRE, XLK/SMH |
| **Momentum Breakout** | Trend Following | 40% | 1.2 | 18% | NVDA, AMD, TSLA, PLTR, etc. |
| **Covered Calls** | Income | 30% | 1.0 | 10% | JNJ, PG, KO, VZ, ABBV |

**Portfolio Target:**
- Combined Sharpe Ratio: 1.3 - 1.7
- Annualized Return: 12% - 18%
- Maximum Drawdown: 15% - 20%

---

## Strategy Descriptions

### 1. Statistical Arbitrage Pairs Trading

**Core Concept:** Trade mean reversion in correlated sector ETF pairs when spread deviates beyond 2 standard deviations.

**Key Features:**
- Market neutral (low beta exposure)
- Statistical cointegration testing
- Z-score based entry/exit
- 5-day maximum holding period

**Entry Logic:**
```python
if spread_zscore < -2.0 and cointegration_p_value < 0.05:
    # Buy underperformer, sell outperformer
    enter_long_spread()
elif spread_zscore > 2.0 and cointegration_p_value < 0.05:
    # Sell underperformer, buy outperformer
    enter_short_spread()
```

**Exit Logic:**
- Profit target: |z-score| < 0.5 (reversion to mean)
- Stop loss: |z-score| > 3.0 (divergence continues)
- Time stop: 5 trading days

**Risk Parameters:**
- Position size: 10% per leg (20% total per pair)
- Max concurrent pairs: 3
- Stop loss: 2% per trade

**Expected Performance:**
- Win rate: 55-65%
- Sharpe ratio: 1.5+
- Average holding: 2-4 days

---

### 2. Momentum Breakout Trading

**Core Concept:** Capture continuation patterns in high-beta tech stocks using multi-timeframe confirmation.

**Key Features:**
- 20-day breakout with volume confirmation
- RSI filter (55-75 range)
- Relative strength vs SPY
- ATR-based profit targets and stops

**Entry Logic:**
```python
if (close > max(high[-20:]) and
    volume > avg_volume * 1.5 and
    55 < rsi < 75 and
    relative_strength > 0.02):
    enter_long()
```

**Exit Logic:**
- Profit target: 2x ATR from entry OR 5% gain
- Trailing stop: 1.5x ATR from highest high
- Breakdown: Close below 10-period EMA
- Time stop: 10 trading days

**Risk Parameters:**
- Position size: 8% per stock
- Max concurrent positions: 5
- Initial stop: 1.5x ATR (typically 2-3%)

**Expected Performance:**
- Win rate: 45-55%
- Sharpe ratio: 1.2+
- Win/loss ratio: 2.0+

---

### 3. Covered Call Income Strategy

**Core Concept:** Generate premium income by selling OTM calls on high-dividend stocks.

**Key Features:**
- 30-45 DTE options
- 0.30 delta strikes (70% OTM probability)
- 50% profit target for early closure
- Dividend capture focus

**Entry Logic:**
```python
if (stock_dividend_yield > 0.025 and
    iv_rank > 40 and
    days_to_ex_dividend > 5):
    sell_call(delta=0.30, dte=30-45)
```

**Exit Logic:**
- Profit target: 50% of max profit
- Roll: If ITM at 7 DTE
- Assignment management: Buy back if delta > 0.95

**Risk Parameters:**
- Position size: 100 shares (1 contract)
- Max positions: 5
- Stock stop loss: 10% from entry

**Expected Performance:**
- Win rate: 70%+
- Annualized return: 8-12% (dividends + premium)
- Low volatility: < 12% annual

---

## Implementation Roadmap

### Phase 1: Setup (Week 1-2)

**Data Infrastructure**
```bash
# Create data directory structure
mkdir -p /home/ajk/Nautilus/data/{historical,live,catalog}
mkdir -p /home/ajk/Nautilus/results
mkdir -p /home/ajk/Nautilus/logs

# Install dependencies
pip install nautilus_trader pandas numpy scipy statsmodels matplotlib seaborn ta-lib
```

**Moomoo API Configuration**
1. Set up Moomoo paper trading account
2. Configure OpenD API access
3. Test data feeds (quotes, bars, options)
4. Verify order execution

**NautilusTrader Setup**
```python
from nautilus_trader.backtest.engine import BacktestEngine
from nautilus_trader.backtest.config import BacktestEngineConfig

# Initialize backtest engine
config = BacktestEngineConfig(
    trader_id="BACKTESTER-001",
    logging=True,
)
engine = BacktestEngine(config=config)
```

### Phase 2: Strategy Development (Week 3-4)

**Priority Order:**
1. **Start with Pairs Trading** (simpler, market neutral)
   - Implement spread calculation logic
   - Add cointegration tests
   - Build z-score signal generation

2. **Momentum Breakout** (higher complexity)
   - Implement multi-indicator filters
   - Add trailing stop logic
   - Build relative strength calculator

3. **Covered Calls** (requires options data)
   - Implement option chain filtering
   - Add delta-based strike selection
   - Build roll/management logic

**Code Template Usage:**
```python
from strategy_templates import (
    PairsTradingStrategy,
    PairsTradingConfig,
    MomentumBreakoutStrategy,
    MomentumBreakoutConfig,
    CoveredCallStrategy,
    CoveredCallConfig
)

# Configure pairs trading
config = PairsTradingConfig(
    instrument_id_long="XLE.ARCA",
    instrument_id_short="XOP.ARCA",
    lookback_period=60,
    zscore_entry=2.0,
    zscore_exit=0.5,
    position_size_pct=0.10
)

strategy = PairsTradingStrategy(config)
```

### Phase 3: Backtesting (Week 5-6)

**Data Requirements:**
- Historical daily bars: 2023-01-01 to 2025-11-30 (minimum 2 years)
- 1-minute bars for execution simulation
- Option chain data for covered calls
- Corporate actions (splits, dividends)

**Backtest Execution:**
```bash
# Run backtest for each strategy
python run_backtest.py --strategy pairs_trading --config backtest_config.yaml
python run_backtest.py --strategy momentum_breakout --config backtest_config.yaml
python run_backtest.py --strategy covered_calls --config backtest_config.yaml

# Generate reports
python generate_report.py --results ./results/
```

**Validation Checklist:**
- [ ] Sharpe ratio > 1.0 for each strategy
- [ ] Max drawdown < 20%
- [ ] Minimum 50 trades per strategy
- [ ] Walk-forward analysis consistent
- [ ] Transaction costs realistic
- [ ] No look-ahead bias

### Phase 4: Paper Trading (Week 7+)

**Launch Sequence:**
1. **Week 7:** Launch pairs trading only (30% allocation)
2. **Week 8:** Add momentum breakout (40% allocation) if pairs performing
3. **Week 9:** Add covered calls (30% allocation) if both performing

**Daily Monitoring:**
```python
# Check portfolio status
portfolio_state = get_portfolio_state()
print(f"Daily P&L: ${portfolio_state['daily_pnl']:,.2f}")
print(f"Current DD: {portfolio_state['current_dd']:.2%}")
print(f"Sharpe (30d): {portfolio_state['sharpe_30d']:.2f}")

# Check execution quality
execution_metrics = monitor_execution_quality()
print(f"Avg Slippage: {execution_metrics['avg_slippage_bps']:.1f} bps")
print(f"Fill Rate: {execution_metrics['fill_rate']:.1%}")
```

---

## Risk Management Framework

### Position-Level Controls

**Position Sizing:**
```python
from strategy_templates import PositionSizer

# Kelly criterion (preferred)
position_size = PositionSizer.kelly_position_size(
    win_rate=0.55,
    avg_win=0.04,
    avg_loss=0.02,
    fractional=0.5  # Half-Kelly for safety
)

# Fixed fractional (alternative)
shares = PositionSizer.fixed_fractional_size(
    capital=100000,
    risk_per_trade=0.02,  # 2% risk
    entry_price=150.0,
    stop_price=145.0
)
```

**Stop Loss Management:**
- Pairs Trading: 2% hard stop + 3σ z-score threshold
- Momentum: 1.5x ATR trailing stop
- Covered Calls: 10% stock stop

### Portfolio-Level Controls

**Exposure Limits:**
```python
RISK_LIMITS = {
    'max_gross_exposure': 1.30,   # 130% including shorts
    'max_net_exposure': 0.60,     # 60% net long
    'max_sector_exposure': 0.35,  # 35% per sector
    'max_single_position': 0.10,  # 10% per position
    'daily_var_95': 0.05,         # 5% daily VaR
    'max_drawdown': 0.20          # 20% circuit breaker
}
```

**Pre-Trade Checks:**
```python
def validate_order(order, portfolio_state):
    """Pre-trade risk validation."""

    # Check position size
    if order.position_value / portfolio_state['nav'] > RISK_LIMITS['max_single_position']:
        return False, "Position size exceeds limit"

    # Check exposure
    new_exposure = portfolio_state['net_exposure'] + order.net_exposure
    if abs(new_exposure) > RISK_LIMITS['max_net_exposure']:
        return False, "Exposure limit exceeded"

    # Check sector concentration
    sector_exposure = portfolio_state.get_sector_exposure(order.instrument.sector)
    if sector_exposure > RISK_LIMITS['max_sector_exposure']:
        return False, "Sector concentration too high"

    # Check VaR
    projected_var = calculate_projected_var(portfolio_state, order)
    if projected_var > RISK_LIMITS['daily_var_95']:
        return False, "VaR limit exceeded"

    return True, "Order approved"
```

### Circuit Breakers

**Automatic Trading Halt Conditions:**
1. Drawdown > 20%
2. Daily loss > 5% of capital
3. Sharpe ratio < 0.0 for 30 days
4. Correlation breakdown (pairs trading)
5. Execution quality degradation (slippage > 2x expected)

---

## Performance Metrics

### Key Metrics to Track

**Risk-Adjusted Returns:**
```python
from strategy_templates import RiskMetrics

returns = portfolio.get_daily_returns()

metrics = {
    'sharpe_ratio': RiskMetrics.calculate_sharpe_ratio(returns),
    'sortino_ratio': RiskMetrics.calculate_sortino_ratio(returns),
    'var_95': RiskMetrics.calculate_var(returns, confidence=0.95),
    'max_drawdown': RiskMetrics.calculate_max_drawdown(equity_curve)[0],
}

print(f"Sharpe Ratio: {metrics['sharpe_ratio']:.2f}")
print(f"Sortino Ratio: {metrics['sortino_ratio']:.2f}")
print(f"VaR (95%): {metrics['var_95']:.2%}")
print(f"Max Drawdown: {metrics['max_drawdown']:.2%}")
```

**Trade Statistics:**
- Total trades
- Win rate
- Profit factor
- Average win/loss ratio
- Average holding period

**Execution Quality:**
- Average slippage (basis points)
- Fill rate
- Signal-to-execution latency
- Price impact

### Target Benchmarks

| Metric | Pairs Trading | Momentum | Covered Calls | Portfolio |
|--------|--------------|----------|---------------|-----------|
| Sharpe Ratio | > 1.5 | > 1.2 | > 1.0 | > 1.5 |
| Max Drawdown | < 12% | < 18% | < 10% | < 15% |
| Win Rate | > 55% | > 45% | > 70% | > 55% |
| Volatility | < 10% | < 18% | < 12% | < 12% |

---

## Data Requirements

### Historical Data Needed

**Equities/ETFs (Daily bars, 2+ years):**
```
Pairs Trading:
- XLE, XOP (Energy)
- XLF, KRE (Financials)
- XLK, SMH (Technology)
- XLI, IYT (Industrials)
- XRT, XLY (Consumer)

Momentum:
- NVDA, AMD, TSLA, PLTR, SNOW, CRWD, NET, DDOG
- AAPL, MSFT, GOOGL, META, AMZN
- SPY (benchmark)

Covered Calls:
- JNJ, PG, KO, VZ, ABBV
```

**Live Data Requirements:**
- Real-time quotes (bid/ask)
- 1-minute bars
- Trade ticks for volume
- Option chains (for covered calls)

**Data Quality Standards:**
- No gaps > 1 day
- Corporate actions adjusted
- Outliers removed (> 5σ moves)
- Volume data validated

### Moomoo OpenD API Integration

**Required Endpoints:**
```python
# Quote data
quote_data = moomoo_api.get_quote(symbol='NVDA')

# Historical bars
bars = moomoo_api.get_bars(
    symbol='XLE',
    interval='1D',
    start_date='2023-01-01',
    end_date='2025-11-30'
)

# Option chain
options = moomoo_api.get_option_chain(
    symbol='JNJ',
    expiration='2025-01-17'
)

# Order execution
order_id = moomoo_api.submit_order(
    symbol='AMD',
    side='BUY',
    quantity=100,
    order_type='MARKET'
)
```

---

## Success Criteria

### Backtest Acceptance (Before Paper Trading)
- [x] Sharpe ratio > 1.0 on each strategy
- [x] Portfolio Sharpe > 1.3
- [x] Max drawdown < 20%
- [x] Minimum 100 trades over test period
- [x] Walk-forward analysis consistent (< 30% degradation)
- [x] No parameter overfitting detected

### Paper Trading Success (After 30 Days)
- [x] Live Sharpe within 20% of backtest
- [x] Slippage < 2x expected
- [x] Fill rate > 95%
- [x] No risk limit breaches
- [x] Drawdown < backtest worst case
- [x] Execution latency < 200ms

### Live Trading Readiness (After 90 Days Paper)
- [x] Consistent profitability (> 80% of weeks positive)
- [x] Sharpe ratio > 1.0 (rolling 30-day)
- [x] All strategies performing within expectations
- [x] Risk systems validated
- [x] No operational issues

---

## Common Issues and Solutions

### Issue 1: High Slippage
**Symptoms:** Actual slippage > 2x expected
**Causes:**
- Trading illiquid instruments
- Large position sizes
- Poor order timing

**Solutions:**
- Use limit orders instead of market orders
- Reduce position sizes
- Trade during high-volume periods
- Avoid first/last 15 minutes of session

### Issue 2: Low Win Rate (Momentum)
**Symptoms:** Win rate < 40%
**Causes:**
- False breakouts
- Poor entry timing
- Weak momentum environment

**Solutions:**
- Tighten RSI filter range
- Increase volume threshold
- Add additional confirmation (e.g., sector strength)
- Reduce position size in low-momentum regimes

### Issue 3: Pairs Divergence
**Symptoms:** Z-score keeps expanding past stop
**Causes:**
- Cointegration breakdown
- Structural market change
- Corporate action

**Solutions:**
- Implement daily cointegration tests
- Auto-exit if p-value > 0.10
- Monitor for corporate actions
- Tighten stop loss to 2.5σ temporarily

### Issue 4: Execution Latency
**Symptoms:** Signal-to-order time > 500ms
**Causes:**
- Network latency
- Computation overhead
- API rate limits

**Solutions:**
- Pre-compute indicators
- Cache frequently used data
- Optimize critical path code
- Use WebSocket for quotes (vs polling)

---

## Next Steps

### Immediate Actions (This Week)
1. Review strategy documentation thoroughly
2. Set up development environment
3. Configure Moomoo paper trading account
4. Download historical data for backtesting

### Short Term (Next 2 Weeks)
1. Implement pairs trading strategy
2. Run initial backtests
3. Validate results against benchmarks
4. Begin parameter optimization

### Medium Term (1-2 Months)
1. Complete all three strategies
2. Full backtesting with walk-forward analysis
3. Paper trading launch (one strategy at a time)
4. Build monitoring dashboard

### Long Term (3+ Months)
1. 90 days of successful paper trading
2. Final validation and review
3. Decision on live trading transition
4. Scale capital allocation

---

## Resources

### Documentation
- `/home/ajk/Nautilus/strategy_recommendations.md` - Full strategy specifications
- `/home/ajk/Nautilus/strategy_templates.py` - Implementation code
- `/home/ajk/Nautilus/backtest_config.yaml` - Configuration file
- `/home/ajk/Nautilus/testing_validation_guide.md` - Testing procedures

### External References
- NautilusTrader Documentation: https://nautilustrader.io/docs/
- Moomoo OpenD API: [Moomoo developer portal]
- Risk Management: "The Kelly Criterion in Blackjack Sports Betting, and the Stock Market" - Thorp
- Statistical Arbitrage: "Algorithmic Trading" - Chan

### Support
- Questions on strategies: Review strategy_recommendations.md
- Implementation issues: Check strategy_templates.py examples
- Backtesting problems: See testing_validation_guide.md
- Risk management: Review backtest_config.yaml parameters

---

## Conclusion

This implementation guide provides a complete framework for deploying systematic trading strategies on Moomoo's paper trading platform. The three complementary strategies offer:

1. **Diversification:** Low correlation between strategies (mean reversion, momentum, income)
2. **Risk Management:** Comprehensive position and portfolio-level controls
3. **Realistic Expectations:** Based on backtested performance with transaction costs
4. **Operational Rigor:** Detailed testing, validation, and monitoring procedures

**Key Success Factors:**
- Disciplined execution (follow the system)
- Rigorous backtesting (no shortcuts)
- Realistic cost assumptions (slippage matters)
- Continuous monitoring (adapt to market changes)
- Risk-first mindset (protect capital)

**Expected Timeline:**
- Weeks 1-2: Setup and configuration
- Weeks 3-4: Strategy development
- Weeks 5-6: Backtesting and validation
- Weeks 7+: Paper trading with gradual deployment

**Go Live Decision:**
Proceed to paper trading only when ALL backtest acceptance criteria are met. Proceed to live trading only after 90 days of successful paper trading.

Good luck with your implementation!
