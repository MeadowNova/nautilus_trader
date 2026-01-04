# Moomoo Adapter Fixes - December 9, 2025

## Overview
Fixed multiple blocking issues preventing the Moomoo trading system from running with NautilusTrader v1.221.0.

## Issues Fixed

### 1. Strategy Bar Subscriptions (pairs_trading.py, momentum_breakout.py)
**Problem:** Strategies were calling `subscribe_bars(instrument_id)` but the method expects a `BarType` object.

**Error:** `Argument 'bar_type' has incorrect type (expected BarType, got InstrumentId)`

**Fix:**
```python
# Before (WRONG)
self.subscribe_bars(self.instrument_a)

# After (CORRECT)
from nautilus_trader.model.data import Bar, BarType, QuoteTick

bar_type_a = BarType.from_str(f"{self.instrument_a}-1-MINUTE-LAST-EXTERNAL")
self.subscribe_bars(bar_type_a)
```

### 2. Data Client Method Signatures (data.py)
**Problem:** Moomoo data client had wrong method signatures. All other adapters receive command objects, but Moomoo was using raw InstrumentId.

**Error:** `'SubscribeQuoteTicks' object has no attribute 'symbol'`

**Fix:**
```python
# Before (WRONG)
async def _subscribe_quote_ticks(self, instrument_id: InstrumentId) -> None:

# After (CORRECT)
from nautilus_trader.data.messages import SubscribeBars, SubscribeQuoteTicks, SubscribeTradeTicks

async def _subscribe_quote_ticks(self, command: SubscribeQuoteTicks) -> None:
    instrument_id = command.instrument_id
    # ... rest of method

async def _subscribe_trade_ticks(self, command: SubscribeTradeTicks) -> None:
    instrument_id = command.instrument_id
    # ... rest of method

async def _subscribe_bars(self, command: SubscribeBars) -> None:
    bar_type = command.bar_type
    instrument_id = bar_type.instrument_id
    # ... rest of method
```

### 3. Missing `_subscribe_bars` Method (data.py)
**Problem:** Data client was missing the `_subscribe_bars` coroutine.

**Error:** `NotImplementedError: implement the '_subscribe_bars' coroutine`

**Fix:** Added new method that registers bar subscriptions and adds underlying instrument to quote subscriptions for price tracking.

### 4. Reconciliation Methods (execution.py)
**Problem:** Missing execution reconciliation methods caused startup failures.

**Error:** `NotImplementedError: method 'generate_order_status_reports' must be implemented`

**Fix:** Added three async methods:
- `generate_order_status_reports()` - Queries `order_list_query()`
- `generate_fill_reports()` - Queries `deal_list_query()`
- `generate_position_status_reports()` - Queries `position_list_query()`

### 5. Position Sizing
**Change:** Reduced position sizes from 8-10% to 2% for safer paper trading.

## Files Modified
- `/nautilus_trader/adapters/moomoo/data.py` - Method signatures, imports, _subscribe_bars
- `/nautilus_trader/adapters/moomoo/execution.py` - Reconciliation methods
- `/ajk_strategies/rl_strategies/pairs_trading.py` - BarType usage, position sizing
- `/ajk_strategies/rl_strategies/momentum_breakout.py` - BarType usage, position sizing

## Moomoo Account Permissions (Not Code Issues)
After code fixes, these errors are account configuration issues:
- "No right to subscribe the quote for US.XLE" - Enable US market data in Moomoo app
- "No available real accounts with US market authority" - Check security_firm/filter_trdmarket settings

## Key Patterns for NautilusTrader Adapters
1. Subscribe methods receive command objects, not raw identifiers
2. Use `command.instrument_id` for quote/trade subscriptions
3. Use `command.bar_type.instrument_id` for bar subscriptions
4. BarType format: `{instrument_id}-{step}-{aggregation}-{price_type}-EXTERNAL`
5. Execution clients must implement all three reconciliation methods
