<!-- Copilot instructions for working in the NautilusTrader repo -->
# Copilot instructions

Use these concise, project-specific guidelines when generating code, tests, or documentation for NautilusTrader.

- Big picture: hybrid Rust + Python project with optional Cython and a separate frontend.
  - Core performance code lives in Rust crates (see `crates/` and top-level `Cargo.toml`).
  - The Python package is in the repo root (`nautilus_trader/`, `python/`), built via PyO3/Cython; builds are orchestrated with the provided `Makefile` and `uv` helper.
  - Frontend lives in `archon-ui-main/` (React + Vite) and follows a vertical-slice `/src/features` pattern.

- Immediate developer workflows (copy-paste these shells):
  - Install deps (recommended): `uv sync --group all` (see `AGENTS.md` and README).
  - Build for iterative development: `make build-debug` (fast compile for Rust/Cython changes).
  - Full build/wheels: `make build` or `make build-wheel`.
  - Run Python tests: `make pytest` or `uv run pytest`.
  - Run Rust tests: `make cargo-test` (uses `cargo-nextest`).

- Project conventions & patterns (do not deviate):
  - Service-layer pattern in backend: API route -> service -> database. See `python/src/server/api_routes/` and `python/src/server/services/` references in `AGENTS.md`.
  - Use TanStack Query and `useSmartPolling` for polling UIs in `archon-ui-main/src/features`.
  - Query key factory pattern is preferred (see `AGENTS.md` snippets).
  - DB/state names are literal: task statuses use `todo|doing|review|done` (UI uses those exact strings).

- Error-handling expectations (follow existing examples in `AGENTS.md`):
  - Fail fast for startup/missing config/database/auth errors.
  - For batch/background jobs: log errors per-item and skip failed items (do not insert placeholder/corrupt data).
  - Preserve full tracebacks in logs (use exc_info=True when logging exceptions).

- Tests & quality gates
  - Pytest is primary for Python; performance tests live under `tests/performance_tests` and use codspeed; use `make test-performance`.
  - Rust tests must be run with `cargo-nextest` (invoked by `make cargo-test`).
  - Linting: Python uses `ruff` and `mypy` (via `uv run ruff check`, `uv run mypy src/`); frontend uses `biome`/`eslint`.

- Integration & environment
  - Supabase is the development DB (`SUPABASE_URL`, `SUPABASE_SERVICE_KEY` in `.env`).
  - MCP server: `localhost:8051` (healthcheck `curl http://localhost:8051/health`).
  - Agents service: `localhost:8052`.
  - Docker Compose orchestrates services; use `docker compose --profile backend up -d` for hybrid development.

- What to change when editing code
  - If you update an API route, update the corresponding service in `python/src/server/services/` and add/adjust tests under `tests/`.
  - For frontend changes, place feature code inside `archon-ui-main/src/features/[feature]/` and use the query/hooks pattern.
  - For changes touching Rust/Cython, run `make build-debug` locally before opening a PR.

- Helpful files to inspect when unsure
  - `AGENTS.md` – repository agent/workflow rules and many examples.
  - `README.md` – build targets, installation, and high-level architecture.
  - `docs/developer_guide/testing.md` – testing conventions and recommended helpers.
  - `Makefile` – canonical build/test commands.

- Safety and style
  - Keep Python code within 120-char line length (project standard).
  - Use specific exception types; prefer clarity over over-generalized error swallowing.

If any of the above is unclear or you need examples for a specific folder (Rust crate, Python server route, or a frontend feature), ask for the exact path and I will include minimal, targeted examples.
