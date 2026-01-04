# AI-Adaptive Infrastructure – Phase Tracker

**Last Updated:** 2025-10-10  
**Scope:** Monitoring bring-up, persistence validation, and paper-trading readiness

---

## Phase 1 — Persistence & Cache (✅ Complete)
- Postgres schema `ai_extensions` live; backtest + model tables populated via short trainer runs.
- Redis cache verified with `StrategyCache` round-trip on container port 6378.
- Model retraining artefacts stored under `ajk_strategies/models/` and hashed.

## Phase 2 — Monitoring Foundations (🚧 In Progress)
- [x] Schema uplift applied (`03-backtest-schema.sql`, `04-dashboard-views.sql`).
- [x] Connection pooling and persistence client refactor.
- [x] Prometheus metrics package scaffolded; Prometheus scraping job/alerts created.
- [x] Launch metrics server with Redis secrets (`REDIS_PASSWORD`, etc.) and confirm healthy scrape from Prometheus.
- [x] Build Grafana dashboards (executive overview, strategy performance, ML optimisation, regime analysis, pattern detection, risk, sentiment, trade analysis) and commit JSON under `infrastructure/monitoring/grafana/`.
- [x] Document metrics validation steps in `implementation.md` / `INFRASTRUCTURE_STATUS.md`.

## Phase 3 — Backtest Persistence Validation (🚧 In Progress)
- [x] Run constrained BTC/ETH backtests with `NAUTILUS_PERSIST_BACKTESTS=1` to populate new tables (`backtest_runs`, `backtest_metrics`, views). Runs recorded as `BTC-USDT_metrics_validation_20251009_173726` and `ETH-USDT_metrics_validation_20251009_174233`.
- [x] Capture verification queries (`SELECT id, run_name FROM ai_extensions.backtest_runs ORDER BY completed_at DESC LIMIT 5;`, `SELECT metric_name, metric_value FROM ai_extensions.backtest_metrics WHERE backtest_run_id = '<latest>';`) and log results in implementation notes.
- [x] Perform GPU validation runs with `AIAdaptiveStrategyV3` (`ajk_strategies/run_backtest_v3_gpu_validation.py`), saving metrics to `backtest_results/gpu_validation_50k_summary.json` (latest segmented run: 20×50k slices → 16 trades, +14_404.84% aggregate, max GPU util 28%) and `backtest_results/gpu_validation_200k_summary.json` (10×200k slices → 5 trades, GPU util 24%).
- [x] Archive run metadata in Prometheus/Grafana dashboards (new Prometheus gauges for PnL %, trades, win rate, profit factor, Sharpe, segment aggregates; Grafana stat panels wired to `ai_backtest_*` + `ai_gpu_validation_*`).

## Phase 4 — Paper-Trading Enablement (🚧 Planned)
- Configure CCXT testnet credentials in `.env.local`; ensure `test_ccxt_fallback.py` passes (expect KuCoin fallback if Bybit blocked).
- Build TradingNode config enabling Postgres/Redis/metrics; run dry run and monitor alerts.
- Draft operational runbooks (start/stop, credential rotation, Redis recovery, alert escalation) and place under `ai-working/database_Infra layer/`.

## Phase 5 — Documentation & Handoff (🚧 Planned)
- Update `implementation.md`, `OPERATIONS.md`, `DASHBOARD_GUIDE.md` with monitoring dashboards, exporter usage, and validation commands.
- Capture screenshots and Prometheus queries for `INFRASTRUCTURE_STATUS.md`.
- Retire duplicate “dashboard enhancing” directories after confirming no remaining gaps.

---

### Immediate Next Steps
1. Stop or relocate the legacy Prometheus instance bound to `:9090` so host-level checks hit the compose-managed config.
2. Schedule refreshed GPU validation runs (50k + 200k) with realism-focused scaler tweaks; compare Prometheus aggregates against JSON summaries to confirm signal quality.
3. Prepare paper TradingNode dry run once dashboards validated; ensure CCXT smoke tests pass beforehand.
4. Expand Grafana with Postgres equity curve panels once longer persisted runs populate `v_backtest_equity_curve`; validate queries return data.
5. Simulate alert pathways (stale metrics, Redis offline, backtest failures) now that dashboards are live and capture remediation steps for the runbook.
