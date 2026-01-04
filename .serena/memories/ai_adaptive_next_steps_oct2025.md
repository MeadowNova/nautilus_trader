## 2025-10-08 Monitoring & Paper-Trading Bridge
- Postgres/Redis persistence verified end-to-end via short trainer run and manual StrategyCache round-trip.
- Remaining blockers: full BTC/ETH backtest persistence run, Prometheus & Grafana dashboards, CCXT TradingNode paper-test workflow.
- Prioritized actions: add Postgres/Redis exporters + alerts, schedule constrained backtest with `NAUTILUS_PERSIST_BACKTESTS=1`, set up Bybit/OKX testnet credentials and TradingNode dry-run with risk limits.