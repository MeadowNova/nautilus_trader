# Nautilus Trader - Data System & Management

**Last Updated:** October 2025

## Data Types

### Market Data Types

1. **OrderBookDelta**: Incremental order book change (L2/L3)
2. **OrderBookDeltas**: Batch of deltas with metadata
3. **OrderBook**: Full order book snapshot (L1/L2/L3)
4. **QuoteTick**: Top-of-book bid and ask
5. **TradeTick**: Individual trade execution
6. **Bar**: OHLCV aggregated data
7. **Instrument**: Trading instrument definition
8. **InstrumentStatus**: Trading status (open, closed, pre-open, etc.)
9. **InstrumentClose**: Session close price
10. **Custom Data**: User-defined data types

### Order Book Levels

- **L1 (Top-of-book)**: Best bid and ask only
- **L2 (Market-by-price)**: Multiple price levels, aggregated quantity
- **L3 (Market-by-order)**: Individual orders with IDs

### Data Attributes

All market data has:
- `ts_event`: When event occurred at source (exchange timestamp)
- `ts_init`: When data initialized in system (local timestamp)

## Timestamp System

### Key Concepts
- **ts_event**: Exchange/venue timestamp (when event occurred)
- **ts_init**: System timestamp (when data received/created locally)
- All timestamps in **nanoseconds** (UNIX epoch)
- Strategies can access `self.clock.timestamp_ns()`

### Best Practices
- Use `ts_event` for strategy logic (true event time)
- Use `ts_init` for latency analysis
- Be aware of timestamp precision from different venues

## Bars and Aggregation

### Bar Types

Format: `{instrument_id}-{step}-{aggregation}-{price_type}`

Example: `ETHUSDT-PERP.BINANCE-100-TICK-LAST`

### Aggregation Methods

1. **TICK**: Aggregate by number of ticks/trades
   - `100-TICK`: Every 100 trades
   
2. **VOLUME**: Aggregate by volume
   - `1000-VOLUME`: Every 1000 units traded
   
3. **VALUE**: Aggregate by notional value
   - `100000-VALUE`: Every $100,000 traded
   
4. **MILLISECOND**: Time-based (sub-second)
   - `100-MILLISECOND`: Every 100ms
   
5. **SECOND**: Time-based
   - `1-SECOND`, `15-SECOND`: Every 1s, 15s
   
6. **MINUTE**: Time-based
   - `1-MINUTE`, `5-MINUTE`, `15-MINUTE`
   
7. **HOUR**: Time-based
   - `1-HOUR`, `4-HOUR`
   
8. **DAY**: Time-based
   - `1-DAY`: Daily bars
   
9. **WEEK**: Time-based
   - `1-WEEK`: Weekly bars
   
10. **MONTH**: Time-based
    - `1-MONTH`: Monthly bars

### Exotic Bar Types

11. **RENKO**: Fixed price movement bars
    - `10-RENKO`: $10 price movement
    
12. **POINT_AND_FIGURE**: Price reversal bars
    - `10-POINT_AND_FIGURE`
    
13. **HEIKIN_ASHI**: Smoothed candlesticks
    - `1-MINUTE-HEIKIN_ASHI`

### Price Types

- **LAST**: Last trade price (default)
- **BID**: Bid price (quote-based)
- **ASK**: Ask price (quote-based)
- **MID**: Midpoint of bid/ask

### Composite Bar Types

Can composite from different price types:
- `ETHUSDT-100-TICK-MID` (aggregated from quote ticks)
- `BTCUSDT-1-MINUTE-BID` (bid price bars)

## Instrument Definitions

### Core Attributes
```python
instrument_id: InstrumentId
native_symbol: Symbol  # Exchange's native symbol
asset_class: AssetClass
instrument_class: InstrumentClass
quote_currency: Currency
is_inverse: bool
price_precision: int
price_increment: Price
size_precision: int
size_increment: Quantity
multiplier: Quantity
lot_size: Quantity | None
max_quantity: Quantity | None
min_quantity: Quantity | None
max_price: Price | None
min_price: Price | None
margin_init: Decimal  # Initial margin requirement
margin_maint: Decimal  # Maintenance margin requirement
maker_fee: Decimal
taker_fee: Decimal
ts_event: int
ts_init: int
```

### Instrument Types

- **Equity**: Stocks
- **FuturesContract**: Futures
- **OptionsContract**: Options
- **CurrencyPair**: Spot FX
- **CryptoFuture**: Crypto futures
- **CryptoPerpetual**: Crypto perpetual swaps
- **Betting**: Sports betting instruments

## Data Subscriptions

### From Strategy

```python
# Subscribe to data (called in on_start typically)
self.subscribe_order_book_deltas(instrument_id, depth=10)
self.subscribe_order_book(instrument_id, depth=20)
self.subscribe_quote_ticks(instrument_id)
self.subscribe_trade_ticks(instrument_id)
self.subscribe_bars(bar_type)
self.subscribe_instrument_status(instrument_id)
self.subscribe_instrument_close(instrument_id)
self.subscribe_data(data_type)  # Custom data

# Unsubscribe
self.unsubscribe_order_book_deltas(instrument_id)
self.unsubscribe_order_book(instrument_id)
self.unsubscribe_quote_ticks(instrument_id)
self.unsubscribe_trade_ticks(instrument_id)
self.unsubscribe_bars(bar_type)
self.unsubscribe_data(data_type)
```

## Data Requests

### Historical Data
```python
# Request historical bars
self.request_bars(
    bar_type,
    start=start_time,  # Optional
    end=end_time,      # Optional
)

# Request historical quote ticks
self.request_quote_ticks(
    instrument_id,
    start=start_time,
    end=end_time,
)

# Request historical trade ticks
self.request_trade_ticks(
    instrument_id,
    start=start_time,
    end=end_time,
)

# Request instrument
self.request_instrument(instrument_id)

# Custom data request
self.request_data(data_type)
```

## ParquetDataCatalog

### Purpose
- Persist data to disk in Parquet format
- Query and load data for backtesting
- Manage large datasets efficiently

### Basic Usage

```python
from nautilus_trader.persistence.catalog import ParquetDataCatalog

# Initialize catalog
catalog = ParquetDataCatalog("./catalog")

# Write data
catalog.write_data([tick1, tick2, tick3])

# Query data
instruments = catalog.instruments(instrument_ids=[instrument_id])
quote_ticks = catalog.quote_ticks(instrument_ids=[instrument_id])
trade_ticks = catalog.trade_ticks(instrument_ids=[instrument_id])
bars = catalog.bars(bar_types=[bar_type])
```

### Data Organization

Catalog stores data organized by:
- Instrument
- Data type
- Date partitions (for efficient queries)

### Integration with Backtesting

```python
from nautilus_trader.backtest.node import BacktestNode
from nautilus_trader.persistence.catalog import ParquetDataCatalog

# Load data from catalog
catalog = ParquetDataCatalog("./catalog")

# Configure backtest
config = BacktestRunConfig(
    engine=BacktestEngineConfig(strategies=[strategy_config]),
    data=BacktestDataConfig(
        catalog_path="./catalog",
        data_cls=QuoteTick,
        instrument_id=instrument_id,
        start_time=start,
        end_time=end,
    ),
    venues=[BacktestVenueConfig(...)],
)

# Run backtest
node = BacktestNode(configs=[config])
results = node.run()
```

## Custom Data Types

### Implementation

```python
from nautilus_trader.core.data import Data

class MyCustomData(Data):
    def __init__(
        self,
        value: float,
        ts_event: int,
        ts_init: int,
    ) -> None:
        super().__init__()
        self.value = value
        self._ts_event = ts_event
        self._ts_init = ts_init
    
    @property
    def ts_event(self) -> int:
        return self._ts_event
    
    @property
    def ts_init(self) -> int:
        return self._ts_init
```

### Using Custom Data

```python
# Subscribe in strategy
data_type = DataType(MyCustomData, metadata={"source": "provider"})
self.subscribe_data(data_type)

# Handle in strategy
def on_data(self, data: Data) -> None:
    if isinstance(data, MyCustomData):
        self.log.info(f"Received custom data: {data.value}")
```

## Data Flow Architecture

1. **External Source** → Data arrives from exchange/provider
2. **DataClient** → Normalizes to Nautilus data types
3. **DataEngine** → Routes to appropriate handlers
4. **Cache** → Stores latest data
5. **MessageBus** → Publishes to subscribers
6. **Strategy/Actor** → Receives data in handler methods

## Best Practices

1. **Use Appropriate Bar Types**: Match aggregation to strategy timeframe
2. **Leverage Cache**: Fast access to latest data
3. **Request Historical Data**: Load past data in `on_start` for indicator warmup
4. **Unsubscribe in on_stop**: Clean up subscriptions
5. **Use ParquetDataCatalog**: Efficient storage and retrieval for backtesting
6. **Timestamp Awareness**: Use `ts_event` for strategy logic
7. **Check Data Availability**: Handle cases where data not yet available
8. **Custom Data for Signals**: Implement custom data types for external signals
9. **Order Book Depth**: Request appropriate depth (L1 faster, L2/L3 more detail)
10. **Bar Aggregation Choice**: TICK/VOLUME bars adapt to market activity, TIME bars for fixed intervals
