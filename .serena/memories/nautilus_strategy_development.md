# Nautilus Trader - Strategy Development Guide

**Last Updated:** October 2025

## Strategy Basics

### Key Capabilities
- All `Actor` capabilities (data subscriptions, cache access, timers)
- Order management (submitting, modifying, canceling orders)
- Portfolio access

### Relationship with Actors
`Strategy` class inherits from `Actor`, gaining all actor functionality plus order management.

### Same Code, All Environments
Once defined, the same strategy source code works for:
- Backtesting
- Sandbox (paper trading)
- Live trading

## Strategy Implementation

### Minimal Constructor
```python
from nautilus_trader.trading.strategy import Strategy

class MyStrategy(Strategy):
    def __init__(self) -> None:
        super().__init__()  # MUST call superclass
```

⚠️ **Warning**: Don't call `clock`, `logger`, etc. in `__init__` (system not yet initialized)

## Handler Methods

### Stateful Actions (Lifecycle)
```python
def on_start(self) -> None:        # Initialize strategy (fetch instruments, subscribe data)
def on_stop(self) -> None:         # Cleanup (cancel orders, close positions, unsubscribe)
def on_resume(self) -> None:       # Resume after pause
def on_reset(self) -> None:        # Reset state
def on_dispose(self) -> None:      # Final cleanup
def on_degrade(self) -> None:      # Handle degraded state
def on_fault(self) -> None:        # Handle fault state
def on_save(self) -> dict[str, bytes]:  # Save custom state
def on_load(self, state: dict[str, bytes]) -> None:  # Load custom state
```

### Data Handling
```python
def on_order_book_deltas(self, deltas: OrderBookDeltas) -> None:
def on_order_book(self, order_book: OrderBook) -> None:
def on_quote_tick(self, tick: QuoteTick) -> None:
def on_trade_tick(self, tick: TradeTick) -> None:
def on_bar(self, bar: Bar) -> None:
def on_instrument(self, instrument: Instrument) -> None:
def on_instrument_status(self, data: InstrumentStatus) -> None:
def on_instrument_close(self, data: InstrumentClose) -> None:
def on_historical_data(self, data: Data) -> None:
def on_data(self, data: Data) -> None:      # Custom data
def on_signal(self, signal: Data) -> None:   # Custom signals
```

### Order Management Events
```python
def on_order_initialized(self, event: OrderInitialized) -> None:
def on_order_denied(self, event: OrderDenied) -> None:
def on_order_emulated(self, event: OrderEmulated) -> None:
def on_order_released(self, event: OrderReleased) -> None:
def on_order_submitted(self, event: OrderSubmitted) -> None:
def on_order_rejected(self, event: OrderRejected) -> None:
def on_order_accepted(self, event: OrderAccepted) -> None:
def on_order_canceled(self, event: OrderCanceled) -> None:
def on_order_expired(self, event: OrderExpired) -> None:
def on_order_triggered(self, event: OrderTriggered) -> None:
def on_order_pending_update(self, event: OrderPendingUpdate) -> None:
def on_order_pending_cancel(self, event: OrderPendingCancel) -> None:
def on_order_modify_rejected(self, event: OrderModifyRejected) -> None:
def on_order_cancel_rejected(self, event: OrderCancelRejected) -> None:
def on_order_updated(self, event: OrderUpdated) -> None:
def on_order_filled(self, event: OrderFilled) -> None:
def on_order_event(self, event: OrderEvent) -> None:  # All order events
```

### Position Management Events
```python
def on_position_opened(self, event: PositionOpened) -> None:
def on_position_changed(self, event: PositionChanged) -> None:
def on_position_closed(self, event: PositionClosed) -> None:
def on_position_event(self, event: PositionEvent) -> None:  # All position events
```

### Generic Event Handler
```python
def on_event(self, event: Event) -> None:  # Receives ALL events eventually
```

## Handler Example

```python
def on_start(self) -> None:
    # Get instrument
    self.instrument = self.cache.instrument(self.instrument_id)
    if self.instrument is None:
        self.log.error(f"Could not find instrument for {self.instrument_id}")
        self.stop()
        return
    
    # Register indicators for updating
    self.register_indicator_for_bars(self.bar_type, self.fast_ema)
    self.register_indicator_for_bars(self.bar_type, self.slow_ema)
    
    # Get historical data
    self.request_bars(self.bar_type)
    
    # Subscribe to live data
    self.subscribe_bars(self.bar_type)
    self.subscribe_quote_ticks(self.instrument_id)
```

## Clock and Timers

### Current Timestamps
```python
# UTC timestamp as pd.Timestamp
now: pd.Timestamp = self.clock.utc_now()

# UTC timestamp as UNIX nanoseconds
unix_nanos: int = self.clock.timestamp_ns()
```

### Time Alerts (One-time)
```python
# Fire TimeEvent one minute from now
self.clock.set_time_alert(
    name="MyTimeAlert1",
    alert_time=self.clock.utc_now() + pd.Timedelta(minutes=1),
)
```

### Timers (Recurring)
```python
# Fire TimeEvent every minute
self.clock.set_timer(
    name="MyTimer1",
    interval=pd.Timedelta(minutes=1),
)
```

## Cache Access

### Fetching Data
```python
last_quote = self.cache.quote_tick(self.instrument_id)
last_trade = self.cache.trade_tick(self.instrument_id)
last_bar = self.cache.bar(bar_type)
```

### Fetching Execution Objects
```python
order = self.cache.order(client_order_id)
position = self.cache.position(position_id)
```

## Portfolio Access

### Account and Positional Information
```python
account = self.portfolio.account(venue)
balances_locked = self.portfolio.balances_locked(venue)
margins_init = self.portfolio.margins_init(venue)
margins_maint = self.portfolio.margins_maint(venue)
unrealized_pnls = self.portfolio.unrealized_pnls(venue)
realized_pnls = self.portfolio.realized_pnls(venue)
net_exposures = self.portfolio.net_exposures(venue)

unrealized_pnl = self.portfolio.unrealized_pnl(instrument_id)
realized_pnl = self.portfolio.realized_pnl(instrument_id)
net_exposure = self.portfolio.net_exposure(instrument_id)
net_position = self.portfolio.net_position(instrument_id)

is_net_long = self.portfolio.is_net_long(instrument_id)
is_net_short = self.portfolio.is_net_short(instrument_id)
is_flat = self.portfolio.is_flat(instrument_id)
is_completely_flat = self.portfolio.is_completely_flat()
```

## Trading Commands

### Submitting Orders

Use built-in `OrderFactory` for convenience:

```python
# Market Order
order: MarketOrder = self.order_factory.market(
    instrument_id=self.instrument_id,
    order_side=OrderSide.BUY,
    quantity=self.instrument.make_qty(self.trade_size),
)
self.submit_order(order)

# Limit Order with Emulation
order: LimitOrder = self.order_factory.limit(
    instrument_id=self.instrument_id,
    order_side=OrderSide.BUY,
    quantity=self.instrument.make_qty(self.trade_size),
    price=self.instrument.make_price(5000.00),
    emulation_trigger=TriggerType.LAST_PRICE,  # Emulate locally
)
self.submit_order(order)

# With Execution Algorithm
order: MarketOrder = self.order_factory.market(
    instrument_id=self.instrument_id,
    order_side=OrderSide.BUY,
    quantity=self.instrument.make_qty(self.trade_size),
    time_in_force=TimeInForce.FOK,
    exec_algorithm_id=ExecAlgorithmId("TWAP"),
    exec_algorithm_params={"horizon_secs": 20, "interval_secs": 2.5},
)
self.submit_order(order)
```

### Canceling Orders
```python
# Single order
self.cancel_order(order)

# Batch of orders
self.cancel_orders([order1, order2, order3])

# All orders
self.cancel_all_orders()
```

### Modifying Orders
```python
new_quantity: Quantity = Quantity.from_int(5)
self.modify_order(order, new_quantity)
# Can also modify price and trigger price
```

## Strategy Configuration

### Configuration Class
```python
from nautilus_trader.config import StrategyConfig
from nautilus_trader.model import InstrumentId, BarType

class MyStrategyConfig(StrategyConfig):
    instrument_id: InstrumentId
    bar_type: BarType
    fast_ema_period: int = 10
    slow_ema_period: int = 20
    trade_size: Decimal
    order_id_tag: str

class MyStrategy(Strategy):
    def __init__(self, config: MyStrategyConfig) -> None:
        super().__init__(config)
        # Access via self.config.instrument_id, self.config.trade_size, etc.
```

### Benefits of Configuration
- Serialize strategies over the wire
- Enable distributed backtesting
- Remote live trading servers
- Clear separation: config data vs strategy state

### Managed GTD Expiry
```python
# Strategy manages GTD expiry locally if venue doesn't support
StrategyConfig(manage_gtd_expiry=True)
# Set use_gtd=False in execution client config to avoid conflicts
```

## Multiple Strategies

When running multiple instances with different configs:
- **Must define unique `order_id_tag` for each strategy**
- Strategy ID format: `{StrategyClassName}-{order_id_tag}`
- Example: `MyStrategy-001`, `MyStrategy-002`

## Best Practices

1. **Use `on_start`**: Initialize strategy (fetch instruments, subscribe data)
2. **Use `on_stop`**: Cleanup (cancel orders, close positions)
3. **Access Config via `self.config`**: Clear separation from state variables
4. **Register Indicators Before Requesting Data**: Ensures proper updates
5. **Check Instrument Availability**: Handle cases where instrument not found
6. **Use OrderFactory**: Reduces boilerplate, handles IDs automatically
7. **Leverage Cache**: Fast access to orders, positions, data
8. **Don't Hold Order References**: Use Cache instead (orders transform when released from emulation)
