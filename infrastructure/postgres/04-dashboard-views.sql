\echo 'Creating AI-adaptive dashboard views...'

SET search_path TO public, ai_extensions;

CREATE OR REPLACE VIEW ai_extensions.v_backtest_performance AS
WITH trade_stats AS (
    SELECT
        backtest_run_id,
        COUNT(*)::BIGINT AS total_trades,
        COALESCE(SUM(CASE WHEN pnl > 0 THEN 1 ELSE 0 END), 0)::BIGINT AS winning_trades,
        COALESCE(SUM(CASE WHEN pnl < 0 THEN 1 ELSE 0 END), 0)::BIGINT AS losing_trades,
        COALESCE(SUM(pnl), 0)::NUMERIC(20, 8) AS trade_pnl,
        COALESCE(SUM(fees_paid), 0)::NUMERIC(20, 8) AS total_fees,
        COALESCE(AVG(pnl), 0)::NUMERIC(20, 8) AS avg_trade_pnl,
        COALESCE(AVG(holding_period_seconds), 0)::DOUBLE PRECISION AS avg_holding_period
    FROM ai_extensions.backtest_trades
    GROUP BY backtest_run_id
), metric_pivot AS (
    SELECT
        backtest_run_id,
        MAX(CASE WHEN metric_name = 'total_pnl' THEN metric_value END) AS total_pnl,
        MAX(CASE WHEN metric_name = 'total_pnl_pct' THEN metric_value END) AS total_pnl_pct,
        MAX(CASE WHEN metric_name = 'sharpe_ratio' THEN metric_value END) AS sharpe_ratio,
        MAX(CASE WHEN metric_name = 'sortino_ratio' THEN metric_value END) AS sortino_ratio,
        MAX(CASE WHEN metric_name = 'max_drawdown' THEN metric_value END) AS max_drawdown,
        MAX(CASE WHEN metric_name = 'max_drawdown_pct' THEN metric_value END) AS max_drawdown_pct,
        MAX(CASE WHEN metric_name = 'profit_factor' THEN metric_value END) AS profit_factor,
        MAX(CASE WHEN metric_name = 'win_rate' THEN metric_value END) AS win_rate
    FROM ai_extensions.backtest_metrics
    GROUP BY backtest_run_id
)
SELECT
    br.id AS backtest_run_id,
    br.strategy_id,
    br.run_name,
    br.instrument_id,
    br.bar_type,
    br.dataset_source,
    br.dataset_start,
    br.dataset_end,
    br.status,
    br.parameters,
    br.model_versions,
    br.started_at,
    br.completed_at,
    COALESCE(mp.total_pnl, (br.metrics ->> 'total_pnl')::DOUBLE PRECISION) AS total_pnl,
    COALESCE(mp.total_pnl_pct, (br.metrics ->> 'total_pnl_pct')::DOUBLE PRECISION) AS total_pnl_pct,
    COALESCE(mp.sharpe_ratio, (br.metrics ->> 'sharpe_ratio')::DOUBLE PRECISION) AS sharpe_ratio,
    COALESCE(mp.sortino_ratio, (br.metrics ->> 'sortino_ratio')::DOUBLE PRECISION) AS sortino_ratio,
    COALESCE(mp.max_drawdown, (br.metrics ->> 'max_drawdown')::DOUBLE PRECISION) AS max_drawdown,
    COALESCE(mp.max_drawdown_pct, (br.metrics ->> 'max_drawdown_pct')::DOUBLE PRECISION) AS max_drawdown_pct,
    COALESCE(mp.profit_factor, (br.metrics ->> 'profit_factor')::DOUBLE PRECISION) AS profit_factor,
    COALESCE(mp.win_rate, (br.metrics ->> 'win_rate')::DOUBLE PRECISION) AS win_rate,
    ts.total_trades,
    ts.winning_trades,
    ts.losing_trades,
    CASE WHEN COALESCE(ts.total_trades, 0) > 0
         THEN (ts.winning_trades::DOUBLE PRECISION / ts.total_trades) * 100
         ELSE COALESCE(mp.win_rate, (br.metrics ->> 'win_rate')::DOUBLE PRECISION)
    END AS calculated_win_rate,
    ts.trade_pnl,
    ts.total_fees,
    ts.avg_trade_pnl,
    ts.avg_holding_period,
    (br.metrics -> 'risk') AS risk_metrics,
    NOW() AS refreshed_at
FROM ai_extensions.backtest_runs br
LEFT JOIN trade_stats ts ON ts.backtest_run_id = br.id
LEFT JOIN metric_pivot mp ON mp.backtest_run_id = br.id;

CREATE OR REPLACE VIEW ai_extensions.v_strategy_comparison AS
SELECT
    strategy_id,
    instrument_id,
    COUNT(*)::BIGINT AS runs,
    AVG(total_pnl) AS avg_total_pnl,
    AVG(total_pnl_pct) AS avg_total_pnl_pct,
    AVG(sharpe_ratio) AS avg_sharpe_ratio,
    AVG(max_drawdown_pct) AS avg_drawdown_pct,
    AVG(profit_factor) AS avg_profit_factor,
    AVG(calculated_win_rate) AS avg_win_rate,
    MAX(completed_at) AS last_completed_at
FROM ai_extensions.v_backtest_performance
GROUP BY strategy_id, instrument_id;

CREATE OR REPLACE VIEW ai_extensions.v_backtest_equity_curve AS
SELECT
    ec.backtest_run_id,
    br.strategy_id,
    br.run_name,
    ec.snapshot_timestamp,
    ec.equity,
    ec.cash_balance,
    ec.unrealized_pnl,
    ec.realized_pnl,
    ec.drawdown,
    ec.drawdown_pct,
    ec.leverage,
    ec.position_exposure,
    ec.metadata
FROM ai_extensions.backtest_equity_curve ec
JOIN ai_extensions.backtest_runs br ON br.id = ec.backtest_run_id;

CREATE OR REPLACE VIEW ai_extensions.v_recent_trades AS
SELECT
    bt.id AS trade_id,
    bt.backtest_run_id,
    br.strategy_id,
    br.run_name,
    bt.instrument_id,
    bt.side,
    bt.entry_timestamp,
    bt.entry_price,
    bt.exit_timestamp,
    bt.exit_price,
    bt.quantity,
    bt.pnl,
    bt.pnl_pct,
    bt.fees_paid,
    bt.annotations
FROM ai_extensions.backtest_trades bt
JOIN ai_extensions.backtest_runs br ON br.id = bt.backtest_run_id
ORDER BY bt.entry_timestamp DESC;

CREATE OR REPLACE VIEW ai_extensions.v_ml_optimization_history AS
SELECT
    ps.backtest_run_id,
    br.strategy_id,
    br.run_name,
    ps.snapshot_timestamp,
    ps.optimisation_step,
    ps.parameters,
    ps.objective_metrics,
    ps.notes
FROM ai_extensions.ml_parameter_snapshots ps
JOIN ai_extensions.backtest_runs br ON br.id = ps.backtest_run_id
ORDER BY ps.snapshot_timestamp DESC;

CREATE OR REPLACE VIEW ai_extensions.v_circuit_breaker_events AS
SELECT
    cbe.id,
    COALESCE(cbe.backtest_run_id, br.id) AS backtest_run_id,
    COALESCE(cbe.strategy_id, br.strategy_id) AS strategy_id,
    cbe.event_type,
    cbe.severity,
    cbe.triggered_at,
    cbe.trigger_reason,
    cbe.metadata
FROM ai_extensions.circuit_breaker_events cbe
LEFT JOIN ai_extensions.backtest_runs br ON br.id = cbe.backtest_run_id;

CREATE OR REPLACE VIEW ai_extensions.v_regime_summary AS
SELECT
    detected_regime,
    DATE_TRUNC('hour', detected_at) AS bucket_start,
    COUNT(*)::BIGINT AS observations,
    AVG(confidence) AS avg_confidence
FROM ai_extensions.regime_detection_log
GROUP BY detected_regime, DATE_TRUNC('hour', detected_at)
ORDER BY bucket_start DESC;

RESET search_path;

\echo 'AI-adaptive dashboard views ready.'
