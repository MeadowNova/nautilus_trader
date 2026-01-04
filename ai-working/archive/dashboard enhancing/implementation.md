# AI-Adaptive Dashboard Enhancement - Implementation Guide

**Created:** October 7, 2025  
**Version:** 1.0  
**Based on:** `plan.md` and `research/analysis.md`  
**Prerequisites:** Docker, Python 3.10+, PostgreSQL, Redis, Prometheus, Grafana (all deployed)

---

## Quick Start

```bash
# Clone and navigate
cd /home/ajk/Nautilus/nautilus_trader

# Verify infrastructure is running
docker-compose ps

# Should show: postgres, redis (both healthy)

# Apply database schema
docker exec nautilus_postgres psql -U nautilus -d nautilus_trader < infrastructure/postgres/03-backtest-schema.sql
docker exec nautilus_postgres psql -U nautilus -d nautilus_trader < infrastructure/postgres/04-dashboard-views.sql

# Install Python dependencies
source activate_env.sh
pip install prometheus_client psycopg2-binary redis

# Start metrics server
python ajk_strategies/monitoring/metrics_server.py &

# Access services
# Grafana: http://localhost:3000 (admin/your_password)
# Prometheus: http://localhost:9090
# Metrics: http://localhost:8000/metrics
```

---

## Model Artefact Telemetry (2025-10-07 Refresh)

- Production ML bundle (`ajk_strategies/models/`) now tracked as part of Phase 5 KPIs.
  - HMM (`market_regime_hmm.pkl`) — 2,262,971 rows; state counts `[57,896, 1,011,601, 1, 1,193,472, 1]`.
  - LSTM (`price_forecast_lstm.h5` + `price_forecast_lstm_meta.pkl`) — validation MSE ≈ 0.83754 (epoch 5).
  - XGBoost (`signal_aggregator_xgb.pkl`) — class distribution `[629,103, 819,741, 814,091]`.
- Integrity hashes captured via `sha256sum ajk_strategies/models/*` on 2025-10-07:
  - `30cc229f62a8c03f0bbd4d4176f84fc51e5d55a5050708fcc48c1f15544a9afc` (HMM)
  - `7ebe9a9d729afc337b483bae360055801e85824e7ecf5a605f8168fdea18a460` (LSTM)
  - `0cc837add39da846d9d108d85af4ff9b93e3db3c7d6bc824ddd5835ff85cda50` (LSTM meta)
  - `5789e06b0b5d77432f58dac9c42b0a5b8fa44e2d3e198216968fc3b5d02e77d2` (XGB)
- Monitoring backlog: extend Prometheus exporter with `model_artifact_info` and `model_validation_metrics` gauges so Grafana can surface freshness/quality panels.

---

## Phase 1: Database Schema - Complete Code

### File 1: `infrastructure/postgres/03-backtest-schema.sql`

```sql
-- ============================================================
-- NAUTILUS TRADER AI-ADAPTIVE BACKTEST SCHEMA
-- Version: 1.0
-- Created: 2025-10-07
-- ============================================================

\echo 'Creating AI-adaptive backtest schema...'

-- Enable extensions
CREATE EXTENSION IF NOT EXISTS pgcrypto;

-- ============================================================
-- TABLE: backtests
-- Main backtest results table
-- ============================================================

CREATE TABLE IF NOT EXISTS backtests (
    -- Primary Key
    id SERIAL PRIMARY KEY,
    run_id TEXT UNIQUE NOT NULL,
    
    -- Strategy Info
    strategy_name TEXT NOT NULL,
    strategy_version TEXT DEFAULT '1.0',
    instrument TEXT NOT NULL,
    
    -- Timeframe
    start_date TIMESTAMPTZ NOT NULL,
    end_date TIMESTAMPTZ NOT NULL,
    
    -- Capital & P&L
    initial_capital NUMERIC(20,2) NOT NULL,
    final_capital NUMERIC(20,2) NOT NULL,
    total_pnl NUMERIC(20,2) NOT NULL,
    total_pnl_pct NUMERIC(10,4) NOT NULL,
    
    -- Trade Statistics
    total_trades INTEGER NOT NULL DEFAULT 0,
    winning_trades INTEGER NOT NULL DEFAULT 0,
    losing_trades INTEGER NOT NULL DEFAULT 0,
    win_rate NUMERIC(5,2) NOT NULL DEFAULT 0.0,
    
    -- Risk Metrics
    sharpe_ratio NUMERIC(10,4),
    sortino_ratio NUMERIC(10,4),
    max_drawdown NUMERIC(20,2),
    max_drawdown_pct NUMERIC(10,4),
    
    -- Execution Metrics
    profit_factor NUMERIC(10,4),
    avg_win NUMERIC(20,2),
    avg_loss NUMERIC(20,2),
    avg_trade_duration INTEGER,  -- seconds
    
    -- Configuration (JSON)
    parameters JSONB,
    
    -- Performance Tracking
    data_bars_processed INTEGER DEFAULT 0,
    duration_seconds NUMERIC(10,2),
    
    -- Metadata
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    notes TEXT
);

-- Indexes for backtests
CREATE INDEX IF NOT EXISTS idx_backtests_run_id ON backtests(run_id);
CREATE INDEX IF NOT EXISTS idx_backtests_instrument ON backtests(instrument);
CREATE INDEX IF NOT EXISTS idx_backtests_created ON backtests(created_at DESC);
CREATE INDEX IF NOT EXISTS idx_backtests_sharpe ON backtests(sharpe_ratio DESC NULLS LAST);
CREATE INDEX IF NOT EXISTS idx_backtests_strategy_name ON backtests(strategy_name);
CREATE INDEX IF NOT EXISTS idx_backtests_win_rate ON backtests(win_rate DESC);

\echo '✓ backtests table created'

-- ============================================================
-- TABLE: trades
-- Individual trade execution records
-- ============================================================

CREATE TABLE IF NOT EXISTS trades (
    -- Primary Key
    id SERIAL PRIMARY KEY,
    backtest_id INTEGER NOT NULL REFERENCES backtests(id) ON DELETE CASCADE,
    
    -- Trade Identification
    trade_id TEXT NOT NULL,
    instrument TEXT NOT NULL,
    side TEXT NOT NULL CHECK (side IN ('BUY', 'SELL', 'LONG', 'SHORT')),
    
    -- Entry Details
    entry_time TIMESTAMPTZ NOT NULL,
    entry_price NUMERIC(20,8) NOT NULL,
    quantity NUMERIC(20,8) NOT NULL,
    
    -- Exit Details
    exit_time TIMESTAMPTZ,
    exit_price NUMERIC(20,8),
    exit_reason TEXT,  -- TAKE_PROFIT, STOP_LOSS, TIMEOUT, SIGNAL, MANUAL
    
    -- P&L Calculation
    realized_pnl NUMERIC(20,2),
    pnl_pct NUMERIC(10,4),
    
    -- Risk Management
    stop_loss NUMERIC(20,8),
    take_profit NUMERIC(20,8),
    max_adverse_excursion NUMERIC(20,2),  -- MAE
    max_favorable_excursion NUMERIC(20,2),  -- MFE
    
    -- Trade Duration
    hold_duration INTEGER,  -- seconds
    
    -- Market Context
    regime TEXT,  -- Market regime at entry
    signal_strength TEXT,
    signal_confidence NUMERIC(5,2),
    sentiment_score NUMERIC(5,2),  -- -1 to +1
    
    -- Fees & Slippage
    entry_fee NUMERIC(20,2) DEFAULT 0,
    exit_fee NUMERIC(20,2) DEFAULT 0,
    slippage NUMERIC(20,2) DEFAULT 0,
    
    -- Metadata
    created_at TIMESTAMPTZ DEFAULT NOW(),
    metadata JSONB
);

-- Indexes for trades
CREATE INDEX IF NOT EXISTS idx_trades_backtest ON trades(backtest_id);
CREATE INDEX IF NOT EXISTS idx_trades_entry_time ON trades(entry_time);
CREATE INDEX IF NOT EXISTS idx_trades_exit_time ON trades(exit_time);
CREATE INDEX IF NOT EXISTS idx_trades_pnl ON trades(realized_pnl DESC NULLS LAST);
CREATE INDEX IF NOT EXISTS idx_trades_instrument ON trades(instrument);
CREATE INDEX IF NOT EXISTS idx_trades_regime ON trades(regime);
CREATE INDEX IF NOT EXISTS idx_trades_side ON trades(side);

\echo '✓ trades table created'

-- ============================================================
-- TABLE: ml_parameter_snapshots
-- ML optimization parameter tracking
-- ============================================================

CREATE TABLE IF NOT EXISTS ml_parameter_snapshots (
    -- Primary Key
    id SERIAL PRIMARY KEY,
    backtest_id INTEGER NOT NULL REFERENCES backtests(id) ON DELETE CASCADE,
    timestamp TIMESTAMPTZ NOT NULL,
    
    -- EMA Parameters
    fast_ema_period INTEGER NOT NULL,
    slow_ema_period INTEGER NOT NULL,
    trend_ema_period INTEGER,
    
    -- RSI/ATR Parameters
    rsi_period INTEGER,
    atr_period INTEGER,
    
    -- Optimization Context
    optimization_trigger TEXT,  -- SCHEDULED, PERFORMANCE_DROP, REGIME_CHANGE, MANUAL
    bars_since_last_optimization INTEGER,
    
    -- Performance Snapshot (Before Optimization)
    win_rate_before NUMERIC(5,2),
    sharpe_before NUMERIC(10,4),
    pnl_before NUMERIC(20,2),
    drawdown_before NUMERIC(10,4),
    
    -- Performance After Optimization
    win_rate_after NUMERIC(5,2),
    sharpe_after NUMERIC(10,4),
    pnl_after NUMERIC(20,2),
    drawdown_after NUMERIC(10,4),
    
    -- ML Metrics
    gradient_norm NUMERIC(10,6),
    loss_value NUMERIC(10,6),
    learning_rate NUMERIC(10,8),
    convergence_status TEXT,  -- CONVERGING, DIVERGING, STABLE
    
    -- Signal Weights (Logistic Regression)
    signal_weight_ema NUMERIC(5,3),
    signal_weight_rsi NUMERIC(5,3),
    signal_weight_pattern NUMERIC(5,3),
    signal_weight_sentiment NUMERIC(5,3),
    
    -- Metadata
    created_at TIMESTAMPTZ DEFAULT NOW(),
    notes TEXT
);

-- Indexes for ml_parameter_snapshots
CREATE INDEX IF NOT EXISTS idx_ml_snapshots_backtest ON ml_parameter_snapshots(backtest_id, timestamp);
CREATE INDEX IF NOT EXISTS idx_ml_snapshots_timestamp ON ml_parameter_snapshots(timestamp DESC);
CREATE INDEX IF NOT EXISTS idx_ml_snapshots_trigger ON ml_parameter_snapshots(optimization_trigger);

\echo '✓ ml_parameter_snapshots table created'

-- ============================================================
-- TABLE: circuit_breaker_events
-- Circuit breaker and risk management events
-- ============================================================

CREATE TABLE IF NOT EXISTS circuit_breaker_events (
    -- Primary Key
    id SERIAL PRIMARY KEY,
    backtest_id INTEGER NOT NULL REFERENCES backtests(id) ON DELETE CASCADE,
    timestamp TIMESTAMPTZ NOT NULL,
    
    -- Trigger Information
    trigger_type TEXT NOT NULL,  -- MAX_DRAWDOWN, DAILY_LOSS, CONSECUTIVE_LOSSES, LOW_WIN_RATE, VOLATILITY_SPIKE
    trigger_value NUMERIC(10,4),
    threshold_value NUMERIC(10,4),
    
    -- Circuit Breaker State
    breaker_status TEXT NOT NULL CHECK (breaker_status IN ('TRIGGERED', 'COOLING_DOWN', 'RESET', 'OVERRIDE')),
    cooldown_until TIMESTAMPTZ,
    cooldown_duration INTEGER,  -- seconds
    
    -- Impact Assessment
    positions_closed INTEGER DEFAULT 0,
    pending_orders_cancelled INTEGER DEFAULT 0,
    capital_protected NUMERIC(20,2),
    
    -- Context at Trigger Time
    current_pnl NUMERIC(20,2),
    current_drawdown_pct NUMERIC(10,4),
    consecutive_losses INTEGER DEFAULT 0,
    current_win_rate NUMERIC(5,2),
    volatility_level NUMERIC(10,6),
    
    -- Actions Taken
    action TEXT,  -- HALT_TRADING, REDUCE_POSITIONS, ALERT_ONLY, CLOSE_ALL
    auto_resume BOOLEAN DEFAULT FALSE,
    
    -- Metadata
    created_at TIMESTAMPTZ DEFAULT NOW(),
    resolved_at TIMESTAMPTZ,
    notes TEXT
);

-- Indexes for circuit_breaker_events
CREATE INDEX IF NOT EXISTS idx_circuit_breaker_backtest ON circuit_breaker_events(backtest_id, timestamp);
CREATE INDEX IF NOT EXISTS idx_circuit_breaker_timestamp ON circuit_breaker_events(timestamp DESC);
CREATE INDEX IF NOT EXISTS idx_circuit_breaker_type ON circuit_breaker_events(trigger_type);
CREATE INDEX IF NOT EXISTS idx_circuit_breaker_status ON circuit_breaker_events(breaker_status);

\echo '✓ circuit_breaker_events table created'

-- ============================================================
-- TRIGGER: Auto-update updated_at timestamp
-- ============================================================

CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ language 'plpgsql';

CREATE TRIGGER update_backtests_updated_at BEFORE UPDATE
    ON backtests FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

\echo '✓ Triggers created'

-- ============================================================
-- GRANT PERMISSIONS
-- ============================================================

-- Grant read access to Grafana user (if exists)
DO $$
BEGIN
    IF EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'grafana_reader') THEN
        GRANT SELECT ON ALL TABLES IN SCHEMA public TO grafana_reader;
        GRANT SELECT ON ALL SEQUENCES IN SCHEMA public TO grafana_reader;
    END IF;
END $$;

\echo '✓ Permissions granted'

\echo 'AI-adaptive backtest schema creation complete!'
```

### File 2: `infrastructure/postgres/04-dashboard-views.sql`

```sql
-- ============================================================
-- NAUTILUS TRADER AI-ADAPTIVE DASHBOARD VIEWS
-- Version: 1.0
-- Created: 2025-10-07
-- ============================================================

\echo 'Creating dashboard views...'

-- ============================================================
-- VIEW: v_backtest_performance
-- Main dashboard view for backtest results
-- ============================================================

CREATE OR REPLACE VIEW v_backtest_performance AS
SELECT 
    b.id,
    b.run_id,
    b.strategy_name,
    b.strategy_version,
    b.instrument,
    b.start_date,
    b.end_date,
    
    -- Performance Metrics
    b.initial_capital,
    b.final_capital,
    b.total_pnl,
    b.total_pnl_pct,
    b.total_trades,
    b.winning_trades,
    b.losing_trades,
    b.win_rate,
    b.sharpe_ratio,
    b.sortino_ratio,
    b.max_drawdown,
    b.max_drawdown_pct,
    b.profit_factor,
    b.avg_win,
    b.avg_loss,
    b.avg_trade_duration,
    
    -- Parameters
    b.parameters->>'fast_ema_period' as fast_ema,
    b.parameters->>'slow_ema_period' as slow_ema,
    b.parameters->>'rsi_period' as rsi_period,
    
    -- Latest Regime
    (SELECT regime FROM regime_detection_log 
     WHERE backtest_id = b.id 
     ORDER BY detected_at DESC LIMIT 1) as latest_regime,
    
    -- ML Optimizations Count
    (SELECT COUNT(*) FROM ml_optimization_log 
     WHERE strategy_id = b.run_id) as ml_optimization_count,
    
    -- Pattern Detections
    (SELECT COUNT(*) FROM pattern_detection_log 
     WHERE symbol = b.instrument 
     AND detected_at BETWEEN b.start_date AND b.end_date) as pattern_count,
    
    -- Risk Events
    (SELECT COUNT(*) FROM risk_events 
     WHERE strategy_id = b.run_id 
     AND severity = 'CRITICAL') as critical_risk_events,
    
    -- Circuit Breaker Events
    (SELECT COUNT(*) FROM circuit_breaker_events 
     WHERE backtest_id = b.id) as circuit_breaker_count,
    
    -- Performance
    b.data_bars_processed,
    b.duration_seconds,
    b.created_at,
    
    -- Calculate ROI
    CASE 
        WHEN b.initial_capital > 0 THEN (b.final_capital - b.initial_capital) / b.initial_capital * 100 
        ELSE 0 
    END as roi_pct,
    
    -- Calculate expectancy
    CASE 
        WHEN b.total_trades > 0 THEN b.total_pnl / b.total_trades 
        ELSE 0 
    END as expectancy
    
FROM backtests b
ORDER BY b.created_at DESC;

\echo '✓ v_backtest_performance view created'

-- ============================================================
-- VIEW: v_strategy_comparison
-- Compare strategy configurations for optimization
-- ============================================================

CREATE OR REPLACE VIEW v_strategy_comparison AS
SELECT 
    instrument,
    parameters->>'fast_ema_period' as fast_ema,
    parameters->>'slow_ema_period' as slow_ema,
    parameters->>'rsi_period' as rsi_period,
    
    COUNT(*) as backtest_count,
    AVG(sharpe_ratio) as avg_sharpe,
    STDDEV(sharpe_ratio) as stddev_sharpe,
    AVG(win_rate) as avg_win_rate,
    AVG(total_pnl_pct) as avg_return_pct,
    MAX(total_pnl_pct) as max_return_pct,
    MIN(total_pnl_pct) as min_return_pct,
    AVG(max_drawdown_pct) as avg_max_dd,
    AVG(profit_factor) as avg_profit_factor,
    
    -- Risk-adjusted return
    CASE 
        WHEN AVG(max_drawdown_pct) != 0 THEN AVG(total_pnl_pct) / ABS(AVG(max_drawdown_pct))
        ELSE 0
    END as return_over_drawdown,
    
    -- Consistency score (lower stddev is better)
    CASE 
        WHEN AVG(sharpe_ratio) != 0 THEN STDDEV(sharpe_ratio) / AVG(sharpe_ratio)
        ELSE 999
    END as consistency_score,
    
    -- Rank by Sharpe
    RANK() OVER (PARTITION BY instrument ORDER BY AVG(sharpe_ratio) DESC) as sharpe_rank
FROM backtests
WHERE total_trades >= 10  -- Minimum statistical significance
GROUP BY instrument, fast_ema, slow_ema, rsi_period
HAVING COUNT(*) >= 3  -- At least 3 backtests for reliability
ORDER BY avg_sharpe DESC;

\echo '✓ v_strategy_comparison view created'

-- ============================================================
-- VIEW: v_regime_performance
-- Analyze performance by market regime
-- ============================================================

CREATE OR REPLACE VIEW v_regime_performance AS
SELECT 
    r.detected_regime,
    COUNT(DISTINCT r.id) as regime_occurrences,
    AVG(r.confidence) as avg_confidence,
    STDDEV(r.confidence) as stddev_confidence,
    
    -- Trade Statistics in This Regime
    (SELECT COUNT(*) FROM trades t 
     WHERE t.regime = r.detected_regime) as trades_in_regime,
    
    -- Win Rate in This Regime
    (SELECT AVG(CASE WHEN realized_pnl > 0 THEN 1.0 ELSE 0.0 END) * 100
     FROM trades t 
     WHERE t.regime = r.detected_regime) as regime_win_rate,
    
    -- Avg PnL in Regime
    (SELECT AVG(realized_pnl) FROM trades t 
     WHERE t.regime = r.detected_regime) as avg_pnl_in_regime,
    
    -- Total PnL in Regime
    (SELECT SUM(realized_pnl) FROM trades t 
     WHERE t.regime = r.detected_regime) as total_pnl_in_regime,
    
    -- Avg Trade Duration in Regime
    (SELECT AVG(hold_duration) FROM trades t 
     WHERE t.regime = r.detected_regime) as avg_duration_seconds,
    
    -- Best Trade in Regime
    (SELECT MAX(realized_pnl) FROM trades t 
     WHERE t.regime = r.detected_regime) as best_trade,
    
    -- Worst Trade in Regime
    (SELECT MIN(realized_pnl) FROM trades t 
     WHERE t.regime = r.detected_regime) as worst_trade
    
FROM regime_detection_log r
GROUP BY r.detected_regime
ORDER BY trades_in_regime DESC;

\echo '✓ v_regime_performance view created'

-- ============================================================
-- VIEW: v_recent_trades
-- Most recent trades with enriched data
-- ============================================================

CREATE OR REPLACE VIEW v_recent_trades AS
SELECT 
    t.id,
    t.trade_id,
    b.strategy_name,
    t.instrument,
    t.side,
    
    -- Entry
    t.entry_time,
    t.entry_price,
    t.quantity,
    
    -- Exit
    t.exit_time,
    t.exit_price,
    t.exit_reason,
    
    -- P&L
    t.realized_pnl,
    t.pnl_pct,
    
    -- Risk
    t.stop_loss,
    t.take_profit,
    t.max_adverse_excursion as mae,
    t.max_favorable_excursion as mfe,
    
    -- Duration
    t.hold_duration,
    CASE 
        WHEN t.hold_duration < 60 THEN CONCAT(t.hold_duration, 's')
        WHEN t.hold_duration < 3600 THEN CONCAT(ROUND(t.hold_duration / 60.0, 1), 'm')
        ELSE CONCAT(ROUND(t.hold_duration / 3600.0, 1), 'h')
    END as duration_formatted,
    
    -- Context
    t.regime,
    t.signal_strength,
    t.signal_confidence,
    t.sentiment_score,
    
    -- Fees
    t.entry_fee + t.exit_fee + t.slippage as total_fees,
    
    -- Win/Loss Classification
    CASE 
        WHEN t.realized_pnl > 0 THEN 'WIN'
        WHEN t.realized_pnl < 0 THEN 'LOSS'
        ELSE 'BREAKEVEN'
    END as outcome,
    
    -- MAE/MFE Ratio (efficiency)
    CASE 
        WHEN t.max_adverse_excursion != 0 THEN ABS(t.max_favorable_excursion / t.max_adverse_excursion)
        ELSE 0
    END as efficiency_ratio,
    
    t.created_at
    
FROM trades t
JOIN backtests b ON t.backtest_id = b.id
ORDER BY t.created_at DESC;

\echo '✓ v_recent_trades view created'

-- ============================================================
-- VIEW: v_ml_optimization_history
-- ML parameter evolution tracking
-- ============================================================

CREATE OR REPLACE VIEW v_ml_optimization_history AS
SELECT 
    m.id,
    m.timestamp,
    b.strategy_name,
    b.instrument,
    
    -- Parameters
    m.fast_ema_period,
    m.slow_ema_period,
    m.trend_ema_period,
    m.rsi_period,
    m.atr_period,
    
    -- Optimization Context
    m.optimization_trigger,
    m.bars_since_last_optimization,
    
    -- Performance Impact
    m.win_rate_before,
    m.win_rate_after,
    m.win_rate_after - m.win_rate_before as win_rate_improvement,
    
    m.sharpe_before,
    m.sharpe_after,
    m.sharpe_after - m.sharpe_before as sharpe_improvement,
    
    m.pnl_before,
    m.pnl_after,
    m.pnl_after - m.pnl_before as pnl_improvement,
    
    m.drawdown_before,
    m.drawdown_after,
    
    -- ML Metrics
    m.gradient_norm,
    m.loss_value,
    m.learning_rate,
    m.convergence_status,
    
    -- Signal Weights
    m.signal_weight_ema,
    m.signal_weight_rsi,
    m.signal_weight_pattern,
    m.signal_weight_sentiment,
    
    -- Classification
    CASE 
        WHEN m.win_rate_after > m.win_rate_before AND m.sharpe_after > m.sharpe_before THEN 'SUCCESSFUL'
        WHEN m.win_rate_after < m.win_rate_before OR m.sharpe_after < m.sharpe_before THEN 'DEGRADED'
        ELSE 'NEUTRAL'
    END as optimization_outcome,
    
    m.created_at
    
FROM ml_parameter_snapshots m
JOIN backtests b ON m.backtest_id = b.id
ORDER BY m.timestamp DESC;

\echo '✓ v_ml_optimization_history view created'

-- ============================================================
-- VIEW: v_risk_summary
-- Risk management summary
-- ============================================================

CREATE OR REPLACE VIEW v_risk_summary AS
SELECT 
    b.id as backtest_id,
    b.run_id,
    b.strategy_name,
    b.instrument,
    
    -- Drawdown
    b.max_drawdown,
    b.max_drawdown_pct,
    
    -- Current Status
    b.total_pnl,
    b.win_rate,
    
    -- Circuit Breaker Summary
    (SELECT COUNT(*) FROM circuit_breaker_events 
     WHERE backtest_id = b.id) as total_breaker_events,
    
    (SELECT COUNT(*) FROM circuit_breaker_events 
     WHERE backtest_id = b.id 
     AND breaker_status = 'TRIGGERED') as active_breakers,
    
    -- Last Circuit Breaker
    (SELECT trigger_type FROM circuit_breaker_events 
     WHERE backtest_id = b.id 
     ORDER BY timestamp DESC LIMIT 1) as last_breaker_trigger,
    
    (SELECT timestamp FROM circuit_breaker_events 
     WHERE backtest_id = b.id 
     ORDER BY timestamp DESC LIMIT 1) as last_breaker_time,
    
    -- Risk Events
    (SELECT COUNT(*) FROM risk_events 
     WHERE strategy_id = b.run_id 
     AND severity = 'CRITICAL') as critical_events,
    
    (SELECT COUNT(*) FROM risk_events 
     WHERE strategy_id = b.run_id 
     AND severity = 'WARNING') as warning_events,
    
    -- Consecutive Losses (from trades)
    (SELECT MAX(consecutive) FROM (
        SELECT 
            SUM(CASE WHEN realized_pnl < 0 THEN 1 ELSE 0 END) OVER (
                ORDER BY entry_time 
                ROWS BETWEEN UNBOUNDED PRECEDING AND CURRENT ROW
            ) as consecutive
        FROM trades 
        WHERE backtest_id = b.id
    ) sub) as max_consecutive_losses,
    
    b.created_at
    
FROM backtests b
ORDER BY b.created_at DESC;

\echo '✓ v_risk_summary view created'

-- ============================================================
-- MATERIALIZED VIEW: v_daily_performance
-- Pre-aggregated daily statistics for fast queries
-- ============================================================

CREATE MATERIALIZED VIEW IF NOT EXISTS v_daily_performance AS
SELECT 
    DATE(t.entry_time) as trade_date,
    t.instrument,
    b.strategy_name,
    
    COUNT(*) as trades_count,
    SUM(CASE WHEN t.realized_pnl > 0 THEN 1 ELSE 0 END) as winning_trades,
    SUM(CASE WHEN t.realized_pnl < 0 THEN 1 ELSE 0 END) as losing_trades,
    AVG(CASE WHEN t.realized_pnl > 0 THEN 1.0 ELSE 0.0 END) * 100 as daily_win_rate,
    
    SUM(t.realized_pnl) as daily_pnl,
    AVG(t.realized_pnl) as avg_pnl_per_trade,
    MAX(t.realized_pnl) as best_trade,
    MIN(t.realized_pnl) as worst_trade,
    
    AVG(t.hold_duration) as avg_duration_seconds,
    SUM(t.entry_fee + t.exit_fee + t.slippage) as total_fees
    
FROM trades t
JOIN backtests b ON t.backtest_id = b.id
GROUP BY DATE(t.entry_time), t.instrument, b.strategy_name
ORDER BY trade_date DESC;

-- Index for materialized view
CREATE INDEX IF NOT EXISTS idx_daily_performance_date ON v_daily_performance(trade_date DESC);

\echo '✓ v_daily_performance materialized view created'
\echo 'Dashboard views creation complete!'
\echo ''
\echo 'To refresh materialized view, run:'
\echo '  REFRESH MATERIALIZED VIEW v_daily_performance;'
```

### Apply Schema to Database

```bash
# Navigate to infrastructure directory
cd /home/ajk/Nautilus/nautilus_trader

# Apply backtest schema
docker exec nautilus_postgres psql -U nautilus -d nautilus_trader < infrastructure/postgres/03-backtest-schema.sql

# Apply dashboard views
docker exec nautilus_postgres psql -U nautilus -d nautilus_trader < infrastructure/postgres/04-dashboard-views.sql

# Verify tables created
docker exec nautilus_postgres psql -U nautilus -d nautilus_trader -c "\dt"

# Verify views created
docker exec nautilus_postgres psql -U nautilus -d nautilus_trader -c "\dv"

# Test a view
docker exec nautilus_postgres psql -U nautilus -d nautilus_trader -c "SELECT * FROM v_backtest_performance LIMIT 1;"
```

---

## Phase 2: Prometheus Metrics Exporter - Complete Code

### Create Directory Structure

```bash
cd /home/ajk/Nautilus/nautilus_trader
mkdir -p ajk_strategies/monitoring
mkdir -p ajk_strategies/database
mkdir -p ajk_strategies/cache
touch ajk_strategies/monitoring/__init__.py
touch ajk_strategies/database/__init__.py
touch ajk_strategies/cache/__init__.py
```

### File 3: `ajk_strategies/database/connection_pool.py`

```python
"""
PostgreSQL connection pool manager for Nautilus Trader.

Provides efficient database connection management with health checks,
retry logic, and automatic connection recovery.
"""

import psycopg2
from psycopg2 import pool, extras
from contextlib import contextmanager
import os
import time
import logging
from typing import Optional

logger = logging.getLogger(__name__)


class DatabasePool:
    """PostgreSQL connection pool with automatic retry and health checks"""
    
    def __init__(
        self,
        min_connections: int = 2,
        max_connections: int = 10,
        max_retries: int = 3,
        retry_delay: int = 5
    ):
        """
        Initialize database connection pool.
        
        Args:
            min_connections: Minimum number of connections to maintain
            max_connections: Maximum number of connections allowed
            max_retries: Maximum connection retry attempts
            retry_delay: Delay between retries in seconds
        """
        self.min_connections = min_connections
        self.max_connections = max_connections
        self.max_retries = max_retries
        self.retry_delay = retry_delay
        self._pool: Optional[pool.SimpleConnectionPool] = None
        
        self._connect()
    
    def _get_connection_params(self) -> dict:
        """Get database connection parameters from environment"""
        return {
            'host': os.getenv('DB_HOST', 'localhost'),
            'port': int(os.getenv('DB_PORT', 5432)),
            'database': os.getenv('DB_NAME', 'nautilus_trader'),
            'user': os.getenv('DB_USER', 'nautilus'),
            'password': os.getenv('DB_PASSWORD', 'changeme'),
            'cursor_factory': extras.RealDictCursor
        }
    
    def _connect(self):
        """Create connection pool with retry logic"""
        for attempt in range(self.max_retries):
            try:
                params = self._get_connection_params()
                self._pool = pool.SimpleConnectionPool(
                    self.min_connections,
                    self.max_connections,
                    **params
                )
                logger.info(f"✓ Database connection pool created (min={self.min_connections}, max={self.max_connections})")
                return
            
            except Exception as e:
                logger.error(f"Database connection attempt {attempt + 1}/{self.max_retries} failed: {e}")
                if attempt < self.max_retries - 1:
                    time.sleep(self.retry_delay)
                else:
                    raise Exception(f"Failed to connect to database after {self.max_retries} attempts") from e
    
    @contextmanager
    def get_connection(self):
        """
        Get a database connection from the pool.
        
        Usage:
            with pool.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT * FROM backtests")
        """
        conn = None
        try:
            conn = self._pool.getconn()
            yield conn
            conn.commit()
        except Exception as e:
            if conn:
                conn.rollback()
            logger.error(f"Database operation failed: {e}")
            raise
        finally:
            if conn:
                self._pool.putconn(conn)
    
    def execute_query(self, query: str, params: tuple = None) -> list:
        """
        Execute SELECT query and return results.
        
        Args:
            query: SQL query string
            params: Query parameters (optional)
        
        Returns:
            List of result rows as dictionaries
        """
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(query, params)
            return cursor.fetchall()
    
    def execute_insert(self, query: str, params: tuple) -> int:
        """
        Execute INSERT query and return inserted ID.
        
        Args:
            query: SQL INSERT query with RETURNING id
            params: Query parameters
        
        Returns:
            Inserted row ID
        """
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(query, params)
            result = cursor.fetchone()
            return result['id'] if result else None
    
    def execute_batch(self, query: str, params_list: list):
        """
        Execute batch INSERT for multiple rows.
        
        Args:
            query: SQL INSERT query
            params_list: List of parameter tuples
        """
        with self.get_connection() as conn:
            cursor = conn.cursor()
            extras.execute_batch(cursor, query, params_list, page_size=1000)
    
    def health_check(self) -> bool:
        """Check if database connection is healthy"""
        try:
            result = self.execute_query("SELECT 1 as health")
            return len(result) > 0
        except:
            return False
    
    def close(self):
        """Close all connections in the pool"""
        if self._pool:
            self._pool.closeall()
            logger.info("Database connection pool closed")


# Global database pool instance
_db_pool: Optional[DatabasePool] = None


def get_db_pool() -> DatabasePool:
    """Get or create global database pool"""
    global _db_pool
    if _db_pool is None:
        _db_pool = DatabasePool()
    return _db_pool
```

### File 4: `ajk_strategies/database/backtest_storage.py`

```python
"""
PostgreSQL storage for backtest results.

Handles storing backtest results, trades, ML optimization history,
and circuit breaker events to PostgreSQL database.
"""

from typing import Dict, List, Optional
from datetime import datetime
from decimal import Decimal
import json
import logging

from database.connection_pool import get_db_pool

logger = logging.getLogger(__name__)


class BacktestStorage:
    """Store backtest results in PostgreSQL"""
    
    def __init__(self):
        self.db_pool = get_db_pool()
    
    def save_backtest_result(
        self,
        run_id: str,
        strategy_name: str,
        instrument: str,
        start_date: datetime,
        end_date: datetime,
        metrics: Dict,
        parameters: Dict
    ) -> int:
        """
        Save backtest result to database.
        
        Args:
            run_id: Unique run identifier
            strategy_name: Name of strategy
            instrument: Trading instrument
            start_date: Backtest start date
            end_date: Backtest end date
            metrics: Performance metrics dictionary
            parameters: Strategy parameters dictionary
        
        Returns:
            backtest_id for further inserts
        """
        query = """
            INSERT INTO backtests (
                run_id, strategy_name, strategy_version, instrument,
                start_date, end_date,
                initial_capital, final_capital, total_pnl, total_pnl_pct,
                total_trades, winning_trades, losing_trades, win_rate,
                sharpe_ratio, sortino_ratio, max_drawdown, max_drawdown_pct,
                profit_factor, avg_win, avg_loss, avg_trade_duration,
                parameters, data_bars_processed, duration_seconds, notes
            ) VALUES (
                %(run_id)s, %(strategy_name)s, %(strategy_version)s, %(instrument)s,
                %(start_date)s, %(end_date)s,
                %(initial_capital)s, %(final_capital)s, %(total_pnl)s, %(total_pnl_pct)s,
                %(total_trades)s, %(winning_trades)s, %(losing_trades)s, %(win_rate)s,
                %(sharpe_ratio)s, %(sortino_ratio)s, %(max_drawdown)s, %(max_drawdown_pct)s,
                %(profit_factor)s, %(avg_win)s, %(avg_loss)s, %(avg_trade_duration)s,
                %(parameters)s, %(data_bars_processed)s, %(duration_seconds)s, %(notes)s
            ) RETURNING id;
        """
        
        data = {
            'run_id': run_id,
            'strategy_name': strategy_name,
            'strategy_version': parameters.get('version', '1.0'),
            'instrument': instrument,
            'start_date': start_date,
            'end_date': end_date,
            'initial_capital': float(metrics.get('initial_capital', 100000)),
            'final_capital': float(metrics.get('final_capital', 0)),
            'total_pnl': float(metrics.get('total_pnl', 0)),
            'total_pnl_pct': float(metrics.get('pnl_pct', 0)),
            'total_trades': metrics.get('total_trades', 0),
            'winning_trades': metrics.get('winning_trades', 0),
            'losing_trades': metrics.get('losing_trades', 0),
            'win_rate': float(metrics.get('win_rate', 0)),
            'sharpe_ratio': float(metrics.get('sharpe_ratio')) if metrics.get('sharpe_ratio') else None,
            'sortino_ratio': float(metrics.get('sortino_ratio')) if metrics.get('sortino_ratio') else None,
            'max_drawdown': float(metrics.get('max_drawdown')) if metrics.get('max_drawdown') else None,
            'max_drawdown_pct': float(metrics.get('max_drawdown_pct')) if metrics.get('max_drawdown_pct') else None,
            'profit_factor': float(metrics.get('profit_factor')) if metrics.get('profit_factor') else None,
            'avg_win': float(metrics.get('avg_win')) if metrics.get('avg_win') else None,
            'avg_loss': float(metrics.get('avg_loss')) if metrics.get('avg_loss') else None,
            'avg_trade_duration': metrics.get('avg_trade_duration'),
            'parameters': json.dumps(parameters),
            'data_bars_processed': metrics.get('bars_processed', 0),
            'duration_seconds': float(metrics.get('duration_seconds', 0)),
            'notes': metrics.get('notes', '')
        }
        
        backtest_id = self.db_pool.execute_insert(query, data)
        logger.info(f"✓ Saved backtest result (ID: {backtest_id}, run_id: {run_id})")
        return backtest_id
    
    def save_trades(self, backtest_id: int, trades: List[Dict]):
        """
        Save trade history to database.
        
        Args:
            backtest_id: Backtest ID from save_backtest_result
            trades: List of trade dictionaries
        """
        if not trades:
            return
        
        query = """
            INSERT INTO trades (
                backtest_id, trade_id, instrument, side,
                entry_time, entry_price, quantity,
                exit_time, exit_price, exit_reason,
                realized_pnl, pnl_pct,
                stop_loss, take_profit,
                max_adverse_excursion, max_favorable_excursion,
                hold_duration, regime, signal_strength, signal_confidence,
                sentiment_score, entry_fee, exit_fee, slippage, metadata
            ) VALUES (
                %(backtest_id)s, %(trade_id)s, %(instrument)s, %(side)s,
                %(entry_time)s, %(entry_price)s, %(quantity)s,
                %(exit_time)s, %(exit_price)s, %(exit_reason)s,
                %(realized_pnl)s, %(pnl_pct)s,
                %(stop_loss)s, %(take_profit)s,
                %(mae)s, %(mfe)s,
                %(hold_duration)s, %(regime)s, %(signal_strength)s, %(signal_confidence)s,
                %(sentiment_score)s, %(entry_fee)s, %(exit_fee)s, %(slippage)s, %(metadata)s
            );
        """
        
        params_list = [
            {
                'backtest_id': backtest_id,
                'trade_id': trade.get('trade_id'),
                'instrument': trade.get('instrument'),
                'side': trade.get('side'),
                'entry_time': trade.get('entry_time'),
                'entry_price': float(trade.get('entry_price')),
                'quantity': float(trade.get('quantity')),
                'exit_time': trade.get('exit_time'),
                'exit_price': float(trade.get('exit_price')) if trade.get('exit_price') else None,
                'exit_reason': trade.get('exit_reason'),
                'realized_pnl': float(trade.get('realized_pnl')) if trade.get('realized_pnl') else None,
                'pnl_pct': float(trade.get('pnl_pct')) if trade.get('pnl_pct') else None,
                'stop_loss': float(trade.get('stop_loss')) if trade.get('stop_loss') else None,
                'take_profit': float(trade.get('take_profit')) if trade.get('take_profit') else None,
                'mae': float(trade.get('mae')) if trade.get('mae') else None,
                'mfe': float(trade.get('mfe')) if trade.get('mfe') else None,
                'hold_duration': trade.get('hold_duration'),
                'regime': trade.get('regime'),
                'signal_strength': trade.get('signal_strength'),
                'signal_confidence': float(trade.get('signal_confidence')) if trade.get('signal_confidence') else None,
                'sentiment_score': float(trade.get('sentiment_score')) if trade.get('sentiment_score') else None,
                'entry_fee': float(trade.get('entry_fee', 0)),
                'exit_fee': float(trade.get('exit_fee', 0)),
                'slippage': float(trade.get('slippage', 0)),
                'metadata': json.dumps(trade.get('metadata', {}))
            }
            for trade in trades
        ]
        
        self.db_pool.execute_batch(query, params_list)
        logger.info(f"✓ Saved {len(trades)} trades for backtest {backtest_id}")
    
    def save_ml_parameter_snapshot(self, backtest_id: int, snapshot: Dict):
        """
        Save ML parameter optimization snapshot.
        
        Args:
            backtest_id: Backtest ID
            snapshot: Parameter snapshot dictionary
        """
        query = """
            INSERT INTO ml_parameter_snapshots (
                backtest_id, timestamp,
                fast_ema_period, slow_ema_period, trend_ema_period,
                rsi_period, atr_period,
                optimization_trigger, bars_since_last_optimization,
                win_rate_before, win_rate_after, sharpe_before, sharpe_after,
                pnl_before, pnl_after, drawdown_before, drawdown_after,
                gradient_norm, loss_value, learning_rate, convergence_status,
                signal_weight_ema, signal_weight_rsi, signal_weight_pattern, signal_weight_sentiment,
                notes
            ) VALUES (
                %(backtest_id)s, %(timestamp)s,
                %(fast_ema)s, %(slow_ema)s, %(trend_ema)s,
                %(rsi)s, %(atr)s,
                %(trigger)s, %(bars_since)s,
                %(win_before)s, %(win_after)s, %(sharpe_before)s, %(sharpe_after)s,
                %(pnl_before)s, %(pnl_after)s, %(dd_before)s, %(dd_after)s,
                %(grad_norm)s, %(loss)s, %(lr)s, %(convergence)s,
                %(w_ema)s, %(w_rsi)s, %(w_pattern)s, %(w_sentiment)s,
                %(notes)s
            );
        """
        
        data = {
            'backtest_id': backtest_id,
            'timestamp': snapshot.get('timestamp'),
            'fast_ema': snapshot.get('fast_ema_period'),
            'slow_ema': snapshot.get('slow_ema_period'),
            'trend_ema': snapshot.get('trend_ema_period'),
            'rsi': snapshot.get('rsi_period'),
            'atr': snapshot.get('atr_period'),
            'trigger': snapshot.get('optimization_trigger'),
            'bars_since': snapshot.get('bars_since_last_optimization'),
            'win_before': float(snapshot.get('win_rate_before')) if snapshot.get('win_rate_before') else None,
            'win_after': float(snapshot.get('win_rate_after')) if snapshot.get('win_rate_after') else None,
            'sharpe_before': float(snapshot.get('sharpe_before')) if snapshot.get('sharpe_before') else None,
            'sharpe_after': float(snapshot.get('sharpe_after')) if snapshot.get('sharpe_after') else None,
            'pnl_before': float(snapshot.get('pnl_before')) if snapshot.get('pnl_before') else None,
            'pnl_after': float(snapshot.get('pnl_after')) if snapshot.get('pnl_after') else None,
            'dd_before': float(snapshot.get('drawdown_before')) if snapshot.get('drawdown_before') else None,
            'dd_after': float(snapshot.get('drawdown_after')) if snapshot.get('drawdown_after') else None,
            'grad_norm': float(snapshot.get('gradient_norm')) if snapshot.get('gradient_norm') else None,
            'loss': float(snapshot.get('loss_value')) if snapshot.get('loss_value') else None,
            'lr': float(snapshot.get('learning_rate')) if snapshot.get('learning_rate') else None,
            'convergence': snapshot.get('convergence_status'),
            'w_ema': float(snapshot.get('signal_weight_ema')) if snapshot.get('signal_weight_ema') else None,
            'w_rsi': float(snapshot.get('signal_weight_rsi')) if snapshot.get('signal_weight_rsi') else None,
            'w_pattern': float(snapshot.get('signal_weight_pattern')) if snapshot.get('signal_weight_pattern') else None,
            'w_sentiment': float(snapshot.get('signal_weight_sentiment')) if snapshot.get('signal_weight_sentiment') else None,
            'notes': snapshot.get('notes', '')
        }
        
        self.db_pool.execute_insert(query, data)
        logger.info(f"✓ Saved ML parameter snapshot for backtest {backtest_id}")
    
    def save_circuit_breaker_event(self, backtest_id: int, event: Dict):
        """
        Save circuit breaker event.
        
        Args:
            backtest_id: Backtest ID
            event: Circuit breaker event dictionary
        """
        query = """
            INSERT INTO circuit_breaker_events (
                backtest_id, timestamp,
                trigger_type, trigger_value, threshold_value,
                breaker_status, cooldown_until, cooldown_duration,
                positions_closed, pending_orders_cancelled, capital_protected,
                current_pnl, current_drawdown_pct, consecutive_losses,
                current_win_rate, volatility_level,
                action, auto_resume, notes
            ) VALUES (
                %(backtest_id)s, %(timestamp)s,
                %(trigger_type)s, %(trigger_value)s, %(threshold_value)s,
                %(status)s, %(cooldown_until)s, %(cooldown_duration)s,
                %(positions_closed)s, %(orders_cancelled)s, %(capital_protected)s,
                %(current_pnl)s, %(current_drawdown)s, %(consecutive_losses)s,
                %(win_rate)s, %(volatility)s,
                %(action)s, %(auto_resume)s, %(notes)s
            );
        """
        
        data = {
            'backtest_id': backtest_id,
            'timestamp': event.get('timestamp'),
            'trigger_type': event.get('trigger_type'),
            'trigger_value': float(event.get('trigger_value')) if event.get('trigger_value') else None,
            'threshold_value': float(event.get('threshold_value')) if event.get('threshold_value') else None,
            'status': event.get('breaker_status'),
            'cooldown_until': event.get('cooldown_until'),
            'cooldown_duration': event.get('cooldown_duration'),
            'positions_closed': event.get('positions_closed', 0),
            'orders_cancelled': event.get('pending_orders_cancelled', 0),
            'capital_protected': float(event.get('capital_protected')) if event.get('capital_protected') else None,
            'current_pnl': float(event.get('current_pnl')) if event.get('current_pnl') else None,
            'current_drawdown': float(event.get('current_drawdown_pct')) if event.get('current_drawdown_pct') else None,
            'consecutive_losses': event.get('consecutive_losses', 0),
            'win_rate': float(event.get('current_win_rate')) if event.get('current_win_rate') else None,
            'volatility': float(event.get('volatility_level')) if event.get('volatility_level') else None,
            'action': event.get('action'),
            'auto_resume': event.get('auto_resume', False),
            'notes': event.get('notes', '')
        }
        
        self.db_pool.execute_insert(query, data)
        logger.info(f"✓ Saved circuit breaker event for backtest {backtest_id}")
```

*Due to response length limits, I'll continue in the next response with the remaining implementation files. The documentation is getting very comprehensive!*

**Status:** Implementation guide in progress - Database layer complete, moving to metrics exporter code next.

Would you like me to continue with the remaining implementation code (Prometheus metrics, Redis cache, Grafana dashboards)?
