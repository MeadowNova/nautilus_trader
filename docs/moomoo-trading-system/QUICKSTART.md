# Quick Start Guide

**Get trading with the Moomoo RL system in 10 minutes**

## Before You Start

### CRITICAL: Market Data Permissions

**BLOCKER**: You must enable US market data permissions in your Moomoo account before trading.

**Error you'll see without permissions:**
```
No right to subscribe the quote for US.XLE
```

**How to fix:**
1. Open Moomoo mobile app
2. Go to Settings → Quotes Permission
3. Enable "US Market Real-time Quotes"
4. Wait 2-3 minutes for activation
5. Restart OpenD gateway

See [CONFIGURATION.md](CONFIGURATION.md#market-data-permissions) for detailed steps with screenshots.

### What You Need

- [ ] Moomoo account with paper trading enabled
- [ ] **US market data permissions enabled** (see above)
- [ ] OpenD gateway downloaded from https://www.moomoo.com/download/OpenD
- [ ] Terminal access with Python 3.11+
- [ ] 8GB+ RAM available

## Step 1: Start OpenD Gateway (1 minute)

Open a separate terminal and start OpenD:

```bash
# Navigate to OpenD installation directory
cd /path/to/OpenD

# Linux/macOS
./OpenD

# Windows
OpenD.exe

# You should see:
# "OpenD started on port 11111"
```

**Keep this terminal running** - OpenD must stay active while trading.

### Verify OpenD is Running

```bash
# Check port 11111 is listening
lsof -i :11111

# Expected output:
# OpenD   12345 user   10u  IPv4  ...  TCP *:11111 (LISTEN)
```

## Step 2: Verify Connection (1 minute)

Test that OpenD can connect to Moomoo:

```bash
cd /home/ajk/Nautilus/nautilus_trader
source .venv/bin/activate

python << 'EOF'
from moomoo import OpenQuoteContext, TrdEnv

# Connect to OpenD
ctx = OpenQuoteContext(host="127.0.0.1", port=11111)
ret, data = ctx.get_global_state()

if ret == 0:
    print("✓ Connected to OpenD successfully!")
    print(f"  US Market: {data.get('market_us')}")
    print(f"  Server Version: {data.get('server_ver')}")
else:
    print(f"✗ Connection failed: {data}")

ctx.close()
EOF
```

**Expected Output:**
```
✓ Connected to OpenD successfully!
  US Market: MORNING  (or AFTERNOON/CLOSED depending on time)
  Server Version: 904
```

**If connection fails**, see [TROUBLESHOOTING.md](TROUBLESHOOTING.md#opend-connection-issues).

## Step 3: Start Infrastructure (2 minutes)

Start PostgreSQL, Redis, Prometheus, and Grafana:

```bash
cd /home/ajk/Nautilus/nautilus_trader/infrastructure/docker

# Start all services
docker compose --env-file ../.env.local up -d

# Verify services are healthy (wait ~30 seconds)
docker ps --format "table {{.Names}}\t{{.Status}}\t{{.Ports}}"
```

**Expected Output:**
```
NAMES                STATUS                PORTS
nautilus_postgres    Up 30 seconds         0.0.0.0:5435->5432/tcp
nautilus_redis       Up 30 seconds         0.0.0.0:6378->6379/tcp
nautilus_prometheus  Up 30 seconds         0.0.0.0:9090->9090/tcp
nautilus_grafana     Up 30 seconds         0.0.0.0:3000->3000/tcp
ai_metrics           Up 30 seconds         0.0.0.0:9100->9100/tcp
```

**If services fail to start**, see [TROUBLESHOOTING.md](TROUBLESHOOTING.md#docker-service-issues).

## Step 4: Start Paper Trading (1 minute)

```bash
cd /home/ajk/Nautilus/nautilus_trader
source .venv/bin/activate

python scripts/start_paper_trading_moomoo.py
```

You should see:

```
MOOMOO OPEND PAPER TRADING - RL ENHANCED STRATEGIES

MODE: Paper Trading with Reinforcement Learning
Gateway: Moomoo OpenD (localhost:11111)

Strategies:
1. RL Pairs Trading (XLE/XLF)
2. RL Momentum Breakout (NVDA, AMD, META)

1. Verifying OpenD connection...
   Market state (US): MORNING
   Paper trading accounts: 1

2. Creating paper trading configuration...

3. Initializing RL framework...
   Experience buffer capacity: 100000
   Agent epsilon (exploration): 0.1

4. Initializing trading node...

5. Creating RL-enhanced strategies...
   Added: RLPairsTradingStrategy
   Added: RLMomentumBreakoutStrategy

6. Initializing training orchestrator...

============================================================
PAPER TRADING SYSTEM READY
============================================================

Trader ID: MOOMOO-RL-PAPER-001
Log directory: ./logs/
Model checkpoints: ./models/

Active Strategies:
  - RLPairsTradingStrategy (XLE/XLF)
  - RLMomentumBreakoutStrategy (NVDA, AMD, META)

RL Training:
  - Background training every 100 new experiences
  - Model saved on shutdown

Press Ctrl+C to stop trading
```

**If you see errors**, check:
1. **Market data permissions** - Most common issue
2. OpenD is running
3. Infrastructure services are up
4. Market hours (US: 9:30 AM - 4:00 PM ET)

See [TROUBLESHOOTING.md](TROUBLESHOOTING.md) for solutions.

## Step 5: Monitor Trading (5 minutes)

### View Real-Time Logs

Open a new terminal:

```bash
cd /home/ajk/Nautilus/nautilus_trader

# Follow logs in real-time
tail -f logs/MOOMOO-RL-PAPER-001_*.log

# Filter for specific events
grep "on_bar\|TradeTick\|OrderAccepted" logs/MOOMOO-RL-PAPER-001_*.log
```

### Access Dashboards

| Service | URL | Default Credentials |
|---------|-----|---------------------|
| Grafana | http://localhost:3000 | admin / (see .env.local) |
| Prometheus | http://localhost:9090 | None required |

**Grafana Dashboards:**
- Live Trading Monitor (P&L, positions, orders)
- RL Training Metrics (buffer size, epsilon, TD error)
- System Health (CPU, memory, latency)

### Check Strategy Status

```bash
# View last 50 log entries
tail -n 50 logs/MOOMOO-RL-PAPER-001_*.log

# Check for quote updates (data is flowing)
grep "QuoteTick" logs/MOOMOO-RL-PAPER-001_*.log | tail -n 10

# Check for bar updates (strategies are receiving data)
grep "on_bar" logs/MOOMOO-RL-PAPER-001_*.log | tail -n 10

# Check for orders (strategies are trading)
grep "OrderAccepted\|OrderFilled" logs/MOOMOO-RL-PAPER-001_*.log
```

## Step 6: Stop Trading Gracefully

Press `Ctrl+C` in the trading terminal. The system will:

1. Stop accepting new signals
2. Close all open positions (if configured)
3. Save RL model checkpoint to `models/`
4. Print training summary
5. Shutdown cleanly

**Expected Output:**
```
^C
Shutdown signal received...

Stopping orchestrator...
Saved model checkpoint: models/moomoo_rl_agent_20251209_153045.pt

Training Summary:
  Total epochs: 15
  Buffer size: 847
  Avg policy loss: 0.0234

Stopping trading node...
Shutdown complete
```

### Stop Infrastructure Services

```bash
cd /home/ajk/Nautilus/nautilus_trader/infrastructure/docker

# Stop all services
docker compose --env-file ../.env.local down

# Or keep services running for next session (recommended)
# Just stop trading script with Ctrl+C
```

## What to Expect

### During Market Hours (9:30 AM - 4:00 PM ET)

**First 10 Minutes:**
- Strategies load instruments
- Quote data starts flowing
- Bars begin accumulating
- No trades yet (building history)

**After 15-20 Minutes:**
- Pairs trading: Monitors XLE/XLF spread z-score
- Momentum: Watches for 15-day high breakouts with volume
- First trades may occur if entry conditions met

**First Trade Example:**
```log
[INFO] RLPairsTradingStrategy: Z-score: 2.31 (above entry threshold 2.25)
[INFO] RLPairsTradingStrategy: Entering LONG_SPREAD position
[INFO] OrderAccepted: BUY 100 XLE.MOOMOO @ 85.23
[INFO] OrderAccepted: SELL 100 XLF.MOOMOO @ 42.15
[INFO] OrderFilled: BUY 100 XLE.MOOMOO @ 85.23 FILLED
[INFO] OrderFilled: SELL 100 XLF.MOOMOO @ 42.15 FILLED
```

### Outside Market Hours

The system connects but strategies will:
- Accumulate historical data
- Not generate signals (no price movement)
- Show "Market: CLOSED" in logs

**This is normal.** Resume trading during market hours.

## Verification Checklist

After 30 minutes of trading, verify:

- [ ] Logs show quote updates every few seconds
- [ ] Bars are being generated (check "on_bar" in logs)
- [ ] RL experience buffer is growing (check logs or Grafana)
- [ ] No repeated error messages
- [ ] Grafana dashboards show live data
- [ ] Model checkpoints are being saved

If any item fails, see [TROUBLESHOOTING.md](TROUBLESHOOTING.md).

## Next Steps

### Immediate (Week 1)
1. Let system run during market hours
2. Collect 30+ trades for statistical significance
3. Review daily logs for errors
4. Monitor risk metrics in Grafana

### Short-Term (Week 2-4)
1. Review strategy performance: `python scripts/analyze_performance.py`
2. Adjust parameters if needed (see [STRATEGIES.md](STRATEGIES.md))
3. Enable RL training if win rate > 35%
4. Consider position size increase (1% → 1.5%)

### Before Live Trading
- [ ] Paper trading for 4+ weeks minimum
- [ ] Win rate > 40% across strategies
- [ ] Max drawdown < 10%
- [ ] Risk management tested (stop losses, position limits)
- [ ] Sharpe ratio > 1.0

**See [SETUP.md](SETUP.md) for detailed configuration and [STRATEGIES.md](STRATEGIES.md) for strategy optimization.**

## Common First-Run Issues

### 1. "No right to subscribe the quote for US.XLE"

**Cause:** US market data permissions not enabled.

**Fix:** Enable in Moomoo app → Settings → Quotes Permission → US Market Real-time Quotes.

Wait 2-3 minutes, restart OpenD.

### 2. OpenD Connection Timeout

**Cause:** OpenD not running or wrong port.

**Fix:**
```bash
# Check OpenD is running
ps aux | grep OpenD

# Check port
lsof -i :11111

# Restart OpenD if needed
killall OpenD && ./OpenD
```

### 3. Strategies Not Trading

**Causes:**
- Outside market hours
- Entry conditions not met (z-score too low, no breakouts)
- Daily loss limit hit
- Risk limits reached

**Check:**
```bash
# Verify market is open
grep "Market.*OPEN\|MORNING\|AFTERNOON" logs/*.log

# Check current z-score (pairs strategy)
grep "z-score" logs/*.log | tail -n 5

# Check RSI values (momentum strategy)
grep "RSI" logs/*.log | tail -n 5
```

### 4. Docker Services Won't Start

**Cause:** Port conflicts or resource constraints.

**Fix:**
```bash
# Check for port conflicts
lsof -i :5435  # PostgreSQL
lsof -i :6378  # Redis
lsof -i :3000  # Grafana
lsof -i :9090  # Prometheus

# If ports in use, edit infrastructure/.env.local
# Change DB_PORT, REDIS_PORT, etc.

# Restart with new ports
docker compose --env-file ../.env.local down
docker compose --env-file ../.env.local up -d
```

**For more issues, see [TROUBLESHOOTING.md](TROUBLESHOOTING.md).**

## Quick Reference

```bash
# Complete startup sequence
cd /home/ajk/Nautilus/nautilus_trader
./OpenD &                                                    # Terminal 1
cd infrastructure/docker && docker compose --env-file ../.env.local up -d
cd ../.. && source .venv/bin/activate
python scripts/start_paper_trading_moomoo.py                # Terminal 2
tail -f logs/*.log                                          # Terminal 3

# Stop everything
Ctrl+C  # In trading terminal
docker compose --env-file ../.env.local down  # In infrastructure/docker
killall OpenD
```

---

**Need help?** Check [TROUBLESHOOTING.md](TROUBLESHOOTING.md) or [CONFIGURATION.md](CONFIGURATION.md) for detailed setup.
