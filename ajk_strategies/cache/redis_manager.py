from __future__ import annotations

import json
import logging
import os
import pickle
from dataclasses import dataclass
from typing import Any, Mapping, Optional

try:
    import redis
except ImportError as exc:  # pragma: no cover
    raise SystemExit(
        "Redis support requires the 'redis' package. Install it with 'pip install redis'."
    ) from exc

LOGGER = logging.getLogger(__name__)


@dataclass(frozen=True)
class RedisCacheConfig:
    """Runtime configuration for Redis cache connectivity."""

    host: str = os.getenv("REDIS_HOST", "localhost")
    port: int = int(os.getenv("REDIS_PORT", "6378"))
    password: Optional[str] = os.getenv("REDIS_PASSWORD", "changeme")
    database: int = int(os.getenv("REDIS_DB", "0"))
    socket_timeout: float | None = float(os.getenv("REDIS_SOCKET_TIMEOUT", "2.0"))
    retry_on_timeout: bool = True


class StrategyCache:
    """Redis-backed cache for AI-Adaptive strategy state and artefacts."""

    def __init__(self, config: RedisCacheConfig | None = None) -> None:
        self._config = config or RedisCacheConfig()
        self._client = redis.Redis(
            host=self._config.host,
            port=self._config.port,
            password=self._config.password,
            db=self._config.database,
            socket_timeout=self._config.socket_timeout,
            retry_on_timeout=self._config.retry_on_timeout,
            decode_responses=False,
        )

    # Connectivity helpers -------------------------------------------------
    def ping(self) -> bool:
        """Return True when Redis is reachable."""
        try:
            return bool(self._client.ping())
        except redis.RedisError:
            LOGGER.exception("Redis ping failed")
            return False

    # Strategy state -------------------------------------------------------
    def save_strategy_state(self, strategy_id: str, state: Mapping[str, Any], *, ttl_seconds: int = 3600) -> None:
        """Persist strategy state (positions, parameters)."""
        key = f"strategy:{strategy_id}:state"
        payload = json.dumps(state, separators=(",", ":"), default=str)
        self._client.setex(key, ttl_seconds, payload.encode("utf-8"))

    def load_strategy_state(self, strategy_id: str) -> dict[str, Any] | None:
        """Return strategy state previously stored in Redis."""
        key = f"strategy:{strategy_id}:state"
        payload = self._client.get(key)
        if payload is None:
            return None
        try:
            return json.loads(payload.decode("utf-8"))
        except json.JSONDecodeError:
            LOGGER.warning("Failed to decode strategy state for key %s", key)
            return None

    def delete_strategy_state(self, strategy_id: str) -> None:
        """Remove cached state for the provided strategy."""
        key = f"strategy:{strategy_id}:state"
        self._client.delete(key)

    # ML model artefacts ---------------------------------------------------
    def save_ml_model(self, strategy_id: str, model: Any, *, version: str = "latest") -> None:
        """Store a pickled ML artefact."""
        key = f"ml_model:{strategy_id}:{version}"
        payload = pickle.dumps(model)
        self._client.set(key, payload)

    def load_ml_model(self, strategy_id: str, *, version: str = "latest") -> Any | None:
        """Load a previously cached model artefact."""
        key = f"ml_model:{strategy_id}:{version}"
        payload = self._client.get(key)
        if payload is None:
            return None
        try:
            return pickle.loads(payload)
        except (pickle.PickleError, TypeError):
            LOGGER.warning("Failed to unpickle model artefact for key %s", key)
            return None

    def save_model_metadata(self, strategy_id: str, metadata: Mapping[str, Any], *, version: str = "latest") -> None:
        """Store JSON metadata describing the model."""
        key = f"ml_model:{strategy_id}:{version}:meta"
        payload = json.dumps(metadata, separators=(",", ":"), default=str)
        self._client.set(key, payload.encode("utf-8"))

    def load_model_metadata(self, strategy_id: str, *, version: str = "latest") -> dict[str, Any] | None:
        """Return cached metadata describing the model artefact."""
        key = f"ml_model:{strategy_id}:{version}:meta"
        payload = self._client.get(key)
        if payload is None:
            return None
        try:
            return json.loads(payload.decode("utf-8"))
        except json.JSONDecodeError:
            LOGGER.warning("Failed to decode metadata for key %s", key)
            return None

    # Rate limiting -------------------------------------------------------
    def increment_rate_limit(self, key: str, *, ttl_seconds: int = 60) -> int:
        """Increment the rate-limit counter and return the current count."""
        namespaced_key = f"ratelimit:{key}"
        with self._client.pipeline() as pipe:
            while True:
                try:
                    pipe.watch(namespaced_key)
                    pipe.multi()
                    pipe.incr(namespaced_key, 1)
                    pipe.expire(namespaced_key, ttl_seconds)
                    results = pipe.execute()
                    return int(results[0])
                except redis.WatchError:
                    continue

    def get_rate_limit(self, key: str) -> int:
        """Return the current rate-limit counter value."""
        namespaced_key = f"ratelimit:{key}"
        value = self._client.get(namespaced_key)
        return int(value) if value is not None else 0

    # Market snapshots -----------------------------------------------------
    def cache_market_snapshot(
        self,
        *,
        venue: str,
        symbol: str,
        payload: Mapping[str, Any],
        ttl_seconds: int = 5,
    ) -> None:
        """Store a short-lived market snapshot for reuse across components."""
        key = f"market:{venue}:{symbol}:snapshot"
        serialized = json.dumps(payload, separators=(",", ":"), default=str)
        self._client.setex(key, ttl_seconds, serialized.encode("utf-8"))

    def load_market_snapshot(self, *, venue: str, symbol: str) -> dict[str, Any] | None:
        """Retrieve a cached market snapshot if available."""
        key = f"market:{venue}:{symbol}:snapshot"
        payload = self._client.get(key)
        if payload is None:
            return None
        try:
            return json.loads(payload.decode("utf-8"))
        except json.JSONDecodeError:
            LOGGER.warning("Failed to decode market snapshot for key %s", key)
            return None
