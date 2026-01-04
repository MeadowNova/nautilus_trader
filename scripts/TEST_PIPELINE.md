# 🚀 Testing Complete Pipeline - Step by Step

## ✅ Pre-Flight Checklist

### 1. Docker Services Status
```bash
docker ps | grep -E "postgres|redis|prometheus|grafana|ai_metrics"
```
**Expected**: All containers showing "Up" and "(healthy)"

✅ **CONFIRMED**: All services running!

### 2. Database Schema Applied
```bash
docker exec nautilus_postgres psql -U nautilus -d nautilus_trader -c \
  "SELECT table_name FROM information_schema.tables 
   WHERE table_schema='ai_extensions' AND table_name LIKE 'live_%';"
```
**Expected**: 8 tables (live_sessions, live_positions, live_orders, etc.)

### 3. VPN Active
```bash
curl -s https://ipapi.co/json/ | grep -E "country|ip"
```
**Expected**: Your VPN country/IP

### 4. API Keys Loaded
Already confirmed in `.env.local` ✅

---

## 🎯 Test Sequence

### Step 1: Start Paper Trading (Terminal 1)

```bash
cd /home/ajk/Nautilus/nautilus_trader
source nautilus_env/bin/activate

# Start paper trading
python scripts/start_paper_trading.py
```

**Expected Output**:
```
✅ Loaded environment from: /home/ajk/Nautilus/nautilus_trader/infrastructure/.env.local
✅ API credentials verified
   Using API key: xxxxxxxx...
✅ All clients verified as testnet mode

🔧 Initializing trading node...
✅ Paper trading system ready!

📊 Monitoring:
   - Grafana: http://localhost:3000
   - Prometheus: http://localhost:9090
```

**Watch for**:
- Connection to Bybit testnet
- Instrument loading (BTCUSDT-LINEAR.BYBIT)
- First market data received

---

### Step 2: Verify Database (Terminal 2)

Wait **5 seconds** after paper trading starts, then:

```bash
# Check session created
docker exec nautilus_postgres psql -U nautilus -d nautilus_trader -c \
  "SELECT trader_id, strategy_id, status, started_at 
   FROM ai_extensions.live_sessions 
   WHERE trader_id = 'PAPER-TRADER-001' 
   ORDER BY started_at DESC LIMIT 1;"
```

**Expected**:
```
     trader_id      |      strategy_id       | status  |         started_at
--------------------+------------------------+---------+----------------------------
 PAPER-TRADER-001   | AIAdaptiveStrategyV3   | RUNNING | 2024-12-XX XX:XX:XX.XXXXXX
```

✅ **Success**: Session is RUNNING

---

### Step 3: Check Prometheus Metrics (Terminal 2)

Wait **15 seconds** after paper trading starts:

```bash
# Check session metrics
curl -s http://localhost:9100/metrics | grep "ai_live_session_status"

# Check equity metrics
curl -s http://localhost:9100/metrics | grep "ai_live_equity_total"

# Check position metrics
curl -s http://localhost:9100/metrics | grep "ai_live_open_positions"
```

**Expected**:
```
ai_live_session_status{trader_id="PAPER-TRADER-001",strategy_id="AIAdaptiveStrategyV3",status="RUNNING"} 1.0
ai_live_equity_total{trader_id="PAPER-TRADER-001",strategy_id="AIAdaptiveStrategyV3"} 100000.0
ai_live_open_positions{trader_id="PAPER-TRADER-001",strategy_id="AIAdaptiveStrategyV3"} 0.0
```

✅ **Success**: Metrics are being collected

---

### Step 4: Open Grafana Dashboard

1. Open browser: http://localhost:3000
2. Login (if needed): admin / VEltbU0u5gCbl4V7tiTSzHZ2
3. Navigate: Dashboards → Live Trading Monitor
4. Or direct link: http://localhost:3000/d/live-trading-monitor

**Expected within 30 seconds**:
- ✅ "Active Sessions" shows: 1
- ✅ "Session Runtime" counting up
- ✅ "Total Equity" shows: ~100,000 USDT
- ✅ "Open Positions" shows: 0 (until first signal)
- ✅ Auto-refreshing every 10 seconds

---

### Step 5: Monitor Trading Activity (5-10 minutes)

**Watch for**:

#### In Terminal 1 (Paper Trading Logs):
- Market data updates
- Strategy calculations
- Order submissions (when signals generate)
- Position updates

#### In Database:
```bash
# Check for orders
docker exec nautilus_postgres psql -U nautilus -d nautilus_trader -c \
  "SELECT order_id, instrument_id, side, quantity, status 
   FROM ai_extensions.live_orders 
   ORDER BY submitted_at DESC LIMIT 5;"

# Check for positions
docker exec nautilus_postgres psql -U nautilus -d nautilus_trader -c \
  "SELECT instrument_id, side, quantity, unrealized_pnl 
   FROM ai_extensions.live_positions 
   WHERE is_open = true;"

# Check equity snapshots
docker exec nautilus_postgres psql -U nautilus -d nautilus_trader -c \
  "SELECT total_equity, cash_balance, captured_at 
   FROM ai_extensions.live_equity_snapshots 
   ORDER BY captured_at DESC LIMIT 10;"
```

#### In Grafana:
- Equity curve should update
- Orders submitted counter should increment
- If positions open, position table should populate
- P&L gauges should move

---

## 🎉 Success Criteria

### ✅ Immediate (< 1 minute)
- [ ] Paper trading starts without errors
- [ ] Session appears in database with RUNNING status
- [ ] Prometheus exposes `ai_live_*` metrics
- [ ] Grafana dashboard loads

### ✅ Short Term (< 5 minutes)
- [ ] Market data streaming from Bybit
- [ ] Metrics updating every 15 seconds
- [ ] Grafana panels showing live data
- [ ] Equity snapshots being recorded

### ✅ Medium Term (< 30 minutes)
- [ ] Strategy generates first signal (depends on market)
- [ ] Orders submitted to Bybit testnet
- [ ] Positions opened (if signal confident)
- [ ] Complete data flow: Trading → DB → Prometheus → Grafana

---

## 🐛 Troubleshooting

### Issue: Connection Error to Bybit

**Symptoms**:
```
Error: Connection refused
Error: Authentication failed
```

**Solutions**:
1. Verify VPN is active:
   ```bash
   curl -s https://ipapi.co/json/ | grep country
   ```

2. Test Bybit testnet API:
   ```bash
   curl -s https://api-testnet.bybit.com/v5/market/time
   ```

3. Verify API keys in .env.local (no extra spaces/quotes)

---

### Issue: No Metrics in Prometheus

**Solutions**:
```bash
# 1. Check metrics collector is running
docker logs ai_metrics --tail 50

# 2. Restart metrics collector
docker restart ai_metrics

# 3. Check Prometheus targets
curl http://localhost:9090/api/v1/targets | python3 -m json.tool
```

---

### Issue: No Data in Grafana

**Solutions**:
1. Verify data source: 
   - Go to: http://localhost:3000/datasources
   - Check "Prometheus" is connected

2. Refresh dashboard:
   - Click refresh button (top right)
   - Change time range to "Last 5 minutes"

3. Check if metrics exist:
   ```bash
   curl -s "http://localhost:9090/api/v1/query?query=ai_live_session_status" | python3 -m json.tool
   ```

---

### Issue: Orders Rejected

**Common Causes**:
1. Insufficient testnet balance
   - Login to: https://testnet.bybit.com/
   - Check wallet balance
   - Request testnet funds if needed

2. Invalid instrument
   - Check logs for "instrument not found"
   - Verify BTCUSDT-LINEAR.BYBIT is available

3. Position size too small/large
   - Check strategy configuration
   - Verify min/max order sizes

---

## 📊 Expected Performance

### First 5 Minutes:
- **Orders**: 0-2 (depends on market conditions)
- **Positions**: 0-1
- **Equity Change**: < 1%
- **Metrics Updates**: Every 15 seconds

### First 30 Minutes:
- **Orders**: 2-10
- **Positions**: 1-3 open/closed
- **Win Rate**: N/A (need 5+ closed trades)
- **Dashboard**: Fully populated

### First Hour:
- **Closed Trades**: 3-10
- **Win Rate**: 40-60% (expected for new strategy)
- **Max Drawdown**: < 5%
- **Complete Pipeline**: Fully validated ✅

---

## 🎓 What You're Testing

This pipeline validates:

1. **Live Trading**: Real Bybit testnet connection with streaming data
2. **Order Execution**: Strategy generates signals and submits orders
3. **Database Persistence**: All events captured in PostgreSQL
4. **Metrics Collection**: Python script reads DB every 15 seconds
5. **Prometheus Scraping**: Metrics exposed on port 9100
6. **Grafana Visualization**: Real-time dashboards
7. **Complete Audit Trail**: Full history for analysis

This is the **exact same infrastructure** professional trading firms use!

---

## 🚀 Ready to Start?

Run this command:

```bash
cd /home/ajk/Nautilus/nautilus_trader
source nautilus_env/bin/activate
python scripts/start_paper_trading.py
```

Then follow the test sequence above. Good luck! 🎉
