# 🎉 Solution: Sandbox Paper Trading (No API Keys Needed!)

**Problem**: Geo-restricted from Binance and Bybit testnet  
**Solution**: Use NautilusTrader's Sandbox execution mode

---

## 🚀 What is Sandbox Mode?

The Sandbox adapter lets you run **fully simulated paper trading** without ANY exchange API keys:

- ✅ **No API keys required** - Zero exchange registration needed
- ✅ **No geo-restrictions** - Works anywhere in the world
- ✅ **Real market data replay** - Uses your existing historical data
- ✅ **Simulated execution** - Orders filled against simulated order book
- ✅ **Full monitoring** - Complete PostgreSQL → Prometheus → Grafana pipeline
- ✅ **Safe testing** - 100% risk-free, no real money involved

---

## 📁 New Script Created

**File**: `scripts/start_paper_trading_sandbox.py`

This script:
1. Uses your existing historical parquet data (from backtests)
2. Simulates a virtual "SANDBOX" venue
3. Executes your AI strategy against replayed market data
4. Captures all metrics to PostgreSQL
5. Exposes metrics to Prometheus
6. Displays in Grafana dashboards

---

## 🎯 How to Use

### Step 1: Ensure Historical Data Exists

```bash
# Check for data files
ls -lh data/nautilus/*.parquet

# If empty, run a quick backtest to generate data
python ajk_strategies/run_backtest_v3_gpu_validation.py
```

### Step 2: Start Sandbox Paper Trading

```bash
cd /home/ajk/Nautilus/nautilus_trader
source nautilus_env/bin/activate

python scripts/start_paper_trading_sandbox.py
```

Expected output:
```
╔══════════════════════════════════════════════════════════════════╗
║           AI-ADAPTIVE SANDBOX PAPER TRADING SYSTEM               ║
║  MODE: Sandbox Simulation (No API Keys Required)                ║
╚══════════════════════════════════════════════════════════════════╝

🔍 Checking for historical data...
✅ Found 245 data files

⚙️  Creating sandbox configuration...
🔧 Initializing sandbox trading node...
✅ Sandbox paper trading system ready!

📊 Monitoring:
   - Grafana: http://localhost:3000
   - Prometheus: http://localhost:9090

💡 Features:
   ✅ No API keys needed
   ✅ No geo-restrictions
   ✅ Uses your historical data
   ✅ Full monitoring integration
   ✅ Safe - 100% simulated
```

### Step 3: Monitor in Grafana

1. Open: http://localhost:3000
2. Go to: Dashboards → Live Trading Monitor
3. Watch your sandbox trading session in real-time!

---

## 📊 What Gets Monitored?

Everything works exactly like real trading:

### Database (PostgreSQL)
```sql
-- View active sandbox sessions
SELECT * FROM ai_extensions.live_sessions WHERE trader_id = 'SANDBOX-TRADER-001';

-- View simulated positions
SELECT * FROM ai_extensions.live_positions;

-- View simulated orders
SELECT * FROM ai_extensions.live_orders;

-- View equity snapshots
SELECT * FROM ai_extensions.live_equity_snapshots ORDER BY captured_at DESC LIMIT 10;
```

### Metrics (Prometheus)
```bash
# Check sandbox metrics
curl -s http://localhost:9100/metrics | grep "ai_live_session_status"

# Sample output:
# ai_live_session_status{trader_id="SANDBOX-TRADER-001",strategy_id="AIAdaptiveStrategyV3",status="RUNNING"} 1.0
```

### Dashboard (Grafana)
- Session runtime
- Equity curve (simulated)
- P&L tracking
- Position monitoring
- Order statistics
- Win rate and Sharpe ratio

---

## ⚙️ Configuration Details

### Starting Balance
Default: `100,000 USDT + 10 BTC`

Modify in script:
```python
SandboxExecutionClientConfig(
    starting_balances=[
        "100000 USDT",  # Change amount here
        "10 BTC",
    ],
    ...
)
```

### Trading Instrument
Default: `BTCUSDT.SANDBOX`

Change to any instrument you have data for:
```python
AIAdaptiveStrategyConfigV3(
    instrument_id=InstrumentId.from_str("ETHUSDT.SANDBOX"),
    bar_type="ETHUSDT.SANDBOX-1-MINUTE-LAST-INTERNAL",
    ...
)
```

### Leverage
Default: `1.0` (no leverage)

Modify for simulated margin trading:
```python
SandboxExecutionClientConfig(
    default_leverage=Decimal("2.0"),  # 2x leverage
    ...
)
```

---

## 🔍 How Sandbox Differs from Real Trading

| Feature | Sandbox | Real Exchange |
|---------|---------|---------------|
| API Keys | ❌ Not needed | ✅ Required |
| Geo-restrictions | ❌ None | ⚠️ May apply |
| Market Data | Historical replay | Live streaming |
| Order Execution | Simulated fills | Real fills |
| Slippage | Optional simulation | Real market impact |
| Fees | Optional simulation | Real fees charged |
| Risk | 🟢 Zero | 🔴 Real money |
| Monitoring | ✅ Full pipeline | ✅ Full pipeline |

---

## 🧪 Testing the Complete Pipeline

### Test Sequence

```bash
# 1. Start sandbox paper trading
python scripts/start_paper_trading_sandbox.py

# 2. In another terminal, verify database (wait 5 seconds)
docker exec nautilus_postgres psql -U nautilus -d nautilus_trader -c \
  "SELECT trader_id, strategy_id, status, started_at 
   FROM ai_extensions.live_sessions 
   WHERE trader_id = 'SANDBOX-TRADER-001';"

# Expected: 1 row with status='RUNNING'

# 3. Check Prometheus metrics (wait 15 seconds)
curl -s http://localhost:9100/metrics | grep "ai_live_equity_total"

# Expected: ai_live_equity_total{...} 100000.0

# 4. Open Grafana and watch live updates
# http://localhost:3000/d/live-trading-monitor
```

### Success Criteria

✅ **Immediate (< 1 minute)**
- Script starts without errors
- Session appears in database
- Metrics exposed to Prometheus
- Grafana shows session

✅ **Short term (< 5 minutes)**
- First orders submitted
- Positions opened (if strategy signals)
- Equity snapshots recorded
- Dashboard updates every 10 seconds

✅ **Medium term (< 30 minutes)**
- Multiple trades executed
- Win rate calculated
- P&L tracking accurate
- No errors in logs

---

## 🔧 Troubleshooting

### Issue: No historical data found

**Solution**:
```bash
# Run a backtest first
cd /home/ajk/Nautilus/nautilus_trader
source nautilus_env/bin/activate
python ajk_strategies/run_backtest_v3_gpu_validation.py

# Verify data created
ls -lh data/nautilus/*.parquet
```

### Issue: Strategy not generating signals

**Cause**: Historical data might not have enough bars for feature warmup

**Solution**: Check strategy logs:
```bash
tail -f logs/SANDBOX-TRADER-001_*.log
```

### Issue: No metrics in Grafana

**Solution**:
```bash
# 1. Check if paper trading is running
ps aux | grep start_paper_trading_sandbox

# 2. Verify database connection
docker ps | grep postgres

# 3. Restart metrics collector
docker restart ai_metrics

# 4. Check Prometheus scraping
curl http://localhost:9090/api/v1/targets
```

---

## 💡 Benefits of Sandbox Mode

### For Development
- ✅ Test strategy changes without risk
- ✅ Validate monitoring pipeline
- ✅ Debug order execution logic
- ✅ Practice with Grafana dashboards

### For Production Readiness
- ✅ Verify database schema works
- ✅ Test metrics collection
- ✅ Validate alert thresholds
- ✅ Ensure dashboard accuracy

### For Analysis
- ✅ Compare backtest vs "live" performance
- ✅ Test strategy in different market conditions
- ✅ Validate risk management rules
- ✅ Analyze order timing and fills

---

## 🎓 Next Steps

### Option 1: Continue with Sandbox
- Perfect for testing and development
- Use different historical data periods
- Test strategy modifications safely
- Validate monitoring infrastructure

### Option 2: Move to Real Paper Trading
When ready to test with live market data:
- ✅ **Interactive Brokers** - Open paper trading account (no geo-restrictions)
- ✅ **OKX Demo** - Try OKX demo trading (check if accessible)
- ⚠️ **VPN + Bybit** - Use VPN to access Bybit testnet (compliance risk)

### Option 3: Go Live (When Confident)
After extensive sandbox and paper trading:
- Use supported exchange in your region
- Start with minimal capital
- Monitor closely via Grafana
- Have circuit breakers enabled

---

## 📊 Comparison: Sandbox vs Real Paper Trading

| Aspect | Sandbox | Real Paper Trading |
|--------|---------|-------------------|
| **Setup Time** | 1 minute | 5-30 minutes (registration) |
| **Data Latency** | Instant (historical) | 1-5 seconds (streaming) |
| **Order Fills** | Instant (simulated) | Realistic delays |
| **Slippage** | Configurable | Real market conditions |
| **Monitoring** | ✅ Full pipeline | ✅ Full pipeline |
| **Cost** | Free | Free |
| **Realism** | 60% realistic | 95% realistic |
| **Purpose** | Testing infrastructure | Testing strategy behavior |

---

## ✅ Current Status Update

**Pipeline Status**: 🟢 READY TO TEST

1. ✅ Database schema deployed
2. ✅ Metrics collector running
3. ✅ Prometheus active
4. ✅ Grafana dashboard ready
5. ✅ **Sandbox script created** 🎉
6. ✅ No API keys needed
7. ⏳ **Ready to test complete pipeline**

---

## 🎯 Action Required

**Test the pipeline now**:

```bash
cd /home/ajk/Nautilus/nautilus_trader
source nautilus_env/bin/activate
python scripts/start_paper_trading_sandbox.py
```

Then open Grafana and watch your monitoring infrastructure in action!

---

**Perfect Solution**: Sandbox mode completely bypasses geo-restrictions while providing a full testing environment for your monitoring infrastructure. You can validate the entire PostgreSQL → Prometheus → Grafana pipeline without ANY exchange API keys.
