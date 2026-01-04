## 2025-10-08 Monitoring Stack Progress
- Added AI-adaptive backtest schema + dashboard views (03-backtest-schema.sql, 04-dashboard-views.sql) and applied them to Postgres.
- Switched persistence client to shared connection pool (ajk_strategies/database/connection_pool.py) to reduce connection churn.
- Scaffolded Prometheus exporter (metrics definitions, collector, server) and hooked Prometheus to scrape `ai-adaptive-metrics`; alerts raised for metrics endpoint and Redis health.
- Metrics server currently logs Redis auth errors; need to launch with Redis credentials from infrastructure/.env.local before validation.
- Next steps: start exporter with correct env, finish Grafana dashboards/ops docs, run constrained backtest with NAUTILUS_PERSIST_BACKTESTS=1, and execute CCXT paper-trading dry run once monitoring validated.