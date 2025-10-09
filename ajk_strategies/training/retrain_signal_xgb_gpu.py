from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Tuple

if __package__ is None:  # pragma: no cover
    sys.path.append(str(Path(__file__).resolve().parents[2]))

import joblib
import numpy as np
import pandas as pd
import torch
from sklearn.preprocessing import StandardScaler
from sklearn.utils import class_weight
from xgboost import XGBClassifier

from ajk_strategies.training import persist_training_run
from ajk_strategies.training.features import (
    compute_regime_features,
    load_price_frame,
    resolve_input_files,
)
from ajk_strategies.training.train_signal_xgb import (
    compute_lstm_forecasts,
    compute_regimes,
    compute_targets,
    load_hmm,
    load_lstm,
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Retrain signal aggregator XGBoost model with GPU acceleration.")
    parser.add_argument(
        "--input-path",
        type=Path,
        default=Path("data/nautilus"),
        help="Path to Nautilus-format parquet data.",
    )
    parser.add_argument(
        "--pattern",
        default="*.parquet",
        help="Glob pattern for parquet files inside input path.",
    )
    parser.add_argument(
        "--instrument",
        default=None,
        help="Optional instrument identifier to filter within parquet files.",
    )
    parser.add_argument(
        "--max-rows",
        type=int,
        default=None,
        help="Optional cap on number of rows for rapid experimentation.",
    )
    parser.add_argument(
        "--output-path",
        type=Path,
        default=Path("ajk_strategies/models/signal_aggregator_xgb_gpu.pkl"),
        help="Destination path for the trained model artifact.",
    )
    parser.add_argument(
        "--volatility-window",
        type=int,
        default=30,
        help="Rolling window for volatility feature.",
    )
    parser.add_argument(
        "--future-horizon",
        type=int,
        default=15,
        help="Bars ahead for target computation.",
    )
    parser.add_argument(
        "--return-threshold",
        type=float,
        default=0.001,
        help="Return threshold for long/short labels.",
    )
    parser.add_argument(
        "--random-state",
        type=int,
        default=42,
        help="Random seed for reproducibility.",
    )
    parser.add_argument(
        "--hmm-model-path",
        type=Path,
        default=Path("ajk_strategies/models/market_regime_hmm.pkl"),
    )
    parser.add_argument(
        "--lstm-model-path",
        type=Path,
        default=Path("ajk_strategies/models/price_forecast_lstm.h5"),
    )
    parser.add_argument(
        "--lstm-meta-path",
        type=Path,
        default=Path("ajk_strategies/models/price_forecast_lstm_meta.pkl"),
    )
    return parser.parse_args()


def log_gpu_state() -> None:
    if torch.cuda.is_available():
        print(f"GPU detected: {torch.cuda.get_device_name(0)}")
    else:
        print("⚠️ CUDA not available. Training will fall back to CPU.")
    try:
        subprocess.run(["nvidia-smi"], check=False)
    except FileNotFoundError:
        print("⚠️ nvidia-smi command not found; unable to display live GPU stats.")


def query_gpu_utilization() -> int | None:
    try:
        output = subprocess.check_output(
            ["nvidia-smi", "--query-gpu=utilization.gpu", "--format=csv,noheader,nounits"],
            text=True,
        )
        util_values = [int(value) for value in output.strip().splitlines() if value.strip().isdigit()]
        return util_values[0] if util_values else None
    except (subprocess.CalledProcessError, FileNotFoundError, ValueError):
        return None


def build_dataset(
    input_path: Path,
    pattern: str,
    instrument: str | None,
    max_rows: int | None,
    volatility_window: int,
    future_horizon: int,
    return_threshold: float,
    hmm_model_path: Path,
    lstm_model_path: Path,
    lstm_meta_path: Path,
) -> Tuple[np.ndarray, np.ndarray, StandardScaler, list[str], list[str], pd.DataFrame, list[Path]]:
    files = resolve_input_files(input_path.expanduser().resolve(), pattern, max_files=None)
    price_frame = load_price_frame(files, instrument=instrument)

    if max_rows is not None and len(price_frame) > max_rows:
        price_frame = price_frame.tail(max_rows)

    feature_frame = compute_regime_features(
        price_frame["close"],
        volatility_window=volatility_window,
    ).sort_index()

    hmm_model, hmm_scaler, state_mapping = load_hmm(hmm_model_path.expanduser().resolve())
    regimes = compute_regimes(feature_frame, hmm_model, hmm_scaler, state_mapping)

    lstm_model, lstm_meta = load_lstm(
        lstm_model_path.expanduser().resolve(),
        lstm_meta_path.expanduser().resolve(),
    )
    lstm_forecasts = compute_lstm_forecasts(price_frame["close"], lstm_model, lstm_meta)

    dataset = feature_frame.join(regimes, how="inner").join(lstm_forecasts, how="inner").dropna()
    targets = compute_targets(price_frame["close"], future_horizon, return_threshold)
    dataset = dataset.join(targets, how="inner").dropna()

    if dataset.empty:
        raise ValueError("Dataset is empty after feature/target alignment. Check horizon and thresholds.")

    feature_columns = ["dsp_trend", "volatility", "lstm_forecast", "regime"]
    numeric_columns = ["dsp_trend", "volatility", "lstm_forecast"]

    scaler = StandardScaler()
    scaled_numeric = scaler.fit_transform(dataset[numeric_columns])
    X = np.column_stack([scaled_numeric, dataset["regime"].to_numpy().reshape(-1, 1)])
    y = dataset["label"].to_numpy(dtype=int)

    return X, y, scaler, feature_columns, numeric_columns, dataset, files


def fit_model(
    X: np.ndarray,
    y: np.ndarray,
    sample_weights: np.ndarray,
    random_state: int,
) -> tuple[XGBClassifier, str, float]:
    preferred_device = "cuda" if torch.cuda.is_available() else "cpu"
    device_used = preferred_device

    while True:
        print(f"🚀 Starting XGBoost training on device={device_used.upper()}")
        start = time.perf_counter()
        model = XGBClassifier(
            tree_method="hist",
            device=device_used,
            n_estimators=500,
            max_depth=6,
            learning_rate=0.05,
            subsample=0.8,
            colsample_bytree=0.8,
            objective="multi:softprob",
            eval_metric="mlogloss",
            num_class=3,
            random_state=random_state,
        )
        model.fit(X, y, sample_weight=sample_weights)
        elapsed = time.perf_counter() - start
        print(f"⏱️ Training completed in {elapsed:.2f} seconds on {device_used.upper()}")

        if device_used == "cuda":
            util = query_gpu_utilization()
            if util is not None:
                print(f"📈 Reported GPU utilization: {util}%")
                if util < 1:
                    print("⚠️ GPU utilization below 1%. Retrying training on CPU for safety.")
                    device_used = "cpu"
                    continue
            else:
                print("⚠️ Unable to query GPU utilization; proceeding with CUDA results.")

        return model, device_used, elapsed


def save_artifact(
    model: XGBClassifier,
    scaler: StandardScaler,
    feature_columns: list[str],
    numeric_columns: list[str],
    dataset: pd.DataFrame,
    future_horizon: int,
    return_threshold: float,
    output_path: Path,
) -> dict:
    output_path = output_path.expanduser().resolve()
    output_path.parent.mkdir(parents=True, exist_ok=True)

    artifact = {
        "model": model,
        "feature_columns": feature_columns,
        "numeric_columns": numeric_columns,
        "scaler": scaler,
        "future_horizon": future_horizon,
        "return_threshold": return_threshold,
    }
    joblib.dump(artifact, output_path)
    print(f"💾 Model artifact saved to {output_path}")

    feature_hash = hashlib.sha256(
        np.ascontiguousarray(dataset[feature_columns].to_numpy(dtype=float)).tobytes()
    ).hexdigest()

    return {
        "path": str(output_path),
        "feature_hash": feature_hash,
    }


def main() -> None:
    args = parse_args()
    log_gpu_state()
    start_time = datetime.now(timezone.utc)

    try:
        (
            X,
            y,
            scaler,
            feature_columns,
            numeric_columns,
            dataset,
            dataset_files,
        ) = build_dataset(
            input_path=args.input_path,
            pattern=args.pattern,
            instrument=args.instrument,
            max_rows=args.max_rows,
            volatility_window=args.volatility_window,
            future_horizon=args.future_horizon,
            return_threshold=args.return_threshold,
            hmm_model_path=args.hmm_model_path,
            lstm_model_path=args.lstm_model_path,
            lstm_meta_path=args.lstm_meta_path,
        )
    except Exception as exc:  # noqa: BLE001
        raise SystemExit(f"❌ Failed to prepare dataset: {exc}") from exc

    class_counts = np.bincount(y, minlength=3)
    print(f"Class distribution (hold, long, short): {class_counts.tolist()}")
    sample_weights = class_weight.compute_sample_weight(class_weight="balanced", y=y)

    model, device_used, elapsed = fit_model(
        X=X,
        y=y,
        sample_weights=sample_weights,
        random_state=args.random_state,
    )

    try:
        proba_sample = model.predict_proba(X[:1])
        print(f"🔍 Sample prediction probabilities: {proba_sample[0].tolist()}")
    except Exception as exc:  # noqa: BLE001
        print(f"⚠️ Failed to compute sample prediction: {exc}")

    artifact_meta = save_artifact(
        model=model,
        scaler=scaler,
        feature_columns=feature_columns,
        numeric_columns=numeric_columns,
        dataset=dataset,
        future_horizon=args.future_horizon,
        return_threshold=args.return_threshold,
        output_path=args.output_path,
    )

    dataset_start = dataset.index.min().to_pydatetime() if not dataset.empty else None
    dataset_end = dataset.index.max().to_pydatetime() if not dataset.empty else None

    completed_at = datetime.now(timezone.utc)
    training_metadata = {
        "device_used": device_used,
        "elapsed_seconds": elapsed,
        "class_counts": class_counts.tolist(),
        "samples": int(len(dataset)),
    }

    run_id = persist_training_run(
        strategy_id="ai_adaptive_strategy_v3",
        model_name="signal_aggregator_xgb_gpu",
        model_version=start_time.strftime("%Y%m%d%H%M%S"),
        dataset_source=str(args.input_path),
        dataset_files=[str(path) for path in dataset_files],
        dataset_start=dataset_start,
        dataset_end=dataset_end,
        hyperparameters={
            "future_horizon": args.future_horizon,
            "return_threshold": args.return_threshold,
            "volatility_window": args.volatility_window,
            "n_estimators": 500,
            "max_depth": 6,
            "learning_rate": 0.05,
            "subsample": 0.8,
            "colsample_bytree": 0.8,
            "random_state": args.random_state,
            "tree_method": "hist",
            "device": device_used,
        },
        metrics=training_metadata,
        feature_hash=artifact_meta["feature_hash"],
        completed_at=completed_at,
        artifacts=[("signal_aggregator_xgb_gpu", Path(artifact_meta["path"]))],
    )
    if run_id:
        print(f"🗄️ Persisted training run under id: {run_id}")

    summary = {
        "device_used": device_used,
        "elapsed_seconds": elapsed,
        "class_distribution": class_counts.tolist(),
        "samples": int(len(dataset)),
        "model_path": artifact_meta["path"],
        "run_id": run_id,
    }
    print(json.dumps(summary, indent=2, default=str))

    print("✅ GPU retraining complete")


if __name__ == "__main__":
    main()
