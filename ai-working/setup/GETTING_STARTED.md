# Getting Started with Nautilus Trader - Beginner's Guide

## Welcome! 👋

This guide will help you understand and set up Nautilus Trader, even if you're new to algorithmic trading or software development. We'll explain everything in simple terms and walk you through each step.

---

## What is Nautilus Trader?

### The Simple Explanation

Imagine you want to create a robot that trades stocks or cryptocurrency for you. Nautilus Trader is the **framework** (like a toolkit) that helps you build that robot.

**Key Features:**
- **Write Once, Run Anywhere:** Your trading strategy works the same whether you're testing it on old data or running it live
- **Fast:** Built with Rust (a super-fast programming language) but you write your strategies in Python (easier to learn)
- **Safe:** Lots of built-in checks to prevent mistakes
- **Flexible:** Works with stocks, crypto, futures, options, and more

### Real-World Analogy

Think of Nautilus Trader like a **professional kitchen**:
- **You** are the chef (strategy developer)
- **Recipes** are your trading strategies
- **Ingredients** are market data (prices, volumes)
- **Cooking equipment** is the Nautilus engine
- **Restaurants** are exchanges (Binance, Coinbase, etc.)

Just like a chef can test recipes at home before serving them in a restaurant, you can test your trading strategies on historical data before risking real money.

---

## Key Concepts (Explained Simply)

### 1. Strategy
**What it is:** The rules your trading robot follows

**Example:**
```
IF Bitcoin price crosses above $50,000
THEN buy 0.1 Bitcoin

IF Bitcoin price drops below $45,000
THEN sell all Bitcoin
```

### 2. Backtesting
**What it is:** Testing your strategy on old data to see if it would have worked

**Why it matters:** You can see if your strategy would have made or lost money in the past before risking real money

**Example:** "If I had used this strategy in 2023, would I have made money?"

### 3. Live Trading
**What it is:** Running your strategy with real money on real exchanges

**Important:** Always test thoroughly before going live!

### 4. Adapter
**What it is:** A translator that connects Nautilus to an exchange

**Why it matters:** Each exchange (Binance, Coinbase, etc.) speaks a different "language." Adapters translate between Nautilus and the exchange.

**Analogy:** Like a power adapter that lets you plug a US device into a European outlet

### 5. Instrument
**What it is:** Something you can trade (like BTC/USDT, AAPL stock, etc.)

**Components:**
- **Base currency:** What you're buying (BTC)
- **Quote currency:** What you're paying with (USDT)
- **Symbol:** The shorthand name (BTCUSDT)

### 6. Order
**What it is:** An instruction to buy or sell

**Types:**
- **Market Order:** "Buy now at whatever the current price is"
- **Limit Order:** "Buy only if the price drops to $50,000"
- **Stop Order:** "Sell if the price drops below $45,000"

### 7. Position
**What it is:** Your current holdings

**Example:** "I own 0.5 Bitcoin" = You have a position of 0.5 BTC

---

## System Requirements

### What You Need

**Computer:**
- Windows, Mac, or Linux
- At least 8GB RAM (16GB recommended)
- 10GB free disk space
- Internet connection

**Software:**
- Python 3.11, 3.12, or 3.13
- Rust programming language
- Git (for downloading code)
- A code editor (VS Code or PyCharm recommended)

**Knowledge:**
- Basic Python programming (you should understand variables, functions, and classes)
- Basic command line usage (how to run commands in terminal)
- Basic trading concepts (what is buying/selling, what is a price)

**Don't worry if you're not an expert!** We'll guide you through everything.

---

## Installation Guide

### Step 1: Install Python

**Check if you have Python:**
```bash
python --version
```

**If you see "Python 3.11", "Python 3.12", or "Python 3.13" - you're good!**

**If not, install Python:**
- **Windows/Mac:** Download from [python.org](https://www.python.org/downloads/)
- **Linux:** 
  ```bash
  sudo apt update
  sudo apt install python3.11
  ```

### Step 2: Install Rust

**What is Rust?** A programming language that makes Nautilus super fast. You don't need to write Rust code, but Nautilus needs it to build.

**Install Rust:**

**Linux/Mac:**
```bash
curl https://sh.rustup.rs -sSf | sh
source $HOME/.cargo/env
```

**Windows:**
1. Download from [rustup.rs](https://rustup.rs/)
2. Run the installer
3. Restart your terminal

**Verify installation:**
```bash
rustc --version
```
You should see something like: `rustc 1.90.0`

### Step 3: Install uv (Package Manager)

**What is uv?** A tool that manages Python packages (like an app store for Python libraries)

**Install uv:**

**Linux/Mac:**
```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
```

**Windows (PowerShell):**
```powershell
powershell -c "irm https://astral.sh/uv/install.ps1 | iex"
```

**Verify installation:**
```bash
uv --version
```

### Step 4: Install Git

**What is Git?** A tool for downloading and managing code

**Check if you have Git:**
```bash
git --version
```

**If not, install Git:**
- **Windows:** Download from [git-scm.com](https://git-scm.com/)
- **Mac:** Run `xcode-select --install`
- **Linux:** `sudo apt install git`

### Step 5: Download Nautilus Trader

**Open your terminal and run:**
```bash
# Go to your projects folder (or create one)
cd ~
mkdir projects
cd projects

# Download Nautilus Trader
git clone https://github.com/nautechsystems/nautilus_trader.git

# Go into the folder
cd nautilus_trader
```

### Step 6: Build Nautilus Trader

**This will take 10-20 minutes the first time:**

```bash
# Install in debug mode (faster for development)
make install-debug
```

**What's happening?**
- Downloading dependencies (libraries Nautilus needs)
- Compiling Rust code (converting it to machine code)
- Building Python extensions
- Setting up your environment

**If you see errors:**
- Make sure Python, Rust, and uv are installed correctly
- Check that you're in the `nautilus_trader` directory
- See the troubleshooting section below

### Step 7: Verify Installation

**Test that everything works:**
```bash
# Start Python
python

# Try importing Nautilus
>>> import nautilus_trader
>>> print(nautilus_trader.__version__)
1.221.0  # (or whatever the current version is)

# Exit Python
>>> exit()
```

**If you see the version number - congratulations! 🎉 You've successfully installed Nautilus Trader!**

---

## Your First Strategy (Simple Example)

Let's create a very simple strategy to understand how Nautilus works.

### The Strategy

**Rule:** If Bitcoin price goes above $50,000, print a message

**Create a file:** `my_first_strategy.py`

```python
from nautilus_trader.trading.strategy import Strategy
from nautilus_trader.model.data import QuoteTick

class MyFirstStrategy(Strategy):
    """
    A simple strategy that monitors Bitcoin price.
    """
    
    def on_start(self):
        """Called when the strategy starts."""
        self.log.info("Strategy started!")
        
        # Subscribe to Bitcoin price updates
        self.subscribe_quote_ticks(
            instrument_id="BTCUSDT.BINANCE"
        )
    
    def on_quote_tick(self, tick: QuoteTick):
        """Called every time we get a new price update."""
        # Get the current bid price (what buyers are willing to pay)
        price = tick.bid_price
        
        # Log the price
        self.log.info(f"Bitcoin price: ${price}")
        
        # Check if price is above $50,000
        if price > 50000:
            self.log.info("🚀 Bitcoin is above $50,000!")
    
    def on_stop(self):
        """Called when the strategy stops."""
        self.log.info("Strategy stopped!")
```

**What this code does:**
1. **on_start():** Runs when your strategy starts - subscribes to Bitcoin prices
2. **on_quote_tick():** Runs every time a new price comes in - checks if price > $50,000
3. **on_stop():** Runs when your strategy stops - logs a message

---

## Understanding the Architecture

### How Data Flows

```
Exchange (Binance) 
    ↓
Adapter (translates exchange data)
    ↓
Message Bus (distributes data)
    ↓
Your Strategy (receives data, makes decisions)
    ↓
Execution Engine (sends orders)
    ↓
Adapter (translates orders)
    ↓
Exchange (executes orders)
```

### Key Components

**1. Message Bus**
- Like a postal service inside Nautilus
- Delivers messages (price updates, order fills) to the right places

**2. Cache**
- Stores current state (prices, positions, orders)
- Like a notebook where Nautilus writes down everything

**3. Portfolio**
- Tracks your money and positions
- Calculates profit/loss

**4. Execution Engine**
- Manages orders
- Makes sure orders are valid before sending

**5. Data Engine**
- Manages market data subscriptions
- Distributes price updates

---

## Common Workflows

### Workflow 1: Backtesting a Strategy

**Purpose:** Test your strategy on historical data

**Steps:**
1. Write your strategy
2. Get historical data
3. Run backtest
4. Analyze results

**Example:**
```python
from nautilus_trader.backtest.engine import BacktestEngine
from nautilus_trader.model.identifiers import Venue

# Create backtest engine
engine = BacktestEngine()

# Add your strategy
engine.add_strategy(MyFirstStrategy())

# Add data (historical prices)
engine.add_data(...)

# Run backtest
engine.run()

# Get results
results = engine.get_result()
print(f"Total PnL: ${results.total_pnl}")
```

### Workflow 2: Paper Trading (Simulated Live Trading)

**Purpose:** Test your strategy in real-time without risking money

**Steps:**
1. Configure paper trading account
2. Connect to live data feed
3. Run strategy
4. Monitor performance

### Workflow 3: Live Trading

**Purpose:** Trade with real money

**Steps:**
1. Test thoroughly in backtest
2. Test thoroughly in paper trading
3. Start with small amounts
4. Monitor closely
5. Scale up gradually

**⚠️ Warning:** Only trade live after extensive testing!

---

## CCXT Integration (Coming Soon)

### What is CCXT?

**CCXT** is a library that connects to 100+ cryptocurrency exchanges with one unified interface.

**Why integrate it with Nautilus?**
- Access to 100+ exchanges instantly
- Don't need to build individual adapters
- CCXT team maintains exchange connections

### How It Will Work

**Current State:**
- Nautilus has adapters for: Binance, Bybit, Coinbase, Interactive Brokers, etc.
- Each adapter is built separately

**With CCXT:**
- One CCXT adapter
- Works with 100+ exchanges
- Configure which exchange to use

**Example Configuration:**
```python
from nautilus_trader.adapters.ccxt import CCXTDataClientConfig

config = CCXTDataClientConfig(
    exchange_id='binance',  # or 'coinbase', 'kraken', etc.
    api_key='your_key',
    api_secret='your_secret',
    sandbox=True,  # Use testnet
)
```

### Timeline

**Phase 1:** Research ✅ (Complete)
**Phase 2:** Environment Setup 🔄 (In Progress)
**Phase 3:** Implementation 📋 (Planned - 4-6 weeks)
**Phase 4:** Testing 📋 (Planned - 2-3 weeks)
**Phase 5:** Release 📋 (Planned - 1-2 weeks)

---

## Troubleshooting

### Problem: "Python version not supported"

**Solution:**
```bash
# Check your Python version
python --version

# If it's not 3.11, 3.12, or 3.13, install the correct version
# Then create a virtual environment with that version
```

### Problem: "Rust not found"

**Solution:**
```bash
# Install Rust
curl https://sh.rustup.rs -sSf | sh

# Restart your terminal
# Verify installation
rustc --version
```

### Problem: "Build failed"

**Solution:**
```bash
# Clean everything
make clean

# Try building again
make install-debug

# If still failing, check:
# 1. Do you have enough disk space? (need 10GB)
# 2. Do you have enough RAM? (need 8GB)
# 3. Is your internet connection stable?
```

### Problem: "Import error"

**Solution:**
```bash
# Make sure you're in the right directory
cd nautilus_trader

# Activate the virtual environment
source .venv/bin/activate  # Linux/Mac
.venv\Scripts\activate     # Windows

# Try importing again
python -c "import nautilus_trader"
```

### Problem: "Build takes forever"

**Solution:**
```bash
# Use debug mode (much faster)
make build-debug

# Or use cranelift (even faster, but requires nightly Rust)
# See docs/developer_guide/environment_setup.md
```

---

## Best Practices

### For Beginners

1. **Start Simple**
   - Begin with a very simple strategy
   - Add complexity gradually
   - Test each change

2. **Use Paper Trading**
   - Never start with live trading
   - Test for at least a month in paper trading
   - Make sure you understand what your strategy is doing

3. **Keep a Trading Journal**
   - Document your strategies
   - Record why you made certain decisions
   - Learn from mistakes

4. **Risk Management**
   - Never risk more than you can afford to lose
   - Use stop losses
   - Diversify

5. **Stay Informed**
   - Join the Nautilus Discord
   - Read the documentation
   - Learn from others

### For Development

1. **Use Version Control**
   - Commit your code regularly
   - Use meaningful commit messages
   - Create branches for experiments

2. **Write Tests**
   - Test your strategies thoroughly
   - Use unit tests for components
   - Use integration tests for full strategies

3. **Document Your Code**
   - Write clear comments
   - Explain why, not just what
   - Future you will thank you

4. **Follow Coding Standards**
   - Use type hints
   - Follow PEP 8 (Python style guide)
   - Run linters

---

## Learning Resources

### Official Documentation
- **Nautilus Docs:** https://nautilustrader.io/docs/
- **Getting Started:** https://nautilustrader.io/docs/getting_started/
- **Tutorials:** https://nautilustrader.io/docs/tutorials/

### Community
- **Discord:** https://discord.gg/NautilusTrader
- **GitHub:** https://github.com/nautechsystems/nautilus_trader
- **Discussions:** https://github.com/nautechsystems/nautilus_trader/discussions

### Learning Python
- **Python.org Tutorial:** https://docs.python.org/3/tutorial/
- **Real Python:** https://realpython.com/
- **Python for Everybody:** https://www.py4e.com/

### Learning Trading
- **Investopedia:** https://www.investopedia.com/
- **Babypips (Forex):** https://www.babypips.com/
- **Khan Academy (Finance):** https://www.khanacademy.org/economics-finance-domain

### Learning Algorithmic Trading
- **QuantStart:** https://www.quantstart.com/
- **Quantopian Lectures:** (archived but still useful)
- **Nautilus Examples:** `examples/` directory in the repository

---

## Next Steps

### Week 1: Learn the Basics
- [ ] Complete installation
- [ ] Read "Getting Started" documentation
- [ ] Run example strategies
- [ ] Join Discord community

### Week 2: Build Your First Strategy
- [ ] Design a simple strategy
- [ ] Implement it in Python
- [ ] Backtest on historical data
- [ ] Analyze results

### Week 3: Improve Your Strategy
- [ ] Add risk management
- [ ] Optimize parameters
- [ ] Test on different time periods
- [ ] Document your findings

### Week 4: Paper Trading
- [ ] Set up paper trading account
- [ ] Run your strategy live (simulated)
- [ ] Monitor for a week
- [ ] Make adjustments

### Month 2+: Advanced Topics
- [ ] Learn about different order types
- [ ] Study portfolio management
- [ ] Explore multi-instrument strategies
- [ ] Consider live trading (with caution!)

---

## Glossary

**Algorithm:** A set of rules or instructions (like a recipe)

**API:** Application Programming Interface - how programs talk to each other

**Backtest:** Testing a strategy on historical data

**Bar:** A summary of price action over a time period (open, high, low, close)

**Bid:** The price buyers are willing to pay

**Ask:** The price sellers are willing to accept

**Spread:** The difference between bid and ask

**Liquidity:** How easy it is to buy/sell without affecting the price

**Slippage:** The difference between expected price and actual execution price

**Latency:** Delay between sending an order and it being executed

**PnL:** Profit and Loss

**Tick:** The smallest price movement

**Volume:** How much has been traded

**Volatility:** How much the price moves up and down

---

## FAQ

**Q: Do I need to know Rust?**
A: No! You write strategies in Python. Rust is used internally for performance.

**Q: Can I use Nautilus for stocks?**
A: Yes! Nautilus supports stocks, crypto, futures, options, and more.

**Q: Is Nautilus free?**
A: Yes! It's open source under LGPL license.

**Q: Can I make money with Nautilus?**
A: Nautilus is a tool. Whether you make money depends on your strategy, risk management, and market conditions. Most traders lose money - trade responsibly!

**Q: How much money do I need to start?**
A: For learning: $0 (use paper trading)
For live trading: Start small ($100-$1000) and scale up gradually

**Q: Is algorithmic trading legal?**
A: Yes, in most countries. But check your local regulations.

**Q: How long does it take to learn?**
A: Basics: 1-2 weeks
Profitable trading: Months to years (if ever)
Be patient and keep learning!

**Q: Can I use Nautilus for high-frequency trading?**
A: Yes, but you'll need low-latency infrastructure and deep technical knowledge.

**Q: What's the difference between Nautilus and other platforms?**
A: Nautilus is production-grade, has Rust core for performance, and maintains parity between backtest and live trading.

---

## Conclusion

Congratulations on starting your journey with Nautilus Trader! 🎉

**Remember:**
- Start simple
- Test thoroughly
- Never risk more than you can afford to lose
- Keep learning
- Join the community

**The Nautilus community is here to help!**
- Ask questions on Discord
- Share your strategies (if you want)
- Learn from others
- Contribute back when you can

**Happy trading! 📈**

---

**Guide Version:** 1.0  
**Last Updated:** January 2025  
**For:** Nautilus Trader v1.221.0+  
**Difficulty:** Beginner  
**Estimated Reading Time:** 30 minutes
