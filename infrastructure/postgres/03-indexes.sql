\echo 'Creating supporting indexes...'

-- Base tables (in public schema) get indexes via upstream DDL.
-- Add indexes for AI extension tables.

SET search_path TO public, ai_extensions;

CREATE INDEX IF NOT EXISTS idx_ml_optimization_log_strategy
    ON ml_optimization_log (strategy_id, created_at DESC);

CREATE INDEX IF NOT EXISTS idx_regime_detection_log_detected
    ON regime_detection_log (detected_at DESC);

CREATE INDEX IF NOT EXISTS idx_pattern_detection_log_symbol
    ON pattern_detection_log (symbol, timeframe, detected_at DESC);

CREATE INDEX IF NOT EXISTS idx_risk_events_strategy
    ON risk_events (strategy_id, triggered_at DESC);

CREATE INDEX IF NOT EXISTS idx_sentiment_log_source
    ON sentiment_log (source, collected_at DESC);

CREATE INDEX IF NOT EXISTS idx_performance_metrics_strategy
    ON performance_metrics (strategy_id, metric_name, calculated_at DESC);

RESET search_path;

\echo 'Indexes created.'
