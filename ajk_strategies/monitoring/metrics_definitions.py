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

BACKTEST_TOTAL_PNL_PCT = Gauge(
    "ai_backtest_total_pnl_pct",
    "Total profit and loss percentage reported for a backtest run.",
    ["strategy_id", "run_name", "instrument_id"],
    registry=REGISTRY,
)

BACKTEST_TOTAL_TRADES = Gauge(
    "ai_backtest_total_trades",
    "Total trades recorded for a backtest run.",
    ["strategy_id", "run_name", "instrument_id"],
    registry=REGISTRY,
)

BACKTEST_WIN_RATE = Gauge(
    "ai_backtest_win_rate_pct",
    "Win rate percentage calculated for a backtest run.",
    ["strategy_id", "run_name", "instrument_id"],
    registry=REGISTRY,
)

BACKTEST_PROFIT_FACTOR = Gauge(
    "ai_backtest_profit_factor",
    "Profit factor computed for a backtest run.",
    ["strategy_id", "run_name", "instrument_id"],
    registry=REGISTRY,
)

BACKTEST_SHARPE_RATIO = Gauge(
    "ai_backtest_sharpe_ratio",
    "Sharpe ratio observed for a backtest run.",
    ["strategy_id", "run_name", "instrument_id"],
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

GPU_VALIDATION_SEGMENT_PNL_MEAN = Gauge(
    "ai_gpu_validation_segment_pnl_mean",
    "Mean net PnL per segment within a GPU validation summary.",
    ["summary_file"],
    registry=REGISTRY,
)

GPU_VALIDATION_SEGMENT_PNL_MEDIAN = Gauge(
    "ai_gpu_validation_segment_pnl_median",
    "Median net PnL per segment within a GPU validation summary.",
    ["summary_file"],
    registry=REGISTRY,
)

GPU_VALIDATION_SEGMENT_TRADES_MEAN = Gauge(
    "ai_gpu_validation_segment_trades_mean",
    "Mean trade count per segment within a GPU validation summary.",
    ["summary_file"],
    registry=REGISTRY,
)

GPU_VALIDATION_SEGMENT_TRADES_MEDIAN = Gauge(
    "ai_gpu_validation_segment_trades_median",
    "Median trade count per segment within a GPU validation summary.",
    ["summary_file"],
    registry=REGISTRY,
)

# Live trading metrics -----------------------------------------------------
LIVE_SESSION_STATUS = Gauge(
    "ai_live_session_status",
    "Status of live trading sessions (1=running, 0=stopped).",
    ["trader_id", "strategy_id", "session_name", "environment", "status"],
    registry=REGISTRY,
)

LIVE_SESSION_RUNTIME = Gauge(
    "ai_live_session_runtime_seconds",
    "Runtime duration of live trading session in seconds.",
    ["trader_id", "strategy_id", "session_name"],
    registry=REGISTRY,
)

LIVE_EQUITY_TOTAL = Gauge(
    "ai_live_equity_total",
    "Current total equity in live trading session.",
    ["trader_id", "strategy_id", "environment"],
    registry=REGISTRY,
)

LIVE_EQUITY_CASH = Gauge(
    "ai_live_equity_cash",
    "Current cash balance in live trading session.",
    ["trader_id", "strategy_id", "environment"],
    registry=REGISTRY,
)

LIVE_PNL_UNREALIZED = Gauge(
    "ai_live_pnl_unrealized",
    "Unrealized profit/loss from open positions.",
    ["trader_id", "strategy_id", "environment"],
    registry=REGISTRY,
)

LIVE_PNL_REALIZED = Gauge(
    "ai_live_pnl_realized",
    "Realized profit/loss from closed positions.",
    ["trader_id", "strategy_id", "environment"],
    registry=REGISTRY,
)

LIVE_PNL_TOTAL = Gauge(
    "ai_live_pnl_total",
    "Total profit/loss (realized + unrealized).",
    ["trader_id", "strategy_id", "environment"],
    registry=REGISTRY,
)

LIVE_PNL_TOTAL_PCT = Gauge(
    "ai_live_pnl_total_pct",
    "Total profit/loss as percentage of initial balance.",
    ["trader_id", "strategy_id", "environment"],
    registry=REGISTRY,
)

LIVE_DRAWDOWN_PCT = Gauge(
    "ai_live_drawdown_pct",
    "Current drawdown as percentage of peak equity.",
    ["trader_id", "strategy_id", "environment"],
    registry=REGISTRY,
)

LIVE_OPEN_POSITIONS = Gauge(
    "ai_live_open_positions",
    "Number of currently open positions.",
    ["trader_id", "strategy_id", "environment"],
    registry=REGISTRY,
)

LIVE_POSITION_VALUE = Gauge(
    "ai_live_position_value",
    "Total value of all open positions.",
    ["trader_id", "strategy_id", "instrument_id", "side"],
    registry=REGISTRY,
)

LIVE_POSITION_PNL = Gauge(
    "ai_live_position_pnl",
    "Unrealized P&L for specific position.",
    ["trader_id", "strategy_id", "instrument_id", "side"],
    registry=REGISTRY,
)

LIVE_TRADES_TOTAL = Gauge(
    "ai_live_trades_total",
    "Total number of completed trades in session.",
    ["trader_id", "strategy_id", "environment"],
    registry=REGISTRY,
)

LIVE_WIN_RATE = Gauge(
    "ai_live_win_rate_pct",
    "Win rate percentage for live trading session.",
    ["trader_id", "strategy_id", "environment"],
    registry=REGISTRY,
)

LIVE_PROFIT_FACTOR = Gauge(
    "ai_live_profit_factor",
    "Profit factor for live trading session.",
    ["trader_id", "strategy_id", "environment"],
    registry=REGISTRY,
)

LIVE_SHARPE_RATIO = Gauge(
    "ai_live_sharpe_ratio",
    "Sharpe ratio for live trading session.",
    ["trader_id", "strategy_id", "environment"],
    registry=REGISTRY,
)

LIVE_ORDERS_SUBMITTED = Gauge(
    "ai_live_orders_submitted_total",
    "Total orders submitted by status.",
    ["trader_id", "strategy_id", "instrument_id", "status"],
    registry=REGISTRY,
)

LIVE_ORDERS_FILLED = Gauge(
    "ai_live_orders_filled_total",
    "Total number of filled orders.",
    ["trader_id", "strategy_id", "instrument_id"],
    registry=REGISTRY,
)

LIVE_ORDERS_REJECTED = Gauge(
    "ai_live_orders_rejected_total",
    "Total number of rejected orders.",
    ["trader_id", "strategy_id", "instrument_id"],
    registry=REGISTRY,
)

LIVE_FEES_TOTAL = Gauge(
    "ai_live_fees_total",
    "Total trading fees paid in live session.",
    ["trader_id", "strategy_id", "environment"],
    registry=REGISTRY,
)

LIVE_ALERTS_COUNT = Gauge(
    "ai_live_alerts_total",
    "Number of alerts triggered by type and severity.",
    ["trader_id", "strategy_id", "alert_type", "severity"],
    registry=REGISTRY,
)

LIVE_ALERTS_UNACKNOWLEDGED = Gauge(
    "ai_live_alerts_unacknowledged",
    "Number of unacknowledged alerts by severity.",
    ["trader_id", "strategy_id", "severity"],
    registry=REGISTRY,
)

# Exposed objects for import convenience.
__all__ = [
    "REGISTRY",
    "BACKTEST_LAST_COMPLETED",
    "BACKTEST_STATUS",
    "BACKTEST_TOTAL_PNL",
    "BACKTEST_DRAWDOWN",
    "BACKTEST_TOTAL_PNL_PCT",
    "BACKTEST_TOTAL_TRADES",
    "BACKTEST_WIN_RATE",
    "BACKTEST_PROFIT_FACTOR",
    "BACKTEST_SHARPE_RATIO",
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
    "GPU_VALIDATION_SEGMENT_PNL_MEAN",
    "GPU_VALIDATION_SEGMENT_PNL_MEDIAN",
    "GPU_VALIDATION_SEGMENT_TRADES_MEAN",
    "GPU_VALIDATION_SEGMENT_TRADES_MEDIAN",
    "LIVE_SESSION_STATUS",
    "LIVE_SESSION_RUNTIME",
    "LIVE_EQUITY_TOTAL",
    "LIVE_EQUITY_CASH",
    "LIVE_PNL_UNREALIZED",
    "LIVE_PNL_REALIZED",
    "LIVE_PNL_TOTAL",
    "LIVE_PNL_TOTAL_PCT",
    "LIVE_DRAWDOWN_PCT",
    "LIVE_OPEN_POSITIONS",
    "LIVE_POSITION_VALUE",
    "LIVE_POSITION_PNL",
    "LIVE_TRADES_TOTAL",
    "LIVE_WIN_RATE",
    "LIVE_PROFIT_FACTOR",
    "LIVE_SHARPE_RATIO",
    "LIVE_ORDERS_SUBMITTED",
    "LIVE_ORDERS_FILLED",
    "LIVE_ORDERS_REJECTED",
    "LIVE_FEES_TOTAL",
    "LIVE_ALERTS_COUNT",
    "LIVE_ALERTS_UNACKNOWLEDGED",
]
