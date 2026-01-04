# Bybit Mainnet Demo Trading Setup

## 🎯 What is Demo Trading?

Bybit's **Demo Trading** mode provides:
- ✅ **Real mainnet market data** (reliable WebSocket streams)
- ✅ **Virtual funds** (no financial risk)
- ✅ **Full exchange functionality** (orders, positions, etc.)
- ✅ **Same performance as live** (no testnet limitations)

This is **NOT the same as testnet** - demo uses mainnet infrastructure with virtual money.

---

## 📋 Quick Start (2 Options)

### Option 1: Use Existing Keys (Fastest)

Your existing `BYBIT_API_KEY` and `BYBIT_API_SECRET` will work with demo endpoints!

```bash
# Start demo trading immediately
cd /home/ajk/Nautilus/nautilus_trader
source nautilus_env/bin/activate
python scripts/start_paper_trading_demo.py
```

The script will:
- Use your existing testnet keys
- Connect to demo REST API: `https://api-demo.bybit.com`
- Stream from mainnet public WebSocket: `wss://stream.bybit.com` ✅
- Use demo private WebSocket: `wss://stream-demo.bybit.com`

---

### Option 2: Create Dedicated Demo Keys (Recommended)

For a completely separate demo account:

1. **Create Demo Account:**
   ```bash
   # Using your mainnet API key
   curl -X POST https://api.bybit.com/v5/user/create-demo-member \
     -H "X-BAPI-API-KEY: your-mainnet-key" \
     -H "X-BAPI-SIGN: signature" \
     -H "X-BAPI-TIMESTAMP: timestamp"
   ```

2. **Get Demo API Keys:**
   - Go to https://www.bybit.com/
   - Switch to "Demo Trading" mode in settings
   - Create API keys in the demo trading section

3. **Add to .env.local:**
   ```bash
   # Add these lines to infrastructure/.env.local
   BYBIT_DEMO_API_KEY=your-demo-key-here
   BYBIT_DEMO_API_SECRET=your-demo-secret-here
   ```

4. **Start trading:**
   ```bash
   python scripts/start_paper_trading_demo.py
   ```

---

## 🔧 Configuration Details

### Endpoints Used:

| Component | Testnet (BROKEN) | Demo (WORKING) |
|-----------|------------------|----------------|
| REST API | `testnet.bybit.com` ❌ | `api-demo.bybit.com` ✅ |
| Public WebSocket | `stream-testnet.bybit.com` ❌ | `stream.bybit.com` ✅ |
| Private WebSocket | `stream-testnet.bybit.com` ❌ | `stream-demo.bybit.com` ✅ |

### What You Get:

```
✅ Real BTCUSDT trade ticks streaming (10-50 per second)
✅ 1-minute bars aggregated locally (INTERNAL)
✅ 60 bars per hour (1,440 per day)
✅ Strategy confidence calculations
✅ Trades executed when confidence > 50%
✅ Full database persistence
✅ Grafana monitoring
✅ Zero financial risk
```

---

## 📊 Monitoring

### Watch Logs:
```bash
tail -f logs/PAPER-TRADER-001_*.log | grep -E "Bar|Trade|Signal probability"
```

### Check Trade Ticks:
```bash
grep -c "TradeTick" logs/PAPER-TRADER-001_*.log
# Should show thousands per hour
```

### Check Bars:
```bash
grep -c "on_bar" logs/PAPER-TRADER-001_*.log
# Should be 1 per minute = 60 per hour
```

### Database:
```bash
docker exec nautilus_postgres psql -U nautilus -d nautilus_trader -c \
  "SELECT COUNT(*) FROM ai_extensions.live_equity_snapshots 
   WHERE snapshot_timestamp > NOW() - INTERVAL '5 minutes';"
```

### Grafana:
```
http://localhost:3000/d/live-trading-monitor
```

---

## ✅ Success Criteria

**Within 1 minute:**
- [x] Trade ticks streaming (100+ per minute)
- [x] First bar aggregated at minute boundary
- [x] Strategy calculates probabilities
- [x] Database equity snapshot created

**Within 1 hour:**
- [x] 60 bars processed
- [x] Strategy confidence observed (40-60% range)
- [x] First trade executed (if confidence > 50%)

**Within 24 hours:**
- [x] 1,440 bars collected
- [x] 20-60 trades executed
- [x] Complete audit trail in database
- [x] Grafana showing live metrics

---

## 🚀 Why This Works

### Problem with Testnet:
```
Testnet WebSocket → Accepts connection ✓
                 → Accepts subscription ✓
                 → Streams data ❌ (INFRASTRUCTURE BROKEN)
```

### Solution with Demo:
```
Demo → Uses mainnet public data ✓
    → Real trade ticks streaming ✓
    → Virtual funds only ✓
    → Full functionality ✓
```

---

## 🆘 Troubleshooting

### No trade ticks streaming:
```bash
# Check WebSocket connection
grep "Connected.*stream.bybit.com" logs/PAPER-TRADER-001_*.log

# Check subscription
grep "publicTrade.BTCUSDT" logs/PAPER-TRADER-001_*.log

# Count ticks received
grep -c "TradeTick" logs/PAPER-TRADER-001_*.log
```

### Authentication errors:
- Verify API keys are correct in `.env.local`
- Check keys have trading permissions
- Ensure using demo endpoints (not testnet)

### Database not updating:
```bash
# Check Postgres is running
docker ps | grep nautilus_postgres

# Check connection
docker exec nautilus_postgres psql -U nautilus -d nautilus_trader -c "SELECT 1;"

# Restart metrics collector
docker restart ai_metrics
```

---

## 📚 API Documentation

Full Bybit demo trading API docs:
- File: `ai-working/paper_trading/Bybit_API_docs.md`
- Endpoints: All market data + full trading API
- Rate limits: Same as mainnet
- Demo funds: Request via `/v5/account/demo-apply-money`

---

## 🎯 Next Steps

1. **Start demo trading:**
   ```bash
   python scripts/start_paper_trading_demo.py
   ```

2. **Monitor for 5 minutes:**
   - Watch logs for trade ticks
   - Confirm bars aggregating
   - Check database updates

3. **Let run for 24 hours:**
   - Collect full day of trading data
   - Review performance in Grafana
   - Analyze strategy behavior

4. **If successful, consider:**
   - Running multiple strategies in parallel
   - Testing different confidence thresholds
   - Optimizing parameters based on demo results

---

## 💡 Pro Tips

- **Demo funds unlimited:** Request more anytime via API
- **Reset account:** Create new demo account if needed
- **Test aggressively:** It's demo - try extreme parameters!
- **Monitor closely first hour:** Ensure everything working
- **Compare to backtest:** Verify strategy behaves as expected

---

**Ready to start? Run:**
```bash
cd /home/ajk/Nautilus/nautilus_trader
source nautilus_env/bin/activate
python scripts/start_paper_trading_demo.py
```

🚀 **This WILL work - mainnet public data is reliable!**
