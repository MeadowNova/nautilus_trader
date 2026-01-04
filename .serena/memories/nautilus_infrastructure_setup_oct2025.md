## 2025-10-07 Infrastructure Bring-Up
- Docker Compose stack (Postgres, Redis, Prometheus, Grafana, exporters) now runs via `docker compose --env-file infrastructure/.env.local -f infrastructure/docker/docker-compose.yml up -d`.
- Host port overrides set in `.env.local`: `DB_PORT=5433`, `REDIS_PORT=6378`; Grafana at http://localhost:3000, Prometheus at http://localhost:9090.
- Setup script exports `COMPOSE_PARALLEL_LIMIT=1` to avoid the compose parallel pull panic and includes a note to clear `~/.docker/config.json` if the Windows credential helper blocks pulls.
- Grafana uses builtin Postgres datasource; only `GF_PLUGINS_PREINSTALL=redis-datasource` remains to provision Redis.
