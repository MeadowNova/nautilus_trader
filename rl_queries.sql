-- ============================================================================
-- RL MULTI-FACTOR STRATEGY - USEFUL SQL QUERIES
-- ============================================================================
-- Database: nautilus_trader @ localhost:5435
-- Password: xSr7IgOZlwgkUwtnBBZoFG7N
-- Session ID: Check rl_training_sessions table
-- ============================================================================

-- 1. CHECK CURRENT SESSION STATUS
-- ============================================================================
SELECT
    session_id,
    start_time,
    end_time,
    status,
    total_episodes,
    total_steps,
    best_sharpe,
    final_portfolio_value
FROM rl_training_sessions
ORDER BY start_time DESC
LIMIT 5;

-- 2. DATA CAPTURE SUMMARY
-- ============================================================================
SELECT
    'Market Data' as table_name,
    COUNT(*) as records,
    MIN(timestamp) as first_record,
    MAX(timestamp) as latest_record,
    EXTRACT(EPOCH FROM (MAX(timestamp) - MIN(timestamp)))/60 as duration_minutes
FROM rl_market_data
UNION ALL
SELECT
    'Alpha Signals',
    COUNT(*),
    MIN(timestamp),
    MAX(timestamp),
    EXTRACT(EPOCH FROM (MAX(timestamp) - MIN(timestamp)))/60
FROM rl_alpha_signals
UNION ALL
SELECT
    'Regime States',
    COUNT(*),
    MIN(timestamp),
    MAX(timestamp),
    EXTRACT(EPOCH FROM (MAX(timestamp) - MIN(timestamp)))/60
FROM rl_regime_states
UNION ALL
SELECT
    'RL States',
    COUNT(*),
    MIN(timestamp),
    MAX(timestamp),
    EXTRACT(EPOCH FROM (MAX(timestamp) - MIN(timestamp)))/60
FROM rl_states
UNION ALL
SELECT
    'RL Actions',
    COUNT(*),
    MIN(timestamp),
    MAX(timestamp),
    EXTRACT(EPOCH FROM (MAX(timestamp) - MIN(timestamp)))/60
FROM rl_actions
UNION ALL
SELECT
    'RL Rewards',
    COUNT(*),
    MIN(timestamp),
    MAX(timestamp),
    EXTRACT(EPOCH FROM (MAX(timestamp) - MIN(timestamp)))/60
FROM rl_rewards
UNION ALL
SELECT
    'Experience Replay',
    COUNT(*),
    MIN(timestamp),
    MAX(timestamp),
    EXTRACT(EPOCH FROM (MAX(timestamp) - MIN(timestamp)))/60
FROM rl_experience_replay;

-- 3. LATEST MARKET DATA (Last 5 minutes)
-- ============================================================================
SELECT
    timestamp,
    symbol,
    close AS price,
    volume,
    ROUND(volatility_20::numeric, 4) AS vol_20d,
    ROUND(rsi_14::numeric, 2) AS rsi,
    ROUND(macd::numeric, 2) AS macd,
    ROUND(bb_width::numeric, 4) AS bb_width
FROM rl_market_data
WHERE timestamp > NOW() - INTERVAL '5 minutes'
ORDER BY timestamp DESC, symbol;

-- 4. ALPHA SIGNALS - CURRENT STATE
-- ============================================================================
SELECT
    timestamp,
    symbol,
    ROUND(momentum_signal::numeric, 3) AS momentum,
    ROUND(mean_reversion_signal::numeric, 3) AS mean_rev,
    ROUND(volatility_signal::numeric, 3) AS vol,
    ROUND(volume_signal::numeric, 3) AS volume,
    ROUND(microstructure_signal::numeric, 3) AS micro,
    ROUND(ensemble_signal::numeric, 3) AS ensemble,
    ROUND(ensemble_confidence::numeric, 3) AS confidence
FROM rl_alpha_signals
WHERE timestamp > NOW() - INTERVAL '5 minutes'
ORDER BY timestamp DESC, symbol;

-- 5. REGIME HISTORY - LAST 24 HOURS
-- ============================================================================
SELECT
    timestamp,
    symbol,
    CASE regime
        WHEN 0 THEN 'CHOPPY'
        WHEN 1 THEN 'TRENDING'
        WHEN 2 THEN 'MEAN_REVERTING'
        WHEN 3 THEN 'VOLATILE'
    END AS regime_name,
    ROUND(regime_confidence::numeric, 3) AS confidence,
    ROUND(trend_strength::numeric, 3) AS trend,
    ROUND(volatility_percentile::numeric, 3) AS vol_pct
FROM rl_regime_states
WHERE timestamp > NOW() - INTERVAL '24 hours'
ORDER BY timestamp DESC, symbol
LIMIT 20;

-- 6. RL EPISODE PERFORMANCE (When Available)
-- ============================================================================
SELECT
    episode,
    symbol,
    ROUND(total_reward::numeric, 2) AS reward,
    ROUND(total_pnl::numeric, 2) AS pnl,
    ROUND(sharpe_ratio::numeric, 2) AS sharpe,
    ROUND(max_drawdown::numeric, 4) AS drawdown,
    ROUND(win_rate::numeric, 3) AS win_rate,
    num_trades,
    ROUND(avg_epsilon::numeric, 3) AS epsilon
FROM rl_performance_metrics
ORDER BY episode DESC
LIMIT 20;

-- 7. ACTION DISTRIBUTION ANALYSIS
-- ============================================================================
SELECT
    symbol,
    CASE action
        WHEN 0 THEN 'STRONG_SELL'
        WHEN 1 THEN 'SELL'
        WHEN 2 THEN 'HOLD'
        WHEN 3 THEN 'BUY'
        WHEN 4 THEN 'STRONG_BUY'
    END AS action_name,
    COUNT(*) AS count,
    ROUND(AVG(epsilon)::numeric, 3) AS avg_epsilon,
    SUM(CASE WHEN is_exploration THEN 1 ELSE 0 END) AS exploration_count,
    ROUND(100.0 * SUM(CASE WHEN is_exploration THEN 1 ELSE 0 END) / COUNT(*)::numeric, 2) AS exploration_pct
FROM rl_actions
GROUP BY symbol, action
ORDER BY symbol, action;

-- 8. REWARD BREAKDOWN
-- ============================================================================
SELECT
    symbol,
    COUNT(*) AS num_rewards,
    ROUND(AVG(total_reward)::numeric, 3) AS avg_total,
    ROUND(AVG(pnl_reward)::numeric, 3) AS avg_pnl,
    ROUND(AVG(sharpe_reward)::numeric, 3) AS avg_sharpe,
    ROUND(AVG(drawdown_penalty)::numeric, 3) AS avg_dd_penalty,
    ROUND(AVG(transaction_cost)::numeric, 3) AS avg_cost,
    ROUND(SUM(cumulative_pnl)::numeric, 2) AS total_pnl
FROM rl_rewards
GROUP BY symbol
ORDER BY total_pnl DESC;

-- 9. EXPERIENCE REPLAY BUFFER STATUS
-- ============================================================================
SELECT
    COUNT(*) AS total_experiences,
    COUNT(DISTINCT symbol) AS num_symbols,
    COUNT(DISTINCT episode_id) AS num_episodes,
    ROUND(AVG(reward)::numeric, 3) AS avg_reward,
    ROUND(STDDEV(reward)::numeric, 3) AS std_reward,
    COUNT(CASE WHEN done THEN 1 END) AS num_terminal_states,
    MIN(timestamp) AS first_experience,
    MAX(timestamp) AS latest_experience
FROM rl_experience_replay;

-- 10. MODEL CHECKPOINTS
-- ============================================================================
SELECT
    checkpoint_name,
    timestamp,
    episode,
    step,
    ROUND(avg_reward::numeric, 3) AS avg_reward,
    ROUND(avg_sharpe::numeric, 3) AS avg_sharpe,
    ROUND(win_rate::numeric, 3) AS win_rate,
    pg_size_pretty(LENGTH(model_weights)) AS model_size
FROM rl_model_checkpoints
ORDER BY timestamp DESC
LIMIT 10;

-- 11. RECENT TRADES (When Available)
-- ============================================================================
SELECT
    timestamp,
    symbol,
    side,
    quantity,
    ROUND(price::numeric, 2) AS price,
    ROUND(value::numeric, 2) AS value,
    ROUND(commission::numeric, 2) AS commission,
    ROUND(slippage::numeric, 2) AS slippage,
    order_status
FROM rl_trades
ORDER BY timestamp DESC
LIMIT 20;

-- 12. SYMBOL PERFORMANCE COMPARISON
-- ============================================================================
WITH latest_states AS (
    SELECT DISTINCT ON (symbol)
        symbol,
        timestamp,
        position_size,
        unrealized_pnl,
        portfolio_value
    FROM rl_states
    ORDER BY symbol, timestamp DESC
)
SELECT
    symbol,
    ROUND(position_size::numeric, 4) AS position,
    ROUND(unrealized_pnl::numeric, 2) AS pnl,
    ROUND(portfolio_value::numeric, 2) AS port_value
FROM latest_states
ORDER BY unrealized_pnl DESC;

-- 13. TIME SERIES: PORTFOLIO VALUE EVOLUTION
-- ============================================================================
SELECT
    date_trunc('hour', timestamp) AS hour,
    symbol,
    ROUND(AVG(portfolio_value)::numeric, 2) AS avg_portfolio_value,
    ROUND(MIN(portfolio_value)::numeric, 2) AS min_portfolio_value,
    ROUND(MAX(portfolio_value)::numeric, 2) AS max_portfolio_value
FROM rl_states
GROUP BY date_trunc('hour', timestamp), symbol
ORDER BY hour DESC, symbol
LIMIT 50;

-- 14. VOLATILITY ANALYSIS BY SYMBOL
-- ============================================================================
SELECT
    symbol,
    ROUND(AVG(volatility_20)::numeric, 4) AS avg_vol,
    ROUND(STDDEV(volatility_20)::numeric, 4) AS vol_of_vol,
    ROUND(MIN(volatility_20)::numeric, 4) AS min_vol,
    ROUND(MAX(volatility_20)::numeric, 4) AS max_vol,
    ROUND(PERCENTILE_CONT(0.5) WITHIN GROUP (ORDER BY volatility_20)::numeric, 4) AS median_vol
FROM rl_market_data
WHERE timestamp > NOW() - INTERVAL '7 days'
GROUP BY symbol
ORDER BY avg_vol DESC;

-- 15. ALPHA FACTOR CORRELATION MATRIX
-- ============================================================================
WITH signal_data AS (
    SELECT
        symbol,
        momentum_signal AS momentum,
        mean_reversion_signal AS mean_rev,
        volatility_signal AS vol,
        volume_signal AS volume
    FROM rl_alpha_signals
    WHERE timestamp > NOW() - INTERVAL '24 hours'
)
SELECT
    'Momentum-MeanRev' AS pair,
    ROUND(CORR(momentum, mean_rev)::numeric, 3) AS correlation
FROM signal_data
UNION ALL
SELECT 'Momentum-Vol', ROUND(CORR(momentum, vol)::numeric, 3)
FROM signal_data
UNION ALL
SELECT 'Momentum-Volume', ROUND(CORR(momentum, volume)::numeric, 3)
FROM signal_data
UNION ALL
SELECT 'MeanRev-Vol', ROUND(CORR(mean_rev, vol)::numeric, 3)
FROM signal_data
UNION ALL
SELECT 'MeanRev-Volume', ROUND(CORR(mean_rev, volume)::numeric, 3)
FROM signal_data
UNION ALL
SELECT 'Vol-Volume', ROUND(CORR(vol, volume)::numeric, 3)
FROM signal_data;

-- 16. EXPERIENCE REPLAY - SAMPLE BATCH
-- ============================================================================
-- Sample 10 random experiences for inspection
SELECT
    timestamp,
    symbol,
    episode_id,
    step_id,
    action,
    ROUND(reward::numeric, 3) AS reward,
    done
FROM rl_experience_replay
ORDER BY RANDOM()
LIMIT 10;

-- 17. TRAINING CONVERGENCE CHECK
-- ============================================================================
WITH episode_metrics AS (
    SELECT
        episode,
        AVG(total_reward) AS avg_reward,
        AVG(sharpe_ratio) AS avg_sharpe,
        AVG(max_drawdown) AS avg_dd
    FROM rl_performance_metrics
    GROUP BY episode
)
SELECT
    episode,
    ROUND(avg_reward::numeric, 2) AS reward,
    ROUND(avg_sharpe::numeric, 2) AS sharpe,
    ROUND(avg_dd::numeric, 4) AS drawdown,
    ROUND((avg_reward - LAG(avg_reward) OVER (ORDER BY episode))::numeric, 2) AS reward_delta
FROM episode_metrics
ORDER BY episode DESC
LIMIT 20;

-- 18. DATABASE SIZE & GROWTH
-- ============================================================================
SELECT
    schemaname,
    tablename,
    pg_size_pretty(pg_total_relation_size(schemaname||'.'||tablename)) AS size,
    pg_total_relation_size(schemaname||'.'||tablename) AS bytes
FROM pg_tables
WHERE tablename LIKE 'rl_%'
ORDER BY bytes DESC;

-- 19. CLEANUP OLD DATA (CAUTION!)
-- ============================================================================
-- Uncomment to delete data older than 30 days
-- DELETE FROM rl_market_data WHERE timestamp < NOW() - INTERVAL '30 days';
-- DELETE FROM rl_alpha_signals WHERE timestamp < NOW() - INTERVAL '30 days';
-- DELETE FROM rl_regime_states WHERE timestamp < NOW() - INTERVAL '30 days';

-- 20. VACUUM & ANALYZE (Maintenance)
-- ============================================================================
-- Run periodically to optimize performance
-- VACUUM ANALYZE rl_market_data;
-- VACUUM ANALYZE rl_alpha_signals;
-- VACUUM ANALYZE rl_regime_states;
-- VACUUM ANALYZE rl_states;
-- VACUUM ANALYZE rl_actions;
-- VACUUM ANALYZE rl_rewards;
-- VACUUM ANALYZE rl_experience_replay;

-- ============================================================================
-- QUICK ACCESS COMMANDS
-- ============================================================================

-- Connect to database:
-- PGPASSWORD='xSr7IgOZlwgkUwtnBBZoFG7N' psql -h localhost -p 5435 -U nautilus -d nautilus_trader

-- Run query from file:
-- PGPASSWORD='xSr7IgOZlwgkUwtnBBZoFG7N' psql -h localhost -p 5435 -U nautilus -d nautilus_trader -f rl_queries.sql

-- Export results to CSV:
-- PGPASSWORD='xSr7IgOZlwgkUwtnBBZoFG7N' psql -h localhost -p 5435 -U nautilus -d nautilus_trader -c "SELECT * FROM rl_performance_metrics" --csv > performance.csv

-- ============================================================================
-- END OF QUERIES
-- ============================================================================
