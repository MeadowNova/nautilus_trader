# Troubleshooting Guide

Comprehensive solutions to common issues with the Moomoo RL Trading System.

## Quick Diagnostics

```bash
# Run automated diagnostic
cd /home/ajk/Nautilus/nautilus_trader
source .venv/bin/activate
python scripts/diagnostics/check_moomoo_system.py
```

## Table of Contents

1. [Market Data Permission Errors](#market-data-permission-errors) ⚠️ **Most Common**
2. [OpenD Connection Issues](#opend-connection-issues)
3. [Strategy Not Trading](#strategy-not-trading)
4. [Docker Service Problems](#docker-service-problems)
5. [Reconciliation Method Errors](#reconciliation-method-errors)
6. [Bar Subscription Errors](#bar-subscription-errors)
7. [Order Execution Failures](#order-execution-failures)
8. [RL Training Issues](#rl-training-issues)
9. [Performance Problems](#performance-problems)
10. [Data Quality Issues](#data-quality-issues)

---

## Market Data Permission Errors

### Error: "No right to subscribe the quote for US.XLE"

**Frequency:** Very Common (90% of first-time issues)

**Full Error:**
```
[ERROR] MoomooDataClient: Failed to subscribe to US.XLE
futu.common.err.handlers.SysNotifyHandlers: No right to subscribe the quote for US.XLE
```

**Root Cause:** US market real-time quote permissions not enabled in Moomoo account.

**Solution:**

#### Step 1: Enable Permissions in Moomoo App

**Mobile App (Recommended):**
1. Open Moomoo app
2. Tap **Quotes** → **Markets** → **US Stocks**
3. Select any US stock (e.g., AAPL)
4. Look for "Apply for Real-Time Quotes" banner at top
5. Tap **Apply Now**
6. Read and accept terms (usually free for basic access)
7. **Wait 2-5 minutes** for activation
8. Verify: Check if stock shows real-time price (not delayed)

**Desktop App:**
1. Open Moomoo desktop application
2. Go to **Settings** → **Market Data** → **Quote Settings**
3. Find **US Stock Market - Real-Time Level 1**
4. Click **Subscribe** or **Apply**
5. Accept terms
6. Wait for confirmation notification

#### Step 2: Verify Activation

```bash
python << 'EOF'
from moomoo import OpenQuoteContext

ctx = OpenQuoteContext(host="127.0.0.1", port=11111)
ret, data = ctx.subscribe(['US.AAPL'], ['QUOTE'])

if ret == 0:
    print("✓ Permissions activated successfully!")
else:
    print(f"✗ Still denied: {data}")
    print("\nTroubleshooting:")
    print("1. Wait longer (up to 10 minutes)")
    print("2. Restart OpenD gateway")
    print("3. Re-login to Moomoo app")
    print("4. Check account is not restricted")

ctx.close()
EOF
```

#### Step 3: Restart OpenD

After enabling permissions:

```bash
# Kill OpenD
killall OpenD

# Restart (in OpenD directory)
./OpenD
```

#### Step 4: Test Trading System

```bash
cd /home/ajk/Nautilus/nautilus_trader
python scripts/start_paper_trading_moomoo.py
```

**Still failing?**
- **Wait longer:** Permissions can take 10-15 minutes
- **Check spam/email:** Approval email may be in spam
- **Account verification:** Ensure account is fully verified
- **Contact support:** Via Moomoo app chat support

### Error: "Subscription quota exceeded"

**Error:**
```
[ERROR] Subscription failed: Quota limit 500 reached
```

**Cause:** Too many instruments subscribed simultaneously.

**Solution:**

```python
# Reduce instruments in start_paper_trading_moomoo.py
all_instruments = (
    "XLE.MOOMOO",
    "XLF.MOOMOO",
    "NVDA.MOOMOO",
    "SPY.MOOMOO",    # Reduced from 10+ instruments
)

# Or upgrade Moomoo plan for higher quota
```

---

## OpenD Connection Issues

### Error: "Connection refused: localhost:11111"

**Error:**
```
[ERROR] Failed to connect to OpenD at 127.0.0.1:11111
ConnectionRefusedError: [Errno 111] Connection refused
```

**Diagnosis:**

```bash
# Check if OpenD is running
ps aux | grep OpenD

# Check port is listening
lsof -i :11111

# Check for port conflicts
netstat -tulpn | grep 11111
```

**Solutions:**

#### Solution 1: Start OpenD

```bash
cd /path/to/OpenD
./OpenD

# Should output: "OpenD started on port 11111"
```

#### Solution 2: Check Firewall

```bash
# Ubuntu/Debian
sudo ufw allow 11111/tcp

# CentOS/RHEL
sudo firewall-cmd --add-port=11111/tcp --permanent
sudo firewall-cmd --reload

# macOS
# System Preferences → Security & Privacy → Firewall
# Add OpenD to allowed applications
```

#### Solution 3: Change Port

If port 11111 is occupied:

**In OpenD:**
1. Open OpenD settings
2. Change port to 11112 or another free port
3. Restart OpenD

**In trading system:**
```bash
# Edit environment
export MOOMOO_PORT=11112

# Or edit infrastructure/.env.local
MOOMOO_PORT=11112
```

### Error: "OpenD authentication failed"

**Error:**
```
[ERROR] Login failed: Invalid trading password
```

**Cause:** Incorrect trading password (6-digit PIN, not account password).

**Solution:**

1. Reset trading password in Moomoo app:
   - **Me** → **Settings** → **Security** → **Trading Password**
   - **Reset** → Follow SMS verification
   - Set new 6-digit PIN

2. Re-login in OpenD:
   - Close OpenD
   - Start OpenD
   - Enter Moomoo username + **trading password**

### Error: "OpenD session expired"

**Error:**
```
[ERROR] Session timeout, please re-login
```

**Cause:** OpenD sessions expire after 24 hours.

**Solution:**

```bash
# Restart OpenD (will prompt for login)
killall OpenD
./OpenD

# Or enable auto-login in OpenD settings
# (less secure, use only on trusted systems)
```

---

## Strategy Not Trading

### Issue: Strategies load but generate no signals

**Symptoms:**
- Logs show quotes/bars arriving
- No "EntrySignal" or "OrderAccepted" messages
- Strategies remain idle for hours

**Diagnosis:**

```bash
# Check if bars are being received
grep "on_bar" logs/MOOMOO-RL-PAPER-001_*.log | tail -n 10

# Check current indicator values
grep "z-score\|RSI\|ATR" logs/MOOMOO-RL-PAPER-001_*.log | tail -n 20

# Check market hours
grep "Market.*state" logs/MOOMOO-RL-PAPER-001_*.log
```

**Common Causes:**

#### Cause 1: Outside Market Hours

US market: 9:30 AM - 4:00 PM ET (pre/post market not supported by default)

**Solution:** Wait for market open or enable extended hours:

```python
# In start_paper_trading_moomoo.py
data_clients={
    "MOOMOO": MoomooDataClientConfig(
        gateway=gateway_config,
        use_extended_hours=True,  # Enable pre/post market
    )
}
```

#### Cause 2: Entry Conditions Not Met

**Pairs Trading:** Z-score must exceed 2.25 (or your entry threshold)

```bash
# Check current z-score
grep "z-score" logs/*.log | tail -n 5
# Example: "z-score: 1.45" → Below 2.25, no entry
```

**Momentum Breakout:** Price must break 15-day high with 1.75x volume

```bash
# Check breakout status
grep "breakout\|RSI" logs/*.log | tail -n 10
```

**Solution:** Wait for conditions or lower thresholds (not recommended):

```python
# Lower entry threshold (riskier)
pairs_config = RLPairsTradingConfig(
    zscore_entry=2.0,  # Lowered from 2.25
)
```

#### Cause 3: Risk Limits Hit

Daily loss limit or max positions reached.

**Diagnosis:**
```bash
grep "risk.*limit\|max.*position" logs/*.log
```

**Solution:**
- Wait for next trading day (daily loss limit)
- Close positions (max concurrent limit)
- Adjust risk settings in config

#### Cause 4: Insufficient Historical Data

Strategies need lookback period data before trading.

**Example:** Pairs strategy needs 40 bars (40 minutes with 1-min bars)

```bash
# Check bar count
grep "on_bar.*count" logs/*.log | tail -n 1
```

**Solution:** Wait 40-60 minutes after start for initial bars to accumulate.

---

## Docker Service Problems

### Error: "Cannot connect to PostgreSQL"

**Error:**
```
[ERROR] psycopg2.OperationalError: could not connect to server: Connection refused
```

**Diagnosis:**

```bash
# Check if PostgreSQL container is running
docker ps | grep postgres

# Check logs
docker logs nautilus_postgres

# Check port
lsof -i :5435
```

**Solutions:**

#### Solution 1: Start Services

```bash
cd /home/ajk/Nautilus/nautilus_trader/infrastructure/docker
docker compose --env-file ../.env.local up -d

# Wait 30 seconds for healthy status
docker ps --format "table {{.Names}}\t{{.Status}}"
```

#### Solution 2: Port Conflict

```bash
# Check if port 5435 is in use
lsof -i :5435

# If occupied, change port in infrastructure/.env.local
DB_PORT=5436  # Use different port

# Restart with new port
docker compose --env-file ../.env.local down
docker compose --env-file ../.env.local up -d
```

#### Solution 3: Reset Database

```bash
# Nuclear option: delete and recreate
docker compose --env-file ../.env.local down -v
docker compose --env-file ../.env.local up -d
```

### Error: "Grafana dashboard not loading"

**Diagnosis:**

```bash
# Check Grafana is running
docker ps | grep grafana

# Check logs
docker logs nautilus_grafana | tail -n 50

# Access directly
curl http://localhost:3000/api/health
```

**Solutions:**

1. **Restart Grafana:**
   ```bash
   docker restart nautilus_grafana
   ```

2. **Check credentials in .env.local:**
   ```bash
   grep GRAFANA infrastructure/.env.local
   # Should show GRAFANA_USER and GRAFANA_PASSWORD
   ```

3. **Reimport dashboards:**
   ```bash
   # Dashboards in infrastructure/monitoring/grafana/dashboards/
   # Import manually via Grafana UI
   ```

---

## Reconciliation Method Errors

### Error: "method 'generate_order_status_reports' must be implemented"

**Full Error:**
```
NotImplementedError: method 'generate_order_status_reports' must be implemented in the subclass to support reconciliation on start
```

**Cause:** Moomoo execution adapter missing reconciliation methods (fixed in v1.0).

**Verification:**

```bash
# Check if reconciliation methods exist
grep -n "generate_order_status_reports\|generate_fill_reports\|generate_position_status_reports" \
  /home/ajk/Nautilus/nautilus_trader/nautilus_trader/adapters/moomoo/execution.py
```

**Solution:**

The methods should already be implemented. If missing, they need to be added to `execution.py`:

```python
# These methods are documented in /home/ajk/Nautilus/MOOMOO_FIXES_PRIORITY1.py
# Key methods:
async def generate_order_status_reports(self, command) -> list[OrderStatusReport]:
    # Queries self._trd_ctx.order_list_query()

async def generate_fill_reports(self, command) -> list[FillReport]:
    # Queries self._trd_ctx.deal_list_query()

async def generate_position_status_reports(self, command) -> list[PositionStatusReport]:
    # Queries self._trd_ctx.position_list_query()
```

**If methods are missing:**

1. **Check NautilusTrader version:**
   ```bash
   python -c "import nautilus_trader; print(nautilus_trader.__version__)"
   # Should be >= 1.221.0
   ```

2. **Apply the fix manually:**
   - See `/home/ajk/Nautilus/MOOMOO_FIXES_PRIORITY1.py` for complete implementation
   - Copy methods into `execution.py` at line 527+

3. **Reinstall adapter:**
   ```bash
   cd /home/ajk/Nautilus/nautilus_trader
   make install-debug
   ```

---

## Bar Subscription Errors

### Error: "Argument 'bar_type' has incorrect type (expected BarType, got InstrumentId)"

**Full Error:**
```
TypeError: Argument 'bar_type' has incorrect type (expected BarType, got InstrumentId)
```

**Cause:** Strategy calling `subscribe_bars(instrument_id)` instead of `subscribe_bars(bar_type)`.

**Solution:**

Fix in strategy code (e.g., `ajk_strategies/rl_strategies/pairs_trading.py`):

```python
# WRONG:
self.subscribe_bars(self.instrument_a)

# CORRECT:
from nautilus_trader.model.data import BarType

bar_type_a = BarType.from_str(f"{self.instrument_a}-1-MINUTE-LAST-EXTERNAL")
self.subscribe_bars(bar_type_a)
```

**BarType format:** `{instrument_id}-{step}-{aggregation}-{price_type}-EXTERNAL`

Examples:
```python
"XLE.MOOMOO-1-MINUTE-LAST-EXTERNAL"     # 1-minute bars, last price
"NVDA.MOOMOO-5-MINUTE-MID-EXTERNAL"     # 5-minute bars, mid price
"SPY.MOOMOO-1-HOUR-LAST-EXTERNAL"       # 1-hour bars
```

---

## Order Execution Failures

### Error: "Order rejected: Insufficient buying power"

**Diagnosis:**

```bash
# Check account balance
python << 'EOF'
from moomoo import OpenSecTradeContext, TrdEnv

ctx = OpenSecTradeContext(host="127.0.0.1", port=11111)
ret, data = ctx.accinfo_query(trd_env=TrdEnv.SIMULATE)

if ret == 0:
    print(f"Cash: {data['cash'][0]}")
    print(f"Buying power: {data['power'][0]}")
else:
    print(f"Error: {data}")

ctx.close()
EOF
```

**Solutions:**

1. **Increase paper account balance:**
   - Moomoo app → Paper Trading → Settings → Reset Account
   - Set higher initial balance (e.g., $100,000)

2. **Reduce position sizes:**
   ```python
   position_size_pct = 0.01  # Reduce to 1%
   ```

3. **Check for stuck orders:**
   ```bash
   grep "OrderAccepted.*NOT.*Filled" logs/*.log
   # Cancel stuck orders manually in Moomoo app
   ```

### Error: "Order rate limit exceeded"

**Error:**
```
[ERROR] Order failed: API rate limit: 15 orders per 30 seconds exceeded
```

**Solution:**

Add rate limiting to adapter config:

```python
exec_clients={
    "MOOMOO": MoomooExecClientConfig(
        gateway=gateway_config,
        max_orders_per_30s=10,  # Reduce from 15 to add buffer
    )
}
```

---

## RL Training Issues

### Issue: Experience buffer not growing

**Diagnosis:**

```bash
# Check buffer size in logs
grep "buffer.*size\|experience.*added" logs/*.log | tail -n 20
```

**Causes:**

1. **No trades executed** → Buffer only grows when trades complete
2. **Experience storage disabled** → Check `experience_buffer` is passed to strategies
3. **Buffer full** → Increase capacity:

```python
experience_buffer = PrioritizedReplayBuffer(
    capacity=200000,  # Increase from 100000
)
```

### Issue: Training loss not decreasing

**Symptoms:**
- Training runs but loss stays constant
- No improvement in strategy performance

**Diagnosis:**

```bash
grep "policy_loss\|td_error" logs/*.log | tail -n 50
```

**Solutions:**

1. **Increase training frequency:**
   ```python
   train_config = TrainingConfig(
       train_every_n=50,  # Train every 50 experiences (was 100)
   )
   ```

2. **Adjust learning rate:**
   ```python
   learning_rate=1e-4,  # Reduce if loss oscillating
   learning_rate=1e-3,  # Increase if loss stuck
   ```

3. **Check reward signal quality:**
   ```bash
   grep "reward" logs/*.log | tail -n 100
   # Should show mix of positive and negative rewards
   ```

---

## Performance Problems

### Issue: High CPU usage

**Diagnosis:**

```bash
# Check process CPU
top -p $(pgrep -f start_paper_trading_moomoo)

# Check which component is hot
py-spy top --pid $(pgrep -f start_paper_trading_moomoo)
```

**Solutions:**

1. **Reduce bar aggregation frequency:**
   ```python
   # Use 5-minute bars instead of 1-minute
   "NVDA.MOOMOO-5-MINUTE-LAST-EXTERNAL"
   ```

2. **Limit concurrent instruments:**
   ```python
   max_concurrent=3  # Reduce from 5
   ```

3. **Disable unnecessary logging:**
   ```python
   log_level="WARNING"  # Change from INFO
   ```

### Issue: High memory usage

**Diagnosis:**

```bash
# Check memory
ps aux | grep start_paper_trading_moomoo

# Monitor over time
watch -n 5 'ps aux | grep start_paper_trading_moomoo'
```

**Solutions:**

1. **Reduce buffer size:**
   ```python
   capacity=50000  # Reduce from 100000
   ```

2. **Limit bar history:**
   ```python
   lookback_bars=5  # Reduce from 10
   ```

3. **Clear old logs:**
   ```bash
   # Archive logs older than 7 days
   find logs/ -name "*.log" -mtime +7 -exec gzip {} \;
   ```

---

## Data Quality Issues

### Issue: Stale or delayed quotes

**Symptoms:**
- Quote timestamps are old
- Prices don't match live market
- Bars not updating

**Diagnosis:**

```bash
# Check latest quote timestamp
grep "QuoteTick" logs/*.log | tail -n 5

# Should be within 1-2 seconds of current time
```

**Solutions:**

1. **Restart OpenD** (most common fix):
   ```bash
   killall OpenD && ./OpenD
   ```

2. **Check market hours:**
   - Pre-market: 4:00-9:30 AM ET (extended hours)
   - Regular: 9:30 AM - 4:00 PM ET
   - After-hours: 4:00-8:00 PM ET (extended hours)

3. **Verify real-time permissions still active:**
   ```python
   # Run permission check from CONFIGURATION.md
   ```

### Issue: Missing bars for instruments

**Symptoms:**
- Some instruments update, others don't
- Gaps in bar data

**Diagnosis:**

```bash
# Check bars per instrument
grep "on_bar" logs/*.log | awk '{print $NF}' | sort | uniq -c
```

**Solutions:**

1. **Verify subscription succeeded:**
   ```bash
   grep "subscribe.*success\|subscribe.*failed" logs/*.log | grep -i nvda
   ```

2. **Check instrument is trading:**
   - May be halted or delisted
   - Check in Moomoo app directly

3. **Resubscribe:**
   ```bash
   # Restart trading system
   Ctrl+C
   python scripts/start_paper_trading_moomoo.py
   ```

---

## Emergency Procedures

### Procedure: Emergency Stop All Trading

```bash
# 1. Stop trading system
pkill -SIGTERM -f start_paper_trading_moomoo

# 2. Close all positions in Moomoo app
#    Go to: Portfolio → Select All → Close

# 3. Cancel all open orders
#    Go to: Orders → Cancel All

# 4. Stop infrastructure (optional)
cd infrastructure/docker
docker compose --env-file ../.env.local down
```

### Procedure: Reset System to Clean State

```bash
# 1. Stop everything
pkill -f start_paper_trading_moomoo
killall OpenD

# 2. Clear logs (backup first!)
mkdir -p logs/backup
mv logs/*.log logs/backup/

# 3. Reset database
cd infrastructure/docker
docker compose --env-file ../.env.local down -v
docker compose --env-file ../.env.local up -d

# 4. Reset paper trading account in Moomoo app
#    Paper Trading → Settings → Reset Account

# 5. Restart fresh
cd /home/ajk/Nautilus/nautilus_trader
./OpenD &
python scripts/start_paper_trading_moomoo.py
```

---

## Getting Help

### Collect Diagnostic Information

Before asking for help, collect:

```bash
# 1. System info
uname -a
python --version
docker --version

# 2. NautilusTrader version
python -c "import nautilus_trader; print(nautilus_trader.__version__)"

# 3. Recent logs (last 100 lines)
tail -n 100 logs/MOOMOO-RL-PAPER-001_*.log > diagnostic_logs.txt

# 4. Docker status
docker ps > docker_status.txt

# 5. OpenD status
lsof -i :11111 > opend_status.txt

# Create diagnostic bundle
tar -czf diagnostic_bundle.tar.gz diagnostic_logs.txt docker_status.txt opend_status.txt
```

### Support Channels

1. **NautilusTrader Issues:** https://github.com/nautechsystems/nautilus_trader/issues
2. **Moomoo API Support:** Via Moomoo app → Help → Contact Support
3. **System Logs:** Review `logs/MOOMOO-RL-PAPER-001_*.log` first

---

**Most issues (80%+) are resolved by:**
1. Enabling US market data permissions
2. Restarting OpenD
3. Waiting for market hours
4. Checking risk limits

**If none of these help, see diagnostic collection above.**
