## 2025-10-08 Stack Verification
- `docker compose --env-file infrastructure/.env.local up -d postgres redis` verified; containers healthy on 5435/6378.
- Manual test run inserted rows into `ai_extensions.model_training_runs`, `model_artifacts`, `backtest_runs`, and `backtest_metrics`.
- Redis state writes confirmed with `StrategyCache.save_strategy_state` and direct `redis-cli` inspection.