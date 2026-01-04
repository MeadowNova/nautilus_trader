# NautilusTrader Learning Path & Architecture Guide

## 🏗️ Understanding the `crates` Folder

### What Are Crates?

**Crates are Rust packages/libraries** - they're the high-performance core of NautilusTrader written in Rust.

The `/crates` folder contains the **compiled Rust code** that powers the platform's performance-critical components. Think of it as the "engine room" of NautilusTrader.

### Architecture: Rust Core + Python Interface

```
┌─────────────────────────────────────────────┐
│         Python Layer (What you use)         │
│  - Write strategies in Python               │
│  - Run backtests                            │
│  - Configure systems                        │
├─────────────────────────────────────────────┤
│         PyO3 Bindings (Bridge)              │
│  - Connects Python to Rust                  │
│  - Located in: crates/pyo3/                 │
├─────────────────────────────────────────────┤
│      Rust Core (High Performance)           │
│  - Event engine                             │
│  - Order matching                           │
│  - Data processing                          │
│  - Risk management                          │
└─────────────────────────────────────────────┘
```

### Key Crates and Their Purpose

```
/crates
├── model/           - Core trading domain models (Instrument, Order, Position, etc.)
├── core/            - Fundamental types and utilities
├── data/            - Data handling and processing
├── execution/       - Order execution engine
├── portfolio/       - Portfolio management and accounting
├── risk/            - Risk management and checks
├── backtest/        - Backtesting engine
├── live/            - Live trading engine
├── indicators/      - Technical indicators (EMA, RSI, etc.)
├── adapters/        - Exchange integrations
│   ├── bybit/       - Bybit exchange
│   ├── databento/   - Databento data provider
│   ├── hyperliquid/ - Hyperliquid DEX
│   └── ...          - Other exchanges
├── network/         - Network communication (WebSocket, HTTP)
├── infrastructure/  - Redis, PostgreSQL, message bus
├── pyo3/           - Python bindings (PyO3)
└── testkit/        - Testing utilities
```

### Do You Need to Touch the Crates?

**For most users: NO** ✋

- ✅ **Strategy development**: Pure Python
- ✅ **Backtesting**: Pure Python
- ✅ **Live trading**: Pure Python
- ✅ **Custom indicators**: Python or Cython

**You only need to work with Rust crates if you:**
- 🔧 Want to modify the core engine
- 🚀 Need extreme performance optimizations
- 🔌 Building a new exchange adapter in Rust
- 🛠️ Contributing to the core platform

### Building Crates (When Needed)

If you modify Rust code, rebuild with:
```bash
make build-debug    # For development (fast compile, slower runtime)
make build          # For production (slow compile, fast runtime)
```

The build process:
1. Compiles Rust crates → binary libraries (`.so` on Linux)
2. Creates Python bindings via PyO3
3. Packages everything for Python to import

---

## 📓 Jupyter Notebooks Explained

### What is Jupyter?

**Jupyter** is an interactive computing environment where you can:
- Write and execute code in **cells** (not entire files)
- See results immediately
- Mix code, visualizations, and documentation
- Experiment iteratively

Think of it like an **interactive scientific calculator** for programming.

### Why Use Jupyter with NautilusTrader?

Perfect for:
- 📊 **Exploratory data analysis** - Visualizing market data
- 🧪 **Strategy prototyping** - Quick experimentation
- 📈 **Backtesting visualization** - Charts, equity curves
- 📚 **Learning** - Step-by-step tutorials
- 📝 **Research notebooks** - Documenting analysis

### Installing Jupyter

```bash
cd /home/ajk/Nautilus/nautilus_trader
source activate_env.sh
pip install jupyter matplotlib seaborn plotly
```

### Starting Jupyter

```bash
cd /home/ajk/Nautilus/nautilus_trader
source activate_env.sh
jupyter notebook
```

This opens your browser with an interactive notebook interface.

### Example Jupyter Workflow

```python
# Cell 1: Import libraries
import pandas as pd
import nautilus_trader as nt
from nautilus_trader.backtest.engine import BacktestEngine

# Cell 2: Load data
data = pd.read_csv('market_data.csv')
print(data.head())  # See results immediately

# Cell 3: Visualize
import matplotlib.pyplot as plt
data['close'].plot()
plt.show()  # Chart appears inline

# Cell 4: Run backtest
engine = BacktestEngine(...)
engine.run()

# Cell 5: Analyze results
positions = engine.cache.positions()
# ... interactive analysis
```

Each cell runs independently, letting you experiment without re-running everything.

### Finding Jupyter Examples

```bash
# Look for .ipynb files
find /home/ajk/Nautilus/nautilus_trader/examples -name "*.ipynb"
```

Current notebooks:
- `/examples/backtest/notebooks/*.py` - Databento examples
- `/examples/other/debugging/debug_mixed_jupyter.ipynb` - Debugging example

---

## 🚀 Your Learning Path: Next Steps

### Phase 1: Foundation (You are here! ✅)
- [x] Install NautilusTrader
- [x] Run first backtest
- [x] Understand basic reports
- [ ] **Next:** Read 2-3 example strategies

### Phase 2: Strategy Development (Weeks 1-2)

#### Step 1: Study Existing Strategies
```bash
cd /home/ajk/Nautilus/nautilus_trader
source activate_env.sh

# Read strategy examples
cat nautilus_trader/examples/strategies/ema_cross_twap.py
cat nautilus_trader/examples/strategies/ema_cross.py
```

**Action:** Pick one strategy and understand:
- How it receives data (on_bar, on_trade_tick)
- How it generates signals (EMA crossovers)
- How it places orders (buy/sell logic)

#### Step 2: Modify an Existing Strategy
```bash
# Copy an example
cp examples/strategies/ema_cross.py my_first_strategy.py

# Modify parameters:
# - Change EMA periods
# - Add a stop-loss
# - Test different position sizes

# Run your backtest
python examples/backtest/crypto_ema_cross_ethusdt_trade_ticks.py
```

#### Step 3: Run the Structured Examples
```bash
cd examples/backtest

# Start with Example 01
cd example_01_load_bars_from_custom_csv
python run.py

# Progress through:
# - Example 02: Clock timers
# - Example 03: Bar aggregation
# - Example 04: Data catalog
# - Example 05: Portfolio
# ... etc
```

### Phase 3: Data Understanding (Week 3)

#### Learn Data Types
- **Ticks**: Individual trades (most granular)
- **Bars**: OHLCV candles (aggregated)
- **Order Book**: Bid/ask levels
- **Custom Data**: Any custom market data

#### Practice with Real Data
```bash
# Explore test data
ls nautilus_trader/test_kit/test_data/

# Write a simple data loader
# (See example_01 for reference)
```

### Phase 4: Build Your First Strategy (Week 4)

**Project: Simple Mean Reversion Strategy**

1. **Design**
   - Buy when price < 20-period moving average
   - Sell when price > 20-period moving average
   - Use fixed position size

2. **Implement**
   ```python
   # Create: my_mean_reversion.py
   from nautilus_trader.trading.strategy import Strategy
   
   class MeanReversion(Strategy):
       def on_bar(self, bar):
           # Your logic here
           pass
   ```

3. **Backtest**
   - Use 1 month of data
   - Test on ETHUSDT
   - Analyze results

4. **Optimize**
   - Try different MA periods (10, 20, 50)
   - Add stop-loss
   - Compare results

### Phase 5: Advanced Topics (Ongoing)

#### Technical Analysis
- [ ] Multiple indicators (RSI, MACD, Bollinger Bands)
- [ ] Indicator cascading (Example 08)
- [ ] Custom indicators in Python

#### Order Management
- [ ] Advanced order types (GTD, FOK, IOC)
- [ ] Bracket orders (entry + stop + target)
- [ ] TWAP/VWAP execution algorithms

#### Risk Management
- [ ] Position sizing algorithms
- [ ] Portfolio risk controls
- [ ] Maximum drawdown limits

#### Data Integration
- [ ] Connect to Databento
- [ ] Use Interactive Brokers
- [ ] Historical data management

---

## 📚 Essential Resources

### Official Documentation
- **Getting Started**: https://nautilustrader.io/docs/latest/getting_started/
- **Concepts**: https://nautilustrader.io/docs/latest/concepts/
- **API Reference**: https://nautilustrader.io/docs/latest/api_reference/

### Key Concepts to Learn

#### 1. Event-Driven Architecture
NautilusTrader uses **events** not loops:
```python
# BAD (typical vectorized backtesting)
for bar in bars:
    if condition:
        buy()

# GOOD (event-driven)
def on_bar(self, bar):
    if condition:
        self.buy()
```

#### 2. Strategy Lifecycle
```
INITIALIZED → STARTING → RUNNING → STOPPING → STOPPED
     ↓           ↓          ↓          ↓         ↓
  on_start  on_data    on_data    on_stop   on_dispose
```

#### 3. Core Components
- **Strategy**: Your trading logic
- **Engine**: Orchestrates everything (BacktestEngine/TradingNode)
- **Cache**: Stores state (orders, positions, instruments)
- **MessageBus**: Passes events between components
- **Portfolio**: Tracks account balances and P&L

### Helpful Commands

```bash
# View all make targets
make help

# Run tests (learn from test examples)
make pytest

# Build documentation locally
make docs

# Format code
make ruff

# Type checking
make mypy
```

---

## 💡 Practical Weekly Plan

### Week 1: Foundation
- **Mon-Tue**: Read 3 example strategies, understand structure
- **Wed-Thu**: Run all 11 example backtests (example_01 through example_11)
- **Fri**: Modify an existing strategy, change one parameter, see results

### Week 2: Data & Indicators
- **Mon-Tue**: Learn bar aggregation (example_03), write custom bar handler
- **Wed-Thu**: Study indicators (example_07), chain indicators (example_08)
- **Fri**: Create a strategy using 2+ indicators

### Week 3: Build Custom Strategy
- **Mon-Tue**: Design strategy on paper, define entry/exit rules
- **Wed-Thu**: Implement in Python, handle edge cases
- **Fri**: Backtest, analyze, document results

### Week 4: Optimization & Integration
- **Mon-Tue**: Parameter optimization (test multiple configurations)
- **Wed-Thu**: Add proper risk management (stop-loss, position limits)
- **Fri**: Connect to real data source (Databento demo or paper trading)

---

## 🎯 Success Metrics

After 4 weeks, you should be able to:
- ✅ Write a custom strategy from scratch
- ✅ Run backtests with custom data
- ✅ Understand event-driven architecture
- ✅ Read and interpret performance reports
- ✅ Use technical indicators effectively
- ✅ Implement proper risk management

---

## 🆘 Getting Help

1. **Documentation**: https://nautilustrader.io/docs/
2. **Discord Community**: https://discord.gg/NautilusTrader
3. **GitHub Issues**: https://github.com/nautechsystems/nautilus_trader/issues
4. **Code Examples**: Browse `/examples` directory extensively

---

## 📖 Recommended Reading Order

1. `README.md` (project root) - Already done! ✅
2. `examples/backtest/example_01*/README.md` - Data loading
3. `nautilus_trader/examples/strategies/` - Strategy examples
4. Docs: [Core Concepts](https://nautilustrader.io/docs/latest/concepts/)
5. Docs: [Strategy Implementation](https://nautilustrader.io/docs/latest/concepts/strategies)
6. This file: `ANALYTICS_GUIDE.md` - Performance analysis

---

## 🔥 Quick Start Tomorrow

```bash
# 1. Activate environment
cd /home/ajk/Nautilus/nautilus_trader
source activate_env.sh

# 2. Run structured examples
cd examples/backtest/example_01_load_bars_from_custom_csv
python run.py

# 3. Study the code
code run.py  # or your preferred editor

# 4. Modify something small
# Change a parameter, re-run, compare results

# 5. Repeat with example_02, example_03, etc.
```

**Start simple. Build incrementally. Ask questions. Have fun!** 🚀
