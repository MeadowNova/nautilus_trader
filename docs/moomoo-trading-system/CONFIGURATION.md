# Configuration Guide

Complete guide to configuring your Moomoo account, OpenD gateway, and trading system.

## Table of Contents

1. [Moomoo Account Setup](#moomoo-account-setup)
2. [Market Data Permissions](#market-data-permissions) ⚠️ **CRITICAL**
3. [OpenD Gateway Configuration](#opend-gateway-configuration)
4. [Paper Trading Activation](#paper-trading-activation)
5. [Environment Variables](#environment-variables)
6. [Trading Parameters](#trading-parameters)
7. [Risk Management Settings](#risk-management-settings)

---

## Moomoo Account Setup

### Account Requirements

- [ ] Moomoo brokerage account (US or International)
- [ ] Account funded (recommended $10,000+ for paper trading simulation)
- [ ] Trading password set (required for API access)
- [ ] Paper trading enabled

### Create Account (If Needed)

1. Download Moomoo app: https://www.moomoo.com/download
2. Complete account registration
3. Verify identity (required for trading)
4. Fund account (optional for paper trading)

### Set Trading Password

The trading password is **separate** from your login password and required for API trading.

**Steps:**
1. Open Moomoo mobile app
2. Go to: **Me** → **Settings** → **Security Center**
3. Select **Trading Password**
4. Create a 6-digit trading password
5. **Save this password securely** - you'll need it in OpenD

---

## Market Data Permissions

### ⚠️ CRITICAL: US Market Real-Time Quotes

**This is the #1 blocker for new users.**

Without US market data permissions, you'll see:
```
Error: No right to subscribe the quote for US.XLE
Error: No right to subscribe the quote for US.NVDA
```

### Enable US Market Data (Required)

**Method 1: Mobile App (Recommended)**

1. Open Moomoo mobile app
2. Go to: **Quotes** → **Markets** → **US Stocks**
3. Tap any US stock (e.g., AAPL)
4. Look for "Apply for Real-Time Quotes" banner
5. Tap **Apply Now**
6. Accept terms and conditions
7. **Wait 2-3 minutes for activation**
8. Verify: Check if stock quotes show real-time prices

**Method 2: Desktop App**

1. Open Moomoo desktop application
2. Go to: **Settings** → **Quote Settings**
3. Find **US Stock Market Data**
4. Click **Subscribe** or **Enable**
5. Agree to terms (usually free for basic real-time quotes)
6. Wait for confirmation email/notification

### Verify Permissions Are Active

After enabling, test in OpenD:

```bash
cd /home/ajk/Nautilus/nautilus_trader
source .venv/bin/activate

python << 'EOF'
from moomoo import OpenQuoteContext

ctx = OpenQuoteContext(host="127.0.0.1", port=11111)

# Try to subscribe to a US stock
ret, data = ctx.subscribe(['US.XLE'], ['QUOTE'])

if ret == 0:
    print("✓ US market data permissions are active!")
else:
    print(f"✗ Permission denied: {data}")
    print("\nAction: Enable US real-time quotes in Moomoo app")

ctx.close()
EOF
```

**Expected:** `✓ US market data permissions are active!`

### Troubleshooting Permissions

**Problem:** Enabled permissions but still getting errors

**Solutions:**
1. **Wait longer** - Activation can take 5-10 minutes
2. **Restart OpenD** - Close and reopen OpenD gateway
3. **Re-login** - Logout and login again in Moomoo app
4. **Check account status** - Ensure account is not restricted
5. **Contact Moomoo support** - Via app chat if issues persist

**Problem:** Permissions expire or get revoked

**Cause:** Free real-time data may require monthly renewal.

**Solution:** Re-apply in Moomoo app (usually automatic).

---

## OpenD Gateway Configuration

### Download and Install

1. Visit: https://www.moomoo.com/download/OpenD
2. Select your operating system:
   - **Windows**: `OpenD_x64_setup.exe`
   - **macOS**: `OpenD.dmg`
   - **Linux**: `OpenD_linux_x64.tar.gz`
3. Install following platform-specific instructions

### Initial Setup

**Windows:**
```powershell
# Extract to desired location
# Double-click OpenD.exe
# Follow setup wizard
```

**macOS:**
```bash
# Open DMG file
# Drag OpenD to Applications
# Open from Applications (right-click → Open if security warning)
```

**Linux:**
```bash
# Extract
tar -xzf OpenD_linux_x64.tar.gz
cd OpenD

# Make executable
chmod +x OpenD

# Run
./OpenD
```

### First-Time Configuration

When you first start OpenD:

1. **Language Selection**: Choose English or Chinese
2. **Login**: Use your Moomoo credentials
3. **Trading Password**: Enter the 6-digit trading password you set earlier
4. **Two-Factor Authentication**: Enter code from SMS/email if prompted
5. **Market Selection**: Ensure "US Market" is checked
6. **Port Configuration**: Default 11111 (change if conflict)

### OpenD Settings

Access settings in OpenD interface:

**Connection:**
- **Host**: `127.0.0.1` (localhost)
- **Port**: `11111` (default)
- **Protocol**: TCP
- **Encryption**: TLS enabled (recommended)

**Trading:**
- **Environment**: Paper Trading (SIMULATE)
- **Security Firm**: FUTUSECURITIES (or your broker)
- **Market**: US
- **Order Rate Limit**: 15 per 30 seconds (API limit)

**Data:**
- **Quote Subscription Quota**: 1000 (check your plan)
- **Real-Time Data**: Enabled
- **Historical Data**: Enabled
- **Kline (Candlestick)**: 1-minute minimum resolution

### Verify OpenD Configuration

```bash
# Check OpenD is listening
lsof -i :11111

# Should show:
# OpenD   12345 user   10u  IPv4  ...  TCP *:11111 (LISTEN)

# Test connection
python -c "from moomoo import OpenQuoteContext; ctx = OpenQuoteContext(); print(ctx.get_global_state())"
```

### OpenD Logs

If issues occur, check OpenD logs:

**Windows:**
```
C:\Users\<username>\AppData\Local\Moomoo\OpenD\logs\
```

**macOS:**
```
~/Library/Application Support/Moomoo/OpenD/logs/
```

**Linux:**
```
~/.moomoo/OpenD/logs/
```

---

## Paper Trading Activation

### Enable Paper Trading in Moomoo

**Mobile App:**
1. Go to: **Trade** → **Paper Trading**
2. Tap **Activate Paper Trading**
3. Set initial balance (e.g., $100,000)
4. Confirm activation

**Desktop App:**
1. Go to: **Account** → **Paper Trading**
2. Click **Enable**
3. Set parameters:
   - Initial cash: $100,000 (recommended)
   - Currency: USD
   - Enable options: No (for stock trading only)

### Verify Paper Trading Account

```bash
python << 'EOF'
from moomoo import OpenSecTradeContext, TrdEnv

ctx = OpenSecTradeContext(host="127.0.0.1", port=11111)

# Get account list
ret, accounts = ctx.get_acc_list()

if ret == 0:
    print("Available Accounts:")
    for idx, row in accounts.iterrows():
        env = row['trd_env']
        acc_id = row['acc_id']
        print(f"  - {acc_id} ({env})")

        if env == TrdEnv.SIMULATE:
            print(f"    ✓ Paper trading account found!")
else:
    print(f"Error: {accounts}")

ctx.close()
EOF
```

**Expected Output:**
```
Available Accounts:
  - 1234567890 (SIMULATE)
    ✓ Paper trading account found!
```

---

## Environment Variables

### Create Configuration File

```bash
cd /home/ajk/Nautilus/nautilus_trader

# Copy template
cp infrastructure/.env.template infrastructure/.env.local

# Edit with your values
nano infrastructure/.env.local
```

### Required Variables

```bash
# Moomoo OpenD Gateway
MOOMOO_HOST=127.0.0.1
MOOMOO_PORT=11111
MOOMOO_TRADING_MODE=paper          # paper | live
MOOMOO_SECURITY_FIRM=FUTUSECURITIES
MOOMOO_TRD_MARKET=US

# Database
POSTGRES_HOST=localhost
POSTGRES_PORT=5435                 # Non-standard port to avoid conflicts
POSTGRES_USER=nautilus
POSTGRES_PASSWORD=nautilus_pass
POSTGRES_DB=nautilus_trader

# Redis
REDIS_HOST=localhost
REDIS_PORT=6378                    # Non-standard port
REDIS_PASSWORD=redis_pass

# Monitoring
PROMETHEUS_HOST=localhost
PROMETHEUS_PORT=9090
GRAFANA_HOST=localhost
GRAFANA_PORT=3000
GRAFANA_USER=admin
GRAFANA_PASSWORD=admin_pass

# Metrics
AI_METRICS_PORT=9100
```

### Optional Variables

```bash
# Logging
LOG_LEVEL=INFO                     # DEBUG | INFO | WARNING | ERROR
LOG_FILE_LEVEL=DEBUG
LOG_DIRECTORY=logs
LOG_COLORS=true

# RL Training
RL_BUFFER_SIZE=100000
RL_BATCH_SIZE=64
RL_LEARNING_RATE=0.0003
RL_GAMMA=0.99
RL_EPSILON=0.1
RL_EPSILON_MIN=0.01
RL_EPSILON_DECAY=0.995

# Risk Management
MAX_POSITION_SIZE_PCT=0.02        # 2% per position
MAX_CONCURRENT_POSITIONS=8
DAILY_LOSS_LIMIT_PCT=0.03         # 3% daily loss limit
MAX_DRAWDOWN_PCT=0.10              # 10% max drawdown
```

### Load Environment Variables

```bash
# Load in current session
export $(cat infrastructure/.env.local | xargs)

# Or source in script
source <(sed 's/^/export /' infrastructure/.env.local)

# Verify
echo $MOOMOO_HOST
echo $POSTGRES_PORT
```

---

## Trading Parameters

### Strategy Configuration

Edit `/home/ajk/Nautilus/nautilus_trader/scripts/start_paper_trading_moomoo.py`:

**Pairs Trading Parameters:**

```python
pairs_config = RLPairsTradingConfig(
    instrument_id_a="XLE.MOOMOO",      # Energy sector ETF
    instrument_id_b="XLF.MOOMOO",      # Financial sector ETF
    lookback_period=40,                # Rolling window for z-score
    zscore_entry=2.25,                 # Entry threshold (2.25 sigma)
    zscore_exit=0.25,                  # Exit at mean reversion
    zscore_stop=3.5,                   # Stop loss (3.5 sigma)
    position_size_pct=0.02,            # 2% per leg (4% total)
    max_holding_bars=80,               # Time-based exit
    use_rl=True,                       # Enable RL enhancement
)
```

**Momentum Breakout Parameters:**

```python
momentum_config = RLMomentumBreakoutConfig(
    instrument_ids=(
        "NVDA.MOOMOO",                 # Tech stocks
        "AMD.MOOMOO",
        "META.MOOMOO",
    ),
    benchmark_id="SPY.MOOMOO",         # S&P 500 benchmark
    breakout_lookback=15,              # 15-day high breakout
    volume_multiplier=1.75,            # 1.75x average volume required
    rsi_period=14,                     # RSI calculation period
    rsi_min=50.0,                      # Min RSI for entry
    rsi_max=70.0,                      # Max RSI (avoid overbought)
    relative_strength_min=0.02,        # Min relative strength vs SPY
    profit_target_atr=2.5,             # Take profit at 2.5x ATR
    trailing_stop_atr=2.0,             # Trailing stop at 2.0x ATR
    position_size_pct=0.02,            # 2% per position
    max_holding_bars=40,               # Max hold period
    max_concurrent=2,                  # Max simultaneous positions
    use_rl=True,
)
```

### Instrument Selection

**Available instruments** (verify permissions first):

```python
# US Equity ETFs
"SPY.MOOMOO"    # S&P 500
"QQQ.MOOMOO"    # NASDAQ 100
"IWM.MOOMOO"    # Russell 2000
"XLE.MOOMOO"    # Energy
"XLF.MOOMOO"    # Financials
"XLK.MOOMOO"    # Technology
"XLV.MOOMOO"    # Healthcare

# Individual Stocks
"AAPL.MOOMOO"   # Apple
"MSFT.MOOMOO"   # Microsoft
"NVDA.MOOMOO"   # NVIDIA
"AMD.MOOMOO"    # AMD
"TSLA.MOOMOO"   # Tesla
"META.MOOMOO"   # Meta
"GOOGL.MOOMOO"  # Google
"AMZN.MOOMOO"   # Amazon
```

**To add instruments**, edit strategy configs and update instrument provider:

```python
# In start_paper_trading_moomoo.py

all_instruments = (
    "XLE.MOOMOO",
    "XLF.MOOMOO",
    "NVDA.MOOMOO",
    "AMD.MOOMOO",
    "META.MOOMOO",
    "SPY.MOOMOO",      # Benchmark
    "YOUR_NEW_INSTRUMENT.MOOMOO",  # Add here
)

config = TradingNodeConfig(
    # ...
    data_clients={
        "MOOMOO": MoomooDataClientConfig(
            instrument_provider=InstrumentProviderConfig(
                load_all=False,
                load_ids=all_instruments,  # Include new instrument
            ),
        )
    },
)
```

---

## Risk Management Settings

### Default Risk Parameters ($100,000 Account)

| Parameter | Default | Description | Editable In |
|-----------|---------|-------------|-------------|
| Max Position Size | 2% ($2,000) | Per instrument | Strategy config |
| Max Concurrent | 8 positions | Total across strategies | Risk manager |
| Daily Loss Limit | 3% ($3,000) | Halts new trades | Risk manager |
| Max Drawdown | 10% ($10,000) | Emergency liquidation | Risk manager |
| Stop Loss (1R) | 1% ($1,000) | Per trade | Strategy logic |
| Order Rate Limit | 15 per 30s | API throttle | Moomoo adapter |

### Configure Risk Manager

Create custom risk configuration:

```python
# In start_paper_trading_moomoo.py

from nautilus_trader.risk import RiskEngineConfig

risk_config = RiskEngineConfig(
    bypass=False,                          # Enforce risk checks
    max_order_rate="15/00:00:30",         # 15 orders per 30 seconds
    max_notional_per_order={
        "MOOMOO": Money.from_str("2000 USD"),
    },
)

config = TradingNodeConfig(
    trader_id=TraderId("MOOMOO-RL-PAPER-001"),
    risk_engine=risk_config,              # Add risk engine
    # ... rest of config
)
```

### Position Sizing Logic

**Fixed Percentage:**
```python
position_size_pct = 0.02  # 2% of account
position_size = account_balance * position_size_pct
```

**ATR-Based:**
```python
# Risk 1% of account per trade, size based on ATR stop
risk_amount = account_balance * 0.01
atr_stop_distance = atr * 1.5
position_size = risk_amount / atr_stop_distance
```

**Kelly Criterion (Advanced):**
```python
# Only use with validated win rate and R-multiple
win_rate = 0.55
avg_win = 1.8  # R-multiple
avg_loss = 1.0
kelly_fraction = (win_rate * avg_win - (1 - win_rate)) / avg_win
position_size = account_balance * kelly_fraction * 0.25  # Quarter Kelly
```

### Adjust for Smaller Accounts

For accounts < $100,000, reduce position sizes proportionally:

```python
# $25,000 account
position_size_pct = 0.02  # Keep 2% but smaller $ amounts

# $10,000 account (minimum recommended)
position_size_pct = 0.02  # May need to trade fewer instruments
max_concurrent = 3        # Reduce concurrent positions
```

**Warning:** Accounts < $10,000 may have difficulty trading effectively due to minimum lot sizes and risk concentration.

---

## Configuration Verification

### Run System Check

```bash
cd /home/ajk/Nautilus/nautilus_trader
source .venv/bin/activate

python << 'EOF'
import os
from moomoo import OpenQuoteContext, OpenSecTradeContext, TrdEnv

print("=== Moomoo Trading System Configuration Check ===\n")

# 1. Environment Variables
print("1. Environment Variables:")
env_vars = [
    "MOOMOO_HOST", "MOOMOO_PORT", "POSTGRES_HOST",
    "POSTGRES_PORT", "REDIS_PORT", "GRAFANA_PORT"
]
for var in env_vars:
    val = os.getenv(var)
    status = "✓" if val else "✗"
    print(f"  {status} {var}: {val or 'NOT SET'}")

# 2. OpenD Connection
print("\n2. OpenD Gateway:")
try:
    ctx = OpenQuoteContext(host="127.0.0.1", port=11111)
    ret, data = ctx.get_global_state()
    if ret == 0:
        print(f"  ✓ Connected to OpenD")
        print(f"    Market: {data.get('market_us')}")
    else:
        print(f"  ✗ Connection failed: {data}")
    ctx.close()
except Exception as e:
    print(f"  ✗ Error: {e}")

# 3. Trading Account
print("\n3. Paper Trading Account:")
try:
    trd_ctx = OpenSecTradeContext(host="127.0.0.1", port=11111)
    ret, accounts = trd_ctx.get_acc_list()
    if ret == 0:
        paper_accts = [r for _, r in accounts.iterrows() if r['trd_env'] == TrdEnv.SIMULATE]
        if paper_accts:
            print(f"  ✓ Paper account found: {paper_accts[0]['acc_id']}")
        else:
            print("  ✗ No paper trading account")
    else:
        print(f"  ✗ Account query failed: {accounts}")
    trd_ctx.close()
except Exception as e:
    print(f"  ✗ Error: {e}")

# 4. Market Data Permissions
print("\n4. Market Data Permissions:")
try:
    ctx = OpenQuoteContext(host="127.0.0.1", port=11111)
    ret, _ = ctx.subscribe(['US.XLE'], ['QUOTE'])
    if ret == 0:
        print("  ✓ US market data permissions active")
    else:
        print("  ✗ US market data not authorized")
        print("    Action: Enable in Moomoo app → Settings → Quotes")
    ctx.close()
except Exception as e:
    print(f"  ✗ Error: {e}")

print("\n=== Configuration Check Complete ===")
EOF
```

**All checks should show ✓ before starting paper trading.**

---

## Next Steps

- **All configured?** → Proceed to [QUICKSTART.md](QUICKSTART.md) to start trading
- **Issues?** → See [TROUBLESHOOTING.md](TROUBLESHOOTING.md)
- **Want to customize strategies?** → See [STRATEGIES.md](STRATEGIES.md)

---

**Critical Reminders:**
1. Enable US market data permissions (most common issue)
2. Set trading password in Moomoo app
3. Activate paper trading account
4. Keep OpenD running during trading
5. Test configuration before market hours
