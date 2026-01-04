# Bybit API Limitations & Workarounds

## 🚨 **CRITICAL FINDING**

**Bybit does NOT support second-level bars!**

### **Supported Timeframes:**

```python
# Bybit MINUTE bars (fastest is 1-minute):
BYBIT_MINUTE_INTERVALS = (1, 3, 5, 15, 30, 60, 120, 240, 360, 720)
#                         ↑  Fastest available!

# Bybit HOUR bars:
BYBIT_HOUR_INTERVALS = (1, 2, 4, 6, 12)

# Also supported:
# - DAY (1 only)
# - WEEK (1 only)
```

### **NOT Supported:**
❌ 5-SECOND bars
❌ 1-SECOND bars  
❌ Any sub-minute timeframes
❌ Tick-by-tick bars

**This is a Bybit API limitation, NOT a NautilusTrader limitation!**

---

## 🔧 **WORKAROUND OPTIONS**

### **Option 1: Use 1-Minute Bars with Aggressive Settings** ✅ RECOMMENDED

**Fastest Bybit bars + Lower confidence threshold = More trades**

```python
# Configuration:
bar_type = "BTCUSDT-LINEAR.BYBIT-1-MINUTE-LAST-EXTERNAL"  # Fastest available
confidence_threshold = 0.65  # Lower = more signals (default: 0.75)
max_bars_in_position = 20    # Shorter holds (20min vs 50min)

# Expected results:
├─ Bars: 60/hour (1 per minute)
├─ Trades: 15-40/day (more with lower threshold)
├─ Position time: 10-20 minutes average
└─ Still comfortable for ML strategy
```

**Advantages:**
- ✅ Works with current infrastructure
- ✅ No code changes needed
- ✅ Bybit testnet supported
- ✅ Simple and reliable

**Disadvantages:**
- ⚠️ Still only 60 data points/hour
- ⚠️ Slower than desired

---

### **Option 2: Subscribe to Tick Data** ⚡ ADVANCED

**Use raw tick data instead of bars for maximum frequency**

```python
# In your strategy:
def on_start(self):
    # Subscribe to tick data instead of bars
    self.subscribe_trade_ticks(self.instrument_id)
    self.subscribe_quote_ticks(self.instrument_id)

def on_trade_tick(self, tick: TradeTick):
    # Process every individual trade (10-1000x per second!)
    # Build your own bars internally
    self._aggregate_tick(tick)
    
    if self._should_check_signal():
        # Your ML strategy
        signal = self._generate_signal()

def _aggregate_tick(self, tick):
    # Build custom timeframe bars (e.g., 5-second bars)
    # from incoming tick data
    pass
```

**How Tick Data Works:**

```
Bybit sends you EVERY trade/quote update:
├─ Trade ticks: Every executed trade (10-100x per second)
├─ Quote ticks: Every bid/ask update (10-1000x per second)
└─ You aggregate internally into any timeframe you want

Example flow:
23:00:00.123 - Trade tick: BTC $67,234.50, size 0.5
23:00:00.456 - Quote tick: Bid $67,234, Ask $67,235
23:00:00.789 - Trade tick: BTC $67,235.00, size 1.2
23:00:01.012 - Quote tick: Bid $67,235, Ask $67,236
    ↓
You aggregate these into 5-second bars internally
    ↓
23:00:05.000 - Your custom 5-second bar ready!
```

**Advantages:**
- ✅ Maximum frequency (10-1000x per second)
- ✅ Build ANY custom timeframe (1s, 5s, 10s, etc.)
- ✅ Tick data available on Bybit
- ✅ True high-frequency capability

**Disadvantages:**
- ⚠️ Requires strategy code changes
- ⚠️ More complex to implement
- ⚠️ Higher memory/CPU usage
- ⚠️ Need to handle aggregation logic

**Implementation Complexity:** Medium-High

---

### **Option 3: Switch to Binance** 🔄 DIFFERENT EXCHANGE

**Use an exchange that supports second-level bars**

```python
# Binance supports:
BINANCE_INTERVALS = (
    "1s",   # ← 1-SECOND BARS!
    "1m", "3m", "5m", "15m", "30m",
    "1h", "2h", "4h", "6h", "8h", "12h",
    "1d", "3d", "1w", "1M"
)

# Configuration:
bar_type = "BTCUSDT.BINANCE-1-SECOND-LAST-EXTERNAL"  # 60x faster than Bybit!
```

**Advantages:**
- ✅ Native 1-second bars (no aggregation needed)
- ✅ 3600 data points/hour vs 60
- ✅ Binance has better liquidity
- ✅ Lower fees for high-frequency

**Disadvantages:**
- ⚠️ Need Binance testnet setup
- ⚠️ Different API credentials
- ⚠️ Binance testnet less stable
- ⚠️ May require adapter configuration

**Implementation Complexity:** Low (just configuration change)

---

### **Option 4: Internal Aggregation from 1-Minute Bars** 🏗️ SYNTHETIC

**Generate synthetic sub-minute bars from 1-minute data**

```python
# Take 1-minute bars and create faster synthetic bars
# Example: Split each 1-minute bar into 12 x 5-second bars

def on_bar(self, bar: Bar):
    # bar.open, bar.high, bar.low, bar.close, bar.volume
    
    # Generate 12 synthetic 5-second bars
    for i in range(12):
        synthetic_bar = self._interpolate_bar(bar, i, 12)
        self._process_synthetic_bar(synthetic_bar)
```

**Advantages:**
- ✅ Works with Bybit 1-minute data
- ✅ Generates more trading signals
- ✅ No external dependency

**Disadvantages:**
- ❌ **NOT REAL DATA** - synthetic/interpolated
- ❌ Accuracy questionable
- ❌ May not reflect actual price movement
- ❌ **NOT RECOMMENDED** for real trading

**Implementation Complexity:** Low, but poor quality

---

## 📊 **COMPARISON MATRIX**

| Option | Frequency | Real Data? | Complexity | Recommended? |
|--------|-----------|------------|------------|--------------|
| **1-min bars + aggressive settings** | 60/hour | ✅ Yes | Low | ✅ **YES** (start here) |
| **Tick data** | 1000+/sec | ✅ Yes | High | ⚠️ Advanced users |
| **Binance 1-second bars** | 3600/hour | ✅ Yes | Low | ✅ **YES** (if willing to switch) |
| **Synthetic bars** | Configurable | ❌ No | Low | ❌ NO (poor quality) |

---

## 🎯 **RECOMMENDED APPROACH**

### **Phase 1: Optimize Current Setup** (Immediate)

**Use 1-minute bars with aggressive settings:**

```python
bar_type = "BTCUSDT-LINEAR.BYBIT-1-MINUTE-LAST-EXTERNAL"
confidence_threshold = 0.65  # Lower threshold = more signals
max_bars_in_position = 20    # Shorter holds = more turnover
```

**Expected improvement:**
- Trades: 15-40/day (vs current 5-20/day)
- Data points: Still 60/hour
- **+100% more trading activity** without infrastructure changes

### **Phase 2: Switch to Binance** (Week 2-3)

**If you need faster data:**

1. Set up Binance testnet account
2. Configure NautilusTrader for Binance
3. Use 1-second bars

**Expected results:**
- Bars: 3600/hour (60x more than Bybit!)
- Trades: 50-200/day
- **Much faster data collection**

### **Phase 3: Tick Data** (Month 2-3)

**For true high-frequency:**

1. Refactor strategy to handle tick data
2. Implement internal bar aggregation
3. Process 10-1000 updates per second

**Expected results:**
- Updates: 10,000+/hour
- Trades: 100-500+/day
- **Maximum frequency possible**

---

## 💡 **IMMEDIATE ACTION**

Since you want to "collect as much data as possible," here's what to do NOW:

### **Quick Fix (5 minutes):**

```bash
# Edit configuration for more aggressive trading
nano scripts/start_paper_trading_sandbox.py

# Change these lines:
confidence_threshold=0.65,     # Was 0.75, lower = more trades
max_bars_in_position=20,       # Was 50, shorter = more turnover

# Restart
source nautilus_env/bin/activate
nohup python scripts/start_paper_trading_sandbox.py > /tmp/paper_trading.out 2>&1 &
```

**This will give you ~2x more trades immediately!**

### **Better Solution (1-2 hours):**

**Switch to Binance** for 1-second bars:

```bash
# 1. Create Binance testnet account
https://testnet.binance.vision/

# 2. Get API keys

# 3. Configure NautilusTrader for Binance
# (We can help with this!)

# 4. Use 1-second bars = 60x more data!
```

---

## 🔍 **WHY BYBIT HAS THIS LIMITATION**

### **Exchange API Design:**

Most exchanges limit kline/candlestick granularity:
- **Bybit**: 1-minute minimum (testnet and mainnet)
- **Binance**: 1-second minimum (very generous!)
- **FTX** (defunct): 15-second minimum
- **Coinbase**: 1-minute minimum
- **Kraken**: 1-minute minimum

**Reason:** 
- Reduces server load
- Most traders don't need sub-minute bars
- High-frequency traders use WebSocket tick streams instead

### **Bybit's Philosophy:**

```
Bybit API design:
├─ Kline/Bar data: 1-minute minimum (for regular traders)
└─ WebSocket tick stream: Real-time (for HFT)

If you want < 1 minute:
→ Use WebSocket ticks
→ Build your own bars
```

---

## 📈 **DATA COLLECTION RATES**

**Current Setup (Bybit 1-min bars):**
```
Per Hour:     60 bars
Per Day:      1,440 bars
Per Week:     10,080 bars
Per Month:    43,200 bars
```

**With Aggressive Settings:**
```
Trades/Day:   15-40 (vs 5-20)
Data Quality: Same
Cost:         Same
Improvement:  +100-200% trades
```

**If Switch to Binance 1-sec bars:**
```
Per Hour:     3,600 bars (60x more!)
Per Day:      86,400 bars
Per Week:     604,800 bars
Per Month:    2,592,000 bars (2.6 MILLION!)
```

**With Tick Data (Bybit or Binance):**
```
Per Hour:     10,000-100,000+ updates
Per Day:      240,000-2,400,000+ updates
Complexity:   High
Data Quality: Maximum
```

---

## ✅ **SUMMARY**

### **The Reality:**
- Bybit doesn't support second-level bars (API limitation)
- 1-minute is the FASTEST Bybit can provide
- NautilusTrader CAN handle much faster, but Bybit can't send it

### **Your Options:**
1. **Stay on Bybit** - Use aggressive settings for 2x more trades
2. **Switch to Binance** - Get 1-second bars (60x more data!) ← RECOMMENDED
3. **Use tick data** - Maximum frequency but complex

### **Recommended Path:**
```
Week 1: Optimize current Bybit setup (aggressive settings)
Week 2: Switch to Binance for 1-second bars
Week 3-4: Validate performance with 60x more data
Month 2+: Consider tick data if needed
```

---

**Bottom Line:** The infrastructure (NautilusTrader + Rust/Cython) CAN handle high-frequency trading, but **Bybit's API won't send data faster than 1-minute bars**. For faster data collection, switch to Binance which supports 1-second bars natively!
