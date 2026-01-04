# Testing and Validation Guide
**NautilusTrader Strategy Backtesting and Paper Trading**

## Table of Contents
1. [Pre-Backtest Checklist](#pre-backtest-checklist)
2. [Backtest Execution Steps](#backtest-execution-steps)
3. [Performance Validation](#performance-validation)
4. [Walk-Forward Analysis](#walk-forward-analysis)
5. [Paper Trading Transition](#paper-trading-transition)
6. [Monitoring and Alerting](#monitoring-and-alerting)

---

## Pre-Backtest Checklist

### Data Quality Validation

**Step 1: Data Completeness**
```python
import pandas as pd
import numpy as np

def validate_data_quality(df: pd.DataFrame, instrument: str) -> dict:
    """
    Validate data quality for backtesting.

    Returns dictionary with quality metrics.
    """
    results = {
        'instrument': instrument,
        'total_bars': len(df),
        'date_range': f"{df.index[0]} to {df.index[-1]}",
        'missing_bars': 0,
        'outliers': 0,
        'zero_volume_bars': 0,
        'quality_score': 0.0
    }

    # Check for missing data
    expected_bars = pd.date_range(
        start=df.index[0],
        end=df.index[-1],
        freq='1D'  # Daily bars
    )
    missing_dates = set(expected_bars) - set(df.index)
    results['missing_bars'] = len(missing_dates)

    # Check for outliers (>5 sigma moves)
    returns = df['close'].pct_change()
    mean_return = returns.mean()
    std_return = returns.std()
    outliers = returns[abs(returns - mean_return) > 5 * std_return]
    results['outliers'] = len(outliers)

    # Check for zero volume
    results['zero_volume_bars'] = len(df[df['volume'] == 0])

    # Calculate quality score (0-100)
    completeness = (1 - results['missing_bars'] / len(expected_bars)) * 100
    outlier_penalty = min(results['outliers'] * 2, 20)  # Max 20% penalty
    volume_penalty = min(results['zero_volume_bars'] * 0.1, 10)  # Max 10% penalty

    results['quality_score'] = max(0, completeness - outlier_penalty - volume_penalty)

    return results


# Example usage
# data_jnj = pd.read_csv('data/JNJ_daily.csv', index_col='date', parse_dates=True)
# quality = validate_data_quality(data_jnj, 'JNJ')
# print(f"Data Quality Score: {quality['quality_score']:.1f}/100")
```

**Step 2: Price Alignment**
```python
def check_price_alignment(df: pd.DataFrame) -> list:
    """
    Check for price alignment issues.

    Returns list of issues found.
    """
    issues = []

    # High < Low check
    invalid_bars = df[df['high'] < df['low']]
    if len(invalid_bars) > 0:
        issues.append(f"Found {len(invalid_bars)} bars where high < low")

    # Close outside high/low
    close_too_high = df[df['close'] > df['high'] * 1.001]  # 0.1% tolerance
    close_too_low = df[df['close'] < df['low'] * 0.999]
    if len(close_too_high) > 0:
        issues.append(f"Found {len(close_too_high)} bars where close > high")
    if len(close_too_low) > 0:
        issues.append(f"Found {len(close_too_low)} bars where close < low")

    # Open outside high/low
    open_too_high = df[df['open'] > df['high'] * 1.001]
    open_too_low = df[df['open'] < df['low'] * 0.999]
    if len(open_too_high) > 0:
        issues.append(f"Found {len(open_too_high)} bars where open > high")
    if len(open_too_low) > 0:
        issues.append(f"Found {len(open_too_low)} bars where open < low")

    return issues
```

**Step 3: Data Sources Checklist**
- [ ] Historical data downloaded for all instruments (2+ years)
- [ ] Dividend/split adjustments applied
- [ ] Data aligned to market hours (9:30 AM - 4:00 PM ET)
- [ ] Corporate actions database up to date
- [ ] Option chain data available (for covered calls)
- [ ] Benchmark data (SPY) available
- [ ] Volume data verified against exchange

---

## Backtest Execution Steps

### Phase 1: Single Strategy Testing

**Test Strategy 1: Pairs Trading**

```python
"""
Backtest execution script for pairs trading strategy.
"""

import pandas as pd
from nautilus_trader.backtest.engine import BacktestEngine
from nautilus_trader.backtest.config import BacktestDataConfig, BacktestEngineConfig
from nautilus_trader.model.currencies import USD
from nautilus_trader.model.enums import AccountType, OmsType
from nautilus_trader.model.identifiers import Venue

from strategy_templates import PairsTradingConfig, PairsTradingStrategy

# Configuration
VENUE = Venue("NASDAQ")
CURRENCY = USD

# Data configuration
data_config = BacktestDataConfig(
    catalog_path="./data/catalog",
    data_cls="BarData",  # or QuoteTick
    instrument_id="XLE.ARCA",
    bar_type="XLE.ARCA-1-DAY-LAST",
    start_time="2023-01-01",
    end_time="2025-11-30",
)

# Engine configuration
engine_config = BacktestEngineConfig(
    trader_id="BACKTESTER-001",
    logging=True,
)

# Create backtest engine
engine = BacktestEngine(config=engine_config)

# Add venue
engine.add_venue(
    venue=VENUE,
    oms_type=OmsType.NETTING,
    account_type=AccountType.MARGIN,
    base_currency=CURRENCY,
    starting_balances=[100_000 * USD],  # $100k starting capital
)

# Configure strategy
strategy_config = PairsTradingConfig(
    instrument_id_long="XLE.ARCA",
    instrument_id_short="XOP.ARCA",
    lookback_period=60,
    zscore_entry=2.0,
    zscore_exit=0.5,
    zscore_stop=3.0,
    position_size_pct=0.10,
)

# Add strategy
strategy = PairsTradingStrategy(config=strategy_config)
engine.add_strategy(strategy)

# Add data (both instruments)
engine.add_data(data_config)  # XLE
# Add XOP data similarly

# Run backtest
engine.run()

# Get results
result = engine.get_result()
print(result.summary())

# Generate report
result.save_report("./results/pairs_trading_backtest.html")
```

**Expected Outputs:**
- Total trades: 40-80 (depending on volatility regime)
- Win rate: 55-65%
- Sharpe ratio: 1.2-1.8
- Max drawdown: < 12%
- Average holding period: 2-4 days

**Red Flags:**
- Win rate < 50%
- Sharpe ratio < 0.8
- Max drawdown > 15%
- Average holding period > 7 days (signals not reverting)

---

### Phase 2: Parameter Optimization

**Grid Search Framework**

```python
from itertools import product
import numpy as np
import pandas as pd

def parameter_grid_search(
    strategy_class,
    base_config: dict,
    param_grid: dict,
    optimization_metric: str = "sharpe_ratio"
) -> pd.DataFrame:
    """
    Perform grid search over parameter space.

    Parameters:
    - strategy_class: Strategy class to test
    - base_config: Base configuration dictionary
    - param_grid: Dictionary of parameters to test
    - optimization_metric: Metric to optimize (sharpe_ratio, profit_factor, etc.)

    Returns:
    - DataFrame with results for each parameter combination
    """
    results = []

    # Generate all combinations
    param_names = list(param_grid.keys())
    param_values = list(param_grid.values())
    combinations = list(product(*param_values))

    print(f"Testing {len(combinations)} parameter combinations...")

    for i, combo in enumerate(combinations, 1):
        # Create config for this combination
        config = base_config.copy()
        for param_name, param_value in zip(param_names, combo):
            config[param_name] = param_value

        # Run backtest (simplified)
        # In production, run full backtest with BacktestEngine
        result = run_single_backtest(strategy_class, config)

        # Store results
        result_dict = {
            'iteration': i,
            **{name: val for name, val in zip(param_names, combo)},
            'sharpe_ratio': result.get('sharpe', 0),
            'total_return': result.get('return', 0),
            'max_drawdown': result.get('max_dd', 0),
            'total_trades': result.get('trades', 0),
            'win_rate': result.get('win_rate', 0),
            'profit_factor': result.get('profit_factor', 0),
        }
        results.append(result_dict)

        if i % 10 == 0:
            print(f"Completed {i}/{len(combinations)} iterations")

    # Convert to DataFrame and sort by optimization metric
    df_results = pd.DataFrame(results)
    df_results = df_results.sort_values(optimization_metric, ascending=False)

    return df_results


# Example for pairs trading
param_grid = {
    'lookback_period': [40, 60, 90, 120],
    'zscore_entry': [1.5, 2.0, 2.5],
    'position_size_pct': [0.05, 0.10, 0.15],
}

# results = parameter_grid_search(
#     PairsTradingStrategy,
#     base_config={'instrument_id_long': 'XLE.ARCA', ...},
#     param_grid=param_grid
# )
# print(results.head(10))
```

**Overfitting Prevention:**
- Split data into train (60%), validation (20%), test (20%)
- Only optimize on train set
- Validate on validation set
- Final evaluation on test set (never seen)
- Max parameter combinations: < 100
- Minimum trades per test: 30

---

## Performance Validation

### Critical Metrics to Track

**1. Risk-Adjusted Returns**

```python
def calculate_performance_metrics(trades: pd.DataFrame, equity_curve: pd.Series) -> dict:
    """
    Calculate comprehensive performance metrics.

    Parameters:
    - trades: DataFrame with trade history
    - equity_curve: Series with daily portfolio values

    Returns:
    - Dictionary with performance metrics
    """
    metrics = {}

    # Returns
    total_return = (equity_curve.iloc[-1] / equity_curve.iloc[0]) - 1
    metrics['total_return'] = total_return
    metrics['annualized_return'] = (1 + total_return) ** (252 / len(equity_curve)) - 1

    # Risk metrics
    returns = equity_curve.pct_change().dropna()
    metrics['volatility'] = returns.std() * np.sqrt(252)
    metrics['sharpe_ratio'] = (metrics['annualized_return'] - 0.04) / metrics['volatility']

    # Downside risk
    downside_returns = returns[returns < 0]
    downside_std = downside_returns.std() * np.sqrt(252)
    metrics['sortino_ratio'] = (metrics['annualized_return'] - 0.04) / downside_std

    # Drawdown
    cummax = equity_curve.cummax()
    drawdown = (equity_curve - cummax) / cummax
    metrics['max_drawdown'] = abs(drawdown.min())
    metrics['avg_drawdown'] = abs(drawdown[drawdown < 0].mean())

    # Trade statistics
    metrics['total_trades'] = len(trades)
    metrics['win_rate'] = len(trades[trades['pnl'] > 0]) / len(trades)
    avg_win = trades[trades['pnl'] > 0]['pnl'].mean()
    avg_loss = abs(trades[trades['pnl'] < 0]['pnl'].mean())
    metrics['avg_win_loss_ratio'] = avg_win / avg_loss if avg_loss > 0 else 0
    metrics['profit_factor'] = trades[trades['pnl'] > 0]['pnl'].sum() / abs(trades[trades['pnl'] < 0]['pnl'].sum())

    # Exposure
    metrics['avg_exposure'] = trades['position_value'].mean() / equity_curve.mean()

    return metrics


# Example usage
# metrics = calculate_performance_metrics(trades_df, equity_series)
# print(f"Sharpe Ratio: {metrics['sharpe_ratio']:.2f}")
# print(f"Max Drawdown: {metrics['max_drawdown']:.2%}")
# print(f"Win Rate: {metrics['win_rate']:.1%}")
```

**2. Strategy-Specific Validation**

**Pairs Trading:**
```python
def validate_pairs_strategy(trades: pd.DataFrame, signals: pd.DataFrame) -> dict:
    """Validate pairs trading specific metrics."""
    validation = {}

    # Cointegration stability
    validation['avg_spread_reversion_time'] = signals['holding_period'].mean()
    validation['spread_stability'] = signals['zscore'].std()

    # Market neutrality
    validation['avg_beta'] = trades['portfolio_beta'].mean()
    validation['beta_range'] = [trades['portfolio_beta'].min(), trades['portfolio_beta'].max()]

    # Mean reversion efficiency
    exits = trades[trades['exit_reason'].isin(['profit_target', 'stop_loss'])]
    validation['reversion_rate'] = len(exits[exits['exit_reason'] == 'profit_target']) / len(exits)

    return validation
```

**Momentum Breakout:**
```python
def validate_momentum_strategy(trades: pd.DataFrame) -> dict:
    """Validate momentum strategy specific metrics."""
    validation = {}

    # Trend capture
    validation['avg_trade_duration'] = trades['holding_period'].mean()
    validation['breakout_success_rate'] = len(trades[trades['pnl'] > 0]) / len(trades)

    # False breakout rate
    quick_reversals = trades[trades['holding_period'] < 2]  # Exits within 2 days
    validation['false_breakout_rate'] = len(quick_reversals[quick_reversals['pnl'] < 0]) / len(trades)

    # Risk management
    validation['avg_stop_distance'] = trades['stop_distance'].mean()
    validation['stops_hit_rate'] = len(trades[trades['exit_reason'] == 'stop_loss']) / len(trades)

    return validation
```

**Covered Calls:**
```python
def validate_covered_call_strategy(trades: pd.DataFrame) -> dict:
    """Validate covered call strategy specific metrics."""
    validation = {}

    # Income generation
    validation['avg_premium_pct'] = trades['premium_pct'].mean()
    validation['annualized_premium_income'] = validation['avg_premium_pct'] * (252 / trades['dte'].mean())

    # Assignment rate
    validation['assignment_rate'] = len(trades[trades['assigned'] == True]) / len(trades)
    validation['early_close_rate'] = len(trades[trades['closed_early'] == True]) / len(trades)

    # Total return components
    validation['dividend_income'] = trades['dividends'].sum()
    validation['option_income'] = trades['premium'].sum()
    validation['stock_appreciation'] = trades['stock_pnl'].sum()

    return validation
```

---

## Walk-Forward Analysis

### Implementation

```python
from datetime import timedelta

def walk_forward_analysis(
    strategy_class,
    data: pd.DataFrame,
    train_days: int = 252,
    test_days: int = 63,
    step_days: int = 21,
    param_grid: dict = None
) -> pd.DataFrame:
    """
    Perform walk-forward analysis.

    Parameters:
    - strategy_class: Strategy to test
    - data: Full dataset
    - train_days: Training period (days)
    - test_days: Testing period (days)
    - step_days: Step forward (days)
    - param_grid: Parameters to optimize

    Returns:
    - DataFrame with walk-forward results
    """
    results = []
    current_date = data.index[0] + timedelta(days=train_days)

    iteration = 0
    while current_date + timedelta(days=test_days) <= data.index[-1]:
        iteration += 1
        print(f"\nWalk-Forward Iteration {iteration}")
        print(f"Train: {current_date - timedelta(days=train_days)} to {current_date}")
        print(f"Test: {current_date} to {current_date + timedelta(days=test_days)}")

        # Split data
        train_data = data[
            (data.index >= current_date - timedelta(days=train_days)) &
            (data.index < current_date)
        ]
        test_data = data[
            (data.index >= current_date) &
            (data.index < current_date + timedelta(days=test_days))
        ]

        # Optimize on train data
        if param_grid:
            train_results = parameter_grid_search(
                strategy_class,
                base_config={},
                param_grid=param_grid
            )
            best_params = train_results.iloc[0].to_dict()
            train_sharpe = best_params['sharpe_ratio']
        else:
            best_params = {}
            train_sharpe = 0

        # Test on test data
        test_result = run_single_backtest(strategy_class, best_params, test_data)
        test_sharpe = test_result['sharpe']

        # Store results
        results.append({
            'iteration': iteration,
            'train_start': train_data.index[0],
            'train_end': train_data.index[-1],
            'test_start': test_data.index[0],
            'test_end': test_data.index[-1],
            'train_sharpe': train_sharpe,
            'test_sharpe': test_sharpe,
            'sharpe_degradation': (train_sharpe - test_sharpe) / train_sharpe if train_sharpe > 0 else 0,
            **best_params
        })

        # Step forward
        current_date += timedelta(days=step_days)

    return pd.DataFrame(results)


# Example usage
# wf_results = walk_forward_analysis(
#     PairsTradingStrategy,
#     data=historical_data,
#     train_days=252,
#     test_days=63,
#     step_days=21,
#     param_grid={'lookback_period': [40, 60, 90], 'zscore_entry': [1.5, 2.0, 2.5]}
# )
#
# print(f"Average test Sharpe: {wf_results['test_sharpe'].mean():.2f}")
# print(f"Average degradation: {wf_results['sharpe_degradation'].mean():.1%}")
```

**Acceptance Criteria:**
- Average test Sharpe > 1.0
- Sharpe degradation < 30% (train to test)
- Consistency: > 60% of windows have positive Sharpe
- No parameter "cliff edges" (small changes = big differences)

---

## Paper Trading Transition

### Pre-Launch Checklist

**Week Before Launch:**
- [ ] All backtests completed with satisfactory results
- [ ] Walk-forward analysis shows consistency
- [ ] Code reviewed and tested
- [ ] Risk limits configured and tested
- [ ] Moomoo paper trading account set up
- [ ] API connection tested (quotes, orders, positions)
- [ ] Monitoring dashboard operational
- [ ] Alert system tested
- [ ] Position sizing logic verified
- [ ] Order execution logic tested

**Launch Day:**
- [ ] Reduced position sizes (50% of target)
- [ ] Single strategy launch (not all three)
- [ ] Real-time monitoring for first hour
- [ ] Verify order fills and prices
- [ ] Check risk metrics updating
- [ ] Validate P&L calculation

### Execution Quality Monitoring

```python
def monitor_execution_quality(trades: pd.DataFrame) -> dict:
    """
    Monitor execution quality metrics.

    Compares expected vs actual execution prices, slippage, and timing.
    """
    metrics = {}

    # Slippage analysis
    trades['actual_slippage'] = (trades['fill_price'] - trades['signal_price']) / trades['signal_price']
    trades['expected_slippage'] = trades['expected_slippage_bps'] / 10000

    metrics['avg_slippage_bps'] = trades['actual_slippage'].mean() * 10000
    metrics['slippage_vs_expected'] = metrics['avg_slippage_bps'] / trades['expected_slippage'].mean()

    # Fill rate
    metrics['fill_rate'] = len(trades[trades['status'] == 'filled']) / len(trades)

    # Latency
    trades['signal_to_order_ms'] = (trades['order_time'] - trades['signal_time']).dt.total_seconds() * 1000
    trades['order_to_fill_ms'] = (trades['fill_time'] - trades['order_time']).dt.total_seconds() * 1000

    metrics['avg_signal_to_order_latency'] = trades['signal_to_order_ms'].mean()
    metrics['avg_order_to_fill_latency'] = trades['order_to_fill_ms'].mean()

    # Price impact
    trades['price_impact_bps'] = abs(
        (trades['post_fill_price'] - trades['pre_fill_price']) / trades['pre_fill_price']
    ) * 10000
    metrics['avg_price_impact_bps'] = trades['price_impact_bps'].mean()

    return metrics


# Example thresholds
# if metrics['avg_slippage_bps'] > 15:  # More than 0.15%
#     print("WARNING: Slippage exceeds expectations")
# if metrics['fill_rate'] < 0.95:  # Less than 95%
#     print("WARNING: Low fill rate, check liquidity")
```

### Performance Tracking Dashboard

**Daily Metrics:**
```python
def generate_daily_report(date: str, portfolio_state: dict, trades: list) -> str:
    """Generate daily performance report."""

    report = f"""
    Daily Trading Report - {date}
    ================================

    Portfolio Summary:
    ------------------
    Starting Balance: ${portfolio_state['start_balance']:,.2f}
    Ending Balance:   ${portfolio_state['end_balance']:,.2f}
    Daily P&L:        ${portfolio_state['daily_pnl']:,.2f} ({portfolio_state['daily_return']:.2%})
    MTD Return:       {portfolio_state['mtd_return']:.2%}
    YTD Return:       {portfolio_state['ytd_return']:.2%}

    Risk Metrics:
    -------------
    Current Drawdown: {portfolio_state['current_dd']:.2%}
    Max Drawdown:     {portfolio_state['max_dd']:.2%}
    Daily VaR (95%):  ${portfolio_state['var_95']:,.0f}
    Gross Exposure:   {portfolio_state['gross_exposure']:.1%}
    Net Exposure:     {portfolio_state['net_exposure']:.1%}

    Trading Activity:
    -----------------
    Trades Today:     {len(trades)}
    Win Rate (30d):   {portfolio_state['win_rate_30d']:.1%}
    Sharpe Ratio (30d): {portfolio_state['sharpe_30d']:.2f}

    Open Positions:
    ---------------
    """

    for position in portfolio_state['open_positions']:
        report += f"  {position['symbol']}: {position['quantity']} @ ${position['avg_price']:.2f} "
        report += f"(P&L: ${position['unrealized_pnl']:,.2f})\n"

    return report
```

---

## Monitoring and Alerting

### Alert Triggers

```python
class AlertManager:
    """Manage trading alerts and notifications."""

    def __init__(self, config: dict):
        self.config = config
        self.alert_history = []

    def check_alerts(self, portfolio_state: dict, latest_trades: list):
        """Check for alert conditions."""

        # Drawdown alert
        if portfolio_state['current_dd'] > self.config['max_dd_warning']:
            self.send_alert(
                level="WARNING",
                message=f"Drawdown {portfolio_state['current_dd']:.2%} exceeds warning threshold"
            )

        if portfolio_state['current_dd'] > self.config['max_dd_limit']:
            self.send_alert(
                level="CRITICAL",
                message=f"Drawdown {portfolio_state['current_dd']:.2%} exceeds limit - STOPPING TRADING"
            )
            return "HALT_TRADING"

        # Daily loss alert
        if portfolio_state['daily_pnl'] < -self.config['daily_loss_limit'] * portfolio_state['start_balance']:
            self.send_alert(
                level="WARNING",
                message=f"Daily loss ${portfolio_state['daily_pnl']:,.0f} exceeds limit"
            )

        # Sharpe degradation
        if portfolio_state['sharpe_30d'] < self.config['min_sharpe']:
            self.send_alert(
                level="INFO",
                message=f"Sharpe ratio {portfolio_state['sharpe_30d']:.2f} below target"
            )

        # Execution quality
        recent_trades = latest_trades[-10:]  # Last 10 trades
        if recent_trades:
            avg_slippage = sum(t['actual_slippage_bps'] for t in recent_trades) / len(recent_trades)
            if avg_slippage > self.config['max_slippage_bps']:
                self.send_alert(
                    level="WARNING",
                    message=f"High slippage detected: {avg_slippage:.1f} bps"
                )

        return "OK"

    def send_alert(self, level: str, message: str):
        """Send alert notification."""
        alert = {
            'timestamp': pd.Timestamp.now(),
            'level': level,
            'message': message
        }
        self.alert_history.append(alert)

        # In production: send email, SMS, or webhook
        print(f"[{level}] {message}")


# Example configuration
alert_config = {
    'max_dd_warning': 0.10,  # 10% warning
    'max_dd_limit': 0.15,    # 15% halt
    'daily_loss_limit': 0.05, # 5% daily loss
    'min_sharpe': 0.5,       # Minimum Sharpe
    'max_slippage_bps': 15,  # 0.15% slippage
}

# alert_mgr = AlertManager(alert_config)
# status = alert_mgr.check_alerts(portfolio_state, recent_trades)
```

### Weekly Review Template

```markdown
# Weekly Trading Review - [Week of DATE]

## Strategy Performance

### Strategy 1: Pairs Trading
- Trades: X
- Win Rate: X%
- Sharpe Ratio: X.XX
- P&L: $X,XXX
- Notable Events: [Any cointegration breakdowns, unusual spreads]

### Strategy 2: Momentum Breakout
- Trades: X
- Win Rate: X%
- Sharpe Ratio: X.XX
- P&L: $X,XXX
- Notable Events: [False breakouts, sector rotation]

### Strategy 3: Covered Calls
- Trades: X
- Premium Collected: $X,XXX
- Assignments: X
- P&L: $X,XXX
- Notable Events: [Early closures, rolls]

## Risk Review
- Max Drawdown: X.X%
- VaR (95%): $X,XXX
- Exposure Analysis: [Sector concentration, correlations]
- Limit Breaches: [Any risk limit violations]

## Execution Quality
- Average Slippage: X.XX bps
- Fill Rate: XX%
- Latency: XX ms
- Issues: [Any execution problems]

## Action Items
- [ ] Adjust parameter X for Strategy Y
- [ ] Investigate abnormal slippage on DATE
- [ ] Review correlation changes
- [ ] Update stop levels if needed

## Next Week Focus
- [Specific monitoring priorities]
- [Parameter changes to test]
- [Market events to watch]
```

---

## Summary: Go/No-Go Decision Criteria

### Backtest Results Must Meet:
- [x] Sharpe ratio > 1.0 (target 1.5)
- [x] Max drawdown < 20% (target < 15%)
- [x] Win rate > 50% (target > 55%)
- [x] Minimum 100 trades over test period
- [x] Profit factor > 1.3
- [x] Walk-forward analysis shows consistency

### Walk-Forward Analysis Must Show:
- [x] Average test Sharpe > 1.0
- [x] Sharpe degradation < 30%
- [x] > 60% of windows profitable
- [x] No extreme parameter sensitivity

### Paper Trading Readiness:
- [x] API connection stable (> 99% uptime)
- [x] Order execution tested successfully
- [x] Risk limits properly configured
- [x] Monitoring dashboard operational
- [x] Alert system functional
- [x] Position sizing logic verified

### Paper Trading Success (After 30 Days):
- [x] Sharpe ratio within 20% of backtest
- [x] Actual slippage < 2x expected
- [x] Fill rate > 95%
- [x] No risk limit breaches
- [x] Drawdown < backtest worst case

**If any critical criterion is not met, DO NOT proceed to live trading.**

---

## Appendix: Example Test Results Format

```python
# Expected backtest output format
backtest_results = {
    'metadata': {
        'strategy': 'PairsTradingStrategy',
        'pair': 'XLE/XOP',
        'start_date': '2023-01-01',
        'end_date': '2025-11-30',
        'initial_capital': 100000,
    },
    'performance': {
        'total_return': 0.24,  # 24%
        'annualized_return': 0.12,  # 12%
        'sharpe_ratio': 1.45,
        'sortino_ratio': 1.82,
        'max_drawdown': 0.089,  # 8.9%
        'volatility': 0.08,  # 8%
    },
    'trades': {
        'total': 67,
        'wins': 39,
        'losses': 28,
        'win_rate': 0.582,
        'avg_win': 1250.00,
        'avg_loss': -780.00,
        'profit_factor': 1.87,
        'avg_holding_period': 3.2,  # days
    },
    'risk': {
        'var_95': 0.031,  # 3.1% daily VaR
        'avg_exposure': 0.19,  # 19% average exposure
        'max_exposure': 0.24,  # 24% max exposure
        'avg_beta': 0.02,  # Near market neutral
    }
}
```

This comprehensive validation framework ensures strategies are thoroughly tested before risking capital in paper or live trading.
