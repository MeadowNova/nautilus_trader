# Research: backend database to transition to full async postgres via supabase. Check Pydantic settings, pyroproject, schemas, full settings and configurations review
## Key Files
- `apps/backend/app/core/config.py`: Pydantic `Settings` defining DB URLs, Redis/Celery, and LLM credentials; defaults still point to SQLite fallbacks.
- `apps/backend/app/core/database.py`: Async and sync engine factories, dependency helpers, and global engine cache for SQLAlchemy sessions.
- `apps/backend/app/models/*`: ORM tables for resumes, jobs, processed artifacts, reconstruction, and telemetry data written by services.
- `apps/backend/app/services/*.py`: Business logic modules (resume/job/reconstruction/optimization) that consume async sessions and orchestrate background work.
- `apps/backend/app/api/router/v1/*.py`: FastAPI endpoints injecting `AsyncSession` via `get_db` to reach the services.
- `apps/backend/app/tasks.py` & `app/core/celery_config.py`: Celery worker entrypoints built on async DB access patterns.
- `apps/backend/app/telemetry/{db.py,supabase_rest.py}`: Dual telemetry persistence layers (SQLAlchemy vs Supabase REST) tied to Supabase credentials.
- `apps/backend/pyproject.toml`: Declares async database drivers (`asyncpg`, `psycopg`) and related runtime dependencies.
- `apps/backend/database/*.py`: Postgres-oriented migration scripts for telemetry and reconstruction tables.
- `docs/database_migration_plan.md`, `docs/research/database_assessment.md`: Existing Supabase migration guidance highlighting outstanding validation work.

## Code Relationships
- FastAPI routers resolve `get_db` → async SQLAlchemy sessions → service classes → ORM models and Celery tasks, forming the API↔DB contract.
- Services enqueue Celery tasks that rehydrate `get_db` inside workers, expecting consistent async session factories.
- ORM definitions underpin migrations and telemetry helpers, with telemetry falling back to Supabase REST when direct Postgres writes fail.
- `Settings` feeds engine constructors and Celery/Redis config; telemetry modules manually inspect environment for Supabase keys, risking divergence.
- `pyproject.toml` pins async drivers used by `create_async_engine`; migrations depend on sync URLs to manipulate Supabase schema.

## Potential Solutions
- Normalize configuration to require explicit Supabase DSNs, deriving async/sync URLs and failing fast when absent while offering explicit dev overrides.
- Expose a reusable `AsyncSessionLocal` (or scoped session) from `database.py` and update CLI/tasks to consume it consistently.
- Align ORM schemas with service expectations (e.g., status/blueprint fields) or adjust services to match actual columns before Supabase enforcement.
- Rework Celery async tasks to use an event loop wrapper or `celery-asyncio`, ensuring workers handle awaits reliably against Supabase.
- Formalize Alembic migrations targeting Supabase, wiring env configs and running dry runs to validate schema parity.
- Centralize telemetry credential loading via `Settings` and consider using the Supabase Python client for consistent auth and retries.

## Known Limitations
- Default SQLite URLs in settings allow silent fallback that undermines Supabase adoption.
- Duplicate lowercase DB settings in `Settings` introduce ambiguity about authoritative configuration fields.
- `database.py` caches engines and lacks exported session factories referenced by CLI/tasks, leading to import/runtime errors.
- `JobService` writes fields missing from `Job` ORM definitions, which will surface once Postgres constraints are active.
- Celery async task definitions rely on default worker pools that do not await coroutines, risking dropped Supabase transactions.
- Telemetry REST fallback manually parses `.env`, bypassing centralized settings and inviting credential drift.
