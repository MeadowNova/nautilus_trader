# AI-Adaptive Strategy Infrastructure Implementation Plan

**Created:** October 6, 2025  
**Status:** In Progress — Persistence verified; monitoring & paper-trading enablement pending  
**Working Directory:** `/home/ajk/Nautilus/nautilus_trader/ai-working/database_Infra layer`  
**Parent Plan:** `/home/ajk/Nautilus/nautilus_trader/infrastructure/INFRASTRUCTURE_PLAN.md`

---

## Executive Summary

This plan adapts the comprehensive Nautilus infrastructure stack specifically for the **AI-Adaptive Strategy** deployment, focusing on:

1. **Immediate Integration** - Connect backtest results to PostgreSQL (eliminate CSV files)
2. **Redis Caching** - Store strategy state, ML models, and real-time data
3. **Monitoring Dashboards** - Track regime detection, ML optimization, and risk metrics
4. **Production Readiness** - Deploy full stack with Docker Compose

**Key Advantage:** Nautilus already has Rust-based infrastructure (`nautilus-infrastructure` crate) with Redis and PostgreSQL support built-in!

---

## Current State Analysis

### ✅ What We Have
- **Backtest + Strategy Integration**: `run_backtest_with_real_data.py` loads the refreshed HMM/LSTM/XGB artefacts and exercises the full pipeline on historical BTC/ETH data.
- **PostgreSQL Stack Online**: Docker compose brings up `nautilus_postgres` on host port **5435**. The `ai_extensions` schema now stores `model_training_runs`, `model_artifacts`, `backtest_runs`, `backtest_metrics`, and the existing AI logs.
- **Training Persistence**: All trainers persist run metadata, artefacts, and metrics whenever `NAUTILUS_PERSIST_MODELS=1`. Latest verification (2025-10-08) confirmed inserts into `ai_extensions.model_training_runs` after a short HMM session.
- **Redis Cache Layer**: `ajk_strategies/cache/redis_manager.py` is live; `AIAdaptiveStrategy` publishes state and model metadata when `enable_redis_cache` or `NAUTILUS_ENABLE_REDIS_CACHE=1`. Manual `StrategyCache.save_strategy_state` + `redis-cli` checks succeeded against container port **6378**.

### ⚙️ What's Still Pending
- **Backtest Persistence Confirmation**: Manual inserts validated via `PostgresPersistenceClient`, but we still need an uninterrupted BTC/ETH backtest run with `NAUTILUS_PERSIST_BACKTESTS=1` to populate `ai_extensions.backtest_runs`/`backtest_metrics` end-to-end.
- **Monitoring & Dashboards**: Prometheus/Grafana services are defined but not bootstrapped. Exporters for Postgres (`model_artifact_info`, training run health) and Redis (cache hit/miss) remain todo along with initial Grafana dashboards.
- **Paper-Trading Enablement**: CCXT adapter wiring, exchange credential scaffolding, and TradingNode dry-runs on Bybit/OKX testnets are outstanding before we can claim paper trading readiness.
- **Operational Automation**: Need cron/CI hooks for migrations, regular artefact retention, alerting, and runbook updates once monitoring comes online.

### 🎯 Current Goal
With persistence and caching verified, focus next on monitoring/alerting bring-up and the CCXT-led paper-trading workflow so we can exercise the infrastructure under production-like conditions.

---

### 2025-10-08 Verification Snapshot
- `docker compose --env-file infrastructure/.env.local up -d postgres redis` remains the canonical bring-up; containers report healthy on **5435/6378**.
- Short HMM trainer run (with `NAUTILUS_PERSIST_MODELS=1`) inserted rows into `ai_extensions.model_training_runs`, `model_artifacts`, and `model_training_metrics`.
- Manual calls through `PostgresPersistenceClient` and `StrategyCache.save_strategy_state` confirmed read/write paths; Redis values retrieved via `redis-cli` round-trip.
- These checks cover persistence primitives; remaining work targets observability, automated validation, and CCXT-driven paper execution.

---

## Dashboard & Monitoring Workstream (Consolidated)

> Derived from historical `ai-working/dashboard enhancing*/plan.md` + `implementation.md` drafts. The canonical home for these tasks is now this document; treat both `ai-working/dashboard enhancing` and its trailing-space duplicate as archived references only.

### Core Deliverables
- **Schema uplift:** Backtest + trade detail tables, ML snapshots, and circuit-breaker logs (`infrastructure/postgres/03-backtest-schema.sql`, `04-dashboard-views.sql`). Includes views for Grafana (`v_backtest_performance`, `v_strategy_comparison`, etc.) and supporting indexes.
- **Python storage helpers:** Connection pooling + query helpers under `ajk_strategies/database/` (pool manager, typed query modules) replacing direct psycopg2 usage in runners.
- **Prometheus exporter:** `ajk_strategies/monitoring/` package to define metrics (`model_artifact_info`, backtest throughput, TradingNode health), scrape Postgres + Redis gauges, and expose `/metrics`.
- **Redis cache extensions:** Additional helpers for regime snapshots, ML model metadata, and circuit-breaker state to support dashboard instrumentation.
- **Grafana dashboards:** Eight JSON dashboards (Executive overview, Strategy performance, ML optimisation, Regime analysis, Pattern detection, Risk, Sentiment, Trade analysis) provisioned via `infrastructure/monitoring/grafana/`.
- **Alerting:** Prometheus alert rules (stale models, failed inserts, cache saturation, paper-trading heartbeat) with escalation guidance.
- **Testing + docs:** Integration tests for the monitoring pipeline, Ops runbook, developer guide, dashboard usage guide.

### Consolidated Gaps
- Backtest dashboard SQL applied (2025-10-08 via `03-backtest-schema.sql` / `04-dashboard-views.sql`) — capture validation queries and add to runbook.
- Monitoring package scaffolded (`ajk_strategies/monitoring/*`) — integrate with Prometheus scrape config + Grafana dashboards and document refresh cadence.
- Docker monitoring stack exists (`prometheus`, `grafana` services) but lacks configuration, exporters, or dashboards.
- Documentation from prior plan lives only in drafts; we need fresh `IMPLEMENTATION.md`, `OPERATIONS.md`, etc., scoped to the now canonical folder.

---

## Phase 1: PostgreSQL Integration *(Completed 2025-10-08)*

- **Stack** – `docker compose --env-file infrastructure/.env.local up -d postgres redis`  
  Host ports: **5435 → postgres**, **6378 → redis** (health-checked). Re-running `02-ai-extensions.sql` / `03-indexes.sql` is safe for future migrations.
- **Schema** – `ai_extensions` now owns: `model_training_runs`, `model_artifacts`, `backtest_runs`, `backtest_metrics`, `performance_metrics`, `ml_optimization_log`, `regime_detection_log`, `pattern_detection_log`, `risk_events`, `sentiment_log`, each indexed for strategy + recency lookups.
- **Application Hooks** – `ajk_strategies/persistence/postgres_storage.py` and `ajk_strategies/training/persistence.py` wrap psycopg2 access. Trainers/backtests opt into writes with `NAUTILUS_PERSIST_MODELS=1` / `NAUTILUS_PERSIST_BACKTESTS=1`.
- **ENV Notes** – Scripts inherit `DB_HOST=localhost`, `DB_PORT=5435`, `DB_USER=nautilus`, `DB_PASSWORD=<secret>` from `infrastructure/.env.local`. Export them manually when running commands outside docker-compose.

## Phase 2: Model Training Artefacts (2025-10-07)
- **Market Regime HMM:** `ajk_strategies/models/market_regime_hmm.pkl` trained on 2,262,971 rows; state counts `[57896, 1011601, 1, 1193472, 1]`.
- **Price Forecast LSTM:** `ajk_strategies/models/price_forecast_lstm.h5` with metadata `price_forecast_lstm_meta.pkl`; validation MSE `0.83754` after early stopping at epoch 5.
- **Signal Aggregator XGBoost:** `ajk_strategies/models/signal_aggregator_xgb.pkl`; class distribution `[629103, 819741, 814091]` for hold/long/short respectively.
- Training CLI enhancements:
  * `features.load_price_frame` now auto-detects `ts_event`/`time` columns as `timestamp` for Nautilus parquet exports.
  * `train_signal_xgb.compute_lstm_forecasts` vectorized via `sliding_window_view`, reducing full-dataset inference from ~30 minutes to ~2 minutes.

---

CREATE INDEX idx_ml_log_backtest 
ON ml_optimization_log(backtest_id, timestamp);

-- Market Regime Tracking
CREATE TABLE regime_detection_log (
    id BIGSERIAL PRIMARY KEY,
    backtest_id INTEGER REFERENCES backtests(id) ON DELETE CASCADE,
    timestamp BIGINT NOT NULL,
    
    -- Regime classification
    regime VARCHAR(20) NOT NULL,  -- TRENDING_UP, TRENDING_DOWN, RANGING, VOLATILE
    confidence DECIMAL(5,2) NOT NULL,
    
    -- Clustering metrics
    cluster_centers JSONB,  -- K-means cluster centers
    inertia DECIMAL(10,6),  -- Clustering quality metric
    
    -- Price characteristics
    volatility DECIMAL(10,6),
    trend_strength DECIMAL(10,6),
    
    created_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX idx_regime_log_backtest 
ON regime_detection_log(backtest_id, timestamp);

CREATE INDEX idx_regime_by_type 
ON regime_detection_log(regime, confidence DESC);

-- Pattern Detection Log
CREATE TABLE pattern_detection_log (
    id BIGSERIAL PRIMARY KEY,
    backtest_id INTEGER REFERENCES backtests(id) ON DELETE CASCADE,
    timestamp BIGINT NOT NULL,
    
    -- Pattern details
    pattern_type VARCHAR(50) NOT NULL,  -- HIGHER_HIGHS, LOWER_LOWS, CONSOLIDATION, etc.
    detection_method VARCHAR(50),  -- DYNAMIC_PROGRAMMING, TEMPLATE_MATCHING
    confidence DECIMAL(5,2),
    
    -- Pattern characteristics
    pattern_start_time BIGINT,
    pattern_duration INTEGER,
    price_range DECIMAL(20,8),
    
    -- Action taken
    signal_generated BOOLEAN DEFAULT FALSE,
    trade_executed BOOLEAN DEFAULT FALSE,
    
    created_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX idx_pattern_log_backtest 
ON pattern_detection_log(backtest_id, timestamp);

-- Risk Management Events
CREATE TABLE risk_events (
    id BIGSERIAL PRIMARY KEY,
    backtest_id INTEGER REFERENCES backtests(id) ON DELETE CASCADE,
    timestamp BIGINT NOT NULL,
    
    -- Event type
    event_type VARCHAR(50) NOT NULL,  -- CIRCUIT_BREAKER, POSITION_LIMIT, DRAWDOWN_LIMIT
    severity VARCHAR(20) NOT NULL,  -- INFO, WARNING, CRITICAL
    
    -- Event details
    current_drawdown DECIMAL(10,4),
    current_win_rate DECIMAL(5,2),
    consecutive_losses INTEGER,
    position_size DECIMAL(20,8),
    
    -- Action taken
    action VARCHAR(50),  -- TRADING_HALTED, POSITION_REDUCED, ALERT_SENT
    description TEXT,
    
    created_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX idx_risk_events_backtest 
ON risk_events(backtest_id, timestamp);

CREATE INDEX idx_risk_events_severity 
ON risk_events(severity, event_type);

-- Sentiment Analysis Log (for Reddit integration)
CREATE TABLE sentiment_log (
    id BIGSERIAL PRIMARY KEY,
    backtest_id INTEGER REFERENCES backtests(id),
    timestamp BIGINT NOT NULL,
    
    -- Sentiment data
    symbol VARCHAR(20) NOT NULL,
    sentiment_score DECIMAL(5,2),  -- -1.0 to +1.0
    mention_count INTEGER,
    engagement_score DECIMAL(10,2),
    
    -- Sources
    subreddit VARCHAR(50),
    post_count INTEGER,
    
    -- Impact
    signal_weight DECIMAL(5,2),  -- How much this influenced trading decision
    
    created_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX idx_sentiment_log_symbol 
ON sentiment_log(symbol, timestamp DESC);

-- View: Strategy Health Dashboard
CREATE VIEW v_strategy_health AS
SELECT 
    b.id as backtest_id,
    b.strategy_name,
    b.instrument,
    b.total_pnl,
    b.win_rate,
    b.sharpe_ratio,
    
    -- Latest regime
    (SELECT regime FROM regime_detection_log 
     WHERE backtest_id = b.id 
     ORDER BY timestamp DESC LIMIT 1) as current_regime,
    
    -- Recent risk events
    (SELECT COUNT(*) FROM risk_events 
     WHERE backtest_id = b.id 
     AND severity = 'CRITICAL') as critical_risk_events,
    
    -- ML optimization count
    (SELECT COUNT(*) FROM ml_optimization_log 
     WHERE backtest_id = b.id) as ml_optimizations,
    
    -- Pattern detections
    (SELECT COUNT(*) FROM pattern_detection_log 
     WHERE backtest_id = b.id 
     AND signal_generated = true) as patterns_detected,
    
    b.created_at
FROM backtests b
WHERE b.strategy_name LIKE '%AI%Adaptive%'
ORDER BY b.created_at DESC;
```

#### Step 1.3: Update Backtest Runner to Use PostgreSQL

**File:** `ajk_strategies/database/backtest_storage.py`
```python
"""
PostgreSQL storage for AI-Adaptive backtest results.
"""

import psycopg2
from psycopg2.extras import RealDictCursor, execute_batch
import json
from datetime import datetime
from typing import Dict, List, Optional
import os

class BacktestDatabaseStorage:
    """Stores backtest results in PostgreSQL."""
    
    def __init__(self):
        self.conn = self._get_connection()
    
    def _get_connection(self):
        """Create database connection."""
        return psycopg2.connect(
            host=os.getenv('DB_HOST', 'localhost'),
            port=int(os.getenv('DB_PORT', 5432)),
            database=os.getenv('DB_NAME', 'nautilus_trader'),
            user=os.getenv('DB_USER', 'nautilus'),
            password=os.getenv('DB_PASSWORD', 'changeme'),
            cursor_factory=RealDictCursor
        )
    
    def save_backtest_result(self, 
                            run_id: str,
                            strategy_name: str,
                            instrument: str,
                            start_date: datetime,
                            end_date: datetime,
                            metrics: Dict,
                            parameters: Dict) -> int:
        """
        Save backtest result to database.
        
        Returns:
            backtest_id for further inserts
        """
        with self.conn.cursor() as cur:
            query = """
                INSERT INTO backtests (
                    run_id, strategy_name, strategy_version, instrument,
                    start_date, end_date,
                    initial_capital, final_capital, total_pnl, total_pnl_pct,
                    total_trades, winning_trades, losing_trades, win_rate,
                    sharpe_ratio, sortino_ratio, max_drawdown, max_drawdown_pct,
                    profit_factor, avg_win, avg_loss,
                    parameters, data_bars_processed, duration_seconds
                ) VALUES (
                    %(run_id)s, %(strategy_name)s, %(strategy_version)s, %(instrument)s,
                    %(start_date)s, %(end_date)s,
                    %(initial_capital)s, %(final_capital)s, %(total_pnl)s, %(total_pnl_pct)s,
                    %(total_trades)s, %(winning_trades)s, %(losing_trades)s, %(win_rate)s,
                    %(sharpe_ratio)s, %(sortino_ratio)s, %(max_drawdown)s, %(max_drawdown_pct)s,
                    %(profit_factor)s, %(avg_win)s, %(avg_loss)s,
                    %(parameters)s, %(data_bars_processed)s, %(duration_seconds)s
                ) RETURNING id;
            """
            
            data = {
                'run_id': run_id,
                'strategy_name': strategy_name,
                'strategy_version': 'v1.0',
                'instrument': instrument,
                'start_date': start_date,
                'end_date': end_date,
                'initial_capital': metrics.get('initial_capital', 100000),
                'final_capital': metrics.get('final_capital', 0),
                'total_pnl': metrics.get('total_pnl', 0),
                'total_pnl_pct': metrics.get('pnl_pct', 0),
                'total_trades': metrics.get('total_trades', 0),
                'winning_trades': metrics.get('winning_trades', 0),
                'losing_trades': metrics.get('losing_trades', 0),
                'win_rate': metrics.get('win_rate', 0),
                'sharpe_ratio': metrics.get('sharpe_ratio'),
                'sortino_ratio': metrics.get('sortino_ratio'),
                'max_drawdown': metrics.get('max_drawdown'),
                'max_drawdown_pct': metrics.get('max_drawdown_pct'),
                'profit_factor': metrics.get('profit_factor'),
                'avg_win': metrics.get('avg_win'),
                'avg_loss': metrics.get('avg_loss'),
                'parameters': json.dumps(parameters),
                'data_bars_processed': metrics.get('bars_processed', 0),
                'duration_seconds': metrics.get('duration_seconds', 0)
            }
            
            cur.execute(query, data)
            backtest_id = cur.fetchone()['id']
            self.conn.commit()
            
            print(f"✅ Saved backtest result to database (ID: {backtest_id})")
            return backtest_id
    
    def save_regime_detection(self, backtest_id: int, regime_logs: List[Dict]):
        """Save regime detection log entries."""
        with self.conn.cursor() as cur:
            query = """
                INSERT INTO regime_detection_log (
                    backtest_id, timestamp, regime, confidence,
                    cluster_centers, volatility, trend_strength
                ) VALUES (
                    %(backtest_id)s, %(timestamp)s, %(regime)s, %(confidence)s,
                    %(cluster_centers)s, %(volatility)s, %(trend_strength)s
                );
            """
            
            data = [
                {
                    'backtest_id': backtest_id,
                    'timestamp': log['timestamp'],
                    'regime': log['regime'],
                    'confidence': log['confidence'],
                    'cluster_centers': json.dumps(log.get('cluster_centers')),
                    'volatility': log.get('volatility'),
                    'trend_strength': log.get('trend_strength')
                }
                for log in regime_logs
            ]
            
            execute_batch(cur, query, data)
            self.conn.commit()
            print(f"✅ Saved {len(regime_logs)} regime detection entries")
    
    def save_ml_optimization(self, backtest_id: int, ml_logs: List[Dict]):
        """Save ML optimization log entries."""
        with self.conn.cursor() as cur:
            query = """
                INSERT INTO ml_optimization_log (
                    backtest_id, timestamp, fast_ema_period, slow_ema_period,
                    gradient_descent_loss, current_win_rate, current_sharpe,
                    bars_since_last_optimization
                ) VALUES (
                    %(backtest_id)s, %(timestamp)s, %(fast_ema)s, %(slow_ema)s,
                    %(gd_loss)s, %(win_rate)s, %(sharpe)s, %(bars_since)s
                );
            """
            
            data = [
                {
                    'backtest_id': backtest_id,
                    'timestamp': log['timestamp'],
                    'fast_ema': log.get('fast_ema_period'),
                    'slow_ema': log.get('slow_ema_period'),
                    'gd_loss': log.get('gradient_descent_loss'),
                    'win_rate': log.get('current_win_rate'),
                    'sharpe': log.get('current_sharpe'),
                    'bars_since': log.get('bars_since_last_opt')
                }
                for log in ml_logs
            ]
            
            execute_batch(cur, query, data)
            self.conn.commit()
            print(f"✅ Saved {len(ml_logs)} ML optimization entries")
    
    def close(self):
        """Close database connection."""
        if self.conn:
            self.conn.close()
```

#### Step 1.4: Integrate with Backtest Runner

**Modify:** `ajk_strategies/run_backtest_with_real_data.py`
```python
# Add at top of file
from database.backtest_storage import BacktestDatabaseStorage

# In run_backtest function, after backtest completes:
def run_backtest(...):
    # ... existing code ...
    
    # Save to database
    db = BacktestDatabaseStorage()
    
    try:
        backtest_id = db.save_backtest_result(
            run_id=timestamp,
            strategy_name=f"AI-Adaptive-{scenario_name}",
            instrument=instrument_symbol,
            start_date=start_time,
            end_date=end_time,
            metrics={
                'initial_capital': starting_usdt,
                'final_capital': total_equity,
                'total_pnl': pnl,
                'pnl_pct': pnl_pct,
                'total_trades': len(closed_positions),
                'win_rate': win_rate if 'win_rate' in locals() else 0,
                'profit_factor': profit_factor if 'profit_factor' in locals() else 0,
                'bars_processed': len(bars),
                'duration_seconds': duration
            },
            parameters=strategy_config.dict()
        )
        
        # If strategy logged regime detections, save them
        if hasattr(strategy, 'regime_history'):
            db.save_regime_detection(backtest_id, strategy.regime_history)
        
        # If strategy logged ML optimizations, save them
        if hasattr(strategy, 'ml_optimization_history'):
            db.save_ml_optimization(backtest_id, strategy.ml_optimization_history)
        
    finally:
        db.close()
    
    # ... rest of existing code ...
```

### Step 1.5: Query and Analysis Tools

**File:** `ajk_strategies/database/query_results.py`
```python
"""Query backtest results from PostgreSQL."""

from database.backtest_storage import BacktestDatabaseStorage

def get_recent_backtests(limit=10):
    """Get recent backtest results."""
    db = BacktestDatabaseStorage()
    with db.conn.cursor() as cur:
        cur.execute("""
            SELECT * FROM v_recent_backtests
            LIMIT %s
        """, (limit,))
        results = cur.fetchall()
    db.close()
    return results

def get_best_strategies(min_trades=10):
    """Get best performing strategy configurations."""
    db = BacktestDatabaseStorage()
    with db.conn.cursor() as cur:
        cur.execute("""
            SELECT 
                instrument,
                parameters->>'fast_ema_period' as fast_ema,
                parameters->>'slow_ema_period' as slow_ema,
                AVG(sharpe_ratio) as avg_sharpe,
                AVG(win_rate) as avg_win_rate,
                AVG(total_pnl_pct) as avg_return,
                COUNT(*) as num_backtests
            FROM backtests
            WHERE total_trades >= %s
            GROUP BY instrument, fast_ema, slow_ema
            HAVING COUNT(*) >= 3
            ORDER BY avg_sharpe DESC
            LIMIT 10
        """, (min_trades,))
        results = cur.fetchall()
    db.close()
    return results

def get_regime_analysis(backtest_id):
    """Analyze regime detection for a backtest."""
    db = BacktestDatabaseStorage()
    with db.conn.cursor() as cur:
        cur.execute("""
            SELECT 
                regime,
                COUNT(*) as occurrences,
                AVG(confidence) as avg_confidence,
                AVG(volatility) as avg_volatility
            FROM regime_detection_log
            WHERE backtest_id = %s
            GROUP BY regime
            ORDER BY occurrences DESC
        """, (backtest_id,))
        results = cur.fetchall()
    db.close()
    return results
```

---

## Phase 2: Redis Caching *(Completed 2025-10-08)*

- **Runtime** – Redis runs via the same compose command (`up -d redis`) and listens on **6378** with password enforcement. `redis-cli -a $REDIS_PASSWORD ping` is the quickest health check.
- **Code** – `ajk_strategies/cache/redis_manager.py` exposes `StrategyCache` (state snapshots, model metadata, rate limiting, market snapshots) driven by `RedisCacheConfig` values from `.env.local`.
- **Strategy** – `AIAdaptiveStrategy` opt-in switches: set `AIAdaptiveStrategyConfig.enable_redis_cache=True` or export `NAUTILUS_ENABLE_REDIS_CACHE=1`. On start it restores counters, republishes metadata, and begins periodic state snapshots (`redis_state_interval`, default 20 bars).
- **Validation** – Manual smoke tests wrote to `strategy:test_strategy:state`; keys were visible via `docker exec nautilus_redis redis-cli -a ... keys strategy:*`.

---

## Phase 3: Monitoring Dashboards (Week 2)

### Objective
Create Grafana dashboards to monitor:
- Backtest performance metrics
- Strategy health (win rate, Sharpe, drawdown)
- Market regime distribution
- ML optimization effectiveness
- Risk events and circuit breakers

### Implementation Plan

#### Step 3.1: Deploy Monitoring Stack
```bash
cd /home/ajk/Nautilus/nautilus_trader/infrastructure/docker

# Start Prometheus + Grafana
docker-compose up -d prometheus grafana

# Access Grafana: http://localhost:3000
# Username: admin
# Password: (from .env.local)
```

#### Step 3.2: Create Grafana Dashboards

**Dashboard 1: AI-Adaptive Strategy Overview**
- Total backtests run
- Average Sharpe ratio
- Average win rate
- Total P&L across all runs
- Best/worst performing instruments

**Dashboard 2: Strategy Health**
- Real-time P&L chart
- Equity curve
- Win rate gauge
- Current drawdown meter
- Circuit breaker status

**Dashboard 3: ML Optimization**
- Parameter evolution (fast/slow EMA over time)
- Optimization frequency
- Win rate before/after optimization
- Gradient descent loss trends

**Dashboard 4: Market Regime Analysis**
- Regime distribution (pie chart)
- Regime transitions over time
- Confidence levels
- Volatility trends per regime

**Dashboard 5: Risk Management**
- Risk events timeline
- Circuit breaker activations
- Drawdown history
- Position size violations
- Consecutive losses tracking

#### Step 3.3: Prometheus Metrics Export

**File:** `ajk_strategies/monitoring/metrics.py`
```python
"""Prometheus metrics for AI-Adaptive strategy."""

from prometheus_client import Counter, Gauge, Histogram, start_http_server

# Strategy Performance
backtest_runs_total = Counter(
    'nautilus_ai_adaptive_backtests_total',
    'Total backtest runs',
    ['instrument', 'scenario']
)

strategy_pnl = Gauge(
    'nautilus_ai_adaptive_pnl',
    'Strategy P&L',
    ['instrument', 'run_id']
)

strategy_sharpe = Gauge(
    'nautilus_ai_adaptive_sharpe_ratio',
    'Strategy Sharpe ratio',
    ['instrument', 'run_id']
)

# ML Optimization
ml_optimizations_total = Counter(
    'nautilus_ai_adaptive_ml_optimizations_total',
    'ML optimization count',
    ['instrument']
)

ema_parameter = Gauge(
    'nautilus_ai_adaptive_ema_parameter',
    'EMA parameter value',
    ['instrument', 'parameter_name']
)

# Regime Detection
regime_changes_total = Counter(
    'nautilus_ai_adaptive_regime_changes_total',
    'Regime change count',
    ['instrument', 'from_regime', 'to_regime']
)

regime_confidence = Gauge(
    'nautilus_ai_adaptive_regime_confidence',
    'Regime detection confidence',
    ['instrument', 'regime']
)

# Risk Management
risk_events_total = Counter(
    'nautilus_ai_adaptive_risk_events_total',
    'Risk event count',
    ['event_type', 'severity']
)

circuit_breaker_active = Gauge(
    'nautilus_ai_adaptive_circuit_breaker_active',
    'Circuit breaker status (1=active, 0=inactive)',
    ['instrument']
)

def start_metrics_server(port=8000):
    """Start Prometheus metrics HTTP server."""
    start_http_server(port)
    print(f"📊 Metrics server started on port {port}")
```

---

## Phase 4: Full Stack Deployment (Week 2)

### Step 4.1: Environment Configuration

**File:** `/home/ajk/Nautilus/nautilus_trader/infrastructure/.env.local`
```bash
# PostgreSQL
DB_HOST=localhost
DB_PORT=5432
DB_NAME=nautilus_trader
DB_USER=nautilus
DB_PASSWORD=your_secure_password_here

# Redis
REDIS_HOST=localhost
REDIS_PORT=6379
REDIS_PASSWORD=your_secure_password_here

# Grafana
GRAFANA_USER=admin
GRAFANA_PASSWORD=your_secure_password_here

# Monitoring
PROMETHEUS_PORT=9090
GRAFANA_PORT=3000
METRICS_SERVER_PORT=8000
```

### Step 4.2: Deploy Full Stack

```bash
cd /home/ajk/Nautilus/nautilus_trader/infrastructure/docker

# Start all services
docker-compose up -d

# Verify all containers running
docker-compose ps

# Check logs
docker-compose logs -f

# Access services:
# Grafana: http://localhost:3000
# Prometheus: http://localhost:9090
# Metrics: http://localhost:8000/metrics
```

### Step 4.3: Initialize Database

```bash
# Run schema creation
docker exec nautilus_postgres psql -U nautilus -d nautilus_trader -f /docker-entrypoint-initdb.d/01-schema.sql

# Run AI-Adaptive extensions
docker exec nautilus_postgres psql -U nautilus -d nautilus_trader < ai_adaptive_schema.sql

# Verify tables created
docker exec nautilus_postgres psql -U nautilus -d nautilus_trader -c "\dt"
```

---

## Phase 5: Integration Testing (Week 2)

### Test Plan

1. **Database Storage Test**
   ```bash
   python ajk_strategies/run_backtest_with_real_data.py
   # Verify results appear in PostgreSQL
   docker exec nautilus_postgres psql -U nautilus -d nautilus_trader -c "SELECT * FROM backtests ORDER BY created_at DESC LIMIT 1;"
   ```

2. **Redis Caching Test**
   ```python
   from cache.redis_manager import StrategyCache
   cache = StrategyCache()
   cache.save_strategy_state('test-001', {'position': 'LONG', 'qty': 0.5})
   state = cache.get_strategy_state('test-001')
   print(state)  # Should return saved data
   ```

3. **Metrics Export Test**
   ```bash
   # Start metrics server
   python -c "from monitoring.metrics import start_metrics_server; start_metrics_server(); import time; time.sleep(60)"
   
   # Check metrics endpoint
   curl http://localhost:8000/metrics
   ```

4. **Grafana Dashboard Test**
   - Access http://localhost:3000
   - Add PostgreSQL data source
   - Import dashboard JSON
   - Verify data visualization

---

## Success Metrics

### Week 1 Completion
- [x] PostgreSQL container running (host port 5435 via docker compose)
- [x] Schema created and tested (`ai_extensions.*` tables + indexes)
- [ ] Backtest results saving to database *(manual inserts verified; awaiting full backtest run due to runtime limits)*
- [x] Redis container running (host port 6378)
- [x] Basic caching implemented (`StrategyCache` opt-in with `NAUTILUS_ENABLE_REDIS_CACHE`)

### Week 2 Completion
- [ ] Grafana dashboards created (pending Prometheus datasource + panels)
- [ ] Prometheus metrics exporting (`model_artifact_info`, Redis/state gauges)
- [ ] Full stack end-to-end test (requires successful backtest persistence run)
- [x] All services healthy (Postgres/Redis containers monitored)
- [ ] Documentation complete (update monitoring + paper-trading guides)

### Performance Targets
- **Database writes**: < 100ms per backtest result
- **Redis cache hits**: > 95% for regime detection
- **Dashboard refresh**: < 2 seconds
- **Metrics collection**: < 10ms overhead per datapoint

---

## Next Steps

### Immediate Focus
1. **Monitoring bring-up**: `docker compose --env-file infrastructure/.env.local up -d prometheus grafana`; add Postgres exporter (training/backtest tables) + Redis exporter (cache hit/miss, TTL) and ship base Grafana dashboards for run health.
2. **Backtest persistence validation**: schedule a constrained BTC/ETH backtest (smaller lookback) under `NAUTILUS_PERSIST_BACKTESTS=1` to populate `ai_extensions.backtest_runs` + `backtest_metrics`, and document verification queries.
3. **Prometheus exporters & alerts**: expose `model_artifact_info`, `training_run_status`, and Redis saturation metrics; define alert thresholds (stale models, cache misses, failed inserts) for the forthcoming dashboards.
4. **GPU-accelerated strategy runs**: confirm `AIAdaptiveStrategyV3` loads the TensorFlow LSTM on CUDA, falls back cleanly to CPU, and halts processing after 50k bars when batching real-data backtests.
5. **Promote GPU artefacts**: wire `signal_aggregator_xgb_gpu.pkl` into live configs, surface `gpu_validation_50k_summary.json` in Grafana, and plan follow-up runs with real trade flow.

• Calibrated GPU Runs

  - ajk_strategies/run_backtest_v3_gpu_validation.py:70-205 now supports segmented execution (--segments, --max-hold-bars, --feature-warmup-bars, --max-hold-bars) plus off‑set slicing so we can
    march through the 2.2 M bar archive in 50 k chunks. Running --segments 20 --max-bars 50000 --max-hold-bars 20 --feature-warmup-bars 50 produces 16 closed trades (223 orders) in ~20.7 s with 28 %
    peak GPU utilisation; the aggregated metrics live in backtest_results/gpu_validation_50k_summary.json.
  - SignalFeatureEngine and AIAdaptiveStrategyV3 have been hardened (ajk_strategies/ai_adaptive_stragey_v3.py:142-509): CUDA/CPU fallback for the LSTM, configurable warmup, trade-cycle
    instrumentation, and deterministic exit timers deliver stable re-entry behaviour so longer slices now emit enough trades for Sharpe/profit-factor validation.
  - We captured an additional 10×200 k-bar validation (backtest_results/gpu_validation_200k_summary.json, 5 closed trades) to benchmark longer windows.

  Grafana Integration

  - Prometheus gauges (ai_gpu_validation_total_trades, ai_gpu_validation_runtime_seconds, ai_gpu_validation_net_pnl, ai_gpu_validation_segments, ai_gpu_validation_last_completed_timestamp) are
    exposed via metrics_collector._refresh_gpu_validation (ajk_strategies/monitoring/metrics_collector.py:14-220, metrics_definitions.py:31-63). Each summary JSON in backtest_results/ now feeds live
    telemetry without manual edits.
  - The “AI Strategy Performance” dashboard was updated (infrastructure/monitoring/grafana/dashboards/ai-strategy-performance.json) to replace the static GPU text panel with four Prometheus-backed
    stat cards (trades, runtime, net PnL, segment count) driven by the new metrics.

  Artifacts & Metrics

  - Latest aggregated JSON summaries: backtest_results/gpu_validation_50k_summary.json (20×50 k slices → trades = 16, runtime ≈ 20.68 s, GPU util 28 %) and backtest_results/
    gpu_validation_200k_summary.json (10×200 k slices → trades = 5, GPU util 24 %). Each segment’s metadata (offset, runtime, completed_at) is preserved under segment_details for drill-downs.
  - GPU validation counters, exits, and probability ceilings are logged per run for quick diagnostics (backtest_gpu_validation.log and /tmp/backtest_gpu_latest.out during execution).

  Next Steps

  1. Verify the new Prometheus gauges from ajk_strategies.monitoring.metrics_server (run with the usual DB/Redis env) and refresh Grafana to confirm the stat cards populate.
  2. Tune the scaler/feature mix so aggregated PnL remains realistic (current segmentation sums raw PnL across slices); consider normalising by segments or switching to median PnL before paper/
     live promotion.


### Pre-Paper-Trading Checklist
1. Populate exchange credentials in `.env.local` (Bybit/OKX testnets) and align adapter configs with `docs/api_reference/adapters` connection parameters; smoke-test CCXT connectivity via `ajk_strategies/ccxt_live_data.py`.
2. Build a paper `TradingNode` profile mirroring backtest parameters, enabling `StrategyCache`, Postgres persistence, and risk limits (`MAX_DAILY_LOSS`, `MAX_DRAWDOWN`, circuit-breakers) per `docs/concepts/portfolio.md` and `docs/concepts/orders.md`.
3. Execute TradingNode dry-runs against CCXT testnet feeds, validating order lifecycle, persistence inserts, Redis snapshots, and Prometheus metrics capture.
4. Draft operational runbooks for start/stop procedures, credential rotation, failure recovery, and alert acknowledgment workflows aligned with `docs/concepts/live.md` guidance.
5. Keep `test_ccxt_integration.py` / `test_ccxt_fallback.py` smoke tests in rotation to monitor reachable venues and update plan assumptions when regional blocking changes.

---

## Resources

### Documentation
- **Parent Plan**: `/home/ajk/Nautilus/nautilus_trader/infrastructure/INFRASTRUCTURE_PLAN.md`
- **Rust Infrastructure**: `/home/ajk/Nautilus/nautilus_trader/crates/infrastructure/`
- **Nautilus Docs**: https://nautilustrader.io/docs/

### Docker Services
- PostgreSQL: Host **5435** (container 5432)
- Redis: Host **6378** (container 6379)
- Prometheus: 9090 *(pending start-up)*
- Grafana: 3000
- Metrics Server: 8000 *(custom exporters to be added)*

### Persistence Helpers
```python
from ajk_strategies.persistence import PostgresPersistenceClient, BacktestRunRecord
from ajk_strategies.cache import StrategyCache

client = PostgresPersistenceClient()
cache = StrategyCache()
```

---

**Status:** DB & Cache operational — Monitoring + paper-trading prep in progress  
**Estimated Remaining Effort:** ~1 focused week (dashboards, TradingNode dry-run)  
**Priority:** High — unlock paper-trading milestone
