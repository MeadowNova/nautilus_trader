# Prometheus/Grafana Pipeline - Complete Guide

**Status**: ✅ **FULLY OPERATIONAL**  
**Date**: October 10, 2025

---

## Overview

The backtest metrics pipeline is now working end-to-end:

```
PostgreSQL (ai_extensions) → Metrics Collector → Prometheus → Grafana
```

---

## Current Status

### ✅ What's Working

1. **Database** (PostgreSQL)
   - Schema: `ai_extensions` with 21 tables + 7 views
   - Test data inserted and visible
   - Views returning correct data

2. **Metrics Collector** (Port 9100)
   - Reading from database
   - Exporting Prometheus metrics
   - Auto-refreshing every scrape

3. **Prometheus** (Port 9090)
   - Scraping metrics successfully
   - Targets all healthy
   - Data retention active

4. **Grafana** (Port 3000)
   - Dashboards configured
   - PostgreSQL datasource connected
   - Ready to visualize

---

## Data Flow Explained

### Step 1: Backtest Execution → Database

When you run a backtest with persistence:

```python
# Set environment variable
os.environ["NAUTILUS_PERSIST_BACKTESTS"] = "1"

# Run backtest (example: scripts/run_backtest_persist_db.py)
# Results saved to:
# - ai_extensions.backtest_runs (metadata)
# - ai_extensions.backtest_metrics (individual metrics)
# - ai_extensions.backtest_trades (trade details) - optional
```

### Step 2: Database Views → Aggregation

The `v_backtest_performance` view aggregates data:

```sql
SELECT * FROM ai_extensions.v_backtest_performance
ORDER BY completed_at DESC LIMIT 10;
```

This view combines:
- Backtest run metadata
- Trade statistics (from backtest_trades)
- Metrics (from backtest_metrics)
- Calculated performance indicators

### Step 3: Metrics Collector → Prometheus Format

The metrics collector (`ajk_strategies/monitoring/metrics_collector.py`):

1. Queries the database every 15-30 seconds
2. Reads from `v_backtest_performance` and other views
3. Exposes metrics at http://localhost:9100/metrics

Example metrics exported:

```prometheus
ai_backtest_total_pnl{strategy_id="ai_adaptive_v3",run_name="test_btc"} 15000.0
ai_backtest_win_rate_pct{strategy_id="ai_adaptive_v3",run_name="test_btc",instrument_id="BTCUSDT.BINANCE"} 66.67
ai_backtest_sharpe_ratio{strategy_id="ai_adaptive_v3",run_name="test_btc",instrument_id="BTCUSDT.BINANCE"} 1.85
```

### Step 4: Prometheus → Scraping

Prometheus configuration (`infrastructure/monitoring/prometheus/prometheus.yml`):

```yaml
scrape_configs:
  - job_name: 'ai_metrics'
    static_configs:
      - targets: ['ai_metrics:9100']
    scrape_interval: 15s
```

### Step 5: Grafana → Visualization

Grafana reads from:
1. **Prometheus** datasource - for time-series metrics
2. **PostgreSQL** datasource - for detailed queries on views

---

## Testing the Pipeline

### Test Data Inserted ✅

We've inserted two test backtest runs:

| Run Name | Instrument | Trades | Win Rate | P&L % | Sharpe |
|----------|------------|--------|----------|-------|--------|
| prometheus_test_btc_20241010 | BTCUSDT.BINANCE | 12 | 66.67% | 15.0% | 1.85 |
| prometheus_test_eth_20241010 | ETHUSDT.BINANCE | 18 | 61.11% | 8.5% | 1.42 |

### Verify Each Step

**1. Check Database**:

```bash
PGPASSWORD=xSr7IgOZlwgkUwtnBBZoFG7N psql -h localhost -p 5435 -U nautilus -d nautilus_trader -c \
  "SELECT run_name, instrument_id, calculated_win_rate, sharpe_ratio 
   FROM ai_extensions.v_backtest_performance 
   ORDER BY completed_at DESC LIMIT 5;"
```

**2. Check Metrics Endpoint**:

```bash
curl http://localhost:9100/metrics | grep ai_backtest_win_rate
```

Expected output:
```
ai_backtest_win_rate_pct{...run_name="prometheus_test_btc_20241010"...} 66.67
ai_backtest_win_rate_pct{...run_name="prometheus_test_eth_20241010"...} 61.11
```

**3. Check Prometheus**:

```bash
# Open browser
http://localhost:9090

# Query:
ai_backtest_win_rate_pct
```

**4. Check Grafana**:

```bash
# Open browser
http://localhost:3000

# Navigate to: AI Strategy Performance dashboard
# You should see the test data
```

---

## Running Real Backtests with Persistence

### Method 1: Quick Script (Recommended for Testing)

```bash
cd /home/ajk/Nautilus/nautilus_trader
source activate_env.sh

# Run the persistence script
python scripts/run_backtest_persist_db.py
```

This script:
- Runs a 50k bar backtest (BTC-USDT, 2024 data)
- Takes ~2-3 minutes
- Automatically persists to PostgreSQL
- Exports metrics immediately

### Method 2: Full Backtest Script

```bash
cd /home/ajk/Nautilus/nautilus_trader
source activate_env.sh

# Set persistence environment variable
export NAUTILUS_PERSIST_BACKTESTS=1

# Run full backtest
python ajk_strategies/run_backtest_with_real_data.py
```

This script:
- Runs comprehensive backtests (BTC + ETH)
- Includes CSV reports
- Full database persistence
- Suitable for production use

---

## Available Metrics

### Backtest Performance Metrics

| Metric | Description | Labels |
|--------|-------------|--------|
| `ai_backtest_total_pnl` | Total profit/loss in currency | strategy_id, run_name |
| `ai_backtest_total_pnl_pct` | P&L percentage | strategy_id, run_name, instrument_id |
| `ai_backtest_total_trades` | Number of trades executed | strategy_id, run_name, instrument_id |
| `ai_backtest_win_rate_pct` | Win rate percentage | strategy_id, run_name, instrument_id |
| `ai_backtest_profit_factor` | Profit factor ratio | strategy_id, run_name, instrument_id |
| `ai_backtest_sharpe_ratio` | Sharpe ratio | strategy_id, run_name, instrument_id |
| `ai_backtest_max_drawdown_pct` | Maximum drawdown | strategy_id, run_name |
| `ai_backtest_duration_seconds` | Backtest runtime (histogram) | - |

### GPU Validation Metrics

| Metric | Description | Labels |
|--------|-------------|--------|
| `ai_gpu_validation_total_trades` | Trades in GPU validation | summary_file, instrument, device |
| `ai_gpu_validation_net_pnl` | Net P&L from GPU run | summary_file, instrument, device |
| `ai_gpu_validation_runtime_seconds` | GPU backtest runtime | summary_file, instrument, device |

### Infrastructure Metrics

| Metric | Description |
|--------|-------------|
| `ai_redis_up` | Redis availability (1=up, 0=down) |
| `ai_redis_memory_usage_bytes` | Redis memory usage |
| `ai_redis_key_count` | Number of keys in Redis |

---

## Grafana Dashboard Queries

### Example PostgreSQL Queries for Grafana

**Latest Performance**:

```sql
SELECT 
    completed_at as time,
    run_name,
    calculated_win_rate as win_rate,
    sharpe_ratio,
    profit_factor
FROM ai_extensions.v_backtest_performance
WHERE $__timeFilter(completed_at)
ORDER BY completed_at DESC
LIMIT 50;
```

**Strategy Comparison**:

```sql
SELECT 
    strategy_id,
    instrument_id,
    AVG(avg_total_pnl_pct) as avg_pnl,
    AVG(avg_win_rate) as avg_winrate
FROM ai_extensions.v_strategy_comparison
GROUP BY strategy_id, instrument_id;
```

### Example Prometheus Queries (PromQL)

**Win Rate Over Time**:

```promql
ai_backtest_win_rate_pct{strategy_id="ai_adaptive_v3"}
```

**P&L Comparison**:

```promql
sum by (instrument_id) (ai_backtest_total_pnl_pct)
```

**Average Sharpe Ratio**:

```promql
avg(ai_backtest_sharpe_ratio{strategy_id="ai_adaptive_v3"})
```

---

## Troubleshooting

### Issue: Metrics show 0.0

**Cause**: The `v_backtest_performance` view calculates some metrics from `backtest_trades` table

**Solution**: Ensure your backtest script populates the trades table, or use the metrics from the JSON `metrics` field in `backtest_runs`

### Issue: No data in Grafana dashboards

**Checklist**:

1. Check database has data:
   ```bash
   psql ... -c "SELECT COUNT(*) FROM ai_extensions.backtest_runs;"
   ```

2. Check metrics endpoint:
   ```bash
   curl http://localhost:9100/metrics | grep ai_backtest
   ```

3. Check Prometheus targets:
   ```bash
   curl http://localhost:9090/api/v1/targets
   ```

4. Restart metrics collector:
   ```bash
   docker restart ai_metrics
   ```

5. Check Grafana datasource:
   - Settings → Data Sources → Postgres
   - Test connection

### Issue: Metrics collector not updating

**Solution**: Restart the metrics collector container:

```bash
docker restart ai_metrics

# Check logs
docker logs ai_metrics --tail 50
```

---

## Next Steps

### Immediate

1. ✅ Run a real backtest with `scripts/run_backtest_persist_db.py`
2. ✅ Verify data appears in Grafana
3. ✅ Customize dashboards to your needs

### Short Term

4. Set up alerting rules in Prometheus
5. Create custom Grafana panels
6. Automate backtest runs (cron jobs)

### Long Term

7. Implement live trading metrics
8. Add real-time position tracking
9. Set up email/Slack notifications

---

## Files Reference

### Key Configuration Files

| File | Purpose |
|------|---------|
| `infrastructure/postgres/02-ai-extensions.sql` | Database schema |
| `infrastructure/postgres/04-dashboard-views.sql` | Grafana views |
| `ajk_strategies/monitoring/metrics_collector.py` | Metrics collection logic |
| `ajk_strategies/monitoring/metrics_definitions.py` | Prometheus metric definitions |
| `infrastructure/monitoring/prometheus/prometheus.yml` | Prometheus config |
| `infrastructure/monitoring/grafana/dashboards/*.json` | Grafana dashboards |

### Useful Scripts

| Script | Purpose |
|--------|---------|
| `scripts/run_backtest_persist_db.py` | Quick backtest with persistence |
| `scripts/populate_test_metrics.sql` | Insert test data |
| `scripts/verify_system.sh` | Check all components |

---

## Summary

The complete Prometheus/Grafana pipeline is now operational:

✅ PostgreSQL database with backtest data  
✅ Metrics collector reading and exporting  
✅ Prometheus scraping successfully  
✅ Grafana ready to visualize  
✅ Test data populated and visible  

**You can now**:
1. Run backtests and see results in Grafana immediately
2. Query historical performance via PostgreSQL views
3. Create custom dashboards and alerts
4. Monitor real-time metrics during paper/live trading

---

**Questions or issues?** Check the main README.md or run `bash scripts/verify_system.sh`

**Last Updated**: October 10, 2025
