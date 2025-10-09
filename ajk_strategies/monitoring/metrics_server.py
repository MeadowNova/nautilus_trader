from __future__ import annotations

import logging
import os
import signal
import sys
import time
from types import FrameType
from typing import Final

from prometheus_client import start_http_server

from ajk_strategies.monitoring.metrics_collector import MetricsCollector
from ajk_strategies.monitoring.metrics_definitions import REGISTRY

LOGGER = logging.getLogger(__name__)

DEFAULT_PORT: Final[int] = int(os.getenv("AI_METRICS_PORT", "8000"))
DEFAULT_REFRESH_INTERVAL: Final[float] = float(os.getenv("AI_METRICS_REFRESH_SECONDS", "30.0"))


def serve_metrics(
    *,
    port: int = DEFAULT_PORT,
    refresh_interval: float = DEFAULT_REFRESH_INTERVAL,
    collector: MetricsCollector | None = None,
) -> None:
    """Start an HTTP server exposing Prometheus metrics."""
    metrics_collector = collector or MetricsCollector()
    start_http_server(port, registry=REGISTRY)
    LOGGER.info("AI metrics server listening on port %s", port)

    def _handle_signal(signum: int, frame: FrameType | None) -> None:  # pragma: no cover
        LOGGER.info("Received signal %s, stopping metrics server.", signum)
        raise SystemExit(0)

    signal.signal(signal.SIGTERM, _handle_signal)  # pragma: no cover
    signal.signal(signal.SIGINT, _handle_signal)  # pragma: no cover

    while True:
        start = time.perf_counter()
        try:
            metrics_collector.refresh()
        except Exception:  # pragma: no cover - defensive
            LOGGER.exception("Metrics refresh failed")
        elapsed = time.perf_counter() - start
        sleep_for = max(0.0, refresh_interval - elapsed)
        time.sleep(sleep_for)


def main(argv: list[str] | None = None) -> int:
    """Entrypoint for CLI usage."""
    logging.basicConfig(
        level=os.getenv("AI_METRICS_LOG_LEVEL", "INFO"),
        format="%(asctime)s %(levelname)s %(name)s %(message)s",
    )
    serve_metrics()
    return 0


if __name__ == "__main__":  # pragma: no cover
    sys.exit(main())
