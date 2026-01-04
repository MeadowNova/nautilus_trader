## 2025-10-08 Persistence & Cache Integration
- Added `ajk_strategies/persistence/*` for Postgres access; training scripts persist runs when `NAUTILUS_PERSIST_MODELS=1`.
- Schema `ai_extensions` now holds model/backtest tables with updated indexes; Docker stack exposes Postgres on port 5435 and Redis on 6378.
- Redis cache manager (`ajk_strategies/cache/redis_manager.py`) introduced; `AIAdaptiveStrategy` publishes state/metadata when `enable_redis_cache` or `NAUTILUS_ENABLE_REDIS_CACHE=1`.