# Trading Strategy Recommendations for Moomoo Paper Trading
**NautilusTrader Implementation Guide**

## Executive Summary

This document outlines three systematic trading strategies designed for paper trading US equities and options through Moomoo's OpenD API. Each strategy is designed for NautilusTrader's event-driven framework with realistic transaction costs and risk management.

---

## Strategy 1: Mean Reversion - Statistical Arbitrage on Sector ETF Pairs

### Concept
Trade mean reversion in correlated sector ETF pairs when their spread deviates beyond statistical thresholds. This exploits temporary dislocations in related sectors while maintaining market neutrality.

### Entry/Exit Logic

**Entry Signals:**
- Calculate rolling z-score of price spread: `z = (spread - spread_mean) / spread_std`
- **Long Signal**: Enter when z < -2.0 (spread compressed)
  - Buy underperformer, short outperformer
- **Short Signal**: Enter when z > 2.0 (spread extended)
  - Short underperformer, buy outperformer
- Require cointegration test (ADF p-value < 0.05) over 60-day lookback

**Exit Signals:**
- **Profit Target**: z-score reverts to mean (|z| < 0.5)
- **Stop Loss**: z-score extends further (|z| > 3.0) or 2% loss on position
- **Time Stop**: Close position after 5 trading days if not triggered

### Key Parameters

```python
PARAMETERS = {
    'lookback_period': 60,        # days for spread statistics
    'zscore_entry': 2.0,          # standard deviations
    'zscore_exit': 0.5,           # mean reversion threshold
    'zscore_stop': 3.0,           # stop loss threshold
    'position_size': 0.10,        # 10% portfolio per leg
    'max_holding_days': 5,        # time-based exit
    'min_correlation': 0.85,      # pair selection filter
    'cointegration_pvalue': 0.05  # statistical requirement
}
```

**Parameter Ranges for Optimization:**
- `lookback_period`: [40, 60, 90, 120] days
- `zscore_entry`: [1.5, 2.0, 2.5] std
- `position_size`: [0.05, 0.10, 0.15] fraction

### Recommended Instruments

**High-Liquidity Sector ETF Pairs:**
1. **XLE/XOP** - Energy sector (large cap vs small cap)
2. **XLF/KRE** - Financials (diversified vs regional banks)
3. **XLK/SMH** - Technology (broad tech vs semiconductors)
4. **XLI/IYT** - Industrials (broad vs transportation)
5. **XRT/XLY** - Retail (equal-weight vs cap-weight consumer discretionary)

**Selection Criteria:**
- Average daily volume > 5M shares
- Tight bid-ask spreads (< 0.05%)
- Market cap > $1B
- Historical correlation > 0.85

### Risk Metrics

**Position-Level:**
- Max position size: 10% per leg (20% total per pair)
- Stop loss: 2% per trade
- Max concurrent pairs: 3

**Portfolio-Level:**
- Max drawdown limit: 15%
- Daily VaR (95% confidence): 3% of portfolio
- Gross exposure limit: 60% (market neutral strategy)
- Beta target: -0.1 to +0.1 (market neutral)

**Performance Targets:**
- Sharpe ratio: > 1.5
- Win rate: > 55%
- Profit factor: > 1.3
- Max drawdown: < 12%

### Transaction Cost Assumptions

```python
COSTS = {
    'commission': 0.0,            # Moomoo zero commission
    'slippage_bps': 5.0,          # 0.05% per trade (ETFs are liquid)
    'spread_bps': 2.0,            # 0.02% bid-ask (half-spread cost)
    'total_cost_per_trade': 7.0   # 0.07% total = 0.14% round trip
}
```

### NautilusTrader Implementation Notes

**Strategy Class Structure:**
```python
class PairsTradingStrategy(Strategy):
    """
    Mean reversion pairs trading strategy.

    Data Requirements:
    - Subscribe to QUOTE and TRADE ticks for both ETFs
    - Request 1-minute bars for spread calculation
    - Maintain rolling window for statistics

    State Management:
    - Track spread z-score
    - Monitor cointegration relationship
    - Manage entry/exit timing
    """

    def on_start(self):
        # Subscribe to data feeds
        # Initialize spread calculation
        # Load historical data for statistics
        pass

    def on_quote_tick(self, tick):
        # Update spread calculation
        # Check entry/exit conditions
        # Generate signals
        pass

    def on_bar(self, bar):
        # Update rolling statistics
        # Recalculate z-score
        # Risk checks
        pass
```

**Risk Manager Integration:**
- Pre-trade checks: exposure limits, correlation breakdown
- Position sizing: Kelly criterion with 0.25 fractional Kelly
- Dynamic stops: trailing stop if z-score momentum reverses

---

## Strategy 2: Momentum - Breakout Trading on High Beta Tech Stocks

### Concept
Capitalize on continuation patterns in high-momentum tech stocks using multi-timeframe confirmation. Combines price action breakouts with volume and relative strength filters.

### Entry/Exit Logic

**Entry Signals:**
- **Price Breakout**: Close above 20-day high with volume > 1.5x average
- **RSI Confirmation**: RSI(14) between 55-75 (not overbought)
- **Relative Strength**: Stock outperforming SPY over 20 days (> 2%)
- **ATR Filter**: ATR percentile > 50th (sufficient volatility)
- Enter on market order at next bar open after signal

**Exit Signals:**
- **Profit Target**: 2x ATR from entry or 5% gain (whichever first)
- **Trailing Stop**: 1.5x ATR from highest high since entry
- **Time Stop**: Close after 10 days if no exit triggered
- **Breakdown**: Close below 10-period EMA with volume spike

### Key Parameters

```python
PARAMETERS = {
    'breakout_lookback': 20,      # days for high/low
    'volume_multiplier': 1.5,     # vs 20-day average
    'rsi_period': 14,             # momentum indicator
    'rsi_min': 55,                # avoid weak momentum
    'rsi_max': 75,                # avoid overbought
    'relative_strength_min': 0.02,# 2% outperformance vs SPY
    'atr_period': 14,             # volatility measure
    'profit_target_atr': 2.0,     # ATR multiplier
    'trailing_stop_atr': 1.5,     # ATR multiplier
    'position_size': 0.08,        # 8% portfolio per position
    'max_holding_days': 10,       # time-based exit
    'max_concurrent': 5           # position limit
}
```

**Parameter Ranges for Optimization:**
- `breakout_lookback`: [15, 20, 30] days
- `profit_target_atr`: [1.5, 2.0, 2.5]
- `trailing_stop_atr`: [1.0, 1.5, 2.0]
- `position_size`: [0.05, 0.08, 0.12]

### Recommended Instruments

**High Beta Tech Stocks (Beta > 1.3):**
1. **NVDA** - NVIDIA (semiconductors)
2. **AMD** - Advanced Micro Devices (semiconductors)
3. **TSLA** - Tesla (EV/tech)
4. **PLTR** - Palantir (AI/software)
5. **SNOW** - Snowflake (cloud)
6. **CRWD** - CrowdStrike (cybersecurity)
7. **NET** - Cloudflare (cloud infrastructure)
8. **DDOG** - Datadog (monitoring)

**Fallback Universe (Mega-Cap Liquid):**
- **AAPL**, **MSFT**, **GOOGL**, **META**, **AMZN**

**Selection Criteria:**
- Beta > 1.3 vs SPY
- Market cap > $50B (or $10B for mid-caps)
- Average daily volume > 10M shares
- IV Rank > 30 (sufficient volatility)

### Risk Metrics

**Position-Level:**
- Max position size: 8% per stock
- Initial stop: 1.5x ATR (typically 2-3%)
- Max loss per trade: 2%

**Portfolio-Level:**
- Max concurrent positions: 5
- Total equity exposure: 40% max
- Sector concentration: < 25% in single sector
- Daily VaR (95%): 4% of portfolio
- Max drawdown limit: 20%

**Performance Targets:**
- Sharpe ratio: > 1.2
- Win rate: > 45%
- Profit factor: > 1.5
- Average win/loss ratio: > 2.0
- Max drawdown: < 18%

### Transaction Cost Assumptions

```python
COSTS = {
    'commission': 0.0,            # Moomoo zero commission
    'slippage_bps': 10.0,         # 0.10% per trade (market orders)
    'spread_bps': 5.0,            # 0.05% bid-ask (liquid stocks)
    'market_impact_bps': 5.0,     # 0.05% for larger orders
    'total_cost_per_trade': 20.0  # 0.20% total = 0.40% round trip
}
```

### NautilusTrader Implementation Notes

**Strategy Class Structure:**
```python
class MomentumBreakoutStrategy(Strategy):
    """
    Multi-timeframe momentum breakout strategy.

    Data Requirements:
    - Subscribe to 1-minute bars for execution
    - Request daily bars for breakout detection
    - Track SPY for relative strength
    - Real-time volume tracking

    Indicators:
    - 20-day high/low
    - RSI(14)
    - ATR(14)
    - Volume MA(20)
    - 10-period EMA
    """

    def on_start(self):
        # Initialize indicators
        # Subscribe to multi-timeframe data
        # Load historical bars
        pass

    def on_bar(self, bar):
        # Update indicators
        # Check breakout conditions
        # Manage trailing stops
        # Generate signals
        pass

    def on_order_filled(self, event):
        # Set initial stops
        # Calculate profit targets
        pass
```

**Position Sizing:**
- Base position: 8% portfolio
- Kelly adjustment: `size = kelly_fraction * (win_rate * avg_win - loss_rate * avg_loss) / avg_win`
- Use 0.5 fractional Kelly for safety
- Reduce size if portfolio heat > 15% (sum of open risk)

**Risk Manager Integration:**
- Volatility scaling: reduce size when VIX > 30
- Correlation check: limit correlated positions (tech concentration)
- Dynamic stops: tighten if adverse momentum shift

---

## Strategy 3: Options Income - Covered Calls on High Dividend Stocks

### Concept
Generate income by selling out-of-the-money covered calls on stable, dividend-paying stocks. Focuses on capital preservation with incremental returns from option premium.

### Entry/Exit Logic

**Stock Selection:**
- Hold 100 shares of qualifying dividend stock
- Minimum yield: 2.5%
- Beta < 1.0 (lower volatility)
- IV Rank > 40 (elevated premium environment)

**Call Option Entry:**
- Sell 30-45 DTE calls at 0.30 delta (70% OTM probability)
- Target premium: > 1% of stock price
- Only sell when stock not near ex-dividend date (avoid assignment)
- Enter on limit order at mid-price or better

**Exit/Roll Logic:**
- **Profit Taking**: Buy back at 50% profit (or 0.05 per contract)
- **Expiration**: Let expire worthless if OTM
- **Roll Out**: If ITM at 7 DTE, roll to next month same strike (credit)
- **Assignment Risk**: Buy back if stock surges to 0.95 delta (95% ITM)

### Key Parameters

```python
PARAMETERS = {
    'dte_min': 30,                # minimum days to expiration
    'dte_max': 45,                # maximum days to expiration
    'delta_target': 0.30,         # target delta for sold calls
    'delta_max': 0.35,            # max delta (closer to ATM)
    'min_premium_pct': 0.01,      # 1% of stock price
    'profit_target_pct': 0.50,    # 50% of max profit
    'roll_threshold_dte': 7,      # days before expiration to consider roll
    'roll_delta_threshold': 0.95, # deep ITM threshold for defensive action
    'min_iv_rank': 40,            # minimum IV environment
    'position_size': 100,         # shares (1 contract)
    'max_positions': 5            # max concurrent covered calls
}
```

**Parameter Ranges for Optimization:**
- `delta_target`: [0.25, 0.30, 0.35] (strike selection)
- `dte_min/max`: [21-35, 30-45, 35-50] (term structure)
- `profit_target_pct`: [0.40, 0.50, 0.60]

### Recommended Instruments

**High-Dividend, Low-Beta Stocks:**
1. **JNJ** - Johnson & Johnson (healthcare, ~3% yield)
2. **PG** - Procter & Gamble (consumer staples, ~2.5% yield)
3. **KO** - Coca-Cola (beverages, ~3% yield)
4. **VZ** - Verizon (telecom, ~6% yield)
5. **T** - AT&T (telecom, ~5% yield)
6. **PFE** - Pfizer (pharma, ~4% yield)
7. **ABBV** - AbbVie (biotech, ~3.5% yield)

**Alternative: Dividend ETFs:**
- **SCHD** - Schwab US Dividend Equity ETF
- **VYM** - Vanguard High Dividend Yield ETF
- **DVY** - iShares Select Dividend ETF

**Selection Criteria:**
- Dividend yield > 2.5%
- Beta < 1.0
- Option volume > 1,000 contracts/day
- Tight bid-ask spreads (< $0.10 for options)
- Stable earnings (low bankruptcy risk)

### Risk Metrics

**Position-Level:**
- Max position: 100 shares per stock (1 covered call)
- Stock stop loss: 10% from purchase price
- Option management: close at 200% loss (option doubled)

**Portfolio-Level:**
- Max concurrent positions: 5 stocks
- Total equity exposure: 50% max (5 x 100 shares)
- Sector concentration: < 30% in single sector
- Portfolio beta: < 0.8 (defensive)
- Max drawdown limit: 12%

**Performance Targets:**
- Sharpe ratio: > 1.0
- Annualized return: 8-12% (dividends + premium)
- Win rate: > 70% (options expire worthless)
- Max drawdown: < 10%
- Volatility: < 12% annualized

### Transaction Cost Assumptions

```python
COSTS = {
    'stock_commission': 0.0,      # Moomoo zero commission
    'option_commission': 0.0,     # Moomoo zero option commission
    'stock_slippage_bps': 5.0,    # 0.05% for stock entry
    'option_slippage': 0.02,      # $0.02 per contract
    'option_spread': 0.05,        # $0.05 bid-ask (half spread)
    'total_cost_per_setup': 0.07  # $0.07 per option round trip
}
```

**Example Trade Economics:**
- Stock: 100 shares at $50 = $5,000
- Sell 1 call at $0.60 = $60 premium
- Cost: $0.07 per contract = $7 total
- Net premium: $53
- Return: 1.06% over 30-45 days (~9-14% annualized)

### NautilusTrader Implementation Notes

**Strategy Class Structure:**
```python
class CoveredCallStrategy(Strategy):
    """
    Covered call income strategy on dividend stocks.

    Data Requirements:
    - Stock quotes and bars
    - Option chain data (greeks, IV)
    - Dividend calendar
    - IV Rank calculation

    State Management:
    - Track stock positions
    - Monitor option positions
    - Handle assignment risk
    - Calculate rolling returns
    """

    def on_start(self):
        # Initialize stock positions
        # Subscribe to option chains
        # Load dividend schedule
        pass

    def on_option_chain(self, chain):
        # Filter by DTE and delta
        # Select optimal strike
        # Check premium threshold
        # Generate sell order
        pass

    def on_quote_tick(self, tick):
        # Monitor option P&L
        # Check profit target
        # Manage assignment risk
        pass

    def on_dividend_announcement(self, event):
        # Avoid selling calls before ex-date
        # Adjust position if necessary
        pass
```

**Position Sizing:**
- Fixed: 100 shares per position (1 standard contract)
- Scale based on portfolio size: `max_positions = portfolio_value / 5000`
- Target allocation: 50% of portfolio in covered call positions

**Risk Manager Integration:**
- Ex-dividend tracking: close options 5 days before ex-date if ITM
- Earnings calendar: avoid selling calls over earnings (or buy back)
- Volatility spike management: close options if IV expands 50%+

---

## Cross-Strategy Portfolio Allocation

### Recommended Capital Allocation
```python
PORTFOLIO_ALLOCATION = {
    'pairs_trading': 0.30,        # 30% - mean reversion
    'momentum_breakout': 0.40,    # 40% - momentum
    'covered_calls': 0.30         # 30% - income
}
```

**Rationale:**
- **Diversification**: Low correlation between strategies
  - Mean reversion (negative correlation to trends)
  - Momentum (directional exposure)
  - Income (volatility harvesting)
- **Risk Balance**: Momentum has highest volatility, pairs is market neutral, income is defensive
- **Return Enhancement**: Target portfolio Sharpe > 1.5

### Portfolio-Level Risk Metrics

**Risk Limits:**
```python
PORTFOLIO_RISK = {
    'max_gross_exposure': 1.30,   # 130% including shorts
    'max_net_exposure': 0.60,     # 60% net long
    'max_sector_exposure': 0.35,  # 35% in any sector
    'max_single_position': 0.10,  # 10% per position
    'daily_var_95': 0.05,         # 5% daily VaR
    'max_drawdown': 0.20,         # 20% max drawdown limit
    'min_sharpe': 1.0,            # minimum acceptable Sharpe
    'target_sharpe': 1.5          # target Sharpe ratio
}
```

**Correlation Management:**
- Monitor inter-strategy correlation (rebalance if > 0.7)
- Reduce momentum allocation if market regime shifts (VIX > 30)
- Increase pairs allocation in high volatility environments

**Rebalancing Rules:**
- Monthly review of strategy allocations
- Reallocate based on rolling 60-day Sharpe ratios
- Increase allocation to best performer by max 10%
- Decrease allocation to worst performer by max 10%

---

## Implementation Roadmap

### Phase 1: Infrastructure (Week 1-2)
1. **Data Pipeline Setup**
   - Configure Moomoo OpenD API connections
   - Subscribe to quote/trade/bar feeds
   - Test data quality and latency
   - Implement data validation

2. **NautilusTrader Configuration**
   - Set up backtest engine
   - Configure paper trading account
   - Implement custom indicators (z-score, RSI, ATR)
   - Build option chain handling (for Strategy 3)

3. **Risk Management Framework**
   - Implement pre-trade risk checks
   - Build position sizing logic (Kelly criterion)
   - Create exposure tracking dashboard
   - Set up alert system

### Phase 2: Strategy Development (Week 3-4)
1. **Pairs Trading Implementation**
   - Code pair selection logic
   - Implement cointegration tests
   - Build spread calculation
   - Add z-score signals

2. **Momentum Breakout Implementation**
   - Code breakout detection
   - Implement multi-indicator filters
   - Build trailing stop logic
   - Add relative strength calculations

3. **Covered Call Implementation**
   - Code option chain filtering
   - Implement delta-based strike selection
   - Build roll/early close logic
   - Add dividend calendar integration

### Phase 3: Backtesting (Week 5-6)
1. **Historical Testing**
   - Run backtests on 2-3 years of data
   - Perform walk-forward analysis
   - Test parameter sensitivity
   - Validate transaction cost assumptions

2. **Performance Analysis**
   - Calculate risk-adjusted metrics
   - Analyze drawdown periods
   - Review trade-by-trade results
   - Identify failure modes

3. **Optimization**
   - Grid search on key parameters
   - Cross-validation on out-of-sample data
   - Test regime changes (bull/bear/sideways)
   - Refine entry/exit rules

### Phase 4: Paper Trading (Week 7+)
1. **Launch Preparation**
   - Final code review
   - Test order execution on paper account
   - Verify risk controls
   - Set up monitoring dashboard

2. **Live Paper Trading**
   - Start with reduced position sizes (50% of target)
   - Monitor execution quality (slippage, fills)
   - Track real-time performance
   - Refine based on live data

3. **Ongoing Monitoring**
   - Daily P&L reviews
   - Weekly risk metric analysis
   - Monthly strategy performance review
   - Quarterly reoptimization

---

## Key Success Factors

### Data Quality
- **Validation**: Check for missing bars, stale quotes, outliers
- **Latency**: Monitor API response times (target < 100ms)
- **Accuracy**: Verify prices against alternative sources
- **Completeness**: Ensure option chain data includes all strikes

### Execution Quality
- **Slippage**: Track actual vs expected slippage
- **Fill Rate**: Monitor order fill percentage
- **Timing**: Minimize signal-to-order latency
- **Costs**: Validate total transaction costs match assumptions

### Risk Management
- **Pre-Trade Checks**: Validate all risk limits before orders
- **Position Monitoring**: Real-time exposure tracking
- **Stop Discipline**: Automated stop execution (no discretion)
- **Circuit Breakers**: Halt trading if drawdown exceeds limits

### Performance Tracking
- **Metrics to Monitor**:
  - Sharpe ratio (rolling 30/60/90 day)
  - Win rate and profit factor
  - Maximum drawdown (current and historical)
  - Average win/loss ratio
  - Exposure utilization
  - Strategy correlation

- **Red Flags**:
  - Sharpe ratio < 0.5 for 30+ days
  - Drawdown > 15% (pause trading)
  - Win rate < 40% for momentum, < 50% for pairs
  - Correlation breakdown in pairs (cointegration failure)

---

## Technology Stack

### Core Components
```python
# NautilusTrader stack
STACK = {
    'execution': 'NautilusTrader Strategy/Actor framework',
    'data': 'Moomoo OpenD API (quotes, bars, options)',
    'backtest': 'NautilusTrader BacktestEngine',
    'risk': 'Custom RiskEngine integration',
    'analytics': 'pandas, numpy, scipy, statsmodels',
    'visualization': 'matplotlib, seaborn, plotly',
    'database': 'PostgreSQL (trade/position history)',
    'monitoring': 'Custom dashboard (Streamlit/Dash)'
}
```

### Key Libraries
```python
# requirements.txt
"""
nautilus_trader>=1.190.0
pandas>=2.0.0
numpy>=1.24.0
scipy>=1.10.0
statsmodels>=0.14.0
matplotlib>=3.7.0
seaborn>=0.12.0
ta-lib>=0.4.0  # Technical indicators
arch>=6.0.0     # GARCH modeling
scikit-learn>=1.3.0  # ML tools
"""
```

---

## Appendix: Risk Formulas

### Position Sizing (Kelly Criterion)
```python
def kelly_position_size(win_rate, avg_win, avg_loss, fractional=0.5):
    """
    Calculate position size using Kelly criterion.

    Parameters:
    - win_rate: probability of winning trade
    - avg_win: average win amount (as ratio)
    - avg_loss: average loss amount (as ratio, positive)
    - fractional: fraction of Kelly to use (0.25-0.5 for safety)

    Returns:
    - Position size as fraction of capital
    """
    kelly_fraction = (win_rate * avg_win - (1 - win_rate) * avg_loss) / avg_win
    return max(0, kelly_fraction * fractional)

# Example for momentum strategy:
# win_rate = 0.45, avg_win = 0.04, avg_loss = 0.02
# kelly = (0.45 * 0.04 - 0.55 * 0.02) / 0.04 = 0.175
# fractional_kelly = 0.175 * 0.5 = 0.0875 (~8.8% position)
```

### Value at Risk (VaR)
```python
def calculate_var(returns, confidence=0.95):
    """
    Calculate Value at Risk using historical simulation.

    Parameters:
    - returns: array of historical returns
    - confidence: confidence level (0.95 = 95%)

    Returns:
    - VaR as percentage (e.g., 0.03 = 3% potential loss)
    """
    return np.percentile(returns, (1 - confidence) * 100)

# Example: 95% VaR = 3% means 95% of days have loss < 3%
```

### Maximum Drawdown
```python
def calculate_max_drawdown(equity_curve):
    """
    Calculate maximum drawdown from equity curve.

    Parameters:
    - equity_curve: array of portfolio values over time

    Returns:
    - max_drawdown: largest peak-to-trough decline (as ratio)
    - max_dd_duration: days from peak to recovery
    """
    cummax = np.maximum.accumulate(equity_curve)
    drawdown = (equity_curve - cummax) / cummax
    max_drawdown = np.min(drawdown)

    # Duration calculation
    dd_start = np.argmax(cummax[:np.argmin(drawdown)])
    dd_end = np.argmin(drawdown)
    max_dd_duration = dd_end - dd_start

    return abs(max_drawdown), max_dd_duration
```

### Sharpe Ratio
```python
def calculate_sharpe(returns, risk_free_rate=0.04, periods=252):
    """
    Calculate annualized Sharpe ratio.

    Parameters:
    - returns: array of returns (daily)
    - risk_free_rate: annual risk-free rate (default 4%)
    - periods: trading periods per year (252 for daily)

    Returns:
    - Sharpe ratio (annualized)
    """
    excess_returns = returns - (risk_free_rate / periods)
    sharpe = np.mean(excess_returns) / np.std(returns) * np.sqrt(periods)
    return sharpe
```

---

## Conclusion

These three strategies provide a diversified approach to systematic trading on Moomoo:

1. **Pairs Trading**: Market-neutral, low correlation to equity markets, steady returns
2. **Momentum Breakout**: Directional exposure, higher returns with higher volatility
3. **Covered Calls**: Income generation, capital preservation, volatility harvesting

**Expected Portfolio Performance:**
- **Sharpe Ratio**: 1.3 - 1.7
- **Annualized Return**: 12% - 18%
- **Max Drawdown**: 15% - 20%
- **Win Rate**: 55% - 60%
- **Volatility**: 12% - 15% annualized

**Next Steps:**
1. Review and approve strategy concepts
2. Set up development environment
3. Begin Phase 1 implementation (data pipeline)
4. Start with Strategy 1 (pairs) as pilot
5. Iterate based on paper trading results

All strategies are designed to work within NautilusTrader's event-driven framework and can be implemented using the provided parameter specifications and risk metrics.
