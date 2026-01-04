# Database Infrastructure Implementation Plan
## AI-Adaptive Strategy Production System

**Created:** January 2025  
**Project:** Nautilus Trader Database Infrastructure Layer  
**Focus:** PostgreSQL + Redis + Monitoring for AI-Adaptive Trading Strategy  
**Working Directory:** `/home/ajk/Nautilus/nautilus_trader/`

---

## 📋 Executive Summary

This plan implements a production-grade database infrastructure for the Nautilus Trader AI-Adaptive Strategy, transitioning from CSV-based backtest results to a full PostgreSQL + Redis + Monitoring stack.

**Current State:**
- ✅ Nautilus Trader v1.221.0 operational
- ✅ AI-Adaptive Strategy code complete (production-ready)
- ✅ Real historical data loaded (4.3 years BTC/ETH, 2.26M bars each)
- ✅ Backtest runner functional (`run_backtest_with_real_data.py`)
- ✅ Nautilus infrastructure crate provides PostgreSQL/Redis support
- ❌ Results only saved to CSV files (not queryable/searchable)
- ❌ No caching layer for strategy state/ML models
- ❌ No monitoring dashboards

**Target State:**
- ✅ PostgreSQL storing all backtest results + AI-specific metrics
- ✅ Redis caching strategy state, ML models, market regimes
- ✅ Grafana dashboards monitoring strategy performance
- ✅ Full production deployment with Docker Compose
- ✅ Integration with existing backtest runner (minimal code changes)

**Timeline:** 2 weeks (6-8 hours/week)  
**Complexity:** Medium (leveraging existing Nautilus infrastructure)  
**Risk:** Low (non-destructive, CSV backups remain)

---

## 🎯 Implementation Goals

### Week 1: Database Layer
1. Deploy PostgreSQL container
2. Extend existing schema with AI-specific tables
3. Create Python storage layer
4. Integrate with backtest runner
5. Verify data persistence

### Week 2: Caching + Monitoring
1. Deploy Redis container
2. Implement strategy state caching
3. Deploy Prometheus + Grafana
4. Create AI-specific dashboards
5. End-to-end testing

---

## 📊 Context & Related Documents

### Existing Plans
- **`/infrastructure/INFRASTRUCTURE_PLAN.md`** (26KB) - Comprehensive PostgreSQL/Redis/Monitoring plan
- **`/ai-working/database_Infra layer/AI_ADAPTIVE_INFRASTRUCTURE_PLAN.md`** - Original AI-focused plan
- **`/ai-working/database_Infra layer/compaction.md`** - Current status document
- **`/ai-working/learning path/SESSION_SUMMARY.md`** - Previous session summary

### Existing Infrastructure
- **`/crates/infrastructure/`** - Rust implementation (PostgreSQL + Redis)
  - `src/sql/` - SQL cache, queries, models
  - `src/redis/` - Redis cache, message bus
  - Python bindings available via PyO3
- **`/schema/sql/`** - Base database schema
  - `tables.sql` - Core tables (trader, strategy, order, instrument, etc.)
  - `types.sql` - Enums and domain types
  - `functions.sql` - Database functions
  - `partitions.sql` - Table partitioning
- **`/infrastructure/`** - Docker/deployment (directories created, empty)
  - `docker/` - For docker-compose.yml
  - `postgres/` - For additional SQL scripts
  - `redis/` - For redis.conf
  - `monitoring/` - For Prometheus/Grafana configs

### Key Code Files
- **`/ajk_strategies/run_backtest_with_real_data.py`** (512 lines) - Backtest runner to modify
- **`/ajk_strategies/ai_adaptive_strategy_main.py`** - Main strategy implementation

---

## 🏗️ Architecture Overview

```
┌─────────────────────────────────────────────────────────────────┐
│                     Nautilus Trader                             │
│            (Python Application + Rust Core)                     │
│                                                                 │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │   Backtest Runner (run_backtest_with_real_data.py)      │  │
│  │   • Loads Parquet data (4.3 years BTC/ETH)             │  │
│  │   • Executes AI-Adaptive Strategy                       │  │
│  │   • Currently saves results to CSV                      │  │
│  └──────────────┬──────────────────────┬────────────────────┘  │
│                 │                      │                        │
│                 ▼                      ▼                        │
│  ┌──────────────────────┐  ┌──────────────────────┐           │
│  │ PostgreSQL Storage   │  │  Redis Cache Layer   │           │
│  │ • Backtest results   │  │  • Strategy state    │           │
│  │ • AI metrics:        │  │  • ML model checkpts │           │
│  │   - ML optimization  │  │  • Market regimes    │           │
│  │   - Regime detection │  │  • Real-time data    │           │
│  │   - Pattern recog    │  │  • Rate limiting     │           │
│  │   - Risk events      │  └──────────────────────┘           │
│  └──────────────────────┘                                      │
└─────────────────────────────────────────────────────────────────┘
         │                                    │
         └────────────────┬───────────────────┘
                          ▼
                 ┌─────────────────┐
                 │   Prometheus    │
                 │ (Metrics Scraper)│
                 └────────┬─────────┘
                          │
                          ▼
                 ┌─────────────────┐
                 │    Grafana      │
                 │  (Dashboards)   │
                 │ • Strategy P&L  │
                 │ • ML evolution  │
                 │ • Regime dist   │
                 │ • Risk events   │
                 └─────────────────┘
```

---

## 📅 Week 1: PostgreSQL Integration

### Day 1: Docker Infrastructure Setup

**Goal:** Get PostgreSQL running in Docker

**Tasks:**

1. **Create Docker Compose configuration**

   File: `/infrastructure/docker/docker-compose.yml`
   
   ```yaml
   version: '3.8'
   
   services:
     postgres:
       image: postgres:16-alpine
       container_name: nautilus_postgres
       environment:
         POSTGRES_DB: nautilus_trader
         POSTGRES_USER: nautilus
         POSTGRES_PASSWORD: ${DB_PASSWORD:-changeme123}
         PGDATA: /var/lib/postgresql/data/pgdata
       ports:
         - "5432:5432"
       volumes:
         - postgres_data:/var/lib/postgresql/data
         - ../postgres/01-base-schema.sql:/docker-entrypoint-initdb.d/01-base-schema.sql
         - ../postgres/02-ai-extensions.sql:/docker-entrypoint-initdb.d/02-ai-extensions.sql
       healthcheck:
         test: ["CMD-SHELL", "pg_isready -U nautilus -d nautilus_trader"]
         interval: 10s
         timeout: 5s
         retries: 5
       restart: unless-stopped
   
   volumes:
     postgres_data:
       driver: local
   ```

2. **Create environment configuration**

   File: `/infrastructure/.env.local` (gitignored)
   
   ```bash
   # PostgreSQL
   DB_HOST=localhost
   DB_PORT=5432
   DB_NAME=nautilus_trader
   DB_USER=nautilus
   DB_PASSWORD=SecurePassword123!Change
   
   # Redis (for Week 2)
   REDIS_HOST=localhost
   REDIS_PORT=6379
   REDIS_PASSWORD=SecureRedisPassword123!
   
   # Grafana (for Week 2)
   GRAFANA_USER=admin
   GRAFANA_PASSWORD=SecureGrafanaPassword123!
   ```

3. **Start PostgreSQL**

   ```bash
   cd /home/ajk/Nautilus/nautilus_trader/infrastructure/docker
   docker-compose up -d postgres
   
   # Verify
   docker-compose ps
   docker-compose logs postgres
   
   # Test connection
   docker exec -it nautilus_postgres psql -U nautilus -d nautilus_trader -c "SELECT version();"
   ```

**Expected Output:**
```
✅ Container nautilus_postgres running
✅ PostgreSQL 16.x initialized
✅ Database nautilus_trader created
✅ Connection test successful
```

---

### Day 2: Database Schema Creation

**Goal:** Extend base Nautilus schema with AI-specific tables

**Tasks:**

1. **Copy base schema from Nautilus**

   File: `/infrastructure/postgres/01-base-schema.sql`
   
   ```bash
   # Copy existing Nautilus schema
   cat /home/ajk/Nautilus/nautilus_trader/schema/sql/types.sql \
       /home/ajk/Nautilus/nautilus_trader/schema/sql/tables.sql \
       > /home/ajk/Nautilus/nautilus_trader/infrastructure/postgres/01-base-schema.sql
   ```

2. **Create AI-Adaptive extensions**

   File: `/infrastructure/postgres/02-ai-extensions.sql`
   
   ```sql
   -- ============================================
   -- AI-ADAPTIVE STRATEGY EXTENSIONS
   -- For storing AI-specific metrics beyond base Nautilus schema
   -- ============================================
   
   -- ============================================
   -- BACKTESTS TABLE (extends base schema)
   -- ============================================
   CREATE TABLE IF NOT EXISTS backtests (
       id SERIAL PRIMARY KEY,
       run_id VARCHAR(100) UNIQUE NOT NULL,
       strategy_name VARCHAR(100) NOT NULL,
       strategy_version VARCHAR(20) DEFAULT 'v1.0',
       instrument VARCHAR(50) NOT NULL,
       start_date TIMESTAMP NOT NULL,
       end_date TIMESTAMP NOT NULL,
       
       -- Capital metrics
       initial_capital DECIMAL(20,2) NOT NULL,
       final_capital DECIMAL(20,2) NOT NULL,
       total_pnl DECIMAL(20,2) NOT NULL,
       total_pnl_pct DECIMAL(10,4),
       
       -- Trading metrics
       total_trades INTEGER DEFAULT 0,
       winning_trades INTEGER DEFAULT 0,
       losing_trades INTEGER DEFAULT 0,
       win_rate DECIMAL(5,2),
       
       -- Risk metrics
       sharpe_ratio DECIMAL(10,4),
       sortino_ratio DECIMAL(10,4),
       max_drawdown DECIMAL(10,4),
       max_drawdown_pct DECIMAL(10,4),
       calmar_ratio DECIMAL(10,4),
       
       -- Other metrics
       profit_factor DECIMAL(10,4),
       avg_win DECIMAL(20,2),
       avg_loss DECIMAL(20,2),
       largest_win DECIMAL(20,2),
       largest_loss DECIMAL(20,2),
       
       -- Strategy configuration (JSONB for flexibility)
       parameters JSONB,
       
       -- Metadata
       created_at TIMESTAMP DEFAULT NOW(),
       duration_seconds INTEGER,
       data_bars_processed BIGINT,
       notes TEXT
   );
   
   CREATE INDEX idx_backtests_strategy ON backtests(strategy_name, created_at DESC);
   CREATE INDEX idx_backtests_performance ON backtests(sharpe_ratio DESC, total_pnl DESC);
   CREATE INDEX idx_backtests_created ON backtests(created_at DESC);
   
   -- ============================================
   -- ML OPTIMIZATION LOG
   -- Tracks machine learning parameter optimization
   -- ============================================
   CREATE TABLE IF NOT EXISTS ml_optimization_log (
       id BIGSERIAL PRIMARY KEY,
       backtest_id INTEGER REFERENCES backtests(id) ON DELETE CASCADE,
       timestamp BIGINT NOT NULL,  -- Unix nanoseconds (Nautilus standard)
       
       -- Current parameters
       fast_ema_period INTEGER,
       slow_ema_period INTEGER,
       trend_ema_period INTEGER,
       
       -- Optimization metrics
       gradient_descent_loss DECIMAL(10,6),
       logistic_regression_score DECIMAL(10,6),
       newton_raphson_iterations INTEGER,
       
       -- Performance snapshot at optimization time
       current_win_rate DECIMAL(5,2),
       current_sharpe DECIMAL(10,4),
       bars_since_last_optimization INTEGER,
       
       -- Metadata
       created_at TIMESTAMP DEFAULT NOW()
   );
   
   CREATE INDEX idx_ml_log_backtest ON ml_optimization_log(backtest_id, timestamp);
   
   -- ============================================
   -- MARKET REGIME DETECTION LOG
   -- Tracks detected market regimes (K-means clustering)
   -- ============================================
   CREATE TABLE IF NOT EXISTS regime_detection_log (
       id BIGSERIAL PRIMARY KEY,
       backtest_id INTEGER REFERENCES backtests(id) ON DELETE CASCADE,
       timestamp BIGINT NOT NULL,
       
       -- Regime classification
       regime VARCHAR(30) NOT NULL,  -- TRENDING_UP, TRENDING_DOWN, RANGING, VOLATILE, BREAKOUT, CONSOLIDATION
       confidence DECIMAL(5,2) NOT NULL,  -- 0-100%
       
       -- Clustering metrics
       cluster_centers JSONB,  -- K-means cluster centers
       inertia DECIMAL(10,6),  -- Clustering quality metric
       
       -- Market characteristics
       volatility DECIMAL(10,6),
       trend_strength DECIMAL(10,6),
       volume_profile DECIMAL(10,6),
       
       created_at TIMESTAMP DEFAULT NOW()
   );
   
   CREATE INDEX idx_regime_log_backtest ON regime_detection_log(backtest_id, timestamp);
   CREATE INDEX idx_regime_by_type ON regime_detection_log(regime, confidence DESC);
   
   -- ============================================
   -- PATTERN DETECTION LOG
   -- Tracks detected chart patterns
   -- ============================================
   CREATE TABLE IF NOT EXISTS pattern_detection_log (
       id BIGSERIAL PRIMARY KEY,
       backtest_id INTEGER REFERENCES backtests(id) ON DELETE CASCADE,
       timestamp BIGINT NOT NULL,
       
       -- Pattern details
       pattern_type VARCHAR(50) NOT NULL,  -- HIGHER_HIGHS, LOWER_LOWS, DOUBLE_BOTTOM, HEAD_SHOULDERS, CONSOLIDATION
       detection_method VARCHAR(50),  -- DYNAMIC_PROGRAMMING, TEMPLATE_MATCHING, LCS_SIMILARITY
       confidence DECIMAL(5,2),
       
       -- Pattern characteristics
       pattern_start_time BIGINT,
       pattern_duration INTEGER,  -- bars
       price_range DECIMAL(20,8),
       
       -- Action taken
       signal_generated BOOLEAN DEFAULT FALSE,
       trade_executed BOOLEAN DEFAULT FALSE,
       
       created_at TIMESTAMP DEFAULT NOW()
   );
   
   CREATE INDEX idx_pattern_log_backtest ON pattern_detection_log(backtest_id, timestamp);
   CREATE INDEX idx_pattern_by_type ON pattern_detection_log(pattern_type, confidence DESC);
   
   -- ============================================
   -- RISK MANAGEMENT EVENTS
   -- Tracks circuit breakers, limits, warnings
   -- ============================================
   CREATE TABLE IF NOT EXISTS risk_events (
       id BIGSERIAL PRIMARY KEY,
       backtest_id INTEGER REFERENCES backtests(id) ON DELETE CASCADE,
       timestamp BIGINT NOT NULL,
       
       -- Event type
       event_type VARCHAR(50) NOT NULL,  -- CIRCUIT_BREAKER, POSITION_LIMIT, DRAWDOWN_LIMIT, DAILY_LOSS_LIMIT
       severity VARCHAR(20) NOT NULL,  -- INFO, WARNING, CRITICAL
       
       -- Event details
       current_drawdown DECIMAL(10,4),
       current_win_rate DECIMAL(5,2),
       consecutive_losses INTEGER,
       position_size DECIMAL(20,8),
       daily_pnl DECIMAL(20,2),
       
       -- Action taken
       action VARCHAR(50),  -- TRADING_HALTED, POSITION_REDUCED, ALERT_SENT, NONE
       description TEXT,
       
       created_at TIMESTAMP DEFAULT NOW()
   );
   
   CREATE INDEX idx_risk_events_backtest ON risk_events(backtest_id, timestamp);
   CREATE INDEX idx_risk_events_severity ON risk_events(severity, event_type);
   
   -- ============================================
   -- SENTIMENT ANALYSIS LOG
   -- For Reddit/social sentiment integration
   -- ============================================
   CREATE TABLE IF NOT EXISTS sentiment_log (
       id BIGSERIAL PRIMARY KEY,
       backtest_id INTEGER REFERENCES backtests(id),
       timestamp BIGINT NOT NULL,
       
       -- Sentiment data
       symbol VARCHAR(20) NOT NULL,
       sentiment_score DECIMAL(5,2),  -- -1.0 to +1.0
       mention_count INTEGER,
       engagement_score DECIMAL(10,2),
       
       -- Sentiment categories
       bullish_keywords_count INTEGER,
       bearish_keywords_count INTEGER,
       
       -- Sources
       subreddit VARCHAR(50),
       post_count INTEGER,
       
       -- Impact on trading
       signal_weight DECIMAL(5,2),  -- How much this influenced decision (0-1)
       
       created_at TIMESTAMP DEFAULT NOW()
   );
   
   CREATE INDEX idx_sentiment_log_symbol ON sentiment_log(symbol, timestamp DESC);
   
   -- ============================================
   -- INDIVIDUAL TRADES (extends base schema)
   -- ============================================
   CREATE TABLE IF NOT EXISTS trades (
       id BIGSERIAL PRIMARY KEY,
       backtest_id INTEGER REFERENCES backtests(id) ON DELETE CASCADE,
       trade_id VARCHAR(100) NOT NULL,
       
       -- Trade details
       instrument VARCHAR(50) NOT NULL,
       side VARCHAR(10) NOT NULL,  -- BUY, SELL
       quantity DECIMAL(20,8) NOT NULL,
       
       -- Entry
       entry_price DECIMAL(20,8) NOT NULL,
       entry_time BIGINT NOT NULL,
       entry_order_id VARCHAR(100),
       entry_regime VARCHAR(30),  -- Market regime at entry
       
       -- Exit
       exit_price DECIMAL(20,8),
       exit_time BIGINT,
       exit_order_id VARCHAR(100),
       exit_reason VARCHAR(50),  -- STOP_LOSS, TAKE_PROFIT, SIGNAL, TIMEOUT, REGIME_CHANGE
       
       -- P&L
       pnl DECIMAL(20,2),
       pnl_pct DECIMAL(10,4),
       commission DECIMAL(20,2) DEFAULT 0,
       
       -- Duration
       duration_seconds INTEGER,
       duration_bars INTEGER,
       
       -- AI context
       ml_optimized BOOLEAN DEFAULT FALSE,  -- Was ML optimization active?
       pattern_detected VARCHAR(50),  -- Pattern that triggered entry (if any)
       sentiment_score DECIMAL(5,2),  -- Sentiment at entry time
       
       created_at TIMESTAMP DEFAULT NOW()
   );
   
   CREATE INDEX idx_trades_backtest ON trades(backtest_id, entry_time);
   CREATE INDEX idx_trades_performance ON trades(pnl DESC);
   CREATE INDEX idx_trades_instrument ON trades(instrument, entry_time DESC);
   
   -- ============================================
   -- PERFORMANCE METRICS TIME SERIES
   -- Equity curve and rolling metrics
   -- ============================================
   CREATE TABLE IF NOT EXISTS performance_metrics (
       id BIGSERIAL PRIMARY KEY,
       backtest_id INTEGER REFERENCES backtests(id) ON DELETE CASCADE,
       timestamp BIGINT NOT NULL,
       
       -- Equity curve
       equity DECIMAL(20,2) NOT NULL,
       cash_balance DECIMAL(20,2),
       unrealized_pnl DECIMAL(20,2) DEFAULT 0,
       
       -- Rolling metrics (calculated over recent window)
       rolling_sharpe DECIMAL(10,4),
       rolling_drawdown DECIMAL(10,4),
       rolling_win_rate DECIMAL(5,2),
       
       -- Position data
       open_positions INTEGER DEFAULT 0,
       position_value DECIMAL(20,2) DEFAULT 0,
       
       created_at TIMESTAMP DEFAULT NOW()
   );
   
   CREATE INDEX idx_performance_backtest_ts ON performance_metrics(backtest_id, timestamp);
   
   -- ============================================
   -- HELPER VIEWS
   -- ============================================
   
   -- View: Strategy Health Dashboard
   CREATE OR REPLACE VIEW v_strategy_health AS
   SELECT 
       b.id as backtest_id,
       b.run_id,
       b.strategy_name,
       b.instrument,
       b.total_pnl,
       b.win_rate,
       b.sharpe_ratio,
       b.max_drawdown,
       b.total_trades,
       
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
   
   -- View: Top Performing Strategies
   CREATE OR REPLACE VIEW v_top_strategies AS
   SELECT 
       strategy_name,
       instrument,
       COUNT(*) as total_runs,
       AVG(total_pnl) as avg_pnl,
       AVG(win_rate) as avg_win_rate,
       AVG(sharpe_ratio) as avg_sharpe,
       MAX(total_pnl) as best_pnl,
       MIN(max_drawdown) as best_drawdown
   FROM backtests
   GROUP BY strategy_name, instrument
   ORDER BY avg_sharpe DESC;
   
   -- View: Recent Backtests Summary
   CREATE OR REPLACE VIEW v_recent_backtests AS
   SELECT 
       b.id,
       b.run_id,
       b.strategy_name,
       b.instrument,
       b.total_pnl,
       b.win_rate,
       b.sharpe_ratio,
       b.max_drawdown,
       COUNT(t.id) as num_trades,
       b.created_at
   FROM backtests b
   LEFT JOIN trades t ON t.backtest_id = b.id
   GROUP BY b.id
   ORDER BY b.created_at DESC
   LIMIT 50;
   
   -- ============================================
   -- INITIAL DATA
   -- ============================================
   
   -- Success message
   DO $$
   BEGIN
       RAISE NOTICE 'AI-Adaptive Strategy schema extensions created successfully!';
       RAISE NOTICE 'Tables: backtests, ml_optimization_log, regime_detection_log, pattern_detection_log, risk_events, sentiment_log, trades, performance_metrics';
       RAISE NOTICE 'Views: v_strategy_health, v_top_strategies, v_recent_backtests';
   END $$;
   ```

3. **Verify schema creation**

   ```bash
   # Restart container to apply init scripts
   docker-compose down
   docker-compose up -d postgres
   
   # Wait for initialization
   sleep 10
   
   # Verify tables created
   docker exec -it nautilus_postgres psql -U nautilus -d nautilus_trader -c "\dt"
   
   # Verify views created
   docker exec -it nautilus_postgres psql -U nautilus -d nautilus_trader -c "\dv"
   
   # Test query
   docker exec -it nautilus_postgres psql -U nautilus -d nautilus_trader -c "SELECT COUNT(*) FROM backtests;"
   ```

**Expected Output:**
```
✅ Tables created: backtests, ml_optimization_log, regime_detection_log, pattern_detection_log, risk_events, sentiment_log, trades, performance_metrics
✅ Views created: v_strategy_health, v_top_strategies, v_recent_backtests
✅ Indexes created successfully
✅ Ready for data insertion
```

---

### Day 3-4: Python Storage Layer

**Goal:** Create Python module to save/query backtest data

**Tasks:**

1. **Create database module directory**

   ```bash
   mkdir -p /home/ajk/Nautilus/nautilus_trader/ajk_strategies/database
   touch /home/ajk/Nautilus/nautilus_trader/ajk_strategies/database/__init__.py
   ```

2. **Create PostgreSQL storage class**

   File: `/ajk_strategies/database/backtest_storage.py`
   
   ```python
   """
   PostgreSQL storage for AI-Adaptive backtest results.
   
   Saves backtest results, AI metrics (ML optimization, regime detection, 
   pattern recognition, risk events) to PostgreSQL database.
   """
   
   import psycopg2
   from psycopg2.extras import RealDictCursor, execute_batch
   import json
   from datetime import datetime
   from typing import Dict, List, Optional, Any
   import os
   from pathlib import Path
   
   
   class BacktestDatabaseStorage:
       """Stores backtest results in PostgreSQL."""
       
       def __init__(self, env_file: Optional[str] = None):
           """
           Initialize database connection.
           
           Args:
               env_file: Path to .env file with DB credentials (optional)
           """
           if env_file:
               self._load_env(env_file)
           
           self.conn = self._get_connection()
           print(f"✅ Connected to PostgreSQL database: {os.getenv('DB_NAME', 'nautilus_trader')}")
       
       def _load_env(self, env_file: str):
           """Load environment variables from file."""
           env_path = Path(env_file)
           if not env_path.exists():
               raise FileNotFoundError(f"Environment file not found: {env_file}")
           
           with open(env_path) as f:
               for line in f:
                   line = line.strip()
                   if line and not line.startswith('#') and '=' in line:
                       key, value = line.split('=', 1)
                       os.environ[key.strip()] = value.strip()
       
       def _get_connection(self):
           """Create database connection."""
           try:
               conn = psycopg2.connect(
                   host=os.getenv('DB_HOST', 'localhost'),
                   port=int(os.getenv('DB_PORT', 5432)),
                   database=os.getenv('DB_NAME', 'nautilus_trader'),
                   user=os.getenv('DB_USER', 'nautilus'),
                   password=os.getenv('DB_PASSWORD', 'changeme'),
                   cursor_factory=RealDictCursor
               )
               return conn
           except psycopg2.Error as e:
               print(f"❌ Database connection failed: {e}")
               raise
       
       def save_backtest_result(
           self,
           run_id: str,
           strategy_name: str,
           instrument: str,
           start_date: datetime,
           end_date: datetime,
           metrics: Dict[str, Any],
           parameters: Dict[str, Any]
       ) -> int:
           """
           Save backtest result to database.
           
           Args:
               run_id: Unique identifier for this backtest run
               strategy_name: Name of strategy
               instrument: Trading instrument (e.g., "BTC-USDT")
               start_date: Backtest start datetime
               end_date: Backtest end datetime
               metrics: Performance metrics dict
               parameters: Strategy parameters dict
           
           Returns:
               backtest_id: Database ID for further inserts
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
                   'strategy_version': parameters.get('version', 'v1.0'),
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
       
       def save_regime_detection(self, backtest_id: int, regime_logs: List[Dict[str, Any]]):
           """Save regime detection log entries."""
           if not regime_logs:
               return
           
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
                       'confidence': log.get('confidence', 0),
                       'cluster_centers': json.dumps(log.get('cluster_centers')),
                       'volatility': log.get('volatility'),
                       'trend_strength': log.get('trend_strength')
                   }
                   for log in regime_logs
               ]
               
               execute_batch(cur, query, data, page_size=1000)
               self.conn.commit()
               print(f"✅ Saved {len(regime_logs)} regime detection entries")
       
       def save_ml_optimization(self, backtest_id: int, ml_logs: List[Dict[str, Any]]):
           """Save ML optimization log entries."""
           if not ml_logs:
               return
           
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
               
               execute_batch(cur, query, data, page_size=1000)
               self.conn.commit()
               print(f"✅ Saved {len(ml_logs)} ML optimization entries")
       
       def save_pattern_detection(self, backtest_id: int, pattern_logs: List[Dict[str, Any]]):
           """Save pattern detection log entries."""
           if not pattern_logs:
               return
           
           with self.conn.cursor() as cur:
               query = """
                   INSERT INTO pattern_detection_log (
                       backtest_id, timestamp, pattern_type, detection_method,
                       confidence, signal_generated, trade_executed
                   ) VALUES (
                       %(backtest_id)s, %(timestamp)s, %(pattern_type)s, %(method)s,
                       %(confidence)s, %(signal_generated)s, %(trade_executed)s
                   );
               """
               
               data = [
                   {
                       'backtest_id': backtest_id,
                       'timestamp': log['timestamp'],
                       'pattern_type': log.get('pattern_type'),
                       'method': log.get('detection_method'),
                       'confidence': log.get('confidence', 0),
                       'signal_generated': log.get('signal_generated', False),
                       'trade_executed': log.get('trade_executed', False)
                   }
                   for log in pattern_logs
               ]
               
               execute_batch(cur, query, data, page_size=1000)
               self.conn.commit()
               print(f"✅ Saved {len(pattern_logs)} pattern detection entries")
       
       def save_risk_events(self, backtest_id: int, risk_logs: List[Dict[str, Any]]):
           """Save risk management events."""
           if not risk_logs:
               return
           
           with self.conn.cursor() as cur:
               query = """
                   INSERT INTO risk_events (
                       backtest_id, timestamp, event_type, severity,
                       current_drawdown, action, description
                   ) VALUES (
                       %(backtest_id)s, %(timestamp)s, %(event_type)s, %(severity)s,
                       %(drawdown)s, %(action)s, %(description)s
                   );
               """
               
               data = [
                   {
                       'backtest_id': backtest_id,
                       'timestamp': log['timestamp'],
                       'event_type': log.get('event_type'),
                       'severity': log.get('severity', 'INFO'),
                       'drawdown': log.get('current_drawdown'),
                       'action': log.get('action'),
                       'description': log.get('description', '')
                   }
                   for log in risk_logs
               ]
               
               execute_batch(cur, query, data, page_size=1000)
               self.conn.commit()
               print(f"✅ Saved {len(risk_logs)} risk events")
       
       def get_recent_backtests(self, limit: int = 10) -> List[Dict[str, Any]]:
           """Get recent backtest results."""
           with self.conn.cursor() as cur:
               cur.execute("""
                   SELECT * FROM v_recent_backtests
                   LIMIT %s
               """, (limit,))
               return cur.fetchall()
       
       def get_strategy_health(self) -> List[Dict[str, Any]]:
           """Get strategy health dashboard data."""
           with self.conn.cursor() as cur:
               cur.execute("SELECT * FROM v_strategy_health ORDER BY created_at DESC LIMIT 20")
               return cur.fetchall()
       
       def close(self):
           """Close database connection."""
           if self.conn:
               self.conn.close()
               print("✅ Database connection closed")
       
       def __enter__(self):
           """Context manager entry."""
           return self
       
       def __exit__(self, exc_type, exc_val, exc_tb):
           """Context manager exit."""
           self.close()
   ```

3. **Create query utilities**

   File: `/ajk_strategies/database/queries.py`
   
   ```python
   """
   Query utilities for analyzing backtest results.
   """
   
   from typing import List, Dict, Any, Optional
   from .backtest_storage import BacktestDatabaseStorage
   
   
   def get_best_strategies(
       min_trades: int = 10,
       min_runs: int = 3,
       limit: int = 10
   ) -> List[Dict[str, Any]]:
       """
       Get best performing strategy configurations.
       
       Args:
           min_trades: Minimum trades per backtest
           min_runs: Minimum number of backtest runs
           limit: Number of results to return
       
       Returns:
           List of top strategies with average metrics
       """
       with BacktestDatabaseStorage() as db:
           with db.conn.cursor() as cur:
               cur.execute("""
                   SELECT 
                       instrument,
                       parameters->>'fast_ema_period' as fast_ema,
                       parameters->>'slow_ema_period' as slow_ema,
                       AVG(sharpe_ratio) as avg_sharpe,
                       AVG(win_rate) as avg_win_rate,
                       AVG(total_pnl_pct) as avg_return_pct,
                       COUNT(*) as num_backtests,
                       MAX(sharpe_ratio) as best_sharpe,
                       MIN(max_drawdown_pct) as best_drawdown
                   FROM backtests
                   WHERE total_trades >= %s
                   GROUP BY instrument, fast_ema, slow_ema
                   HAVING COUNT(*) >= %s
                   ORDER BY avg_sharpe DESC
                   LIMIT %s
               """, (min_trades, min_runs, limit))
               return cur.fetchall()
   
   
   def get_regime_analysis(backtest_id: int) -> List[Dict[str, Any]]:
       """Analyze regime detection for a specific backtest."""
       with BacktestDatabaseStorage() as db:
           with db.conn.cursor() as cur:
               cur.execute("""
                   SELECT 
                       regime,
                       COUNT(*) as occurrences,
                       AVG(confidence) as avg_confidence,
                       AVG(volatility) as avg_volatility,
                       AVG(trend_strength) as avg_trend_strength
                   FROM regime_detection_log
                   WHERE backtest_id = %s
                   GROUP BY regime
                   ORDER BY occurrences DESC
               """, (backtest_id,))
               return cur.fetchall()
   
   
   def get_ml_optimization_history(backtest_id: int) -> List[Dict[str, Any]]:
       """Get ML parameter optimization history."""
       with BacktestDatabaseStorage() as db:
           with db.conn.cursor() as cur:
               cur.execute("""
                   SELECT 
                       timestamp,
                       fast_ema_period,
                       slow_ema_period,
                       gradient_descent_loss,
                       current_win_rate,
                       current_sharpe
                   FROM ml_optimization_log
                   WHERE backtest_id = %s
                   ORDER BY timestamp ASC
               """, (backtest_id,))
               return cur.fetchall()
   
   
   def get_performance_comparison(
       strategy_names: List[str],
       instrument: Optional[str] = None
   ) -> Dict[str, Any]:
       """Compare performance across multiple strategies."""
       with BacktestDatabaseStorage() as db:
           with db.conn.cursor() as cur:
               query = """
                   SELECT 
                       strategy_name,
                       COUNT(*) as num_runs,
                       AVG(total_pnl_pct) as avg_return,
                       AVG(sharpe_ratio) as avg_sharpe,
                       AVG(win_rate) as avg_win_rate,
                       AVG(max_drawdown_pct) as avg_max_drawdown,
                       MAX(total_pnl_pct) as best_return,
                       MIN(total_pnl_pct) as worst_return
                   FROM backtests
                   WHERE strategy_name = ANY(%s)
               """
               
               params = [strategy_names]
               
               if instrument:
                   query += " AND instrument = %s"
                   params.append(instrument)
               
               query += " GROUP BY strategy_name ORDER BY avg_sharpe DESC"
               
               cur.execute(query, params)
               return cur.fetchall()
   ```

4. **Test database storage**

   Create test file: `/ajk_strategies/database/test_storage.py`
   
   ```python
   """Test database storage functionality."""
   
   from datetime import datetime, timedelta
   from backtest_storage import BacktestDatabaseStorage
   
   
   def test_save_backtest():
       """Test saving a backtest result."""
       
       # Create storage instance
       env_file = "/home/ajk/Nautilus/nautilus_trader/infrastructure/.env.local"
       db = BacktestDatabaseStorage(env_file=env_file)
       
       # Sample data
       run_id = f"test_run_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
       strategy_name = "AI-Adaptive-Strategy-Test"
       instrument = "BTC-USDT"
       start_date = datetime.now() - timedelta(days=365)
       end_date = datetime.now()
       
       metrics = {
           'initial_capital': 100000,
           'final_capital': 125000,
           'total_pnl': 25000,
           'pnl_pct': 25.0,
           'total_trades': 50,
           'winning_trades': 30,
           'losing_trades': 20,
           'win_rate': 60.0,
           'sharpe_ratio': 2.5,
           'max_drawdown': 8.5,
           'max_drawdown_pct': 8.5,
           'profit_factor': 2.0,
           'bars_processed': 525600,
           'duration_seconds': 120
       }
       
       parameters = {
           'fast_ema_period': 8,
           'slow_ema_period': 21,
           'trend_ema_period': 50,
           'stop_loss_atr': 2.0,
           'take_profit_atr': 3.0
       }
       
       # Save to database
       backtest_id = db.save_backtest_result(
           run_id=run_id,
           strategy_name=strategy_name,
           instrument=instrument,
           start_date=start_date,
           end_date=end_date,
           metrics=metrics,
           parameters=parameters
       )
       
       print(f"\n✅ Test passed! Backtest ID: {backtest_id}")
       
       # Test regime logs
       regime_logs = [
           {
               'timestamp': int(datetime.now().timestamp() * 1e9),
               'regime': 'TRENDING_UP',
               'confidence': 85.5,
               'cluster_centers': {'k0': [1.5, 2.0], 'k1': [0.5, 1.0]},
               'volatility': 0.025,
               'trend_strength': 0.75
           }
       ]
       db.save_regime_detection(backtest_id, regime_logs)
       
       # Query recent backtests
       recent = db.get_recent_backtests(limit=5)
       print(f"\n✅ Recent backtests: {len(recent)} found")
       for bt in recent:
           print(f"  - {bt['strategy_name']} on {bt['instrument']}: {bt['total_pnl']} PnL")
       
       # Close connection
       db.close()
       
       print("\n✅ All tests passed!")
   
   
   if __name__ == "__main__":
       test_save_backtest()
   ```

   **Run test:**
   ```bash
   cd /home/ajk/Nautilus/nautilus_trader/ajk_strategies/database
   python3 test_storage.py
   ```

**Expected Output:**
```
✅ Connected to PostgreSQL database: nautilus_trader
✅ Saved backtest result to database (ID: 1)
✅ Saved 1 regime detection entries
✅ Recent backtests: 1 found
  - AI-Adaptive-Strategy-Test on BTC-USDT: 25000.00 PnL
✅ Database connection closed
✅ All tests passed!
```

---

### Day 5: Integration with Backtest Runner

**Goal:** Modify existing backtest runner to save to PostgreSQL

**Tasks:**

1. **Update backtest runner imports**

   Add to `/ajk_strategies/run_backtest_with_real_data.py` (top of file):
   
   ```python
   # Add after existing imports
   from database.backtest_storage import BacktestDatabaseStorage
   ```

2. **Add database saving logic**

   Find the section where results are saved to CSV (around line 450+) and add:
   
   ```python
   # After calculating all metrics and before CSV export:
   
   # ========================================
   # SAVE TO DATABASE
   # ========================================
   print("\n" + "="*60)
   print("SAVING TO DATABASE")
   print("="*60)
   
   try:
       # Initialize database storage
       env_file = "/home/ajk/Nautilus/nautilus_trader/infrastructure/.env.local"
       db = BacktestDatabaseStorage(env_file=env_file)
       
       # Prepare metrics dictionary
       metrics = {
           'initial_capital': starting_usdt,
           'final_capital': total_equity,
           'total_pnl': pnl,
           'pnl_pct': pnl_pct,
           'total_trades': len(closed_positions),
           'winning_trades': len([p for p in closed_positions if p.realized_pnl > 0]) if closed_positions else 0,
           'losing_trades': len([p for p in closed_positions if p.realized_pnl <= 0]) if closed_positions else 0,
           'win_rate': win_rate if 'win_rate' in locals() else 0,
           'sharpe_ratio': sharpe_ratio if 'sharpe_ratio' in locals() else None,
           'max_drawdown': max_drawdown if 'max_drawdown' in locals() else None,
           'max_drawdown_pct': max_drawdown_pct if 'max_drawdown_pct' in locals() else None,
           'profit_factor': profit_factor if 'profit_factor' in locals() else None,
           'avg_win': avg_win if 'avg_win' in locals() else None,
           'avg_loss': avg_loss if 'avg_loss' in locals() else None,
           'bars_processed': len(bars),
           'duration_seconds': int(duration)
       }
       
       # Prepare parameters dictionary
       parameters = {
           'fast_ema_period': strategy_config.fast_ema_period,
           'slow_ema_period': strategy_config.slow_ema_period,
           'atr_period': strategy_config.atr_period,
           'stop_loss_atr': strategy_config.stop_loss_atr,
           'take_profit_atr': strategy_config.take_profit_atr,
           'trade_size': strategy_config.trade_size,
           'max_trades': strategy_config.max_trades
       }
       
       # Save main backtest result
       backtest_id = db.save_backtest_result(
           run_id=timestamp,
           strategy_name=f"AI-Adaptive-{instrument_symbol}",
           instrument=instrument_symbol,
           start_date=datetime.fromtimestamp(start_time / 1e9),
           end_date=datetime.fromtimestamp(end_time / 1e9),
           metrics=metrics,
           parameters=parameters
       )
       
       print(f"✅ Backtest result saved to database (ID: {backtest_id})")
       
       # Save AI-specific logs if strategy tracks them
       if hasattr(strategy, 'regime_history') and strategy.regime_history:
           db.save_regime_detection(backtest_id, strategy.regime_history)
       
       if hasattr(strategy, 'ml_optimization_history') and strategy.ml_optimization_history:
           db.save_ml_optimization(backtest_id, strategy.ml_optimization_history)
       
       if hasattr(strategy, 'pattern_history') and strategy.pattern_history:
           db.save_pattern_detection(backtest_id, strategy.pattern_history)
       
       if hasattr(strategy, 'risk_events') and strategy.risk_events:
           db.save_risk_events(backtest_id, strategy.risk_events)
       
       # Close database connection
       db.close()
       
       print("✅ All data saved to PostgreSQL successfully!")
       
   except Exception as e:
       print(f"⚠️ Failed to save to database: {e}")
       print("Continuing with CSV export as backup...")
   
   # Continue with existing CSV export logic...
   ```

3. **Test integrated backtest**

   ```bash
   cd /home/ajk/Nautilus/nautilus_trader
   python3 ajk_strategies/run_backtest_with_real_data.py
   ```

4. **Verify data in database**

   ```bash
   # Query database
   docker exec -it nautilus_postgres psql -U nautilus -d nautilus_trader -c "
   SELECT 
       id, run_id, strategy_name, instrument, 
       total_pnl, win_rate, sharpe_ratio, total_trades, created_at 
   FROM backtests 
   ORDER BY created_at DESC 
   LIMIT 5;"
   
   # Check strategy health view
   docker exec -it nautilus_postgres psql -U nautilus -d nautilus_trader -c "
   SELECT * FROM v_strategy_health LIMIT 5;"
   ```

**Expected Output:**
```
✅ Backtest completed in 45.23 seconds
✅ Backtest result saved to database (ID: 2)
✅ Saved 234 regime detection entries
✅ Saved 15 ML optimization entries
✅ All data saved to PostgreSQL successfully!
✅ CSV files saved as backup
```

---

## 📅 Week 2: Redis + Monitoring

### Day 6: Redis Deployment

**Goal:** Deploy Redis for caching strategy state and ML models

**Tasks:**

1. **Add Redis to docker-compose**

   Update `/infrastructure/docker/docker-compose.yml`:
   
   ```yaml
   services:
     # ... existing postgres service ...
     
     redis:
       image: redis:7-alpine
       container_name: nautilus_redis
       command: redis-server --requirepass ${REDIS_PASSWORD:-changeme123}
       ports:
         - "6379:6379"
       volumes:
         - redis_data:/data
       healthcheck:
         test: ["CMD", "redis-cli", "--raw", "incr", "ping"]
         interval: 10s
         timeout: 3s
         retries: 5
       restart: unless-stopped
   
   volumes:
     postgres_data:
       driver: local
     redis_data:
       driver: local
   ```

2. **Start Redis**

   ```bash
   cd /home/ajk/Nautilus/nautilus_trader/infrastructure/docker
   docker-compose up -d redis
   
   # Test connection
   docker exec -it nautilus_redis redis-cli -a changeme123 ping
   # Expected: PONG
   ```

3. **Create Redis cache manager**

   File: `/ajk_strategies/cache/redis_manager.py`
   
   ```python
   """Redis cache manager for AI-Adaptive strategy."""
   
   import redis
   import json
   import pickle
   from typing import Any, Optional, Dict
   import os
   import time
   
   
   class StrategyCache:
       """Redis cache for strategy state and ML models."""
       
       def __init__(self, env_file: Optional[str] = None):
           """Initialize Redis connection."""
           if env_file:
               self._load_env(env_file)
           
           self.client = redis.Redis(
               host=os.getenv('REDIS_HOST', 'localhost'),
               port=int(os.getenv('REDIS_PORT', 6379)),
               password=os.getenv('REDIS_PASSWORD', 'changeme'),
               db=0,
               decode_responses=False  # For pickle support
           )
           
           # Test connection
           self.client.ping()
           print(f"✅ Connected to Redis: {os.getenv('REDIS_HOST', 'localhost')}:6379")
       
       def _load_env(self, env_file: str):
           """Load environment variables from file."""
           with open(env_file) as f:
               for line in f:
                   line = line.strip()
                   if line and not line.startswith('#') and '=' in line:
                       key, value = line.split('=', 1)
                       os.environ[key.strip()] = value.strip()
       
       # Strategy State Management
       def save_strategy_state(self, strategy_id: str, state: Dict[str, Any], ttl: int = 3600):
           """
           Save strategy state (positions, parameters, etc.)
           
           Args:
               strategy_id: Unique strategy identifier
               state: State dictionary
               ttl: Time to live in seconds
           """
           key = f"strategy:{strategy_id}:state"
           self.client.setex(key, ttl, json.dumps(state))
       
       def get_strategy_state(self, strategy_id: str) -> Optional[Dict[str, Any]]:
           """Get strategy state."""
           key = f"strategy:{strategy_id}:state"
           data = self.client.get(key)
           return json.loads(data) if data else None
       
       # ML Model Checkpoints
       def save_ml_model(self, strategy_id: str, model: Any, version: str = "latest"):
           """
           Save ML model checkpoint (pickled).
           
           Args:
               strategy_id: Strategy identifier
               model: ML model object (any picklable object)
               version: Model version tag
           """
           key = f"ml_model:{strategy_id}:{version}"
           self.client.set(key, pickle.dumps(model))
           print(f"✅ Saved ML model: {key}")
       
       def load_ml_model(self, strategy_id: str, version: str = "latest") -> Optional[Any]:
           """Load ML model checkpoint."""
           key = f"ml_model:{strategy_id}:{version}"
           data = self.client.get(key)
           return pickle.loads(data) if data else None
       
       # Regime Detection Cache
       def cache_current_regime(self, instrument: str, regime: str, confidence: float, ttl: int = 300):
           """
           Cache current market regime.
           
           Args:
               instrument: Trading instrument
               regime: Detected regime (e.g., "TRENDING_UP")
               confidence: Confidence score (0-100)
               ttl: Time to live in seconds
           """
           key = f"regime:{instrument}:current"
           data = {
               'regime': regime,
               'confidence': confidence,
               'timestamp': int(time.time() * 1e9)
           }
           self.client.setex(key, ttl, json.dumps(data))
       
       def get_current_regime(self, instrument: str) -> Optional[Dict[str, Any]]:
           """Get cached regime."""
           key = f"regime:{instrument}:current"
           data = self.client.get(key)
           return json.loads(data) if data else None
       
       # Market Data Cache
       def cache_bar(self, instrument: str, timeframe: str, bar_data: Dict[str, Any], ttl: int = 60):
           """
           Cache latest bar data.
           
           Args:
               instrument: Trading instrument
               timeframe: Bar timeframe (e.g., "1H")
               bar_data: Bar data dict (open, high, low, close, volume, timestamp)
               ttl: Time to live in seconds
           """
           key = f"market:{instrument}:{timeframe}:latest_bar"
           self.client.setex(key, ttl, json.dumps(bar_data))
       
       def get_cached_bar(self, instrument: str, timeframe: str) -> Optional[Dict[str, Any]]:
           """Get cached bar data."""
           key = f"market:{instrument}:{timeframe}:latest_bar"
           data = self.client.get(key)
           return json.loads(data) if data else None
       
       # Performance Metrics Cache
       def cache_performance(self, strategy_id: str, metrics: Dict[str, Any], ttl: int = 60):
           """Cache current performance metrics."""
           key = f"performance:{strategy_id}:current"
           self.client.setex(key, ttl, json.dumps(metrics))
       
       def get_cached_performance(self, strategy_id: str) -> Optional[Dict[str, Any]]:
           """Get cached performance metrics."""
           key = f"performance:{strategy_id}:current"
           data = self.client.get(key)
           return json.loads(data) if data else None
       
       # Utility Methods
       def clear_strategy_cache(self, strategy_id: str):
           """Clear all cache for a strategy."""
           pattern = f"*{strategy_id}*"
           keys = self.client.keys(pattern)
           if keys:
               self.client.delete(*keys)
               print(f"✅ Cleared {len(keys)} cache entries for {strategy_id}")
       
       def get_cache_stats(self) -> Dict[str, Any]:
           """Get Redis cache statistics."""
           info = self.client.info()
           return {
               'used_memory_human': info['used_memory_human'],
               'total_keys': self.client.dbsize(),
               'connected_clients': info['connected_clients'],
               'uptime_days': info['uptime_in_days']
           }
       
       def close(self):
           """Close Redis connection."""
           self.client.close()
           print("✅ Redis connection closed")
   ```

4. **Test Redis caching**

   Create: `/ajk_strategies/cache/test_redis.py`
   
   ```python
   """Test Redis caching functionality."""
   
   from redis_manager import StrategyCache
   import time
   
   
   def test_redis():
       """Test Redis cache operations."""
       
       env_file = "/home/ajk/Nautilus/nautilus_trader/infrastructure/.env.local"
       cache = StrategyCache(env_file=env_file)
       
       # Test strategy state
       print("\n1. Testing strategy state...")
       state = {
           'position': 'LONG',
           'quantity': 0.5,
           'entry_price': 50000.0,
           'stop_loss': 49000.0
       }
       cache.save_strategy_state('test-strategy-001', state, ttl=60)
       retrieved = cache.get_strategy_state('test-strategy-001')
       assert retrieved == state
       print(f"   ✅ State saved and retrieved: {retrieved}")
       
       # Test regime caching
       print("\n2. Testing regime caching...")
       cache.cache_current_regime('BTC-USDT', 'TRENDING_UP', 85.5, ttl=30)
       regime = cache.get_current_regime('BTC-USDT')
       print(f"   ✅ Regime cached: {regime}")
       
       # Test performance caching
       print("\n3. Testing performance caching...")
       metrics = {
           'pnl': 2500.0,
           'win_rate': 65.5,
           'sharpe': 2.3,
           'trades': 25
       }
       cache.cache_performance('test-strategy-001', metrics, ttl=60)
       perf = cache.get_cached_performance('test-strategy-001')
       print(f"   ✅ Performance cached: {perf}")
       
       # Test ML model (simple dict as example)
       print("\n4. Testing ML model caching...")
       model = {'weights': [0.5, 0.3, 0.2], 'bias': 0.1}
       cache.save_ml_model('test-strategy-001', model, version='v1.0')
       loaded_model = cache.load_ml_model('test-strategy-001', version='v1.0')
       assert loaded_model == model
       print(f"   ✅ ML model saved and loaded: {loaded_model}")
       
       # Get cache stats
       print("\n5. Cache statistics:")
       stats = cache.get_cache_stats()
       for key, value in stats.items():
           print(f"   {key}: {value}")
       
       # Cleanup
       cache.clear_strategy_cache('test-strategy-001')
       cache.close()
       
       print("\n✅ All Redis tests passed!")
   
   
   if __name__ == "__main__":
       test_redis()
   ```

   ```bash
   cd /home/ajk/Nautilus/nautilus_trader/ajk_strategies/cache
   python3 test_redis.py
   ```

**Expected Output:**
```
✅ Connected to Redis: localhost:6379
✅ State saved and retrieved: {'position': 'LONG', ...}
✅ Regime cached: {'regime': 'TRENDING_UP', 'confidence': 85.5, ...}
✅ Performance cached: {'pnl': 2500.0, ...}
✅ ML model saved and loaded: {'weights': [...], ...}
✅ Cleared 5 cache entries for test-strategy-001
✅ All Redis tests passed!
```

---

### Day 7-8: Prometheus + Grafana Monitoring

**Goal:** Deploy monitoring stack with AI-specific dashboards

**Tasks:**

1. **Add monitoring services to docker-compose**

   Update `/infrastructure/docker/docker-compose.yml`:
   
   ```yaml
   services:
     # ... existing postgres and redis services ...
     
     prometheus:
       image: prom/prometheus:latest
       container_name: nautilus_prometheus
       ports:
         - "9090:9090"
       volumes:
         - ./monitoring/prometheus.yml:/etc/prometheus/prometheus.yml
         - prometheus_data:/prometheus
       command:
         - '--config.file=/etc/prometheus/prometheus.yml'
         - '--storage.tsdb.path=/prometheus'
         - '--storage.tsdb.retention.time=30d'
       restart: unless-stopped
     
     grafana:
       image: grafana/grafana:latest
       container_name: nautilus_grafana
       ports:
         - "3000:3000"
       environment:
         - GF_SECURITY_ADMIN_USER=${GRAFANA_USER:-admin}
         - GF_SECURITY_ADMIN_PASSWORD=${GRAFANA_PASSWORD:-admin}
         - GF_INSTALL_PLUGINS=redis-datasource,postgres-datasource
       volumes:
         - grafana_data:/var/lib/grafana
         - ./monitoring/grafana/dashboards:/etc/grafana/provisioning/dashboards
         - ./monitoring/grafana/datasources:/etc/grafana/provisioning/datasources
       depends_on:
         - prometheus
         - postgres
       restart: unless-stopped
   
   volumes:
     postgres_data:
     redis_data:
     prometheus_data:
     grafana_data:
   ```

2. **Create Prometheus configuration**

   File: `/infrastructure/monitoring/prometheus.yml`
   
   ```yaml
   global:
     scrape_interval: 15s
     evaluation_interval: 15s
   
   scrape_configs:
     - job_name: 'nautilus_trader'
       static_configs:
         - targets: ['host.docker.internal:8000']
       metrics_path: '/metrics'
       scrape_interval: 10s
   ```

3. **Create Grafana datasource provisioning**

   File: `/infrastructure/monitoring/grafana/datasources/postgres.yml`
   
   ```yaml
   apiVersion: 1
   
   datasources:
     - name: PostgreSQL
       type: postgres
       url: postgres:5432
       database: nautilus_trader
       user: nautilus
       secureJsonData:
         password: ${DB_PASSWORD}
       jsonData:
         sslmode: disable
         postgresVersion: 1600
         timescaledb: false
   ```

4. **Create AI-Adaptive dashboard JSON**

   File: `/infrastructure/monitoring/grafana/dashboards/ai_adaptive_dashboard.json`
   
   ```json
   {
     "dashboard": {
       "title": "AI-Adaptive Strategy Performance",
       "panels": [
         {
           "id": 1,
           "title": "Total P&L",
           "type": "stat",
           "targets": [
             {
               "rawSql": "SELECT SUM(total_pnl) FROM backtests WHERE created_at >= NOW() - INTERVAL '7 days'"
             }
           ]
         },
         {
           "id": 2,
           "title": "Win Rate Trend",
           "type": "timeseries",
           "targets": [
             {
               "rawSql": "SELECT created_at AS time, win_rate FROM backtests ORDER BY created_at"
             }
           ]
         },
         {
           "id": 3,
           "title": "Sharpe Ratio Distribution",
           "type": "histogram",
           "targets": [
             {
               "rawSql": "SELECT sharpe_ratio FROM backtests WHERE sharpe_ratio IS NOT NULL"
             }
           ]
         },
         {
           "id": 4,
           "title": "Regime Distribution",
           "type": "piechart",
           "targets": [
             {
               "rawSql": "SELECT regime, COUNT(*) FROM regime_detection_log GROUP BY regime"
             }
           ]
         }
       ]
     }
   }
   ```

5. **Start monitoring stack**

   ```bash
   cd /home/ajk/Nautilus/nautilus_trader/infrastructure/docker
   docker-compose up -d prometheus grafana
   
   # Wait for startup
   sleep 10
   
   # Access Grafana
   echo "Grafana: http://localhost:3000"
   echo "Username: admin"
   echo "Password: (from .env.local)"
   ```

6. **Configure Grafana dashboards manually**

   Open browser to http://localhost:3000:
   
   - Login with admin credentials
   - Go to Dashboards → Import
   - Upload `/infrastructure/monitoring/grafana/dashboards/ai_adaptive_dashboard.json`
   - Configure PostgreSQL datasource
   - Explore metrics

**Expected Output:**
```
✅ Prometheus running on port 9090
✅ Grafana running on port 3000
✅ PostgreSQL datasource configured
✅ AI-Adaptive dashboard loaded
```

---

## 🧪 Testing & Validation

### End-to-End Test Checklist

```bash
# 1. Verify all containers running
docker-compose ps
# Expected: postgres, redis, prometheus, grafana (all UP)

# 2. Test database connection
docker exec -it nautilus_postgres psql -U nautilus -d nautilus_trader -c "SELECT COUNT(*) FROM backtests;"

# 3. Test Redis connection
docker exec -it nautilus_redis redis-cli -a ${REDIS_PASSWORD} ping

# 4. Run backtest and save to database
cd /home/ajk/Nautilus/nautilus_trader
python3 ajk_strategies/run_backtest_with_real_data.py

# 5. Query saved results
docker exec -it nautilus_postgres psql -U nautilus -d nautilus_trader -c "
SELECT * FROM v_strategy_health ORDER BY created_at DESC LIMIT 5;"

# 6. Test Redis cache
cd ajk_strategies/cache
python3 test_redis.py

# 7. Access Grafana
xdg-open http://localhost:3000  # or manually open in browser

# 8. Check Prometheus metrics
curl http://localhost:9090/api/v1/targets
```

---

## 📊 Success Metrics

### Week 1 Completion Checklist
- [ ] PostgreSQL container running and accessible
- [ ] Base + AI-extension schemas created and verified
- [ ] Python storage module (`backtest_storage.py`) created and tested
- [ ] Backtest runner integrated with database saving
- [ ] At least 1 successful end-to-end backtest saved to PostgreSQL
- [ ] Query utilities working (can retrieve and analyze results)

### Week 2 Completion Checklist
- [ ] Redis container running and accessible
- [ ] Redis cache manager (`redis_manager.py`) created and tested
- [ ] Strategy state caching functional
- [ ] Prometheus + Grafana deployed
- [ ] PostgreSQL datasource configured in Grafana
- [ ] At least 1 dashboard created and displaying data
- [ ] All 4 services (PostgreSQL, Redis, Prometheus, Grafana) healthy

### Final Validation
- [ ] Can run backtest and see results in PostgreSQL within 1 minute
- [ ] Can query best strategies using SQL
- [ ] Can view regime analysis for specific backtest
- [ ] Redis cache hit rate > 90% for regime queries
- [ ] Grafana dashboards update within 30 seconds
- [ ] Full stack survives container restart (`docker-compose restart`)
- [ ] CSV export still works as backup

---

## 🔧 Troubleshooting

### PostgreSQL Issues

**Problem:** Container won't start
```bash
# Check logs
docker-compose logs postgres

# Common fix: Remove existing data volume
docker-compose down
docker volume rm docker_postgres_data
docker-compose up -d postgres
```

**Problem:** Schema not created
```bash
# Manually run schema scripts
docker exec -i nautilus_postgres psql -U nautilus -d nautilus_trader < /home/ajk/Nautilus/nautilus_trader/infrastructure/postgres/02-ai-extensions.sql
```

**Problem:** Connection refused from Python
```bash
# Check container network
docker network inspect docker_default

# Verify .env.local settings
cat /home/ajk/Nautilus/nautilus_trader/infrastructure/.env.local
```

### Redis Issues

**Problem:** Auth failed
```bash
# Test with correct password
docker exec -it nautilus_redis redis-cli -a $(grep REDIS_PASSWORD infrastructure/.env.local | cut -d'=' -f2) ping
```

**Problem:** Out of memory
```bash
# Check Redis memory usage
docker exec -it nautilus_redis redis-cli -a ${REDIS_PASSWORD} INFO memory

# Clear all keys (CAUTION)
docker exec -it nautilus_redis redis-cli -a ${REDIS_PASSWORD} FLUSHALL
```

### Grafana Issues

**Problem:** Can't login
```bash
# Reset admin password
docker exec -it nautilus_grafana grafana-cli admin reset-admin-password newpassword
```

**Problem:** PostgreSQL datasource connection failed
```bash
# Verify from inside Grafana container
docker exec -it nautilus_grafana ping postgres
```

---

## 📚 Reference Documentation

### Related Files
- `/infrastructure/INFRASTRUCTURE_PLAN.md` - Original comprehensive plan
- `/ai-working/database_Infra layer/AI_ADAPTIVE_INFRASTRUCTURE_PLAN.md` - AI-specific plan
- `/ai-working/database_Infra layer/compaction.md` - Status document
- `/ai-working/learning path/SESSION_SUMMARY.md` - Previous session notes
- `/schema/sql/tables.sql` - Base Nautilus schema
- `/crates/infrastructure/README.md` - Rust infrastructure docs

### Nautilus Infrastructure
- **Rust Crate**: `/crates/infrastructure/`
  - SQL cache implementation: `src/sql/cache.rs`
  - Redis cache implementation: `src/redis/cache.rs`
  - Python bindings: `src/python/`
- **Schema**: `/schema/sql/`
  - Types: `types.sql`
  - Tables: `tables.sql`
  - Functions: `functions.sql`
  - Partitions: `partitions.sql`

### External Resources
- [PostgreSQL Docker Hub](https://hub.docker.com/_/postgres)
- [Redis Docker Hub](https://hub.docker.com/_/redis)
- [Grafana Documentation](https://grafana.com/docs/)
- [Prometheus Documentation](https://prometheus.io/docs/)
- [Nautilus Trader Docs](https://nautilustrader.io/docs/)

---

## 🚀 Next Steps After Completion

### Phase 3: Live Trading Infrastructure (Future)
1. **Real-time Data Feeds**
   - WebSocket connections to exchanges
   - Redis Pub/Sub for real-time updates
   - Order book streaming

2. **Production Deployment**
   - Kubernetes orchestration
   - Load balancing
   - Auto-scaling
   - Disaster recovery

3. **Advanced Monitoring**
   - Alert rules for critical events
   - Slack/Email notifications
   - Performance optimization
   - Cost tracking

### Phase 4: Multi-Strategy Portfolio (Future)
1. **Strategy Management**
   - Multiple strategies in parallel
   - Portfolio allocation
   - Correlation analysis
   - Risk aggregation

2. **Backtesting at Scale**
   - Distributed backtesting
   - GPU acceleration
   - Walk-forward optimization automation
   - Parameter grid search

---

## 📝 Notes & Considerations

### Security
- **Never commit `.env.local`** - Add to `.gitignore`
- Change all default passwords before production
- Use strong passwords (20+ characters, mixed case, numbers, symbols)
- Consider using Docker secrets for production
- Implement API key rotation for exchanges
- Enable PostgreSQL SSL in production

### Performance
- PostgreSQL: Use partitioning for large datasets (>1M rows)
- Redis: Monitor memory usage, set `maxmemory` policy
- Prometheus: Adjust retention based on disk space
- Grafana: Limit dashboard query complexity

### Backup Strategy
- PostgreSQL: Daily automated backups (`pg_dump`)
- Redis: AOF + RDB persistence enabled
- Grafana: Export dashboards as JSON
- Code: Git repository with proper branching

### Scalability
- Current setup supports: ~1000 backtests/day, ~10 concurrent strategies
- For higher scale: Consider PostgreSQL read replicas
- For distributed: Consider Kafka for message bus
- For analytics: Consider TimescaleDB extension

---

## ✅ Completion Criteria

This plan is considered complete when:

1. ✅ All 4 services (PostgreSQL, Redis, Prometheus, Grafana) running
2. ✅ Can run backtest and see results in database within 1 minute
3. ✅ Can view strategy health dashboard in Grafana
4. ✅ Can query regime analysis, ML optimization history
5. ✅ Redis caching operational (>90% hit rate)
6. ✅ CSV export still works as backup
7. ✅ Full system survives restart
8. ✅ Documentation complete and tested

---

**Status:** Ready for Implementation  
**Estimated Time:** 2 weeks (12-16 hours total)  
**Priority:** High - Critical for production deployment  
**Risk Level:** Low - Non-destructive, incremental implementation  
**Dependencies:** Docker, Python packages (psycopg2, redis-py)

**Last Updated:** January 2025  
**Next Review:** After Week 1 completion
