from __future__ import annotations

import logging
import json
from datetime import datetime
from pathlib import Path
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
    BACKTEST_TOTAL_PNL_PCT,
    BACKTEST_TOTAL_TRADES,
    BACKTEST_WIN_RATE,
    BACKTEST_PROFIT_FACTOR,
    BACKTEST_SHARPE_RATIO,
    GPU_VALIDATION_LAST_COMPLETED,
    GPU_VALIDATION_PNL,
    GPU_VALIDATION_RUNTIME,
    GPU_VALIDATION_SEGMENTS,
    GPU_VALIDATION_TRADES,
    GPU_VALIDATION_SEGMENT_PNL_MEAN,
    GPU_VALIDATION_SEGMENT_PNL_MEDIAN,
    GPU_VALIDATION_SEGMENT_TRADES_MEAN,
    GPU_VALIDATION_SEGMENT_TRADES_MEDIAN,
    MODEL_ARTIFACT_INFO,
    MODEL_TRAINING_STATUS,
    REDIS_KEY_COUNT,
    REDIS_MEMORY_USAGE,
    REDIS_UP,
    LIVE_SESSION_STATUS,
    LIVE_SESSION_RUNTIME,
    LIVE_EQUITY_TOTAL,
    LIVE_EQUITY_CASH,
    LIVE_PNL_UNREALIZED,
    LIVE_PNL_REALIZED,
    LIVE_PNL_TOTAL,
    LIVE_PNL_TOTAL_PCT,
    LIVE_DRAWDOWN_PCT,
    LIVE_OPEN_POSITIONS,
    LIVE_POSITION_VALUE,
    LIVE_POSITION_PNL,
    LIVE_TRADES_TOTAL,
    LIVE_WIN_RATE,
    LIVE_PROFIT_FACTOR,
    LIVE_SHARPE_RATIO,
    LIVE_ORDERS_SUBMITTED,
    LIVE_ORDERS_FILLED,
    LIVE_ORDERS_REJECTED,
    LIVE_FEES_TOTAL,
    LIVE_ALERTS_COUNT,
    LIVE_ALERTS_UNACKNOWLEDGED,
    REGISTRY,
)

LOGGER = logging.getLogger(__name__)
PROJECT_ROOT = Path(__file__).resolve().parents[2]
GPU_SUMMARY_DIR = PROJECT_ROOT / "backtest_results"


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
        self._refresh_gpu_validation()
        self._refresh_live_trading()

    # ------------------------------------------------------------------ #
    def _refresh_backtests(self) -> None:
        BACKTEST_LAST_COMPLETED.clear()
        BACKTEST_STATUS.clear()
        BACKTEST_TOTAL_PNL.clear()
        BACKTEST_DRAWDOWN.clear()
        BACKTEST_TOTAL_PNL_PCT.clear()
        BACKTEST_TOTAL_TRADES.clear()
        BACKTEST_WIN_RATE.clear()
        BACKTEST_PROFIT_FACTOR.clear()
        BACKTEST_SHARPE_RATIO.clear()

        sql = """
            SELECT
                br.id AS backtest_run_id,
                br.strategy_id,
                br.run_name,
                br.status,
                br.started_at,
                br.completed_at,
                perf.total_pnl,
                perf.max_drawdown_pct,
                perf.total_pnl_pct,
                perf.total_trades,
                perf.calculated_win_rate,
                perf.profit_factor,
                perf.sharpe_ratio,
                perf.instrument_id
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
            instrument_id = row.get("instrument_id") or "unknown"
            status = row["status"] or "unknown"
            completed_at = row.get("completed_at")
            started_at = row.get("started_at")
            total_pnl = row.get("total_pnl") or 0.0
            drawdown_pct = row.get("max_drawdown_pct") or 0.0
            total_pnl_pct = row.get("total_pnl_pct") or 0.0
            total_trades = row.get("total_trades") or 0.0
            win_rate = row.get("calculated_win_rate") or 0.0
            profit_factor = row.get("profit_factor") or 0.0
            sharpe_ratio = row.get("sharpe_ratio") or 0.0

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
            BACKTEST_TOTAL_PNL_PCT.labels(strategy_id, run_name, instrument_id).set(
                float(total_pnl_pct)
            )
            BACKTEST_TOTAL_TRADES.labels(strategy_id, run_name, instrument_id).set(
                float(total_trades)
            )
            BACKTEST_WIN_RATE.labels(strategy_id, run_name, instrument_id).set(
                float(win_rate)
            )
            BACKTEST_PROFIT_FACTOR.labels(strategy_id, run_name, instrument_id).set(
                float(profit_factor)
            )
            BACKTEST_SHARPE_RATIO.labels(strategy_id, run_name, instrument_id).set(
                float(sharpe_ratio)
            )

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

    # ------------------------------------------------------------------ #
    def _refresh_gpu_validation(self) -> None:
        GPU_VALIDATION_TRADES.clear()
        GPU_VALIDATION_PNL.clear()
        GPU_VALIDATION_RUNTIME.clear()
        GPU_VALIDATION_SEGMENTS.clear()
        GPU_VALIDATION_LAST_COMPLETED.clear()
        GPU_VALIDATION_SEGMENT_PNL_MEAN.clear()
        GPU_VALIDATION_SEGMENT_PNL_MEDIAN.clear()
        GPU_VALIDATION_SEGMENT_TRADES_MEAN.clear()
        GPU_VALIDATION_SEGMENT_TRADES_MEDIAN.clear()

        if not GPU_SUMMARY_DIR.exists():
            return

        for path in sorted(GPU_SUMMARY_DIR.glob("gpu_validation_*_summary.json")):
            try:
                data = json.loads(path.read_text())
            except Exception:  # noqa: BLE001
                LOGGER.exception("Failed to parse GPU validation summary: %s", path)
                continue

            instrument = data.get("instrument", "unknown")
            device = data.get("device", "unknown")
            summary_file = path.name

            GPU_VALIDATION_TRADES.labels(summary_file, instrument, device).set(
                float(data.get("total_trades", 0.0))
            )
            GPU_VALIDATION_PNL.labels(summary_file, instrument, device).set(
                float(data.get("net_pnl", 0.0))
            )
            GPU_VALIDATION_RUNTIME.labels(summary_file, instrument, device).set(
                float(data.get("runtime_seconds", 0.0))
            )

            segments = int(data.get("segments")) if "segments" in data else 1
            GPU_VALIDATION_SEGMENTS.labels(summary_file).set(float(segments))

            completed_timestamp = 0.0
            segment_details = data.get("segment_details") or []
            if segment_details:
                last_completed = segment_details[-1].get("completed_at")
            else:
                last_completed = data.get("completed_at")
            if isinstance(last_completed, str):
                try:
                    dt = datetime.fromisoformat(last_completed.replace("Z", "+00:00"))
                    completed_timestamp = dt.timestamp()
                except ValueError:
                    LOGGER.warning(
                        "Unable to parse GPU validation completion timestamp %s", last_completed
                    )
            GPU_VALIDATION_LAST_COMPLETED.labels(summary_file).set(completed_timestamp)

            if segment_details:
                segment_pnls = [float(item.get("net_pnl", 0.0)) for item in segment_details]
                segment_trades = [float(item.get("total_trades", 0.0)) for item in segment_details]

                mean_pnl = sum(segment_pnls) / len(segment_pnls)
                sorted_pnls = sorted(segment_pnls)
                mid_index = len(sorted_pnls) // 2
                if len(sorted_pnls) % 2 == 0:
                    median_pnl = (sorted_pnls[mid_index - 1] + sorted_pnls[mid_index]) / 2.0
                else:
                    median_pnl = sorted_pnls[mid_index]

                mean_trades = sum(segment_trades) / len(segment_trades)
                sorted_trades = sorted(segment_trades)
                mid_trades = len(sorted_trades) // 2
                if len(sorted_trades) % 2 == 0:
                    median_trades = (sorted_trades[mid_trades - 1] + sorted_trades[mid_trades]) / 2.0
                else:
                    median_trades = sorted_trades[mid_trades]

                GPU_VALIDATION_SEGMENT_PNL_MEAN.labels(summary_file).set(float(mean_pnl))
                GPU_VALIDATION_SEGMENT_PNL_MEDIAN.labels(summary_file).set(float(median_pnl))
                GPU_VALIDATION_SEGMENT_TRADES_MEAN.labels(summary_file).set(float(mean_trades))
                GPU_VALIDATION_SEGMENT_TRADES_MEDIAN.labels(summary_file).set(float(median_trades))

    # ------------------------------------------------------------------ #
    def _refresh_live_trading(self) -> None:
        """Refresh live trading metrics from database views."""
        # Clear all live metrics
        LIVE_SESSION_STATUS.clear()
        LIVE_SESSION_RUNTIME.clear()
        LIVE_EQUITY_TOTAL.clear()
        LIVE_EQUITY_CASH.clear()
        LIVE_PNL_UNREALIZED.clear()
        LIVE_PNL_REALIZED.clear()
        LIVE_PNL_TOTAL.clear()
        LIVE_PNL_TOTAL_PCT.clear()
        LIVE_DRAWDOWN_PCT.clear()
        LIVE_OPEN_POSITIONS.clear()
        LIVE_POSITION_VALUE.clear()
        LIVE_POSITION_PNL.clear()
        LIVE_TRADES_TOTAL.clear()
        LIVE_WIN_RATE.clear()
        LIVE_PROFIT_FACTOR.clear()
        LIVE_SHARPE_RATIO.clear()
        LIVE_ORDERS_SUBMITTED.clear()
        LIVE_ORDERS_FILLED.clear()
        LIVE_ORDERS_REJECTED.clear()
        LIVE_FEES_TOTAL.clear()
        LIVE_ALERTS_COUNT.clear()
        LIVE_ALERTS_UNACKNOWLEDGED.clear()

        # Query current active sessions with latest metrics
        sessions_sql = """
            SELECT * FROM ai_extensions.v_live_sessions_current
            ORDER BY started_at DESC;
        """

        with self._pool.connection() as connection:
            with connection.cursor(cursor_factory=RealDictCursor) as cursor:
                cursor.execute(sessions_sql)
                sessions: Iterable[Mapping[str, object]] = cursor.fetchall()

        for session in sessions:
            trader_id = session.get("trader_id") or "unknown"
            strategy_id = session.get("strategy_id") or "unknown"
            session_name = session.get("session_name") or "unnamed"
            environment = session.get("environment") or "unknown"
            status = session.get("status") or "unknown"

            # Session metrics
            LIVE_SESSION_STATUS.labels(
                trader_id, strategy_id, session_name, environment, status
            ).set(1.0 if status == "RUNNING" else 0.0)

            runtime_seconds = session.get("runtime_seconds") or 0
            LIVE_SESSION_RUNTIME.labels(trader_id, strategy_id, session_name).set(
                float(runtime_seconds)
            )

            # Equity metrics
            total_equity = session.get("total_equity") or 0.0
            cash_balance = session.get("cash_balance") or 0.0
            unrealized_pnl = session.get("unrealized_pnl") or 0.0
            realized_pnl = session.get("realized_pnl") or 0.0
            total_pnl = session.get("total_pnl") or 0.0
            total_pnl_pct = session.get("total_pnl_pct") or 0.0
            drawdown_pct = session.get("drawdown_pct") or 0.0
            num_open_positions = session.get("num_open_positions") or 0

            LIVE_EQUITY_TOTAL.labels(trader_id, strategy_id, environment).set(
                float(total_equity)
            )
            LIVE_EQUITY_CASH.labels(trader_id, strategy_id, environment).set(
                float(cash_balance)
            )
            LIVE_PNL_UNREALIZED.labels(trader_id, strategy_id, environment).set(
                float(unrealized_pnl)
            )
            LIVE_PNL_REALIZED.labels(trader_id, strategy_id, environment).set(
                float(realized_pnl)
            )
            LIVE_PNL_TOTAL.labels(trader_id, strategy_id, environment).set(
                float(total_pnl)
            )
            LIVE_PNL_TOTAL_PCT.labels(trader_id, strategy_id, environment).set(
                float(total_pnl_pct)
            )
            LIVE_DRAWDOWN_PCT.labels(trader_id, strategy_id, environment).set(
                float(drawdown_pct)
            )
            LIVE_OPEN_POSITIONS.labels(trader_id, strategy_id, environment).set(
                float(num_open_positions)
            )

            # Performance metrics
            total_trades = session.get("total_trades") or 0
            win_rate = session.get("win_rate") or 0.0
            profit_factor = session.get("profit_factor") or 0.0
            sharpe_ratio = session.get("sharpe_ratio") or 0.0
            total_fees = session.get("total_fees_paid") or 0.0

            LIVE_TRADES_TOTAL.labels(trader_id, strategy_id, environment).set(
                float(total_trades)
            )
            LIVE_WIN_RATE.labels(trader_id, strategy_id, environment).set(
                float(win_rate)
            )
            LIVE_PROFIT_FACTOR.labels(trader_id, strategy_id, environment).set(
                float(profit_factor)
            )
            LIVE_SHARPE_RATIO.labels(trader_id, strategy_id, environment).set(
                float(sharpe_ratio)
            )
            LIVE_FEES_TOTAL.labels(trader_id, strategy_id, environment).set(
                float(total_fees)
            )

        # Query open positions
        positions_sql = """
            SELECT * FROM ai_extensions.v_live_positions_open
            ORDER BY opened_at DESC;
        """

        with self._pool.connection() as connection:
            with connection.cursor(cursor_factory=RealDictCursor) as cursor:
                cursor.execute(positions_sql)
                positions: Iterable[Mapping[str, object]] = cursor.fetchall()

        for position in positions:
            trader_id = "PAPER-TRADER-001"  # Default for now
            strategy_id = position.get("strategy_id") or "unknown"
            instrument_id = position.get("instrument_id") or "unknown"
            side = position.get("side") or "FLAT"
            quantity = position.get("quantity") or 0.0
            current_price = position.get("current_price") or 0.0
            unrealized_pnl = position.get("unrealized_pnl") or 0.0

            position_value = float(quantity) * float(current_price)
            LIVE_POSITION_VALUE.labels(
                trader_id, strategy_id, instrument_id, side
            ).set(position_value)
            LIVE_POSITION_PNL.labels(
                trader_id, strategy_id, instrument_id, side
            ).set(float(unrealized_pnl))

        # Query order statistics
        orders_sql = """
            SELECT
                strategy_id,
                environment,
                instrument_id,
                status,
                COUNT(*) AS order_count
            FROM ai_extensions.v_live_orders_recent
            GROUP BY strategy_id, environment, instrument_id, status;
        """

        with self._pool.connection() as connection:
            with connection.cursor(cursor_factory=RealDictCursor) as cursor:
                cursor.execute(orders_sql)
                order_stats: Iterable[Mapping[str, object]] = cursor.fetchall()

        for stat in order_stats:
            trader_id = "PAPER-TRADER-001"
            strategy_id = stat.get("strategy_id") or "unknown"
            instrument_id = stat.get("instrument_id") or "unknown"
            status = stat.get("status") or "unknown"
            order_count = stat.get("order_count") or 0

            LIVE_ORDERS_SUBMITTED.labels(
                trader_id, strategy_id, instrument_id, status
            ).set(float(order_count))

            if status == "FILLED":
                LIVE_ORDERS_FILLED.labels(
                    trader_id, strategy_id, instrument_id
                ).set(float(order_count))
            elif status == "REJECTED":
                LIVE_ORDERS_REJECTED.labels(
                    trader_id, strategy_id, instrument_id
                ).set(float(order_count))

        # Query alerts
        alerts_sql = """
            SELECT
                ls.trader_id,
                ls.strategy_id,
                la.alert_type,
                la.severity,
                COUNT(*) AS alert_count,
                COUNT(*) FILTER (WHERE NOT la.acknowledged) AS unacknowledged_count
            FROM ai_extensions.live_alerts la
            JOIN ai_extensions.live_sessions ls ON ls.id = la.session_id
            WHERE la.triggered_at > NOW() - INTERVAL '24 hours'
            GROUP BY ls.trader_id, ls.strategy_id, la.alert_type, la.severity;
        """

        with self._pool.connection() as connection:
            with connection.cursor(cursor_factory=RealDictCursor) as cursor:
                cursor.execute(alerts_sql)
                alert_stats: Iterable[Mapping[str, object]] = cursor.fetchall()

        for stat in alert_stats:
            trader_id = stat.get("trader_id") or "unknown"
            strategy_id = stat.get("strategy_id") or "unknown"
            alert_type = stat.get("alert_type") or "unknown"
            severity = stat.get("severity") or "unknown"
            alert_count = stat.get("alert_count") or 0
            unack_count = stat.get("unacknowledged_count") or 0

            LIVE_ALERTS_COUNT.labels(
                trader_id, strategy_id, alert_type, severity
            ).set(float(alert_count))

            if unack_count > 0:
                LIVE_ALERTS_UNACKNOWLEDGED.labels(
                    trader_id, strategy_id, severity
                ).set(float(unack_count))


__all__ = ["MetricsCollector"]
