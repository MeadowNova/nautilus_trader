# Implementation Guide: Database and Infrastructure and Performance Monitoring

## Overview
- **Last Updated:** 2025-10-07
- **Current Phase:** Infrastructure hardening + observability
- **Objective:** Ensure Docker stack is production ready, document runbooks, and keep CCXT connectivity checks aligned with docs.

---

## Session Notes

### Infrastructure Stack
- `docker-compose.yaml` at repo root now mirrors secure defaults (auth-enabled Redis, Postgres 16, shared config file) and expects secrets from `infrastructure/.env.local` created by `setup.sh`.
- `infrastructure/docker/docker-compose.yml`
  - Added `env_file` consumption via setup script (`docker compose --env-file ../.env.local`) so interpolation works.
  - Redis health check authenticates with `redis-cli -a ${REDIS_PASSWORD}`.
  - Host port overrides recorded in `.env.local` (`DB_PORT=5433`, `REDIS_PORT=6378`) to avoid conflicts with local services.
  - Grafana no longer writes to the trading database; it falls back to the bundled SQLite store.
  - Postgres exporter and Redis exporter inherit credentials from `.env.local`.
- `infrastructure/postgres/postgresql.conf` tuned for an 8 GB workstation (lower shared buffers, work_mem) to avoid OOM on laptops.

### Setup Automation
- `infrastructure/setup.sh`
  - Detects `docker compose` vs `docker-compose` and uses `--env-file ../.env.local` so env interpolation works without manual exports.
  - Forces `COMPOSE_PARALLEL_LIMIT=1` to avoid the Docker Compose plugin’s `fatal error: concurrent map writes` bug when pulling images in parallel.
  - Clears Windows credential helper references when they block pulls (`~/.docker/config.json` backup/overwrite step documented in session log).
  - Verifies `openssl` and `curl` in addition to Docker and `psql`.
  - Loads secrets from `.env.local` regardless of whether the file already existed.

### CCXT Diagnostics
- Restored `test_ccxt_integration.py` and `test_ccxt_fallback.py` as lightweight smoke tests for public CCXT endpoints. Use them before running backtests or spinning up paper accounts.
  - `test_ccxt_integration.py --exchange bybit` runs a deeper check against a single venue.
  - `test_ccxt_fallback.py` iterates across Bybit, KuCoin, OKX, Bitfinex, MEXC, Gate.io and recommends the first responsive venue.
  - 2025-10-07 run: Bybit blocked (403) from current region; KuCoin responded successfully and is the recommended venue. KuCoin requires `limit=20` for order book snapshots—handled in the test harness.

---

## Outstanding Follow-ups
- Extend Grafana dashboards to include CCXT rate limits and Redis hit rate (current dashboard focuses on infrastructure only).
- Document recommended external dashboards/tools (Grafana, TablePlus or pgAdmin, RedisInsight) in `infrastructure/OPERATIONS_GUIDE.md`.
- Wire the backtest runner to persist results into PostgreSQL once the schema is live.

---

## Next Actions
1. Capture Grafana/Prometheus validation in `INFRASTRUCTURE_STATUS.md` and expand dashboards with strategy metrics.
2. Run `python test_ccxt_fallback.py` periodically to monitor reachable exchanges; fall back to KuCoin if Bybit remains blocked.
3. Begin wiring the backtest pipeline to write results into PostgreSQL (schema already mounted in container).
