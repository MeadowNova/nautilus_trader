from __future__ import annotations

from prometheus_client import CollectorRegistry, Gauge, Histogram

REGISTRY = CollectorRegistry()

# Backtest metrics ---------------------------------------------------------
BACKTEST_LAST_COMPLETED = Gauge(
    "ai_backtest_last_completed_timestamp",
    "Unix timestamp of the most recent completed backtest run.",
    ["strategy_id", "run_name"],
    registry=REGISTRY,
)

BACKTEST_STATUS = Gauge(
    "ai_backtest_status",
    "Status flag for tracked backtest runs (1=completed, 0=other).",
    ["strategy_id", "run_name", "status"],
    registry=REGISTRY,
)

BACKTEST_TOTAL_PNL = Gauge(
    "ai_backtest_total_pnl",
    "Total profit and loss reported for a backtest run.",
    ["strategy_id", "run_name"],
    registry=REGISTRY,
)

BACKTEST_DRAWDOWN = Gauge(
    "ai_backtest_max_drawdown_pct",
    "Maximum drawdown percentage observed during the run.",
    ["strategy_id", "run_name"],
    registry=REGISTRY,
)

BACKTEST_DURATION = Histogram(
    "ai_backtest_duration_seconds",
    "Duration of completed backtest runs in seconds.",
    buckets=(60, 300, 600, 1200, 1800, 3600, 7200, 14400),
    registry=REGISTRY,
)

# Model metrics -------------------------------------------------------------
MODEL_ARTIFACT_INFO = Gauge(
    "ai_model_artifact_info",
    "Metadata about persisted model artefacts.",
    ["strategy_id", "model_name", "model_version", "artifact_type"],
    registry=REGISTRY,
)

MODEL_TRAINING_STATUS = Gauge(
    "ai_model_training_runs_total",
    "Count of model training runs grouped by status.",
    ["strategy_id", "model_name", "status"],
    registry=REGISTRY,
)

# Redis/cache metrics ------------------------------------------------------
REDIS_UP = Gauge(
    "ai_redis_up",
    "Gauge signalling Redis availability (1=reachable).",
    registry=REGISTRY,
)

REDIS_MEMORY_USAGE = Gauge(
    "ai_redis_memory_usage_bytes",
    "Reported Redis used_memory in bytes.",
    registry=REGISTRY,
)

REDIS_KEY_COUNT = Gauge(
    "ai_redis_key_count",
    "Total number of keys in the configured Redis database.",
    registry=REGISTRY,
)

# GPU validation metrics ---------------------------------------------------
GPU_VALIDATION_TRADES = Gauge(
    "ai_gpu_validation_total_trades",
    "Total trades recorded in a GPU validation summary file.",
    ["summary_file", "instrument", "device"],
    registry=REGISTRY,
)

GPU_VALIDATION_PNL = Gauge(
    "ai_gpu_validation_net_pnl",
    "Net PnL captured in the GPU validation summary.",
    ["summary_file", "instrument", "device"],
    registry=REGISTRY,
)

GPU_VALIDATION_RUNTIME = Gauge(
    "ai_gpu_validation_runtime_seconds",
    "Runtime spent executing the GPU validation summary.",
    ["summary_file", "instrument", "device"],
    registry=REGISTRY,
)

GPU_VALIDATION_SEGMENTS = Gauge(
    "ai_gpu_validation_segments",
    "Number of segments aggregated in the GPU validation summary.",
    ["summary_file"],
    registry=REGISTRY,
)

GPU_VALIDATION_LAST_COMPLETED = Gauge(
    "ai_gpu_validation_last_completed_timestamp",
    "Unix timestamp for the latest segment completion in the summary.",
    ["summary_file"],
    registry=REGISTRY,
)

# Exposed objects for import convenience.
__all__ = [
    "REGISTRY",
    "BACKTEST_LAST_COMPLETED",
    "BACKTEST_STATUS",
    "BACKTEST_TOTAL_PNL",
    "BACKTEST_DRAWDOWN",
    "BACKTEST_DURATION",
    "MODEL_ARTIFACT_INFO",
    "MODEL_TRAINING_STATUS",
    "REDIS_UP",
    "REDIS_MEMORY_USAGE",
    "REDIS_KEY_COUNT",
    "GPU_VALIDATION_TRADES",
    "GPU_VALIDATION_PNL",
    "GPU_VALIDATION_RUNTIME",
    "GPU_VALIDATION_SEGMENTS",
    "GPU_VALIDATION_LAST_COMPLETED",
]
