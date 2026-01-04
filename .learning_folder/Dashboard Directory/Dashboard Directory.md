   📊 **GRAFANA DASHBOARDS DIRECTORY**

   Location: /home/ajk/Nautilus/nautilus_trader/infrastructure/monitoring/grafana/dashboards/

   **All 10 Dashboards (✅ All Loaded in Grafana)**

   | Dashboard | File | Size | Status | Purpose |
   |-----------|------|------|--------|---------|
   | Live Trading Monitor | live-trading-monitor.json | 16K | ✅ Active | Real-time paper trading - Your primary dashboard |
   | AI Strategy Performance | ai-strategy-performance.json | 20K | ✅ Ready | Backtest vs live comparison |
   | AI Trade Analytics | ai-trade-analytics.json | 6.3K | ✅ Ready | Detailed trade analysis |
   | AI Risk Monitoring | ai-risk-monitoring.json | 2.6K | ✅ Ready | Risk metrics & alerts |
   | AI Pattern Detection | ai-pattern-detection.json | 2.8K | ✅ Ready | Market pattern recognition |
   | AI Regime Analysis | ai-regime-analysis.json | 2.7K | ✅ Ready | Market regime detection |
   | AI ML Optimisation | ai-ml-optimisation.json | 2.6K | ✅ Ready | Model performance |
   | AI Sentiment Tracking | ai-sentiment-tracking.json | 2.8K | ✅ Ready | Sentiment analysis |
   | AI Executive Overview | ai-executive-overview.json | 2.5K | ✅ Ready | High-level summary |
   | Infrastructure Overview | infrastructure-overview.json | 1.7K | ✅ Ready | System health |

   ──────────────────────────────────────────

   🎯 **QUICK ACCESS LINKS**

   **Currently Monitoring Your Paper Trading:**

   1. 🔥 Live Trading Monitor (Your main dashboard)

     http://localhost:3000/d/live-trading-monitor

   Shows: Active session, equity, P&L, positions, orders, alerts

   2. 📊 AI Strategy Performance

     http://localhost:3000/d/fb079b01-cfaa-4d38-ae18-84bbba3356a5/ai-strategy-performance

   Shows: Backtest results, live performance comparison, win rates

   3. 📈 AI Trade Analytics

     http://localhost:3000/d/b9cfb842-d4a2-43e2-8dce-c40c2b0d2617/ai-trade-analytics

   Shows: Trade history, P&L distribution, holding times

   ──────────────────────────────────────────

   **Risk & Analysis:**

   4. ⚠️ AI Risk Monitoring

     http://localhost:3000/d/5956d8ed-c546-4a1c-9f92-b52734f395ad/ai-risk-monitoring

   Shows: Drawdown, position limits, circuit breakers

   5. 🧠 AI Pattern Detection

     http://localhost:3000/d/c62709b4-94fd-4b57-a9cb-fa49514bdc74/ai-pattern-detection

   Shows: Market patterns detected by strategy

   6. 🌊 AI Regime Analysis

     http://localhost:3000/d/eae78e27-b46d-4b3c-8227-4c2a35805760/ai-regime-analysis

   Shows: Bull/bear/sideways market classification

   ──────────────────────────────────────────

   **ML & Advanced:**

   7. 🤖 AI ML Optimisation

     http://localhost:3000/d/0b8ef4d6-5869-400f-9d05-bc15070cb713/ai-ml-optimisation

   Shows: XGBoost model metrics, feature importance

   8. 💭 AI Sentiment Tracking

     http://localhost:3000/d/2120b151-b166-46c2-9f4f-d304a46150ee/ai-sentiment-tracking

   Shows: Sentiment indicators (if integrated)

   ──────────────────────────────────────────

   **Overview:**

   9. 💡 AI Executive Overview

     http://localhost:3000/d/2e7f80be-c148-4580-b847-e1ce4c9f3644/ai-executive-overview

   Shows: Top-level KPIs across all strategies

   10. 🔧 Infrastructure Overview

     http://localhost:3000/d/07562b36-a9c3-4845-b0ee-47a745e7c5c4/infrastructure-overview

   Shows: PostgreSQL, Redis, Prometheus status

   ──────────────────────────────────────────

   🛠️ **DASHBOARD MANAGEMENT**

   **View Dashboard in Browser**

   bash
     # Open specific dashboard
     xdg-open "http://localhost:3000/d/live-trading-monitor" 2>/dev/null || \
     echo "Open manually: http://localhost:3000/d/live-trading-monitor"

   **Check Dashboard Contents**

   bash
     # See what panels are in a dashboard
     cd /home/ajk/Nautilus/nautilus_trader
     jq -r '.panels[] | "\(.id): \(.title) (\(.type))"' \
       infrastructure/monitoring/grafana/dashboards/live-trading-monitor.json

   **Import/Update Dashboards**

   bash
     # Reimport a dashboard (if you edited it)
     GRAFANA_PASS=$(grep GRAFANA_PASSWORD infrastructure/.env.local | cut -d'=' -f2)
     curl -X POST http://admin:${GRAFANA_PASS}@localhost:3000/api/dashboards/db \
       -H "Content-Type: application/json" \
       -d @infrastructure/monitoring/grafana/dashboards/live-trading-monitor.json

   **Export Dashboard from Grafana**

   bash
     # Export current dashboard state
     GRAFANA_PASS=$(grep GRAFANA_PASSWORD infrastructure/.env.local | cut -d'=' -f2)
     curl -s http://admin:${GRAFANA_PASS}@localhost:3000/api/dashboards/uid/live-trading-monitor | \
       jq '.dashboard' > infrastructure/monitoring/grafana/dashboards/live-trading-monitor-backup.json

   ──────────────────────────────────────────

   📈 **WHICH DASHBOARD TO USE WHEN**

   **During Paper Trading** (Now):
   •  Primary: Live Trading Monitor
   •  Secondary: AI Strategy Performance (compare to backtests)
   •  Watch: AI Risk Monitoring (ensure no issues)

   **After First Trades**:
   •  AI Trade Analytics - Analyze trade quality
   •  AI Pattern Detection - See what patterns triggered trades
   •  AI Regime Analysis - Confirm market conditions

   **Daily Review**:
   •  AI Executive Overview - Quick summary
   •  AI Strategy Performance - Performance trends
   •  Infrastructure Overview - System health

   **When Debugging**:
   •  AI Risk Monitoring - Check if limits hit
   •  AI ML Optimisation - Model performance issues
   •  Infrastructure Overview - System problems

   ──────────────────────────────────────────

   💡 **QUICK TIP**

   Open Multiple Dashboards in Tabs:

   bash
     # Linux with default browser
     xdg-open "http://localhost:3000/d/live-trading-monitor" &
     xdg-open "http://localhost:3000/d/fb079b01-cfaa-4d38-ae18-84bbba3356a5/ai-strategy-performance" &
     xdg-open "http://localhost:3000/d/5956d8ed-c546-4a1c-9f92-b52734f395ad/ai-risk-monitoring" &

   Or create a bookmark folder with all dashboard links for quick access!

   ──────────────────────────────────────────

   All 10 dashboards are ready and operational. The Live Trading Monitor is actively displaying your running paper trading session right now! 🎯