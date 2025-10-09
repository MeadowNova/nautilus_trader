from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
import threading
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

pre_parser = argparse.ArgumentParser(add_help=False)
pre_parser.add_argument("--force-cpu", action="store_true")
pre_args, _ = pre_parser.parse_known_args()
if pre_args.force_cpu:
    os.environ["CUDA_VISIBLE_DEVICES"] = ""

from decimal import Decimal

import numpy as np
import pandas as pd
import torch
from nautilus_trader.backtest.engine import BacktestEngine, BacktestEngineConfig
from nautilus_trader.config import LoggingConfig
from nautilus_trader.model.currencies import BTC, USDT
from nautilus_trader.model.enums import AccountType, AssetClass, OmsType
from nautilus_trader.model.identifiers import TraderId, Venue
from nautilus_trader.model.instruments import CryptoPerpetual
from nautilus_trader.model.objects import Money
from nautilus_trader.model.data import BarType
from nautilus_trader.persistence.wranglers import BarDataWrangler

from ajk_strategies.ai_adaptive_stragey_v3 import (
    AIAdaptiveStrategyConfigV3,
    AIAdaptiveStrategyV3,
)


PROJECT_ROOT = Path(__file__).resolve().parents[1]
DATA_PATH = PROJECT_ROOT / "data" / "nautilus"
RESULTS_DIR = PROJECT_ROOT / "backtest_results"
GPU_MODEL_PATH = PROJECT_ROOT / "ajk_strategies" / "models" / "signal_aggregator_xgb_gpu.pkl"


def humanize_seconds(seconds: float) -> str:
    minutes, sec = divmod(int(seconds), 60)
    hours, minutes = divmod(minutes, 60)
    if hours:
        return f"{hours}h {minutes}m {sec}s"
    if minutes:
        return f"{minutes}m {sec}s"
    return f"{sec}s"


def load_instrument(symbol: str) -> CryptoPerpetual:
    from nautilus_trader.test_kit.providers import TestInstrumentProvider

    symbol_map = {
        "BTC-USDT": TestInstrumentProvider.btcusdt_binance,
        "ETH-USDT": TestInstrumentProvider.ethusdt_binance,
    }
    if symbol not in symbol_map:
        raise ValueError(f"Unsupported instrument symbol: {symbol}")
    instrument = symbol_map[symbol]()
    return instrument  # type: ignore[return-value]


def load_bars(
    instrument_symbol: str,
    instrument: CryptoPerpetual,
    max_bars: int,
    start_offset: int = 0,
) -> list:
    parquet_file = DATA_PATH / f"{instrument_symbol}-1-MINUTE.parquet"
    if not parquet_file.exists():
        raise FileNotFoundError(f"Parquet file not found: {parquet_file}")

    import pyarrow.parquet as pq

    table = pq.read_table(str(parquet_file))
    df = table.to_pandas()
    if start_offset:
        df = df.iloc[start_offset:]
    df["timestamp"] = pd.to_datetime(df["ts_event"], unit="ms", utc=True)
    df = df.set_index("timestamp").sort_index()
    numeric_cols = ["open", "high", "low", "close", "volume"]
    df = df[numeric_cols].apply(pd.to_numeric, errors="coerce").dropna()

    if len(df) > max_bars:
        df = df.head(max_bars)

    bar_type_str = f"{instrument.id}-1-MINUTE-LAST-EXTERNAL"
    wrangler = BarDataWrangler(
        bar_type=BarType.from_str(bar_type_str),
        instrument=instrument,
    )
    bars = wrangler.process(df)
    if not bars:
        raise ValueError("No bars generated for backtest.")
    return bars


def monitor_gpu_utilization(stop_event: threading.Event) -> dict:
    stats = {"max_util": 0}
    if not torch.cuda.is_available() or pre_args.force_cpu:
        return stats

    process = subprocess.Popen(
        ["nvidia-smi", "--query-gpu=utilization.gpu", "--format=csv,noheader,nounits", "--loop-ms=1000"],
        stdout=subprocess.PIPE,
        stderr=subprocess.DEVNULL,
        text=True,
    )

    def reader() -> None:
        if not process.stdout:
            return
        try:
            for line in process.stdout:
                if stop_event.is_set():
                    break
                line = line.strip()
                if line.isdigit():
                    value = int(line)
                    stats["max_util"] = max(stats["max_util"], value)
        finally:
            process.terminate()

    thread = threading.Thread(target=reader, daemon=True)
    thread.start()
    stats["thread"] = thread
    stats["process"] = process
    return stats


def finalize_gpu_monitor(monitor: dict, stop_event: threading.Event) -> int:
    stop_event.set()
    thread = monitor.get("thread")
    process = monitor.get("process")
    if thread:
        thread.join(timeout=2)
    if process and process.poll() is None:
        process.terminate()
    return int(monitor.get("max_util", 0))


def run_backtest(
    max_bars: int,
    device_label: str,
    confidence_threshold: float,
    enable_monte_carlo: bool,
    max_hold_bars: int,
    feature_warmup_bars: int,
    start_offset: int = 0,
) -> dict:
    instrument_symbol = "BTC-USDT"
    instrument = load_instrument(instrument_symbol)
    bars = load_bars(
        instrument_symbol,
        instrument,
        max_bars=max_bars,
        start_offset=start_offset,
    )
    print(
        f"Loaded {len(bars)} bars for validation (offset={start_offset})."
    )

    engine = BacktestEngine(
        config=BacktestEngineConfig(
            trader_id=TraderId(f"AI-ADAPTIVE-V3-{instrument_symbol}"),
            logging=LoggingConfig(log_level="INFO"),
        )
    )

    engine.add_venue(
        venue=Venue("BINANCE"),
        oms_type=OmsType.NETTING,
        account_type=AccountType.CASH,
        base_currency=None,
        starting_balances=[
            Money(Decimal("100000"), USDT),
            Money(Decimal("10"), BTC),
        ],
    )
    engine.add_instrument(instrument)
    engine.add_data(bars)

    bar_type_str = f"{instrument.id}-1-MINUTE-LAST-EXTERNAL"
    strategy_config = AIAdaptiveStrategyConfigV3(
        instrument_id=str(instrument.id),
        bar_type=bar_type_str,
        venue="BINANCE",
        model_path_signal_xgb=str(GPU_MODEL_PATH),
        model_path_regime_hmm=str(PROJECT_ROOT / "ajk_strategies" / "models" / "market_regime_hmm.pkl"),
        model_path_forecast_lstm=str(PROJECT_ROOT / "ajk_strategies" / "models" / "price_forecast_lstm.h5"),
        max_bars_per_run=max_bars,
        confidence_threshold=confidence_threshold,
        enable_monte_carlo=enable_monte_carlo,
        max_bars_in_position=max_hold_bars,
        feature_warmup_bars=feature_warmup_bars,
    )
    strategy = AIAdaptiveStrategyV3(strategy_config)
    engine.add_strategy(strategy)

    start_time = datetime.now(timezone.utc)
    try:
        engine.run()
    except Exception as exc:  # noqa: BLE001
        raise RuntimeError(f"Backtest failed: {exc}") from exc
    end_time = datetime.now(timezone.utc)
    duration = (end_time - start_time).total_seconds()

    account = next(iter(engine.cache.accounts()), None)
    if account is None:
        raise RuntimeError("No account data captured during backtest.")

    balances = {str(balance.currency): float(balance.total) for balance in account.balances().values()}
    final_usdt = balances.get("USDT", 0.0)
    base_qty = balances.get(str(BTC), 0.0)
    final_price = float(bars[-1].close)
    base_value = base_qty * final_price
    total_equity = final_usdt + base_value
    pnl = total_equity - 100_000.0
    pnl_pct = (pnl / 100_000.0) * 100

    positions = list(engine.cache.positions())
    closed_positions = [position for position in positions if position.is_closed]
    orders = list(engine.cache.orders())

    winning_positions = [p for p in closed_positions if p.realized_pnl and float(p.realized_pnl) > 0]
    losing_positions = [p for p in closed_positions if p.realized_pnl and float(p.realized_pnl) < 0]
    wins = len(winning_positions)
    losses = len(losing_positions)
    total_trades = wins + losses
    win_rate = (wins / total_trades) * 100 if total_trades else 0.0

    profit_factor = 0.0
    sharpe_ratio = 0.0
    if losses:
        avg_win = sum(float(p.realized_pnl) for p in winning_positions) / wins if wins else 0.0
        avg_loss = sum(float(p.realized_pnl) for p in losing_positions) / losses
        profit_factor = abs(avg_win / avg_loss) if avg_loss != 0 else 0.0

    pnl_values = [float(p.realized_pnl) for p in closed_positions if p.realized_pnl]
    if len(pnl_values) > 1 and np.std(pnl_values) > 0:
        sharpe_ratio = (np.mean(pnl_values) / np.std(pnl_values)) * np.sqrt(252)

    summary = {
        "instrument": instrument_symbol,
        "device": device_label,
        "bars_processed": len(bars),
        "runtime_seconds": duration,
        "total_equity": total_equity,
        "net_pnl": pnl,
        "pnl_pct": pnl_pct,
        "total_trades": total_trades,
        "win_rate": win_rate,
        "profit_factor": profit_factor,
        "sharpe_ratio": sharpe_ratio,
        "orders": len(orders),
        "closed_positions": len(closed_positions),
        "completed_at": end_time.isoformat(),
        "confidence_threshold": confidence_threshold,
        "monte_carlo_enabled": enable_monte_carlo,
        "segment_offset": start_offset,
        "bars_consumed": strategy._bars_processed,
    }

    return summary


def run_validation(args: argparse.Namespace) -> dict:
    RESULTS_DIR.mkdir(parents=True, exist_ok=True)

    device_label = "GPU"
    if args.force_cpu or not torch.cuda.is_available():
        device_label = "CPU"

    print(f"Starting AI-Adaptive V3 backtest (device={device_label})")
    if torch.cuda.is_available() and not args.force_cpu:
        print(f"GPU in use: {torch.cuda.get_device_name(0)}")
    else:
        print("Running with CPU execution.")
    print(f"Confidence threshold: {args.confidence_threshold:.2f}")
    print(f"Max hold bars: {args.max_hold_bars}")
    print(f"Feature warmup bars: {args.feature_warmup_bars}")
    print(f"Monte Carlo filter: {'enabled' if not args.disable_monte_carlo else 'disabled'}")

    try:
        subprocess.run(["nvidia-smi"], check=False)
    except FileNotFoundError:
        print("⚠️ nvidia-smi not available on this system.")

    stop_event = threading.Event()
    monitor = monitor_gpu_utilization(stop_event)

    mc_enabled = not args.disable_monte_carlo
    segment_summaries: list[dict] = []
    offset = 0
    for idx in range(args.segments):
        try:
            summary = run_backtest(
                max_bars=args.max_bars,
                device_label=device_label,
                confidence_threshold=args.confidence_threshold,
                enable_monte_carlo=mc_enabled,
                max_hold_bars=args.max_hold_bars,
                feature_warmup_bars=args.feature_warmup_bars,
                start_offset=offset,
            )
        except FileNotFoundError:
            print(f"No additional bars available for segment {idx}; stopping.")
            break
        summary["segment_index"] = idx
        segment_summaries.append(summary)
        offset += args.max_bars
        if summary.get("bars_consumed", 0) < args.feature_warmup_bars:
            print("Not enough bars consumed to continue; stopping segment loop.")
            break

    if not segment_summaries:
        raise RuntimeError("No validation segments completed successfully.")

    # Aggregate totals
    aggregate = {
        "instrument": segment_summaries[0]["instrument"],
        "device": device_label,
        "segments": len(segment_summaries),
        "bars_processed": sum(seg["bars_processed"] for seg in segment_summaries),
        "bars_consumed": sum(seg.get("bars_consumed", 0) for seg in segment_summaries),
        "runtime_seconds": sum(seg["runtime_seconds"] for seg in segment_summaries),
        "total_equity": segment_summaries[-1]["total_equity"],
        "net_pnl": sum(seg["net_pnl"] for seg in segment_summaries),
        "pnl_pct": sum(seg["pnl_pct"] for seg in segment_summaries),
        "total_trades": sum(seg["total_trades"] for seg in segment_summaries),
        "win_rate": 0.0,
        "profit_factor": 0.0,
        "sharpe_ratio": 0.0,
        "orders": sum(seg["orders"] for seg in segment_summaries),
        "closed_positions": sum(seg["closed_positions"] for seg in segment_summaries),
        "confidence_threshold": args.confidence_threshold,
        "monte_carlo_enabled": mc_enabled,
        "segment_details": segment_summaries,
    }

    # Compute aggregate win rate if data available
    total_closed = sum(seg["closed_positions"] for seg in segment_summaries)
    if total_closed:
        wins = sum(
            seg.get("win_rate", 0.0) / 100 * seg["closed_positions"]
            for seg in segment_summaries
        )
        aggregate["win_rate"] = (wins / total_closed) * 100

    summary = aggregate

    max_util = finalize_gpu_monitor(monitor, stop_event)
    if device_label == "GPU":
        print(f"Observed max GPU utilization: {max_util}%")
        if max_util < 1 and not args.force_cpu:
            print("⚠️ GPU utilization below 1%. Rerunning validation on CPU.")
            env = os.environ.copy()
            env["CUDA_VISIBLE_DEVICES"] = ""
            cpu_result = subprocess.run(
                [sys.executable, __file__, "--max-bars", str(args.max_bars), "--force-cpu"],
                env=env,
                check=True,
                capture_output=True,
                text=True,
            )
            print(cpu_result.stdout)
            return json.loads(cpu_result.stdout.splitlines()[-1])

    if args.max_bars >= 1000:
        bars_label = f"{args.max_bars // 1000}k"
    else:
        bars_label = str(args.max_bars)
    results_path = RESULTS_DIR / f"gpu_validation_{bars_label}_summary.json"
    with results_path.open("w") as fp:
        json.dump(summary, fp, indent=2)

    print(f"Elapsed runtime: {summary['runtime_seconds']:.2f} seconds")
    print(f"Total trades executed: {summary['total_trades']}")
    print(f"Total PnL: ${summary['net_pnl']:.2f} ({summary['pnl_pct']:+.2f}%)")
    if summary["sharpe_ratio"]:
        print(f"Sharpe Ratio: {summary['sharpe_ratio']:.2f}")

    summary["max_gpu_util"] = max_util
    runtime_human = humanize_seconds(summary["runtime_seconds"])
    gpu_name = torch.cuda.get_device_name(0) if torch.cuda.is_available() and device_label == "GPU" else "CPU"
    summary_line = (
        f"Trades: {summary['total_trades']} | "
        f"PnL: {summary['pnl_pct']:+.2f}% | "
        f"Runtime: {runtime_human} | "
        f"GPU: {gpu_name} | "
        f"GPU Util: {max_util}% | "
        f"MC: {'on' if mc_enabled else 'off'}"
    )
    print("✅ GPU validation backtest completed successfully")
    print(summary_line)

    summary["summary_line"] = summary_line
    print(json.dumps(summary))
    return summary


def parse_args(argv: Optional[list[str]] = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run GPU validation backtest for AI-Adaptive Strategy V3.")
    parser.add_argument("--max-bars", type=int, default=50_000, help="Maximum number of bars to process.")
    parser.add_argument("--force-cpu", action="store_true", help="Force CPU execution (used for fallback).")
    parser.add_argument(
        "--confidence-threshold",
        type=float,
        default=0.75,
        help="Minimum class probability to open a position.",
    )
    parser.add_argument(
        "--disable-monte-carlo",
        action="store_true",
        help="Skip Monte Carlo risk rejection when generating trades.",
    )
    parser.add_argument(
        "--max-hold-bars",
        type=int,
        default=100,
        help="Maximum number of bars to keep a position open before forcing an exit.",
    )
    parser.add_argument(
        "--feature-warmup-bars",
        type=int,
        default=50,
        help="Number of bars required before generating features (reduces warmup delay).",
    )
    parser.add_argument(
        "--segments",
        type=int,
        default=1,
        help="Number of consecutive segments to evaluate (each of length max-bars).",
    )
    return parser.parse_args(argv)


def main(argv: Optional[list[str]] = None) -> None:
    args = parse_args(argv)
    run_validation(args)


if __name__ == "__main__":
    main()
