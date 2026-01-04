# AI-Adaptive Dashboard Enhancement - Implementation Plan

**Created:** October 7, 2025  
**Based on:** `research/analysis.md`  
**Timeline:** 2-3 days  
**Complexity:** Medium  
**Prerequisites:** PostgreSQL + Redis + Prometheus + Grafana (✅ Deployed)

---

## Executive Summary

This plan provides a **step-by-step roadmap** for implementing comprehensive AI-adaptive monitoring and visualization for Nautilus Trader. The implementation is broken into 7 phases with clear deliverables, dependencies, and validation steps.

**Architecture Overview:**
```
AI-Adaptive Strategy → Metrics Export → Storage Layer → Visualization
                              ↓              ↓              ↓
                       Prometheus      PostgreSQL      Grafana
                                           Redis
```

**Key Deliverables:**
1. Enhanced PostgreSQL schema with backtest tables
2. Prometheus metrics exporter (Python)
3. Redis cache manager for real-time state
4. 8 Grafana dashboards with 100+ panels
5. 15+ alert rules with notifications
6. Integration with existing backtest runner
7. Testing suite and operational runbook

---

## Phase 1: Database Schema Enhancement

**Duration:** 2-4 hours  
**Priority:** High (Foundation)  
**Dependencies:** PostgreSQL container running

### 1.1 Objectives

- Extend existing AI-extensions schema with backtest-specific tables
- Create views for dashboard queries
- Add indexes for performance
- Implement data retention policies

### 1.2 Tasks

#### Task 1.1: Create Enhanced Schema

**File:** `infrastructure/postgres/03-backtest-schema.sql`

**Actions:**
1. Create `backtests` table for main backtest results
2. Create `trades` table for individual trade records
3. Create `ml_parameter_snapshots` table for optimization tracking
4. Create `circuit_breaker_events` table for risk events
5. Add foreign key relationships
6. Create indexes on frequently queried columns

**Deliverable:** SQL file with CREATE TABLE statements

**Validation:**
```bash
# Apply schema
docker exec nautilus_postgres psql -U nautilus -d nautilus_trader < infrastructure/postgres/03-backtest-schema.sql

# Verify tables
docker exec nautilus_postgres psql -U nautilus -d nautilus_trader -c "\dt"

# Should show:
# - backtests
# - trades
# - ml_parameter_snapshots
# - circuit_breaker_events
# Plus existing tables from 02-ai-extensions.sql
```

#### Task 1.2: Create Dashboard Views

**File:** `infrastructure/postgres/04-dashboard-views.sql`

**Actions:**
1. Create `v_backtest_performance` view for main dashboard
2. Create `v_strategy_comparison` view for parameter optimization
3. Create `v_regime_performance` view for regime analysis
4. Create `v_recent_trades` view for trade monitoring
5. Create `v_ml_optimization_history` view for ML tracking

**Deliverable:** SQL file with CREATE VIEW statements

**Validation:**
```bash
# Apply views
docker exec nautilus_postgres psql -U nautilus -d nautilus_trader < infrastructure/postgres/04-dashboard-views.sql

# Test view
docker exec nautilus_postgres psql -U nautilus -d nautilus_trader -c "SELECT * FROM v_backtest_performance LIMIT 5;"
```

#### Task 1.3: Create Database Connection Pool

**File:** `ajk_strategies/database/connection_pool.py`

**Actions:**
1. Create PostgreSQL connection pool manager
2. Implement connection health checks
3. Add retry logic for transient failures
4. Create context manager for transactions

**Deliverable:** Python module for database connections

**Validation:**
```python
from database.connection_pool import DatabasePool

pool = DatabasePool()
with pool.get_connection() as conn:
    cursor = conn.cursor()
    cursor.execute("SELECT version();")
    print(cursor.fetchone())
```

### 1.3 Success Criteria

- [ ] All schema tables created without errors
- [ ] All views return data (or empty results)
- [ ] Indexes created and functional
- [ ] Connection pool works reliably
- [ ] No foreign key constraint violations

### 1.4 Time Estimate

- Schema creation: 1 hour
- View creation: 1 hour
- Connection pool: 1-2 hours
- Testing: 30 minutes

---

## Phase 2: Prometheus Metrics Exporter

**Duration:** 4-8 hours  
**Priority:** High (Core Functionality)  
**Dependencies:** Phase 1 complete

### 2.1 Objectives

- Create Prometheus metrics definitions
- Implement metrics collection from strategy
- Build HTTP server for `/metrics` endpoint
- Integrate with existing backtest runner

### 2.2 Tasks

#### Task 2.1: Define Prometheus Metrics

**File:** `ajk_strategies/monitoring/metrics_definitions.py`

**Actions:**
1. Define 40+ metrics (Counters, Gauges, Histograms)
2. Organize by category (performance, ML, risk, regime, sentiment)
3. Add proper labels for multi-dimensional data
4. Document each metric's purpose

**Deliverable:** Python module with all metric definitions

**Example:**
```python
from prometheus_client import Counter, Gauge, Histogram

# Performance metrics
trades_total = Counter(
    'nautilus_ai_adaptive_trades_total',
    'Total trades executed',
    ['instrument', 'side', 'regime']
)

current_pnl = Gauge(
    'nautilus_ai_adaptive_pnl_dollars',
    'Current P&L in dollars',
    ['instrument', 'strategy_id']
)

trade_duration = Histogram(
    'nautilus_ai_adaptive_trade_duration_seconds',
    'Trade hold duration distribution',
    ['instrument'],
    buckets=[60, 300, 900, 1800, 3600, 7200, 14400]
)
```

#### Task 2.2: Build Metrics Collector

**File:** `ajk_strategies/monitoring/metrics_collector.py`

**Actions:**
1. Create collector class that queries PostgreSQL/Redis
2. Implement periodic data aggregation (every 15 seconds)
3. Update Prometheus gauges with current values
4. Handle database connection failures gracefully

**Deliverable:** Background metrics collection service

**Example:**
```python
import time
from database.connection_pool import DatabasePool
from monitoring.metrics_definitions import current_pnl, win_rate

class MetricsCollector:
    def __init__(self, update_interval=15):
        self.db_pool = DatabasePool()
        self.interval = update_interval
        self.running = False
    
    def collect_from_database(self):
        """Query PostgreSQL for current metrics"""
        with self.db_pool.get_connection() as conn:
            cursor = conn.cursor()
            
            # Get latest backtest performance
            cursor.execute("""
                SELECT 
                    instrument,
                    run_id,
                    total_pnl,
                    win_rate
                FROM backtests
                WHERE created_at > NOW() - INTERVAL '1 day'
                ORDER BY created_at DESC
                LIMIT 10
            """)
            
            for row in cursor.fetchall():
                current_pnl.labels(
                    instrument=row['instrument'],
                    strategy_id=row['run_id']
                ).set(float(row['total_pnl']))
                
                win_rate.labels(
                    instrument=row['instrument'],
                    lookback_period='1d'
                ).set(float(row['win_rate']))
    
    def run(self):
        """Start collection loop"""
        self.running = True
        while self.running:
            try:
                self.collect_from_database()
                time.sleep(self.interval)
            except Exception as e:
                print(f"Collection error: {e}")
                time.sleep(5)  # Backoff on error
```

#### Task 2.3: Create Metrics HTTP Server

**File:** `ajk_strategies/monitoring/metrics_server.py`

**Actions:**
1. Create HTTP server on port 8000
2. Expose `/metrics` endpoint for Prometheus scraping
3. Add health check endpoint `/health`
4. Implement graceful shutdown

**Deliverable:** Standalone metrics server script

**Example:**
```python
from prometheus_client import start_http_server
from monitoring.metrics_collector import MetricsCollector
import signal
import sys

def main():
    # Start HTTP server
    print("Starting metrics server on port 8000...")
    start_http_server(8000)
    
    # Start metrics collector
    collector = MetricsCollector(update_interval=15)
    
    # Handle shutdown gracefully
    def signal_handler(sig, frame):
        print("\nShutting down metrics server...")
        collector.running = False
        sys.exit(0)
    
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    print("Metrics server running. Press Ctrl+C to stop.")
    print("Metrics endpoint: http://localhost:8000/metrics")
    
    # Run collector
    collector.run()

if __name__ == '__main__':
    main()
```

**Validation:**
```bash
# Start server
python ajk_strategies/monitoring/metrics_server.py &

# Check metrics endpoint
curl http://localhost:8000/metrics

# Should see output like:
# nautilus_ai_adaptive_trades_total{instrument="BTCUSDT",side="BUY",regime="TRENDING_UP"} 145.0
# nautilus_ai_adaptive_pnl_dollars{instrument="BTCUSDT",strategy_id="20251007_01"} 2450.50
```

#### Task 2.4: Integrate with Backtest Runner

**File:** `ajk_strategies/run_backtest_with_real_data.py` (modify)

**Actions:**
1. Import metrics from `metrics_definitions.py`
2. Update metrics on key events (trade, optimization, regime change)
3. Increment counters, set gauges, observe histograms
4. Ensure metrics don't slow down backtesting (< 5ms overhead)

**Deliverable:** Enhanced backtest runner with metrics export

**Example integration:**
```python
# Add imports at top
from monitoring.metrics_definitions import (
    trades_total,
    current_pnl,
    trade_duration,
    optimizations_total,
    regime_changes_total
)

# In strategy on_order_filled:
def on_order_filled(self, event):
    # Existing code...
    
    # Export metric
    trades_total.labels(
        instrument=str(self.instrument_id),
        side=event.order_side.name,
        regime=self.current_regime.value
    ).inc()
    
    # Update P&L gauge
    current_pnl.labels(
        instrument=str(self.instrument_id),
        strategy_id=self.run_id
    ).set(float(self.portfolio.unrealized_pnl))

# In strategy on_ml_optimization_complete:
def on_ml_optimization_complete(self):
    optimizations_total.labels(
        instrument=str(self.instrument_id),
        trigger_type='scheduled'
    ).inc()
```

### 2.3 Success Criteria

- [ ] All metrics defined and documented
- [ ] Metrics collector runs without errors
- [ ] HTTP server serves `/metrics` endpoint
- [ ] Prometheus can scrape metrics successfully
- [ ] Backtest integration works with < 5% overhead

### 2.4 Time Estimate

- Metrics definitions: 2 hours
- Metrics collector: 2-3 hours
- HTTP server: 1 hour
- Backtest integration: 2-3 hours

---

## Phase 3: Redis Cache Manager

**Duration:** 2-4 hours  
**Priority:** Medium  
**Dependencies:** Redis container running

### 3.1 Objectives

- Implement Redis cache for real-time strategy state
- Create ML model checkpoint storage
- Build regime detection cache
- Add circuit breaker state management

### 3.2 Tasks

#### Task 3.1: Create Redis Manager

**File:** `ajk_strategies/cache/redis_manager.py`

**Actions:**
1. Create `StrategyCache` class for state management
2. Implement key-value storage patterns
3. Add TTL (time-to-live) management
4. Create helper methods for common operations

**Deliverable:** Redis cache manager module

**Example:**
```python
import redis
import json
import pickle
from typing import Any, Optional
import os

class StrategyCache:
    """Redis cache for AI-adaptive strategy"""
    
    def __init__(self):
        self.client = redis.Redis(
            host=os.getenv('REDIS_HOST', 'localhost'),
            port=int(os.getenv('REDIS_PORT', 6379)),
            password=os.getenv('REDIS_PASSWORD', ''),
            db=0,
            decode_responses=False
        )
        self.default_ttl = 3600  # 1 hour
    
    # Strategy State
    def save_strategy_state(self, strategy_id: str, state: dict, ttl: Optional[int] = None):
        """Save strategy state with TTL"""
        key = f"strategy:{strategy_id}:state"
        ttl = ttl or self.default_ttl
        self.client.setex(key, ttl, json.dumps(state))
    
    def get_strategy_state(self, strategy_id: str) -> Optional[dict]:
        """Get strategy state"""
        key = f"strategy:{strategy_id}:state"
        data = self.client.get(key)
        return json.loads(data) if data else None
    
    # ML Models
    def save_ml_model(self, strategy_id: str, model: Any, version: str = "latest"):
        """Save ML model (pickled, no TTL)"""
        key = f"ml_model:{strategy_id}:{version}"
        self.client.set(key, pickle.dumps(model))
    
    def load_ml_model(self, strategy_id: str, version: str = "latest") -> Optional[Any]:
        """Load ML model"""
        key = f"ml_model:{strategy_id}:{version}"
        data = self.client.get(key)
        return pickle.loads(data) if data else None
    
    # Regime Detection
    def cache_regime(self, instrument: str, regime_data: dict, ttl: int = 300):
        """Cache current market regime (5 min TTL)"""
        key = f"regime:{instrument}:current"
        self.client.setex(key, ttl, json.dumps(regime_data))
    
    def get_regime(self, instrument: str) -> Optional[dict]:
        """Get cached regime"""
        key = f"regime:{instrument}:current"
        data = self.client.get(key)
        return json.loads(data) if data else None
    
    # Circuit Breaker
    def set_circuit_breaker(self, instrument: str, breaker_type: str, active: bool, cooldown_seconds: int = 300):
        """Set circuit breaker state"""
        key = f"circuit_breaker:{instrument}:{breaker_type}"
        state = {
            'active': active,
            'triggered_at': int(time.time()) if active else None,
            'cooldown_until': int(time.time()) + cooldown_seconds if active else None
        }
        self.client.setex(key, cooldown_seconds if active else 60, json.dumps(state))
    
    def is_circuit_breaker_active(self, instrument: str, breaker_type: str) -> bool:
        """Check if circuit breaker is active"""
        key = f"circuit_breaker:{instrument}:{breaker_type}"
        data = self.client.get(key)
        if not data:
            return False
        state = json.loads(data)
        return state.get('active', False)
    
    # Health Check
    def ping(self) -> bool:
        """Check Redis connection"""
        try:
            return self.client.ping()
        except:
            return False
```

#### Task 3.2: Integrate with Strategy

**File:** `ajk_strategies/ai_adaptive_strategy.py` (modify)

**Actions:**
1. Add Redis cache instance to strategy
2. Cache strategy state on each bar
3. Save ML model checkpoints after optimization
4. Cache regime detection results
5. Use cache for circuit breaker state

**Deliverable:** Enhanced strategy with Redis caching

### 3.3 Success Criteria

- [ ] Redis manager connects successfully
- [ ] Strategy state persists to Redis
- [ ] ML models can be saved and loaded
- [ ] Regime cache updates correctly
- [ ] Circuit breaker state is reliable

### 3.4 Time Estimate

- Redis manager: 2 hours
- Strategy integration: 2 hours

---

## Phase 4: Prometheus Configuration

**Duration:** 1-2 hours  
**Priority:** High  
**Dependencies:** Phase 2 complete (metrics server running)

### 4.1 Objectives

- Configure Prometheus to scrape metrics exporter
- Set up recording rules for aggregations
- Configure alert rules
- Test scraping and data retention

### 4.2 Tasks

#### Task 4.1: Update Prometheus Config

**File:** `infrastructure/monitoring/prometheus/prometheus.yml` (update)

**Actions:**
1. Add scrape config for metrics exporter
2. Set scrape interval to 15 seconds
3. Configure service discovery (if needed)
4. Set retention period to 30 days

**Deliverable:** Updated Prometheus configuration

**Example:**
```yaml
global:
  scrape_interval: 15s
  evaluation_interval: 15s
  external_labels:
    cluster: 'nautilus-trader'
    environment: 'development'

scrape_configs:
  - job_name: 'prometheus'
    static_configs:
      - targets: ['prometheus:9090']
  
  - job_name: 'postgres'
    static_configs:
      - targets: ['postgres-exporter:9187']
  
  - job_name: 'redis'
    static_configs:
      - targets: ['redis-exporter:9121']
  
  # NEW: AI-Adaptive Strategy Metrics
  - job_name: 'nautilus-ai-adaptive'
    scrape_interval: 15s
    static_configs:
      - targets: ['host.docker.internal:8000']  # Metrics server
        labels:
          service: 'ai-adaptive-strategy'
          version: '1.0'
```

**Validation:**
```bash
# Reload Prometheus
docker-compose restart prometheus

# Check targets
curl http://localhost:9090/api/v1/targets

# Should see nautilus-ai-adaptive target with state="up"
```

#### Task 4.2: Create Alert Rules

**File:** `infrastructure/monitoring/prometheus/alerts/ai_adaptive_alerts.yml`

**Actions:**
1. Create alert groups (critical_risk, performance, ml, system_health)
2. Define 15+ alert rules with thresholds
3. Add annotations for context
4. Set appropriate `for` durations

**Deliverable:** Alert rules YAML file

**Example:**
```yaml
groups:
  - name: critical_risk
    interval: 30s
    rules:
      - alert: MaxDrawdownExceeded
        expr: nautilus_ai_adaptive_drawdown_percent > 10
        for: 1m
        labels:
          severity: critical
          category: risk
        annotations:
          summary: "Maximum drawdown exceeded on {{ $labels.instrument }}"
          description: "Current drawdown: {{ $value }}% (threshold: 10%)"
          action: "Strategy should be halted immediately"
      
      - alert: CircuitBreakerTriggered
        expr: nautilus_ai_adaptive_circuit_breaker_active == 1
        for: 0s
        labels:
          severity: critical
          category: risk
        annotations:
          summary: "Circuit breaker activated on {{ $labels.instrument }}"
          description: "Breaker type: {{ $labels.breaker_type }}"
          action: "Trading is paused. Review risk metrics."
  
  - name: performance
    interval: 5m
    rules:
      - alert: WinRateDropping
        expr: nautilus_ai_adaptive_winrate_percent < 35
        for: 15m
        labels:
          severity: warning
          category: performance
        annotations:
          summary: "Win rate below threshold on {{ $labels.instrument }}"
          description: "Current: {{ $value }}% (threshold: 35%)"
```

**Update prometheus.yml to include alerts:**
```yaml
rule_files:
  - 'alerts/ai_adaptive_alerts.yml'
```

### 4.3 Success Criteria

- [ ] Prometheus scrapes metrics exporter
- [ ] All metrics visible in Prometheus UI
- [ ] Alert rules loaded without errors
- [ ] Test alert fires correctly

### 4.4 Time Estimate

- Prometheus config: 30 minutes
- Alert rules: 1-1.5 hours

---

## Phase 5: Grafana Dashboard Creation

**Duration:** 8-12 hours  
**Priority:** High (User-Facing)  
**Dependencies:** Phase 1, 2, 4 complete

### 5.1 Objectives

- Create 8 specialized dashboards
- Configure data sources
- Build 100+ panels with queries
- Set up dashboard variables
- Configure auto-refresh

### 5.2 Tasks

#### Task 5.1: Configure Grafana Data Sources

**File:** `infrastructure/monitoring/grafana/provisioning/datasources/datasources.yml`

**Actions:**
1. Add PostgreSQL data source
2. Add Prometheus data source (already exists)
3. Add Redis data source
4. Test all connections

**Deliverable:** Data source configuration

**Example:**
```yaml
apiVersion: 1

datasources:
  - name: NautilusPrometheus
    type: prometheus
    access: proxy
    url: http://prometheus:9090
    isDefault: true
    editable: false
  
  - name: NautilusPostgreSQL
    type: postgres
    access: proxy
    url: postgres:5432
    database: nautilus_trader
    user: grafana_reader
    secureJsonData:
      password: ${GRAFANA_DB_PASSWORD}
    jsonData:
      sslmode: disable
      maxOpenConns: 10
      maxIdleConns: 5
    editable: false
  
  - name: NautilusRedis
    type: redis-datasource
    access: proxy
    url: redis:6379
    jsonData:
      client: standalone
    secureJsonData:
      password: ${REDIS_PASSWORD}
    editable: false
```

**Validation:**
```bash
# Restart Grafana
docker-compose restart grafana

# Check data sources
curl -u admin:password http://localhost:3000/api/datasources
```

#### Task 5.2: Create Dashboard 1 - Executive Overview

**File:** `infrastructure/monitoring/grafana/dashboards/01-executive-overview.json`

**Panels:**
1. Total P&L (Stat)
2. Win Rate (Gauge)
3. Sharpe Ratio (Stat)
4. Current Drawdown (Gauge)
5. Active Strategies (Stat)
6. Recent Backtests (Table)
7. P&L Trend (Time Series)
8. Trade Count (Bar Chart)
9. Critical Alerts (Alert List)
10. Regime Distribution (Pie Chart)

**Time:** 2-3 hours

#### Task 5.3: Create Dashboard 2 - Strategy Performance

**File:** `infrastructure/monitoring/grafana/dashboards/02-strategy-performance.json`

**Panels:**
1. Cumulative P&L (Time Series)
2. Daily P&L (Bar Chart)
3. Win Rate Trend (Time Series)
4. Profit Factor (Gauge)
5. Sharpe Ratio Evolution (Time Series)
6. Max Drawdown History (Time Series)
7. Trade Distribution (Histogram)
8. Win/Loss Ratio (Stat)
9. Average Trade Duration (Stat)
10. Best/Worst Trades (Table)

**Time:** 2 hours

#### Task 5.4: Create Dashboard 3 - ML Optimization

**File:** `infrastructure/monitoring/grafana/dashboards/03-ml-optimization.json`

**Panels:**
1. Fast EMA Period (Time Series)
2. Slow EMA Period (Time Series)
3. Optimization Frequency (Bar Chart)
4. Loss Function (Time Series)
5. Signal Weights Heatmap (Heatmap)
6. Win Rate Before/After (Comparison)
7. Sharpe Before/After (Comparison)
8. Optimization Duration (Histogram)
9. Parameter Evolution Table (Table)
10. Convergence Status (Stat)

**Time:** 1.5 hours

#### Task 5.5: Create Dashboard 4 - Market Regime Analysis

**File:** `infrastructure/monitoring/grafana/dashboards/04-regime-analysis.json`

**Panels:**
1. Current Regime (Stat with color)
2. Regime Confidence (Gauge)
3. Regime Distribution (Pie Chart)
4. Regime Timeline (Time Series with annotations)
5. Win Rate by Regime (Bar Chart)
6. Avg PnL by Regime (Bar Chart)
7. Regime Duration (Histogram)
8. Transition Matrix (Heatmap)
9. Volatility Trend (Time Series)
10. Trend Strength (Gauge)

**Time:** 1.5 hours

#### Task 5.6: Create Dashboard 5 - Pattern Detection

**File:** `infrastructure/monitoring/grafana/dashboards/05-pattern-detection.json`

**Panels:**
1. Patterns Detected (Counter)
2. Pattern Type Distribution (Pie Chart)
3. Pattern Timeline (Time Series)
4. Success Rate by Pattern (Bar Chart)
5. Confidence Distribution (Histogram)
6. Recent Patterns (Table)
7. Pattern Duration (Box Plot)
8. Signal Generation Rate (Gauge)

**Time:** 1 hour

#### Task 5.7: Create Dashboard 6 - Risk Management

**File:** `infrastructure/monitoring/grafana/dashboards/06-risk-management.json`

**Panels:**
1. Circuit Breaker Status (Stat - Red/Green)
2. Current Drawdown (Gauge with threshold)
3. Risk Event Timeline (Time Series with annotations)
4. Drawdown History (Time Series)
5. Position Size Tracking (Time Series)
6. Consecutive Losses (Stat)
7. Daily Loss (Gauge)
8. Risk Events by Type (Bar Chart)
9. Circuit Breaker Activations (Counter)
10. Max Adverse Excursion (Histogram)

**Time:** 1.5 hours

#### Task 5.8: Create Dashboard 7 - Sentiment Analysis

**File:** `infrastructure/monitoring/grafana/dashboards/07-sentiment-analysis.json`

**Panels:**
1. Current Sentiment (Gauge -1 to +1)
2. Sentiment Trend (Time Series)
3. Mention Volume (Bar Chart)
4. Sentiment vs Price (Dual-axis Time Series)
5. Source Breakdown (Pie Chart)
6. Sentiment Shift Events (Annotations)
7. Signal Weight Impact (Stat)
8. Engagement Score (Time Series)

**Time:** 1 hour

#### Task 5.9: Create Dashboard 8 - Trade Analysis

**File:** `infrastructure/monitoring/grafana/dashboards/08-trade-analysis.json`

**Panels:**
1. Trade Heatmap (Entry/Exit times)
2. Duration Distribution (Histogram)
3. P&L Distribution (Histogram)
4. MAE vs MFE Scatter Plot
5. Recent Trades Table
6. Trade Count by Hour (Bar Chart)
7. Win Rate by Day of Week (Bar Chart)
8. Trade Size Distribution (Histogram)
9. Exit Reason Breakdown (Pie Chart)
10. Best Trade (Stat)

**Time:** 1.5 hours

### 5.3 Dashboard Best Practices

**All Dashboards Should Have:**
- [ ] Dashboard variables for filtering (instrument, date range)
- [ ] Auto-refresh (15-30 seconds for real-time, 5 minutes for historical)
- [ ] Consistent color scheme
- [ ] Descriptive panel titles
- [ ] Tooltips with helpful information
- [ ] Links to related dashboards
- [ ] Annotations for important events
- [ ] Responsive layouts (mobile-friendly)

### 5.4 Success Criteria

- [ ] All 8 dashboards load without errors
- [ ] All panels show data (or "No data" if expected)
- [ ] Queries execute in < 2 seconds
- [ ] Auto-refresh works correctly
- [ ] Dashboard variables filter correctly
- [ ] User can navigate between dashboards easily

### 5.5 Time Estimate

- Data sources setup: 30 minutes
- Dashboard 1: 2-3 hours
- Dashboards 2-8: 6-9 hours
- Testing & refinement: 1-2 hours

---

## Phase 6: Integration & Testing

**Duration:** 4-8 hours  
**Priority:** High  
**Dependencies:** All previous phases complete

### 6.1 Objectives

- Integrate all components end-to-end
- Run comprehensive testing suite
- Validate performance overhead
- Fix bugs and issues

### 6.2 Tasks

#### Task 6.1: End-to-End Integration Test

**File:** `tests/integration/test_monitoring_pipeline.py`

**Test Flow:**
```
1. Start metrics server
2. Run backtest with AI-adaptive strategy
3. Verify metrics exported to Prometheus
4. Verify data stored in PostgreSQL
5. Verify state cached in Redis
6. Verify dashboards show data in Grafana
7. Verify alerts fire correctly
```

**Deliverable:** Automated integration test

#### Task 6.2: Performance Benchmark

**Tests:**
1. Measure metrics export overhead (target: < 5ms per event)
2. Measure database write latency (target: < 50ms per batch)
3. Measure dashboard query performance (target: < 2s per query)
4. Measure Prometheus scrape duration (target: < 100ms)

**Deliverable:** Performance benchmark report

#### Task 6.3: Load Testing

**Scenarios:**
1. 10 concurrent strategies
2. 1000 trades/hour
3. 100 ML optimizations/hour
4. 50 regime changes/hour

**Deliverable:** Load test results with bottleneck analysis

#### Task 6.4: Bug Fixes

**Common Issues:**
- Database connection timeouts
- Redis memory limits
- Prometheus scrape failures
- Grafana query timeouts
- Alert rule syntax errors

**Deliverable:** All tests passing, no critical issues

### 6.3 Success Criteria

- [ ] Full backtest runs with monitoring enabled
- [ ] All metrics appear in Prometheus
- [ ] All data persists to PostgreSQL
- [ ] Redis cache updates correctly
- [ ] All dashboards show data
- [ ] Alerts fire as expected
- [ ] Performance overhead < 5%
- [ ] No memory leaks or crashes

### 6.4 Time Estimate

- Integration testing: 2-3 hours
- Performance benchmarking: 1-2 hours
- Load testing: 1 hour
- Bug fixes: 2-4 hours

---

## Phase 7: Documentation & Handoff

**Duration:** 2-4 hours  
**Priority:** Medium  
**Dependencies:** Phase 6 complete

### 7.1 Objectives

- Create operational runbook
- Document troubleshooting procedures
- Write user guide for dashboards
- Prepare handoff materials

### 7.2 Tasks

#### Task 7.1: Operational Runbook

**File:** `ai-working/dashboard enhancing/OPERATIONS.md`

**Contents:**
1. Daily operations checklist
2. How to start/stop services
3. How to check system health
4. Common troubleshooting scenarios
5. Backup and restore procedures
6. Alert response playbook

**Deliverable:** Comprehensive operations guide

#### Task 7.2: Dashboard User Guide

**File:** `ai-working/dashboard enhancing/DASHBOARD_GUIDE.md`

**Contents:**
1. Overview of each dashboard
2. How to interpret key metrics
3. How to use dashboard variables
4. How to create custom views
5. How to export data
6. Common questions and answers

**Deliverable:** Dashboard user documentation

#### Task 7.3: Developer Documentation

**File:** `ai-working/dashboard enhancing/DEVELOPER.md`

**Contents:**
1. Architecture overview
2. How to add new metrics
3. How to create new dashboards
4. How to modify alert rules
5. Code structure and organization
6. Development setup

**Deliverable:** Developer guide

### 7.3 Success Criteria

- [ ] All documentation is clear and comprehensive
- [ ] Another developer can operate the system using docs
- [ ] Troubleshooting guide covers common issues
- [ ] Handoff materials are complete

### 7.4 Time Estimate

- Operational runbook: 1-2 hours
- Dashboard guide: 1 hour
- Developer docs: 1 hour

---

## Implementation Schedule

### Day 1 (8 hours)

**Morning (4 hours):**
- Phase 1: Database Schema Enhancement (2-4 hours)
  - Create schema files
  - Apply to PostgreSQL
  - Test with sample data

**Afternoon (4 hours):**
- Phase 2: Prometheus Metrics Exporter (4 hours)
  - Define metrics
  - Build collector
  - Create HTTP server
  - Basic testing

### Day 2 (8 hours)

**Morning (4 hours):**
- Phase 2 (continued): Backtest Integration (2-3 hours)
- Phase 3: Redis Cache Manager (2-4 hours)
  - Build cache manager
  - Integrate with strategy

**Afternoon (4 hours):**
- Phase 4: Prometheus Configuration (1-2 hours)
- Phase 5: Grafana Dashboards (Start)
  - Configure data sources
  - Create Dashboard 1 & 2

### Day 3 (8 hours)

**Morning (4 hours):**
- Phase 5 (continued): Grafana Dashboards
  - Create Dashboards 3-8

**Afternoon (4 hours):**
- Phase 6: Integration & Testing
  - End-to-end tests
  - Performance benchmarks
  - Bug fixes

### Day 4 (Optional, 4 hours)

**Morning (2 hours):**
- Phase 6 (continued): Final testing and refinement

**Afternoon (2 hours):**
- Phase 7: Documentation & Handoff

---

## Risk Management

### High-Risk Items

| Risk | Impact | Probability | Mitigation |
|------|--------|-------------|------------|
| Database schema conflicts | High | Low | Review existing schema first, use ALTER TABLE ADD COLUMN IF NOT EXISTS |
| Prometheus scraping fails | High | Medium | Add health checks, implement retry logic |
| Grafana queries timeout | Medium | Medium | Optimize queries, add indexes, use views |
| Redis memory overflow | Medium | Low | Set max memory policy, use TTLs |
| Performance overhead | High | Medium | Batch operations, async processing, benchmark early |

### Contingency Plans

**If PostgreSQL performance is poor:**
- Add more indexes
- Use connection pooling
- Implement query caching in Redis
- Consider read replicas

**If Prometheus scraping is slow:**
- Reduce scrape interval
- Implement metrics batching
- Use summary metrics instead of histograms
- Add more labels carefully (cardinality)

**If Grafana dashboards are slow:**
- Use PostgreSQL views for complex queries
- Add query caching
- Reduce panel refresh rates
- Implement data pre-aggregation

---

## Success Metrics

### Functional Metrics

- [ ] 100% of backtest results stored in PostgreSQL
- [ ] 100% of metrics exported to Prometheus
- [ ] 100% of dashboards load successfully
- [ ] 100% of alerts configured and tested
- [ ] 0 critical bugs in production

### Performance Metrics

- [ ] Metrics export overhead: < 5% of backtest runtime
- [ ] Database write latency: < 50ms per batch
- [ ] Prometheus scrape duration: < 100ms
- [ ] Dashboard query time: < 2 seconds
- [ ] Alert evaluation time: < 30 seconds

### Operational Metrics

- [ ] System uptime: > 99.9%
- [ ] Alert false positive rate: < 5%
- [ ] Dashboard user satisfaction: > 8/10
- [ ] Documentation completeness: 100%
- [ ] Time to resolve issues: < 1 hour

---

## Handoff Checklist

### For Next Developer

- [ ] All code committed to repository
- [ ] All schema files in `infrastructure/postgres/`
- [ ] All dashboard JSONs in `infrastructure/monitoring/grafana/dashboards/`
- [ ] All alert rules in `infrastructure/monitoring/prometheus/alerts/`
- [ ] All documentation in `ai-working/dashboard enhancing/`
- [ ] Environment variables documented in `.env.template`
- [ ] Integration tests pass
- [ ] Performance benchmarks documented
- [ ] Known issues documented
- [ ] Next steps identified

### For Operations Team

- [ ] Operational runbook complete
- [ ] Alert response procedures documented
- [ ] Backup and restore procedures tested
- [ ] Monitoring of monitoring in place
- [ ] On-call escalation path defined
- [ ] System access credentials provided
- [ ] Training session scheduled

---

## Appendix

### A. File Structure

```
nautilus_trader/
├── infrastructure/
│   ├── postgres/
│   │   ├── 01-base-schema.sql          (existing)
│   │   ├── 02-ai-extensions.sql        (existing)
│   │   ├── 03-backtest-schema.sql      (new)
│   │   └── 04-dashboard-views.sql      (new)
│   └── monitoring/
│       ├── prometheus/
│       │   ├── prometheus.yml          (update)
│       │   └── alerts/
│       │       └── ai_adaptive_alerts.yml (new)
│       └── grafana/
│           ├── provisioning/
│           │   └── datasources/
│           │       └── datasources.yml  (update)
│           └── dashboards/
│               ├── 01-executive-overview.json      (new)
│               ├── 02-strategy-performance.json    (new)
│               ├── 03-ml-optimization.json         (new)
│               ├── 04-regime-analysis.json         (new)
│               ├── 05-pattern-detection.json       (new)
│               ├── 06-risk-management.json         (new)
│               ├── 07-sentiment-analysis.json      (new)
│               └── 08-trade-analysis.json          (new)
├── ajk_strategies/
│   ├── database/
│   │   ├── __init__.py
│   │   ├── connection_pool.py          (new)
│   │   └── backtest_storage.py         (new)
│   ├── cache/
│   │   ├── __init__.py
│   │   └── redis_manager.py            (new)
│   ├── monitoring/
│   │   ├── __init__.py
│   │   ├── metrics_definitions.py      (new)
│   │   ├── metrics_collector.py        (new)
│   │   └── metrics_server.py           (new)
│   ├── ai_adaptive_strategy.py         (modify)
│   └── run_backtest_with_real_data.py  (modify)
├── tests/
│   └── integration/
│       └── test_monitoring_pipeline.py (new)
└── ai-working/
    └── dashboard enhancing/
        ├── research/
        │   └── analysis.md             (complete)
        ├── plan.md                     (this file)
        ├── implementation.md           (next)
        ├── OPERATIONS.md               (Phase 7)
        ├── DASHBOARD_GUIDE.md          (Phase 7)
        └── DEVELOPER.md                (Phase 7)
```

### B. Dependencies Matrix

| Phase | Depends On | Blocks |
|-------|------------|--------|
| 1 (Database) | PostgreSQL running | 2, 5 |
| 2 (Metrics) | None | 4, 6 |
| 3 (Redis) | Redis running | 6 |
| 4 (Prometheus) | 2 | 5, 6 |
| 5 (Grafana) | 1, 4 | 6 |
| 6 (Testing) | 1, 2, 3, 4, 5 | 7 |
| 7 (Docs) | 6 | None |

### C. Quick Start Commands

```bash
# 1. Start infrastructure
cd infrastructure
docker-compose up -d

# 2. Initialize database
docker exec nautilus_postgres psql -U nautilus -d nautilus_trader < postgres/03-backtest-schema.sql
docker exec nautilus_postgres psql -U nautilus -d nautilus_trader < postgres/04-dashboard-views.sql

# 3. Start metrics server
python ajk_strategies/monitoring/metrics_server.py &

# 4. Run backtest with monitoring
python ajk_strategies/run_backtest_with_real_data.py

# 5. Access dashboards
# Grafana: http://localhost:3000
# Prometheus: http://localhost:9090
# Metrics: http://localhost:8000/metrics
```

---

**Status:** Implementation Plan Complete ✅  
**Next Step:** Create detailed implementation guide  
**Estimated Total Time:** 24-32 hours (3-4 days)

