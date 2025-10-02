# Implementation Guide: [Database Migration Plan]

## Context
- **Plan Reference**: [/home/ajk/FormatIQ_v3/ai-working/database/plan.md]
- **Research Notes**: [/home/ajk/FormatIQ_v3/ai-working/database/research/analysis.md]
- **Objective**: [What this implementation must achieve]

---

## Phase 1: Setup & Verification
- [x] Read plan and research notes fully
- [x] Confirm related files and modules
- [x] Verify existing checkmarks in plan (if resuming)

---

## Phase 2: Implementation Steps
### Step 1
- Status: Completed (see compaction steps 1-3)
- Notes: Supabase DSN normalization merged; no further changes planned unless regressions appear.

### Step 2
- Status: Completed (see compaction steps 1-3)
- Notes: Async session factories exported and adopted across services and workers.

### Step 3
- Status: Completed (see compaction steps 1-3)
- Notes: Job and ScoreImprovement schemas realigned; migrations drafted awaiting Alembic wiring.

### Step 4 (Completed)
- Action: Implement Celery async execution strategy so background tasks await DB operations.
- Files: `apps/backend/app/tasks.py`, `apps/backend/app/core/celery_config.py`, `apps/backend/app/services/*`
- Expected Outcome: Celery workers consistently execute async DB calls using shared session factories without event loop conflicts.
- Verification: Manual smoke run of Celery worker invoking `optimize_resume` and `process_reconstruction`; ensure tasks complete without `RuntimeError: no running event loop`.
- Status Update: Introduced `AwaitableTask` base with per-worker event loop lifecycle hooks so async tasks execute via `loop.run_until_complete`; cleaned task module imports.
- Validation Note: Local eager execution (`dummy_async_task.apply()`) confirmed awaitable tasks complete via new loop wrapper; full worker validation pending queued broker run.

### Step 5 (In Progress)
- Action: Centralize telemetry credentials in settings and ensure Alembic uses whichever Postgres DSN is active (`.env.local` for docker today, Supabase later).
- Files: `apps/backend/app/telemetry/*`, `apps/backend/app/core/config.py`, `apps/backend/database/env.py`, `apps/backend/alembic.ini`
- Expected Outcome: Telemetry writes succeed using unified settings; Alembic upgrades operate against the current `DATABASE_URL` without manual rewiring.
- Status Update: Settings now prioritize `.env.local` (renamed from `.env.supabase`) and accept `DATABASE_URL` directly; `database/env.py` mirrors the same lookup so Alembic reads the local DSN. Docker compose now publishes Postgres on `localhost:5433` with credentials `formatiq/averysafepassword`. Seed workflow (`scripts/seed_local_db.py`) rebuilds the domain + telemetry tables and stamps Alembic with `fig_seed_20250913`, for which a no-op revision now exists. Telemetry smoke writes remain validated via direct `fiq_events` insert and Supabase REST client.
- Validation Note: Supabase connection verified via psycopg2 (`SELECT version()`), async SQLAlchemy ping, and full Alembic upgrade; local docker verification achieved via seed script, with `alembic current` returning `fig_seed_20250913`.
- High-Priority Subtasks:
  1. ✅ Refresh `.env.sample` and developer docs to default to local docker `DATABASE_URL` / `REDIS_URL` (now pointing to port 5433 and the reset password).
  2. ✅ Wire config + Alembic loaders to `.env.local`, keeping Supabase DSNs optional for staging.
  3. ✅ Provide seeding script + marker revision so local docker instances reflect Supabase schema and `alembic current` succeeds.
  4. ✅ Validate Celery/Redis runtime: detached worker connected to Redis (`celery@AdamsLaptop`), processed `process_resume_task` against empty DB (expected "resume not found" log), and logged rejection of `celery.ping` (task not registered) for observability.
  5. ✅ Telemetry REST + direct write smoke tests (Supabase) already executed; no new action.

### Step 6 (In Progress)
- Action: Execute full verification suite (pytest, smoke scripts) and add monitoring hooks per plan.
- Files: `apps/backend/tests/**`, `apps/backend/scripts/**`, deployment runbooks
- Expected Outcome: Supabase-backed stack passes automated checks with observable connection metrics.
- Verification Plan:
  1. Run Alembic against live Supabase: `alembic upgrade head` (after seeding required data for data-dependent migrations). **Status:** Completed against pooled DSN after widening `alembic_version.version_num` to `varchar(64)`; local docker now managed via seed workflow.
  2. Execute backend test suite: `pytest -q` from `apps/backend` (Supabase DSN loaded via `.env`). **Status:** Outstanding; prior Supabase run reported 22 failures + 2 errors unrelated to connectivity.
  3. Smoke-test async DB access: invoke `AsyncSessionLocal().execute("SELECT 1")` and run `alembic current` to confirm schema alignment. **Status:** Completed (local seed + alembic marker).
  4. Celery worker check: launch worker with `celery -A app.core.celery_config.celery_app worker --loglevel=info` and enqueue representative tasks (resume/job) to verify awaited execution end-to-end. **Status:** Completed locally—worker connected to Redis and DB, processed sample task, and logged expected warning for missing resume ID.
  5. Observe telemetry writes by toggling `FORMATIQ_DB_TELEMETRY=1` and verifying `fiq_events` entries via Supabase REST client test helper. **Status:** Completed previously (Supabase smoke).
- Verification Note: Celery log stored at `/tmp/celery-formatiq.log` (2025-09-28) records Redis connect, task execution, and the handled missing-resume warning; `celery@AdamsLaptop` responded to `inspect ping` during the smoke.

---

## Phase 3: Verification
- [ ] Runs tests
- [ ] Confirm criteria from plan.md are satisfied
- [ ] Cross-reference with AGENTS.md or system prompts

---

## Status Compaction (running log)
- **Progress**:  
  - Done: Step 4 Celery awaitable integration implemented with eager-mode validation.  
  - In Progress: Step 5 telemetry settings centralized and Alembic wiring validated via `alembic heads`.  
  - Issues: Offline migration generation fails due to data-dependent scripts; full worker runtime validation deferred until broker available; need decision on ScoreImprovement endpoint revival timing.  
- **Next Steps**:  
  1. Capture follow-up plan for handling migrations requiring live Supabase data before executing dry-run (likely seed fixtures or run against staging Supabase where `reconstruction_jobs` exists).  
  2. Enumerate prerequisites for Step 6 verification (pytest, Celery worker, telemetry toggle) and queue execution once environment access is confirmed.

---

## Notes
- If mismatches arise, log them here in the format:

