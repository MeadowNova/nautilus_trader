from __future__ import annotations
from dataclasses import dataclass
from datetime import datetime
from typing import Any, Iterable, Mapping
from uuid import UUID

from psycopg2.extras import Json

from ajk_strategies.database import DatabasePool, get_global_pool

AI_SCHEMA = "ai_extensions"


def _json_or_none(value: Mapping[str, Any] | None) -> Any:
    """Return a psycopg2 JSON wrapper when value is not None."""
    if value is None:
        return None
    return Json(value)


@dataclass(frozen=True)
class ModelTrainingRunRecord:
    """Metadata required to store a model training run."""

    strategy_id: str
    model_name: str
    model_version: str
    dataset_source: str | None = None
    dataset_hash: str | None = None
    dataset_start: datetime | None = None
    dataset_end: datetime | None = None
    feature_hash: str | None = None
    hyperparameters: Mapping[str, Any] | None = None
    metrics: Mapping[str, Any] | None = None
    status: str = "completed"
    notes: str | None = None
    completed_at: datetime | None = None


@dataclass(frozen=True)
class ModelArtifactRecord:
    """Metadata for a persisted model artefact."""

    training_run_id: UUID
    artifact_type: str
    artifact_uri: str
    checksum: str | None = None
    checksum_algorithm: str | None = None
    file_size_bytes: int | None = None


@dataclass(frozen=True)
class BacktestRunRecord:
    """Metadata required to store a backtest execution."""

    strategy_id: str
    run_name: str | None
    instrument_id: str | None = None
    bar_type: str | None = None
    model_versions: Mapping[str, Any] | None = None
    parameters: Mapping[str, Any] | None = None
    dataset_source: str | None = None
    dataset_start: datetime | None = None
    dataset_end: datetime | None = None
    status: str = "completed"
    metrics: Mapping[str, Any] | None = None
    started_at: datetime | None = None
    completed_at: datetime | None = None


@dataclass(frozen=True)
class BacktestMetricRecord:
    """Individual metric captured for a backtest execution."""

    backtest_run_id: UUID
    metric_name: str
    metric_value: float | None
    metadata: Mapping[str, Any] | None = None
    recorded_at: datetime | None = None


class PostgresPersistenceClient:
    """Persistence gateway for AI strategy artefacts and analytics."""

    def __init__(
        self,
        *,
        host: str | None = None,
        port: int | None = None,
        database: str | None = None,
        user: str | None = None,
        password: str | None = None,
        connect_timeout: int = 5,
        pool: DatabasePool | None = None,
    ) -> None:
        pool_overrides = {
            "host": host,
            "port": port,
            "database": database,
            "user": user,
            "password": password,
            "connect_timeout": connect_timeout,
        }
        # Remove None overrides to avoid forcing pool recreation unnecessarily.
        pool_overrides = {key: value for key, value in pool_overrides.items() if value is not None}
        self._pool = pool or get_global_pool(**pool_overrides)

    def record_model_training_run(self, record: ModelTrainingRunRecord) -> UUID:
        """Insert a model training run row and return the assigned identifier."""
        sql = f"""
            INSERT INTO {AI_SCHEMA}.model_training_runs (
                strategy_id,
                model_name,
                model_version,
                dataset_source,
                dataset_hash,
                dataset_start,
                dataset_end,
                feature_hash,
                hyperparameters,
                metrics,
                status,
                notes,
                completed_at
            ) VALUES (
                %(strategy_id)s,
                %(model_name)s,
                %(model_version)s,
                %(dataset_source)s,
                %(dataset_hash)s,
                %(dataset_start)s,
                %(dataset_end)s,
                %(feature_hash)s,
                %(hyperparameters)s,
                %(metrics)s,
                %(status)s,
                %(notes)s,
                %(completed_at)s
            )
            RETURNING id;
        """

        params = {
            "strategy_id": record.strategy_id,
            "model_name": record.model_name,
            "model_version": record.model_version,
            "dataset_source": record.dataset_source,
            "dataset_hash": record.dataset_hash,
            "dataset_start": record.dataset_start,
            "dataset_end": record.dataset_end,
            "feature_hash": record.feature_hash,
            "hyperparameters": _json_or_none(record.hyperparameters),
            "metrics": _json_or_none(record.metrics),
            "status": record.status,
            "notes": record.notes,
            "completed_at": record.completed_at,
        }

        with self._pool.connection() as connection:
            with connection.cursor() as cursor:
                cursor.execute(sql, params)
                result = cursor.fetchone()
                if result is None:
                    raise RuntimeError("Model training run insert did not return an id.")
                connection.commit()
        return UUID(result[0]) if isinstance(result[0], str) else result[0]

    def record_model_artifact(self, record: ModelArtifactRecord) -> UUID:
        """Insert a model artefact row linked to a training run."""
        sql = f"""
            INSERT INTO {AI_SCHEMA}.model_artifacts (
                training_run_id,
                artifact_type,
                artifact_uri,
                checksum,
                checksum_algorithm,
                file_size_bytes
            ) VALUES (
                %(training_run_id)s,
                %(artifact_type)s,
                %(artifact_uri)s,
                %(checksum)s,
                %(checksum_algorithm)s,
                %(file_size_bytes)s
            )
            RETURNING id;
        """

        params = {
            "training_run_id": str(record.training_run_id),
            "artifact_type": record.artifact_type,
            "artifact_uri": record.artifact_uri,
            "checksum": record.checksum,
            "checksum_algorithm": record.checksum_algorithm,
            "file_size_bytes": record.file_size_bytes,
        }

        with self._pool.connection() as connection:
            with connection.cursor() as cursor:
                cursor.execute(sql, params)
                result = cursor.fetchone()
                if result is None:
                    raise RuntimeError("Model artefact insert did not return an id.")
                connection.commit()
        return UUID(result[0]) if isinstance(result[0], str) else result[0]

    def record_backtest_run(self, record: BacktestRunRecord) -> UUID:
        """Insert a backtest run and return the generated identifier."""
        sql = f"""
            INSERT INTO {AI_SCHEMA}.backtest_runs (
                strategy_id,
                run_name,
                instrument_id,
                bar_type,
                model_versions,
                parameters,
                dataset_source,
                dataset_start,
                dataset_end,
                status,
                metrics,
                started_at,
                completed_at
            ) VALUES (
                %(strategy_id)s,
                %(run_name)s,
                %(instrument_id)s,
                %(bar_type)s,
                %(model_versions)s,
                %(parameters)s,
                %(dataset_source)s,
                %(dataset_start)s,
                %(dataset_end)s,
                %(status)s,
                %(metrics)s,
                %(started_at)s,
                %(completed_at)s
            )
            RETURNING id;
        """

        params = {
            "strategy_id": record.strategy_id,
            "run_name": record.run_name,
            "instrument_id": record.instrument_id,
            "bar_type": record.bar_type,
            "model_versions": _json_or_none(record.model_versions),
            "parameters": _json_or_none(record.parameters),
            "dataset_source": record.dataset_source,
            "dataset_start": record.dataset_start,
            "dataset_end": record.dataset_end,
            "status": record.status,
            "metrics": _json_or_none(record.metrics),
            "started_at": record.started_at,
            "completed_at": record.completed_at,
        }

        with self._pool.connection() as connection:
            with connection.cursor() as cursor:
                cursor.execute(sql, params)
                result = cursor.fetchone()
                if result is None:
                    raise RuntimeError("Backtest run insert did not return an id.")
                connection.commit()
        return UUID(result[0]) if isinstance(result[0], str) else result[0]

    def record_backtest_metrics(self, records: Iterable[BacktestMetricRecord]) -> None:
        """Bulk insert metric rows associated with a backtest run."""
        if not records:
            return

        sql = f"""
            INSERT INTO {AI_SCHEMA}.backtest_metrics (
                backtest_run_id,
                metric_name,
                metric_value,
                metadata,
                recorded_at
            ) VALUES (
                %(backtest_run_id)s,
                %(metric_name)s,
                %(metric_value)s,
                %(metadata)s,
                %(recorded_at)s
            );
        """

        params_list = [
            {
                "backtest_run_id": str(record.backtest_run_id),
                "metric_name": record.metric_name,
                "metric_value": record.metric_value,
                "metadata": _json_or_none(record.metadata),
                "recorded_at": record.recorded_at,
            }
            for record in records
        ]

        with self._pool.connection() as connection:
            with connection.cursor() as cursor:
                cursor.executemany(sql, params_list)
                connection.commit()
