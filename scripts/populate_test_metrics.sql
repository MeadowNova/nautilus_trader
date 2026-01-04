-- Populate test backtest data for Prometheus/Grafana testing

-- Insert a test backtest run
INSERT INTO ai_extensions.backtest_runs (
    id,
    strategy_id,
    run_name,
    instrument_id,
    bar_type,
    model_versions,
    parameters,
    dataset_source,
    dataset_start,
    dataset_end,
    status,
    metrics,
    started_at,
    completed_at
) VALUES (
    gen_random_uuid(),
    'ai_adaptive_v3',
    'prometheus_test_btc_20241010',
    'BTCUSDT.BINANCE',
    'BTCUSDT.BINANCE-1-MINUTE-LAST-EXTERNAL',
    '{"xgboost": "gpu", "monte_carlo": "disabled"}'::jsonb,
    '{"max_bars": 50000, "confidence_threshold": 0.75}'::jsonb,
    '/data/nautilus/BTC-USDT-1-MINUTE.parquet',
    '2024-01-01 00:00:00+00'::timestamptz,
    '2024-03-01 00:00:00+00'::timestamptz,
    'completed',
    '{"bars_processed": 50000, "duration_seconds": 145.5, "total_equity": 115000.00, "net_pnl": 15000.00, "pnl_pct": 15.0, "total_trades": 12, "win_rate": 66.67, "profit_factor": 2.5, "sharpe_ratio": 1.85}'::jsonb,
    NOW() - interval '1 hour',
    NOW() - interval '58 minutes'
) RETURNING id \gset run_id1

-- Insert metrics for the first run
INSERT INTO ai_extensions.backtest_metrics (backtest_run_id, metric_name, metric_value, recorded_at) VALUES
(:run_id1, 'bars_processed', 50000, NOW() - interval '58 minutes'),
(:run_id1, 'duration_seconds', 145.5, NOW() - interval '58 minutes'),
(:run_id1, 'total_equity', 115000.00, NOW() - interval '58 minutes'),
(:run_id1, 'net_pnl', 15000.00, NOW() - interval '58 minutes'),
(:run_id1, 'pnl_pct', 15.0, NOW() - interval '58 minutes'),
(:run_id1, 'total_trades', 12, NOW() - interval '58 minutes'),
(:run_id1, 'win_rate', 66.67, NOW() - interval '58 minutes'),
(:run_id1, 'profit_factor', 2.5, NOW() - interval '58 minutes'),
(:run_id1, 'sharpe_ratio', 1.85, NOW() - interval '58 minutes');

-- Insert a second backtest run  
INSERT INTO ai_extensions.backtest_runs (
    id,
    strategy_id,
    run_name,
    instrument_id,
    bar_type,
    model_versions,
    parameters,
    dataset_source,
    dataset_start,
    dataset_end,
    status,
    metrics,
    started_at,
    completed_at
) VALUES (
    gen_random_uuid(),
    'ai_adaptive_v3',
    'prometheus_test_eth_20241010',
    'ETHUSDT.BINANCE',
    'ETHUSDT.BINANCE-1-MINUTE-LAST-EXTERNAL',
    '{"xgboost": "gpu", "monte_carlo": "disabled"}'::jsonb,
    '{"max_bars": 50000, "confidence_threshold": 0.80}'::jsonb,
    '/data/nautilus/ETH-USDT-1-MINUTE.parquet',
    '2024-01-01 00:00:00+00'::timestamptz,
    '2024-03-01 00:00:00+00'::timestamptz,
    'completed',
    '{"bars_processed": 50000, "duration_seconds": 132.8, "total_equity": 108500.00, "net_pnl": 8500.00, "pnl_pct": 8.5, "total_trades": 18, "win_rate": 61.11, "profit_factor": 2.1, "sharpe_ratio": 1.42}'::jsonb,
    NOW() - interval '30 minutes',
    NOW() - interval '28 minutes'
) RETURNING id \gset run_id2

-- Insert metrics for the second run
INSERT INTO ai_extensions.backtest_metrics (backtest_run_id, metric_name, metric_value, recorded_at) VALUES
(:run_id2, 'bars_processed', 50000, NOW() - interval '28 minutes'),
(:run_id2, 'duration_seconds', 132.8, NOW() - interval '28 minutes'),
(:run_id2, 'total_equity', 108500.00, NOW() - interval '28 minutes'),
(:run_id2, 'net_pnl', 8500.00, NOW() - interval '28 minutes'),
(:run_id2, 'pnl_pct', 8.5, NOW() - interval '28 minutes'),
(:run_id2, 'total_trades', 18, NOW() - interval '28 minutes'),
(:run_id2, 'win_rate', 61.11, NOW() - interval '28 minutes'),
(:run_id2, 'profit_factor', 2.1, NOW() - interval '28 minutes'),
(:run_id2, 'sharpe_ratio', 1.42, NOW() - interval '28 minutes');

\echo 'Test data inserted successfully! Now checking results...'

-- Verify data was inserted
SELECT 
    run_name,
    instrument_id,
    status,
    (metrics->>'total_trades')::numeric as trades,
    (metrics->>'win_rate')::numeric as win_rate,
    (metrics->>'pnl_pct')::numeric as pnl_pct,
    completed_at
FROM ai_extensions.backtest_runs
ORDER BY completed_at DESC
LIMIT 5;
