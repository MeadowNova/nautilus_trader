# Nautilus Trader - Orders & Execution

**Last Updated:** October 2025

## Order Types

### Basic Order Types

1. **MARKET**: Execute immediately at best available price
   - No price specified
   - Guaranteed fill (sufficient liquidity assumed)
   - May experience slippage

2. **LIMIT**: Execute at specified price or better
   - Must specify price
   - May not fill if price not reached
   - Can specify `post_only=True` (maker-only)

3. **STOP_MARKET**: Market order triggered at stop price
   - Trigger price specified
   - Becomes market order when triggered
   - Used for stop-losses and breakout entries

4. **STOP_LIMIT**: Limit order triggered at stop price
   - Both trigger and limit price specified
   - Becomes limit order when triggered
   - More control but less fill guarantee

5. **MARKET_TO_LIMIT**: Market order that becomes limit if not immediately filled
   - Initial market order
   - Unfilled quantity becomes limit at last traded price
   - Reduces slippage vs pure market

6. **MARKET_IF_TOUCHED (MIT)**: Limit order that becomes market when price touched
   - Trigger price specified
   - Becomes market order when triggered
   - Opposite direction to stop orders

7. **LIMIT_IF_TOUCHED (LIT)**: Limit order triggered when price touched
   - Trigger and limit price specified
   - Becomes limit order when triggered

8. **TRAILING_STOP_MARKET**: Stop order that trails price
   - Trailing offset or percentage
   - Adjusts trigger as price moves favorably
   - Locks in profits while allowing upside

9. **TRAILING_STOP_LIMIT**: Trailing stop that becomes limit
   - Trailing offset/percentage + limit offset
   - More control but less fill guarantee

## Execution Instructions

### Time In Force (TIF)

- **GTC (Good Till Cancel)**: Remains active until filled or canceled
- **GTD (Good Till Date)**: Expires at specified date/time
- **FOK (Fill Or Kill)**: Immediate complete fill or cancel
- **IOC (Immediate Or Cancel)**: Immediate partial/complete fill, cancel remainder
- **DAY**: Active until end of trading day
- **AT_THE_OPEN**: Execute at market open
- **AT_THE_CLOSE**: Execute at market close

### Special Instructions

- **post_only**: Only add liquidity (maker), reject if would take liquidity
- **reduce_only**: Only reduce existing position (no new positions)
- **display_qty**: Iceberg order, show only partial quantity
- **hidden**: Don't display order in public book (venue dependent)

### Trigger Types

Determines what price triggers stop/trailing orders:

- **DEFAULT**: Venue's default trigger mechanism
- **LAST_PRICE**: Last trade price
- **BID_ASK**: Two-price trigger (bid for sell, ask for buy)
- **MARK_PRICE**: Mark price (typically for derivatives)
- **INDEX_PRICE**: Index price (typically for derivatives)

## Contingent Orders

### Order-Triggered-Order (OTO)

Secondary order submitted when primary fills:
```python
primary = self.order_factory.market(...)
secondary = self.order_factory.limit(...)  # Take profit

self.submit_order(primary, contingency_type=ContingencyType.OTO)
self.submit_order(secondary, parent_order_id=primary.client_order_id)
```

### One-Cancels-Other (OCO)

When one order fills, others in group are canceled:
```python
stop_loss = self.order_factory.stop_market(...)
take_profit = self.order_factory.limit(...)

self.submit_order(stop_loss, contingency_type=ContingencyType.OCO)
self.submit_order(take_profit, linked_order_ids=[stop_loss.client_order_id])
```

### One-Updates-Other (OUO)

When one order fills, update linked orders:
```python
# Used for adjusting stops/targets as position changes
```

### Bracket Orders

Combined entry + stop loss + take profit:
```python
entry = self.order_factory.market(...)
stop_loss = self.order_factory.stop_market(...)
take_profit = self.order_factory.limit(...)

# Entry triggers OTO for stop and take profit
# Stop and take profit are OCO with each other
self.submit_order(entry, contingency_type=ContingencyType.OTO)
self.submit_order(stop_loss, parent_order_id=entry.client_order_id, contingency_type=ContingencyType.OCO)
self.submit_order(take_profit, parent_order_id=entry.client_order_id, linked_order_ids=[stop_loss.client_order_id])
```

## Emulated Orders

### Purpose
- Execute orders locally within Nautilus
- Useful when venue doesn't support order type
- Reduces exchange load
- Enables advanced order types

### Configuration

```python
# In order creation
order = self.order_factory.stop_market(
    instrument_id=self.instrument_id,
    order_side=OrderSide.SELL,
    quantity=qty,
    trigger_price=stop_price,
    emulation_trigger=TriggerType.LAST_PRICE,  # Enable emulation
)
```

### Emulated Order Lifecycle

1. **INITIALIZED**: Order created locally
2. **EMULATED**: Held locally, monitoring for trigger
3. **RELEASED**: Trigger condition met, submitted to venue
4. **Venue State**: Normal venue order lifecycle

⚠️ **Important**: Emulated orders don't exist on venue until released

### Supported Emulated Types

- STOP_MARKET
- STOP_LIMIT  
- MARKET_IF_TOUCHED
- LIMIT_IF_TOUCHED
- TRAILING_STOP_MARKET
- TRAILING_STOP_LIMIT

## Order Management System (OMS)

### OMS Types

1. **NETTING**: Single position per instrument
   - Opposite orders net against each other
   - Most common for crypto/FX
   
2. **HEDGING**: Multiple positions per instrument
   - Can have simultaneous long and short
   - Common for futures/equities

Configure in venue settings:
```python
BacktestVenueConfig(
    name="BINANCE",
    oms_type=OmsType.NETTING,
    ...
)
```

## Execution Flow

### Command Flow

1. **Strategy** → Generates trading command (`SubmitOrder`, `CancelOrder`, `ModifyOrder`)
2. **MessageBus** → Publishes command
3. **RiskEngine** → Pre-trade risk checks
   - Account balance
   - Position limits
   - Order rate limits
   - Custom risk rules
4. **ExecutionEngine** → Routes to appropriate client
5. **ExecutionClient** → Submits to venue
6. **Venue** → Processes order

### Event Flow Back

1. **Venue** → Order state change (fill, cancel, reject, etc.)
2. **ExecutionClient** → Normalizes to Nautilus event
3. **ExecutionEngine** → Processes event
4. **Cache** → Updates order/position state
5. **MessageBus** → Publishes event
6. **Strategy** → Receives event in handler (`on_order_filled`, etc.)
7. **Portfolio** → Updates positions and balances

## Risk Engine

### Pre-Trade Checks

- **Max Order Rate**: Prevent order spam
- **Max Notional Per Order**: Limit order size
- **Free Balance Check**: Ensure sufficient capital
- **Position Limit**: Max contracts/shares per instrument
- **Custom Risk Rules**: User-defined validation

### Configuration

```python
RiskEngineConfig(
    bypass=False,  # Set True to disable (USE WITH CAUTION)
    max_order_rate="100/00:00:01",  # 100 orders per second
    max_notional_per_order={instrument_id: 1000000},
)
```

## Execution Algorithms

### Purpose
- Break large orders into smaller pieces
- Reduce market impact
- Achieve VWAP/TWAP execution
- Smart routing

### TWAP Example

```python
order = self.order_factory.market(
    instrument_id=self.instrument_id,
    order_side=OrderSide.BUY,
    quantity=Quantity.from_int(1000),
    exec_algorithm_id=ExecAlgorithmId("TWAP"),
    exec_algorithm_params={
        "horizon_secs": 600,    # 10 minute execution window
        "interval_secs": 10,    # Child order every 10 seconds
    },
)
self.submit_order(order)
```

### Order Spawning

Execution algorithms spawn child orders:
- Parent order (1000 qty) → Multiple child orders (100 qty each)
- Tracks fills across children
- Reports parent fill when all children complete

## Order States

### State Machine

- **INITIALIZED**: Created locally
- **DENIED**: Denied by risk engine
- **EMULATED**: Held locally for emulation
- **RELEASED**: Released from emulation, sent to venue
- **SUBMITTED**: Submitted to venue, awaiting acknowledgment
- **ACCEPTED**: Acknowledged by venue
- **REJECTED**: Rejected by venue
- **CANCELED**: Canceled
- **EXPIRED**: Expired (GTD orders)
- **TRIGGERED**: Stop/trailing order triggered
- **PENDING_UPDATE**: Modify request submitted
- **PENDING_CANCEL**: Cancel request submitted
- **PARTIALLY_FILLED**: Partial fill received
- **FILLED**: Completely filled

## Position States

- **OPEN**: Position has non-zero quantity
- **CLOSED**: Position reduced to zero quantity

## Best Practices

### Order Management

1. **Use OrderFactory**: Reduces boilerplate, handles IDs
2. **Match OMS Type**: Configure venue OMS to match reality
3. **Emulation for Advanced Types**: Use when venue lacks support
4. **Contingent Orders**: Bracket orders for risk management
5. **Don't Hold Order References**: Use cache (orders transform during emulation)

### Risk Management

6. **Enable Risk Engine**: Keep `bypass=False` unless testing
7. **Set Appropriate Limits**: Max notional, position limits
8. **Monitor Order Events**: React to rejections appropriately
9. **Handle Partial Fills**: Don't assume complete fills

### Execution

10. **Choose Appropriate TIF**: Match order intent
11. **Use post_only for Makers**: Avoid taker fees when possible
12. **Reduce-Only for Exits**: Prevent accidental position reversal
13. **Exec Algorithms for Large Orders**: Reduce market impact
14. **Consider Trigger Types**: LAST vs BID_ASK for stops

### Event Handling

15. **Handle All States**: Rejected, canceled, expired, etc.
16. **Use Specific Handlers**: `on_order_filled` vs `on_order_event`
17. **Check Order State**: Before modifying/canceling
18. **Position Events**: Track `on_position_opened/closed/changed`

## Common Patterns

### Entry with Stop and Target
```python
def enter_long(self, entry_price: Price, stop: Price, target: Price, qty: Quantity):
    entry = self.order_factory.limit(
        instrument_id=self.instrument_id,
        order_side=OrderSide.BUY,
        quantity=qty,
        price=entry_price,
    )
    
    stop_loss = self.order_factory.stop_market(
        instrument_id=self.instrument_id,
        order_side=OrderSide.SELL,
        quantity=qty,
        trigger_price=stop,
    )
    
    take_profit = self.order_factory.limit(
        instrument_id=self.instrument_id,
        order_side=OrderSide.SELL,
        quantity=qty,
        price=target,
    )
    
    self.submit_order(entry, contingency_type=ContingencyType.OTO)
    self.submit_order(stop_loss, parent_order_id=entry.client_order_id, contingency_type=ContingencyType.OCO)
    self.submit_order(take_profit, parent_order_id=entry.client_order_id, linked_order_ids=[stop_loss.client_order_id])
```

### Trailing Stop for Profit Protection
```python
def set_trailing_stop(self, position: Position, trail_pct: float):
    trailing_offset = position.avg_px_open * trail_pct
    
    stop = self.order_factory.trailing_stop_market(
        instrument_id=position.instrument_id,
        order_side=OrderSide.SELL if position.is_long else OrderSide.BUY,
        quantity=position.quantity,
        trailing_offset=self.instrument.make_price(trailing_offset),
        trigger_type=TriggerType.LAST_PRICE,
    )
    
    self.submit_order(stop)
```
