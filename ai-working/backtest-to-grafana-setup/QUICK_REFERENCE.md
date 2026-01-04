# Quick Reference Guide

## 🚀 Quick Commands

### Run Backtest (50k bars, ~20 seconds)

```bash
cd /home/ajk/Nautilus/nautilus_trader
source activate_env.sh
python ajk_strategies/run_backtest_v3_gpu_validation.py
```

### Check Results

```bash
# View latest results
cat backtest_results/gpu_validation_50k_summary.json | python3 -m json.tool | head -50

# Check Prometheus metrics
curl http://localhost:9100/metrics | grep ai_gpu_validation

# Query database
psql -h localhost -p 5435 -U nautilus -d nautilus_trader -c \
  "SELECT * FROM ai_extensions.v_backtest_performance ORDER BY completed_at DESC LIMIT 5;"
```

### Start Paper Trading

```bash
# Set testnet credentials
export BINANCE_TESTNET_API_KEY="your-testnet-key"
export BINANCE_TESTNET_API_SECRET="your-testnet-secret"

# Start paper trading
python scripts/start_paper_trading.py
```

---

## 📊 Monitoring URLs

| Service | URL | Purpose |
|---------|-----|---------|
| Grafana | http://localhost:3000 | Dashboards & visualization |
| Prometheus | http://localhost:9090 | Metrics & alerts |
| Metrics API | http://localhost:9100/metrics | Raw metrics endpoint |
| Postgres | localhost:5435 | Database (use psql) |
| Redis | localhost:6378 | Cache (use redis-cli) |

---

## 🗄️ Key Directories

```
/home/ajk/Nautilus/nautilus_trader/
├── ajk_strategies/
│   ├── ai_adaptive_stragey_v3.py       # Strategy implementation
│   ├── run_backtest_v3_gpu_validation.py  # Backtest runner
│   ├── models/                          # AI models (XGBoost, LSTM)
│   └── monitoring/
│       ├── metrics_collector.py         # Metrics collection
│       └── metrics_definitions.py       # Prometheus metrics
├── backtest_results/                    # JSON backtest outputs
├── data/nautilus/                       # Market data (parquet files)
├── infrastructure/
│   ├── .env.local                       # Configuration secrets
│   ├── monitoring/
│   │   ├── grafana/dashboards/          # Grafana JSON dashboards
│   │   └── prometheus/prometheus.yml    # Prometheus config
│   └── postgres/                        # Database schemas
├── logs/                                # Application logs
└── scripts/
    ├── run_backtest_with_metrics.sh     # Backtest wrapper
    └── start_paper_trading.py           # Paper trading launcher
```

---

## 🔧 Configuration Files

### Strategy Config

**File**: `ajk_strategies/ai_adaptive_stragey_v3.py`

```python
class AIAdaptiveStrategyConfigV3:
    max_bars_per_run: int = 50_000      # Limit bars for quick tests
    enable_monte_carlo: bool = False     # Disable for speed
    confidence_threshold: float = 0.75   # Trade signal threshold
    max_bars_in_position: int = 100      # Max holding period
```

### Database Connection

**File**: `infrastructure/.env.local`

```bash
DB_HOST=localhost
DB_PORT=5435
DB_NAME=nautilus_trader
DB_USER=nautilus
DB_PASSWORD=<from-env-file>
```

### API Keys (Paper Trading)

**Environment Variables**:

```bash
BINANCE_TESTNET_API_KEY="your-key"
BINANCE_TESTNET_API_SECRET="your-secret"
```

Get testnet keys: https://testnet.binance.vision/

---

## 🔍 Common Queries

### PostgreSQL

```sql
-- Latest backtest results
SELECT run_name, instrument_id, total_pnl, win_rate, sharpe_ratio, completed_at
FROM ai_extensions.v_backtest_performance
ORDER BY completed_at DESC LIMIT 5;

-- Strategy comparison
SELECT strategy_id, instrument_id, runs, avg_total_pnl_pct, avg_win_rate
FROM ai_extensions.v_strategy_comparison;

-- Recent trades
SELECT instrument_id, side, quantity, entry_price, exit_price, pnl, entry_timestamp
FROM ai_extensions.v_recent_trades
ORDER BY entry_timestamp DESC LIMIT 20;
```

### Prometheus (PromQL)

```promql
# Latest GPU validation P&L
ai_gpu_validation_net_pnl{summary_file="gpu_validation_50k_summary.json"}

# Redis health
ai_redis_up

# Backtest duration histogram
histogram_quantile(0.95, ai_backtest_duration_seconds_bucket)
```

### Redis

```bash
# Connect to Redis
redis-cli -h localhost -p 6378 -a <password>

# Check keys
KEYS *

# Monitor commands
MONITOR
```

---

## ⚡ Performance Benchmarks

### Backtest Performance (RTX 4070 GPU)

| Bars | Runtime | Trades | P&L% |
|------|---------|--------|------|
| 50,000 | 21s | 16 | +14,404% |
| 200,000 | 60s | 5 | +856,534% |

*Note: High P&L% due to leverage and compounding*

### Hardware Requirements

**Minimum**:
- CPU: 4 cores
- RAM: 8 GB
- GPU: Optional (10x faster)
- Storage: 10 GB

**Recommended**:
- CPU: 8+ cores
- RAM: 16 GB
- GPU: NVIDIA RTX 3060+ (8GB VRAM)
- Storage: 50 GB (SSD)

---

## 🚨 Safety Checks

### Before Paper Trading

```bash
# 1. Verify testnet mode
grep "testnet" ajk_strategies/paper_trading_config.py

# 2. Test API connection
curl https://testnet.binance.vision/api/v3/ping

# 3. Check credentials
echo $BINANCE_TESTNET_API_KEY | cut -c1-8

# 4. Validate strategy config
python -c "from ajk_strategies.ai_adaptive_stragey_v3 import AIAdaptiveStrategyConfigV3; print(AIAdaptiveStrategyConfigV3())"
```

### Emergency Stop

```bash
# Stop all running processes
pkill -f "start_paper_trading"

# Close all positions (if needed - manual via exchange)

# Check logs
tail -100 logs/paper_trading_*.log
```

---

## 📈 Grafana Dashboard IDs

| Dashboard | Path | Purpose |
|-----------|------|---------|
| AI Strategy Performance | `/d/ai-strategy-performance` | Overall P&L, win rate |
| Trade Analytics | `/d/ai-trade-analytics` | Individual trades, equity curve |
| Risk Monitoring | `/d/ai-risk-monitoring` | Drawdowns, circuit breakers |
| Regime Analysis | `/d/ai-regime-analysis` | Market regime detection |
| Infrastructure | `/d/infrastructure-overview` | Service health |

---

## 🐛 Quick Troubleshooting

### Issue: Backtest not starting

```bash
# Check GPU
nvidia-smi

# Check virtual environment
which python

# Check dependencies
pip list | grep -E "(nautilus|xgboost|torch)"
```

### Issue: No metrics in Grafana

```bash
# 1. Check metrics exporter
curl http://localhost:9100/metrics | head

# 2. Check Prometheus targets
curl http://localhost:9090/api/v1/targets | python3 -m json.tool

# 3. Restart services
docker restart nautilus_prometheus nautilus_grafana
```

### Issue: Database connection failed

```bash
# Check PostgreSQL
docker ps | grep postgres

# Test connection
pg_isready -h localhost -p 5435

# Check logs
docker logs nautilus_postgres
```

---

## 📞 Support & Resources

- **Documentation**: `ai-working/backtest-to-grafana-setup/README.md`
- **Infrastructure Status**: `INFRASTRUCTURE_STATUS.md`
- **NautilusTrader Docs**: https://nautilustrader.io
- **Strategy Details**: `ajk_strategies/docs/`

---

**Last Updated**: October 10, 2025
