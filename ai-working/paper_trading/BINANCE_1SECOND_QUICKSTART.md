# Binance Testnet 1-Second Bar Paper Trading - Quick Start

**Created:** January 2025  
**Status:** Ready to Run

---

## 🚀 Quick Start (Copy/Paste Commands)

```bash
# 1. Navigate to project
cd /home/ajk/Nautilus/nautilus_trader

# 2. Activate virtual environment
source nautilus_env/bin/activate

# 3. Start Binance paper trading with 1-second bars
python scripts/start_paper_trading_binance.py
```

**Expected startup output:**
```
╔══════════════════════════════════════════════════════════════════╗
║         BINANCE TESTNET PAPER TRADING - 1-SECOND BARS            ║
╚══════════════════════════════════════════════════════════════════╝

✅ Loaded environment from: infrastructure/.env.local
✅ API credentials verified
✅ All clients verified as testnet mode
🔧 Initializing trading node...
📊 Configuring AI-Adaptive strategy (1-SECOND BARS)...
📊 Initializing database monitoring...
✅ Binance paper trading system ready!
```

---

## 📊 What to Expect

### Data Collection Rate
- **Bars per second:** 1
- **Bars per minute:** 60
- **Bars per hour:** 3,600
- **Bars per day:** 86,400
- **Bars per week:** 604,800

**Comparison:**
- Bybit 5-minute: 288 bars/day
- Bybit 1-minute: 1,440 bars/day
- **Binance 1-second: 86,400 bars/day (60x more!)**

### Trading Activity
- **Expected trades per day:** 50-200
- **Time to first trade:** < 5 minutes
- **Confidence threshold:** 0.60 (aggressive)
- **Max position time:** 5 minutes (300 seconds)

### Performance
- **Strategy processing time:** ~50ms per bar
- **Bar interval:** 1,000ms
- **Processing headroom:** 95% (very comfortable!)

---

## 📈 Monitoring Your Paper Trading

### Real-Time Monitoring (Grafana)

**Open Dashboard:**
```bash
firefox http://localhost:3000/d/live-trading-monitor
# Or: http://localhost:3000/d/live-trading-monitor
```

**What You'll See:**
- Session status: RUNNING
- Session runtime: Counting up
- Total equity: Starting at $100,000
- Equity curve: Live updates every 10 seconds
- Open positions: Live table
- Order statistics: Submitted, filled, rejected
- Win rate: Calculated after 10+ trades
- Profit factor: Updates live
- Recent alerts: Risk monitoring

### Database Queries

**Check Active Session:**
```bash
docker exec nautilus_postgres psql -U nautilus -d nautilus_trader -c \
  "SELECT trader_id, strategy_id, status, started_at 
   FROM ai_extensions.live_sessions 
   WHERE status='RUNNING' ORDER BY started_at DESC LIMIT 1;"
```

**Check Trade Count:**
```bash
docker exec nautilus_postgres psql -U nautilus -d nautilus_trader -c \
  "SELECT COUNT(*) as total_trades,
   SUM(CASE WHEN pnl > 0 THEN 1 ELSE 0 END) as wins,
   ROUND(AVG(pnl)::numeric, 2) as avg_pnl,
   ROUND(SUM(pnl)::numeric, 2) as total_pnl
   FROM ai_extensions.live_trades 
   WHERE session_id = (SELECT id FROM ai_extensions.live_sessions 
   WHERE status='RUNNING' ORDER BY started_at DESC LIMIT 1);"
```

**Check Recent Trades:**
```bash
docker exec nautilus_postgres psql -U nautilus -d nautilus_trader -c \
  "SELECT entry_price, exit_price, 
   ROUND(pnl::numeric, 2) as pnl,
   ROUND(realized_return_pct::numeric, 2) as return_pct,
   holding_period
   FROM ai_extensions.live_trades 
   WHERE session_id = (SELECT id FROM ai_extensions.live_sessions 
   WHERE status='RUNNING' ORDER BY started_at DESC LIMIT 1)
   ORDER BY exit_timestamp DESC LIMIT 10;"
```

**Check Equity Snapshots (should be many!):**
```bash
docker exec nautilus_postgres psql -U nautilus -d nautilus_trader -c \
  "SELECT COUNT(*) as snapshot_count,
   MIN(captured_at) as first_snapshot,
   MAX(captured_at) as latest_snapshot
   FROM ai_extensions.live_equity_snapshots 
   WHERE session_id = (SELECT id FROM ai_extensions.live_sessions 
   WHERE status='RUNNING' ORDER BY started_at DESC LIMIT 1);"
```

### Prometheus Metrics

**Check Session Status:**
```bash
curl -s http://localhost:9100/metrics | grep "ai_live_session_status"
```

**Check Equity:**
```bash
curl -s http://localhost:9100/metrics | grep "ai_live_equity_total"
```

**Check Trade Count:**
```bash
curl -s http://localhost:9100/metrics | grep "ai_live_trades_total"
```

**Check Win Rate:**
```bash
curl -s http://localhost:9100/metrics | grep "ai_live_win_rate"
```

### Log Monitoring

**Watch bars arriving (should be FAST!):**
```bash
tail -f logs/PAPER-TRADER-001_*.log | grep "Bar"
```

**Watch trading activity:**
```bash
tail -f logs/PAPER-TRADER-001_*.log | grep -E "Order|Trade|Fill"
```

**Watch all activity:**
```bash
tail -f logs/PAPER-TRADER-001_*.log
```

---

## 🛑 Stopping Paper Trading

**In the terminal running paper trading:**
```
Press Ctrl+C
```

**Verify it stopped:**
```bash
docker exec nautilus_postgres psql -U nautilus -d nautilus_trader -c \
  "SELECT status, stopped_at FROM ai_extensions.live_sessions 
   ORDER BY started_at DESC LIMIT 1;"
```

---

## 🔧 Troubleshooting

### Issue: No bars arriving

**Check logs:**
```bash
tail -f logs/PAPER-TRADER-001_*.log
```

**Possible causes:**
- WebSocket connection issue
- API keys invalid
- VPN blocking connection to testnet.binance.vision

**Solution:**
- Verify API keys at https://testnet.binance.vision/
- Ensure API trading is enabled
- Check network connectivity

### Issue: Orders rejected

**Check rejection reason:**
```bash
docker exec nautilus_postgres psql -U nautilus -d nautilus_trader -c \
  "SELECT status, rejection_reason 
   FROM ai_extensions.live_orders 
   WHERE status = 'REJECTED' 
   ORDER BY submitted_at DESC LIMIT 5;"
```

**Common causes:**
- Insufficient testnet balance
- Order size too small/large
- Invalid price

**Solution:**
- Fund testnet account at https://testnet.binance.vision/
- Check order parameters in logs

### Issue: Too many/too few trades

**Too many trades (>300/day):**
```python
# Edit scripts/start_paper_trading_binance.py
# Line ~127: Increase confidence threshold
confidence_threshold=0.70,  # From 0.60
```

**Too few trades (<20/day):**
```python
# Edit scripts/start_paper_trading_binance.py
# Line ~127: Decrease confidence threshold
confidence_threshold=0.55,  # From 0.60
```

**Restart after changes:**
```bash
# Stop with Ctrl+C
# Edit file
# Restart:
python scripts/start_paper_trading_binance.py
```

### Issue: Win rate too low (<40%)

**Make strategy more conservative:**
```python
# Edit scripts/start_paper_trading_binance.py
confidence_threshold=0.75,  # More selective
max_bars_in_position=600,   # 10 minutes (from 5 minutes)
```

### Issue: Grafana shows "No data"

**Check metrics collector:**
```bash
docker ps | grep ai_metrics
docker logs ai_metrics --tail 50
```

**Restart metrics collector:**
```bash
docker restart ai_metrics
```

**Verify Prometheus scraping:**
```bash
curl http://localhost:9090/api/v1/targets | jq '.data.activeTargets[] | select(.labels.job == "ai_metrics")'
```

---

## 📊 Performance Targets

### After 1 Hour
- [ ] Bars collected: 3,600+
- [ ] Trades executed: 5-15
- [ ] Win rate: > 40%
- [ ] No rejected orders
- [ ] System stable

### After 24 Hours
- [ ] Bars collected: 86,400+
- [ ] Trades executed: 50-200
- [ ] Win rate: > 50%
- [ ] Profit factor: > 1.2
- [ ] Max drawdown: < 15%

### After 1 Week
- [ ] Bars collected: 604,800+
- [ ] Trades executed: 350-1400
- [ ] Consistent win rate
- [ ] Ready for analysis

---

## 💾 Data Collected

### Database Tables Populated

**1. live_sessions:**
- Session metadata
- Start/end times
- Configuration used

**2. live_positions:**
- Open and closed positions
- Entry/exit details
- P&L calculations

**3. live_orders:**
- All order submissions
- Fill information
- Rejections (if any)

**4. live_trades:**
- Complete round-trip trades
- Performance metrics
- Holding periods

**5. live_equity_snapshots:**
- Captured every minute
- Full account state
- Equity curve data

**6. live_performance_metrics:**
- Aggregated statistics
- Win rate, profit factor
- Sharpe ratio
- Risk metrics

---

## 🎯 Next Steps

### After 24-48 Hours

**1. Analyze Performance:**
```bash
# Run comprehensive analysis
docker exec nautilus_postgres psql -U nautilus -d nautilus_trader -c \
  "SELECT * FROM ai_extensions.v_live_trading_summary 
   WHERE session_id = (SELECT id FROM ai_extensions.live_sessions 
   WHERE status='STOPPED' ORDER BY stopped_at DESC LIMIT 1);"
```

**2. Compare to Backtest:**
```bash
# See how paper trading compares to historical backtest
docker exec nautilus_postgres psql -U nautilus -d nautilus_trader -c \
  "SELECT 
     'Paper Trading' as source,
     AVG(win_rate) as avg_win_rate,
     AVG(profit_factor) as avg_pf
   FROM ai_extensions.live_performance_metrics
   UNION ALL
   SELECT 
     'Backtest' as source,
     AVG(win_rate),
     AVG(profit_factor)
   FROM ai_extensions.backtest_metrics
   WHERE strategy_id = 'AIAdaptiveStrategyV3';"
```

**3. Tune Parameters:**
- If outperforming backtest: Great!
- If underperforming: Adjust confidence threshold
- If too volatile: Increase max_bars_in_position

### After 1 Week

**1. Export Data for Analysis:**
```bash
# Export all trades to CSV
docker exec nautilus_postgres psql -U nautilus -d nautilus_trader -c \
  "COPY (SELECT * FROM ai_extensions.live_trades 
   WHERE session_id IN (SELECT id FROM ai_extensions.live_sessions 
   WHERE trader_id='PAPER-TRADER-001')) 
   TO STDOUT WITH CSV HEADER" > paper_trading_trades.csv
```

**2. Consider Live Trading:**
- If performance is good and stable
- Switch to real Binance account
- Start with small capital ($500-1000)
- Use more conservative settings

---

## 📚 Related Documentation

- **Full Implementation Plan:** `ai-working/paper_trading/plan.md`
- **Bybit Limitations:** `ai-working/paper_trading/BYBIT_LIMITATIONS.md`
- **Trading Frequency Guide:** `ai-working/paper_trading/TRADING_FREQUENCY_EXPLAINED.md`
- **Monitoring Guide:** `ai-working/backtest-to-grafana-setup/LIVE_TRADING_METRICS_GUIDE.md`
- **Infrastructure Status:** `ai-working/backtest-to-grafana-setup/FINAL_STATUS.md`

---

## 🔐 Safety Reminders

- ✅ This is TESTNET only (no real money)
- ✅ All trades are with simulated testnet funds
- ✅ Multiple safety checks prevent live trading
- ✅ Full audit trail in database
- ✅ Can stop anytime with Ctrl+C

**When you're ready for LIVE trading:**
1. Change `testnet=False` in configuration
2. Use real Binance API keys
3. Start with minimal capital ($500-1000)
4. Use MORE conservative settings (confidence=0.80+)

---

**Good luck with your maximum data collection!** 🚀

You're collecting **60x more data** than with 1-minute bars - this dataset will be excellent for ML model training and strategy validation.
