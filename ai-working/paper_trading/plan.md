# Paper Trading Implementation Plan

**Project**: NautilusTrader AI-Adaptive Strategy  
**Phase**: Paper Trading with Live Market Data  
**Start Date**: January 2025  
**Goal**: Deploy live paper trading with full monitoring pipeline

---

## Overview

This plan outlines the implementation of paper trading using **Bybit testnet for live market data** combined with **Sandbox execution for simulated trading**, integrated with the complete **PostgreSQL → Prometheus → Grafana monitoring pipeline**.

**Key Decision**: Use existing `start_paper_trading_sandbox.py` script with minimal modifications.

---

## Prerequisites ✅

### Infrastructure (Already Complete)
- [x] PostgreSQL schema deployed (`05-live-trading-schema.sql`)
- [x] Metrics collector extended with live trading support
- [x] Prometheus configured for metrics scraping
- [x] Grafana dashboard created (`live-trading-monitor`)
- [x] Sandbox adapter available
- [x] Bybit adapter available
- [x] AI-Adaptive Strategy V3 ready

### Remaining Requirements
- [ ] Bybit testnet account registration
- [ ] Bybit testnet API keys
- [ ] Environment variables configured

---

## Implementation Phases

### Phase 1: Bybit Testnet Setup (15 minutes)

#### Task 1.1: Register Testnet Account

**Steps:**
1. Visit: https://testnet.bybit.com/
2. Click "Sign Up"
3. Complete registration (email + password)
4. Verify email
5. Login to testnet dashboard

**Expected Outcome:** Registered testnet account with dashboard access

#### Task 1.2: Generate API Keys

**Steps:**
1. Login to testnet dashboard
2. Navigate to: **Account** → **API Management**
3. Click **Create New Key**
4. Configure permissions:
   - ✅ Read-Write (for data + paper orders)
   - ✅ Order (place orders)
   - ✅ Position (manage positions)
   - ❌ Withdrawal (not needed)
5. Complete security verification
6. **Copy and save securely:**
   - API Key
   - API Secret

**Expected Outcome:** API key pair ready for use

**Security Notes:**
- Testnet keys are low-risk (virtual funds only)
- Still, never commit to git
- Store in `.env.local` or environment variables

#### Task 1.3: Fund Testnet Account

**Steps:**
1. In testnet dashboard, navigate to **Assets**
2. Click **Testnet Funds** or similar
3. Request testnet USDT (usually instant)
4. Verify balance shows in account

**Expected Outcome:** Testnet account funded with virtual USDT

**Typical Amounts:**
- Spot: 1,000,000 USDT
- Linear: 100,000 USDT
- Inverse: 10 BTC

### Phase 2: Configuration (10 minutes)

#### Task 2.1: Set Environment Variables

**Location:** `/home/ajk/Nautilus/nautilus_trader/infrastructure/.env.local`

**Add these lines:**
```bash
# Bybit Testnet Credentials
BYBIT_TESTNET_API_KEY=your_testnet_api_key_here
BYBIT_TESTNET_API_SECRET=your_testnet_api_secret_here

# Optional: Override defaults
BYBIT_TESTNET_PRODUCT_TYPE=LINEAR  # LINEAR, SPOT, INVERSE
BYBIT_TESTNET_SYMBOL=BTCUSDT       # Trading pair
```

**Alternative: Export directly**
```bash
export BYBIT_TESTNET_API_KEY="your_key"
export BYBIT_TESTNET_API_SECRET="your_secret"
```

**Expected Outcome:** Credentials available to trading system

#### Task 2.2: Verify .env.local Loading

**Check script loads environment:**

```bash
cd /home/ajk/Nautilus/nautilus_trader

# View relevant section
head -n 20 scripts/start_paper_trading_sandbox.py | grep -A 5 "load_dotenv"
```

**Expected Output:**
```python
env_file = project_root / "infrastructure" / ".env.local"
if env_file.exists():
    load_dotenv(env_file)
    print(f"✅ Loaded environment from: {env_file}")
```

**If not present, add to script:**
```python
from dotenv import load_dotenv

env_file = project_root / "infrastructure" / ".env.local"
if env_file.exists():
    load_dotenv(env_file)
```

**Expected Outcome:** Script can read credentials from `.env.local`

#### Task 2.3: Review Script Configuration

**File:** `scripts/start_paper_trading_sandbox.py`

**Key Configuration Points:**

```python
# 1. Trading Node ID
trader_id=TraderId("SANDBOX-TRADER-001")  # Can customize

# 2. Bybit Data Client
data_clients={
    BYBIT: BybitDataClientConfig(
        api_key=os.getenv("BYBIT_TESTNET_API_KEY"),
        api_secret=os.getenv("BYBIT_TESTNET_API_SECRET"),
        testnet=True,  # ✅ Must be True
        product_types=[BybitProductType.LINEAR],
        ...
    )
}

# 3. Sandbox Execution Client
exec_clients={
    BYBIT: SandboxExecutionClientConfig(
        venue=BYBIT,
        starting_balances=["100000 USDT", "10 BTC"],  # Can adjust
        account_type="MARGIN",
        default_leverage=Decimal("1.0"),  # Can adjust
        ...
    )
}

# 4. Strategy Configuration
strategy_config = AIAdaptiveStrategyConfigV3(
    instrument_id="BTCUSDT-LINEAR.BYBIT",
    bar_type="BTCUSDT-LINEAR.BYBIT-1-MINUTE-LAST-EXTERNAL",
    confidence_threshold=0.75,  # Can adjust
    enable_monte_carlo=True,
    max_bars_in_position=50,  # Can adjust
    ...
)
```

**Customization Options:**
- **Starting Balance**: Adjust based on strategy capital requirements
- **Leverage**: Default 1.0 (no leverage), increase if strategy designed for margin
- **Confidence Threshold**: Lower = more trades, higher = more selective
- **Max Bars in Position**: Position holding time limit

**Expected Outcome:** Configuration reviewed and customized as needed

### Phase 3: Testing (30 minutes)

#### Task 3.1: Test Bybit Connectivity

**Test CCXT integration first:**

```bash
cd /home/ajk/Nautilus/nautilus_trader
source nautilus_env/bin/activate

python test_ccxt_integration.py --exchange bybit --symbol BTC/USDT:USDT
```

**Expected Output:**
```
>>> Testing bybit (BTC/USDT:USDT)
  Ticker last: 42,350.50
  Order book best bid/ask: 42,350.00, 42,351.00
  OHLCV 2025-01-10 14:00: O=42,300.00 C=42,350.00
  OHLCV 2025-01-10 15:00: O=42,350.00 C=42,400.00
  OHLCV 2025-01-10 16:00: O=42,400.00 C=42,350.00
  Recent trades: 3 records
  Supported endpoints:
    fetchTicker: True
    fetchOrderBook: True
    fetchOHLCV: True
    fetchTrades: True
```

**If Failed:**
- Check internet connection
- Verify Bybit testnet is online: https://testnet.bybit.com/
- Try different symbol: `BTC/USDT` (spot) vs `BTC/USDT:USDT` (linear)
- Check if VPN needed (unlikely for testnet)

**Expected Outcome:** Bybit responds to public data requests

#### Task 3.2: Verify Infrastructure

**Check all Docker containers:**

```bash
cd /home/ajk/Nautilus/nautilus_trader

docker ps --format "table {{.Names}}\t{{.Status}}\t{{.Ports}}"
```

**Expected Output:**
```
NAMES               STATUS              PORTS
nautilus_postgres   Up X hours          5432->5432
nautilus_redis      Up X hours          6379->6379
nautilus_prometheus Up X hours          9090->9090
nautilus_grafana    Up X hours          3000->3000
ai_metrics          Up X hours          9100->9100
```

**If any container is down:**

```bash
# Check logs
docker logs <container_name> --tail 50

# Restart if needed
docker restart <container_name>

# Or restart entire stack
cd infrastructure/docker
docker-compose restart
```

**Expected Outcome:** All 5 containers running

#### Task 3.3: Verify Database Schema

```bash
docker exec nautilus_postgres psql -U nautilus -d nautilus_trader -c "
  SELECT table_name 
  FROM information_schema.tables 
  WHERE table_schema = 'ai_extensions' 
  AND table_name LIKE 'live_%'
  ORDER BY table_name;
"
```

**Expected Output:**
```
      table_name       
-----------------------
 live_alerts
 live_equity_snapshots
 live_executions
 live_orders
 live_performance_metrics
 live_positions
 live_sessions
 live_trades
(8 rows)
```

**If missing tables:**

```bash
# Re-run schema creation
docker exec -i nautilus_postgres psql -U nautilus -d nautilus_trader < \
  infrastructure/postgres/05-live-trading-schema.sql
```

**Expected Outcome:** All 8 live trading tables exist

#### Task 3.4: Test Metrics Collector

```bash
# Restart to ensure latest code
docker restart ai_metrics

# Wait for startup
sleep 5

# Check metrics endpoint
curl -s http://localhost:9100/metrics | grep "^ai_live" | head -20
```

**Expected Output:**
```
# HELP ai_live_session_status Status of live trading session
# TYPE ai_live_session_status gauge
# HELP ai_live_session_runtime_seconds Runtime of live trading session
# TYPE ai_live_session_runtime_seconds gauge
# HELP ai_live_equity_total Total equity in account
# TYPE ai_live_equity_total gauge
...
```

**Note:** Values will be 0 or absent until paper trading starts.

**Expected Outcome:** Metrics endpoint exposes live trading metrics

#### Task 3.5: Verify Grafana Dashboard

**Steps:**
1. Open browser: http://localhost:3000
2. Login (default: admin/admin, change on first login)
3. Navigate to: **Dashboards** → **Live Trading Monitor**
4. Verify dashboard loads without errors

**Expected Panels:**
- Session Overview (4-6 stat panels)
- Performance & P&L (graphs and gauges)
- Positions & Orders (table and stats)
- Alerts & Risk (table)

**All panels should show:**
- "No data" or zeros (expected before paper trading starts)
- No error messages
- Proper axis labels

**If dashboard missing:**

```bash
# Import dashboard
docker exec -i nautilus_grafana curl -X POST \
  http://admin:admin@localhost:3000/api/dashboards/db \
  -H "Content-Type: application/json" \
  -d @infrastructure/monitoring/grafana/dashboards/live-trading-monitor.json
```

**Expected Outcome:** Dashboard ready to display data

### Phase 4: Launch Paper Trading (15 minutes)

#### Task 4.1: Activate Virtual Environment

```bash
cd /home/ajk/Nautilus/nautilus_trader
source nautilus_env/bin/activate

# Verify activation
which python3
# Expected: /home/ajk/Nautilus/nautilus_trader/nautilus_env/bin/python3
```

**Expected Outcome:** Virtual environment active

#### Task 4.2: Start Paper Trading

```bash
# Ensure credentials are exported (if not in .env.local)
export BYBIT_TESTNET_API_KEY="your_key"
export BYBIT_TESTNET_API_SECRET="your_secret"

# Launch paper trading
python scripts/start_paper_trading_sandbox.py
```

**Expected Output:**
```
╔══════════════════════════════════════════════════════════════════╗
║           AI-ADAPTIVE SANDBOX PAPER TRADING SYSTEM               ║
║  MODE: Sandbox Simulation (No API Keys Required)                ║
╚══════════════════════════════════════════════════════════════════╝

✅ Loaded environment from: /home/ajk/Nautilus/nautilus_trader/infrastructure/.env.local

🔍 Checking Bybit testnet connection...
✅ Connection to Bybit testnet successful

⚙️  Creating sandbox configuration...
🔧 Initializing sandbox trading node...
📊 Configuring AI-Adaptive strategy...

✅ Sandbox paper trading system ready!

📊 Monitoring:
   - Grafana: http://localhost:3000
   - Prometheus: http://localhost:9090
   - Logs: ./logs/

💡 Features:
   ✅ Real market data from Bybit
   ✅ Simulated order execution
   ✅ Full monitoring integration
   ✅ Safe - 100% paper trading

⚠️  Press Ctrl+C to stop trading

[INFO] 2025-01-10 16:30:00 - SANDBOX-TRADER-001 - Strategy started: AIAdaptiveStrategyV3
[INFO] 2025-01-10 16:30:01 - SANDBOX-TRADER-001 - Subscribed to: BTCUSDT-LINEAR.BYBIT
...
```

**If Errors:**

**Error: "Connection refused"**
- Check Docker containers running: `docker ps`
- Restart infrastructure: `cd infrastructure/docker && docker-compose restart`

**Error: "Invalid API credentials"**
- Verify API keys are correct
- Check environment variables: `echo $BYBIT_TESTNET_API_KEY`
- Ensure `testnet=True` in config

**Error: "Module not found"**
- Virtual environment not activated
- Re-run: `source nautilus_env/bin/activate`

**Error: "Instrument not found"**
- Check Bybit testnet has the trading pair
- Try different symbol in config

**Expected Outcome:** Paper trading system running, logs streaming

#### Task 4.3: Monitor System Startup

**Watch logs for key events (first 2 minutes):**

✅ **Strategy initialization:**
```
[INFO] Strategy started: AIAdaptiveStrategyV3
```

✅ **Data subscription:**
```
[INFO] Subscribed to: BTCUSDT-LINEAR.BYBIT
```

✅ **First market data received:**
```
[DEBUG] Bar received: BTCUSDT-LINEAR.BYBIT-1-MINUTE-LAST-EXTERNAL
```

✅ **Strategy warmup:**
```
[INFO] Building feature matrix...
[INFO] Feature matrix complete: 50 bars
```

⚠️ **Watch for errors:**
```
[ERROR] Failed to connect to...  # Network issues
[WARNING] Order rejected...       # Strategy issues
[ERROR] Database connection...    # Infrastructure issues
```

**Expected Outcome:** Clean startup, data flowing, no errors

### Phase 5: Validation (30-60 minutes)

#### Task 5.1: Database Validation (30 seconds after start)

**Check session created:**

```bash
docker exec nautilus_postgres psql -U nautilus -d nautilus_trader -c "
  SELECT 
    trader_id,
    strategy_id,
    status,
    started_at,
    initial_balance
  FROM ai_extensions.live_sessions
  WHERE trader_id = 'SANDBOX-TRADER-001'
  ORDER BY started_at DESC
  LIMIT 1;
"
```

**Expected Output:**
```
    trader_id      |     strategy_id     | status  |       started_at       | initial_balance
-------------------+---------------------+---------+------------------------+-----------------
 SANDBOX-TRADER-001| AIAdaptiveStrategyV3| RUNNING | 2025-01-10 16:30:00+00 |      100000.00
```

**If no row:**
- Wait 30 more seconds (database writes may lag)
- Check if paper trading process still running
- Check metrics collector logs: `docker logs ai_metrics --tail 50`

**Expected Outcome:** Session record exists with RUNNING status

#### Task 5.2: Metrics Validation (15 seconds after start)

**Check Prometheus metrics:**

```bash
curl -s http://localhost:9100/metrics | grep "ai_live_session_status"
```

**Expected Output:**
```
ai_live_session_status{trader_id="SANDBOX-TRADER-001",strategy_id="AIAdaptiveStrategyV3",session_name="unnamed",environment="TESTNET",status="RUNNING"} 1.0
```

**Check equity metric:**

```bash
curl -s http://localhost:9100/metrics | grep "ai_live_equity_total"
```

**Expected Output:**
```
ai_live_equity_total{trader_id="SANDBOX-TRADER-001",strategy_id="AIAdaptiveStrategyV3",environment="TESTNET"} 100000.0
```

**Expected Outcome:** Metrics exposed with correct values

#### Task 5.3: Grafana Validation (1 minute after start)

**Steps:**
1. Open: http://localhost:3000/d/live-trading-monitor
2. Dashboard should auto-refresh every 10 seconds

**Verify Panels:**

**Session Overview:**
- ✅ Active Sessions: **1**
- ✅ Session Runtime: **Increasing** (e.g., "2m 15s")
- ✅ Open Positions: **0** (initially)
- ✅ Total Trades: **0** (initially)

**Performance & P&L:**
- ✅ Total Equity: **100,000 USDT** (line graph starting)
- ✅ P&L Realized: **0**
- ✅ P&L Unrealized: **0**
- ✅ Total P&L %: **0%** (gauge)
- ✅ Drawdown %: **0%** (gauge)

**Positions & Orders:**
- ✅ Open Positions table: **Empty** (initially)
- ✅ Orders by Status: **All zeros** (initially)

**If panels show "No data":**
- Wait 10-15 seconds for first refresh
- Click refresh icon in Grafana
- Check Prometheus targets: http://localhost:9090/targets
- Verify `ai_metrics` target is UP

**Expected Outcome:** Dashboard displaying session data

#### Task 5.4: First Trade Validation (5-30 minutes)

**Wait for strategy to generate first signal.**

**Monitor logs for:**
```
[INFO] Signal generated: BUY, confidence: 0.82
[INFO] Order submitted: OrderId('O-20250110-163015-001')
[INFO] Order accepted: OrderId('O-20250110-163015-001')
[INFO] Order filled: OrderId('O-20250110-163015-001'), Price: 42350.50
[INFO] Position opened: BTCUSDT-LINEAR.BYBIT LONG, Quantity: 0.01
```

**Check database for orders:**

```bash
docker exec nautilus_postgres psql -U nautilus -d nautilus_trader -c "
  SELECT 
    order_id,
    instrument_id,
    side,
    order_type,
    status,
    quantity,
    filled_qty,
    created_at
  FROM ai_extensions.live_orders
  WHERE session_id IN (
    SELECT id FROM ai_extensions.live_sessions 
    WHERE trader_id = 'SANDBOX-TRADER-001'
  )
  ORDER BY created_at DESC
  LIMIT 5;
"
```

**Expected Output:**
```
            order_id            |      instrument_id      | side | order_type | status | quantity | filled_qty |       created_at       
--------------------------------+-------------------------+------+------------+--------+----------+------------+------------------------
 O-20250110-163015-001          | BTCUSDT-LINEAR.BYBIT    | BUY  | MARKET     | FILLED |   0.0100 |     0.0100 | 2025-01-10 16:30:15+00
```

**Check Grafana for updates:**
- Open Positions: **1**
- Total Trades: **1** (after position closed)
- Orders Submitted: **1+**
- Orders Filled: **1+**

**If no trades after 30 minutes:**
- **Check strategy confidence threshold** - May be too high
- **Check market volatility** - Strategy may be waiting for setup
- **Check logs for errors** - Strategy may have issues
- **Verify bars are updating** - Look for bar received messages

**Not necessarily a problem** - Strategy is selective and may wait for good setups.

**Expected Outcome:** First trade executed and recorded

#### Task 5.5: Equity Snapshot Validation

**Equity snapshots should record every minute.**

**Wait 2-3 minutes, then check:**

```bash
docker exec nautilus_postgres psql -U nautilus -d nautilus_trader -c "
  SELECT 
    captured_at,
    total_equity,
    unrealized_pnl,
    realized_pnl,
    open_positions
  FROM ai_extensions.live_equity_snapshots
  WHERE session_id IN (
    SELECT id FROM ai_extensions.live_sessions 
    WHERE trader_id = 'SANDBOX-TRADER-001'
  )
  ORDER BY captured_at DESC
  LIMIT 5;
"
```

**Expected Output:**
```
       captured_at       | total_equity | unrealized_pnl | realized_pnl | open_positions
-------------------------+--------------+----------------+--------------+----------------
 2025-01-10 16:33:00+00  |    100050.25 |          25.50 |        24.75 |              1
 2025-01-10 16:32:00+00  |    100024.75 |           0.00 |        24.75 |              0
 2025-01-10 16:31:00+00  |    100000.00 |           0.00 |         0.00 |              0
```

**Verify in Grafana:**
- **Total Equity** graph: Should show line with updates
- Values should match database

**If no snapshots:**
- Check if equity snapshot task is running
- Review strategy code for snapshot trigger
- Check database logs for insert errors

**Expected Outcome:** Equity tracked every minute

### Phase 6: Extended Monitoring (2-4 hours)

#### Task 6.1: Performance Tracking

**Let system run for 2-4 hours to collect meaningful data.**

**Monitor Key Metrics:**

**Session Health:**
```bash
# Check session still running
docker exec nautilus_postgres psql -U nautilus -d nautilus_trader -c "
  SELECT status, 
         EXTRACT(EPOCH FROM (NOW() - started_at))/3600 as runtime_hours
  FROM ai_extensions.live_sessions 
  WHERE trader_id = 'SANDBOX-TRADER-001';
"
```

**Trade Statistics:**
```bash
# Check trade count and performance
docker exec nautilus_postgres psql -U nautilus -d nautilus_trader -c "
  SELECT 
    COUNT(*) as total_trades,
    SUM(CASE WHEN pnl > 0 THEN 1 ELSE 0 END) as winning_trades,
    SUM(CASE WHEN pnl < 0 THEN 1 ELSE 0 END) as losing_trades,
    AVG(pnl) as avg_pnl,
    SUM(pnl) as total_pnl
  FROM ai_extensions.live_trades
  WHERE session_id IN (
    SELECT id FROM ai_extensions.live_sessions 
    WHERE trader_id = 'SANDBOX-TRADER-001'
  );
"
```

**Order Statistics:**
```bash
# Check order success rate
docker exec nautilus_postgres psql -U nautilus -d nautilus_trader -c "
  SELECT 
    status,
    COUNT(*) as count
  FROM ai_extensions.live_orders
  WHERE session_id IN (
    SELECT id FROM ai_extensions.live_sessions 
    WHERE trader_id = 'SANDBOX-TRADER-001'
  )
  GROUP BY status
  ORDER BY count DESC;
"
```

**Expected Outcomes:**
- Session: RUNNING for full duration
- Trades: 10-50+ depending on market volatility
- Orders: Mostly FILLED status, few/no REJECTED
- P&L: Depends on strategy and market, track trend

#### Task 6.2: Error Monitoring

**Check for errors in logs:**

```bash
# Paper trading process logs
tail -f logs/SANDBOX-TRADER-001_*.log | grep -E "ERROR|WARNING"

# Metrics collector logs
docker logs ai_metrics --tail 100 | grep -E "ERROR|WARNING"

# Database logs
docker logs nautilus_postgres --tail 100 | grep -E "ERROR|WARNING"
```

**Common warnings (usually OK):**
- `WARNING: Rate limit approaching` - Strategy may be too active
- `WARNING: No signal generated` - Market conditions not met

**Critical errors (need investigation):**
- `ERROR: Database connection failed` - Infrastructure issue
- `ERROR: Exchange connection lost` - Network/API issue
- `ERROR: Order rejected` - Strategy or configuration issue

**Expected Outcome:** Minimal warnings, no errors

#### Task 6.3: Grafana Dashboard Usage

**Familiarize with dashboard features:**

1. **Time Range Selector**
   - Default: Last 6 hours
   - Change to: Last 1 hour, Last 24 hours, etc.

2. **Auto-Refresh**
   - Currently: 10 seconds
   - Can change: 5s, 30s, 1m, etc.

3. **Panel Interactions**
   - Hover: See exact values
   - Click legend: Toggle series
   - Zoom: Click and drag on graph

4. **Alerts** (to be configured)
   - Click bell icon on panels
   - Set thresholds
   - Configure notifications

**Expected Outcome:** Comfortable navigating dashboard

### Phase 7: Analysis & Optimization (After 24-48 hours)

#### Task 7.1: Compare with Backtest Results

**Run comparison query:**

```sql
-- Compare paper trading vs backtest performance
WITH paper_perf AS (
  SELECT 
    AVG(win_rate) as paper_win_rate,
    AVG(profit_factor) as paper_profit_factor,
    AVG(sharpe_ratio) as paper_sharpe,
    AVG(max_drawdown_pct) as paper_max_dd
  FROM ai_extensions.live_performance_metrics
  WHERE session_id IN (
    SELECT id FROM ai_extensions.live_sessions 
    WHERE trader_id = 'SANDBOX-TRADER-001'
  )
),
backtest_perf AS (
  SELECT 
    AVG(win_rate) as backtest_win_rate,
    AVG(profit_factor) as backtest_profit_factor,
    AVG(sharpe_ratio) as backtest_sharpe,
    AVG(max_drawdown_pct) as backtest_max_dd
  FROM ai_extensions.backtest_metrics
  WHERE backtest_run_id IN (
    SELECT id FROM ai_extensions.backtest_runs
    WHERE strategy_id = 'AIAdaptiveStrategyV3'
    ORDER BY completed_at DESC
    LIMIT 10
  )
)
SELECT 
  p.paper_win_rate,
  b.backtest_win_rate,
  p.paper_win_rate - b.backtest_win_rate as win_rate_delta,
  p.paper_profit_factor,
  b.backtest_profit_factor,
  p.paper_sharpe,
  b.backtest_sharpe,
  p.paper_max_dd,
  b.backtest_max_dd
FROM paper_perf p, backtest_perf b;
```

**Acceptable Deltas:**
- Win Rate: ±3-5%
- Profit Factor: ±0.2
- Sharpe Ratio: ±0.3
- Max Drawdown: +5-10% (paper trading usually worse)

**If deltas too large:**
- **Win rate much lower**: Strategy may be overfitted to historical data
- **Max drawdown higher**: May need tighter risk controls
- **Profit factor lower**: Fees or slippage may be different than modeled

**Expected Outcome:** Performance within expected variance

#### Task 7.2: Identify Issues

**Look for patterns in losing trades:**

```sql
SELECT 
  instrument_id,
  side,
  entry_price,
  exit_price,
  pnl,
  holding_period,
  exit_reason
FROM ai_extensions.live_trades
WHERE session_id IN (
  SELECT id FROM ai_extensions.live_sessions 
  WHERE trader_id = 'SANDBOX-TRADER-001'
)
AND pnl < 0
ORDER BY pnl ASC
LIMIT 20;
```

**Common issues:**
- **Stopped out too early**: Stop-loss too tight
- **Held too long**: Exit signals not triggering
- **Entry timing**: Entering before trend confirmation
- **Market regime**: Strategy not adapting to current conditions

**Expected Outcome:** Insights for strategy improvement

#### Task 7.3: Parameter Tuning

**Based on analysis, consider adjusting:**

**In `AIAdaptiveStrategyConfigV3`:**
```python
# Make strategy more conservative
confidence_threshold=0.85  # Raise from 0.75

# Reduce position holding time
max_bars_in_position=30  # Lower from 50

# Tighten stop-loss
stop_loss_pct=0.015  # If parameter exists

# Reduce position size
position_size_pct=0.02  # If parameter exists
```

**Test changes:**
1. Stop current paper trading (Ctrl+C)
2. Modify configuration
3. Restart paper trading
4. Compare results after another 24-48 hours

**Expected Outcome:** Improved performance metrics

### Phase 8: Continuous Operation (Ongoing)

#### Task 8.1: Daily Monitoring Routine

**Morning (5 minutes):**
1. Check Grafana dashboard
2. Verify session still RUNNING
3. Check overnight P&L
4. Review any alerts

**Evening (5 minutes):**
1. Check daily performance vs backtest
2. Review trade decisions
3. Note any unusual market conditions
4. Plan parameter adjustments if needed

**Weekly (30 minutes):**
1. Run performance comparison queries
2. Analyze losing trades
3. Review strategy behavior
4. Document insights

**Expected Outcome:** Consistent monitoring and improvement

#### Task 8.2: Maintenance Tasks

**Weekly:**
- Restart paper trading to clear memory
- Review and archive old logs
- Check disk space (PostgreSQL)
- Update strategy parameters if needed

**Monthly:**
- Full system backup
- Review and optimize database
- Update monitoring dashboards
- Document strategy changes

**Expected Outcome:** Stable long-term operation

---

## Success Criteria

### Immediate (Within 1 hour)
- [x] Bybit testnet account created
- [ ] API keys generated and configured
- [ ] Paper trading system starts successfully
- [ ] Database shows active session
- [ ] Grafana dashboard displays metrics

### Short-Term (Within 24 hours)
- [ ] At least 10 trades executed
- [ ] No critical errors in logs
- [ ] Monitoring pipeline stable
- [ ] Win rate > 40%
- [ ] Max drawdown < 10%

### Medium-Term (Within 1 week)
- [ ] 100+ trades executed
- [ ] Performance within ±5% of backtest
- [ ] Rejected orders < 2%
- [ ] System uptime > 95%
- [ ] Dashboard alerts configured

### Long-Term (Within 1 month)
- [ ] 500+ trades executed
- [ ] Sharpe ratio > 1.0
- [ ] Profit factor > 1.5
- [ ] Max drawdown < 15%
- [ ] Ready for live trading decision

---

## Troubleshooting Guide

### Issue: Paper trading won't start

**Symptoms:** Script crashes on startup

**Checks:**
1. Virtual environment activated?
   ```bash
   which python3  # Should show venv path
   ```

2. Dependencies installed?
   ```bash
   pip list | grep nautilus
   ```

3. Environment variables set?
   ```bash
   echo $BYBIT_TESTNET_API_KEY
   ```

4. Docker containers running?
   ```bash
   docker ps | wc -l  # Should be 6+ (header + 5 containers)
   ```

**Solutions:**
- Activate venv: `source nautilus_env/bin/activate`
- Install deps: `pip install -e .`
- Export vars: `export BYBIT_TESTNET_API_KEY="..."`
- Start Docker: `cd infrastructure/docker && docker-compose up -d`

### Issue: No trades being executed

**Symptoms:** System runs but no orders submitted

**Checks:**
1. Strategy receiving bars?
   ```bash
   tail -f logs/SANDBOX-TRADER-001_*.log | grep "Bar received"
   ```

2. Feature matrix building?
   ```bash
   tail -f logs/SANDBOX-TRADER-001_*.log | grep "feature"
   ```

3. Confidence threshold too high?
   ```python
   # Check config
   confidence_threshold=0.75  # Lower to 0.65-0.70
   ```

4. Market volatility too low?
   - Check if market is moving
   - Try different instrument

**Solutions:**
- Lower confidence threshold
- Check market hours (crypto is 24/7 but volume varies)
- Verify strategy logic not blocking trades
- Add debug logging to strategy

### Issue: High rejection rate

**Symptoms:** Many orders rejected by exchange

**Checks:**
1. Testnet funds available?
   - Login to testnet dashboard
   - Check balance

2. Order size valid?
   ```sql
   SELECT quantity, instrument_id 
   FROM ai_extensions.live_orders 
   WHERE status = 'REJECTED';
   ```

3. Rate limits exceeded?
   ```bash
   tail -f logs/SANDBOX-TRADER-001_*.log | grep "rate limit"
   ```

**Solutions:**
- Fund testnet account
- Reduce order frequency
- Check instrument min/max order sizes
- Add rate limit backoff

### Issue: Metrics not in Grafana

**Symptoms:** Dashboard shows "No data"

**Checks:**
1. Metrics collector running?
   ```bash
   docker ps | grep ai_metrics
   ```

2. Metrics exposed?
   ```bash
   curl http://localhost:9100/metrics | grep ai_live
   ```

3. Prometheus scraping?
   ```bash
   curl http://localhost:9090/api/v1/targets | jq '.data.activeTargets[] | select(.labels.job == "ai_metrics")'
   ```

4. Database has data?
   ```bash
   docker exec nautilus_postgres psql -U nautilus -d nautilus_trader -c "SELECT COUNT(*) FROM ai_extensions.live_sessions;"
   ```

**Solutions:**
- Restart metrics collector: `docker restart ai_metrics`
- Check Prometheus config: `infrastructure/prometheus/prometheus.yml`
- Verify database connection in metrics collector
- Check Grafana data source configuration

### Issue: High memory usage

**Symptoms:** System slows down over time

**Checks:**
1. Memory usage:
   ```bash
   docker stats --no-stream
   ```

2. Database size:
   ```bash
   docker exec nautilus_postgres psql -U nautilus -d nautilus_trader -c "
     SELECT pg_size_pretty(pg_database_size('nautilus_trader'));
   "
   ```

3. Log file sizes:
   ```bash
   du -sh logs/
   ```

**Solutions:**
- Restart paper trading daily
- Archive old logs: `mv logs logs_backup_$(date +%Y%m%d)`
- Clean old equity snapshots (keep last 7 days):
  ```sql
  DELETE FROM ai_extensions.live_equity_snapshots 
  WHERE captured_at < NOW() - INTERVAL '7 days';
  ```
- Increase Docker memory limits

---

## Next Steps After Paper Trading

### Before Live Trading

1. **Minimum Paper Trading Duration:** 2-4 weeks
2. **Minimum Trades:** 500+
3. **Performance Requirements:**
   - Win rate > 50%
   - Profit factor > 1.5
   - Sharpe ratio > 1.0
   - Max drawdown < 15%
   - Rejected orders < 1%

4. **Risk Management Validation:**
   - Position sizing working correctly
   - Stop-losses triggering appropriately
   - Drawdown limits enforced
   - Circuit breakers tested

5. **Infrastructure Validation:**
   - System uptime > 99%
   - No data gaps
   - Monitoring alerts working
   - Emergency stop procedures tested

### Transition to Live Trading

1. **Choose Exchange:**
   - Bybit (if accessible)
   - OKX (good alternative)
   - Other supported exchanges

2. **Start Small:**
   - Use minimum account size (e.g., $500-$1000)
   - Reduce position sizes by 50-75%
   - Monitor very closely first week

3. **Scale Gradually:**
   - Week 1: Minimum capital
   - Week 2-4: If profitable, increase 25%
   - Month 2: If still profitable, increase to target capital

4. **Never:**
   - Skip paper trading
   - Start with full capital
   - Trade without monitoring
   - Ignore risk limits

---

## Documentation

### Files Updated
- ✅ `ai-working/paper_trading/research/analysis.md` - Technical analysis
- ✅ `ai-working/paper_trading/plan.md` - This implementation plan
- [ ] `ai-working/paper_trading/implementation.md` - Progress tracking (to update)

### Files to Monitor
- `scripts/start_paper_trading_sandbox.py` - Main script
- `infrastructure/postgres/05-live-trading-schema.sql` - Database schema
- `ajk_strategies/monitoring/metrics_collector.py` - Metrics logic
- `infrastructure/monitoring/grafana/dashboards/live-trading-monitor.json` - Dashboard

### Logs Location
- Paper trading: `logs/SANDBOX-TRADER-001_*.log`
- Metrics collector: `docker logs ai_metrics`
- Database: `docker logs nautilus_postgres`
- Grafana: `docker logs nautilus_grafana`

---

## Summary

**Goal**: Deploy paper trading with live market data and full monitoring

**Approach**: Bybit testnet (data) + Sandbox execution (simulated)

**Timeline**:
- Setup: 30 minutes
- Validation: 1 hour
- Extended testing: 24-48 hours
- Analysis: 2-4 weeks

**Resources Needed**:
- Bybit testnet account (free)
- Running infrastructure (already deployed)
- Monitoring access (Grafana dashboard)

**Success Metrics**:
- System uptime > 95%
- Win rate > 50%
- Performance within ±5% of backtest
- Ready for live trading after 2-4 weeks

**Next Action**: Register Bybit testnet account and generate API keys

---

**Status**: Ready to implement  
**Blockers**: None (all prerequisites met)  
**Estimated Time to First Trade**: < 30 minutes after account creation
