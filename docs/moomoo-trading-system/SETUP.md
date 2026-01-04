# Detailed Setup Guide

Comprehensive installation and setup instructions for the Moomoo RL Paper Trading System.

## Overview

This guide covers the complete setup process, from system requirements to first trade. For a quicker setup, see [QUICKSTART.md](QUICKSTART.md).

**Estimated Time:** 30-45 minutes

## Table of Contents

1. [System Requirements](#system-requirements)
2. [Python Environment Setup](#python-environment-setup)
3. [Infrastructure Services](#infrastructure-services)
4. [Moomoo Account Configuration](#moomoo-account-configuration)
5. [OpenD Gateway Installation](#opend-gateway-installation)
6. [NautilusTrader Installation](#nautilustrader-installation)
7. [RL Framework Setup](#rl-framework-setup)
8. [Verification](#verification)

---

## System Requirements

### Hardware Requirements

| Component | Minimum | Recommended |
|-----------|---------|-------------|
| CPU | 4 cores, 2.0 GHz | 8 cores, 3.0 GHz+ |
| RAM | 8 GB | 16 GB+ |
| Disk Space | 20 GB free | 50 GB+ SSD |
| Network | 10 Mbps | 50 Mbps+ low latency |

### Operating System Support

**Fully Supported:**
- Ubuntu 22.04+, 24.04 (recommended)
- Debian 11+
- macOS 12+ (Monterey or later)
- Windows 11 with WSL2 (Ubuntu 22.04+)

**Partially Supported:**
- CentOS 8+, Rocky Linux 8+
- macOS 11 (Big Sur) - may have issues
- Windows 10 with WSL2

### Software Prerequisites

```bash
# Check versions
python --version  # Python 3.11+ required
docker --version  # Docker 20.10+ required
git --version     # Git 2.30+ required

# If missing, install:

# Ubuntu/Debian
sudo apt update
sudo apt install python3.11 python3.11-venv docker.io git

# macOS (via Homebrew)
brew install python@3.11 docker git

# Verify Docker is running
docker ps
```

---

## Python Environment Setup

### Option 1: Using uv (Recommended)

`uv` is faster and more reliable than pip/venv.

**Install uv:**
```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
source ~/.bashrc  # or ~/.zshrc for macOS
```

**Create virtual environment:**
```bash
cd /home/ajk/Nautilus/nautilus_trader

# Create and activate
uv venv .venv
source .venv/bin/activate

# Install dependencies
uv sync --all-groups --all-extras

# Verify installation
python -c "import nautilus_trader; print(nautilus_trader.__version__)"
```

### Option 2: Using venv and pip

```bash
cd /home/ajk/Nautilus/nautilus_trader

# Create virtual environment
python3.11 -m venv .venv
source .venv/bin/activate

# Upgrade pip
pip install --upgrade pip setuptools wheel

# Install NautilusTrader
pip install nautilus_trader[all]

# Install Moomoo API
pip install moomoo-api

# Install additional dependencies
pip install torch numpy pandas ta-lib scikit-learn xgboost
```

### Verify Python Environment

```bash
python << 'EOF'
import sys
import nautilus_trader
import moomoo
import torch
import numpy as np
import pandas as pd

print("Python Version:", sys.version)
print("NautilusTrader:", nautilus_trader.__version__)
print("Moomoo API:", moomoo.__version__)
print("PyTorch:", torch.__version__)
print("NumPy:", np.__version__)
print("Pandas:", pd.__version__)

print("\n✓ All dependencies installed successfully!")
EOF
```

---

## Infrastructure Services

### Docker Compose Setup

**Verify Docker Compose:**
```bash
docker compose version
# Should be v2.0+
```

**Configure environment:**
```bash
cd /home/ajk/Nautilus/nautilus_trader

# Copy template
cp infrastructure/.env.template infrastructure/.env.local

# Edit with your values
nano infrastructure/.env.local
```

**Minimum `.env.local` configuration:**
```bash
# Database
DB_PORT=5435
POSTGRES_USER=nautilus
POSTGRES_PASSWORD=nautilus_pass
POSTGRES_DB=nautilus_trader

# Redis
REDIS_PORT=6378
REDIS_PASSWORD=redis_pass

# Grafana
GRAFANA_PORT=3000
GRAFANA_USER=admin
GRAFANA_PASSWORD=your_secure_password

# Prometheus
PROMETHEUS_PORT=9090

# Metrics
AI_METRICS_PORT=9100

# Moomoo
MOOMOO_HOST=127.0.0.1
MOOMOO_PORT=11111
MOOMOO_TRADING_MODE=paper
```

### Start Infrastructure

```bash
cd infrastructure/docker

# Pull images (first time only)
docker compose --env-file ../.env.local pull

# Start all services
docker compose --env-file ../.env.local up -d

# Wait for services to be healthy (~30 seconds)
sleep 30

# Verify services
docker ps --format "table {{.Names}}\t{{.Status}}\t{{.Ports}}"
```

**Expected output:**
```
NAMES                STATUS                PORTS
nautilus_postgres    Up 30 seconds (healthy)  0.0.0.0:5435->5432/tcp
nautilus_redis       Up 30 seconds (healthy)  0.0.0.0:6378->6379/tcp
nautilus_prometheus  Up 30 seconds            0.0.0.0:9090->9090/tcp
nautilus_grafana     Up 30 seconds            0.0.0.0:3000->3000/tcp
ai_metrics           Up 30 seconds            0.0.0.0:9100->9100/tcp
```

### Initialize Database

```bash
# Connect to PostgreSQL
docker exec -it nautilus_postgres psql -U nautilus -d nautilus_trader

# Run in psql:
CREATE TABLE IF NOT EXISTS trades (
    id SERIAL PRIMARY KEY,
    timestamp TIMESTAMP NOT NULL,
    strategy_id VARCHAR(50),
    instrument_id VARCHAR(50),
    side VARCHAR(10),
    quantity INTEGER,
    entry_price NUMERIC(12,4),
    exit_price NUMERIC(12,4),
    pnl NUMERIC(12,2),
    r_multiple NUMERIC(6,2),
    bars_held INTEGER,
    max_favorable_excursion NUMERIC(12,2),
    max_adverse_excursion NUMERIC(12,2)
);

CREATE INDEX idx_trades_timestamp ON trades(timestamp);
CREATE INDEX idx_trades_strategy ON trades(strategy_id);

-- Verify
\dt
\q
```

### Configure Grafana Dashboards

```bash
# Access Grafana
open http://localhost:3000  # macOS
# or browse to http://localhost:3000

# Login with credentials from .env.local

# Import dashboards (manual steps):
# 1. Click "+" → "Import"
# 2. Upload JSON from: infrastructure/monitoring/grafana/dashboards/
# 3. Import:
#    - live-trading-monitor.json
#    - rl-training-metrics.json
#    - system-health.json
```

---

## Moomoo Account Configuration

### Create Moomoo Account

If you don't have an account:

1. Download Moomoo app: https://www.moomoo.com/download
2. Sign up (email or phone)
3. Complete identity verification
4. Fund account (optional for paper trading)

### Set Trading Password

**Mobile App:**
1. Open Moomoo app
2. Tap **Me** → **Settings** → **Security Center**
3. Select **Trading Password**
4. Create 6-digit PIN
5. **Save this securely** - needed for OpenD

**This is different from your login password!**

### Enable Paper Trading

**Mobile App:**
1. Tap **Trade** → **Paper Trading**
2. Tap **Activate Paper Trading**
3. Set initial balance: **$100,000** (recommended)
4. Confirm activation

**Verify:**
```
Paper Trading account should now appear in account list
Balance: $100,000.00
```

### Enable US Market Data Permissions

**CRITICAL STEP - See [CONFIGURATION.md](CONFIGURATION.md#market-data-permissions) for details.**

**Quick Steps:**
1. Moomoo app → **Quotes** → **Markets** → **US Stocks**
2. Tap any US stock (e.g., AAPL)
3. Look for "Apply for Real-Time Quotes" banner
4. Tap **Apply Now** → Accept terms
5. **Wait 2-5 minutes** for activation
6. Verify: Stock should show real-time price (not "15 min delayed")

---

## OpenD Gateway Installation

### Download OpenD

**Official Source:** https://www.moomoo.com/download/OpenD

**Select your platform:**
- Windows: `OpenD_x64_setup.exe`
- macOS: `OpenD.dmg`
- Linux: `OpenD_linux_x64.tar.gz`

### Installation by Platform

**Windows:**
```powershell
# Run installer
.\OpenD_x64_setup.exe

# Follow wizard
# Default install location: C:\Program Files\Moomoo\OpenD\

# Start OpenD
cd "C:\Program Files\Moomoo\OpenD"
.\OpenD.exe
```

**macOS:**
```bash
# Mount DMG
open OpenD.dmg

# Drag to Applications
cp -R /Volumes/OpenD/OpenD.app /Applications/

# First run (bypass Gatekeeper)
xattr -d com.apple.quarantine /Applications/OpenD.app
open /Applications/OpenD.app
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

### Configure OpenD

**First-time setup:**

1. **Select Language:** English (or Chinese)
2. **Login Method:** Username/Password
3. **Username:** Your Moomoo email/phone
4. **Password:** Your Moomoo login password
5. **Trading Password:** The 6-digit PIN you created
6. **Two-Factor:** Enter SMS/email code if prompted
7. **Market Selection:** Check "US Market"
8. **Port:** 11111 (default, change if conflict)

**Advanced Settings:**

```
Connection:
  - Host: 127.0.0.1 (localhost)
  - Port: 11111
  - Protocol: TCP
  - Encryption: TLS (enabled)

Trading:
  - Environment: Paper Trading (SIMULATE)
  - Security Firm: FUTUSECURITIES
  - Market: US
  - Order Rate Limit: 15 per 30 seconds

Data:
  - Quote Subscription: 1000 (check your plan)
  - Real-Time: Enabled
  - Historical: Enabled
  - Kline Resolution: 1-minute minimum
```

### Verify OpenD Connection

```bash
# Check OpenD is listening
lsof -i :11111

# Should show:
# OpenD   12345 user   10u  IPv4  ...  TCP *:11111 (LISTEN)

# Test connection
python << 'EOF'
from moomoo import OpenQuoteContext, OpenSecTradeContext, TrdEnv

# Test quote connection
quote_ctx = OpenQuoteContext(host="127.0.0.1", port=11111)
ret, data = quote_ctx.get_global_state()

if ret == 0:
    print("✓ Quote connection successful")
    print(f"  Market US: {data.get('market_us')}")
else:
    print(f"✗ Quote connection failed: {data}")

quote_ctx.close()

# Test trade connection
trade_ctx = OpenSecTradeContext(host="127.0.0.1", port=11111)
ret, accounts = trade_ctx.get_acc_list()

if ret == 0:
    paper_accts = [r for _, r in accounts.iterrows() if r['trd_env'] == TrdEnv.SIMULATE]
    if paper_accts:
        print(f"✓ Paper trading account found: {paper_accts[0]['acc_id']}")
    else:
        print("✗ No paper trading account")
else:
    print(f"✗ Account query failed: {accounts}")

trade_ctx.close()

print("\n✓ OpenD configuration complete!")
EOF
```

---

## NautilusTrader Installation

### Install from Source (Development)

```bash
cd /home/ajk/Nautilus/nautilus_trader
source .venv/bin/activate

# Set required environment variables
export LD_LIBRARY_PATH="$HOME/.local/share/uv/python/cpython-3.13.4-linux-x86_64-gnu/lib:$LD_LIBRARY_PATH"
export PYO3_PYTHON=$(pwd)/.venv/bin/python

# Install in debug mode (faster builds during development)
BUILD_MODE=debug make install-debug

# Or release mode (optimized, slower builds)
BUILD_MODE=release make install

# Verify installation
python -c "import nautilus_trader; print('Version:', nautilus_trader.__version__)"
```

### Install from PyPI (Production)

```bash
pip install nautilus_trader[all]

# Install Moomoo adapter dependencies
pip install moomoo-api pandas numpy
```

### Install Moomoo Adapter

The Moomoo adapter is already included in the repository at:
`/home/ajk/Nautilus/nautilus_trader/nautilus_trader/adapters/moomoo/`

**Verify adapter:**
```bash
python << 'EOF'
from nautilus_trader.adapters.moomoo import MOOMOO
from nautilus_trader.adapters.moomoo.config import MoomooGatewayConfig
from nautilus_trader.adapters.moomoo.factories import (
    MoomooLiveDataClientFactory,
    MoomooLiveExecClientFactory,
)

print("✓ Moomoo adapter imported successfully")
print(f"  Venue: {MOOMOO}")
EOF
```

---

## RL Framework Setup

### Install RL Dependencies

```bash
# PyTorch (CPU version for paper trading)
pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cpu

# Or GPU version (if CUDA available)
# pip install torch torchvision torchaudio

# Additional ML libraries
pip install scikit-learn xgboost optuna

# Verify
python << 'EOF'
import torch
print(f"PyTorch: {torch.__version__}")
print(f"CUDA Available: {torch.cuda.is_available()}")
print(f"Device: {'cuda' if torch.cuda.is_available() else 'cpu'}")
EOF
```

### Verify RL Framework

```bash
python << 'EOF'
from ajk_strategies.rl_framework.agents.base_agent import SimpleRuleAgent, AgentConfig
from ajk_strategies.rl_framework.state.state_builder import StateBuilder, StateConfig
from ajk_strategies.rl_framework.reward.reward_calculator import RewardCalculator
from ajk_strategies.rl_framework.training.experience_buffer import PrioritizedReplayBuffer

# Test components
agent_config = AgentConfig(state_dim=75, action_dim=4)
agent = SimpleRuleAgent(config=agent_config)

buffer = PrioritizedReplayBuffer(capacity=10000)

state_builder = StateBuilder(StateConfig(lookback_bars=10))

reward_calc = RewardCalculator()

print("✓ RL Framework components loaded successfully")
print(f"  Agent: {agent.__class__.__name__}")
print(f"  Buffer capacity: {buffer.capacity}")
EOF
```

### Create Models Directory

```bash
mkdir -p /home/ajk/Nautilus/nautilus_trader/models

# Verify
ls -la /home/ajk/Nautilus/nautilus_trader/models/
```

---

## Verification

### System Verification Script

Create and run comprehensive verification:

```bash
cd /home/ajk/Nautilus/nautilus_trader
source .venv/bin/activate

python << 'EOF'
import os
import sys
from moomoo import OpenQuoteContext, OpenSecTradeContext, TrdEnv

print("=" * 60)
print("MOOMOO RL SYSTEM VERIFICATION")
print("=" * 60)

# 1. Python Environment
print("\n1. Python Environment:")
try:
    import nautilus_trader
    import moomoo
    import torch
    import numpy as np
    import pandas as pd
    print(f"  ✓ Python: {sys.version.split()[0]}")
    print(f"  ✓ NautilusTrader: {nautilus_trader.__version__}")
    print(f"  ✓ Moomoo API: {moomoo.__version__}")
    print(f"  ✓ PyTorch: {torch.__version__}")
except ImportError as e:
    print(f"  ✗ Missing dependency: {e}")

# 2. Docker Services
print("\n2. Docker Services:")
import subprocess
result = subprocess.run(['docker', 'ps'], capture_output=True, text=True)
services = ['postgres', 'redis', 'grafana', 'prometheus']
for svc in services:
    if svc in result.stdout.lower():
        print(f"  ✓ {svc.capitalize()} running")
    else:
        print(f"  ✗ {svc.capitalize()} not found")

# 3. OpenD Connection
print("\n3. OpenD Gateway:")
try:
    ctx = OpenQuoteContext(host="127.0.0.1", port=11111)
    ret, data = ctx.get_global_state()
    if ret == 0:
        print("  ✓ Connected to OpenD")
        print(f"    Market: {data.get('market_us')}")
    else:
        print(f"  ✗ Connection failed: {data}")
    ctx.close()
except Exception as e:
    print(f"  ✗ Error: {e}")

# 4. Paper Trading Account
print("\n4. Paper Trading Account:")
try:
    trd_ctx = OpenSecTradeContext(host="127.0.0.1", port=11111)
    ret, accounts = trd_ctx.get_acc_list()
    if ret == 0:
        paper_accts = [r for _, r in accounts.iterrows() if r['trd_env'] == TrdEnv.SIMULATE]
        if paper_accts:
            print(f"  ✓ Paper account: {paper_accts[0]['acc_id']}")
        else:
            print("  ✗ No paper trading account")
    else:
        print(f"  ✗ Account query failed")
    trd_ctx.close()
except Exception as e:
    print(f"  ✗ Error: {e}")

# 5. US Market Data Permissions
print("\n5. Market Data Permissions:")
try:
    ctx = OpenQuoteContext(host="127.0.0.1", port=11111)
    ret, _ = ctx.subscribe(['US.AAPL'], ['QUOTE'])
    if ret == 0:
        print("  ✓ US market data authorized")
    else:
        print("  ✗ US market data not authorized")
        print("    Action: Enable in Moomoo app")
    ctx.close()
except Exception as e:
    print(f"  ✗ Error: {e}")

# 6. RL Framework
print("\n6. RL Framework:")
try:
    from ajk_strategies.rl_framework.agents.base_agent import SimpleRuleAgent
    from ajk_strategies.rl_framework.training.experience_buffer import PrioritizedReplayBuffer
    print("  ✓ RL components available")
except ImportError as e:
    print(f"  ✗ Missing RL component: {e}")

# 7. Strategies
print("\n7. Trading Strategies:")
try:
    from ajk_strategies.rl_strategies import (
        RLPairsTradingStrategy,
        RLMomentumBreakoutStrategy,
    )
    print("  ✓ Pairs Trading strategy")
    print("  ✓ Momentum Breakout strategy")
except ImportError as e:
    print(f"  ✗ Strategy import failed: {e}")

print("\n" + "=" * 60)
print("VERIFICATION COMPLETE")
print("=" * 60)
print("\nIf all checks show ✓, you're ready to start trading!")
print("Run: python scripts/start_paper_trading_moomoo.py")
EOF
```

**All checks should pass before proceeding to trading.**

---

## Next Steps

1. **Configure strategies** → See [STRATEGIES.md](STRATEGIES.md)
2. **Start trading** → See [QUICKSTART.md](QUICKSTART.md)
3. **Monitor performance** → See [MONITORING.md](MONITORING.md)
4. **Troubleshoot issues** → See [TROUBLESHOOTING.md](TROUBLESHOOTING.md)

---

**Installation complete!** You're ready to start paper trading.
