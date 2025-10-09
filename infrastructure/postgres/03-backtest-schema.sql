\echo 'Creating AI-adaptive dashboard tables...'

SET search_path TO public, ai_extensions;

-- Detailed trade records captured per backtest run.
CREATE TABLE IF NOT EXISTS ai_extensions.backtest_trades (
    id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
    backtest_run_id UUID NOT NULL REFERENCES ai_extensions.backtest_runs (id) ON DELETE CASCADE,
    trade_sequence INTEGER,
    instrument_id TEXT NOT NULL,
    side TEXT NOT NULL CHECK (side IN ('LONG', 'SHORT', 'BUY', 'SELL')),
    position_type TEXT CHECK (position_type IN ('OPEN', 'CLOSE', 'REVERSAL')),
    entry_timestamp TIMESTAMPTZ NOT NULL,
    entry_price NUMERIC(20, 8) NOT NULL,
    entry_order_id TEXT,
    exit_timestamp TIMESTAMPTZ,
    exit_price NUMERIC(20, 8),
    exit_order_id TEXT,
    quantity NUMERIC(20, 8) NOT NULL,
    fees_paid NUMERIC(20, 8) DEFAULT 0,
    pnl NUMERIC(20, 8),
    pnl_pct NUMERIC(10, 4),
    holding_period_seconds DOUBLE PRECISION,
    annotations JSONB,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_backtest_trades_run
    ON ai_extensions.backtest_trades (backtest_run_id, entry_timestamp);

CREATE INDEX IF NOT EXISTS idx_backtest_trades_instrument
    ON ai_extensions.backtest_trades (instrument_id, side, entry_timestamp);

-- Equity curve / performance snapshots to drive Grafana time-series panels.
CREATE TABLE IF NOT EXISTS ai_extensions.backtest_equity_curve (
    id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
    backtest_run_id UUID NOT NULL REFERENCES ai_extensions.backtest_runs (id) ON DELETE CASCADE,
    snapshot_timestamp TIMESTAMPTZ NOT NULL,
    equity NUMERIC(20, 8) NOT NULL,
    cash_balance NUMERIC(20, 8),
    unrealized_pnl NUMERIC(20, 8),
    realized_pnl NUMERIC(20, 8),
    drawdown NUMERIC(20, 8),
    drawdown_pct NUMERIC(10, 4),
    leverage DOUBLE PRECISION,
    position_exposure NUMERIC(20, 8),
    metadata JSONB,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE (backtest_run_id, snapshot_timestamp)
);

CREATE INDEX IF NOT EXISTS idx_backtest_equity_curve_run
    ON ai_extensions.backtest_equity_curve (backtest_run_id, snapshot_timestamp);

-- Parameter snapshots recorded during optimisation sweeps or adaptive runs.
CREATE TABLE IF NOT EXISTS ai_extensions.ml_parameter_snapshots (
    id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
    backtest_run_id UUID NOT NULL REFERENCES ai_extensions.backtest_runs (id) ON DELETE CASCADE,
    snapshot_timestamp TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    optimisation_step INTEGER,
    parameters JSONB NOT NULL,
    objective_metrics JSONB,
    notes TEXT
);

CREATE INDEX IF NOT EXISTS idx_ml_parameter_snapshots_run
    ON ai_extensions.ml_parameter_snapshots (backtest_run_id, snapshot_timestamp);

-- Circuit breaker & risk-control events emitted during simulation/paper trading.
CREATE TABLE IF NOT EXISTS ai_extensions.circuit_breaker_events (
    id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
    backtest_run_id UUID REFERENCES ai_extensions.backtest_runs (id) ON DELETE CASCADE,
    strategy_id TEXT,
    event_type TEXT NOT NULL,
    severity TEXT CHECK (severity IN ('info', 'warning', 'critical')),
    triggered_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    trigger_reason TEXT,
    metadata JSONB
);

CREATE INDEX IF NOT EXISTS idx_circuit_breaker_events_run
    ON ai_extensions.circuit_breaker_events (backtest_run_id, triggered_at DESC);

RESET search_path;

\echo 'AI-adaptive dashboard tables ready.'
