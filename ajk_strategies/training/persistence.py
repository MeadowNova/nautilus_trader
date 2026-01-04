from __future__ import annotations

import hashlib
import logging
import os
from datetime import datetime
from pathlib import Path
from typing import Any, Iterable, Mapping, Sequence
from uuid import UUID

from ajk_strategies.persistence import (
    ModelArtifactRecord,
    ModelTrainingRunRecord,
    PostgresPersistenceClient,
)

LOGGER = logging.getLogger(__name__)
PERSIST_ENV_VAR = "NAUTILUS_PERSIST_MODELS"


def persistence_enabled(env_var: str = PERSIST_ENV_VAR) -> bool:
    """Return True when training artefacts should be persisted."""
    return os.getenv(env_var, "0").lower() in {"1", "true", "yes"}


def _normalize_files(dataset_files: Iterable[Path] | None) -> list[Path]:
    files: list[Path] = []
    if dataset_files is None:
        return files
    for file in dataset_files:
        resolved = Path(file).expanduser().resolve()
        if resolved.exists():
            files.append(resolved)
        else:
            LOGGER.debug("Ignoring missing dataset file: %s", resolved)
    return files


def _compute_dataset_hash(files: Sequence[Path]) -> str:
    """Compute a lightweight hash for the dataset inputs."""
    digest = hashlib.sha256()
    for file in sorted(files):
        stat = file.stat()
        digest.update(str(file).encode("utf-8"))
        digest.update(str(stat.st_size).encode("utf-8"))
        digest.update(str(int(stat.st_mtime)).encode("utf-8"))
    return digest.hexdigest()


def _hash_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            if not chunk:
                break
            digest.update(chunk)
    return digest.hexdigest()


def persist_training_run(
    *,
    strategy_id: str,
    model_name: str,
    model_version: str,
    dataset_source: str | None,
    dataset_files: Iterable[Path] | None,
    dataset_start: datetime | None,
    dataset_end: datetime | None,
    hyperparameters: Mapping[str, Any],
    metrics: Mapping[str, Any],
    feature_hash: str | None = None,
    status: str = "completed",
    notes: str | None = None,
    completed_at: datetime | None = None,
    artifacts: Iterable[tuple[str, Path]] = (),
) -> UUID | None:
    """
    Persist training metadata and artefacts when enabled.

    Returns:
        UUID of the stored training run, or None when persistence is disabled.
    """
    if not persistence_enabled():
        return None

    files = _normalize_files(dataset_files)
    dataset_hash = _compute_dataset_hash(files) if files else None

    try:
        client = PostgresPersistenceClient()
        run_record = ModelTrainingRunRecord(
            strategy_id=strategy_id,
            model_name=model_name,
            model_version=model_version,
            dataset_source=dataset_source,
            dataset_hash=dataset_hash,
            dataset_start=dataset_start,
            dataset_end=dataset_end,
            feature_hash=feature_hash,
            hyperparameters=dict(hyperparameters),
            metrics=dict(metrics),
            status=status,
            notes=notes,
            completed_at=completed_at,
        )
        run_id = client.record_model_training_run(run_record)

        for artifact_type, artifact_path in artifacts:
            path = Path(artifact_path).expanduser().resolve()
            if not path.exists():
                LOGGER.warning("Skipping persistence for missing artefact %s", path)
                continue
            checksum = _hash_file(path)
            stat = path.stat()
            artifact_record = ModelArtifactRecord(
                training_run_id=run_id,
                artifact_type=artifact_type,
                artifact_uri=str(path),
                checksum=checksum,
                checksum_algorithm="sha256",
                file_size_bytes=stat.st_size,
            )
            client.record_model_artifact(artifact_record)

        return run_id
    except Exception as exc:  # pragma: no cover - defensive path
        LOGGER.warning("Failed to persist training run for %s: %s", model_name, exc, exc_info=True)
        return None
