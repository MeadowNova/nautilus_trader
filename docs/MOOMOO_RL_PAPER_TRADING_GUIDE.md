# Moomoo RL Paper Trading System - Complete Setup Guide

## Overview

This guide provides step-by-step instructions to set up and run the Moomoo RL Paper Trading System using NautilusTrader with reinforcement learning enhanced strategies.

**System Components:**
- NautilusTrader Core (Rust/Python hybrid trading engine)
- Moomoo OpenD API (Market data and execution)
- RL Framework (State builder, reward calculator, experience buffer)
- PostgreSQL (Trade persistence and analytics)
- Prometheus + Grafana (Monitoring dashboards)

**Trading Strategies:**
1. **RL Pairs Trading** (XLE/XLF) - Mean reversion with z-score signals
2. **RL Momentum Breakout** (NVDA, AMD, META) - Technical breakout with volume confirmation

---

## Prerequisites

### 1. System Requirements
- OS: Linux (Ubuntu 22.04+), macOS, or Windows with WSL2
- RAM: 8GB minimum, 16GB recommended
- Python: 3.11+ (3.13 supported)
- Docker: Required for infrastructure services

### 2. Moomoo Account & OpenD
- Moomoo trading account (US market access)
- OpenD gateway installed and running
- Paper trading enabled on your account

---

## Step 1: Install OpenD Gateway

### Download OpenD
```bash
# Visit: https://www.moomoo.com/download/openD
# Download the appropriate version for your OS
```

### Start OpenD
```bash
# Linux/macOS
./OpenD

# Windows
OpenD.exe
```

**Verify OpenD is running:**
```bash
lsof -i :11111  # Should show OpenD listening
```

---

## Step 2: Set Up Python Environment

### Activate the Virtual Environment
```bash
cd /home/ajk/Nautilus/nautilus_trader
source .venv/bin/activate
```

### Install Dependencies
```bash
# Install moomoo-api
python -m pip install moomoo-api

# Verify installation
python -c "from moomoo import OpenQuoteContext; print('moomoo-api installed successfully')"
```

---

## Step 3: Start Infrastructure Services

### Configure Environment Variables
```bash
# Check that .env.local exists
ls -la infrastructure/.env.local

# Key variables (already configured):
# DB_PORT=5435
# REDIS_PORT=6378
# GRAFANA_PORT=3000
# PROMETHEUS_PORT=9090
```

### Start Docker Services
```bash
cd infrastructure/docker

# Start all services
docker compose --env-file ../.env.local up -d

# Verify services are running
docker ps --format "table {{.Names}}\t{{.Status}}\t{{.Ports}}"
```

**Expected Services:**
| Service | Port | Status |
|---------|------|--------|
| nautilus_postgres | 5435 | healthy |
| nautilus_redis | 6378 | healthy |
| nautilus_prometheus | 9090 | healthy |
| nautilus_grafana | 3000 | healthy |
| ai_metrics | 9100 | healthy |

---

## Step 4: Verify OpenD Connection

```bash
source .venv/bin/activate
python << 'EOF'
from moomoo import OpenQuoteContext, OpenSecTradeContext, TrdEnv

# Test connection
quote_ctx = OpenQuoteContext(host="127.0.0.1", port=11111)
ret, data = quote_ctx.get_global_state()

if ret == 0:
    print(f"Connected to OpenD!")
    print(f"  Market US: {data.get('market_us')}")
    print(f"  Server Version: {data.get('server_ver')}")
else:
    print(f"Connection failed: {data}")

quote_ctx.close()
EOF
```

**Expected Output:**
```
Connected to OpenD!
  Market US: AFTERNOON  (or MORNING/CLOSED depending on time)
  Server Version: 904
```

---

## Step 5: Configure Risk Parameters

### Risk Configuration Summary ($100,000 Account)

| Parameter | Value | Description |
|-----------|-------|-------------|
| Max Position Size | $10,000 (10%) | Per instrument limit |
| Max Concurrent Positions | 8 | Across all strategies |
| Daily Loss Limit | 3% ($3,000) | Halts new trades |
| Max Drawdown | 10% ($10,000) | Emergency liquidation |
| Per-Trade Risk (1R) | 1% ($1,000) | Stop loss sizing |
| Orders per Minute | 10 | Rate limit |

### R-Multiple Targets

| Level | R-Multiple | Profit |
|-------|------------|--------|
| Stop Loss | -1R | -$1,000 |
| Target 1 | +1R | +$1,000 |
| Target 2 | +2R | +$2,000 |
| Target 3 | +3R | +$3,000 |

---

## Step 6: Start Paper Trading

### Option A: Run the Orchestrator Script
```bash
cd /home/ajk/Nautilus/nautilus_trader
source .venv/bin/activate
python scripts/start_paper_trading_moomoo.py
```

### Option B: Manual Start with Custom Configuration
```python
# custom_paper_trading.py
from nautilus_trader.live.node import TradingNode
from nautilus_trader.config import TradingNodeConfig, LoggingConfig
from nautilus_trader.model.identifiers import TraderId

from nautilus_trader.adapters.moomoo.config import (
    MoomooGatewayConfig,
    MoomooDataClientConfig,
    MoomooExecClientConfig,
)
from nautilus_trader.adapters.moomoo.factories import (
    MoomooLiveDataClientFactory,
    MoomooLiveExecClientFactory,
)
from nautilus_trader.ajk_strategies.rl_strategies import (
    RLPairsTradingStrategy,
    RLPairsTradingConfig,
)

# Configuration
gateway = MoomooGatewayConfig(
    host="127.0.0.1",
    port=11111,
    trading_mode="SIMULATE",  # Paper trading
)

config = TradingNodeConfig(
    trader_id=TraderId("MOOMOO-RL-001"),
    logging=LoggingConfig(log_level="INFO"),
    data_clients={"MOOMOO": MoomooDataClientConfig(gateway=gateway)},
    exec_clients={"MOOMOO": MoomooExecClientConfig(gateway=gateway)},
)

# Create node
node = TradingNode(config=config)
node.add_data_client_factory("MOOMOO", MoomooLiveDataClientFactory)
node.add_exec_client_factory("MOOMOO", MoomooLiveExecClientFactory)

# Add strategy
strategy = RLPairsTradingStrategy(RLPairsTradingConfig(
    instrument_id_a="XLE.MOOMOO",
    instrument_id_b="XLF.MOOMOO",
    zscore_entry=2.25,
    position_size_pct=0.08,
))
node.trader.add_strategy(strategy)

# Run
node.build()
node.run()
```

---

## Step 7: Monitor Trading

### Access Dashboards

| Dashboard | URL | Credentials |
|-----------|-----|-------------|
| Grafana | http://localhost:3000 | admin / (see .env.local) |
| Prometheus | http://localhost:9090 | None |

### Key Metrics to Monitor

1. **Strategy Performance**
   - P&L by strategy (pairs vs momentum)
   - Win rate (rolling 20 trades)
   - R-multiple distribution

2. **Risk Metrics**
   - Current drawdown
   - Daily loss vs limit
   - Position exposure

3. **RL Training**
   - Experience buffer size
   - Epsilon (exploration rate)
   - TD error mean

### View Logs
```bash
# Real-time logs
tail -f logs/MOOMOO-RL-PAPER-001_*.log

# Error filtering
grep -i error logs/MOOMOO-RL-PAPER-001_*.log
```

---

## Step 8: Review Results

### Database Queries (PostgreSQL)
```bash
# Connect to database
docker exec -it nautilus_postgres psql -U nautilus -d nautilus_trader

# View recent trades
SELECT * FROM trades ORDER BY timestamp DESC LIMIT 20;

# Calculate daily P&L
SELECT DATE(timestamp), SUM(pnl) as daily_pnl
FROM trades
GROUP BY DATE(timestamp)
ORDER BY DATE(timestamp) DESC;

# Strategy performance
SELECT strategy_id, COUNT(*) as trades,
       AVG(pnl) as avg_pnl,
       SUM(CASE WHEN pnl > 0 THEN 1 ELSE 0 END)::float / COUNT(*) as win_rate
FROM trades
GROUP BY strategy_id;
```

### Prometheus Queries
```promql
# Experience buffer size
nautilus_rl_buffer_size

# Trading P&L
rate(nautilus_trading_pnl_total[1h])

# Order rate
rate(nautilus_orders_total[5m])
```

---

## Strategy Parameters Reference

### Pairs Trading (Recommended)
```python
RLPairsTradingConfig(
    instrument_id_a="XLE.MOOMOO",
    instrument_id_b="XLF.MOOMOO",
    lookback_period=40,           # Rolling window for stats
    zscore_entry=2.25,            # Entry threshold (2.25 sigma)
    zscore_exit=0.25,             # Exit threshold (mean reversion)
    zscore_stop=3.5,              # Stop loss threshold
    position_size_pct=0.08,       # 8% per leg
    max_holding_bars=80,          # Max bars before time stop
    use_rl=True,                  # Enable RL decision making
)
```

### Momentum Breakout (Recommended)
```python
RLMomentumBreakoutConfig(
    instrument_ids=("NVDA.MOOMOO", "AMD.MOOMOO", "META.MOOMOO"),
    benchmark_id="SPY.MOOMOO",
    breakout_lookback=15,         # 15-day high breakout
    volume_multiplier=1.75,       # 1.75x avg volume required
    rsi_period=14,
    rsi_min=50.0,                 # Lower RSI bound
    rsi_max=70.0,                 # Upper RSI bound
    profit_target_atr=2.5,        # 2.5x ATR profit target
    trailing_stop_atr=2.0,        # 2.0x ATR trailing stop
    position_size_pct=0.06,       # 6% per position
    max_concurrent=2,             # Max 2 positions
    max_holding_bars=40,          # Max bars in position
    use_rl=True,
)
```

---

## Troubleshooting

### OpenD Connection Issues
```bash
# Check if OpenD is running
ps aux | grep OpenD

# Check port binding
netstat -tulpn | grep 11111

# Restart OpenD if needed
killall OpenD && ./OpenD
```

### Docker Service Issues
```bash
# View logs
docker compose --env-file ../.env.local logs -f postgres

# Restart specific service
docker compose --env-file ../.env.local restart grafana

# Full restart
docker compose --env-file ../.env.local down
docker compose --env-file ../.env.local up -d
```

### Strategy Not Trading
1. **Check market hours** - US markets: 9:30 AM - 4:00 PM ET
2. **Verify data subscription** - Check logs for quote updates
3. **Review risk limits** - Daily loss limit may be hit
4. **Check z-score/RSI** - Current values may not meet entry criteria

---

## Quick Reference Commands

```bash
# Start everything
cd /home/ajk/Nautilus/nautilus_trader
source .venv/bin/activate
cd infrastructure/docker && docker compose --env-file ../.env.local up -d
cd ../.. && python scripts/start_paper_trading_moomoo.py

# Stop trading
Ctrl+C  # Graceful shutdown with model checkpoint

# View status
docker ps  # Services
tail -f logs/*.log  # Trading logs

# Access dashboards
# Grafana: http://localhost:3000
# Prometheus: http://localhost:9090
```

---

## Expected Performance (After 30+ Trades)

| Metric | Pairs Trading | Momentum | Combined |
|--------|---------------|----------|----------|
| Win Rate | 55% | 42% | 48% |
| Avg R-Multiple | 0.8R | 1.8R | 1.2R |
| Sharpe Ratio | 1.5 | 1.0 | 1.3 |
| Max Drawdown | 8% | 12% | 10% |
| Expectancy | 0.20R | 0.20R | 0.20R |

---

## Next Steps

1. **Week 1**: Run paper trading, collect 30+ trades
2. **Week 2**: Review performance, adjust parameters if needed
3. **Week 3**: Enable RL training if win rate > 35%
4. **Week 4**: Evaluate for position size increase (1% → 1.5%)

**Important**: Do not increase risk until expectancy is positive and proven over 50+ trades.
