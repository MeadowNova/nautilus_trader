\echo 'Creating live trading metrics tables...'

SET search_path TO public, ai_extensions;

-- ========================================================================
-- LIVE TRADING SESSION MANAGEMENT
-- ========================================================================

-- Track each live/paper trading session
CREATE TABLE IF NOT EXISTS ai_extensions.live_sessions (
    id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
    trader_id TEXT NOT NULL,
    strategy_id TEXT NOT NULL,
    session_name TEXT,
    environment TEXT NOT NULL CHECK (environment IN ('PAPER', 'LIVE', 'TESTNET')),
    exchange_venue TEXT NOT NULL,
    started_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    stopped_at TIMESTAMPTZ,
    status TEXT NOT NULL DEFAULT 'RUNNING' CHECK (status IN ('RUNNING', 'STOPPED', 'ERROR', 'PAUSED')),
    initial_balance NUMERIC(20, 8) NOT NULL,
    config JSONB,
    metadata JSONB,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_live_sessions_strategy 
    ON ai_extensions.live_sessions (strategy_id, started_at DESC);

CREATE INDEX IF NOT EXISTS idx_live_sessions_status 
    ON ai_extensions.live_sessions (status, started_at DESC);

-- ========================================================================
-- LIVE POSITIONS - Current holdings in real-time
-- ========================================================================

CREATE TABLE IF NOT EXISTS ai_extensions.live_positions (
    id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
    session_id UUID NOT NULL REFERENCES ai_extensions.live_sessions (id) ON DELETE CASCADE,
    position_id TEXT NOT NULL UNIQUE,
    instrument_id TEXT NOT NULL,
    side TEXT NOT NULL CHECK (side IN ('LONG', 'SHORT', 'FLAT')),
    quantity NUMERIC(20, 8) NOT NULL,
    avg_entry_price NUMERIC(20, 8),
    current_price NUMERIC(20, 8),
    unrealized_pnl NUMERIC(20, 8),
    realized_pnl NUMERIC(20, 8) DEFAULT 0,
    opened_at TIMESTAMPTZ NOT NULL,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    closed_at TIMESTAMPTZ,
    metadata JSONB
);

CREATE INDEX IF NOT EXISTS idx_live_positions_session 
    ON ai_extensions.live_positions (session_id, opened_at DESC);

CREATE INDEX IF NOT EXISTS idx_live_positions_instrument 
    ON ai_extensions.live_positions (instrument_id, closed_at);

-- ========================================================================
-- LIVE ORDERS - Order lifecycle tracking
-- ========================================================================

CREATE TABLE IF NOT EXISTS ai_extensions.live_orders (
    id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
    session_id UUID NOT NULL REFERENCES ai_extensions.live_sessions (id) ON DELETE CASCADE,
    order_id TEXT NOT NULL,
    client_order_id TEXT NOT NULL,
    venue_order_id TEXT,
    instrument_id TEXT NOT NULL,
    side TEXT NOT NULL CHECK (side IN ('BUY', 'SELL')),
    order_type TEXT NOT NULL CHECK (order_type IN ('MARKET', 'LIMIT', 'STOP_MARKET', 'STOP_LIMIT', 'TRAILING_STOP_MARKET')),
    quantity NUMERIC(20, 8) NOT NULL,
    price NUMERIC(20, 8),
    trigger_price NUMERIC(20, 8),
    filled_qty NUMERIC(20, 8) DEFAULT 0,
    avg_fill_price NUMERIC(20, 8),
    status TEXT NOT NULL CHECK (status IN ('INITIALIZED', 'SUBMITTED', 'ACCEPTED', 'REJECTED', 'CANCELED', 'EXPIRED', 'TRIGGERED', 'PENDING_UPDATE', 'PENDING_CANCEL', 'PARTIALLY_FILLED', 'FILLED')),
    time_in_force TEXT CHECK (time_in_force IN ('GTC', 'IOC', 'FOK', 'GTD', 'DAY', 'AT_THE_OPEN', 'AT_THE_CLOSE')),
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    submitted_at TIMESTAMPTZ,
    accepted_at TIMESTAMPTZ,
    filled_at TIMESTAMPTZ,
    canceled_at TIMESTAMPTZ,
    rejected_at TIMESTAMPTZ,
    rejection_reason TEXT,
    fees_paid NUMERIC(20, 8) DEFAULT 0,
    metadata JSONB,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_live_orders_session 
    ON ai_extensions.live_orders (session_id, created_at DESC);

CREATE INDEX IF NOT EXISTS idx_live_orders_status 
    ON ai_extensions.live_orders (status, created_at DESC);

CREATE INDEX IF NOT EXISTS idx_live_orders_instrument 
    ON ai_extensions.live_orders (instrument_id, created_at DESC);

CREATE UNIQUE INDEX IF NOT EXISTS idx_live_orders_client_id 
    ON ai_extensions.live_orders (client_order_id);

-- ========================================================================
-- LIVE EXECUTIONS - Trade fills
-- ========================================================================

CREATE TABLE IF NOT EXISTS ai_extensions.live_executions (
    id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
    session_id UUID NOT NULL REFERENCES ai_extensions.live_sessions (id) ON DELETE CASCADE,
    order_id UUID NOT NULL REFERENCES ai_extensions.live_orders (id) ON DELETE CASCADE,
    execution_id TEXT NOT NULL UNIQUE,
    instrument_id TEXT NOT NULL,
    side TEXT NOT NULL CHECK (side IN ('BUY', 'SELL')),
    quantity NUMERIC(20, 8) NOT NULL,
    price NUMERIC(20, 8) NOT NULL,
    commission NUMERIC(20, 8) DEFAULT 0,
    commission_currency TEXT,
    executed_at TIMESTAMPTZ NOT NULL,
    liquidity_side TEXT CHECK (liquidity_side IN ('MAKER', 'TAKER')),
    metadata JSONB,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_live_executions_session 
    ON ai_extensions.live_executions (session_id, executed_at DESC);

CREATE INDEX IF NOT EXISTS idx_live_executions_order 
    ON ai_extensions.live_executions (order_id, executed_at);

-- ========================================================================
-- LIVE TRADES - Completed round-trip trades (entry + exit)
-- ========================================================================

CREATE TABLE IF NOT EXISTS ai_extensions.live_trades (
    id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
    session_id UUID NOT NULL REFERENCES ai_extensions.live_sessions (id) ON DELETE CASCADE,
    trade_id TEXT NOT NULL,
    instrument_id TEXT NOT NULL,
    side TEXT NOT NULL CHECK (side IN ('LONG', 'SHORT')),
    entry_order_id UUID REFERENCES ai_extensions.live_orders (id),
    exit_order_id UUID REFERENCES ai_extensions.live_orders (id),
    quantity NUMERIC(20, 8) NOT NULL,
    entry_price NUMERIC(20, 8) NOT NULL,
    exit_price NUMERIC(20, 8),
    entry_timestamp TIMESTAMPTZ NOT NULL,
    exit_timestamp TIMESTAMPTZ,
    holding_period_seconds DOUBLE PRECISION,
    pnl NUMERIC(20, 8),
    pnl_pct NUMERIC(10, 4),
    fees_total NUMERIC(20, 8) DEFAULT 0,
    status TEXT NOT NULL DEFAULT 'OPEN' CHECK (status IN ('OPEN', 'CLOSED', 'PARTIAL')),
    metadata JSONB,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_live_trades_session 
    ON ai_extensions.live_trades (session_id, entry_timestamp DESC);

CREATE INDEX IF NOT EXISTS idx_live_trades_instrument 
    ON ai_extensions.live_trades (instrument_id, status, entry_timestamp DESC);

-- ========================================================================
-- LIVE EQUITY CURVE - Real-time account performance snapshots
-- ========================================================================

CREATE TABLE IF NOT EXISTS ai_extensions.live_equity_snapshots (
    id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
    session_id UUID NOT NULL REFERENCES ai_extensions.live_sessions (id) ON DELETE CASCADE,
    snapshot_timestamp TIMESTAMPTZ NOT NULL,
    total_equity NUMERIC(20, 8) NOT NULL,
    cash_balance NUMERIC(20, 8) NOT NULL,
    unrealized_pnl NUMERIC(20, 8) DEFAULT 0,
    realized_pnl NUMERIC(20, 8) DEFAULT 0,
    total_pnl NUMERIC(20, 8) DEFAULT 0,
    total_pnl_pct NUMERIC(10, 4),
    drawdown NUMERIC(20, 8),
    drawdown_pct NUMERIC(10, 4),
    peak_equity NUMERIC(20, 8),
    num_open_positions INTEGER DEFAULT 0,
    total_position_value NUMERIC(20, 8) DEFAULT 0,
    leverage DOUBLE PRECISION DEFAULT 1.0,
    margin_used NUMERIC(20, 8) DEFAULT 0,
    margin_available NUMERIC(20, 8),
    metadata JSONB,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE (session_id, snapshot_timestamp)
);

CREATE INDEX IF NOT EXISTS idx_live_equity_snapshots_session 
    ON ai_extensions.live_equity_snapshots (session_id, snapshot_timestamp DESC);

-- ========================================================================
-- LIVE PERFORMANCE METRICS - Aggregate statistics per session
-- ========================================================================

CREATE TABLE IF NOT EXISTS ai_extensions.live_performance_metrics (
    id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
    session_id UUID NOT NULL REFERENCES ai_extensions.live_sessions (id) ON DELETE CASCADE,
    calculated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    
    -- Trade statistics
    total_trades INTEGER DEFAULT 0,
    winning_trades INTEGER DEFAULT 0,
    losing_trades INTEGER DEFAULT 0,
    win_rate NUMERIC(10, 4),
    
    -- P&L metrics
    total_pnl NUMERIC(20, 8),
    total_pnl_pct NUMERIC(10, 4),
    avg_win NUMERIC(20, 8),
    avg_loss NUMERIC(20, 8),
    largest_win NUMERIC(20, 8),
    largest_loss NUMERIC(20, 8),
    profit_factor NUMERIC(10, 4),
    
    -- Risk metrics
    max_drawdown NUMERIC(20, 8),
    max_drawdown_pct NUMERIC(10, 4),
    sharpe_ratio NUMERIC(10, 4),
    sortino_ratio NUMERIC(10, 4),
    
    -- Execution metrics
    avg_holding_period_seconds DOUBLE PRECISION,
    total_fees_paid NUMERIC(20, 8),
    
    -- Position metrics
    max_concurrent_positions INTEGER,
    avg_position_size NUMERIC(20, 8),
    
    metadata JSONB,
    UNIQUE (session_id, calculated_at)
);

CREATE INDEX IF NOT EXISTS idx_live_performance_metrics_session 
    ON ai_extensions.live_performance_metrics (session_id, calculated_at DESC);

-- ========================================================================
-- LIVE ALERTS - Risk events and notifications
-- ========================================================================

CREATE TABLE IF NOT EXISTS ai_extensions.live_alerts (
    id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
    session_id UUID NOT NULL REFERENCES ai_extensions.live_sessions (id) ON DELETE CASCADE,
    alert_type TEXT NOT NULL CHECK (alert_type IN ('RISK_LIMIT', 'DRAWDOWN', 'POSITION_SIZE', 'ORDER_REJECTED', 'CONNECTION_LOSS', 'STRATEGY_ERROR', 'PERFORMANCE', 'CUSTOM')),
    severity TEXT NOT NULL CHECK (severity IN ('INFO', 'WARNING', 'CRITICAL', 'EMERGENCY')),
    title TEXT NOT NULL,
    message TEXT NOT NULL,
    triggered_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    acknowledged BOOLEAN DEFAULT FALSE,
    acknowledged_at TIMESTAMPTZ,
    metadata JSONB
);

CREATE INDEX IF NOT EXISTS idx_live_alerts_session 
    ON ai_extensions.live_alerts (session_id, triggered_at DESC);

CREATE INDEX IF NOT EXISTS idx_live_alerts_severity 
    ON ai_extensions.live_alerts (severity, acknowledged, triggered_at DESC);

-- ========================================================================
-- VIEWS FOR PROMETHEUS METRICS COLLECTION
-- ========================================================================

-- Current active sessions summary
CREATE OR REPLACE VIEW ai_extensions.v_live_sessions_current AS
SELECT
    ls.id AS session_id,
    ls.trader_id,
    ls.strategy_id,
    ls.session_name,
    ls.environment,
    ls.exchange_venue,
    ls.status,
    ls.started_at,
    ls.initial_balance,
    EXTRACT(EPOCH FROM (COALESCE(ls.stopped_at, NOW()) - ls.started_at)) AS runtime_seconds,
    
    -- Latest equity snapshot
    les.total_equity,
    les.cash_balance,
    les.unrealized_pnl,
    les.realized_pnl,
    les.total_pnl,
    les.total_pnl_pct,
    les.drawdown_pct,
    les.num_open_positions,
    
    -- Latest performance metrics
    lpm.total_trades,
    lpm.win_rate,
    lpm.profit_factor,
    lpm.sharpe_ratio,
    lpm.total_fees_paid
    
FROM ai_extensions.live_sessions ls
LEFT JOIN LATERAL (
    SELECT * FROM ai_extensions.live_equity_snapshots
    WHERE session_id = ls.id
    ORDER BY snapshot_timestamp DESC
    LIMIT 1
) les ON TRUE
LEFT JOIN LATERAL (
    SELECT * FROM ai_extensions.live_performance_metrics
    WHERE session_id = ls.id
    ORDER BY calculated_at DESC
    LIMIT 1
) lpm ON TRUE
WHERE ls.status = 'RUNNING';

-- Open positions summary
CREATE OR REPLACE VIEW ai_extensions.v_live_positions_open AS
SELECT
    lp.session_id,
    ls.strategy_id,
    ls.environment,
    lp.instrument_id,
    lp.side,
    lp.quantity,
    lp.avg_entry_price,
    lp.current_price,
    lp.unrealized_pnl,
    lp.realized_pnl,
    lp.opened_at,
    EXTRACT(EPOCH FROM (NOW() - lp.opened_at)) AS holding_duration_seconds
FROM ai_extensions.live_positions lp
JOIN ai_extensions.live_sessions ls ON ls.id = lp.session_id
WHERE lp.closed_at IS NULL;

-- Recent orders summary
CREATE OR REPLACE VIEW ai_extensions.v_live_orders_recent AS
SELECT
    lo.session_id,
    ls.strategy_id,
    ls.environment,
    lo.instrument_id,
    lo.side,
    lo.order_type,
    lo.status,
    lo.quantity,
    lo.filled_qty,
    lo.price,
    lo.avg_fill_price,
    lo.created_at,
    lo.filled_at,
    EXTRACT(EPOCH FROM (COALESCE(lo.filled_at, lo.canceled_at, NOW()) - lo.created_at)) AS order_duration_seconds
FROM ai_extensions.live_orders lo
JOIN ai_extensions.live_sessions ls ON ls.id = lo.session_id
WHERE lo.created_at > NOW() - INTERVAL '24 hours'
ORDER BY lo.created_at DESC;

-- Trade performance by instrument
CREATE OR REPLACE VIEW ai_extensions.v_live_trades_performance AS
SELECT
    lt.session_id,
    ls.strategy_id,
    ls.environment,
    lt.instrument_id,
    COUNT(*) AS total_trades,
    COUNT(*) FILTER (WHERE lt.pnl > 0) AS winning_trades,
    COUNT(*) FILTER (WHERE lt.pnl <= 0) AS losing_trades,
    ROUND(
        (COUNT(*) FILTER (WHERE lt.pnl > 0)::NUMERIC / NULLIF(COUNT(*), 0)) * 100,
        2
    ) AS win_rate_pct,
    SUM(lt.pnl) AS total_pnl,
    AVG(lt.pnl) AS avg_pnl,
    SUM(lt.fees_total) AS total_fees,
    AVG(lt.holding_period_seconds) AS avg_holding_seconds
FROM ai_extensions.live_trades lt
JOIN ai_extensions.live_sessions ls ON ls.id = lt.session_id
WHERE lt.status = 'CLOSED'
GROUP BY lt.session_id, ls.strategy_id, ls.environment, lt.instrument_id;

RESET search_path;

\echo 'Live trading metrics tables created successfully.'
\echo 'Views created: v_live_sessions_current, v_live_positions_open, v_live_orders_recent, v_live_trades_performance'
