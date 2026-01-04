# Multi-Factor Strategy - Quick Start Guide

## Prerequisites

1. **Moomoo OpenD** - Running on localhost:11111
2. **PostgreSQL** - Running on localhost:5435
3. **Prometheus** - Running on localhost:9090
4. **Grafana** - Running on localhost:3000
5. **Python packages** - yfinance, psycopg, prometheus_client, moomoo-api

## Installation

All dependencies should already be installed. Verify:

```bash
pip list | grep -E "(yfinance|psycopg|prometheus|moomoo)"
```

Expected output:
```
moomoo_api                               9.4.5408
prometheus_client                        0.22.1
psycopg                                  3.1.19
yfinance                                 0.2.66
```

## Step 1: Start Moomoo OpenD

In a separate terminal:

```bash
# Navigate to Moomoo OpenD installation directory
# Start OpenD (this varies by OS)
# Verify it's running on localhost:11111
```

## Step 2: Test Connectivity

```bash
python /home/ajk/Nautilus/nautilus_trader/scripts/test_hybrid_connection.py
```

Expected output:
```
[Test 1] Testing yfinance data access...
  ✓ Successfully fetched SPY data
  ✓ Successfully fetched AAPL data

[Test 2] Testing Moomoo OpenD connectivity...
  ✓ Connected to OpenD
  ✓ Market state: US_OPEN
  ✓ Paper trading accounts: 2
```

If this fails, troubleshoot:
- **yfinance error**: Check internet connection
- **Moomoo error**: Verify OpenD is running, check firewall

## Step 3: Verify PostgreSQL

```bash
psql postgresql://localhost:5435/nautilus -c "SELECT 1"
```

If connection fails:
```bash
# Start PostgreSQL (if not running)
# Or update POSTGRES_CONN_STRING environment variable
export POSTGRES_CONN_STRING="postgresql://your_connection_string"
```

## Step 4: Launch Strategy

```bash
cd /home/ajk/Nautilus/nautilus_trader
python scripts/live_multi_factor_strategy.py
```

Expected startup sequence:
```
PRODUCTION MULTI-FACTOR STRATEGY - LIVE TRADING
================================================

[1/5] Initializing data provider...
[2/5] Connecting to Moomoo OpenD...
  US Market state: US_OPEN
  Stock Account: 1252643
  Options Account: 1252648
[3/5] Connecting to PostgreSQL...
[4/5] Starting Prometheus metrics server...
  Prometheus metrics: http://localhost:8000/metrics
[5/5] Initializing strategy...

LIVE TRADING ACTIVE
================================================================================

Initial Capital: $100,000.00
Symbols: SPY, AAPL, NVDA
Update Interval: 60s

Metrics: http://localhost:8000/metrics
Grafana: http://localhost:3000

Press Ctrl+C to stop
```

## Step 5: Monitor Metrics

### View Prometheus Metrics
Open browser: http://localhost:8000/metrics

Key metrics to check:
```
multifactor_portfolio_value_dollars
multifactor_alpha_signal{symbol="SPY"}
multifactor_regime_state{symbol="SPY"}
```

### View Grafana Dashboard
Open browser: http://localhost:3000

1. Login (default: admin/admin)
2. Add Prometheus data source:
   - URL: http://localhost:9090
   - Access: Browser
   - Save & Test
3. Import dashboard (see GRAFANA_DASHBOARD.json below)

### Query PostgreSQL Trades
```bash
psql postgresql://localhost:5435/nautilus -c "
  SELECT symbol, direction, entry_price, exit_price, pnl, pnl_pct, exit_reason
  FROM multifactor_trades
  ORDER BY entry_time DESC
  LIMIT 10;
"
```

## Step 6: Monitor Console Output

The strategy will log each iteration:

```
================================================================================
ITERATION 1 - 2025-12-09 14:30:00
================================================================================

[14:30:00] Updating data from yfinance...
  SPY: $450.25 (history: 180 bars)
  AAPL: $195.50 (history: 180 bars)
  NVDA: $495.75 (history: 180 bars)

[Account] Cash: $100,000.00, Market Value: $0.00

[SPY] Processing...
[SPY] Regime: TRENDING (confidence: 0.75)
[SPY] Alpha Signal: 0.523 (confidence: 0.65)
[SPY] Signal below conviction threshold (0.65 < 0.70)  # Example - no trade

[AAPL] Processing...
[AAPL] Regime: MEAN_REVERTING (confidence: 0.80)
[AAPL] Alpha Signal: -0.412 (confidence: 0.55)

[AAPL] ENTRY SIGNAL:
  Direction: SHORT
  Price: $195.50
  Shares: 50
  Notional: $9,775.00
  Stop Loss: $198.45 (1.51%)
  Profit Target: $186.65 (-4.53%)
  Transaction Cost: $4.89

[Moomoo] Placing LIMIT order:
  Symbol: US.AAPL
  Side: SELL
  Shares: 50
  Price: $195.40 (original: $195.50)
  Order placed successfully: MO_20251209_143000_001

[AAPL] Position opened successfully

================================================================================
Portfolio Value: $100,000.00 | Positions: 1
================================================================================
```

## Step 7: Observe First Trade

Wait for a position to close (either stop loss, profit target, or time stop):

```
[AAPL] CLOSING POSITION:
  Reason: profit_target
  Entry: $195.50
  Exit: $186.65
  PnL: $442.50 (2.26%)
  Transaction Cost: $9.33
  MAE: -0.45%, MFE: 4.76%

[Moomoo] Placing LIMIT order:
  Symbol: US.AAPL
  Side: BUY
  Shares: 50
  Price: $186.74 (original: $186.65)
  Order placed successfully: MO_20251209_150000_001

[AAPL] Position closed successfully
```

## Step 8: Graceful Shutdown

Press **Ctrl+C** to stop the strategy:

```
^C

Shutdown signal received...

[AAPL] CLOSING POSITION:
  Reason: shutdown
  Entry: $195.50
  Exit: $187.25
  ...

[Moomoo] Disconnected

FINAL PERFORMANCE SUMMARY
================================================================================
Total Trades: 5
Win Rate: 60.00%
Total PnL: $1,250.50
Sharpe Ratio: 0.85
Max Drawdown: 3.25%
Final Portfolio Value: $101,250.50
================================================================================

Shutdown complete
```

## Common Issues

### Issue: "No data available" for symbols
**Solution**: Wait 1-2 minutes for yfinance to fetch historical data

### Issue: "Outside market hours"
**Solution**: Strategy only trades during US market hours (9:30 AM - 4:00 PM ET)
- For testing outside market hours, comment out the `is_market_hours()` check

### Issue: "Insufficient capital"
**Solution**: Lower `max_portfolio_heat` or increase `initial_capital`

### Issue: No trades generated after 1 hour
**Solutions**:
1. Lower `min_conviction` threshold (default 0.4 → try 0.3)
2. Check alpha signals in Prometheus - they may be too weak
3. Verify regime detection is working (check console logs)

## Parameter Tuning

Edit the `config` dictionary in `live_multi_factor_strategy.py`:

```python
config = {
    # To get more trades:
    'min_conviction': 0.3,              # Lower from 0.4
    'kelly_fraction': 0.35,             # Increase from 0.25

    # To reduce risk:
    'max_portfolio_heat': 0.01,         # Lower from 0.02
    'atr_multiplier': 1.5,              # Tighten from 2.0

    # To hold positions longer:
    'time_stop_bars': 100,              # Increase from 50

    # To update more frequently:
    'update_interval_seconds': 30,      # Lower from 60
}
```

## Performance Benchmarks

After running for 1 day, check:

```bash
psql postgresql://localhost:5435/nautilus -c "
  SELECT
    COUNT(*) as total_trades,
    SUM(CASE WHEN pnl > 0 THEN 1 ELSE 0 END)::FLOAT / COUNT(*) as win_rate,
    SUM(pnl) as total_pnl,
    AVG(pnl) as avg_pnl,
    MAX(pnl) as best_trade,
    MIN(pnl) as worst_trade
  FROM multifactor_trades;
"
```

Expected after 1 day (assuming 5-10 trades):
```
total_trades | win_rate | total_pnl | avg_pnl | best_trade | worst_trade
-------------+----------+-----------+---------+------------+-------------
     8       |  0.375   |  -125.50  | -15.69  |   450.00   |  -275.00
```

**Interpretation**:
- Win rate 37.5% is acceptable (target: >35%)
- Small daily loss is normal (transaction costs dominate with few trades)
- After 1 week, expect positive cumulative PnL with Sharpe > 0.3

## Next Steps

1. **Run for 1 week** - Let the strategy accumulate 20-30 trades
2. **Analyze performance** - Use PostgreSQL queries and Grafana
3. **Tune parameters** - Based on actual signal quality and win rate
4. **Expand universe** - Add more symbols if Sharpe ratio > 0.8

## Support

For issues, check:
1. Console logs for errors
2. Prometheus metrics for stale data
3. PostgreSQL for trade history
4. Grafana for visualization

**File Location**: `/home/ajk/Nautilus/nautilus_trader/scripts/live_multi_factor_strategy.py`
**Full Documentation**: `/home/ajk/Nautilus/nautilus_trader/scripts/MULTI_FACTOR_DEPLOYMENT_PLAN.md`
