# AI-Adaptive Strategy Infrastructure Implementation Plan

**Created:** October 6, 2025  
**Status:** Planning → Implementation  
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
- **Backtest Runner**: `run_backtest_with_real_data.py` (512 lines) - fully operational
- **Data**: 4.3 years BTC/ETH (2.26M bars each) in Parquet format
- **Results Export**: CSV files to `backtest_results/` directory
- **Strategy**: AI-Adaptive with ML optimization, regime detection, risk management

### ❌ What's Missing
- **Database Storage**: Results only in CSV, not queryable/searchable
- **Caching Layer**: No Redis for strategy state persistence
- **Monitoring**: No real-time dashboards or metrics
- **Infrastructure**: No Docker stack deployed

### 🎯 Goal
Transform from **file-based results** to **production database infrastructure** with monitoring.

---

## Phase 1: PostgreSQL Integration (Week 1)

### Objective
Store backtest results in PostgreSQL instead of CSV files, enabling:
- Historical result queries
- Strategy comparison analysis
- Performance trend tracking
- Advanced analytics

### Implementation Plan

#### Step 1.1: Deploy PostgreSQL Container
```bash
cd /home/ajk/Nautilus/nautilus_trader/infrastructure/docker

# Start PostgreSQL
docker-compose up -d postgres

# Verify
docker-compose ps
docker-compose logs postgres
```

#### Step 1.2: Create Database Schema
The parent plan already has comprehensive schema at `infrastructure/postgres/schema.sql`. We'll extend it for AI-Adaptive specific needs:

**File:** `infrastructure/postgres/ai_adaptive_schema.sql`
```sql
-- ============================================
-- AI-ADAPTIVE STRATEGY EXTENSIONS
-- ============================================

-- ML Model Performance Tracking
CREATE TABLE ml_optimization_log (
    id BIGSERIAL PRIMARY KEY,
    backtest_id INTEGER REFERENCES backtests(id) ON DELETE CASCADE,
    timestamp BIGINT NOT NULL,
    
    -- Current parameters
    fast_ema_period INTEGER,
    slow_ema_period INTEGER,
    
    -- Optimization metrics
    gradient_descent_loss DECIMAL(10,6),
    logistic_regression_score DECIMAL(10,6),
    newton_raphson_iterations INTEGER,
    
    -- Performance snapshot
    current_win_rate DECIMAL(5,2),
    current_sharpe DECIMAL(10,4),
    bars_since_last_optimization INTEGER,
    
    created_at TIMESTAMP DEFAULT NOW()
);

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

## Phase 2: Redis Caching (Week 1-2)

### Objective
Implement Redis caching for:
- Strategy state persistence (positions, parameters)
- ML model checkpoints
- Real-time market data (when moving to live trading)
- Rate limiting for exchange APIs

### Implementation Plan

#### Step 2.1: Deploy Redis Container
```bash
cd /home/ajk/Nautilus/nautilus_trader/infrastructure/docker

# Start Redis
docker-compose up -d redis

# Test connection
docker exec nautilus_redis redis-cli ping
```

#### Step 2.2: Create Redis Manager

**File:** `ajk_strategies/cache/redis_manager.py`
```python
"""Redis cache manager for AI-Adaptive strategy."""

import redis
import json
import pickle
from typing import Any, Optional
import os

class StrategyCache:
    """Redis cache for strategy state and models."""
    
    def __init__(self):
        self.client = redis.Redis(
            host=os.getenv('REDIS_HOST', 'localhost'),
            port=int(os.getenv('REDIS_PORT', 6379)),
            password=os.getenv('REDIS_PASSWORD', 'changeme'),
            db=0,
            decode_responses=False  # For pickle support
        )
    
    # Strategy State Management
    def save_strategy_state(self, strategy_id: str, state: dict, ttl: int = 3600):
        """Save strategy state (positions, parameters, etc.)"""
        key = f"strategy:{strategy_id}:state"
        self.client.setex(key, ttl, json.dumps(state))
    
    def get_strategy_state(self, strategy_id: str) -> Optional[dict]:
        """Get strategy state."""
        key = f"strategy:{strategy_id}:state"
        data = self.client.get(key)
        return json.loads(data) if data else None
    
    # ML Model Checkpoints
    def save_ml_model(self, strategy_id: str, model: Any, version: str = "latest"):
        """Save ML model checkpoint (pickled)."""
        key = f"ml_model:{strategy_id}:{version}"
        self.client.set(key, pickle.dumps(model))
    
    def load_ml_model(self, strategy_id: str, version: str = "latest") -> Optional[Any]:
        """Load ML model checkpoint."""
        key = f"ml_model:{strategy_id}:{version}"
        data = self.client.get(key)
        return pickle.loads(data) if data else None
    
    # Regime Detection Cache
    def cache_current_regime(self, instrument: str, regime: str, confidence: float, ttl: int = 300):
        """Cache current market regime."""
        key = f"regime:{instrument}:current"
        data = {
            'regime': regime,
            'confidence': confidence,
            'timestamp': int(time.time() * 1e9)
        }
        self.client.setex(key, ttl, json.dumps(data))
    
    def get_current_regime(self, instrument: str) -> Optional[dict]:
        """Get cached regime."""
        key = f"regime:{instrument}:current"
        data = self.client.get(key)
        return json.loads(data) if data else None
```

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
- [ ] PostgreSQL container running
- [ ] Schema created and tested
- [ ] Backtest results saving to database
- [ ] Redis container running
- [ ] Basic caching implemented

### Week 2 Completion
- [ ] Grafana dashboards created
- [ ] Prometheus metrics exporting
- [ ] Full stack deployed and tested
- [ ] All services healthy
- [ ] Documentation complete

### Performance Targets
- **Database writes**: < 100ms per backtest result
- **Redis cache hits**: > 95% for regime detection
- **Dashboard refresh**: < 2 seconds
- **Metrics collection**: < 10ms overhead per datapoint

---

## Next Steps

### Immediate (This Session)
1. Review this plan with user
2. Create directory structure
3. Copy docker-compose.yml from infrastructure/
4. Set up .env.local with passwords

### Tomorrow
1. Deploy PostgreSQL + Redis
2. Create database schema
3. Test basic connectivity
4. Update backtest runner

### This Week
1. Complete database integration
2. Deploy monitoring stack
3. Create first Grafana dashboard
4. Run end-to-end test

---

## Resources

### Documentation
- **Parent Plan**: `/home/ajk/Nautilus/nautilus_trader/infrastructure/INFRASTRUCTURE_PLAN.md`
- **Rust Infrastructure**: `/home/ajk/Nautilus/nautilus_trader/crates/infrastructure/`
- **Nautilus Docs**: https://nautilustrader.io/docs/

### Docker Services
- PostgreSQL: Port 5432
- Redis: Port 6379
- Prometheus: Port 9090
- Grafana: Port 3000
- Metrics Server: Port 8000

### Database Connections
```python
# PostgreSQL
from database.backtest_storage import BacktestDatabaseStorage
db = BacktestDatabaseStorage()

# Redis
from cache.redis_manager import StrategyCache
cache = StrategyCache()
```

---

**Status:** Ready for Implementation  
**Estimated Time:** 2 weeks (6-8 hours per week)  
**Priority:** High - Needed for production deployment

