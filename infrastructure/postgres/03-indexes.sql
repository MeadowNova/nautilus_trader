\echo 'Creating supporting indexes...'

-- Base tables (in public schema) get indexes via upstream DDL.
-- Add indexes for AI extension tables.

SET search_path TO public, ai_extensions;

CREATE INDEX IF NOT EXISTS idx_ml_optimization_log_strategy
    ON ai_extensions.ml_optimization_log (strategy_id, created_at DESC);

CREATE INDEX IF NOT EXISTS idx_regime_detection_log_detected
    ON ai_extensions.regime_detection_log (detected_at DESC);

CREATE INDEX IF NOT EXISTS idx_pattern_detection_log_symbol
    ON ai_extensions.pattern_detection_log (symbol, timeframe, detected_at DESC);

CREATE INDEX IF NOT EXISTS idx_risk_events_strategy
    ON ai_extensions.risk_events (strategy_id, triggered_at DESC);

CREATE INDEX IF NOT EXISTS idx_sentiment_log_source
    ON ai_extensions.sentiment_log (source, collected_at DESC);

CREATE INDEX IF NOT EXISTS idx_performance_metrics_strategy
    ON ai_extensions.performance_metrics (strategy_id, metric_name, calculated_at DESC);

CREATE INDEX IF NOT EXISTS idx_model_training_runs_strategy
    ON ai_extensions.model_training_runs (strategy_id, model_name, model_version);

CREATE INDEX IF NOT EXISTS idx_model_artifacts_training
    ON ai_extensions.model_artifacts (training_run_id, artifact_type);

CREATE INDEX IF NOT EXISTS idx_backtest_runs_strategy
    ON ai_extensions.backtest_runs (strategy_id, started_at DESC);

CREATE INDEX IF NOT EXISTS idx_backtest_runs_instrument
    ON ai_extensions.backtest_runs (instrument_id, bar_type, started_at DESC);

CREATE INDEX IF NOT EXISTS idx_backtest_metrics_run
    ON ai_extensions.backtest_metrics (backtest_run_id, metric_name);

RESET search_path;

\echo 'Indexes created.'
