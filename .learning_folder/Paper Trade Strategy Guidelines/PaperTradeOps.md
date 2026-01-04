⛬  Perfect! Now let me give you a comprehensive answer:

   📊 **CURRENT DATA STATUS**

   **What You Have:**
   •  ✅ Live Trading Data: 1 active session (running 16 minutes)
   •  ✅ Some Backtest Data: 3 backtest runs with 17 metrics records
   •  ❌ No bars received yet: The strategy is subscribed but waiting for bars

   **Which Dashboards Have Data:**

   ✅ Working Now:
   •  Live Trading Monitor - Shows your active session
   •  Infrastructure Overview - System health

   ⚠️ Limited Data:
   •  AI Strategy Performance - Has some backtest data (3 runs) but no live comparison yet
   •  AI Trade Analytics - Will populate after first trades

   ❌ Waiting for Activity:
   •  All other dashboards need trading activity (bars, signals, trades) to show meaningful data

   ──────────────────────────────────────────

   ⏱️ **HOW LONG TO RUN PAPER TRADING**

   **Minimum Recommended Durations:**

   **1. Initial Test (1-2 hours)** ← **Your Current Phase**

   Purpose: Verify system works and first signal generation
   •  Duration: 1-2 hours
   •  Expected:
     •  50-60 bars received
     •  Feature matrix built
     •  Possibly 1-2 trading signals
     •  First trade executed (if market conditions align)
   •  Why: Validates the complete pipeline works

   **2. Short Validation (4-8 hours)**

   Purpose: See multiple trades and basic strategy behavior
   •  Duration: 4-8 hours (or overnight)
   •  Expected:
     •  5-15 trades
     •  Basic win rate calculation
     •  P&L trend visible
     •  Multiple market conditions tested
   •  Why: Enough data to spot obvious issues

   **3. Medium Test (24-48 hours)**

   Purpose: Meaningful performance metrics
   •  Duration: 1-2 days continuous
   •  Expected:
     •  20-50+ trades
     •  Reliable win rate (>50%)
     •  Sharpe ratio calculable
     •  Multiple market regime changes
   •  Why: Industry standard for paper trading validation

   **4. Extended Validation (1-2 weeks)**

   Purpose: Pre-production confidence
   •  Duration: 1-2 weeks
   •  Expected:
     •  100+ trades
     •  Performance within ±5% of backtest
     •  All risk controls tested
     •  Edge cases encountered
   •  Why: Required before considering live trading with real money

   ──────────────────────────────────────────

   🎯 **RECOMMENDATION FOR YOU**

   **Option 1: Quick Test (Recommended for now)**

   Run for: 2-4 hours

   bash
     # Let it run, then check status:
     bash scripts/monitor_live_trading.sh

     # When ready to stop:
     bash scripts/stop_paper_trading.sh

   Check after 2 hours if:
   •  ✅ Bars are being received
   •  ✅ First trade executed
   •  ✅ No errors in logs
   •  ✅ Grafana shows live updates

   **Option 2: Overnight Run**

   Run for: 8-12 hours (overnight)

   bash
     # Start in evening
     # Let run overnight
     # Review results in morning

   Better because:
   •  Multiple trades likely
   •  Tests strategy in different market conditions
   •  More meaningful metrics

   **Option 3: Weekend Long Run**

   Run for: 48 hours (Friday evening → Sunday evening)

   bash
     # Crypto markets trade 24/7
     # Full weekend of data
     # Comprehensive validation

   ──────────────────────────────────────────

   🛑 **HOW TO STOP PAPER TRADING**

   **Method 1: Graceful Shutdown (Recommended)** ✅

   bash
     cd /home/ajk/Nautilus/nautilus_trader
     bash scripts/stop_paper_trading.sh

   What it does:
   1. Shows session summary
   2. Displays trading statistics
   3. Sends graceful shutdown signal (SIGTERM)
   4. Waits for clean exit (30s timeout)
   5. Updates database (marks session STOPPED)
   6. Preserves all data

   **Method 2: Manual Stop**

   bash
     # Send interrupt signal (same as Ctrl+C)
     pkill -SIGTERM -f start_paper_trading_sandbox.py

     # Wait a moment, then verify stopped
     ps aux | grep start_paper_trading_sandbox | grep -v grep

     # If still running after 30 seconds, force:
     pkill -9 -f start_paper_trading_sandbox.py

   **Method 3: If Process is Hung**

   bash
     # Find exact PID
     ps aux | grep start_paper_trading_sandbox

     # Force kill
     kill -9 <PID>

     # Manually update database
     docker exec nautilus_postgres psql -U nautilus -d nautilus_trader -c \
       "UPDATE ai_extensions.live_sessions SET status='STOPPED', stopped_at=NOW() WHERE status='RUNNING';"

   ──────────────────────────────────────────

   📋 **AFTER STOPPING - WHAT TO DO**

   **1. Review the Data**

   bash
     # Check session summary
     docker exec nautilus_postgres psql -U nautilus -d nautilus_trader -c "
       SELECT 
         trader_id,
         strategy_id,
         started_at,
         stopped_at,
         EXTRACT(EPOCH FROM (stopped_at - started_at))/3600 as runtime_hours
       FROM ai_extensions.live_sessions 
       WHERE trader_id = 'SANDBOX-TRADER-001'
       ORDER BY started_at DESC LIMIT 1;
     "

     # Check total trades
     docker exec nautilus_postgres psql -U nautilus -d nautilus_trader -c "
       SELECT COUNT(*) as total_trades,
              SUM(CASE WHEN pnl > 0 THEN 1 ELSE 0 END) as wins,
              SUM(CASE WHEN pnl < 0 THEN 1 ELSE 0 END) as losses,
              AVG(pnl) as avg_pnl,
              SUM(pnl) as total_pnl
       FROM ai_extensions.live_trades;
     "

   **2. View in Grafana**
   •  Live Trading Monitor will show historical data
   •  You can change time range to view the full session
   •  Metrics persist in Prometheus for 15 days

   **3. Compare to Backtest**

   bash
     # See if you need to load backtest data into database
     docker exec nautilus_postgres psql -U nautilus -d nautilus_trader -c "
       SELECT 
         br.strategy_id,
         br.completed_at,
         bm.win_rate,
         bm.total_trades
       FROM ai_extensions.backtest_runs br
       JOIN ai_extensions.backtest_metrics bm ON br.id = bm.backtest_run_id
       ORDER BY br.completed_at DESC;
     "

   **4. Restart for Longer Run**

   bash
     # If you want to run longer
     cd /home/ajk/Nautilus/nautilus_trader
     source nautilus_env/bin/activate
     nohup python scripts/start_paper_trading_sandbox.py > /tmp/paper_trading.out 2>&1 &

   ──────────────────────────────────────────

   ⚠️ **IMPORTANT NOTES**

   **Data Persistence**
   •  ✅ Database: All session data saved permanently
   •  ✅ Logs: Saved in logs/ directory
   •  ⚠️ Prometheus: Metrics kept for 15 days, then auto-deleted
   •  ⚠️ In-Memory: Strategy state is lost on restart

   **When to Stop Early**

   Stop immediately if you see:
   •  ❌ High error rate in logs
   •  ❌ All orders getting rejected
   •  ❌ System errors or crashes
   •  ❌ Unusual behavior (e.g., excessive trading)

   **Safe to Stop Anytime**
   •  ✅ Between trades (no open positions)
   •  ✅ During market data reception
   •  ✅ After seeing errors
   •  ✅ Anytime using graceful shutdown script

   ──────────────────────────────────────────

   🎯 **MY RECOMMENDATION FOR YOU**

   Right now (16 minutes in):
   1. Let it run for at least 2 more hours to see first trades
   2. Monitor with: bash scripts/monitor_live_trading.sh (every 30 minutes)
   3. Check logs for bars:
      ```bash
      tail -f logs/SANDBOX-TRADER-001_*.log | grep -E "Bar|Order|Signal"
      ```
   4. After 2-4 hours, use bash scripts/stop_paper_trading.sh to gracefully shutdown
   5. Review results in Grafana and database
   6. Decide: Run longer (overnight/weekend) or adjust strategy

   Your goal: See at least 3-5 trades to validate the pipeline works correctly before running a longer session.

   ──────────────────────────────────────────

   Files Created:
   •  ✅ scripts/stop_paper_trading.sh - Graceful shutdown script
   •  ✅ scripts/monitor_live_trading.sh - Live monitoring dashboard

   Next command to run (after 2+ hours):

   bash
     bash scripts/stop_paper_trading.sh
