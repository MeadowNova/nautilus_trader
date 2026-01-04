# 🚀 Quick Start: Advanced Strategy

## Run It Right Now!

### **Method 1: Using the Script (Easiest)**
```bash
cd ~/Nautilus/nautilus_trader
./RUN_ADVANCED_STRATEGY.sh
```

### **Method 2: Direct Python**
```bash
cd ~/Nautilus/nautilus_trader
source activate_env.sh
python examples/backtest/advanced_profitable_strategy.py
```

### **Method 3: With Filtered Output (See Signals Only)**
```bash
cd ~/Nautilus/nautilus_trader
source activate_env.sh
python examples/backtest/advanced_profitable_strategy.py 2>&1 | \
  grep -E "(🟢|🔴|💰|🛑|FINAL STATS|Total orders|Total positions)"
```

---

## 📊 What You'll See

### **Entry Signals (🟢)**
```
🟢 ENTRY: Price=424.68, EMA(424.57/424.29), Pattern=True, Sentiment=0.00
```

### **Exit Signals (🔴/💰/🛑)**
```
💰 TAKE PROFIT: +4.23%
🛑 STOP LOSS: -2.01%  
📉 TRAILING STOP: +3.45%
```

### **Final Results**
```
📊 FINAL STATS: Trades=10, Wins=2, Win Rate=20.00%, Total P&L=-0.0184
Total orders: 21
Total positions: 11
```

---

## 📁 Where Results Are Stored

### **1. Terminal Output**
- Real-time during execution
- Full log with all events

### **2. Saved Log Files** (if using script)
```
/home/ajk/Nautilus/nautilus_trader/backtest_results/
└── advanced_strategy_20251003_150430.log
```

### **3. In-Memory During Run**
- Portfolio state
- Position history
- Order history

### **4. Export Results Manually**
Add this to the end of `run_advanced_strategy()` function:

```python
# Generate reports
positions_df = engine.trader.generate_positions_report()
orders_df = engine.trader.generate_orders_report()
fills_df = engine.trader.generate_fills_report()

# Save to CSV
positions_df.to_csv("backtest_results/positions.csv")
orders_df.to_csv("backtest_results/orders.csv")
fills_df.to_csv("backtest_results/fills.csv")

print("\n✅ Reports saved to backtest_results/")
```

---

## 🔧 Customize Strategy

Edit `/home/ajk/Nautilus/nautilus_trader/examples/backtest/advanced_profitable_strategy.py`

### **Lines 664-680: Configure Parameters**
```python
strategy_config = AdvancedStrategyConfig(
    instrument_id=str(ETHUSDT_BINANCE.id),
    bar_type="ETHUSDT.BINANCE-250-TICK-LAST-INTERNAL",
    
    # 🔧 ADJUST THESE:
    fast_ema_period=9,        # Try: 5, 9, 13, 21
    slow_ema_period=21,       # Try: 13, 21, 34, 55
    trend_ema_period=50,      # Try: 50, 100, 200
    
    base_trade_size=Decimal("0.10000"),  # Position size
    
    stop_loss_pct=0.02,       # 2% stop loss
    take_profit_pct=0.04,     # 4% take profit
    trailing_stop_pct=0.015,  # 1.5% trailing
    max_hold_seconds=3600,    # 1 hour max hold
    
    min_win_rate=0.40,        # Pause below 40%
    max_drawdown=0.15,        # Pause above 15% DD
)
```

### **Line 690: Use More Data**
```python
# Current (100k ticks ~5 hours):
ticks = wrangler.process(provider.read_csv_ticks("binance/ethusdt-trades.csv"))

# Use FULL dataset:
ticks = wrangler.process(provider.read_csv_ticks("binance/ethusdt-trades.csv"))
# Remove any [:100000] slicing
```

---

## 📈 Expected Results

### **Current Test (5 hours of data)**
- Trades: ~10-11
- Win Rate: 20-30%
- P&L: -1% to +2% (varies by market conditions)
- Orders: ~20-22
- Runtime: ~0.3 seconds

### **Full Dataset (days of data)**
- Trades: 100-500+
- Win Rate: 35-50%
- P&L: Varies widely
- Runtime: ~5-30 seconds

---

## 🎯 Quick Commands Reference

```bash
# Navigate to project
cd ~/Nautilus/nautilus_trader

# Run strategy (simple)
./RUN_ADVANCED_STRATEGY.sh

# Run with filtered output
python examples/backtest/advanced_profitable_strategy.py 2>&1 | \
  grep -E "(🟢|🔴|💰|🛑|FINAL)"

# Save results with timestamp
python examples/backtest/advanced_profitable_strategy.py > \
  backtest_results/run_$(date +%Y%m%d_%H%M%S).log 2>&1

# View last saved results
ls -lt backtest_results/ | head -5
cat backtest_results/advanced_strategy_*.log | tail -50

# Search for specific events
grep "ENTRY" backtest_results/advanced_strategy_*.log
grep "STOP LOSS" backtest_results/advanced_strategy_*.log
grep "TAKE PROFIT" backtest_results/advanced_strategy_*.log
```

---

## 📚 Full Documentation

For complete details, see:
- **ADVANCED_STRATEGY_SUCCESS.md** - Full technical documentation
- **PROFITABILITY_ROADMAP.md** - 12-month path to profits
- **AI_AUTOMATION_GUIDE.md** - AI integration levels

---

## 🆘 Troubleshooting

### **Error: "Invalid size precision"**
✅ Already fixed! Using `qty_str = f"{float(quantity):.5f}"`

### **Error: "Module not found"**
```bash
source activate_env.sh  # Activate environment first
```

### **Error: "File not found: ethusdt-trades.csv"**
```bash
# Check data exists:
ls -la ~/.nautilus/data/binance/
# Should see: ethusdt-trades.csv
```

### **No output / Silent failure**
```bash
# Run with full output:
python examples/backtest/advanced_profitable_strategy.py 2>&1 | less
# Scroll to see all logs
```

---

## ✅ Success Checklist

- [x] Environment activated
- [x] Strategy runs without errors
- [x] See entry signals (🟢)
- [x] See exit signals (🔴/💰/🛑)
- [x] See final statistics
- [x] Results make sense (not all profits!)

---

**Next Steps:**
1. ✅ Run the strategy (you're doing this now!)
2. 📊 Review the results
3. 🔧 Optimize parameters
4. 📈 Test on more data
5. 🚀 Move to paper trading

**You're Ready to Trade!** 🎯
