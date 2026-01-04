# Nautilus Trader - Backtesting Guide

**Last Updated:** October 2025

## Overview

NautilusTrader provides high-fidelity backtesting with realistic market simulation.

### Key Features
- Event-driven simulation
- Multiple data types (ticks, bars, order books)
- Realistic order matching and fills
- Configurable fill models and slippage
- Multiple account types (Cash, Margin, Betting)
- Same code for backtest/sandbox/live

## APIs

### Low-Level API
- Full programmatic control
- Build backtest step by step
- Maximum flexibility
- More verbose

### High-Level API (Recommended)
- Configuration-based
- Concise and declarative
- Easier to serialize and distribute
- Uses `BacktestNode` and config objects

## Backtest Configuration

### Basic Structure

```python
from nautilus_trader.backtest.node import BacktestNode
from nautilus_trader.config import BacktestRunConfig, BacktestEngineConfig, BacktestDataConfig, BacktestVenueConfig

config = BacktestRunConfig(
    engine=BacktestEngineConfig(
        strategies=[strategy_config],
        # Optional: actors, exec_algorithms
    ),
    data=BacktestDataConfig(
        catalog_path="./catalog",
        data_cls=QuoteTick,
        instrument_id=instrument_id,
        start_time="2024-01-01",
        end_time="2024-12-31",
    ),
    venues=[
        BacktestVenueConfig(
            name="BINANCE",
            oms_type=OmsType.NETTING,
            account_type=AccountType.MARGIN,
            base_currency=USD,
            starting_balances=["1000000 USD"],
        )
    ],
)

node = BacktestNode(configs=[config])
results = node.run()
```

## Data Requirements

### Data Types Supported

1. **OrderBookDelta / OrderBookDeltas**: Most granular, highest fidelity
2. **QuoteTick**: Top-of-book quotes
3. **TradeTick**: Individual trades  
4. **Bar**: OHLCV bars
5. **Custom Data**: Any custom data type

### Order Book Granularity

- **L1 (BBO)**: Best bid/offer only
  - Fastest simulation
  - Less realistic fills
  
- **L2 (Market-by-price)**: Multiple price levels
  - Aggregated liquidity per price
  - Good balance of speed and realism
  
- **L3 (Market-by-order)**: Individual orders
  - Highest fidelity
  - Slowest simulation
  - Most realistic fills

### Data Loading

#### From ParquetDataCatalog
```python
BacktestDataConfig(
    catalog_path="./catalog",
    data_cls=QuoteTick,
    instrument_id=instrument_id,
    start_time=start,
    end_time=end,
)
```

#### Multiple Instruments
```python
# Load data for multiple instruments
data_configs = [
    BacktestDataConfig(
        catalog_path="./catalog",
        data_cls=QuoteTick,
        instrument_id="BTCUSDT-PERP.BINANCE",
    ),
    BacktestDataConfig(
        catalog_path="./catalog",
        data_cls=QuoteTick,
        instrument_id="ETHUSDT-PERP.BINANCE",
    ),
]
```

## Timestamp Conventions

### Critical Understanding

- **ts_event**: When event occurred at exchange
- **ts_init**: When data entered system

For backtesting:
- Simulation clock advances through `ts_event` timestamps
- Data replayed in `ts_event` order
- Strategy sees data as if receiving it historically

### Best Practice
- Always use `ts_event` for strategy logic
- Represents "market time"
- `ts_init` useful for latency analysis only

## Bar Aggregation

### Available Methods

1. **Time-based**: SECOND, MINUTE, HOUR, DAY, WEEK, MONTH
2. **Tick-based**: TICK (count of trades)
3. **Volume-based**: VOLUME
4. **Value-based**: VALUE (notional)
5. **Exotic**: RENKO, POINT_AND_FIGURE, HEIKIN_ASHI

### Bar Building

Backtest engine can build bars from ticks:
```python
# Subscribe to bars in strategy
self.subscribe_bars(BarType.from_str("ETHUSDT-PERP.BINANCE-1-MINUTE-LAST"))

# Engine builds bars from QuoteTick or TradeTick data automatically
```

### Pre-aggregated vs Real-time Aggregation

- **Pre-aggregated**: Load bars directly from catalog (faster)
- **Real-time**: Engine aggregates from ticks (more flexible, tests aggregation logic)

## Fill Models

### Purpose
Determine how orders are filled during backtest simulation.

### Built-in Fill Models

1. **FillModel** (Base): Simple immediate fills
2. **LatencyModel**: Adds processing/network latency
3. **L1 OrderBook Model**: Uses L1 data for fills
4. **L2 OrderBook Model**: Uses L2 data for fills (most realistic)
5. **L3 OrderBook Model**: Uses L3 data for fills (highest fidelity)

### Configuration

```python
BacktestVenueConfig(
    name="BINANCE",
    fill_model=YourCustomFillModel(),  # Optional custom model
)
```

### Slippage

Fill models can simulate:
- **Bid-ask spread**: Realistic entry/exit costs
- **Slippage**: Price movement during order execution
- **Partial fills**: Order not completely filled
- **Latency**: Delay between order submission and execution

## Account Types

### AccountType.CASH

- Cash-only trading (no margin)
- Must have full capital for each trade
- Common for equity/stock trading
- Simple P&L calculation

### AccountType.MARGIN

- Leveraged trading
- Requires margin for positions
- Complex P&L with funding/interest
- Common for FX, crypto derivatives

### AccountType.BETTING

- Betting exchange style (e.g., Betfair)
- Liability-based risk
- Special P&L calculation for betting

### Configuration

```python
BacktestVenueConfig(
    name="BINANCE",
    account_type=AccountType.MARGIN,
    base_currency=USD,
    starting_balances=["1000000 USD"],
)
```

## Margin Models

For MARGIN accounts:

### Standard Margin
- Fixed margin requirement per position
- Based on notional value
- Common for FX

### Leveraged Margin  
- Leverage-based margin calculation
- Margin = Position Value / Leverage
- Common for crypto derivatives

### Configuration

Via instrument definition:
```python
instrument.margin_init  # Initial margin requirement
instrument.margin_maint  # Maintenance margin requirement
```

## Venue Configuration

### Complete Example

```python
BacktestVenueConfig(
    name="BINANCE",
    oms_type=OmsType.NETTING,
    account_type=AccountType.MARGIN,
    base_currency=USD,
    starting_balances=["1000000 USD"],
    default_leverage=Decimal("10.0"),
    leverages={instrument_id: Decimal("20.0")},  # Per-instrument
    modules=[],  # Optional risk/exec modules
    fill_model=None,  # Optional custom fill model
    fee_model=None,  # Optional custom fee model
    latency_model=None,  # Optional latency model
    book_type=BookType.L2_MBP,  # L1, L2, or L3
)
```

## Running Backtests

### Single Backtest

```python
node = BacktestNode(configs=[config])
results = node.run()
```

### Multiple Backtests (Parameter Sweep)

```python
configs = []
for param_value in [10, 20, 30, 40, 50]:
    strategy_config = MyStrategyConfig(
        instrument_id=instrument_id,
        parameter=param_value,
        order_id_tag=f"param_{param_value}",
    )
    
    config = BacktestRunConfig(
        engine=BacktestEngineConfig(strategies=[strategy_config]),
        data=data_config,
        venues=[venue_config],
    )
    configs.append(config)

node = BacktestNode(configs=configs)
results = node.run()
```

### Parallel Backtests

```python
# Automatic parallelization
node = BacktestNode(configs=configs)
results = node.run()  # Runs configs in parallel

# Results indexed by run ID
for run_id, result in results.items():
    print(f"Run {run_id}: {result}")
```

## Analyzing Results

### Available Metrics

After backtest:
```python
# Access portfolio statistics
portfolio = engine.trader.generate_account_report()
print(portfolio)

# Access order reports
orders = engine.trader.generate_order_fills_report()
print(orders)

# Access position reports
positions = engine.trader.generate_positions_report()
print(positions)

# Performance statistics
stats = result.get_statistics()
```

### Key Metrics
- Total PnL
- Sharpe Ratio
- Max Drawdown
- Win Rate
- Average Win/Loss
- Number of trades
- Expectancy

## Best Practices

### Data Preparation

1. **Use ParquetDataCatalog**: Efficient storage and retrieval
2. **Validate Data Quality**: Check for gaps, outliers
3. **Match Data to Strategy**: Bars for trend strategies, ticks for HFT
4. **Include Multiple Instruments**: Test correlation strategies

### Configuration

5. **Match Venue Settings**: OMS type, account type to reality
6. **Set Realistic Starting Capital**: Don't overtrade account
7. **Configure Fill Models**: Use L2/L3 for realistic fills
8. **Set Proper Latency**: Network/processing delays matter

### Strategy Design

9. **Warm Up Indicators**: Request historical data in `on_start`
10. **Handle Edge Cases**: Missing data, rejected orders
11. **Same Code for Live**: Design with live trading in mind
12. **Manage Risk**: Set stops, position sizing

### Execution

13. **Start with Single Instrument**: Debug strategy logic first
14. **Parameter Sweeps**: Find optimal parameters
15. **Walk-Forward Testing**: Prevent overfitting
16. **Out-of-Sample Testing**: Reserve data for validation

### Analysis

17. **Review All Metrics**: Not just total PnL
18. **Analyze Drawdowns**: Maximum and duration
19. **Check Trade Distribution**: Wins vs losses
20. **Validate Against Reality**: Compare to known benchmarks

## Common Pitfalls

### Lookahead Bias
- Using future data in decisions
- Bar close price available immediately (use `on_bar` carefully)
- Check indicator calculations

### Survivorship Bias
- Only testing instruments that still exist
- Include delisted/expired instruments

### Overfitting
- Too many parameters
- Optimizing on test data
- Use walk-forward and out-of-sample validation

### Unrealistic Fills
- Assuming immediate fills at exact price
- Ignoring slippage and spreads
- Use proper fill models

### Ignoring Costs
- Trading fees (maker/taker)
- Funding rates (perpetuals)
- Slippage
- Configure fee models properly

## Performance Optimization

### Speed Improvements

1. **Use Bars Instead of Ticks**: Much faster if appropriate
2. **Reduce Data Granularity**: L1 vs L2 vs L3
3. **Limit Instruments**: Test on subset first
4. **Parallel Execution**: Multiple backtests concurrently
5. **Compiled Cython**: Use release builds

### Memory Management

6. **Stream Data**: Don't load all in memory
7. **Clear Cache**: Between backtest runs
8. **Partition Data**: By date ranges

## Advanced Features

### Custom Fill Models

Implement custom matching logic:
```python
from nautilus_trader.backtest.models import FillModel

class MyFillModel(FillModel):
    def is_limit_filled(self, order, bid, ask):
        # Custom logic
        return False
    
    def is_stop_triggered(self, order, bid, ask):
        # Custom logic
        return False
```

### Custom Fee Models

```python
from nautilus_trader.backtest.models import FeeModel

class MyFeeModel(FeeModel):
    def get_fees(self, order, fill_px, fill_qty):
        # Calculate custom fees
        return commission
```

### Simulated Exchange Modules

Add custom venue behavior:
- Order matching rules
- Risk checks
- Margin calculations
- Position limits
