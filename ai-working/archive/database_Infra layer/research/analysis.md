# Phase 2/3 Follow-up Research Notes

## Dashboard Data Sources
- Postgres views exposed in `infrastructure/postgres/04-dashboard-views.sql` provide run-level (`v_backtest_performance`), comparative (`v_strategy_comparison`), equity curve (`v_backtest_equity_curve`), and trade-level (`v_recent_trades`) data needed for Grafana panels.
- Grafana provisioning registers `Prometheus` (uid `prometheus`) and `Postgres` (uid `postgres`) datasources via `infrastructure/monitoring/grafana/provisioning/datasources/datasource.yml`.
- Existing AI dashboards (e.g., `ai-trade-analytics.json`, `ai-strategy-performance.json`) only consume Prometheus metrics today; no panels leverage the new SQL views.

## Persistence Verification Targets
- Current `ai_extensions.backtest_trades` / `backtest_equity_curve` tables contain minimal data because prior runs used `max_bars=50k`; longer runs should populate trade/equity snapshots to validate the new views.
- `run_backtest_with_real_data.run_backtest` supports overriding `max_bars`; calling it directly allows full-history runs without editing the script (pass `max_bars=None`).
- Verify inserts post-run with `SELECT COUNT(*)` on `ai_extensions.backtest_trades` and sample rows from `v_backtest_equity_curve` to ensure Grafana queries return data.

## TradingNode Prep Considerations
- Docker compose already exposes Postgres/Redis/Grafana endpoints; TradingNode dry run will need the same `.env.local` secrets plus CCXT testnet credentials.
- Review `ajk_strategies/cache/redis_manager.py` and `ajk_strategies/database/connection_pool.py` to reuse connection helpers within the TradingNode configuration when enabling persistence.
- Identify existing Nautilus examples (e.g., `examples/sandbox/binance_spot_futures_sandbox.py`) as templates for building a minimal paper TradingNode once dashboards validate against populated data.
