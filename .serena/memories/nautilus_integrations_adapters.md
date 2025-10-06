# Nautilus Trader - Integrations & Adapters

**Last Updated:** October 2025

## Available Integrations

### Cryptocurrency Exchanges

| Exchange | Spot | Futures | Perpetuals | Options | Status |
|----------|------|---------|------------|---------|--------|
| **Binance** | ✓ | ✓ | ✓ | - | Full support |
| **Bybit** | ✓ | ✓ | ✓ | ✓ | Full support |
| **BitMEX** | - | ✓ | ✓ | - | Full support |
| **OKX** | ✓ | ✓ | ✓ | ✓ | Full support |
| **Coinbase Intx** | ✓ | ✓ | ✓ | - | Full support |
| **dYdX** | - | - | ✓ | - | Full support |
| **Hyperliquid** | - | - | ✓ | - | In development |

### Traditional Brokers & Data

| Provider | Market Data | Execution | Status |
|----------|-------------|-----------|--------|
| **Interactive Brokers** | ✓ | ✓ | Full support |
| **Databento** | ✓ | - | Data only |
| **Tardis** | ✓ | - | Data only (historical) |
| **Polygon.io** | ✓ | - | Data only |

### Other

| Provider | Type | Status |
|----------|------|--------|
| **Betfair** | Sports betting exchange | Full support |
| **Polymarket** | Prediction markets | Full support |

## Adapter Architecture

### Standard Components

Each integration adapter typically includes:

1. **HttpClient**: Low-level REST API connectivity
2. **WebSocketClient**: Low-level WebSocket API connectivity  
3. **InstrumentProvider**: Parse and load instruments
4. **DataClient**: Manage market data feeds
5. **ExecutionClient**: Handle account management and order execution
6. **LiveDataClientFactory**: Factory for data clients (used by trading node)
7. **LiveExecClientFactory**: Factory for execution clients (used by trading node)

### Usage Pattern

Most users work with high-level configuration, not direct component usage:

```python
from nautilus_trader.adapters.binance import BINANCE
from nautilus_trader.live.node import TradingNode

config = TradingNodeConfig(
    data_clients={BINANCE: {...}},
    exec_clients={BINANCE: {...}},
)

node = TradingNode(config=config)
node.add_data_client_factory(BINANCE, BinanceLiveDataClientFactory)
node.add_exec_client_factory(BINANCE, BinanceLiveExecClientFactory)
node.build()
```

## Binance Integration

### Product Support

- **Spot Markets**: Full support (including Binance US)
- **USDT-Margined Futures**: Perpetuals and delivery
- **Coin-Margined Futures**: Perpetuals and delivery
- **Margin Trading**: Not yet implemented

### Symbology

Nautilus appends `-PERP` suffix to perpetual contracts:
- Native Binance: `BTCUSDT` (ambiguous - could be spot or perpetual)
- Nautilus spot: `BTCUSDT.BINANCE`
- Nautilus perpetual: `BTCUSDT-PERP.BINANCE`

### Custom Data Types

- **BinanceTicker**: 24-hour ticker data
- **BinanceBar**: Bar data with additional volume metrics
- **BinanceFuturesMarkPriceUpdate**: Mark price and funding rate updates

### Order Capabilities

#### Order Types by Account

| Order Type | Spot | Margin | USDT Futures | Coin Futures |
|------------|------|--------|--------------|--------------|
| MARKET | ✓ | ✓ | ✓ | ✓ |
| LIMIT | ✓ | ✓ | ✓ | ✓ |
| STOP_MARKET | - | ✓ | ✓ | ✓ |
| STOP_LIMIT | ✓ | ✓ | ✓ | ✓ |
| MARKET_IF_TOUCHED | - | - | ✓ | ✓ |
| LIMIT_IF_TOUCHED | ✓ | ✓ | ✓ | ✓ |
| TRAILING_STOP_MARKET | - | - | ✓ | ✓ |

#### Time in Force

- **GTC**: All products
- **GTD**: Futures native, Spot/Margin converted to GTC with warning
- **FOK**: All products
- **IOC**: All products

#### Execution Instructions

- **post_only**: All products (LIMIT only)
- **reduce_only**: Futures only

### Binance-Specific Features

#### Price Match (Futures Only)

Delegate price selection to exchange:
```python
order = strategy.order_factory.limit(...)
strategy.submit_order(order, params={"price_match": "QUEUE"})
```

Valid values: `OPPONENT`, `OPPONENT_5/10/20`, `QUEUE`, `QUEUE_5/10/20`

#### Trailing Stops

Binance uses **activation price** concept:
- ⚠️ Must use `activation_price`, not `trigger_price`
- Activation price triggers the trailing mechanism
- Trigger price calculated automatically from callback rate

```python
stop = strategy.order_factory.trailing_stop_market(
    instrument_id=instrument_id,
    order_side=OrderSide.SELL,
    quantity=qty,
    trailing_offset=offset,
    activation_price=activation_price,  # Required for Binance
)
```

### Configuration

```python
config = TradingNodeConfig(
    data_clients={
        BINANCE: {
            "api_key": "YOUR_KEY",
            "api_secret": "YOUR_SECRET",
            "account_type": "spot",  # spot, margin, usdt_future, coin_future
            "base_url_http": None,  # Optional override
            "base_url_ws": None,    # Optional override
            "us": False,            # True for Binance US
        },
    },
    exec_clients={
        BINANCE: {
            "api_key": "YOUR_KEY",
            "api_secret": "YOUR_SECRET",
            "account_type": "usdt_future",
            "use_gtd": True,           # Use Binance GTD vs local management
            "use_reduce_only": True,   # Send reduce_only to exchange
            "use_position_ids": True,  # Use hedging position IDs
            "futures_leverages": {"BTCUSDT-PERP.BINANCE": 10},
            "futures_margin_types": {"BTCUSDT-PERP.BINANCE": "isolated"},
        },
    },
)
```

### Rate Limiting

Token bucket system approximates Binance interval-based limits:

| Endpoint | Limit (weight/min) |
|----------|-------------------|
| Global (Spot) | 6,000 |
| Global (Futures) | 2,400 |
| Order placement (Spot) | 3,000 |
| Order placement (Futures) | 1,200 |

⚠️ Exceeding limits → HTTP 429 and potential IP bans

## Bybit Integration

### Product Support

- **Spot**: Full support with margin trading
- **Linear**: USDT/USDC margined perpetuals and futures
- **Inverse**: Coin-margined perpetuals and futures
- **Options**: USDC-settled options

### Symbology

Product category suffixes distinguish instrument types:
- Spot: `ETHUSDT-SPOT.BYBIT`
- Linear perpetuals: `BTCUSDT-LINEAR.BYBIT`
- Inverse perpetuals: `BTCUSD-INVERSE.BYBIT`
- Options: `BTC-31DEC21-50000-C-OPTION.BYBIT`

### Order Capabilities

#### Order Types

| Order Type | Spot | Linear | Inverse |
|------------|------|--------|---------|
| MARKET | ✓ | ✓ | ✓ |
| LIMIT | ✓ | ✓ | ✓ |
| STOP_MARKET | ✓ | ✓ | ✓ |
| STOP_LIMIT | ✓ | ✓ | ✓ |
| MARKET_IF_TOUCHED | ✓ | ✓ | ✓ |
| LIMIT_IF_TOUCHED | ✓ | ✓ | ✓ |
| TRAILING_STOP_MARKET | - | ✓ | ✓ |

#### Time in Force

- **GTC**: All products
- **GTD**: Not supported
- **FOK**: All products
- **IOC**: All products

#### Execution Instructions

- **post_only**: All products (LIMIT only)
- **reduce_only**: Linear and Inverse only

### Bybit-Specific Features

#### SPOT Margin Trading

Enable margin borrowing per order:
```python
order = strategy.order_factory.market(
    instrument_id="BTCUSDT-SPOT.BYBIT",
    order_side=OrderSide.BUY,
    quantity=qty,
    params={"is_leverage": True}  # Enable margin for this order
)
```

⚠️ **Important**: Without `is_leverage=True`, SPOT orders won't borrow even if auto-borrow is enabled on account.

#### Unified Trading Accounts (UTA)

- Standard account type for most Bybit users
- Allows trading SPOT + derivatives in one account
- SPOT margin requires explicit `is_leverage=True` per order

### Configuration

```python
config = TradingNodeConfig(
    data_clients={
        BYBIT: {
            "api_key": "YOUR_KEY",
            "api_secret": "YOUR_SECRET",
            "product_types": ["spot", "linear"],  # Specify product types
            "base_url_http": None,
            "testnet": False,
        },
    },
    exec_clients={
        BYBIT: {
            "api_key": "YOUR_KEY",
            "api_secret": "YOUR_SECRET",
            "product_types": ["linear"],
            "use_gtd": False,              # GTD not supported
            "use_ws_trade_api": False,     # Use WebSocket for orders
            "use_http_batch_api": False,   # Use batch API
            "futures_leverages": {"BTCUSDT-LINEAR.BYBIT": 10},
            "position_mode": {"linear": "one_way"},  # one_way or hedge
            "margin_mode": "cross",        # cross or isolated
        },
    },
)
```

### Rate Limiting

| Endpoint | Limit (req/sec) |
|----------|-----------------|
| Global | 120 (600 req / 5s) |
| Kline | 20 |
| Order create | 10 |
| Order cancel | 10 |
| Batch create | 5 |
| Batch cancel | 5 |
| Cancel all | 2 |

⚠️ Exceeding limits → Error code 10016 and potential IP block

## Interactive Brokers Integration

### Overview

- Traditional broker with global market access
- Stocks, futures, options, FX, bonds
- TWS (Trader Workstation) or IB Gateway required
- Docker support for IB Gateway

### Configuration

```python
from nautilus_trader.adapters.interactive_brokers import INTERACTIVE_BROKERS

config = TradingNodeConfig(
    data_clients={
        INTERACTIVE_BROKERS: {
            "ibg_host": "127.0.0.1",
            "ibg_port": 4002,           # Paper: 4002, Live: 4001
            "ibg_client_id": 1,
            "use_regular_trading_hours": False,
        },
    },
    exec_clients={
        INTERACTIVE_BROKERS: {
            "ibg_host": "127.0.0.1",
            "ibg_port": 4002,
            "ibg_client_id": 1,
            "account_id": "DU123456",   # Your IB account ID
        },
    },
)
```

### Docker Setup

IB Gateway can run in Docker container for headless operation.

## Data-Only Integrations

### Databento

High-quality market data for US equities, futures, options:
- Historical and real-time data
- Multiple data schemas (MBO, MBP, trades, OHLCV)
- Normalized across venues

```python
from nautilus_trader.adapters.databento import DATABENTO

config = TradingNodeConfig(
    data_clients={
        DATABENTO: {
            "api_key": "YOUR_KEY",
            "http_gateway": None,  # Optional gateway URL
        },
    },
)
```

### Tardis

Historical cryptocurrency market data:
- Tick-by-tick historical data
- Multiple exchanges
- Order book reconstructions

## Instrument Providers

### Standalone Usage (Research/Backtesting)

```python
import asyncio
from nautilus_trader.adapters.binance import get_cached_binance_http_client
from nautilus_trader.adapters.binance.futures.providers import BinanceFuturesInstrumentProvider
from nautilus_trader.common.component import LiveClock

clock = LiveClock()
client = get_cached_binance_http_client(
    loop=asyncio.get_event_loop(),
    clock=clock,
    account_type=BinanceAccountType.USDT_FUTURES,
    key=api_key,
    secret=api_secret,
)
await client.connect()

provider = BinanceFuturesInstrumentProvider(
    client=client,
    account_type=BinanceAccountType.USDT_FUTURES,
)

await provider.load_all_async()
instruments = provider.list_all()
```

### Live Trading

Configure instrument loading behavior:

```python
# Option 1: Load all instruments on start
InstrumentProviderConfig(load_all=True)

# Option 2: Load specific instruments only
InstrumentProviderConfig(
    load_ids=["BTCUSDT-PERP.BINANCE", "ETHUSDT-PERP.BINANCE"]
)
```

## Data Clients

### Custom Data Requests

Actors/Strategies can request custom data from `DataClient`:

```python
# In strategy
def on_start(self) -> None:
    # Request instrument
    self.request_instrument(instrument_id)
    
    # Custom data request
    request = DataRequest(
        data_type=MyCustomDataType,
        metadata={"source": "provider"},
        callback=self._handle_data_response,
    )
    self._send_data_req(request)
```

### Data Client Implementation

Data clients implement handlers for requests:
```python
# In DataClient
async def _request_instrument(self, request: RequestInstrument) -> None:
    instrument = self._instrument_provider.find(request.instrument_id)
    if instrument:
        self._handle_instrument(instrument, request.id, request.params)
```

## Best Practices

### Configuration

1. **Use Environment Variables**: Never hardcode API keys
2. **Test with Testnet**: All major exchanges provide testnets
3. **Configure Rate Limits**: Respect exchange limits
4. **Set Appropriate Timeouts**: Network reliability varies

### API Keys

5. **Separate Keys**: Different keys for data vs execution
6. **IP Whitelisting**: Enable when available
7. **Minimal Permissions**: Only grant necessary permissions
8. **Key Rotation**: Regularly rotate API keys

### Order Management

9. **Match OMS Type**: Configure venue OMS correctly (NETTING vs HEDGING)
10. **Understand Symbology**: Use correct suffixes for instrument types
11. **Venue-Specific Features**: Leverage exchange-specific order types
12. **Test Exhaustively**: Test all order types before live trading

### Data

13. **Subscribe Efficiently**: Only subscribe to needed data
14. **Understand Timestamps**: Use ts_event for strategy logic
15. **Handle Reconnections**: Design for WebSocket reconnections
16. **Rate Limit Requests**: Respect data request limits

### Integration-Specific

17. **Read Exchange Docs**: Each exchange has unique features
18. **Understand Fee Structure**: Fee currency varies by exchange/product
19. **Margin Requirements**: Understand margin calculation methods
20. **Position Modes**: Configure hedging vs netting correctly

## Common Issues

### Authentication Errors

- Verify API key and secret
- Check IP whitelist
- Ensure correct account type configured
- Verify key permissions

### Order Rejections

- Check margin/balance requirements
- Verify order type supported
- Ensure TIF compatible with order type
- Check minimum/maximum order sizes

### Data Issues

- Verify subscription parameters
- Check WebSocket connection status
- Ensure instrument ID format correct
- Verify market is open/trading

### Rate Limiting

- Monitor rate limit headers
- Implement backoff strategies
- Batch operations when possible
- Cache frequently accessed data

## Testing

### Testnets Available

- **Binance**: Spot and Futures testnets
- **Bybit**: Unified testnet
- **BitMEX**: Testnet available
- **dYdX**: Testnet available

### Paper Trading

Most integrations support paper trading:
- Use testnet or demo account
- Configure with paper trading mode
- Test full order lifecycle
- Verify P&L calculations

## Extras Installation

Install adapter-specific dependencies:

```bash
# Interactive Brokers
pip install -U "nautilus_trader[docker,ib]"

# Betfair
pip install -U "nautilus_trader[betfair]"

# dYdX
pip install -U "nautilus_trader[dydx]"

# Polymarket
pip install -U "nautilus_trader[polymarket]"
```
