from __future__ import annotations

import os
from contextlib import contextmanager
from threading import Lock
from typing import Iterator

from psycopg2 import pool as pg_pool
from psycopg2.extensions import STATUS_IN_TRANSACTION, STATUS_PREPARED


def _resolve_connection_kwargs(
    *,
    host: str | None = None,
    port: int | None = None,
    database: str | None = None,
    user: str | None = None,
    password: str | None = None,
    connect_timeout: int | None = None,
) -> dict[str, object]:
    """Normalise connection keyword arguments with environment fallbacks."""
    return {
        "host": host or os.getenv("DB_HOST", "localhost"),
        "port": port or int(os.getenv("DB_PORT", "5433")),
        "database": database or os.getenv("DB_NAME", "nautilus_trader"),
        "user": user or os.getenv("DB_USER", "nautilus"),
        "password": password or os.getenv("DB_PASSWORD", "changeme"),
        "connect_timeout": connect_timeout
        if connect_timeout is not None
        else int(os.getenv("DB_CONNECT_TIMEOUT", "5")),
    }


class DatabasePool:
    """Thin wrapper around psycopg2's SimpleConnectionPool with sane defaults."""

    def __init__(
        self,
        *,
        min_connections: int = 1,
        max_connections: int = 5,
        **connection_kwargs: object,
    ) -> None:
        if min_connections <= 0:
            raise ValueError("min_connections must be positive")
        if max_connections < min_connections:
            raise ValueError("max_connections must be >= min_connections")
        self._pool = pg_pool.SimpleConnectionPool(
            min_connections,
            max_connections,
            **connection_kwargs,
        )

    @contextmanager
    def connection(self) -> Iterator[pg_pool.connection]:
        """Yield a connection from the pool with automatic cleanup."""
        connection = self._pool.getconn()
        try:
            yield connection
        finally:
            self.release(connection)

    def release(self, connection: pg_pool.connection, *, discard: bool = False) -> None:
        """Return a connection to the pool, rolling back stray transactions."""
        if connection.closed:
            discard = True
        elif connection.status in (STATUS_IN_TRANSACTION, STATUS_PREPARED):
            connection.rollback()

        if discard:
            self._pool.putconn(connection, close=True)
        else:
            self._pool.putconn(connection)

    def closeall(self) -> None:
        """Close all managed connections."""
        self._pool.closeall()


_POOL_LOCK = Lock()
_SHARED_POOL: DatabasePool | None = None


def get_global_pool(**overrides: object) -> DatabasePool:
    """Return a shared connection pool configured from environment overrides."""
    global _SHARED_POOL
    with _POOL_LOCK:
        if _SHARED_POOL is None or overrides:
            kwargs = _resolve_connection_kwargs(**overrides)
            _SHARED_POOL = DatabasePool(
                min_connections=int(os.getenv("DB_POOL_MIN", "1")),
                max_connections=int(os.getenv("DB_POOL_MAX", "5")),
                **kwargs,
            )
        return _SHARED_POOL
