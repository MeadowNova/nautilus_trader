# Monitoring and Dashboard Guide

Complete guide to monitoring the Moomoo RL Paper Trading System in real-time.

## Table of Contents

1. [Dashboard Access](#dashboard-access)
2. [Grafana Dashboards](#grafana-dashboards)
3. [Log Analysis](#log-analysis)
4. [Performance Metrics](#performance-metrics)
5. [System Health Monitoring](#system-health-monitoring)
6. [Alerts and Notifications](#alerts-and-notifications)
7. [Database Queries](#database-queries)

---

## Dashboard Access

### Grafana (Primary Dashboard)

**URL:** http://localhost:3000

**Default Credentials:**
```
Username: admin
Password: (check infrastructure/.env.local for GRAFANA_PASSWORD)
```

**Dashboards Available:**
1. **Live Trading Monitor** - Real-time P&L, positions, orders
2. **RL Training Metrics** - Experience buffer, learning progress
3. **System Health** - CPU, memory, network latency
4. **Strategy Performance** - Win rate, R-multiples, expectancy

### Prometheus (Metrics Database)

**URL:** http://localhost:9090

**No authentication required.**

Use for:
- Raw metrics queries (PromQL)
- Alert rule testing
- Time-series data exploration

### Logs (File-Based)

**Location:** `/home/ajk/Nautilus/nautilus_trader/logs/`

**Latest log:**
```bash
tail -f logs/MOOMOO-RL-PAPER-001_*.log
```

---

## Grafana Dashboards

### 1. Live Trading Monitor

**Key Panels:**

#### Realized P&L (Top Left)
```promql
# Total realized P&L
nautilus_trading_pnl_realized_total

# P&L by strategy
sum by (strategy_id) (nautilus_trading_pnl_realized_total)
```

**Interpretation:**
- Green = profitable
- Red = losing
- Flat line = no trades

#### Unrealized P&L (Top Middle)
```promql
# Current open position P&L
nautilus_trading_pnl_unrealized_total
```

**Interpretation:**
- Shows live profit/loss on open positions
- Updates tick-by-tick

#### Position Count (Top Right)
```promql
# Number of open positions
nautilus_trading_positions_open
```

**Interpretation:**
- Should stay ≤ max_concurrent (8 default)
- Spikes may indicate stuck orders

#### Orders Per Minute (Middle Left)
```promql
# Order rate
rate(nautilus_orders_total[1m])
```

**Interpretation:**
- Should be < 15 per 30s (API limit)
- Sustained high rate = potential issue

#### Win Rate (Rolling 20 Trades) (Middle Right)
```promql
# Trailing win rate
sum(increase(nautilus_trades_wins_total[1h])) /
sum(increase(nautilus_trades_total[1h]))
```

**Interpretation:**
- Target: 40-55% depending on strategy
- < 35% for extended period = review needed

#### Cumulative P&L Chart (Bottom)
```promql
# Cumulative profit
sum(nautilus_trading_pnl_realized_total)
```

**Interpretation:**
- Should trend upward (with drawdowns)
- Flat/declining = strategy not working

### 2. RL Training Metrics

**Key Panels:**

#### Experience Buffer Size
```promql
nautilus_rl_buffer_size
```

**Interpretation:**
- Starts at 0, grows with trades
- Training begins at 1,000 experiences
- Target: 10,000+ for reliable training

#### Training Loss
```promql
nautilus_rl_policy_loss
```

**Interpretation:**
- Should decrease over time
- Plateaus are normal
- Sudden spikes = instability

#### TD Error (Mean)
```promql
nautilus_rl_td_error_mean
```

**Interpretation:**
- Measures prediction accuracy
- Lower = better predictions
- Target: < 0.5 after 10,000 experiences

#### Epsilon (Exploration Rate)
```promql
nautilus_rl_epsilon
```

**Interpretation:**
- Starts at 0.1 (10% random actions)
- Decays to 0.01 over time
- Higher = more exploration

#### Reward Distribution
```promql
histogram_quantile(0.5, nautilus_rl_reward_bucket)
```

**Interpretation:**
- Median reward should be positive
- Wide distribution = high variance

### 3. System Health

**Key Panels:**

#### CPU Usage
```promql
100 - (avg by (instance) (rate(node_cpu_seconds_total{mode="idle"}[5m])) * 100)
```

**Interpretation:**
- < 50% = healthy
- 50-80% = acceptable
- > 80% = investigate bottleneck

#### Memory Usage
```promql
(node_memory_MemTotal_bytes - node_memory_MemAvailable_bytes) /
node_memory_MemTotal_bytes * 100
```

**Interpretation:**
- < 60% = healthy
- 60-80% = monitor
- > 80% = risk of OOM

#### Network Latency (OpenD)
```promql
nautilus_moomoo_latency_ms
```

**Interpretation:**
- < 10ms = excellent
- 10-50ms = acceptable
- > 50ms = network issues

### 4. Strategy Performance

**Key Panels:**

#### R-Multiple Distribution
```promql
histogram_quantile(0.5, nautilus_strategy_r_multiple_bucket)
```

**Interpretation:**
- Median R-multiple should be > 0
- Target: 0.5R-1.5R depending on strategy

#### Expectancy
```promql
(sum(nautilus_trades_wins_total * nautilus_trades_avg_win) -
 sum(nautilus_trades_losses_total * nautilus_trades_avg_loss)) /
sum(nautilus_trades_total)
```

**Interpretation:**
- Positive = profitable system
- Target: > 0.20R
- Negative = losing system

#### Max Drawdown
```promql
max_over_time(nautilus_trading_pnl_peak[1d]) - nautilus_trading_pnl_realized_total
```

**Interpretation:**
- Should be < 10% of account
- Larger = riskier strategy

---

## Log Analysis

### Real-Time Log Monitoring

**Follow live logs:**
```bash
tail -f logs/MOOMOO-RL-PAPER-001_*.log
```

**Filter specific events:**
```bash
# Trades only
grep "TradeTick\|OrderFilled" logs/*.log | tail -n 20

# Errors only
grep "ERROR" logs/*.log | tail -n 50

# RL training events
grep "policy_loss\|td_error\|buffer_size" logs/*.log | tail -n 30

# Strategy signals
grep "EntrySignal\|ExitSignal\|z-score\|RSI" logs/*.log | tail -n 40
```

### Common Log Patterns

**Successful Trade Sequence:**
```log
[INFO] RLPairsTradingStrategy: Z-score: 2.31 (above entry 2.25)
[INFO] RLPairsTradingStrategy: Entering LONG_SPREAD position
[INFO] OrderAccepted: BUY 100 XLE.MOOMOO @ 85.23
[INFO] OrderFilled: BUY 100 XLE.MOOMOO @ 85.23 FILLED
[INFO] OrderAccepted: SELL 100 XLF.MOOMOO @ 42.15
[INFO] OrderFilled: SELL 100 XLF.MOOMOO @ 42.15 FILLED
...
[INFO] RLPairsTradingStrategy: Z-score: 0.18 (below exit 0.25)
[INFO] RLPairsTradingStrategy: Closing position
[INFO] OrderAccepted: SELL 100 XLE.MOOMOO @ 87.10
[INFO] OrderFilled: SELL 100 XLE.MOOMOO @ 87.10 FILLED
[INFO] OrderAccepted: BUY 100 XLF.MOOMOO @ 42.01
[INFO] OrderFilled: BUY 100 XLF.MOOMOO @ 42.01 FILLED
[INFO] PositionClosed: LONG_SPREAD, P&L: +172.00 USD
```

**RL Training Event:**
```log
[INFO] RLTrainer: Training step: epoch=15, policy_loss=0.0234, td_error=0.1523
[INFO] RLTrainer: Buffer size: 1,847, avg_reward: 0.0523
[INFO] RLTrainer: Epsilon: 0.092 (exploration rate)
[INFO] RLTrainer: Checkpoint saved: models/moomoo_rl_agent_20251209_153045.pt
```

**Error Conditions:**
```log
[ERROR] MoomooDataClient: No right to subscribe to US.XLE
→ Fix: Enable US market permissions

[ERROR] OrderRejected: Insufficient buying power
→ Fix: Reduce position size or check account balance

[WARNING] RiskEngine: Daily loss limit reached (3.00%)
→ Fix: Wait for next trading day or adjust limit

[ERROR] OpenD connection timeout
→ Fix: Restart OpenD gateway
```

### Log Rotation

Logs are automatically named with timestamps. Manage old logs:

```bash
# Archive logs older than 7 days
find logs/ -name "*.log" -mtime +7 -exec gzip {} \;

# Delete archived logs older than 30 days
find logs/ -name "*.log.gz" -mtime +30 -delete

# Check total log size
du -sh logs/
```

---

## Performance Metrics

### Key Performance Indicators (KPIs)

**Daily Review Metrics:**

```bash
# Connect to PostgreSQL
docker exec -it nautilus_postgres psql -U nautilus -d nautilus_trader

# Daily P&L
SELECT
    DATE(timestamp) as trade_date,
    COUNT(*) as num_trades,
    SUM(CASE WHEN pnl > 0 THEN 1 ELSE 0 END) as wins,
    SUM(CASE WHEN pnl < 0 THEN 1 ELSE 0 END) as losses,
    ROUND(SUM(pnl), 2) as total_pnl,
    ROUND(AVG(pnl), 2) as avg_pnl,
    ROUND(SUM(CASE WHEN pnl > 0 THEN 1 ELSE 0 END)::float / COUNT(*) * 100, 1) as win_rate_pct
FROM trades
WHERE timestamp >= CURRENT_DATE - INTERVAL '7 days'
GROUP BY DATE(timestamp)
ORDER BY trade_date DESC;
```

**Strategy Comparison:**

```sql
SELECT
    strategy_id,
    COUNT(*) as trades,
    SUM(CASE WHEN pnl > 0 THEN 1 ELSE 0 END) as wins,
    ROUND(AVG(pnl), 2) as avg_pnl,
    ROUND(SUM(pnl), 2) as total_pnl,
    ROUND(STDDEV(pnl), 2) as std_dev,
    ROUND(AVG(pnl) / NULLIF(STDDEV(pnl), 0), 2) as sharpe_approx
FROM trades
WHERE timestamp >= CURRENT_DATE - INTERVAL '30 days'
GROUP BY strategy_id
ORDER BY total_pnl DESC;
```

**R-Multiple Analysis:**

```sql
SELECT
    CASE
        WHEN r_multiple < -2 THEN '-2R or worse'
        WHEN r_multiple < -1 THEN '-1R to -2R'
        WHEN r_multiple < 0 THEN '0R to -1R'
        WHEN r_multiple < 1 THEN '0R to 1R'
        WHEN r_multiple < 2 THEN '1R to 2R'
        WHEN r_multiple < 3 THEN '2R to 3R'
        ELSE '3R or better'
    END as r_bucket,
    COUNT(*) as count,
    ROUND(AVG(pnl), 2) as avg_pnl
FROM trades
WHERE timestamp >= CURRENT_DATE - INTERVAL '30 days'
GROUP BY r_bucket
ORDER BY MIN(r_multiple);
```

### Expectancy Calculation

```python
# In Python (for detailed analysis)
import pandas as pd
import psycopg2

conn = psycopg2.connect("dbname=nautilus_trader user=nautilus host=localhost port=5435")
df = pd.read_sql("SELECT * FROM trades WHERE timestamp >= CURRENT_DATE - INTERVAL '30 days'", conn)

# Calculate expectancy
wins = df[df['pnl'] > 0]
losses = df[df['pnl'] < 0]

win_rate = len(wins) / len(df)
avg_win = wins['pnl'].mean()
avg_loss = abs(losses['pnl'].mean())

expectancy = (win_rate * avg_win) - ((1 - win_rate) * avg_loss)
print(f"Expectancy: ${expectancy:.2f} per trade")
print(f"Win Rate: {win_rate:.1%}")
print(f"Avg Win: ${avg_win:.2f}")
print(f"Avg Loss: ${avg_loss:.2f}")
```

---

## System Health Monitoring

### CPU and Memory

**Check resource usage:**

```bash
# Process CPU/memory
ps aux | grep start_paper_trading_moomoo

# Continuous monitoring
top -p $(pgrep -f start_paper_trading_moomoo)

# Memory breakdown
pmap $(pgrep -f start_paper_trading_moomoo) | tail -n 1
```

**Thresholds:**
- CPU > 80% sustained = investigate bottleneck
- Memory > 4GB = check for memory leak
- Swap usage > 0 = insufficient RAM

### Network Latency

**Test OpenD latency:**

```bash
python << 'EOF'
import time
from moomoo import OpenQuoteContext

ctx = OpenQuoteContext(host="127.0.0.1", port=11111)

# Measure round-trip time
start = time.time()
ret, data = ctx.get_global_state()
latency = (time.time() - start) * 1000

print(f"OpenD Latency: {latency:.2f} ms")

if latency < 10:
    print("✓ Excellent")
elif latency < 50:
    print("✓ Acceptable")
else:
    print("✗ High latency - check network")

ctx.close()
EOF
```

### Database Health

**Check PostgreSQL status:**

```bash
# Connection count
docker exec nautilus_postgres psql -U nautilus -d nautilus_trader -c \
  "SELECT count(*) FROM pg_stat_activity;"

# Database size
docker exec nautilus_postgres psql -U nautilus -d nautilus_trader -c \
  "SELECT pg_size_pretty(pg_database_size('nautilus_trader'));"

# Table sizes
docker exec nautilus_postgres psql -U nautilus -d nautilus_trader -c \
  "SELECT tablename, pg_size_pretty(pg_total_relation_size(schemaname||'.'||tablename))
   FROM pg_tables WHERE schemaname = 'public' ORDER BY pg_total_relation_size(schemaname||'.'||tablename) DESC;"
```

---

## Alerts and Notifications

### Prometheus Alerts

**Configure in `infrastructure/monitoring/prometheus/alerts.yml`:**

```yaml
groups:
  - name: trading_alerts
    rules:
      # Daily loss limit breached
      - alert: DailyLossLimitExceeded
        expr: nautilus_trading_daily_loss_pct > 3
        for: 1m
        annotations:
          summary: "Daily loss limit exceeded"
          description: "Daily loss is {{ $value }}%, limit is 3%"

      # Max drawdown alert
      - alert: MaxDrawdownExceeded
        expr: nautilus_trading_drawdown_pct > 10
        for: 5m
        annotations:
          summary: "Max drawdown exceeded"
          description: "Current drawdown is {{ $value }}%"

      # Win rate dropped
      - alert: LowWinRate
        expr: (sum(increase(nautilus_trades_wins_total[24h])) / sum(increase(nautilus_trades_total[24h]))) < 0.30
        for: 1h
        annotations:
          summary: "Win rate below 30%"
          description: "24h win rate is {{ $value | humanizePercentage }}"

      # High order rejection rate
      - alert: HighOrderRejectionRate
        expr: rate(nautilus_orders_rejected_total[5m]) > 0.1
        for: 5m
        annotations:
          summary: "High order rejection rate"
          description: "{{ $value }} orders rejected per second"
```

### Email Notifications (Optional)

**Install alertmanager:**

```bash
cd infrastructure/monitoring
docker compose up -d alertmanager

# Configure in alertmanager.yml
receivers:
  - name: 'email'
    email_configs:
      - to: 'your-email@example.com'
        from: 'trading-alerts@example.com'
        smarthost: 'smtp.gmail.com:587'
        auth_username: 'your-email@gmail.com'
        auth_password: 'app-password'
```

---

## Database Queries

### Useful PostgreSQL Queries

**Connect to database:**

```bash
docker exec -it nautilus_postgres psql -U nautilus -d nautilus_trader
```

**Query Examples:**

```sql
-- Recent trades (last 20)
SELECT timestamp, strategy_id, instrument_id, side, quantity, entry_price, exit_price, pnl, r_multiple
FROM trades
ORDER BY timestamp DESC
LIMIT 20;

-- Best performing instruments
SELECT instrument_id, COUNT(*) as trades, SUM(pnl) as total_pnl, AVG(pnl) as avg_pnl
FROM trades
WHERE timestamp >= CURRENT_DATE - INTERVAL '30 days'
GROUP BY instrument_id
ORDER BY total_pnl DESC;

-- Worst drawdown periods
SELECT DATE(timestamp) as date, MIN(cumulative_pnl) as lowest_point
FROM (
    SELECT timestamp, SUM(pnl) OVER (ORDER BY timestamp) as cumulative_pnl
    FROM trades
) sub
GROUP BY DATE(timestamp)
ORDER BY lowest_point ASC
LIMIT 10;

-- Holding period analysis
SELECT
    CASE
        WHEN bars_held < 10 THEN '< 10 bars'
        WHEN bars_held < 20 THEN '10-20 bars'
        WHEN bars_held < 40 THEN '20-40 bars'
        ELSE '40+ bars'
    END as hold_period,
    COUNT(*) as trades,
    AVG(pnl) as avg_pnl,
    SUM(CASE WHEN pnl > 0 THEN 1 ELSE 0 END)::float / COUNT(*) as win_rate
FROM trades
WHERE timestamp >= CURRENT_DATE - INTERVAL '30 days'
GROUP BY hold_period;
```

---

## Performance Review Checklist

**Daily (5 minutes):**
- [ ] Check Grafana for P&L trend
- [ ] Review error logs (grep "ERROR" logs/*.log)
- [ ] Verify no stuck orders
- [ ] Check daily loss vs limit

**Weekly (15 minutes):**
- [ ] Calculate expectancy (SQL query)
- [ ] Review R-multiple distribution
- [ ] Check strategy win rates
- [ ] Analyze RL training progress
- [ ] Archive old logs

**Monthly (30 minutes):**
- [ ] Generate performance report
- [ ] Compare vs backtest results
- [ ] Review parameter effectiveness
- [ ] Plan parameter adjustments (if needed)
- [ ] Backup database

---

**For troubleshooting dashboard issues, see [TROUBLESHOOTING.md](TROUBLESHOOTING.md#docker-service-problems).**
