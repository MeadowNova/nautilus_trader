from __future__ import annotations

import logging
from typing import Iterable, Mapping

import redis
from psycopg2.extras import RealDictCursor

from ajk_strategies.cache.redis_manager import RedisCacheConfig
from ajk_strategies.database import DatabasePool, get_global_pool
from ajk_strategies.monitoring.metrics_definitions import (
    BACKTEST_DRAWDOWN,
    BACKTEST_DURATION,
    BACKTEST_LAST_COMPLETED,
    BACKTEST_STATUS,
    BACKTEST_TOTAL_PNL,
    MODEL_ARTIFACT_INFO,
    MODEL_TRAINING_STATUS,
    REDIS_KEY_COUNT,
    REDIS_MEMORY_USAGE,
    REDIS_UP,
    REGISTRY,
)

LOGGER = logging.getLogger(__name__)


class MetricsCollector:
    """Collect metrics from Postgres/Redis and expose them to Prometheus."""

    def __init__(
        self,
        *,
        pool: DatabasePool | None = None,
        redis_config: RedisCacheConfig | None = None,
        registry=REGISTRY,
        backtest_limit: int = 25,
    ) -> None:
        self._pool = pool or get_global_pool()
        self._redis_config = redis_config or RedisCacheConfig()
        self._registry = registry
        self._backtest_limit = backtest_limit
        self._redis_client = redis.Redis(
            host=self._redis_config.host,
            port=self._redis_config.port,
            password=self._redis_config.password,
            db=self._redis_config.database,
            socket_timeout=self._redis_config.socket_timeout,
            retry_on_timeout=self._redis_config.retry_on_timeout,
            decode_responses=False,
        )
        self._observed_backtests: set[str] = set()

    # ------------------------------------------------------------------ #
    def refresh(self) -> None:
        """Refresh all metric families."""
        self._refresh_backtests()
        self._refresh_model_metadata()
        self._refresh_redis_stats()

    # ------------------------------------------------------------------ #
    def _refresh_backtests(self) -> None:
        BACKTEST_LAST_COMPLETED.clear()
        BACKTEST_STATUS.clear()
        BACKTEST_TOTAL_PNL.clear()
        BACKTEST_DRAWDOWN.clear()

        sql = """
            SELECT
                br.id AS backtest_run_id,
                br.strategy_id,
                br.run_name,
                br.status,
                br.started_at,
                br.completed_at,
                perf.total_pnl,
                perf.max_drawdown_pct
            FROM ai_extensions.backtest_runs br
            LEFT JOIN ai_extensions.v_backtest_performance perf
                ON perf.backtest_run_id = br.id
            ORDER BY COALESCE(br.completed_at, br.started_at) DESC
            LIMIT %s;
        """

        with self._pool.connection() as connection:
            with connection.cursor(cursor_factory=RealDictCursor) as cursor:
                cursor.execute(sql, (self._backtest_limit,))
                rows: Iterable[Mapping[str, object]] = cursor.fetchall()

        for row in rows:
            strategy_id = row["strategy_id"] or "unknown"
            run_name = row["run_name"] or row["backtest_run_id"]
            status = row["status"] or "unknown"
            completed_at = row.get("completed_at")
            started_at = row.get("started_at")
            total_pnl = row.get("total_pnl") or 0.0
            drawdown_pct = row.get("max_drawdown_pct") or 0.0

            if completed_at:
                BACKTEST_LAST_COMPLETED.labels(strategy_id, run_name).set(
                    completed_at.timestamp()
                )
                duration_seconds = (
                    completed_at - started_at
                ).total_seconds() if started_at and completed_at else None
                if duration_seconds and duration_seconds > 0 and str(row["backtest_run_id"]) not in self._observed_backtests:
                    BACKTEST_DURATION.observe(duration_seconds)
            else:
                BACKTEST_LAST_COMPLETED.labels(strategy_id, run_name).set(0)

            BACKTEST_STATUS.labels(strategy_id, run_name, status).set(1.0)
            BACKTEST_TOTAL_PNL.labels(strategy_id, run_name).set(float(total_pnl))
            BACKTEST_DRAWDOWN.labels(strategy_id, run_name).set(float(drawdown_pct))

            self._observed_backtests.add(str(row["backtest_run_id"]))

    # ------------------------------------------------------------------ #
    def _refresh_model_metadata(self) -> None:
        MODEL_ARTIFACT_INFO.clear()
        MODEL_TRAINING_STATUS.clear()

        artifact_sql = """
            SELECT
                mtr.strategy_id,
                mtr.model_name,
                mtr.model_version,
                ma.artifact_type,
                COALESCE(ma.file_size_bytes, 0) AS file_size_bytes
            FROM ai_extensions.model_artifacts ma
            JOIN ai_extensions.model_training_runs mtr
                ON mtr.id = ma.training_run_id
            ORDER BY ma.created_at DESC
            LIMIT 50;
        """

        status_sql = """
            SELECT
                strategy_id,
                model_name,
                status,
                COUNT(*) AS run_count
            FROM ai_extensions.model_training_runs
            GROUP BY strategy_id, model_name, status;
        """

        with self._pool.connection() as connection:
            with connection.cursor(cursor_factory=RealDictCursor) as cursor:
                cursor.execute(artifact_sql)
                artifacts = cursor.fetchall()
                cursor.execute(status_sql)
                training_status = cursor.fetchall()

        for row in artifacts:
            MODEL_ARTIFACT_INFO.labels(
                row["strategy_id"],
                row["model_name"],
                row["model_version"],
                row["artifact_type"],
            ).set(float(row["file_size_bytes"]))

        for row in training_status:
            MODEL_TRAINING_STATUS.labels(
                row["strategy_id"],
                row["model_name"],
                row["status"],
            ).set(int(row["run_count"]))

    # ------------------------------------------------------------------ #
    def _refresh_redis_stats(self) -> None:
        try:
            info = self._redis_client.info(section="memory")
            dbsize = self._redis_client.dbsize()
        except redis.RedisError:
            LOGGER.exception("Failed to query Redis metrics")
            REDIS_UP.set(0)
            REDIS_MEMORY_USAGE.set(0)
            REDIS_KEY_COUNT.set(0)
            return

        REDIS_UP.set(1)
        REDIS_MEMORY_USAGE.set(float(info.get("used_memory", 0)))
        REDIS_KEY_COUNT.set(float(dbsize))


__all__ = ["MetricsCollector"]
