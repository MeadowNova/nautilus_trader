# Nautilus Trader - Beginner's Playbook

**A Complete Guide to Algorithmic Trading with Nautilus Trader**

*From Installation to Production Deployment*

---

## Table of Contents

1. [System Overview](#1-system-overview)
2. [Environment Setup](#2-environment-setup)
3. [Your First Strategy](#3-your-first-strategy)
4. [Strategy Development Deep Dive](#4-strategy-development-deep-dive)
5. [Data Management](#5-data-management)
6. [Backtesting Workflows](#6-backtesting-workflows)
7. [Paper Trading Setup](#7-paper-trading-setup)
8. [Production Infrastructure](#8-production-infrastructure)
9. [Production Deployment](#9-production-deployment)
10. [Troubleshooting & FAQ](#10-troubleshooting--faq)
11. [Resources & Next Steps](#11-resources--next-steps)
12. [Phase 5 – Documentation & Handoff (AI-Adaptive Infrastructure)](#12-phase-5--documentation--handoff-ai-adaptive-infrastructure)

---

## 1. System Overview

### 1.1 What is Nautilus Trader?

Nautilus Trader is a **high-performance algorithmic trading platform** that lets you:
- **Backtest** strategies on historical data
- **Paper trade** with real-time market data (no real money)
- **Live trade** in production with real capital
- **Use the same code** across all three environments

**Key Features:**
- 🚀 High performance (Rust core with Python interface)
- 📊 Professional backtesting engine
- 🔄 Identical code for backtesting and live trading
- 📈 Built-in technical indicators
- 🏦 Multiple exchange support
- 🔒 Type-safe and memory-safe

### 1.2 Architecture Overview

```
┌─────────────────────────────────────────────┐
│           Your Strategy (Python)            │
│   - Strategy logic in Python                │
│   - Easy to write and understand            │
└──────────────────┬──────────────────────────┘
                   │
                   │ Python API
                   │
┌──────────────────▼──────────────────────────┐
│        Nautilus Core (Rust)                 │
│   - Event engine (ultra-fast)               │
│   - Order matching                          │
│   - Data handling                           │
│   - Exchange connections                    │
└─────────────────────────────────────────────┘
```

**What this means:**
- You write strategies in **Python** (easy, flexible)
- Performance-critical parts run in **Rust** (fast, safe)
- Best of both worlds!

### 1.3 Two API Levels

Nautilus offers two ways to build strategies:

#### Low-Level API (`BacktestEngine`)
**Use for:** Learning, prototyping, experimentation

✅ **Pros:**
- Simpler to understand
- Easier data loading (CSV, custom formats)
- Direct component access
- Faster iteration

❌ **Cons:**
- No direct path to live trading
- Manual setup required

#### High-Level API (`BacktestNode` / `TradingNode`)
**Use for:** Production strategies

✅ **Pros:**
- Smooth transition to live trading
- Built-in infrastructure
- Professional-grade features
- Complete monitoring

❌ **Cons:**
- Requires Parquet data catalog
- More abstraction

**Recommended Path:**
1. Start with **Low-Level API** for learning
2. Migrate to **High-Level API** when ready for production

### 1.4 Event-Driven Architecture

Everything in Nautilus happens through **events**:

```
Market Data Event → Strategy → Order Event → Exchange
                       ↓
               Portfolio Update
```

**Benefits:**
- Deterministic execution
- Complete audit trail
- Easy testing
- Same behavior in backtest and live

---

## 2. Environment Setup

### 2.1 Prerequisites

**Required:**
- Python 3.10 or higher
- pip or uv package manager
- 4GB+ RAM
- Linux, macOS, or Windows (WSL)

**Optional:**
- Rust toolchain (only if building from source)
- Docker (for infrastructure later)

### 2.2 Installation Steps

#### Option 1: Install from PyPI (Recommended)

```bash
# Create virtual environment
python3 -m venv nautilus_env
source nautilus_env/bin/activate  # On Windows: nautilus_env\Scripts\activate

# Install Nautilus Trader
pip install nautilus_trader

# Or using uv (faster)
uv pip install nautilus_trader
```

#### Option 2: Install from Source

```bash
# Clone repository
git clone https://github.com/nautechsystems/nautilus_trader.git
cd nautilus_trader

# Create virtual environment
python3 -m venv nautilus_env
source nautilus_env/bin/activate

# Install in development mode
pip install -e .

# Or build with Rust optimizations
make install
```

### 2.3 Verification

**Test your installation:**

```python
# test_installation.py
import nautilus_trader

print(f"Nautilus Trader version: {nautilus_trader.__version__}")

# Import key components
from nautilus_trader.trading.strategy import Strategy
from nautilus_trader.backtest.engine import BacktestEngine
from nautilus_trader.model.instruments import Instrument

print("✅ Installation successful!")
```

Run it:
```bash
python test_installation.py
```

**Expected output:**
```
Nautilus Trader version: X.X.X
✅ Installation successful!
```

### 2.4 IDE Setup

**VS Code (Recommended):**

Install extensions:
- Python (Microsoft)
- Pylance (Microsoft)
- Jupyter (for notebooks)

**Settings (`.vscode/settings.json`):**
```json
{
    "python.linting.enabled": true,
    "python.linting.pylintEnabled": true,
    "python.formatting.provider": "black",
    "python.analysis.typeCheckingMode": "basic"
}
```

**PyCharm:**
- Configure Python interpreter to use your virtual environment
- Enable type checking in settings

### 2.5 Common Installation Issues

**Issue: Rust compiler not found**
```
error: Rust compiler not found
```
**Solution:** Install Rust toolchain:
```bash
curl --proto '=https' --tlsv1.2 -sSf https://sh.rustup.rs | sh
source $HOME/.cargo/env
```

**Issue: Python version too old**
```
ERROR: Python 3.10 or higher is required
```
**Solution:** Upgrade Python or use pyenv:
```bash
pyenv install 3.11
pyenv local 3.11
```

**Issue: Missing dependencies**
```
ImportError: No module named 'xyz'
```
**Solution:** Reinstall with all dependencies:
```bash
pip install --force-reinstall nautilus_trader
```

---

## 3. Your First Strategy

### 3.1 The Simple EMA Cross Strategy

Let's build a simple strategy:
- **Buy** when fast EMA crosses above slow EMA
- **Sell** when fast EMA crosses below slow EMA

### 3.2 Complete Code Example

Create `my_first_strategy.py`:

```python
from decimal import Decimal
from dataclasses import dataclass

from nautilus_trader.trading.strategy import Strategy, StrategyConfig
from nautilus_trader.model.identifiers import InstrumentId
from nautilus_trader.model.data import Bar
from nautilus_trader.indicators.ema import ExponentialMovingAverage
from nautilus_trader.model.enums import OrderSide


# Step 1: Define Configuration
@dataclass(frozen=True)
class EMACrossConfig(StrategyConfig):
    """Configuration for EMA Cross strategy"""
    instrument_id: str
    fast_period: int = 10
    slow_period: int = 20
    trade_size: str = "1.0"


# Step 2: Implement Strategy
class EMACrossStrategy(Strategy):
    """
    Simple EMA crossover strategy.
    
    - Buys when fast EMA crosses above slow EMA
    - Sells when fast EMA crosses below slow EMA
    """
    
    def __init__(self, config: EMACrossConfig):
        super().__init__(config)
        
        # Parse instrument ID
        self.instrument_id = InstrumentId.from_str(config.instrument_id)
        
        # Create indicators
        self.fast_ema = ExponentialMovingAverage(config.fast_period)
        self.slow_ema = ExponentialMovingAverage(config.slow_period)
        
        # Track previous signal for crossover detection
        self.previous_signal = 0
        
    def on_start(self):
        """Called when strategy starts"""
        # Subscribe to bars for our instrument
        self.subscribe_bars(self.instrument_id)
        self.log.info(f"Strategy started for {self.instrument_id}")
    
    def on_bar(self, bar: Bar):
        """Called on each new bar"""
        # Update indicators with latest close price
        self.fast_ema.update(bar.close)
        self.slow_ema.update(bar.close)
        
        # Wait for indicators to initialize
        if not self.fast_ema.initialized or not self.slow_ema.initialized:
            return
        
        # Calculate current signal
        current_signal = 1 if self.fast_ema.value > self.slow_ema.value else -1
        
        # Detect crossover (signal change)
        if current_signal != self.previous_signal:
            # Close any existing position first
            if not self.portfolio.is_flat(self.instrument_id):
                self.close_all_positions(self.instrument_id)
            
            # Open new position in crossover direction
            if current_signal == 1:
                self.log.info(f"BUY signal: Fast EMA ({self.fast_ema.value:.2f}) > Slow EMA ({self.slow_ema.value:.2f})")
                self.buy(trade_size=Decimal(self.config.trade_size))
            else:
                self.log.info(f"SELL signal: Fast EMA ({self.fast_ema.value:.2f}) < Slow EMA ({self.slow_ema.value:.2f})")
                self.sell(trade_size=Decimal(self.config.trade_size))
        
        # Update previous signal
        self.previous_signal = current_signal
    
    def on_stop(self):
        """Called when strategy stops"""
        # Close all positions
        self.close_all_positions(self.instrument_id)
        self.log.info("Strategy stopped")
```

### 3.3 Running Your First Backtest

Now let's backtest this strategy with the **Low-Level API**:

```python
# backtest_ema_cross.py
from decimal import Decimal
from nautilus_trader.backtest.engine import BacktestEngine
from nautilus_trader.model.currencies import USD
from nautilus_trader.model.enums import AccountType, OMSType
from nautilus_trader.model.identifiers import Venue
from nautilus_trader.model.objects import Money
from nautilus_trader.test_kit.providers import TestInstrumentProvider
from my_first_strategy import EMACrossStrategy, EMACrossConfig

# Step 1: Create backtest engine
engine = BacktestEngine()

# Step 2: Add a venue (exchange)
BINANCE = Venue("BINANCE")
engine.add_venue(
    venue=BINANCE,
    oms_type=OMSType.NETTING,  # Single position per instrument
    account_type=AccountType.CASH,  # Cash account (not margin)
    base_currency=USD,
    starting_balances=[Money(100_000, USD)]  # Start with $100,000
)

# Step 3: Add instrument
instrument = TestInstrumentProvider.btcusdt_binance()
engine.add_instrument(instrument)

# Step 4: Add strategy
config = EMACrossConfig(
    instrument_id=str(instrument.id),
    fast_period=10,
    slow_period=20,
    trade_size="0.1"  # Trade 0.1 BTC
)
strategy = EMACrossStrategy(config=config)
engine.add_strategy(strategy)

# Step 5: Load data (placeholder - we'll cover this in Section 5)
# For now, use test data
from nautilus_trader.test_kit.providers import TestDataProvider
bars = TestDataProvider.btcusdt_binance_bars()
engine.add_data(bars)

# Step 6: Run backtest
engine.run()

# Step 7: Get results
account = engine.trader.generate_account_report(BINANCE)
print(account)

orders = engine.trader.generate_order_fills_report()
print(orders)

positions = engine.trader.generate_positions_report()
print(positions)
```

### 3.4 Understanding the Output

**Account Report:**
```
=============================== Account Report ===============================
Venue: BINANCE
Balance: 102,450.00 USD
Realized PnL: 2,450.00 USD
Unrealized PnL: 0.00 USD
==============================================================================
```

**Order Fills:**
```
======================== Order Fills ========================
Time                 | Instrument | Side | Quantity | Price
2024-01-01 10:00:00 | BTC/USD   | BUY  | 0.1      | 45000
2024-01-02 14:30:00 | BTC/USD   | SELL | 0.1      | 46000
2024-01-03 09:15:00 | BTC/USD   | BUY  | 0.1      | 45500
...
=============================================================
```

**What this tells you:**
- Starting balance: $100,000
- Ending balance: $102,450
- Profit: $2,450 (2.45%)
- Total trades: [shown in order fills]

### 3.5 Modifying Your Strategy

**Try these experiments:**

1. **Change EMA periods:**
```python
config = EMACrossConfig(
    instrument_id=str(instrument.id),
    fast_period=5,   # Faster signal
    slow_period=30,  # Slower signal
    trade_size="0.1"
)
```

2. **Change trade size:**
```python
trade_size="0.5"  # Larger position
```

3. **Add logging to see indicator values:**
```python
def on_bar(self, bar: Bar):
    self.log.info(f"Fast: {self.fast_ema.value:.2f}, Slow: {self.slow_ema.value:.2f}")
```

---

## 4. Strategy Development Deep Dive

### 4.1 Strategy Anatomy

Every Nautilus strategy has two components:

#### Component 1: Configuration (Frozen Dataclass)

```python
from dataclasses import dataclass
from nautilus_trader.trading.strategy import StrategyConfig

@dataclass(frozen=True)
class MyStrategyConfig(StrategyConfig):
    """
    Configuration must be frozen (immutable) for reproducibility
    """
    instrument_id: str
    parameter1: int = 10
    parameter2: float = 1.5
    parameter3: str = "default"
```

**Why frozen?**
- Ensures backtest reproducibility
- Prevents accidental parameter changes
- Required by Nautilus framework

#### Component 2: Strategy Class

```python
from nautilus_trader.trading.strategy import Strategy

class MyStrategy(Strategy):
    """Your strategy logic"""
    
    def __init__(self, config: MyStrategyConfig):
        super().__init__(config)
        # Initialize your indicators, state, etc.
    
    def on_start(self):
        # Subscribe to data
        pass
    
    def on_bar(self, bar: Bar):
        # React to new bars
        pass
    
    def on_stop(self):
        # Cleanup
        pass
```

### 4.2 Strategy Lifecycle Hooks

Nautilus calls these methods at specific times:

| Method | When Called | Purpose |
|--------|-------------|---------|
| `on_start()` | Strategy starts | Subscribe to data, initialize |
| `on_stop()` | Strategy stops | Close positions, cleanup |
| `on_bar(bar)` | New bar received | Bar-based strategy logic |
| `on_quote_tick(tick)` | New quote | Tick-based strategies |
| `on_trade_tick(tick)` | New trade | Trade flow strategies |
| `on_order_event(event)` | Order update | Order state management |
| `on_position_event(event)` | Position update | Position monitoring |
| `on_data(data)` | Custom data | Alternative data handling |

### 4.3 Data Subscription

**Subscribe in `on_start()`:**

```python
def on_start(self):
    # Subscribe to bars
    self.subscribe_bars(
        instrument_id=self.instrument_id,
        bar_type=BarType.from_str("BTCUSDT.BINANCE-1-MINUTE-LAST")
    )
    
    # Subscribe to quote ticks (best bid/ask)
    self.subscribe_quote_ticks(self.instrument_id)
    
    # Subscribe to trade ticks
    self.subscribe_trade_ticks(self.instrument_id)
    
    # Subscribe to order book
    self.subscribe_order_book_deltas(self.instrument_id, depth=10)
```

### 4.4 Technical Indicators

**Built-in Indicators:**

```python
from nautilus_trader.indicators.ema import ExponentialMovingAverage
from nautilus_trader.indicators.sma import SimpleMovingAverage
from nautilus_trader.indicators.rsi import RelativeStrengthIndex
from nautilus_trader.indicators.atr import AverageTrueRange
from nautilus_trader.indicators.macd import MovingAverageConvergenceDivergence
from nautilus_trader.indicators.bollinger_bands import BollingerBands

class IndicatorStrategy(Strategy):
    def __init__(self, config):
        super().__init__(config)
        
        # Initialize indicators
        self.ema = ExponentialMovingAverage(period=20)
        self.rsi = RelativeStrengthIndex(period=14)
        self.atr = AverageTrueRange(period=14)
        self.macd = MovingAverageConvergenceDivergence(
            fast_period=12,
            slow_period=26,
            signal_period=9
        )
        self.bb = BollingerBands(period=20, k=2.0)
    
    def on_bar(self, bar: Bar):
        # Update all indicators
        self.ema.update(bar.close)
        self.rsi.update(bar.close)
        self.atr.update(bar.high, bar.low, bar.close)
        self.macd.update(bar.close)
        self.bb.update(bar.close)
        
        # Check if initialized (have enough data)
        if not self.ema.initialized:
            return
        
        # Use indicator values
        if self.rsi.value < 30 and bar.close < self.bb.lower:
            self.buy()  # Oversold + below lower band
```

**Important:** Always check `indicator.initialized` before using values!

### 4.5 Order Management

#### Placing Orders

**Market Orders (immediate execution):**
```python
from nautilus_trader.model.objects import Quantity
from decimal import Decimal

# Simple buy
self.buy(trade_size=Decimal("1.0"))

# Simple sell
self.sell(trade_size=Decimal("1.0"))

# Or with full control
from nautilus_trader.model.orders import MarketOrder

order = self.order_factory.market(
    instrument_id=self.instrument_id,
    order_side=OrderSide.BUY,
    quantity=Quantity.from_int(1)
)
self.submit_order(order)
```

**Limit Orders (specific price):**
```python
from nautilus_trader.model.objects import Price

order = self.order_factory.limit(
    instrument_id=self.instrument_id,
    order_side=OrderSide.BUY,
    quantity=Quantity.from_str("1.0"),
    price=Price.from_str("45000.00")
)
self.submit_order(order)
```

**Stop Orders (trigger at price):**
```python
order = self.order_factory.stop_market(
    instrument_id=self.instrument_id,
    order_side=OrderSide.SELL,
    quantity=Quantity.from_str("1.0"),
    trigger_price=Price.from_str("44000.00")  # Stop loss
)
self.submit_order(order)
```

#### Managing Orders

```python
# Cancel order
self.cancel_order(order)

# Modify order
self.modify_order(
    order,
    quantity=Quantity.from_str("2.0"),
    price=Price.from_str("45100.00")
)

# Cancel all orders
self.cancel_all_orders(self.instrument_id)
```

### 4.6 Position Management

**Check current position:**
```python
def on_bar(self, bar: Bar):
    # Check if flat (no position)
    if self.portfolio.is_flat(self.instrument_id):
        # No position, can enter
        self.buy()
    
    # Get current position
    position = self.portfolio.position(self.instrument_id)
    if position:
        print(f"Position: {position.quantity} @ {position.avg_px_open}")
        print(f"Unrealized PnL: {position.unrealized_pnl}")
    
    # Close position
    self.close_position(position)
    
    # Close all positions for instrument
    self.close_all_positions(self.instrument_id)
```

### 4.7 Portfolio Access

```python
def on_bar(self, bar: Bar):
    # Get account
    account = self.portfolio.account(BINANCE)
    print(f"Balance: {account.balance()}")
    
    # Get all positions
    positions = self.portfolio.positions()
    
    # Get open positions
    open_positions = self.portfolio.positions_open()
    
    # Get closed positions
    closed_positions = self.portfolio.positions_closed()
    
    # Check position exists
    has_position = self.portfolio.position_exists(self.instrument_id)
```

### 4.8 Risk Management Patterns

**Position Sizing:**
```python
from decimal import Decimal

class RiskManagedStrategy(Strategy):
    def calculate_position_size(self, account_balance, risk_percent, stop_distance):
        """
        Calculate position size based on risk
        
        risk_amount = account_balance * risk_percent
        position_size = risk_amount / stop_distance
        """
        risk_amount = account_balance * (risk_percent / 100)
        position_size = risk_amount / stop_distance
        return Decimal(str(position_size))
    
    def on_bar(self, bar: Bar):
        account = self.portfolio.account(self.venue)
        balance = float(account.balance().as_decimal())
        
        # Risk 1% per trade with 2% stop
        stop_distance = float(bar.close) * 0.02
        size = self.calculate_position_size(balance, 1.0, stop_distance)
        
        self.buy(trade_size=size)
```

**Stop Loss & Take Profit:**
```python
def on_bar(self, bar: Bar):
    # Entry order
    entry = self.order_factory.market(
        instrument_id=self.instrument_id,
        order_side=OrderSide.BUY,
        quantity=Quantity.from_str("1.0")
    )
    
    # Stop loss (2% below entry)
    stop_price = bar.close * Decimal("0.98")
    stop_loss = self.order_factory.stop_market(
        instrument_id=self.instrument_id,
        order_side=OrderSide.SELL,
        quantity=Quantity.from_str("1.0"),
        trigger_price=Price.from_str(str(stop_price))
    )
    
    # Take profit (3% above entry)
    tp_price = bar.close * Decimal("1.03")
    take_profit = self.order_factory.limit(
        instrument_id=self.instrument_id,
        order_side=OrderSide.SELL,
        quantity=Quantity.from_str("1.0"),
        price=Price.from_str(str(tp_price))
    )
    
    # Submit all orders
    self.submit_order(entry)
    self.submit_order(stop_loss)
    self.submit_order(take_profit)
```

**Maximum Loss Limit:**
```python
class MaxLossStrategy(Strategy):
    def __init__(self, config):
        super().__init__(config)
        self.max_loss_pct = Decimal("0.05")  # 5% max drawdown
        self.starting_balance = None
    
    def on_start(self):
        account = self.portfolio.account(self.venue)
        self.starting_balance = account.balance().as_decimal()
        self.subscribe_bars(self.instrument_id)
    
    def on_bar(self, bar: Bar):
        account = self.portfolio.account(self.venue)
        current_balance = account.balance().as_decimal()
        
        # Calculate drawdown
        drawdown = (self.starting_balance - current_balance) / self.starting_balance
        
        # Check max loss
        if drawdown >= self.max_loss_pct:
            self.log.error(f"Max loss exceeded: {drawdown:.2%}")
            self.close_all_positions(self.instrument_id)
            self.stop()  # Stop strategy
            return
        
        # Continue normal strategy logic...
```

---

## 5. Data Management

### 5.1 Data Requirements

For backtesting, you need historical market data in one of these formats:
- **Parquet** (recommended for production)
- **CSV** (easy for development)
- **Custom formats** (via data loaders)

### 5.2 Data Sources

**Free Sources:**
- Exchange APIs (Binance, Kraken, etc.) - Usually last 1000 candles
- [CryptoDataDownload](https://www.cryptodatadownload.com/) - Historical crypto CSV

**Paid Sources:**
- [Databento](https://databento.com/) - Professional market data
- [Tardis](https://tardis.dev/) - Crypto market replay
- Direct from exchanges - Historical data subscriptions

### 5.3 CSV Data Format

**Expected CSV format for bars:**
```csv
timestamp,open,high,low,close,volume
2024-01-01T00:00:00,45000.0,45100.0,44900.0,45050.0,10.5
2024-01-01T00:01:00,45050.0,45200.0,45000.0,45150.0,8.3
...
```

**Loading CSV data:**
```python
import pandas as pd
from nautilus_trader.model.data import Bar, BarType
from nautilus_trader.model.objects import Price, Quantity
from nautilus_trader.core.datetime import dt_to_unix_nanos

def load_bars_from_csv(filepath, instrument_id, bar_type):
    """Load bars from CSV file"""
    df = pd.read_csv(filepath)
    bars = []
    
    for _, row in df.iterrows():
        bar = Bar(
            bar_type=BarType.from_str(bar_type),
            open=Price.from_str(str(row['open'])),
            high=Price.from_str(str(row['high'])),
            low=Price.from_str(str(row['low'])),
            close=Price.from_str(str(row['close'])),
            volume=Quantity.from_str(str(row['volume'])),
            ts_event=dt_to_unix_nanos(pd.to_datetime(row['timestamp'])),
            ts_init=dt_to_unix_nanos(pd.to_datetime(row['timestamp']))
        )
        bars.append(bar)
    
    return bars

# Usage
bars = load_bars_from_csv(
    'data/BTCUSDT_1m.csv',
    'BTCUSDT.BINANCE',
    'BTCUSDT.BINANCE-1-MINUTE-LAST'
)
engine.add_data(bars)
```

### 5.4 Parquet Data Catalog

For production, use Parquet format:

**Directory structure:**
```
data/
└── catalog/
    ├── bars/
    │   ├── BTCUSDT-PERP.BINANCE.1-MINUTE-LAST.parquet
    │   └── ETHUSDT-PERP.BINANCE.5-MINUTE-LAST.parquet
    ├── quotes/
    │   └── BTCUSDT-PERP.BINANCE.parquet
    └── trades/
        └── BTCUSDT-PERP.BINANCE.parquet
```

**Creating Parquet from CSV:**
```python
import pandas as pd

# Read CSV
df = pd.read_csv('BTCUSDT_1m.csv')

# Convert timestamp to datetime
df['timestamp'] = pd.to_datetime(df['timestamp'])

# Save as Parquet
df.to_parquet('data/catalog/bars/BTCUSDT-PERP.BINANCE.1-MINUTE-LAST.parquet')
```

### 5.5 Data Validation

**Always validate your data:**

```python
def validate_bars(bars):
    """Validate bar data quality"""
    issues = []
    
    for i, bar in enumerate(bars):
        # Check OHLC relationship
        if bar.high < max(bar.open, bar.close):
            issues.append(f"Bar {i}: High < max(open, close)")
        
        if bar.low > min(bar.open, bar.close):
            issues.append(f"Bar {i}: Low > min(open, close)")
        
        # Check for zero volume
        if bar.volume == 0:
            issues.append(f"Bar {i}: Zero volume")
        
        # Check timestamps
        if i > 0 and bar.ts_event <= bars[i-1].ts_event:
            issues.append(f"Bar {i}: Timestamp not increasing")
    
    if issues:
        print("⚠️  Data validation issues:")
        for issue in issues:
            print(f"  - {issue}")
    else:
        print("✅ Data validation passed")
    
    return len(issues) == 0

# Usage
if validate_bars(bars):
    engine.add_data(bars)
else:
    print("Fix data issues before running backtest")
```

### 5.6 Handling Missing Data

**Gap detection:**
```python
def detect_gaps(bars, expected_interval_seconds):
    """Detect gaps in time series data"""
    gaps = []
    
    for i in range(1, len(bars)):
        time_diff = (bars[i].ts_event - bars[i-1].ts_event) / 1_000_000_000  # Convert to seconds
        
        if time_diff > expected_interval_seconds * 1.5:  # Allow 50% tolerance
            gaps.append({
                'index': i,
                'start': bars[i-1].ts_event,
                'end': bars[i].ts_event,
                'duration_seconds': time_diff
            })
    
    return gaps

# Check for gaps in 1-minute bars
gaps = detect_gaps(bars, expected_interval_seconds=60)
if gaps:
    print(f"Found {len(gaps)} gaps in data")
    for gap in gaps[:5]:  # Show first 5
        print(f"  Gap at index {gap['index']}: {gap['duration_seconds']/60:.1f} minutes")
```

---

## 6. Backtesting Workflows

### 6.1 Low-Level Backtesting (BacktestEngine)

**Complete example:**

```python
from decimal import Decimal
from nautilus_trader.backtest.engine import BacktestEngine
from nautilus_trader.backtest.models import FillModel
from nautilus_trader.model.currencies import USD, BTC
from nautilus_trader.model.enums import AccountType, OMSType
from nautilus_trader.model.identifiers import Venue
from nautilus_trader.model.objects import Money
from nautilus_trader.model.instruments import CryptoPerpetual

# 1. Create engine
engine = BacktestEngine()

# 2. Configure venue
BINANCE = Venue("BINANCE")
engine.add_venue(
    venue=BINANCE,
    oms_type=OMSType.NETTING,
    account_type=AccountType.MARGIN,
    base_currency=USD,
    starting_balances=[Money(100_000, USD)]
)

# 3. Add instrument
btcusdt = CryptoPerpetual(
    id=InstrumentId.from_str("BTCUSDT-PERP.BINANCE"),
    native_symbol="BTCUSDT",
    base_currency=BTC,
    quote_currency=USD,
    settlement_currency=USD,
    price_precision=2,
    size_precision=3,
    maker_fee=Decimal("0.0002"),
    taker_fee=Decimal("0.0004"),
    # ... other parameters
)
engine.add_instrument(btcusdt)

# 4. Load data
bars = load_bars_from_csv('data/BTCUSDT_1m.csv', btcusdt.id, 'BTCUSDT-PERP.BINANCE-1-MINUTE-LAST')
engine.add_data(bars)

# 5. Add strategy
config = MyStrategyConfig(
    instrument_id=str(btcusdt.id),
    parameter1=10
)
strategy = MyStrategy(config=config)
engine.add_strategy(strategy)

# 6. Run backtest
engine.run()

# 7. Analyze results
print("=" * 80)
print("BACKTEST RESULTS")
print("=" * 80)

account = engine.trader.generate_account_report(BINANCE)
print(account)

fills = engine.trader.generate_order_fills_report()
print(fills)

positions = engine.trader.generate_positions_report()
print(positions)
```

### 6.2 High-Level Backtesting (BacktestNode)

**For production-ready backtests:**

```python
from nautilus_trader.backtest.node import BacktestNode, BacktestNodeConfig
from nautilus_trader.config import BacktestDataConfig, BacktestEngineConfig, BacktestRunConfig
from nautilus_trader.persistence.catalog import ParquetDataCatalog

# 1. Configure data catalog
data_config = BacktestDataConfig(
    catalog_path="data/catalog",
    data_cls=Bar,
    instrument_id="BTCUSDT-PERP.BINANCE",
    start_time="2024-01-01",
    end_time="2024-03-31"
)

# 2. Configure engine
engine_config = BacktestEngineConfig(
    strategies=[{
        "strategy_cls": MyStrategy,
        "config": {
            "instrument_id": "BTCUSDT-PERP.BINANCE",
            "parameter1": 10
        }
    }]
)

# 3. Configure run
run_config = BacktestRunConfig(
    engine=engine_config,
    data=data_config,
    venues=[{
        "name": "BINANCE",
        "oms_type": "NETTING",
        "account_type": "MARGIN",
        "base_currency": "USD",
        "starting_balances": ["100000 USD"]
    }]
)

# 4. Create and run node
node = BacktestNode(config=run_config)
results = node.run()

# 5. Analyze results
print(results)
```

### 6.3 Performance Metrics

**Key metrics to analyze:**

```python
def analyze_performance(engine):
    """Calculate comprehensive performance metrics"""
    
    # Get all filled orders
    fills = engine.trader.generate_order_fills_report()
    
    # Calculate metrics
    total_trades = len(fills)
    winning_trades = len([f for f in fills if f.realized_pnl > 0])
    losing_trades = len([f for f in fills if f.realized_pnl < 0])
    
    win_rate = winning_trades / total_trades if total_trades > 0 else 0
    
    # PnL metrics
    total_pnl = sum(f.realized_pnl for f in fills)
    avg_win = sum(f.realized_pnl for f in fills if f.realized_pnl > 0) / winning_trades if winning_trades > 0 else 0
    avg_loss = sum(f.realized_pnl for f in fills if f.realized_pnl < 0) / losing_trades if losing_trades > 0 else 0
    
    # Risk metrics
    profit_factor = abs(avg_win / avg_loss) if avg_loss != 0 else float('inf')
    
    print("=" * 80)
    print("PERFORMANCE METRICS")
    print("=" * 80)
    print(f"Total Trades: {total_trades}")
    print(f"Winning Trades: {winning_trades}")
    print(f"Losing Trades: {losing_trades}")
    print(f"Win Rate: {win_rate:.2%}")
    print(f"Total PnL: ${total_pnl:,.2f}")
    print(f"Average Win: ${avg_win:,.2f}")
    print(f"Average Loss: ${avg_loss:,.2f}")
    print(f"Profit Factor: {profit_factor:.2f}")
    print("=" * 80)

# Usage
analyze_performance(engine)
```

### 6.4 Parameter Optimization

**Grid search example:**

```python
def run_parameter_optimization(param_grid):
    """
    Run backtests with different parameters
    
    param_grid = {
        'fast_period': [5, 10, 15],
        'slow_period': [20, 30, 40]
    }
    """
    results = []
    
    for fast in param_grid['fast_period']:
        for slow in param_grid['slow_period']:
            print(f"Testing: fast={fast}, slow={slow}")
            
            # Create engine
            engine = BacktestEngine()
            # ... setup engine ...
            
            # Add strategy with parameters
            config = EMACrossConfig(
                instrument_id="BTCUSDT-PERP.BINANCE",
                fast_period=fast,
                slow_period=slow
            )
            strategy = EMACrossStrategy(config=config)
            engine.add_strategy(strategy)
            
            # Run
            engine.run()
            
            # Get performance
            account = engine.trader.generate_account_report(BINANCE)
            pnl = account.total_pnl()
            
            results.append({
                'fast_period': fast,
                'slow_period': slow,
                'pnl': pnl
            })
    
    # Sort by PnL
    results.sort(key=lambda x: x['pnl'], reverse=True)
    
    print("\n" + "=" * 80)
    print("OPTIMIZATION RESULTS")
    print("=" * 80)
    for r in results[:5]:  # Top 5
        print(f"Fast={r['fast_period']}, Slow={r['slow_period']}: PnL=${r['pnl']:,.2f}")
    
    return results

# Run optimization
param_grid = {
    'fast_period': [5, 10, 15, 20],
    'slow_period': [20, 30, 40, 50]
}
results = run_parameter_optimization(param_grid)
```

**Warning:** Beware of overfitting! Always validate on out-of-sample data.

---

## 7. Paper Trading Setup

### 7.1 What is Paper Trading?

Paper trading lets you:
- ✅ Test strategies with **real-time market data**
- ✅ No real money at risk (simulated account)
- ✅ Validate strategy logic in live conditions
- ✅ Test order execution and timing
- ✅ Identify bugs before production

**When to paper trade:**
- After backtesting shows promise
- Before risking real capital
- To validate execution logic
- To test exchange connectivity

**How long?** Minimum 1-2 weeks, ideally 1 month

### 7.2 Exchange API Setup

**Step 1: Create Exchange Account**

For testnet (recommended):
- Binance Testnet: https://testnet.binance.vision/
- Bybit Testnet: https://testnet.bybit.com/
- OKX Demo: https://www.okx.com/demo-trading

**Step 2: Generate API Keys**

1. Log into exchange
2. Go to API Management
3. Create new API key
4. **Enable:** Read, Trade (for paper trading)
5. **Disable:** Withdrawals (security)
6. **Save:** API Key and Secret securely

**Step 3: Configure Environment Variables**

Create `.env` file:
```bash
# Exchange API Keys
BINANCE_API_KEY=your_api_key_here
BINANCE_API_SECRET=your_api_secret_here

# Optional: Testnet
BINANCE_TESTNET=true
```

**Load in Python:**
```python
import os
from dotenv import load_dotenv

load_dotenv()

api_key = os.getenv('BINANCE_API_KEY')
api_secret = os.getenv('BINANCE_API_SECRET')
```

### 7.3 TradingNode Configuration

**Create paper trading config:**

```python
from nautilus_trader.live.node import TradingNode, TradingNodeConfig
from nautilus_trader.adapters.binance.config import BinanceDataConfig, BinanceExecConfig

# Configure data client
data_config = BinanceDataConfig(
    api_key=os.getenv('BINANCE_API_KEY'),
    api_secret=os.getenv('BINANCE_API_SECRET'),
    testnet=True,  # Use testnet
    instrument_ids=["BTCUSDT.BINANCE"]
)

# Configure execution client
exec_config = BinanceExecConfig(
    api_key=os.getenv('BINANCE_API_KEY'),
    api_secret=os.getenv('BINANCE_API_SECRET'),
    testnet=True,
    account_type="cash"  # or "margin"
)

# Configure trading node
node_config = TradingNodeConfig(
    data_clients={
        "BINANCE": data_config
    },
    exec_clients={
        "BINANCE": exec_config
    },
    strategies=[{
        "strategy_cls": MyStrategy,
        "config": {
            "instrument_id": "BTCUSDT.BINANCE",
            "parameter1": 10
        }
    }],
    timeout_connection=30.0,
    timeout_reconciliation=10.0,
    timeout_portfolio=10.0,
    timeout_disconnection=10.0
)

# Create node
node = TradingNode(config=node_config)
```

### 7.4 Running Paper Trading

**Start trading node:**

```python
# start_paper_trading.py
import asyncio
from nautilus_trader.live.node import TradingNode

async def main():
    # Create and build node
    node = TradingNode(config=node_config)
    await node.build()
    
    # Start node
    await node.start()
    
    try:
        # Run until interrupted
        await asyncio.sleep(float('inf'))
    except KeyboardInterrupt:
        print("\nStopping trading node...")
    finally:
        # Stop node
        await node.stop()
        await node.dispose()

if __name__ == "__main__":
    asyncio.run(main())
```

**Run it:**
```bash
python start_paper_trading.py
```

**To stop:** Press `Ctrl+C`

### 7.5 Monitoring Paper Trading

**What to monitor:**

1. **Strategy Status**
   - Is strategy receiving data?
   - Are indicators updating?
   - Are signals generating?

2. **Order Execution**
   - Orders submitting successfully?
   - Fill prices reasonable?
   - Any rejected orders?

3. **Position Management**
   - Positions opening/closing correctly?
   - P&L calculating properly?
   - Risk limits working?

4. **System Health**
   - Connection stable?
   - Latency acceptable?
   - Error rate low?

**Logging example:**
```python
import logging

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('paper_trading.log'),
        logging.StreamHandler()  # Also print to console
    ]
)

# In your strategy
class MyStrategy(Strategy):
    def on_bar(self, bar: Bar):
        self.log.info(f"Received bar: close={bar.close}")
        
    def on_order_event(self, event: OrderEvent):
        self.log.info(f"Order event: {event}")
```

### 7.6 Paper Trading Checklist

Before starting paper trading:

- [ ] Strategy backtested successfully
- [ ] Exchange API keys configured
- [ ] Using testnet/sandbox (not real money)
- [ ] Logging configured
- [ ] Monitoring plan in place
- [ ] Emergency stop procedure defined
- [ ] Risk limits set
- [ ] Test small position sizes first

During paper trading:

- [ ] Check logs daily
- [ ] Monitor positions
- [ ] Track P&L
- [ ] Watch for errors
- [ ] Verify order execution
- [ ] Compare to backtest performance

---

## 8. Production Infrastructure

### 8.1 Infrastructure Overview

For live trading, you need:

```
┌──────────────────────────────────────────────┐
│         Your Trading Strategy                │
│         (Python + Nautilus)                  │
└────┬─────────────────────────┬───────────────┘
     │                         │
     ▼                         ▼
┌─────────────┐        ┌──────────────────┐
│  Database   │        │  Cache (Redis)   │
│ (PostgreSQL)│        │  - Market data   │
│ - Orders    │        │  - Positions     │
│ - Positions │        └──────────────────┘
│ - Portfolio │
└─────────────┘
     │
     ▼
┌─────────────────────────────────────────────┐
│         Monitoring & Alerting               │
│    (Prometheus + Grafana + Alertmanager)    │
└─────────────────────────────────────────────┘
```

### 8.2 Docker Compose Setup

**Create `docker-compose.yml`:**

```yaml
version: '3.8'

services:
  # PostgreSQL Database
  postgres:
    image: postgres:15
    container_name: nautilus_postgres
    environment:
      POSTGRES_DB: nautilus
      POSTGRES_USER: nautilus
      POSTGRES_PASSWORD: ${POSTGRES_PASSWORD}
    ports:
      - "5432:5432"
    volumes:
      - postgres_data:/var/lib/postgresql/data
      - ./init.sql:/docker-entrypoint-initdb.d/init.sql
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U nautilus"]
      interval: 10s
      timeout: 5s
      retries: 5

  # Redis Cache
  redis:
    image: redis:7-alpine
    container_name: nautilus_redis
    ports:
      - "6379:6379"
    volumes:
      - redis_data:/data
    healthcheck:
      test: ["CMD", "redis-cli", "ping"]
      interval: 10s
      timeout: 3s
      retries: 5

  # Prometheus Monitoring
  prometheus:
    image: prom/prometheus:latest
    container_name: nautilus_prometheus
    ports:
      - "9090:9090"
    volumes:
      - ./prometheus/prometheus.yml:/etc/prometheus/prometheus.yml
      - prometheus_data:/prometheus
    command:
      - '--config.file=/etc/prometheus/prometheus.yml'
      - '--storage.tsdb.path=/prometheus'

  # Grafana Dashboards
  grafana:
    image: grafana/grafana:latest
    container_name: nautilus_grafana
    ports:
      - "3000:3000"
    environment:
      - GF_SECURITY_ADMIN_PASSWORD=${GRAFANA_PASSWORD}
    volumes:
      - grafana_data:/var/lib/grafana
      - ./grafana/dashboards:/etc/grafana/provisioning/dashboards
      - ./grafana/datasources:/etc/grafana/provisioning/datasources
    depends_on:
      - prometheus

volumes:
  postgres_data:
  redis_data:
  prometheus_data:
  grafana_data:
```

**Start infrastructure:**
```bash
docker-compose up -d
```

### 8.3 PostgreSQL Configuration

**Create `init.sql`:**

```sql
-- Create schema for Nautilus
CREATE SCHEMA IF NOT EXISTS nautilus;

-- Orders table
CREATE TABLE nautilus.orders (
    id UUID PRIMARY KEY,
    strategy_id VARCHAR(255) NOT NULL,
    instrument_id VARCHAR(255) NOT NULL,
    order_side VARCHAR(10) NOT NULL,
    order_type VARCHAR(50) NOT NULL,
    quantity DECIMAL(20, 8) NOT NULL,
    price DECIMAL(20, 8),
    trigger_price DECIMAL(20, 8),
    status VARCHAR(50) NOT NULL,
    filled_qty DECIMAL(20, 8) DEFAULT 0,
    avg_px DECIMAL(20, 8),
    created_at TIMESTAMPTZ NOT NULL,
    updated_at TIMESTAMPTZ NOT NULL,
    filled_at TIMESTAMPTZ
);

-- Positions table
CREATE TABLE nautilus.positions (
    id UUID PRIMARY KEY,
    strategy_id VARCHAR(255) NOT NULL,
    instrument_id VARCHAR(255) NOT NULL,
    side VARCHAR(10) NOT NULL,
    quantity DECIMAL(20, 8) NOT NULL,
    avg_px_open DECIMAL(20, 8) NOT NULL,
    avg_px_close DECIMAL(20, 8),
    realized_pnl DECIMAL(20, 2),
    unrealized_pnl DECIMAL(20, 2),
    opened_at TIMESTAMPTZ NOT NULL,
    closed_at TIMESTAMPTZ,
    status VARCHAR(50) NOT NULL
);

-- Portfolio snapshots
CREATE TABLE nautilus.portfolio_snapshots (
    id SERIAL PRIMARY KEY,
    timestamp TIMESTAMPTZ NOT NULL,
    account_id VARCHAR(255) NOT NULL,
    balance DECIMAL(20, 2) NOT NULL,
    margin_used DECIMAL(20, 2),
    margin_available DECIMAL(20, 2),
    unrealized_pnl DECIMAL(20, 2),
    realized_pnl DECIMAL(20, 2)
);

-- Create indexes
CREATE INDEX idx_orders_strategy ON nautilus.orders(strategy_id);
CREATE INDEX idx_orders_instrument ON nautilus.orders(instrument_id);
CREATE INDEX idx_orders_created ON nautilus.orders(created_at);
CREATE INDEX idx_positions_strategy ON nautilus.positions(strategy_id);
CREATE INDEX idx_positions_instrument ON nautilus.positions(instrument_id);
CREATE INDEX idx_portfolio_timestamp ON nautilus.portfolio_snapshots(timestamp);
```

**Connect from Nautilus:**

```python
from nautilus_trader.persistence.sql import PostgresAdapter

# Configure database connection
db_config = {
    'host': 'localhost',
    'port': 5432,
    'database': 'nautilus',
    'user': 'nautilus',
    'password': os.getenv('POSTGRES_PASSWORD')
}

# Create adapter
db_adapter = PostgresAdapter(config=db_config)
```

### 8.4 Redis Configuration

**Connect from Nautilus:**

```python
import redis

# Create Redis client
redis_client = redis.Redis(
    host='localhost',
    port=6379,
    decode_responses=True
)

# Cache market data
def cache_latest_price(instrument_id, price):
    redis_client.setex(
        f"price:{instrument_id}",
        60,  # TTL 60 seconds
        str(price)
    )

# Get cached price
def get_cached_price(instrument_id):
    price = redis_client.get(f"price:{instrument_id}")
    return Decimal(price) if price else None
```

### 8.5 Prometheus Monitoring

**Create `prometheus/prometheus.yml`:**

```yaml
global:
  scrape_interval: 15s
  evaluation_interval: 15s

scrape_configs:
  - job_name: 'nautilus'
    static_configs:
      - targets: ['host.docker.internal:8000']  # Your Nautilus metrics endpoint
```

**Expose metrics from Nautilus:**

```python
from prometheus_client import start_http_server, Counter, Gauge, Histogram

# Define metrics
orders_total = Counter('nautilus_orders_total', 'Total orders submitted', ['strategy', 'side'])
positions_open = Gauge('nautilus_positions_open', 'Number of open positions', ['strategy'])
pnl_total = Gauge('nautilus_pnl_total', 'Total PnL', ['strategy'])
order_latency = Histogram('nautilus_order_latency_seconds', 'Order submission latency')

# Start metrics server
start_http_server(8000)

# Update metrics in strategy
class MyStrategy(Strategy):
    def on_order_event(self, event: OrderEvent):
        if event.event_type == OrderEventType.FILLED:
            orders_total.labels(
                strategy=self.id,
                side=event.order_side
            ).inc()
```

### 8.6 Grafana Dashboards

**Create `grafana/datasources/prometheus.yml`:**

```yaml
apiVersion: 1

datasources:
  - name: Prometheus
    type: prometheus
    access: proxy
    url: http://prometheus:9090
    isDefault: true
```

**Access Grafana:**
1. Open http://localhost:3000
2. Login (admin / your_password)
3. Create dashboard
4. Add panels for:
   - Total orders
   - Open positions
   - P&L over time
   - Order latency
   - Error rate

---

## 9. Production Deployment

### 9.1 Pre-Deployment Checklist

**Code Quality:**
- [ ] All tests passing
- [ ] Code reviewed
- [ ] No hardcoded secrets
- [ ] Logging configured
- [ ] Error handling comprehensive

**Strategy Validation:**
- [ ] Backtested on historical data
- [ ] Paper traded for minimum 2 weeks
- [ ] Performance meets expectations
- [ ] Risk limits verified
- [ ] Edge cases tested

**Infrastructure:**
- [ ] Database setup and tested
- [ ] Redis cache configured
- [ ] Monitoring dashboards created
- [ ] Alerts configured
- [ ] Backup strategy in place

**Security:**
- [ ] API keys secured (environment variables)
- [ ] Database credentials secured
- [ ] Network access restricted
- [ ] Audit logging enabled

**Operations:**
- [ ] Runbook created
- [ ] On-call schedule defined
- [ ] Incident response plan
- [ ] Rollback procedure tested

### 9.2 Deployment Process

**Step 1: Final Testing**

```bash
# Run all tests
pytest tests/

# Run paper trading one more time
python start_paper_trading.py
```

**Step 2: Deploy Infrastructure**

```bash
# Start infrastructure services
docker-compose -f docker-compose.prod.yml up -d

# Verify services
docker-compose ps
```

**Step 3: Deploy Strategy Code**

```bash
# Copy code to production server
scp -r ./strategy_code user@prod-server:/opt/nautilus/

# SSH to server
ssh user@prod-server

# Activate environment
cd /opt/nautilus
source nautilus_env/bin/activate

# Install dependencies
pip install -r requirements.txt
```

**Step 4: Configure for Production**

```python
# production_config.py
from nautilus_trader.live.node import TradingNodeConfig

config = TradingNodeConfig(
    # Use PRODUCTION API keys (not testnet)
    data_clients={
        "BINANCE": BinanceDataConfig(
            api_key=os.getenv('BINANCE_PROD_API_KEY'),
            api_secret=os.getenv('BINANCE_PROD_API_SECRET'),
            testnet=False,  # IMPORTANT: Production mode
            instrument_ids=["BTCUSDT.BINANCE"]
        )
    },
    exec_clients={
        "BINANCE": BinanceExecConfig(
            api_key=os.getenv('BINANCE_PROD_API_KEY'),
            api_secret=os.getenv('BINANCE_PROD_API_SECRET'),
            testnet=False,  # IMPORTANT: Production mode
            account_type="cash"
        )
    },
    strategies=[{
        "strategy_cls": MyStrategy,
        "config": {
            "instrument_id": "BTCUSDT.BINANCE",
            # START WITH SMALL SIZE
            "trade_size": "0.001"  # Very small for initial production run
        }
    }],
    # Production-specific settings
    log_level="INFO",
    save_state=True,
    database_config=db_config,
    cache_config=redis_config
)
```

**Step 5: Start Production Strategy**

```bash
# Use process manager (systemd, supervisor, or screen)
screen -S nautilus
python start_production.py

# Detach: Ctrl+A, then D
```

**Step 6: Verify Deployment**

```bash
# Check logs
tail -f production.log

# Check process
ps aux | grep python

# Check connections
netstat -an | grep ESTABLISHED

# Verify in Grafana
open http://your-server:3000
```

### 9.3 Risk Management in Production

**Position Limits:**

```python
class ProductionStrategy(Strategy):
    def __init__(self, config):
        super().__init__(config)
        # Hard limits
        self.max_position_size = Decimal("1.0")  # Max 1 BTC
        self.max_open_positions = 3
        self.max_daily_loss = Decimal("1000.0")  # Max $1000 loss per day
        
        # Track daily stats
        self.daily_pnl = Decimal("0")
        self.trade_count_today = 0
    
    def on_bar(self, bar: Bar):
        # Check daily loss limit
        if self.daily_pnl <= -self.max_daily_loss:
            self.log.error("Daily loss limit reached. Stopping strategy.")
            self.close_all_positions(self.instrument_id)
            self.stop()
            return
        
        # Check position count
        if len(self.portfolio.positions_open()) >= self.max_open_positions:
            self.log.warning("Max open positions reached. Skipping trade.")
            return
        
        # Continue normal logic...
```

**Circuit Breaker:**

```python
class CircuitBreaker:
    def __init__(self, max_errors=5, reset_time=300):
        self.max_errors = max_errors
        self.reset_time = reset_time  # seconds
        self.error_count = 0
        self.last_error_time = None
        self.is_open = False
    
    def record_error(self):
        self.error_count += 1
        self.last_error_time = time.time()
        
        if self.error_count >= self.max_errors:
            self.is_open = True
            logging.error("Circuit breaker OPEN - too many errors")
    
    def can_trade(self):
        if not self.is_open:
            return True
        
        # Check if we should reset
        if time.time() - self.last_error_time > self.reset_time:
            self.reset()
            return True
        
        return False
    
    def reset(self):
        self.error_count = 0
        self.is_open = False
        logging.info("Circuit breaker RESET")

# Use in strategy
circuit_breaker = CircuitBreaker()

def on_order_event(self, event: OrderEvent):
    if event.event_type == OrderEventType.REJECTED:
        circuit_breaker.record_error()

def on_bar(self, bar: Bar):
    if not circuit_breaker.can_trade():
        self.log.warning("Circuit breaker open - not trading")
        return
    
    # Normal trading logic...
```

### 9.4 Operational Procedures

**Daily Checklist:**
- [ ] Check Grafana dashboards
- [ ] Review overnight logs
- [ ] Verify all positions
- [ ] Check P&L
- [ ] Ensure no alerts fired
- [ ] Verify data feed health

**Weekly Review:**
- [ ] Analyze weekly performance
- [ ] Review all trades
- [ ] Check for unexpected behavior
- [ ] Update strategy parameters if needed
- [ ] Review and clear logs
- [ ] Backup database

**Monthly Tasks:**
- [ ] Full performance review
- [ ] Risk analysis
- [ ] Infrastructure health check
- [ ] Security audit
- [ ] Update dependencies
- [ ] Review and optimize costs

### 9.5 Incident Response

**If something goes wrong:**

1. **Stop Trading Immediately**
```bash
# Kill process
pkill -f "python start_production.py"

# Or use emergency stop script
python emergency_stop.py
```

2. **Close All Positions**
```python
# emergency_stop.py
from nautilus_trader.live.node import TradingNode

async def emergency_stop():
    node = TradingNode(config=config)
    await node.build()
    
    # Close all positions
    for strategy in node.trader.strategies():
        strategy.close_all_positions()
    
    # Cancel all orders
    for strategy in node.trader.strategies():
        strategy.cancel_all_orders()
    
    await node.stop()

asyncio.run(emergency_stop())
```

3. **Investigate**
- Check logs
- Review recent trades
- Check exchange account
- Verify positions closed

4. **Document**
- What happened?
- What was the impact?
- What caused it?
- How to prevent it?

5. **Fix and Re-deploy**
- Fix the issue
- Test thoroughly
- Deploy fix
- Monitor closely

---

## 10. Troubleshooting & FAQ

### 10.1 Installation Issues

**Q: `ImportError: No module named 'nautilus_trader'`**

A: Virtual environment not activated or package not installed
```bash
source nautilus_env/bin/activate
pip install nautilus_trader
```

**Q: Rust compiler errors during installation**

A: Need to install Rust toolchain
```bash
curl --proto '=https' --tlsv1.2 -sSf https://sh.rustup.rs | sh
source $HOME/.cargo/env
```

**Q: `error: failed to compile nautilus_trader`**

A: Try installing from wheel instead of source
```bash
pip install nautilus_trader --no-build-isolation
```

### 10.2 Strategy Issues

**Q: Indicators not updating**

A: Check if indicators are initialized before using
```python
def on_bar(self, bar: Bar):
    self.ema.update(bar.close)
    
    if not self.ema.initialized:
        self.log.warning("Indicator not ready yet")
        return
    
    # Now safe to use self.ema.value
```

**Q: Orders not executing**

A: Check several things:
```python
# 1. Is portfolio flat?
if not self.portfolio.is_flat(self.instrument_id):
    self.log.info("Already have position")
    
# 2. Are you subscribed to data?
def on_start(self):
    self.subscribe_bars(self.instrument_id)

# 3. Check account balance
account = self.portfolio.account(venue)
self.log.info(f"Balance: {account.balance()}")
```

**Q: Position sizes wrong**

A: Ensure quantity is Decimal type
```python
# Wrong
self.buy(trade_size=1.0)  # Float

# Correct
from decimal import Decimal
self.buy(trade_size=Decimal("1.0"))
```

### 10.3 Data Issues

**Q: Timestamp errors in data**

A: Ensure timestamps are UnixNanos
```python
from nautilus_trader.core.datetime import dt_to_unix_nanos
import pandas as pd

ts = dt_to_unix_nanos(pd.to_datetime("2024-01-01"))
```

**Q: Bars not matching expected times**

A: Check bar aggregation and timezone
```python
# Verify bar type
bar_type = BarType.from_str("BTCUSDT.BINANCE-1-MINUTE-LAST")
print(f"Bar spec: {bar_type.spec}")
```

**Q: Missing data gaps**

A: Use gap detection (see Section 5.6) and fill or skip gaps

### 10.4 Performance Issues

**Q: Backtests running slowly**

A: Optimize data loading and strategy logic
```python
# Use Parquet instead of CSV
# Reduce logging verbosity
# Vectorize calculations where possible
```

**Q: High memory usage**

A: Don't store all bars in memory
```python
# Instead of:
self.all_bars = []
def on_bar(self, bar):
    self.all_bars.append(bar)  # Memory leak!

# Do:
def on_bar(self, bar):
    # Process bar immediately, don't store
    self.process_bar(bar)
```

### 10.5 Production Issues

**Q: Connection dropping**

A: Implement reconnection logic
```python
# Nautilus handles this automatically with TradingNode
# But you can monitor connection status
def on_event(self, event):
    if isinstance(event, DisconnectedEvent):
        self.log.error("Connection lost!")
```

**Q: API rate limits**

A: Reduce API calls or increase intervals
```python
# Subscribe to less frequent bars
bar_type = BarType.from_str("BTCUSDT.BINANCE-5-MINUTE-LAST")  # Instead of 1-minute
```

**Q: Orders rejected by exchange**

A: Check logs for rejection reason
```python
def on_order_event(self, event: OrderEvent):
    if event.event_type == OrderEventType.REJECTED:
        self.log.error(f"Order rejected: {event.reason}")
        # Common reasons:
        # - Insufficient balance
        # - Invalid price
        # - Position limit exceeded
        # - Market closed
```

---

## 11. Resources & Next Steps

### 11.1 Official Documentation

- **Main Docs**: https://nautilustrader.io/docs/
- **API Reference**: https://nautilustrader.io/docs/api_reference/
- **GitHub**: https://github.com/nautechsystems/nautilus_trader
- **Discord Community**: https://discord.gg/nautilustrader

### 11.2 Learning Resources

**Tutorials:**
- `/tutorials/` in Nautilus repository
- Step-by-step examples
- Various difficulty levels

**Example Strategies:**
- `/nautilus_trader/examples/strategies/`
- Production-quality reference implementations

**Documentation:**
- Concepts guide
- Developer guide
- Integration guides

### 11.3 Next Steps

**After completing this playbook:**

1. **Build Your Own Strategy**
   - Start with simple idea
   - Backtest thoroughly
   - Paper trade extensively
   - Deploy carefully

2. **Join the Community**
   - Discord for questions
   - GitHub for issues
   - Share your learnings

3. **Advanced Topics**
   - Multi-strategy portfolios
   - Custom adapters
   - Performance optimization
   - Machine learning integration

4. **Keep Learning**
   - Read research papers
   - Study other strategies
   - Experiment with ideas
   - Track your progress

### 11.4 Contributing

**Want to contribute to Nautilus?**
- Report bugs on GitHub
- Suggest features
- Submit pull requests
- Improve documentation

### 11.5 Final Tips

**Remember:**
- Start small and simple
- Test everything thoroughly
- Never risk more than you can afford to lose
- Keep learning and improving
- Trading is risky - be careful!

**Success Factors:**
- Disciplined risk management
- Thorough testing
- Continuous monitoring
- Learning from mistakes
- Patience and persistence

---

## Conclusion

Congratulations! You now have a comprehensive understanding of Nautilus Trader from installation to production deployment.

**Your Journey:**
1. ✅ Understand architecture
2. ✅ Install and verify
3. ✅ Build first strategy
4. ✅ Master strategy patterns
5. ✅ Manage data properly
6. ✅ Run backtests
7. ✅ Paper trade safely
8. ✅ Deploy to production

**Remember:** Algorithmic trading is challenging. Success requires:
- Technical skill (you're building this)
- Risk management (essential)
- Patience (markets are unpredictable)
- Continuous learning (markets evolve)

**Good luck with your trading journey!** 🚀

---

*This playbook is a living document. Nautilus Trader evolves, and so should your knowledge. Keep this guide updated as you learn new patterns and best practices.*

---

## 12. Phase 5 – Documentation & Handoff (AI-Adaptive Infrastructure)

Phase 5 captures everything you need to wrap up the AI-Adaptive infrastructure work so future teammates can operate it confidently. Treat this section as a **guided checklist**: it explains what is happening, why it matters, how to run the supporting commands, and what to prepare next.

### 12.1 Why Documentation & Handoff Matter

- **Shared understanding** – newcomers can follow the same ritual to bring the monitoring stack online.
- **Reproducibility** – runbooks, dashboard exports, and validation logs make each deployment auditable.
- **Faster onboarding** – a single place that tells people *what to do*, *where to look*, and *how to verify*.

### 12.2 System-at-a-Glance

```mermaid
flowchart LR
    subgraph Strategy Layer
        A[AI-Adaptive Strategy]
    end
    subgraph Persistence & Cache
        B[(PostgreSQL ai_extensions)]
        C[(Redis Cache)]
    end
    subgraph Observability
        D>Metrics Exporter (9100)]
        E((Prometheus))
        F[[Grafana Dashboards]]
        G{{Alert Rules}}
    end

    A --> B
    A --> C
    A --> D
    D --> E --> F
    E --> G
    F -->|Dashboards & Docs| H[Team]
    G -->|Notifications| H
```

### 12.3 Prepare the Environment

All credentials (Postgres, Redis, Grafana) already live in `infrastructure/.env.local`. Load them into your shell before running commands:

```bash
# Always work from the project root
cd /home/ajk/Nautilus/nautilus_trader

# Export secrets for this shell (never commit them!)
set -a
source infrastructure/.env.local
set +a
```

> **Tip:** If you only need a few values, export them ad-hoc: `export DB_PASSWORD="$DB_PASSWORD"`.

### 12.4 Step-by-Step Execution

1. **Launch or verify core services**
   ```bash
   docker compose --env-file infrastructure/.env.local up -d postgres redis prometheus grafana
   docker compose ps
   ```
   Confirm Postgres (`pg_isready`) and Redis (`redis-cli -a "$REDIS_PASSWORD" ping`) report `ready` / `PONG`.

2. **Start the metrics exporter** (runs alongside strategy tooling)
   ```bash
   DB_HOST=localhost \
   DB_PORT=5435 \
   DB_USER=nautilus \
   DB_PASSWORD="$DB_PASSWORD" \
   REDIS_HOST=localhost \
   REDIS_PORT=6378 \
   REDIS_PASSWORD="$REDIS_PASSWORD" \
   AI_METRICS_PORT=9100 \
   python -m ajk_strategies.monitoring.metrics_server
   ```
   Keep this running while you validate Prometheus.

3. **Confirm Prometheus scrape success**
   - Open `http://localhost:9090` → **Status › Targets** → ensure `ai-adaptive-metrics` is `UP`.
   - Run query `up{job="ai-adaptive-metrics"}`; expect `1`.

4. **Snapshot Grafana dashboards**
   - Log in at `http://localhost:3000`.
   - Create/refresh panels for: Executive Overview, Strategy Performance, ML Optimisation, Regime Analysis, Pattern Detection, Risk, Sentiment, Trade Analysis.
   - Export JSON: Dashboard → **Share** → **Export** → **View JSON** → save into `infrastructure/monitoring/grafana/<name>.json`.

5. **Document verification**
   - Record SQL checks (examples below) and Prometheus queries in `ai-working/database_Infra layer/implementation.md`.
   ```bash
   docker exec -it nautilus_postgres psql -U nautilus -d nautilus_trader -c "SELECT * FROM ai_extensions.v_backtest_performance LIMIT 5;"
   docker exec -it nautilus_postgres psql -U nautilus -d nautilus_trader -c "SELECT COUNT(*) FROM ai_extensions.backtest_runs;"
   ```
   - Update `INFRASTRUCTURE_STATUS.md` with the timestamps and outcomes of these checks.

6. **Bundle handoff artifacts**
   ```bash
   mkdir -p ai-working/database_Infra\ layer/handoff_bundle
   cp infrastructure/monitoring/grafana/*.json ai-working/database_Infra\ layer/handoff_bundle/
   cp infrastructure/monitoring/prometheus/{prometheus.yml,alerts.yml} ai-working/database_Infra\ layer/handoff_bundle/
   cp infrastructure/.env.local.example ai-working/database_Infra\ layer/handoff_bundle/  # sanitize secrets first
   ```

### 12.5 Documentation Checklist

- [ ] Update `ai-working/database_Infra layer/implementation.md` with:
  - Latest service verification timestamps
  - Prometheus/Grafana validation notes
  - Any command tweaks made during setup
- [ ] Refresh `ai-working/database_Infra layer/OPERATIONS.md` with start/stop, credential rotation, and alert response procedures.
- [ ] Extend `INFRASTRUCTURE_STATUS.md` with monitoring bring-up status, screenshots links, and known caveats.
- [ ] Ensure legacy “dashboard enhancing” directories point to this canonical plan (note their archival status).

### 12.6 Knowledge Transfer & Next Steps

1. **Schedule KT session** – walk through the bundle, dashboards, and runbooks live with the team.
2. **Capture artifacts** – store meeting notes, recording links, and slide decks in `ai-working/database_Infra layer/` (or your knowledge base of choice).
3. **Paper trading rehearsal** – once dashboards are feeding data, run the TradingNode dry-run so dashboards/alerts respond to real events.
4. **Plan follow-up backlog** – create tasks for:
   - Automated AWS deployment or other hosting targets
   - Extending venue coverage in Prometheus exporters
   - Adding automated regression tests for metrics endpoints
5. **Mark milestone complete** – update your tracker with “Monitoring & Documentation Ready” and link this section for future reference.

You now have a clear handoff trail: anyone can replay the monitoring stack, validate it, and understand the operational guardrails surrounding the AI-Adaptive infrastructure.
