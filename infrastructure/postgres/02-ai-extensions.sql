\echo 'Creating AI-adaptive extension tables...'

CREATE EXTENSION IF NOT EXISTS pgcrypto;

CREATE SCHEMA IF NOT EXISTS ai_extensions;
SET search_path TO public, ai_extensions;

CREATE TABLE IF NOT EXISTS ai_extensions.ml_optimization_log (
    id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
    strategy_id TEXT NOT NULL,
    parameter_set JSONB NOT NULL,
    objective_metric TEXT NOT NULL,
    objective_value DOUBLE PRECISION NOT NULL,
    status TEXT NOT NULL DEFAULT 'completed',
    notes TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS ai_extensions.regime_detection_log (
    id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
    detected_regime TEXT NOT NULL,
    confidence DOUBLE PRECISION NOT NULL,
    features JSONB,
    detected_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS ai_extensions.pattern_detection_log (
    id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
    symbol TEXT NOT NULL,
    timeframe TEXT NOT NULL,
    pattern TEXT NOT NULL,
    score DOUBLE PRECISION,
    metadata JSONB,
    detected_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS ai_extensions.risk_events (
    id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
    strategy_id TEXT NOT NULL,
    venue TEXT,
    severity TEXT NOT NULL,
    event_type TEXT NOT NULL,
    details JSONB,
    triggered_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS ai_extensions.sentiment_log (
    id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
    source TEXT NOT NULL,
    symbol TEXT,
    score NUMERIC NOT NULL,
    magnitude NUMERIC,
    payload JSONB,
    collected_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS ai_extensions.performance_metrics (
    id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
    strategy_id TEXT NOT NULL,
    metric_name TEXT NOT NULL,
    metric_value DOUBLE PRECISION NOT NULL,
    metric_window TEXT,
    calculated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS ai_extensions.model_training_runs (
    id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
    strategy_id TEXT NOT NULL,
    model_name TEXT NOT NULL,
    model_version TEXT NOT NULL,
    dataset_source TEXT,
    dataset_hash TEXT,
    dataset_start TIMESTAMPTZ,
    dataset_end TIMESTAMPTZ,
    feature_hash TEXT,
    hyperparameters JSONB,
    metrics JSONB,
    status TEXT NOT NULL DEFAULT 'completed',
    notes TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    completed_at TIMESTAMPTZ,
    UNIQUE (strategy_id, model_name, model_version)
);

CREATE TABLE IF NOT EXISTS ai_extensions.model_artifacts (
    id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
    training_run_id UUID NOT NULL REFERENCES ai_extensions.model_training_runs (id) ON DELETE CASCADE,
    artifact_type TEXT NOT NULL,
    artifact_uri TEXT NOT NULL,
    checksum TEXT,
    checksum_algorithm TEXT,
    file_size_bytes BIGINT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS ai_extensions.backtest_runs (
    id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
    strategy_id TEXT NOT NULL,
    run_name TEXT,
    instrument_id TEXT,
    bar_type TEXT,
    model_versions JSONB,
    parameters JSONB,
    dataset_source TEXT,
    dataset_start TIMESTAMPTZ,
    dataset_end TIMESTAMPTZ,
    status TEXT NOT NULL DEFAULT 'completed',
    metrics JSONB,
    started_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    completed_at TIMESTAMPTZ,
    UNIQUE (strategy_id, run_name)
);

CREATE TABLE IF NOT EXISTS ai_extensions.backtest_metrics (
    id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
    backtest_run_id UUID NOT NULL REFERENCES ai_extensions.backtest_runs (id) ON DELETE CASCADE,
    metric_name TEXT NOT NULL,
    metric_value DOUBLE PRECISION,
    metadata JSONB,
    recorded_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

RESET search_path;

\echo 'AI-adaptive tables ready.'
