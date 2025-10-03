# NautilusTrader Quick Reference

## 🎯 TL;DR - What You Need to Know

### The Crates Folder = Rust Core (High Performance Engine)
**You DON'T need to touch it** for strategy development. It's the compiled engine that makes NautilusTrader fast.

### Jupyter Notebooks = Interactive Python Environment
**Like Excel for code** - run cells one at a time, see results immediately, perfect for experimenting.

### Your Work: Write Strategies in Python
**Everything you need is accessible through Python** - no Rust knowledge required.

---

## 📁 Project Structure (What Matters to You)

```
nautilus_trader/
├── crates/                    # ⚙️  Rust core (DON'T TOUCH - it's the engine)
│   ├── model/                 # Trading models (Order, Position, etc.)
│   ├── backtest/              # Backtest engine
│   ├── execution/             # Order execution
│   └── adapters/              # Exchange connections
│
├── nautilus_trader/           # 🐍 Python package (THIS IS WHAT YOU USE)
│   ├── examples/
│   │   ├── strategies/        # ✨ Study these! Pre-built strategies
│   │   ├── algorithms/        # Execution algorithms (TWAP, VWAP)
│   │   └── indicators/        # Technical indicators
│   ├── backtest/              # Backtesting utilities
│   ├── live/                  # Live trading
│   └── model/                 # Python interfaces to Rust models
│
├── examples/                  # 📚 Learning resources
│   ├── backtest/
│   │   ├── example_01_*/      # Start here!
│   │   ├── example_02_*/
│   │   └── ...
│   └── notebooks/             # Jupyter notebooks
│
├── LEARNING_PATH.md           # 📖 Your study guide (READ THIS!)
├── ANALYTICS_GUIDE.md         # 📊 Performance analysis reference
└── activate_env.sh            # 🔧 Environment activation script
```

---

## 🚀 Daily Workflow

### Start Your Session
```bash
cd /home/ajk/Nautilus/nautilus_trader
source activate_env.sh
```

### Option 1: Run Python Scripts
```bash
# Run an example backtest
python examples/backtest/crypto_ema_cross_ethusdt_trade_ticks.py

# Run detailed analysis
python examples/backtest/crypto_ema_cross_ethusdt_detailed_analysis.py

# Run structured examples
cd examples/backtest/example_01_load_bars_from_custom_csv
python run.py
```

### Option 2: Use Jupyter Notebooks (Interactive)
```bash
# Install Jupyter (first time only)
pip install jupyter matplotlib

# Start Jupyter
jupyter notebook

# Opens browser → navigate to examples/notebooks/quickstart_analysis.ipynb
# Run cells with Shift+Enter
```

### Option 3: Python REPL (Quick Tests)
```bash
python

>>> import nautilus_trader
>>> print(nautilus_trader.__version__)
>>> # Test your code interactively
```

---

## 🎓 Learning Sequence (4 Weeks)

### Week 1: Examples & Understanding
```bash
# Day 1-2: Read strategies
cat nautilus_trader/examples/strategies/ema_cross.py
cat nautilus_trader/examples/strategies/orderbook_imbalance.py

# Day 3-4: Run structured examples
cd examples/backtest/example_01_load_bars_from_custom_csv && python run.py
cd ../example_02_use_clock_timer && python run.py
cd ../example_03_bar_aggregation && python run.py

# Day 5: Modify and re-run
# Copy an example, change parameters, compare results
```

### Week 2: Data & Indicators
```bash
# Learn data types
cd examples/backtest/example_04_using_data_catalog && python run.py

# Study indicators
cd ../example_07_using_indicators && python run.py

# Chain indicators
cd ../example_08_cascaded_indicator && python run.py
```

### Week 3: Build Your Strategy
```python
# Create: my_strategy.py
from nautilus_trader.trading.strategy import Strategy

class MyStrategy(Strategy):
    def on_start(self):
        self.subscribe_bars(self.bar_type)
    
    def on_bar(self, bar):
        # Your logic here
        if self.should_buy(bar):
            self.buy()
```

### Week 4: Optimize & Integrate
- Test multiple parameters
- Add risk management
- Connect to real data sources

---

## 🔑 Key Concepts

### 1. Architecture: Rust + Python

```
┌──────────────────────────────────┐
│   You Write: Python Strategies   │ ← Your code
├──────────────────────────────────┤
│   PyO3: Python ↔ Rust Bridge     │ ← Automatic
├──────────────────────────────────┤
│   Rust Core: High Performance    │ ← Pre-compiled
│   (crates/ folder)                │   (Don't touch)
└──────────────────────────────────┘
```

**Result:** Python ease + Rust speed

### 2. Event-Driven (Not Loop-Based)

```python
# ❌ Traditional (wrong)
for bar in bars:
    if condition:
        buy()

# ✅ NautilusTrader (correct)
def on_bar(self, bar):
    if condition:
        self.buy()
```

### 3. Strategy Lifecycle

```
1. on_start()     → Initialize, subscribe to data
2. on_data()      → Receive market data, make decisions
3. on_event()     → Handle order fills, position updates
4. on_stop()      → Clean up, close positions
```

### 4. Data Types

- **Ticks**: Individual trades (most granular)
- **Bars**: OHLCV candles (time-aggregated)
- **OrderBook**: Bid/ask levels
- **Custom**: Any data you need

---

## 💡 Common Tasks

### Run a Backtest
```python
from nautilus_trader.backtest.engine import BacktestEngine

engine = BacktestEngine(config=...)
engine.add_venue(...)
engine.add_instrument(...)
engine.add_data(...)
engine.add_strategy(strategy)
engine.run()

# Analyze
positions = engine.trader.generate_positions_report()
```

### Create a Simple Strategy
```python
from nautilus_trader.trading.strategy import Strategy

class SimpleMA(Strategy):
    def __init__(self, period: int = 20):
        self.period = period
        self.ma = None
    
    def on_start(self):
        self.subscribe_bars(self.bar_type)
    
    def on_bar(self, bar):
        # Calculate moving average
        # Buy/sell based on price vs MA
        pass
```

### Access Performance Data
```python
# After engine.run()
positions = engine.cache.positions()
orders = engine.cache.orders()
account = engine.cache.account_for_venue(venue)

# Reports
positions_df = engine.trader.generate_positions_report()
fills_df = engine.trader.generate_order_fills_report()
```

---

## 🆘 Troubleshooting

### Issue: Import Error
```bash
# Make sure environment is activated
source activate_env.sh

# Verify installation
python -c "import nautilus_trader; print(nautilus_trader.__version__)"
```

### Issue: Need to Rebuild
```bash
# After modifying Rust/Cython code
make build-debug  # Fast compile, slower runtime
make build        # Slow compile, fast runtime
```

### Issue: Jupyter Not Working
```bash
# Install Jupyter in the virtual environment
pip install jupyter ipykernel

# Register kernel
python -m ipykernel install --user --name=nautilus-trader

# Start Jupyter
jupyter notebook
```

---

## 📚 Essential Reading (In Order)

1. ✅ **README.md** (Done!)
2. 📖 **LEARNING_PATH.md** (Comprehensive guide) ← Start here
3. 📊 **ANALYTICS_GUIDE.md** (Performance analysis)
4. 🌐 [Official Docs](https://nautilustrader.io/docs/) (Online reference)
5. 💬 [Discord Community](https://discord.gg/NautilusTrader) (Get help)

---

## 🎯 Your First Steps Tomorrow

```bash
# 1. Activate
cd /home/ajk/Nautilus/nautilus_trader
source activate_env.sh

# 2. Read one strategy
cat nautilus_trader/examples/strategies/ema_cross.py

# 3. Run first structured example
cd examples/backtest/example_01_load_bars_from_custom_csv
python run.py

# 4. Study the code, understand what it does

# 5. Try Jupyter (optional)
pip install jupyter matplotlib
jupyter notebook
# Open: examples/notebooks/quickstart_analysis.ipynb
```

---

## 🔥 Power User Tips

### View All Make Commands
```bash
make help
```

### Run Tests
```bash
make pytest              # All tests
pytest tests/unit_tests  # Unit tests only
```

### Format Code
```bash
make ruff    # Auto-format Python code
```

### Build Documentation Locally
```bash
make docs
# Opens in browser
```

### Check for Updates
```bash
git pull origin develop
uv sync --all-extras
```

---

## 🎉 You're Ready!

**Remember:**
- 🐍 Write strategies in **Python**
- ⚙️ **Crates** are pre-compiled (don't touch)
- 📓 **Jupyter** = interactive experimentation
- 📖 Follow **LEARNING_PATH.md** for structured learning

**Start simple. Build incrementally. Ask questions!**

Join Discord: https://discord.gg/NautilusTrader
Read Docs: https://nautilustrader.io/docs/

Happy Trading! 🚀
