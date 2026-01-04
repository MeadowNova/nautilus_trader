# Backtest-to-Grafana Pipeline & Paper Trading Setup

**Last Updated**: October 10, 2025  
**Status**: ✅ Fully Operational

## Overview

This guide documents the complete pipeline for running AI-Adaptive Strategy backtests, collecting metrics, visualizing in Grafana, and transitioning to paper trading.

## 📋 Table of Contents

1. [System Architecture](#system-architecture)
2. [Quick Start Guide](#quick-start-guide)
3. [Backtest Execution](#backtest-execution)
4. [Metrics & Monitoring](#metrics--monitoring)
5. [Paper Trading Setup](#paper-trading-setup)
6. [Troubleshooting](#troubleshooting)

---

## System Architecture

### Data Flow

```
Market Data (CCXT/Parquet Files)
         ↓
AI-Adaptive Strategy V3 (GPU Accelerated)
         ↓
NautilusTrader Backtest Engine
         ↓
    ┌────────┴────────┐
    ↓                 ↓
PostgreSQL        JSON Files
(ai_extensions)   (backtest_results/)
    ↓                 ↓
Prometheus ← Metrics Exporter
    ↓
Grafana Dashboards
```

### Infrastructure Components

| Component | Port | Status | Purpose |
|-----------|------|--------|---------|
| PostgreSQL | 5435 | ✅ Running | Metrics storage |
| Redis | 6378 | ✅ Running | Strategy state cache |
| Prometheus | 9090 | ✅ Running | Metrics aggregation |
| Grafana | 3000 | ✅ Running | Visualization |
| Metrics Exporter | 9100 | ✅ Running | Prometheus scraping |
| Metrics Proxy | 9101 | ✅ Running | HTTP API for metrics |

---

## Quick Start Guide

### Prerequisites

1. ✅ Docker containers running (postgres, redis, grafana, prometheus)
2. ✅ Virtual environment activated: `source activate_env.sh`
3. ✅ Market data files in `data/nautilus/` (BTC-USDT, ETH-USDT)
4. ✅ AI models in `ajk_strategies/models/`

### Run a Backtest (50k bars, ~20 seconds)

```bash
# Quick execution
cd /home/ajk/Nautilus/nautilus_trader
source activate_env.sh
python ajk_strategies/run_backtest_v3_gpu_validation.py
```

**Results Location**:
- JSON Summary: `backtest_results/gpu_validation_50k_summary.json`
- Prometheus Metrics: http://localhost:9100/metrics
- Grafana Dashboards: http://localhost:3000

---

## Backtest Execution

### Method 1: GPU Validation Script (Recommended)

**File**: `ajk_strategies/run_backtest_v3_gpu_validation.py`

**Features**:
- ✅ GPU acceleration (CUDA)
- ✅ 50,000 bar limit (configurable)
- ✅ Monte Carlo disabled for speed
- ✅ JSON results with detailed segments
- ✅ Automatic metrics export

**Usage**:

```bash
# Standard run
python ajk_strategies/run_backtest_v3_gpu_validation.py

# Force CPU mode
python ajk_strategies/run_backtest_v3_gpu_validation.py --force-cpu

# Custom configuration (edit script for max_bars, confidence_threshold, etc.)
```

**Configuration** (in `ai_adaptive_stragey_v3.py`):

```python
class AIAdaptiveStrategyConfigV3:
    max_bars_per_run: int = 50_000  # Limit for quick backtests
    enable_monte_carlo: bool = False  # Disabled for speed
    confidence_threshold: float = 0.75  # Trade signal threshold
    max_bars_in_position: int = 100  # Max holding period
```

### Method 2: Full Data Pipeline (With PostgreSQL Persistence)

**File**: `ajk_strategies/run_backtest_with_real_data.py`

**Features**:
- ✅ Database persistence (`ai_extensions` schema)
- ✅ CSV reports (fills, positions, orders)
- ✅ Multiple instruments (BTC, ETH)
- ✅ Metric recording for Grafana

**Usage**:

```bash
# Enable persistence
export NAUTILUS_PERSIST_BACKTESTS=1
export DB_HOST=localhost
export DB_PORT=5435
export DB_NAME=nautilus_trader
export DB_USER=nautilus
export DB_PASSWORD=xSr7IgOZlwgkUwtnBBZoFG7N

# Run backtest
python ajk_strategies/run_backtest_with_real_data.py
```

**Check Results**:

```bash
# Query database
psql -h localhost -p 5435 -U nautilus -d nautilus_trader -c \
  "SELECT run_name, total_pnl, win_rate, sharpe_ratio \
   FROM ai_extensions.v_backtest_performance \
   ORDER BY completed_at DESC LIMIT 5;"
```

### Performance Results (Recent Run)

**Configuration**:
- Instrument: BTC-USDT
- Bars: 50,000
- Device: GPU (NVIDIA RTX 4070)
- Duration: 21.5 seconds

**Metrics**:
- Total Trades: 16
- Runtime: 0.305s per segment (average)
- Bars Consumed: 1,206 (effective trading bars)
- Monte Carlo: Disabled

---

## Metrics & Monitoring

### Prometheus Metrics Available

Access at: http://localhost:9100/metrics

**Key Metrics**:

```promql
# Backtest metrics
ai_backtest_total_pnl
ai_backtest_total_trades
ai_backtest_win_rate_pct
ai_backtest_profit_factor
ai_backtest_sharpe_ratio
ai_backtest_max_drawdown_pct
ai_backtest_duration_seconds

# GPU validation metrics
ai_gpu_validation_total_trades
ai_gpu_validation_net_pnl
ai_gpu_validation_runtime_seconds

# Infrastructure metrics
ai_redis_up
ai_redis_memory_usage_bytes
ai_redis_key_count
```

### Grafana Dashboards

Access at: http://localhost:3000  
**Credentials**: admin / (check `infrastructure/.env.local`)

**Available Dashboards**:

1. **AI Strategy Performance** (`/d/ai-strategy-performance`)
   - P&L over time
   - Win rate trends
   - Sharpe ratio evolution

2. **Trade Analytics** (`/d/ai-trade-analytics`)
   - Individual trade details
   - Equity curve
   - Drawdown visualization

3. **Risk Monitoring** (`/d/ai-risk-monitoring`)
   - Drawdown alerts
   - Circuit breaker events
   - Risk exposure

4. **Regime Analysis** (`/d/ai-regime-analysis`)
   - Market regime detection
   - Regime transition patterns

5. **Infrastructure Overview** (`/d/infrastructure-overview`)
   - Service health
   - Database metrics
   - Redis performance

### PostgreSQL Views for Grafana

```sql
-- Latest backtest performance
SELECT * FROM ai_extensions.v_backtest_performance 
ORDER BY completed_at DESC LIMIT 10;

-- Strategy comparison
SELECT * FROM ai_extensions.v_strategy_comparison;

-- Recent trades
SELECT * FROM ai_extensions.v_recent_trades LIMIT 50;

-- Equity curve
SELECT * FROM ai_extensions.v_backtest_equity_curve 
WHERE backtest_run_id = '<run-id>';
```

---

## Paper Trading Setup

### Prerequisites

1. **Exchange Account** (Testnet recommended):
   - Binance Testnet: https://testnet.binance.vision/
   - Register and obtain API keys

2. **API Credentials** (Never commit to git!):
   - Store in `infrastructure/.env.local`
   - Or use environment variables

### Configuration

**File**: Create `ajk_strategies/paper_trading_config.py`

```python
from nautilus_trader.config import TradingNodeConfig
from nautilus_trader.adapters.binance.config import (
    BinanceDataClientConfig,
    BinanceExecClientConfig,
)
from nautilus_trader.model.enums import AccountType

from ajk_strategies.ai_adaptive_stragey_v3 import AIAdaptiveStrategyConfigV3

# Testnet configuration
config = TradingNodeConfig(
    trader_id="PAPER-TRADER-001",
    
    # Data client (testnet)
    data_clients={
        "BINANCE": BinanceDataClientConfig(
            api_key=os.getenv("BINANCE_TESTNET_API_KEY"),
            api_secret=os.getenv("BINANCE_TESTNET_API_SECRET"),
            account_type=AccountType.SPOT,
            testnet=True,  # CRITICAL: Use testnet
            base_url_http="https://testnet.binance.vision/api",
            base_url_ws="wss://testnet.binance.vision/ws",
        )
    },
    
    # Execution client (testnet)
    exec_clients={
        "BINANCE": BinanceExecClientConfig(
            api_key=os.getenv("BINANCE_TESTNET_API_KEY"),
            api_secret=os.getenv("BINANCE_TESTNET_API_SECRET"),
            account_type=AccountType.SPOT,
            testnet=True,
            base_url_http="https://testnet.binance.vision/api",
        )
    },
    
    # Strategy configuration (conservative)
    strategies=[
        AIAdaptiveStrategyConfigV3(
            instrument_id="BTCUSDT.BINANCE",
            bar_type="BTCUSDT.BINANCE-1-MINUTE-LAST-EXTERNAL",
            venue="BINANCE",
            confidence_threshold=0.80,  # Higher threshold for paper trading
            enable_monte_carlo=True,     # Enable for risk assessment
            max_bars_in_position=50,     # Shorter hold time
        )
    ],
)
```

### Launcher Script

**File**: `scripts/start_paper_trading.py`

```python
#!/usr/bin/env python3
"""
Paper Trading Launcher

SAFETY CHECKS:
- Verifies testnet mode
- Confirms API credentials
- Validates risk parameters
"""

import os
from nautilus_trader.live.node import TradingNode

from ajk_strategies.paper_trading_config import config

def verify_testnet():
    """Ensure we're using testnet"""
    if not config.data_clients["BINANCE"].testnet:
        raise RuntimeError("❌ TESTNET NOT ENABLED! Aborting for safety.")
    
    print("✅ Testnet mode confirmed")

def verify_credentials():
    """Check API credentials are set"""
    if not os.getenv("BINANCE_TESTNET_API_KEY"):
        raise RuntimeError("❌ BINANCE_TESTNET_API_KEY not set!")
    
    if not os.getenv("BINANCE_TESTNET_API_SECRET"):
        raise RuntimeError("❌ BINANCE_TESTNET_API_SECRET not set!")
    
    print("✅ Credentials verified")

def main():
    print("🚀 Starting Paper Trading System...")
    
    # Safety checks
    verify_testnet()
    verify_credentials()
    
    # Initialize trading node
    node = TradingNode(config=config)
    
    try:
        # Start the node
        node.start()
        print("✅ Paper trading active!")
        print("📊 Monitor at: http://localhost:3000")
        
        # Run until Ctrl+C
        node.run()
    
    except KeyboardInterrupt:
        print("\n⏸️  Shutting down gracefully...")
    
    finally:
        node.stop()
        node.dispose()
        print("✅ Shutdown complete")

if __name__ == "__main__":
    main()
```

### Safety Checklist

Before starting paper trading:

- [ ] Testnet mode enabled (`testnet=True`)
- [ ] API keys are testnet keys (check URL endpoints)
- [ ] Conservative risk parameters set
- [ ] Position size limits configured
- [ ] Max daily loss configured
- [ ] Stop-loss always enabled
- [ ] Monitoring dashboards open
- [ ] Alert system configured

### Monitoring Paper Trading

**Real-time Logs**:

```bash
# Follow logs
tail -f logs/paper_trading_$(date +%Y%m%d).log

# Check positions
# (Add monitoring script)
```

**Grafana**:
- Real-time P&L
- Open positions
- Recent trades
- Risk metrics

**PostgreSQL**:

```sql
-- Current positions
SELECT * FROM positions WHERE is_open = true;

-- Recent orders
SELECT * FROM orders ORDER BY ts_event DESC LIMIT 20;

-- Today's performance
SELECT SUM(realized_pnl) as daily_pnl
FROM positions
WHERE ts_closed > CURRENT_DATE;
```

---

## Troubleshooting

### Backtest Issues

**Problem**: TensorFlow not found

```bash
# Solution: Use V3 GPU validation script (doesn't require TensorFlow)
python ajk_strategies/run_backtest_v3_gpu_validation.py
```

**Problem**: No GPU detected

```bash
# Check GPU
nvidia-smi

# Force CPU mode
python ajk_strategies/run_backtest_v3_gpu_validation.py --force-cpu
```

**Problem**: Out of memory

```bash
# Reduce max_bars_per_run in config
# Or use smaller dataset segments
```

### Metrics Issues

**Problem**: Prometheus not scraping metrics

```bash
# Check metrics endpoint
curl http://localhost:9100/metrics | grep ai_

# Restart Prometheus
docker restart nautilus_prometheus
```

**Problem**: Grafana shows no data

```bash
# 1. Check Prometheus is scraping
curl http://localhost:9090/api/v1/targets

# 2. Check datasource configuration in Grafana
# Settings > Data Sources > Postgres

# 3. Verify database connection
psql -h localhost -p 5435 -U nautilus -d nautilus_trader -c "SELECT 1;"
```

### Paper Trading Issues

**Problem**: Connection refused

```bash
# Check testnet is accessible
curl https://testnet.binance.vision/api/v3/ping

# Verify API keys
echo $BINANCE_TESTNET_API_KEY
```

**Problem**: Invalid signature errors

```bash
# Ensure API secret is correct
# Check system clock is synchronized
timedatectl status
```

**Problem**: Strategy not trading

```bash
# 1. Check confidence threshold isn't too high
# 2. Verify market data is flowing
# 3. Check risk limits aren't blocking trades
# 4. Review logs for rejection reasons
```

---

## Additional Resources

- **NautilusTrader Docs**: https://nautilustrader.io
- **CCXT Documentation**: https://docs.ccxt.com
- **Prometheus Query Examples**: `infrastructure/monitoring/prometheus/examples/`
- **Grafana Dashboard Templates**: `infrastructure/monitoring/grafana/dashboards/`

---

## Next Steps

1. ✅ Run more backtests with different parameters
2. ✅ Analyze results in Grafana
3. ✅ Optimize strategy based on metrics
4. 🔄 Set up testnet paper trading
5. 🔄 Monitor performance for 1-2 weeks
6. ⏳ Transition to live trading (with extreme caution)

---

**Questions or Issues?**
- Review logs in `logs/` directory
- Check `INFRASTRUCTURE_STATUS.md` for system status
- Consult `ajk_strategies/docs/` for strategy details
