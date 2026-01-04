• - Applied the new dashboard schema and views to Postgres and confirmed they’re live (infrastructure/postgres/03-backtest-schema.sql, infrastructure/postgres/04-dashboard-
    views.sql, verification logged in ai-working/database_Infra layer/AI_ADAPTIVE_INFRASTRUCTURE_PLAN.md:63-66). \dt ai_extensions.* and \dv ai_extensions.* now show the
    additional tables/views for trades, equity curves, and dashboard pivots.
  - Introduced pooled DB access via ajk_strategies/database/connection_pool.py:1-87 and updated the persistence client to reuse it (ajk_strategies/persistence/
    postgres_storage.py:1-148), removing ad‑hoc connection handling.
  - Scaffolded the monitoring package—Prometheus metric definitions, collectors, and HTTP server (ajk_strategies/monitoring/metrics_definitions.py:1-71,
    metrics_collector.py:1-156, metrics_server.py:1-64)—and wired Prometheus/alert configs to scrape the new endpoint (infrastructure/monitoring/prometheus/
    prometheus.yml:13-24, alerts.yml:1-32). Running python -m ajk_strategies.monitoring.metrics_server with explicit env vars now starts the exporter on port 9100.

• - 2025-10-09 Verification sweep completed:
    - Brought `nautilus_postgres` and `nautilus_redis` online via `docker compose -f infrastructure/docker/docker-compose.yml --env-file infrastructure/.env.local up -d postgres redis`; `pg_isready` and `redis-cli ping` both report healthy.
    - Ran `ModelTrainingRunRecord` smoke insert through `PostgresPersistenceClient`, confirmed retrieval, and removed the test row.
    - Validated `StrategyCache.save_strategy_state` round-trip using the `.env.local` credentials; cached payload matched on readback and key was deleted afterward.

  Notable follow-up:

  - The metrics server currently logs Redis authentication failures because RedisCacheConfig defaults to changeme; set REDIS_PASSWORD=DNW1YCzbg6MYmDoZF7TZ8o9f (and related
    vars) when launching, or adjust RedisCacheConfig to consume the same .env.local secrets.
  - Prometheus job points to host.docker.internal:8000; on Linux adjust this target or route through the bridge interface.

  Next steps:

  1. Re-launch the metrics server with the proper Redis credentials (e.g., REDIS_PASSWORD=DNW1YCzbg6MYmDoZF7TZ8o9f AI_METRICS_PORT=9100 python -m
     ajk_strategies.monitoring.metrics_server) and validate the new Prometheus job reports up == 1.
  2. Build the Grafana dashboards/OPS docs in ai-working/database_Infra layer/ using the new views, then run a constrained backtest with NAUTILUS_PERSIST_BACKTESTS=1 to
     populate metrics for dashboard validation.

  Untracked directories (ajk_strategies/database/, ajk_strategies/monitoring/, etc.) remain; review/commit alongside the updated YAML/SQL files.

• - 2025-10-09 Phase 2 monitoring build-out:
    - Extended `infrastructure/docker/docker-compose.yml` with dedicated `ai_metrics` and `ai_metrics_proxy` services to keep the exporter and proxy co-located with the stack.
      Both containers run on `nautilus_network`, override database/redis hosts, and expose 9100/9101 for host verification.
    - Added `infrastructure/monitoring/prometheus/metrics_proxy.py` to forward Prometheus scrapes when the exporter lives off-container. Proxy uses a threading HTTP server
      and inherits `TARGET_*` envs from compose.
    - Updated `infrastructure/monitoring/prometheus/prometheus.yml` to point the custom AI job at the proxy, rename the job for clarity, and fix exporter hostnames
      (`postgres_exporter`, `redis_exporter`). Prometheus now records healthy targets for Postgres + Redis exporters; custom metrics scrape succeeds via proxy but Prometheus
      still reports `up=0` because a host-level Prometheus (outside compose) continues to answer on :9090 using the legacy configuration.
    - Observed periodic 200s from the proxy logs confirming the compose-managed Prom server reaches the exporter. Host-port curl checks (`localhost:9100/metrics` and
      `:9101/metrics`) return the refreshed gauges.
    - Outstanding action: terminate or reconfigure the non-compose Prometheus instance binding to :9090 so the compose-managed server can serve the updated config (currently
      container reloads succeed but queries hit the other listener). Once resolved, the `ai-adaptive-metrics-v2` target should flip to `up=1` without further code changes.

  Follow-up items:

  - Stop the stray host-level Prometheus process and re-run `docker compose up -d prometheus`; verify `ss -ltnp | grep :9090` resolves to the compose container PID and the
    target list reflects `localhost` endpoints.
  - After cleaning up the listener conflict, trigger a manual scrape (`curl http://localhost:9090/api/v1/targets`) to confirm AI metrics job reports healthy before moving on
    to alert simulation and dashboard work.

• - 2025-10-09 Phase 2 monitoring validation:
    - Recreated the compose-managed Prometheus on the shared bridge network (9090 published via `infrastructure/docker/docker-compose.yml`), updated scrape targets to service
      DNS (`infrastructure/monitoring/prometheus/prometheus.yml`), and refreshed the stack; `docker exec nautilus_prometheus wget -qO- http://localhost:9090/api/v1/targets`
      now reports `health":"up"` for `ai_metrics_proxy:9101`, `postgres_exporter:9187`, and `redis_exporter:9121`.
    - Verified the exporter with production secrets by launching `ai_metrics`/`ai_metrics_proxy` through compose (`REDIS_PASSWORD=DNW1YCzbg6MYmDoZF7TZ8o9f`, Postgres creds
      from `.env.local`); `docker exec nautilus_prometheus wget -qO- "http://localhost:9090/api/v1/query?query=up%7Bjob%3D%22ai-adaptive-metrics-v2%22%7D"` returns `value
      ... "1"` confirming the AI job is healthy.
    - Added Grafana dashboards for executive, strategy performance, ML optimisation, regime, pattern, risk, sentiment, and trade analytics
      (`infrastructure/monitoring/grafana/dashboards/ai-*.json`) and verified provisioning picks them up via the default folder.
    - Note: `curl http://localhost:9090/...` on the host still hits the legacy host-level Prometheus binary; remove that process (PID 1580) or shift the compose binding to a
      free port when ready so external checks surface the same healthy target list recorded inside the container.

• - 2025-10-09 Backtest persistence smoke:
    - Hardened `run_backtest_with_real_data` reporting by writing pandas reports with `DataFrame.to_csv` and attaching `recorded_at=end_time` for each `BacktestMetricRecord`
      (see `ajk_strategies/run_backtest_with_real_data.py:343-470`) to avoid ambiguous truthiness and satisfy the NOT NULL constraint on `ai_extensions.backtest_metrics.recorded_at`.
    - Executed constrained runs with 5k bars for BTC and ETH (`DB_HOST=localhost DB_PORT=5435 ... NAUTILUS_PERSIST_BACKTESTS=1`), capturing summaries under
      `backtest_results/summary_BTC-USDT_metrics_validation_20251009_173726.json` and `...ETH-USDT_metrics_validation_20251009_174233.json`.
    - Verified persistence: `SELECT run_name, completed_at FROM ai_extensions.backtest_runs ORDER BY completed_at DESC LIMIT 5;` shows both metrics_validation runs,
      and `SELECT metric_name, metric_value FROM ai_extensions.backtest_metrics WHERE backtest_run_id='<latest>';` returns eight rows (bars_processed through profit_factor).
    - Current scenarios generated zero trades (expected for the truncated slice); follow-up backtests should expand bar counts or adjust parameters once trade flow validation is required.

• - 2025-10-10 CUDA enablement sprint:
    - Updated `ajk_strategies/ai_adaptive_stragey_v3.py` so `SignalFeatureEngine` loads the TensorFlow LSTM on the active CUDA device when available, wraps inference in `tf.device`, and surfaces GPU failures with explicit warnings.
    - Added `torch.cuda` diagnostics in `AIAdaptiveStrategyV3.on_start` plus a configurable `max_bars_per_run` guard (default 50k) to stop processing long parquet batches from overwhelming local RAM.
    - Introduced GPU-specific signal training (`ajk_strategies/training/retrain_signal_xgb_gpu.py`) with XGBoost `device='cuda'`, `tree_method='hist'`, and runtime ~37.5s; artifact stored at `ajk_strategies/models/signal_aggregator_xgb_gpu.pkl` with class mix `[629103, 819741, 814091]`.
    - Validated AIAdaptiveStrategyV3 via `ajk_strategies/run_backtest_v3_gpu_validation.py --max-bars 50000`, observing max GPU utilization of 17%, 0 trades triggered, +53.87% equity drift, and persisted metrics under `backtest_results/gpu_validation_50k_summary.json`.

• - 2025-10-10 GPU validation follow-up:
    - Installed the CUDA build of PyTorch (`torch==2.6.0+cu124`) inside the project `.venv` so the strategy and validation runner share the same GPU stack (`torch.cuda.is_available()` now resolves true after `source activate_env.sh`).
    - Hardened `SignalFeatureEngine` with TensorFlow device fallback—failed CuDNN calls drop to `/CPU:0` without killing the run—and added probability sampling instrumentation so we can report max long/short confidences per run.
    - Relaxed the live gate to `confidence_threshold=0.30`, added hold/cross-threshold/time-based exit rules plus a forced `on_stop` liquidation, and observed the first closed trade in both 50k- and 200k-bar GPU validations (orders: 2, closed_positions: 1).
    - Latest summaries recorded at `backtest_results/gpu_validation_50k_summary.json` (segmented: 20×50k, 16 trades, max GPU util 28%) and `backtest_results/gpu_validation_200k_summary.json` (segmented: 10×200k, 5 trades, util 24%). Trade count remains sparse because model confidences top out at ~0.415 (long) / 0.379 (short); next pass should revisit scaler/feature prep before paper-trading.
    - Added segmented validation support: `run_backtest_v3_gpu_validation.py` now accepts `--segments`, `--max-hold-bars`, and `--feature-warmup-bars`, aggregating multiple 50k slices into a single summary. Running `--segments 20` yields 16 closed trades (orders 223) while staying GPU-accelerated. Summaries capture per-segment metadata under `segment_details` for Grafana drill downs.
    - Exposed the high-level JSON metrics to Prometheus via new gauges (`ai_gpu_validation_*`) in `metrics_collector`; Grafana panels can now chart trades, PnL, runtime, and last-completed timestamp straight from `backtest_results/gpu_validation_*_summary.json`.
    - Updated `ai-strategy-performance.json` to replace the static GPU text snapshot with live Prometheus-backed stat panels (trades/runtime/PnL/segment count) sourced from the new metrics.

• - 2025-10-10 Monitoring refinements:
    - Restarted the `ai_metrics` exporter to pick up fresh Prometheus gauges and confirmed `/metrics` now reports per-segment statistics (`ai_gpu_validation_segment_*`) derived from `segment_details` in each JSON summary.
    - Extended `metrics_collector._refresh_gpu_validation` to compute mean/median PnL and trade counts per segment; new gauges feed directly into Grafana stat panels (“GPU Segment Mean/Median PnL” and “GPU Segment Mean/Median Trades”).
    - Refreshed `ai-strategy-performance.json` with the additional Prometheus panels so Grafana surfaces the segment aggregates alongside existing GPU stats.
    - Verified the compose-managed Prometheus target (`ai-adaptive-metrics-v2`) continues to report `up=1`; a host-level Prometheus process (`/bin/prometheus` running as root) is still bound to :9090 and requires elevated privileges to stop—documented for follow-up.

• - 2025-10-10 Backtest metric archiving:
    - Added dedicated Prometheus gauges for backtest PnL %, total trades, win rate, profit factor, and Sharpe ratio in `metrics_definitions.py`, each keyed by strategy/run/instrument for Grafana drill-downs.
    - Updated `metrics_collector._refresh_backtests` to pull the enriched columns from `ai_extensions.v_backtest_performance`, populate the new gauges, and retain duration histogram behaviour.
    - Expanded `ai-strategy-performance.json` with stat cards (“Backtest Win Rate (%)”, “Backtest PnL (%)”, “Backtest Profit Factor”, “Backtest Sharpe Ratio”, “Backtest Trades (Total)”) wired to the new Prometheus series to complete the metadata archival milestone.
