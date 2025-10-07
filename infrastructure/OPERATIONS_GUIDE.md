# Nautilus Trader Operations Guide
## From Installation to Production Live Trading

**Target Audience:** New traders with no prior algorithmic trading experience  
**Goal:** Complete, secure, reliable production trading system  
**Philosophy:** Configuration over scripting, hardened over hacky  

---

## 📋 Table of Contents

1. [Overview](#overview)
2. [Phase 1: Infrastructure Setup](#phase-1-infrastructure-setup-week-1-2)
3. [Phase 2: Backtesting](#phase-2-backtesting-week-2-3)
4. [Phase 3: Paper Trading](#phase-3-paper-trading-week-3-4)
5. [Phase 4: Live Trading](#phase-4-live-trading-week-5)
6. [Daily Operations](#daily-operations)
7. [Monitoring & Alerts](#monitoring--alerts)
8. [Troubleshooting](#troubleshooting)
9. [Security Checklist](#security-checklist)
10. [Emergency Procedures](#emergency-procedures)

---

## Overview

### System Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                     YOUR TRADING SYSTEM                         │
│                                                                 │
│  ┌────────────────────┐         ┌────────────────────┐        │
│  │   Trading Engine   │────────>│  Risk Management   │        │
│  │  (Nautilus Trader) │<────────│    (Circuit       │        │
│  └──────┬─────────────┘         │     Breakers)      │        │
│         │                       └────────────────────┘        │
│         │                                                      │
│         ├─────> PostgreSQL (Persistent Storage)               │
│         ├─────> Redis (Fast Cache)                            │
│         ├─────> Prometheus (Metrics)                          │
│         └─────> Grafana (Dashboards)                          │
│                                                                 │
│  ┌────────────────────┐         ┌────────────────────┐        │
│  │  Paper Trading     │         │   Live Trading     │        │
│  │  (Testnet/Fake $)  │────────>│  (Real Money)      │        │
│  └────────────────────┘         └────────────────────┘        │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
                    ┌──────────────────┐
                    │    Exchanges     │
                    │  (Binance, IB)   │
                    └──────────────────┘
```

### Timeline to Live Trading

| Phase | Duration | Goal | Real Money? |
|-------|----------|------|-------------|
| Phase 1: Infrastructure | Week 1-2 | Setup database, monitoring | No |
| Phase 2: Backtesting | Week 2-3 | Test strategies on historical data | No |
| Phase 3: Paper Trading | Week 3-4 | Test with fake money, real market | No |
| Phase 4: Live Trading | Week 5+ | Deploy with real money | **Yes** |

**Key Principle:** You cannot skip phases. Each builds on the previous.

---

## Phase 1: Infrastructure Setup (Week 1-2)

### Prerequisites

**Required Software:**
- Docker (v20.10+) - [Install](https://docs.docker.com/get-docker/)
- Docker Compose (v2.0+) - Usually included with Docker
- Git - For version control
- Python 3.11+ - Already installed for Nautilus

**System Requirements:**
- **Minimum:** 4GB RAM, 20GB disk, 2 CPU cores
- **Recommended:** 8GB RAM, 50GB SSD, 4 CPU cores
- **Production:** 16GB RAM, 100GB SSD, 8 CPU cores

### Step 1: Initial Setup (30 minutes)

```bash
# 1. Navigate to infrastructure directory
cd /home/ajk/Nautilus/nautilus_trader/infrastructure

# 2. Create environment configuration
cp .env.template .env.local

# 3. Edit .env.local with your passwords
nano .env.local  # or use your preferred editor

# Required changes:
#   - DB_PASSWORD (strong password, 20+ chars)
#   - REDIS_PASSWORD (strong password, 20+ chars)
#   - GRAFANA_PASSWORD (strong password, 20+ chars)

# 4. Secure the file
chmod 600 .env.local

# 5. Verify .env.local is in .gitignore
grep -q ".env.local" ../.gitignore || echo ".env.local" >> ../.gitignore
```

**Example Strong Password Generation:**
```bash
# Generate secure passwords (Linux/Mac)
openssl rand -base64 32

# Or use this pattern: [UpperLower][Numbers][Symbols]
# Example: Tr4d1ng$yst3m#2025!Secur3
```

### Step 2: Start Infrastructure (10 minutes)

```bash
# Start all services
cd /home/ajk/Nautilus/nautilus_trader/infrastructure/docker
docker-compose up -d

# Wait for initialization (first time takes 30-60 seconds)
sleep 60

# Check status (all should be "Up")
docker-compose ps

# Expected output:
# NAME                      STATUS
# nautilus_postgres         Up (healthy)
# nautilus_redis            Up (healthy)
# nautilus_prometheus       Up (healthy)
# nautilus_grafana          Up (healthy)
# nautilus_postgres_exporter Up
# nautilus_redis_exporter   Up
```

### Step 3: Verify Services (15 minutes)

```bash
# Test PostgreSQL connection
docker exec -it nautilus_postgres psql -U nautilus -d nautilus_trader -c "SELECT version();"

# Test Redis connection
docker exec -it nautilus_redis redis-cli -a $(grep REDIS_PASSWORD ../..env.local | cut -d'=' -f2) ping
# Expected: PONG

# Test Prometheus (should return JSON)
curl http://localhost:9090/api/v1/targets

# Access Grafana
# Open browser: http://localhost:3000
# Login: admin / <your GRAFANA_PASSWORD>
```

### Step 4: Initialize Database Schema (5 minutes)

```bash
# Schema is auto-initialized on first startup
# Verify tables exist:
docker exec -it nautilus_postgres psql -U nautilus -d nautilus_trader -c "\dt"

# Expected tables: backtests, ml_optimization_log, regime_detection_log, etc.

# Test insert
docker exec -it nautilus_postgres psql -U nautilus -d nautilus_trader -c "
INSERT INTO backtests (run_id, strategy_name, instrument, start_date, end_date, initial_capital, final_capital, total_pnl, total_pnl_pct, total_trades, parameters)
VALUES ('test-001', 'TestStrategy', 'BTC-USDT', NOW() - INTERVAL '1 day', NOW(), 100000, 100000, 0, 0, 0, '{}');
"

# Verify insert
docker exec -it nautilus_postgres psql -U nautilus -d nautilus_trader -c "SELECT * FROM backtests;"
```

### Step 5: Configure Monitoring (20 minutes)

**Access Grafana:**
1. Open http://localhost:3000
2. Login with admin credentials
3. Go to **Configuration** → **Data Sources**
4. Verify **PostgreSQL** datasource is configured
5. Verify **Prometheus** datasource is configured

**Import Dashboards:**
```bash
# Copy dashboard templates to Grafana
cp ../monitoring/grafana/dashboards/*.json /tmp/

# Import via Grafana UI:
# 1. Go to Dashboards → Import
# 2. Upload JSON file
# 3. Select data source (PostgreSQL or Prometheus)
```

### Validation Checklist ✅

- [ ] All 6 Docker containers running and healthy
- [ ] PostgreSQL accessible (can connect and query)
- [ ] Redis accessible (PING returns PONG)
- [ ] Prometheus accessible (http://localhost:9090)
- [ ] Grafana accessible (http://localhost:3000)
- [ ] Database schema created (tables visible)
- [ ] Grafana dashboards loaded

**If all checks pass, proceed to Phase 2. Otherwise, see [Troubleshooting](#troubleshooting).**

---

## Phase 2: Backtesting (Week 2-3)

### Goal
Test your trading strategies on historical data to see how they would have performed. **No real money, no risk.**

### Prerequisites
- ✅ Phase 1 complete (infrastructure running)
- ✅ Historical data loaded (4.3 years BTC/ETH already available)

### Step 1: Run Your First Backtest (15 minutes)

```bash
# Navigate to strategy directory
cd /home/ajk/Nautilus/nautilus_trader

# Run backtest with database storage
python3 ajk_strategies/run_backtest_with_real_data.py

# This will:
# 1. Load historical data from Parquet files
# 2. Execute strategy on data
# 3. Save results to PostgreSQL
# 4. Export CSV backup
```

**What to Watch:**
- Execution time (should be < 2 minutes for 1 year of data)
- Number of trades executed
- Final P&L
- "✅ Saved to database" confirmation

### Step 2: Analyze Results (30 minutes)

**Via PostgreSQL:**
```bash
# View recent backtests
docker exec -it nautilus_postgres psql -U nautilus -d nautilus_trader -c "
SELECT 
    id, run_id, strategy_name, instrument,
    total_pnl, win_rate, sharpe_ratio, total_trades,
    created_at
FROM backtests
ORDER BY created_at DESC
LIMIT 10;
"

# View strategy health
docker exec -it nautilus_postgres psql -U nautilus -d nautilus_trader -c "
SELECT * FROM v_strategy_health ORDER BY created_at DESC LIMIT 5;
"

# Get best strategies
docker exec -it nautilus_postgres psql -U nautilus -d nautilus_trader -c "
SELECT * FROM v_top_strategies;
"
```

**Via Grafana:**
1. Open http://localhost:3000
2. Navigate to "AI-Adaptive Strategy Performance" dashboard
3. Observe:
   - Total P&L over time
   - Win rate trends
   - Sharpe ratio distribution
   - Regime changes

### Step 3: Iterate and Optimize (Days/Weeks)

**Optimization Cycle:**
1. **Analyze** → What worked? What didn't?
2. **Modify** → Adjust parameters (EMA periods, stop loss, etc.)
3. **Backtest** → Run again with new parameters
4. **Compare** → Use PostgreSQL queries to compare runs
5. **Repeat** → Until you find optimal parameters

**Query to Compare Strategies:**
```sql
SELECT 
    parameters->>'fast_ema_period' as fast_ema,
    parameters->>'slow_ema_period' as slow_ema,
    AVG(sharpe_ratio) as avg_sharpe,
    AVG(win_rate) as avg_win_rate,
    AVG(total_pnl_pct) as avg_return,
    COUNT(*) as num_runs
FROM backtests
WHERE strategy_name = 'AI-Adaptive-BTC-USDT'
GROUP BY fast_ema, slow_ema
HAVING COUNT(*) >= 3
ORDER BY avg_sharpe DESC;
```

### Success Criteria (Before Moving to Paper Trading)

| Metric | Minimum | Good | Excellent |
|--------|---------|------|-----------|
| **Sharpe Ratio** | > 1.0 | > 1.5 | > 2.0 |
| **Win Rate** | > 45% | > 50% | > 55% |
| **Max Drawdown** | < 20% | < 15% | < 10% |
| **Total Trades** | > 50 | > 100 | > 200 |
| **Profit Factor** | > 1.2 | > 1.5 | > 2.0 |
| **Consistency** | 6/12 positive months | 8/12 | 10/12 |

**Rule:** Don't proceed to paper trading unless you meet **Minimum** criteria on ALL metrics.

---

## Phase 3: Paper Trading (Week 3-4)

### Goal
Test your strategy with **real market conditions** but **fake money**. This reveals issues that backtesting cannot (latency, order fills, market impact, etc.).

### Prerequisites
- ✅ Phase 2 complete (strategy performs well in backtests)
- ✅ Backtest Sharpe ratio > 1.5
- ✅ Backtest win rate > 45%

### Step 1: Get Paper Trading API Keys (1-2 hours)

**Binance Testnet (Recommended for Crypto)**

1. Visit: https://testnet.binance.vision/
2. Click "Generate HMAC_SHA256 Key"
3. Save API Key and Secret Key
4. Add to `.env.local`:
   ```bash
   BINANCE_API_KEY=your_testnet_api_key
   BINANCE_API_SECRET=your_testnet_secret_key
   BINANCE_TESTNET=true
   ```

**Interactive Brokers Paper Trading (Recommended for Stocks/Options)**

1. Create IB account: https://www.interactivebrokers.com/
2. Apply for paper trading account (instant approval)
3. Download TWS (Trader Workstation): https://www.interactivebrokers.com/en/trading/tws.php
4. Launch TWS → Login with paper account
5. Configure API:
   - File → Global Configuration → API → Settings
   - Enable "Enable ActiveX and Socket Clients"
   - Add "127.0.0.1" to "Trusted IPs"
   - Set "Socket port" to 7497 (paper trading)
6. Add to `.env.local`:
   ```bash
   IB_USERNAME=your_ib_username
   IB_PASSWORD=your_ib_password
   IB_ACCOUNT_ID=DU123456  # Your paper account ID
   IB_TRADING_MODE=paper
   IB_PORT=7497
   ```

**Bybit Testnet (Alternative for Crypto)**

1. Visit: https://testnet.bybit.com/
2. Register account
3. Go to API Management
4. Create API key
5. Add to `.env.local`:
   ```bash
   BYBIT_API_KEY=your_testnet_api_key
   BYBIT_API_SECRET=your_testnet_secret_key
   BYBIT_TESTNET=true
   ```

### Step 2: Configure Paper Trading (30 minutes)

Create paper trading configuration:

File: `/home/ajk/Nautilus/nautilus_trader/configs/paper_trading_config.json`

```json
{
  "trader_id": "PAPER-TRADER-001",
  "environment": "paper",
  "log_level": "INFO",
  
  "risk_management": {
    "max_position_size": 10000,
    "max_daily_loss": 1000,
    "max_drawdown": 5000,
    "circuit_breaker_enabled": true
  },
  
  "exchanges": {
    "binance": {
      "enabled": true,
      "testnet": true,
      "instruments": ["BTC/USDT", "ETH/USDT"],
      "api_key_env": "BINANCE_API_KEY",
      "api_secret_env": "BINANCE_API_SECRET"
    },
    "interactive_brokers": {
      "enabled": false,
      "paper_trading": true,
      "instruments": ["SPY", "AAPL"],
      "port": 7497
    }
  },
  
  "strategy": {
    "name": "AI-Adaptive-Strategy",
    "parameters": {
      "fast_ema_period": 8,
      "slow_ema_period": 21,
      "stop_loss_atr": 2.0,
      "take_profit_atr": 3.0
    }
  },
  
  "monitoring": {
    "save_to_database": true,
    "report_interval_seconds": 60,
    "alert_on_loss": true,
    "alert_threshold_pct": 2.0
  }
}
```

### Step 3: Run Paper Trading (1-2 weeks)

**Start Paper Trading:**
```bash
# Create paper trading runner script
cd /home/ajk/Nautilus/nautilus_trader

# Run in screen/tmux so it persists
screen -S paper_trading

# Start trading
python3 ajk_strategies/run_paper_trading.py --config configs/paper_trading_config.json

# Detach: Ctrl+A, D
# Reattach: screen -r paper_trading
```

**Monitor in Real-Time:**
1. **Grafana Dashboard:** http://localhost:3000
   - Watch equity curve
   - Monitor open positions
   - Check win rate
   - Observe drawdown

2. **PostgreSQL Queries:**
   ```bash
   # Current positions
   docker exec -it nautilus_postgres psql -U nautilus -d nautilus_trader -c "
   SELECT * FROM trades WHERE exit_time IS NULL ORDER BY entry_time DESC;
   "
   
   # Recent trades
   docker exec -it nautilus_postgres psql -U nautilus -d nautilus_trader -c "
   SELECT * FROM trades ORDER BY entry_time DESC LIMIT 20;
   "
   
   # Today's performance
   docker exec -it nautilus_postgres psql -U nautilus -d nautilus_trader -c "
   SELECT 
       COUNT(*) as trades_today,
       SUM(CASE WHEN pnl > 0 THEN 1 ELSE 0 END)::float / COUNT(*) * 100 as win_rate,
       SUM(pnl) as total_pnl
   FROM trades
   WHERE entry_time > EXTRACT(EPOCH FROM DATE_TRUNC('day', NOW())) * 1000000000;
   "
   ```

3. **Logs:**
   ```bash
   # View logs
   tail -f logs/paper_trading.log
   ```

### Step 4: Daily Review (15 minutes/day)

**Morning Checklist:**
- [ ] Check if paper trading is still running (`screen -ls`)
- [ ] Review overnight trades
- [ ] Check for any errors in logs
- [ ] Verify risk limits not breached

**Evening Checklist:**
- [ ] Review day's performance
- [ ] Compare to backtest expectations
- [ ] Note any anomalies or issues
- [ ] Update trading journal

### Success Criteria (Before Moving to Live Trading)

| Metric | Requirement | Why |
|--------|-------------|-----|
| **Duration** | Minimum 2 weeks | See strategy in various market conditions |
| **Sharpe Ratio** | Within 80% of backtest | Validate backtest wasn't over-optimized |
| **Win Rate** | Within 10% of backtest | Ensure realistic performance |
| **Max Drawdown** | < 15% | Risk control working |
| **No System Crashes** | 100% uptime | System stability verified |
| **Order Fills** | > 95% filled | Liquidity sufficient |
| **Latency** | < 500ms avg | Fast enough for strategy |
| **Circuit Breakers** | Tested & working | Safety mechanisms operational |

**Critical Rule:** If paper trading performance is significantly worse than backtests, **DO NOT** go live. Investigate and fix issues first.

---

## Phase 4: Live Trading (Week 5+)

### ⚠️ DANGER ZONE ⚠️

**Before you start:**
- ✅ Completed 2+ weeks successful paper trading
- ✅ Performance matches backtest expectations
- ✅ All risk controls tested and working
- ✅ Emergency stop procedure documented
- ✅ Only risk capital you can afford to lose

### Step 1: Risk Assessment (1 hour)

**Calculate Your Risk:**
1. **Total Capital Available:** $______
2. **Maximum Loss You Can Accept:** $______
3. **Initial Trading Capital (10-20% of total):** $______
4. **Maximum Daily Loss (2% of trading capital):** $______
5. **Maximum Drawdown (5% of trading capital):** $______

**Example:**
- Total capital: $50,000
- Max acceptable loss: $5,000 (10%)
- Initial trading capital: $5,000 (10%)
- Max daily loss: $100 (2% of $5,000)
- Max drawdown: $250 (5% of $5,000)

### Step 2: Get Live API Keys (2-3 hours)

**Binance Live Trading**

1. Visit: https://www.binance.com/
2. Complete KYC verification
3. Go to API Management
4. Create API key with:
   - ✅ Enable Reading
   - ✅ Enable Spot & Margin Trading
   - ❌ Disable Withdrawals (security)
5. Whitelist your IP address
6. Set trading limits:
   - Max order size
   - Max daily trades
7. Add to `.env.local`:
   ```bash
   BINANCE_API_KEY=your_live_api_key
   BINANCE_API_SECRET=your_live_secret_key
   BINANCE_TESTNET=false  # LIVE TRADING
   ```

**Interactive Brokers Live Trading**

1. Fund your IB account
2. Configure API same as paper trading
3. Use port 7496 (live) instead of 7497
4. Enable two-factor authentication
5. Add to `.env.local`:
   ```bash
   IB_TRADING_MODE=live  # LIVE TRADING
   IB_PORT=7496
   ```

### Step 3: Update Configuration (30 minutes)

Update `/configs/live_trading_config.json`:

```json
{
  "trader_id": "LIVE-TRADER-001",
  "environment": "production",
  "log_level": "INFO",
  
  "risk_management": {
    "max_position_size": 5000,      # Start small!
    "max_daily_loss": 100,           # Your calculated value
    "max_drawdown": 250,             # Your calculated value
    "circuit_breaker_enabled": true,
    "auto_shutdown_on_breach": true
  },
  
  "exchanges": {
    "binance": {
      "enabled": true,
      "testnet": false,  # LIVE
      "instruments": ["BTC/USDT"],  # Start with 1 instrument
      "api_key_env": "BINANCE_API_KEY",
      "api_secret_env": "BINANCE_API_SECRET"
    }
  },
  
  "strategy": {
    "name": "AI-Adaptive-Strategy",
    "parameters": {
      # Use parameters that worked in paper trading
      "fast_ema_period": 8,
      "slow_ema_period": 21,
      "stop_loss_atr": 2.0,
      "take_profit_atr": 3.0
    }
  },
  
  "monitoring": {
    "save_to_database": true,
    "report_interval_seconds": 30,  # More frequent
    "alert_on_loss": true,
    "alert_threshold_pct": 1.0,     # Alert at 1% loss
    "email_alerts": "your@email.com"
  },
  
  "safety": {
    "require_manual_start": true,    # Manual confirmation
    "max_order_retries": 3,
    "kill_switch_enabled": true,
    "kill_switch_hotkey": "Ctrl+C"
  }
}
```

### Step 4: Pre-Launch Checklist (30 minutes)

**System Health:**
- [ ] All Docker containers healthy
- [ ] PostgreSQL accessible
- [ ] Redis accessible
- [ ] Grafana dashboards showing data
- [ ] Logs directory has space (> 10GB free)

**Risk Controls:**
- [ ] Max daily loss set correctly
- [ ] Max drawdown set correctly
- [ ] Circuit breaker enabled
- [ ] Kill switch tested
- [ ] Emergency contact numbers saved

**Exchange Connectivity:**
- [ ] API keys valid (test with balance query)
- [ ] Order placement tested (small test order)
- [ ] Order cancellation tested
- [ ] WebSocket connection stable

**Monitoring:**
- [ ] Grafana open and visible
- [ ] PostgreSQL queries prepared
- [ ] Phone notifications enabled
- [ ] Email alerts configured

**Documentation:**
- [ ] Emergency stop procedure printed
- [ ] Exchange support contacts saved
- [ ] Trading journal ready

### Step 5: Launch (30 minutes)

**Start Live Trading:**
```bash
# Final confirmation
read -p "Are you ready to start LIVE TRADING with REAL MONEY? (yes/no): " confirm

if [ "$confirm" = "yes" ]; then
    # Start in screen/tmux
    screen -S live_trading
    
    # Launch with manual confirmation
    python3 ajk_strategies/run_live_trading.py \
        --config configs/live_trading_config.json \
        --confirm-live
    
    # You will be prompted:
    # "Starting LIVE TRADING. Type 'START' to confirm: "
    
    # Type: START
fi

# Detach: Ctrl+A, D
# Reattach: screen -r live_trading
```

**First Hour Monitoring:**
- ⏰ 0-15 min: Watch every tick, every order
- ⏰ 15-30 min: Check if orders filling correctly
- ⏰ 30-45 min: Verify P&L tracking matches expectations
- ⏰ 45-60 min: Confirm monitoring/alerts working

**First Day:**
- Check every hour
- Take notes on any issues
- Compare to paper trading
- Be ready to stop if something is wrong

**First Week:**
- Check 3-4 times per day
- Daily performance review
- Weekly journal entry

### Step 6: Ongoing Operations

See [Daily Operations](#daily-operations) section below.

---

## Daily Operations

### Morning Routine (10-15 minutes)

```bash
# 1. Check system health
cd /home/ajk/Nautilus/nautilus_trader/infrastructure/docker
docker-compose ps  # All should be "Up (healthy)"

# 2. Verify trading is running
screen -ls  # Should see live_trading session

# 3. Check overnight performance
docker exec -it nautilus_postgres psql -U nautilus -d nautilus_trader -c "
SELECT 
    COUNT(*) as trades_since_midnight,
    SUM(CASE WHEN pnl > 0 THEN 1 ELSE 0 END)::float / NULLIF(COUNT(*), 0) * 100 as win_rate,
    SUM(pnl) as total_pnl,
    MIN(pnl) as worst_trade,
    MAX(pnl) as best_trade
FROM trades
WHERE entry_time > EXTRACT(EPOCH FROM DATE_TRUNC('day', NOW())) * 1000000000;
"

# 4. Check for errors in logs
tail -100 logs/live_trading.log | grep -i error

# 5. View Grafana dashboard
# Open: http://localhost:3000
```

### Evening Routine (15-20 minutes)

```bash
# 1. Generate daily report
python3 ajk_strategies/reports/generate_daily_report.py

# 2. Update trading journal
# Record:
#   - Total P&L for the day
#   - Number of trades
#   - Win rate
#   - Any anomalies or observations
#   - Market conditions

# 3. Check system resources
docker stats --no-stream

# 4. Backup database
docker exec nautilus_postgres pg_dump -U nautilus nautilus_trader | gzip > \
    /backups/nautilus_trader_$(date +%Y%m%d).sql.gz
```

### Weekly Routine (1-2 hours)

```bash
# 1. Performance analysis
python3 ajk_strategies/reports/generate_weekly_report.py

# 2. Strategy review
# - Compare to paper trading
# - Check if parameters need adjustment
# - Review risk metrics

# 3. System maintenance
docker-compose down
docker system prune -f  # Clean up unused images
docker-compose up -d

# 4. Update dependencies (if needed)
cd /home/ajk/Nautilus/nautilus_trader
git pull origin develop
pip install --upgrade nautilus_trader

# 5. Review logs for warnings
grep -r "WARN" logs/ | tail -100
```

---

## Monitoring & Alerts

### Real-Time Monitoring (Grafana)

**Dashboard 1: Trading Overview**
- Current equity
- Open positions
- Today's P&L
- Win rate gauge
- Total trades

**Dashboard 2: Risk Metrics**
- Current drawdown meter
- Daily loss tracker
- Position size compliance
- Circuit breaker status
- Risk limit gauges

**Dashboard 3: System Health**
- Container status
- CPU usage
- Memory usage
- Database size
- Redis cache hit rate

**Dashboard 4: AI Strategy Metrics**
- ML optimization frequency
- Regime detection distribution
- Pattern recognition accuracy
- Sentiment scores

### Alert Rules

**Critical Alerts (Immediate Action):**
- Trading system crashed
- Exchange connectivity lost
- Daily loss limit breached
- Drawdown limit breached
- Database connection lost

**Warning Alerts (Review Soon):**
- Win rate below 40%
- Large losing trade (> 2x average)
- Unusual order fill latency
- Low cache hit rate

**Info Alerts (FYI):**
- Daily report generated
- Weekly backup completed
- New regime detected
- ML optimization triggered

### Setting Up Alerts

**Email Alerts (via Grafana):**
1. Grafana → Alerting → Contact points
2. Add email contact
3. Test alert
4. Configure alert rules in dashboards

**SMS Alerts (via Twilio):**
```python
# In your trading code
from twilio.rest import Client

def send_sms_alert(message):
    client = Client(os.getenv('TWILIO_SID'), os.getenv('TWILIO_TOKEN'))
    client.messages.create(
        body=f"[NAUTILUS ALERT] {message}",
        from_=os.getenv('TWILIO_FROM'),
        to=os.getenv('TWILIO_TO')
    )
```

---

## Troubleshooting

### Common Issues

#### 1. Container Won't Start

**Symptom:** `docker-compose up -d` fails

**Solutions:**
```bash
# Check logs
docker-compose logs postgres

# Common fixes:
# - Port already in use
docker-compose down
sudo lsof -i :5432  # Kill process using port
docker-compose up -d

# - Volume corruption
docker-compose down -v  # WARNING: Deletes data!
docker-compose up -d
```

#### 2. Can't Connect to Database

**Symptom:** `psycopg2.OperationalError: could not connect`

**Solutions:**
```bash
# Test connection
docker exec -it nautilus_postgres pg_isready -U nautilus

# Check password
grep DB_PASSWORD infrastructure/.env.local

# Restart PostgreSQL
docker-compose restart postgres
```

#### 3. Trading Strategy Not Executing

**Symptom:** No trades being placed

**Solutions:**
```bash
# Check logs
tail -100 logs/live_trading.log

# Common causes:
# - No signal generated (market conditions)
# - Risk limits preventing trades
# - Exchange connectivity issue
# - Insufficient balance

# Verify exchange connection
python3 -c "
from nautilus_trader.adapters.binance.config import BinanceDataClientConfig
# Test connection code here
"
```

#### 4. High Memory Usage

**Symptom:** System slow, containers crashing

**Solutions:**
```bash
# Check usage
docker stats

# Restart Redis (clears cache)
docker-compose restart redis

# Adjust memory limits in docker-compose.yml

# Clear old logs
find logs/ -mtime +30 -delete
```

---

## Security Checklist

### Before Going Live

- [ ] Change all default passwords
- [ ] Use strong passwords (20+ chars, mixed case, numbers, symbols)
- [ ] `.env.local` file has chmod 600
- [ ] `.env.local` in `.gitignore`
- [ ] API keys have withdrawal disabled
- [ ] IP whitelist enabled on exchange
- [ ] Two-factor authentication enabled
- [ ] Trading limits set on exchange
- [ ] Regular backups configured
- [ ] Emergency contacts saved

### Ongoing Security

- [ ] Rotate passwords monthly
- [ ] Review API key permissions quarterly
- [ ] Monitor for unauthorized access
- [ ] Keep Nautilus Trader updated
- [ ] Keep Docker images updated
- [ ] Review logs for suspicious activity

---

## Emergency Procedures

### Emergency Stop (Kill Switch)

**If something is going wrong:**

1. **Immediate Stop (< 5 seconds):**
   ```bash
   # Method 1: Detach screen and kill
   screen -r live_trading
   Ctrl+C  # Kill trading process
   
   # Method 2: Kill from outside
   pkill -f "run_live_trading.py"
   ```

2. **Cancel All Open Orders:**
   ```bash
   python3 scripts/emergency_cancel_all.py
   ```

3. **Close All Positions (if needed):**
   ```bash
   python3 scripts/emergency_close_all.py
   ```

### System Failure Recovery

**If system crashes:**

1. **Restart infrastructure:**
   ```bash
   cd /home/ajk/Nautilus/nautilus_trader/infrastructure/docker
   docker-compose down
   docker-compose up -d
   ```

2. **Verify exchange positions:**
   ```bash
   # Check what's actually on exchange
   python3 scripts/check_exchange_positions.py
   ```

3. **Reconcile with database:**
   ```bash
   python3 scripts/reconcile_positions.py
   ```

4. **Manual intervention if needed:**
   - Login to exchange web interface
   - Manually close positions if system can't

### Contact Numbers

**Keep these handy (print and stick to monitor):**

- **Exchange Support:**
  - Binance: +1-xxx-xxx-xxxx
  - Interactive Brokers: +1-xxx-xxx-xxxx
  
- **Your Emergency Contacts:**
  - Trading partner: ________________
  - Technical support: _______________
  
- **Critical Commands:**
  ```
  Emergency stop: Ctrl+C in screen session
  Cancel orders: python3 scripts/emergency_cancel_all.py
  System restart: docker-compose restart
  ```

---

## Appendix

### Useful SQL Queries

```sql
-- Today's P&L
SELECT SUM(pnl) FROM trades 
WHERE entry_time > EXTRACT(EPOCH FROM DATE_TRUNC('day', NOW())) * 1000000000;

-- Win rate last 100 trades
SELECT 
    COUNT(CASE WHEN pnl > 0 THEN 1 END)::float / COUNT(*) * 100 as win_rate
FROM (SELECT * FROM trades ORDER BY entry_time DESC LIMIT 100) t;

-- Drawdown analysis
SELECT 
    MIN(equity) as lowest_equity,
    MAX(equity) as highest_equity,
    (MAX(equity) - MIN(equity)) / MAX(equity) * 100 as max_drawdown_pct
FROM performance_metrics
WHERE timestamp > EXTRACT(EPOCH FROM NOW() - INTERVAL '30 days') * 1000000000;
```

### Performance Optimization

```bash
# Optimize PostgreSQL
docker exec -it nautilus_postgres psql -U nautilus -d nautilus_trader -c "
VACUUM ANALYZE;
REINDEX DATABASE nautilus_trader;
"

# Clear Redis cache
docker exec -it nautilus_redis redis-cli -a $REDIS_PASSWORD FLUSHALL

# Prune Docker
docker system prune -af --volumes
```

---

## Support & Resources

- **Nautilus Trader Docs:** https://nautilustrader.io/docs/
- **Discord Community:** https://discord.gg/nautilustrader
- **GitHub Issues:** https://github.com/nautechsystems/nautilus_trader/issues
- **Your Trading Journal:** `/trading_journal/YYYY-MM-DD.md`

---

**Remember:** Trading involves risk. Only trade with capital you can afford to lose. Start small, be patient, and never stop learning.

**Last Updated:** January 2025  
**Version:** 1.0  
**Next Review:** After Phase 3 completion
