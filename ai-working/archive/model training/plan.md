# Model Training — Nautilus Trader

## AI-Adaptive Strategy Production System

**Created:** January 2025  
**Last Reviewed:** 2025-10-07  
**Project:** AI-Adaptive Strategy  
**Focus:** Regime detection, price forecasting, and signal aggregation models  
**Working Directory:** `/home/ajk/Nautilus/nautilus_trader/`

---

## 📋 Executive Summary

Re-trained the full production trio of models (HMM regimes, LSTM price forecast, XGBoost signal aggregator) on the complete 4.3-year BTC/ETH minute dataset exported under `data/nautilus/`. Artefacts now live in `ajk_strategies/models/` and will be consumed by the live strategy once wired.

- **HMM Market Regime:** 2.26M rows, 5-state mapping persisted.  
- **LSTM Forecast:** 10-epoch cap with early stopping; validation MSE ~0.84.  
- **XGBoost Signal Aggregator:** Balanced class weights applied; hold/long/short counts ~0.63M / 0.82M / 0.81M.

**Current State:** Models trained and saved; integration and monitoring pending.

---

## 🎯 Goals
1. Maintain reproducible training pipelines for HMM, LSTM, XGB.  
2. Persist artefacts + scalers to `ajk_strategies/models/`.  
3. Capture run metadata (rows processed, metrics) for audit.  
4. Hand off artefacts to live strategy once inference adapters ready.

---

## 🛠️ Environment & Data
- **Data Source:** `data/nautilus/*.parquet` (BTC-USDT, ETH-USDT, minute bars).  
- **Hardware:** Local CPU (TensorFlow CPU build).  
- **Virtualenv:** `source activate_env.sh` (Python 3.13).  
- **Model Output Path:** `ajk_strategies/models/`.

---

## 📅 Work Breakdown

| Phase | Description | Status |
|-------|-------------|--------|
| 1 | Refresh data ingestion utilities (`features.load_price_frame`) for Nautilus parquet schema | ✅ Done |
| 2 | Train Market Regime HMM | ✅ Done (2025-10-07) |
| 3 | Train Price Forecast LSTM | ✅ Done (2025-10-07) |
| 4 | Train Signal Aggregator XGBoost | ✅ Done (2025-10-07) |
| 5 | Package artefacts + metadata | ✅ Done |
| 6 | Wire models into live strategy | ✅ Done (2025-10-07) |
| 7 | Persistence + observability rollout (DB, Redis, dashboards) | 🔄 In Progress |

---

## 🔄 Next Iteration Checklist
- ✅ Integrate new artefacts into `ai_adaptive_strategy_main.py` inference path.  
- ✅ Draft Postgres storage schema + ingestion adapters for backtest/model metadata.  
- Prototype Redis-backed strategy state + artefact cache aligned with `CacheConfig` guidance.  
- Instrument training + inference metrics for Prometheus/Grafana dashboards.  
- Log artefact hashes + metrics to `INFRASTRUCTURE_STATUS.md`.  
- Schedule periodic retraining cadence (monthly) with automated validation + retention policy.

### Progress Notes
- Training scripts now register runs and artefacts in Postgres when `NAUTILUS_PERSIST_MODELS=1`, following `infrastructure/postgres/02-ai-extensions.sql` schema conventions.
- Real-data backtest runner persists outcomes under `NAUTILUS_PERSIST_BACKTESTS=1`; synthetic scenario harnesses remain CSV-based until real market data is wired in.
- Redis cache integration implemented via `ajk_strategies/cache/redis_manager.py` with opt-in strategy state publishing (`enable_redis_cache` flag in `AIAdaptiveStrategyConfig`).

---

## 🧭 Next-Stage Development Plan

### Phase A — Database Persistence
- Extend `infrastructure/postgres` schema with tables for model artefacts, backtest runs, and optimisation logs (see `docs/api_reference/model/identifiers.md` for consistent key usage).
- Update training/backtest runners to write structured metadata to Postgres while respecting `ai-working/database_Infra layer/AI_ADAPTIVE_INFRASTRUCTURE_PLAN.md`.
- Validate migrations and ingestion through targeted BTC/ETH backtests stored via the new pipeline.

### Phase B — Redis Cache Integration
- Configure Redis persistence through `CacheConfig` (`docs/concepts/cache.md`) to retain strategy state, regime context, and latest model forecasts.
- Implement cache bootstrap utilities so `AIAdaptiveStrategy` hydrates artefacts and state efficiently on start/restart.
- Document cache failure handling and fallbacks per developer guide logging/monitoring standards.

### Phase C — Observability & Reporting
- Emit Prometheus metrics for training runs, inference scores, and trade outcomes guided by `docs/concepts/logging.md` and `docs/developer_guide/benchmarking.md`.
- Provision Grafana dashboards (regime state, XGB probabilities, PnL curves) using Postgres + Redis data sources from the infrastructure plan.
- Record artefact hashes, dataset versions, and validation KPIs in `INFRASTRUCTURE_STATUS.md` to support auditability.

### Phase D — Automation Cadence
- Script monthly retraining workflow with artefact versioning, automatic metric capture, and Ruff/pytest validation (see `docs/developer_guide/testing.md`).
- Establish retention policy for historic models and ensure documentation updates follow `docs/developer_guide/docs.md`.
