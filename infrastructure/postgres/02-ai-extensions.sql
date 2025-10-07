\echo 'Creating AI-adaptive extension tables...'

CREATE EXTENSION IF NOT EXISTS pgcrypto;

CREATE SCHEMA IF NOT EXISTS ai_extensions;
SET search_path TO public, ai_extensions;

CREATE TABLE IF NOT EXISTS ml_optimization_log (
    id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
    strategy_id TEXT NOT NULL,
    parameter_set JSONB NOT NULL,
    objective_metric TEXT NOT NULL,
    objective_value DOUBLE PRECISION NOT NULL,
    status TEXT NOT NULL DEFAULT 'completed',
    notes TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS regime_detection_log (
    id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
    detected_regime TEXT NOT NULL,
    confidence DOUBLE PRECISION NOT NULL,
    features JSONB,
    detected_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS pattern_detection_log (
    id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
    symbol TEXT NOT NULL,
    timeframe TEXT NOT NULL,
    pattern TEXT NOT NULL,
    score DOUBLE PRECISION,
    metadata JSONB,
    detected_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS risk_events (
    id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
    strategy_id TEXT NOT NULL,
    venue TEXT,
    severity TEXT NOT NULL,
    event_type TEXT NOT NULL,
    details JSONB,
    triggered_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS sentiment_log (
    id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
    source TEXT NOT NULL,
    symbol TEXT,
    score NUMERIC NOT NULL,
    magnitude NUMERIC,
    payload JSONB,
    collected_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS performance_metrics (
    id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
    strategy_id TEXT NOT NULL,
    metric_name TEXT NOT NULL,
    metric_value DOUBLE PRECISION NOT NULL,
    window TEXT,
    calculated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

RESET search_path;

\echo 'AI-adaptive tables ready.'
