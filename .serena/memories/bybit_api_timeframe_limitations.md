# Bybit API Timeframe Limitations - Critical Reference

## Quick Summary

**Bybit does NOT support second-level or sub-minute bars through their API.**

### Supported Timeframes Only
```python
# From: nautilus_trader/adapters/bybit/common/constants.py (line 91-92)
BYBIT_MINUTE_INTERVALS = (1, 3, 5, 15, 30, 60, 120, 240, 360, 720)
BYBIT_HOUR_INTERVALS = (1, 2, 4, 6, 12)
```

Also supported: DAY (1 only), WEEK (1 only)

### NOT Supported
- ❌ Any second-level bars (1s, 5s, 15s, 30s, etc.)
- ❌ Any sub-minute bars
- ❌ Millisecond bars
- ❌ Tick bars (via bar aggregation)

## Error When Attempting Second-Level Bars

### What Happens
```python
# Configuration:
bar_type = "BTCUSDT-LINEAR.BYBIT-5-SECOND-LAST-EXTERNAL"

# Error:
AttributeError: 'nautilus_trader.model.data.BarType' object has no attribute 'aggregation'

# Traceback location:
File: nautilus_trader/adapters/bybit/common/parsing.py
Function: get_interval_from_bar_type()
Line: 115
```

### Root Cause
The Bybit adapter's parsing function expects only supported timeframes. When it receives a SECOND-aggregated bar type, it falls through to the default case which tries to access `bar_type.aggregation` in an error message, but the attribute path is incorrect.

## Workarounds for Faster Data Collection

### 1. Use Fastest Bybit Bar (1-minute) ✅
```python
bar_type = "BTCUSDT-LINEAR.BYBIT-1-MINUTE-LAST-EXTERNAL"
# This is the FASTEST Bybit supports via bar subscription
```

### 2. Subscribe to Tick Data ⚡
```python
# In strategy on_start():
self.subscribe_trade_ticks(self.instrument_id)  # Every trade
self.subscribe_quote_ticks(self.instrument_id)  # Every quote update

# Then handle in:
def on_trade_tick(self, tick: TradeTick):
    # Process every trade (10-1000x per second)
    # Build your own custom bars internally
    pass

def on_quote_tick(self, tick: QuoteTick):
    # Process every bid/ask update
    pass
```
**Note**: Tick data is available on Bybit, just not pre-aggregated bars under 1 minute.

### 3. Switch to Binance for 1-Second Bars 🔄
```python
# Binance supports native 1-second bars!
bar_type = "BTCUSDT.BINANCE-1-SECOND-LAST-EXTERNAL"

# Binance intervals:
# 1s, 1m, 3m, 5m, 15m, 30m, 1h, 2h, 4h, 6h, 8h, 12h, 1d, 3d, 1w, 1M
```
**Data increase**: 60x more data points than Bybit (3,600/hour vs 60/hour)

## Exchange Comparison: Sub-Minute Bar Support

| Exchange | Minimum Bar | 1-Second Bars? | Tick Data? |
|----------|-------------|----------------|------------|
| **Bybit** | 1 minute | ❌ No | ✅ Yes (via WebSocket) |
| **Binance** | 1 second | ✅ Yes | ✅ Yes |
| **Coinbase** | 1 minute | ❌ No | ✅ Yes |
| **Kraken** | 1 minute | ❌ No | ✅ Yes |
| **OKX** | 1 minute | ❌ No | ✅ Yes |

**Industry Standard**: Most exchanges limit aggregated bars to 1-minute minimum. High-frequency traders use tick streams instead.

## Bybit Documentation References

### Kline/Candlestick Intervals
From Bybit API docs (https://bybit-exchange.github.io/docs/v5/market/kline):

**Linear & Inverse:**
- 1,3,5,15,30,60,120,240,360,720,D,M,W

**Spot:**
- 1,3,5,15,30,60,120,240,360,720,D,M,W

**Where:**
- Numbers = minutes
- D = day
- W = week  
- M = month

**No "s" option for seconds!**

## Alternative: Build Custom Sub-Minute Bars from Ticks

### Example Implementation
```python
from collections import deque
from datetime import datetime, timedelta

class CustomBarBuilder:
    def __init__(self, bar_duration_seconds=5):
        self.bar_duration = timedelta(seconds=bar_duration_seconds)
        self.current_bar_start = None
        self.current_bar_data = {
            'open': None,
            'high': None,
            'low': None,
            'close': None,
            'volume': 0
        }
    
    def on_trade_tick(self, tick: TradeTick):
        now = tick.ts_init
        
        # Initialize or check if new bar period
        if self.current_bar_start is None:
            self.current_bar_start = now
            self.current_bar_data['open'] = tick.price
            self.current_bar_data['high'] = tick.price
            self.current_bar_data['low'] = tick.price
        
        # Check if bar period ended
        if now >= self.current_bar_start + self.bar_duration:
            # Emit completed bar
            self._emit_bar()
            # Start new bar
            self.current_bar_start = now
            self.current_bar_data['open'] = tick.price
            self.current_bar_data['high'] = tick.price
            self.current_bar_data['low'] = tick.price
        
        # Update current bar
        self.current_bar_data['high'] = max(self.current_bar_data['high'], tick.price)
        self.current_bar_data['low'] = min(self.current_bar_data['low'], tick.price)
        self.current_bar_data['close'] = tick.price
        self.current_bar_data['volume'] += tick.size
    
    def _emit_bar(self):
        # Process your custom bar here
        # Call strategy logic with completed bar
        pass
```

**Complexity**: Medium - requires refactoring strategy to handle tick data

## Configuration Best Practices

### For Maximum Data Collection on Bybit

#### Option A: Fastest Bars Available
```python
bar_type = "BTCUSDT-LINEAR.BYBIT-1-MINUTE-LAST-EXTERNAL"
# 60 bars/hour, 1,440/day, 43,200/month
```

#### Option B: More Aggressive Trading Settings
```python
bar_type = "BTCUSDT-LINEAR.BYBIT-1-MINUTE-LAST-EXTERNAL"
confidence_threshold = 0.65  # Lower = more signals (default: 0.75)
max_bars_in_position = 20    # Shorter holds (vs default: 50)
# Expected: 2x more trades per day
```

#### Option C: Tick Data Processing
```python
# Subscribe to raw ticks
self.subscribe_trade_ticks(instrument_id)
self.subscribe_quote_ticks(instrument_id)

# Build custom bars (any duration!)
custom_bar_builder = CustomBarBuilder(bar_duration_seconds=5)

# Process 10-1000+ updates per second
```

## When to Switch Away from Bybit

### Consider Binance If:
1. Need more than 60 data points per hour
2. Want native 1-second bars (no custom aggregation)
3. Willing to switch testnet environments
4. Want 60x more data for ML training

### Stay on Bybit If:
1. 1-minute bars sufficient for strategy
2. Already have Bybit testnet set up
3. Comfortable with tick data implementation
4. Prefer Bybit's interface/API

## Code Locations for Reference

### Bybit Adapter Constants
```
File: nautilus_trader/adapters/bybit/common/constants.py
Lines: 91-92

BYBIT_MINUTE_INTERVALS: Final[tuple[int, ...]] = (1, 3, 5, 15, 30, 60, 120, 240, 360, 720)
BYBIT_HOUR_INTERVALS: Final[tuple[int, ...]] = (1, 2, 4, 6, 12)
```

### Bybit Bar Parsing
```
File: nautilus_trader/adapters/bybit/common/parsing.py
Function: get_interval_from_bar_type(bar_type: BarType) -> str
Lines: 86-117

Uses match/case on bar_type.spec.aggregation
Only handles: MINUTE, HOUR, DAY, WEEK
Default case raises ValueError for anything else
```

### Bybit Data Client
```
File: nautilus_trader/adapters/bybit/data.py
Function: _subscribe_bars()
Line: ~450

Calls get_interval_from_bar_type() which enforces the interval restrictions
```

## Testing Timeframe Support

### Quick Test Script
```python
from nautilus_trader.adapters.bybit.common.parsing import get_interval_from_bar_type
from nautilus_trader.model.data import BarType

# Test if timeframe supported:
try:
    bar_type_str = "BTCUSDT-LINEAR.BYBIT-5-SECOND-LAST-EXTERNAL"
    bar_type = BarType.from_str(bar_type_str)
    interval = get_interval_from_bar_type(bar_type)
    print(f"✅ Supported: {bar_type_str} -> {interval}")
except (ValueError, AttributeError) as e:
    print(f"❌ Not supported: {bar_type_str}")
    print(f"   Error: {e}")
```

## Summary

**Bottom Line**: Bybit's API design forces a choice:
1. Use 1-minute bars (pre-aggregated, simple, limited data)
2. Use tick data (raw, complex, unlimited data)
3. Switch to Binance (native 1-second bars)

For the user's goal of "collecting as much data as possible", **Binance is the recommended path** - offers 60x more data points with minimal complexity increase.

## Related Documentation

- `ai-working/paper_trading/BYBIT_LIMITATIONS.md` - Comprehensive guide with all workarounds
- `ai-working/paper_trading/TRADING_FREQUENCY_EXPLAINED.md` - Trading timeframe hierarchy
- `ai-working/paper_trading/ARCHITECTURE_CLARIFICATION.md` - System performance capabilities
