from __future__ import annotations

import argparse
import sys
from pathlib import Path

if __package__ is None:  # pragma: no cover
    sys.path.append(str(Path(__file__).resolve().parents[2]))

import joblib
import numpy as np
import pandas as pd
from numpy.lib.stride_tricks import sliding_window_view

try:
    from sklearn.preprocessing import StandardScaler
    from sklearn.utils import class_weight
except ImportError as exc:  # pragma: no cover
    raise SystemExit("Install scikit-learn to run this training script.") from exc

try:
    from tensorflow import keras
except ImportError as exc:  # pragma: no cover
    raise SystemExit("Install tensorflow to compute LSTM forecasts.") from exc

try:
    from xgboost import XGBClassifier
except ImportError as exc:  # pragma: no cover
    raise SystemExit("Install xgboost to train the signal aggregator.") from exc

from ajk_strategies.training.features import (
    compute_regime_features,
    load_price_frame,
    resolve_input_files,
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Train XGBoost signal aggregation model.")
    parser.add_argument("--input-path", type=Path, required=True, help="Path to parquet file or directory.")
    parser.add_argument("--pattern", default="*.parquet", help="Filename glob when input is a directory.")
    parser.add_argument("--instrument", default=None, help="Optional instrument filter when column exists.")
    parser.add_argument("--max-files", type=int, default=None)
    parser.add_argument("--max-rows", type=int, default=None)
    parser.add_argument("--volatility-window", type=int, default=30)
    parser.add_argument("--future-horizon", type=int, default=15, help="Bars ahead for target computation.")
    parser.add_argument("--return-threshold", type=float, default=0.001, help="Return threshold for long/short labels.")
    parser.add_argument("--random-state", type=int, default=42)
    parser.add_argument("--n-estimators", type=int, default=400)
    parser.add_argument("--learning-rate", type=float, default=0.05)
    parser.add_argument("--max-depth", type=int, default=4)
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
    parser.add_argument(
        "--output-path",
        type=Path,
        default=Path("ajk_strategies/models/signal_aggregator_xgb.pkl"),
    )
    return parser.parse_args()


def load_hmm(model_path: Path) -> tuple:
    model, scaler, summary = joblib.load(model_path)
    mapping = getattr(model, "state_label_map", None)
    if mapping is None:
        mapping = summary.get("state_mapping", {}) if isinstance(summary, dict) else {}
    return model, scaler, mapping


def compute_regimes(feature_frame: pd.DataFrame, hmm_model, scaler, mapping: dict[int, int]) -> pd.Series:
    cols = getattr(hmm_model, "training_columns", list(feature_frame.columns))
    features = feature_frame[cols]
    scaled = scaler.transform(features.values)
    states = hmm_model.predict(scaled)
    regimes = [mapping.get(state, 5) for state in states]
    return pd.Series(regimes, index=feature_frame.index, name="regime")


def load_lstm(model_path: Path, meta_path: Path):
    model = keras.models.load_model(model_path, compile=False)
    meta = joblib.load(meta_path)
    required_keys = {"input_scaler", "target_scaler", "sequence_length"}
    if not required_keys.issubset(meta.keys()):
        missing = required_keys - set(meta.keys())
        raise ValueError(f"LSTM metadata missing keys: {missing}")
    return model, meta


def compute_lstm_forecasts(close: pd.Series, model, meta: dict) -> pd.Series:
    returns = close.pct_change().fillna(0.0)
    input_scaler: StandardScaler = meta["input_scaler"]
    target_scaler: StandardScaler = meta["target_scaler"]
    seq_len: int = meta["sequence_length"]

    scaled_returns = input_scaler.transform(returns.values.reshape(-1, 1)).flatten()
    forecasts = np.full_like(scaled_returns, np.nan, dtype=float)

    if len(scaled_returns) <= seq_len:
        return pd.Series(forecasts, index=close.index, name="lstm_forecast")

    windows = sliding_window_view(scaled_returns, seq_len)[:-1]
    inputs = windows.reshape(-1, seq_len, 1)
    preds_scaled = model.predict(inputs, batch_size=2048, verbose=0).flatten()
    preds = target_scaler.inverse_transform(preds_scaled.reshape(-1, 1)).flatten()
    forecasts[seq_len:] = preds

    return pd.Series(forecasts, index=close.index, name="lstm_forecast")


def compute_targets(close: pd.Series, horizon: int, threshold: float) -> pd.Series:
    future_returns = close.pct_change(periods=horizon).shift(-horizon)
    labels = np.zeros(len(close), dtype=float)
    labels[future_returns > threshold] = 1.0
    labels[future_returns < -threshold] = 2.0
    labels[future_returns.isna()] = np.nan
    if horizon > 0:
        labels[-horizon:] = np.nan
    return pd.Series(labels, index=close.index, name="label")


def main() -> None:
    args = parse_args()

    files = resolve_input_files(args.input_path.expanduser().resolve(), args.pattern, args.max_files)
    price_frame = load_price_frame(files, instrument=args.instrument)

    if args.max_rows is not None and len(price_frame) > args.max_rows:
        price_frame = price_frame.tail(args.max_rows)

    feature_frame = compute_regime_features(
        price_frame["close"],
        volatility_window=args.volatility_window,
    )
    feature_frame = feature_frame.sort_index()

    hmm_model, hmm_scaler, state_mapping = load_hmm(args.hmm_model_path.expanduser().resolve())
    regimes = compute_regimes(feature_frame, hmm_model, hmm_scaler, state_mapping)

    lstm_model, lstm_meta = load_lstm(
        args.lstm_model_path.expanduser().resolve(),
        args.lstm_meta_path.expanduser().resolve(),
    )
    lstm_forecasts = compute_lstm_forecasts(price_frame["close"], lstm_model, lstm_meta)

    dataset = feature_frame.join(regimes, how="inner").join(lstm_forecasts, how="inner")
    dataset = dataset.dropna()

    targets = compute_targets(price_frame["close"], args.future_horizon, args.return_threshold)
    dataset = dataset.join(targets, how="inner")
    dataset = dataset.dropna()

    if dataset.empty:
        raise ValueError("Dataset is empty after feature/target alignment. Check horizon and thresholds.")

    feature_columns = ["dsp_trend", "volatility", "lstm_forecast", "regime"]
    numeric_columns = ["dsp_trend", "volatility", "lstm_forecast"]

    scaler = StandardScaler()
    scaled_numeric = scaler.fit_transform(dataset[numeric_columns])
    X = np.column_stack([scaled_numeric, dataset["regime"].to_numpy().reshape(-1, 1)])
    y = dataset["label"].to_numpy(dtype=int)

    sample_weights = class_weight.compute_sample_weight(class_weight="balanced", y=y)

    model = XGBClassifier(
        n_estimators=args.n_estimators,
        learning_rate=args.learning_rate,
        max_depth=args.max_depth,
        subsample=0.8,
        colsample_bytree=0.8,
        objective="multi:softprob",
        eval_metric="mlogloss",
        num_class=3,
        random_state=args.random_state,
    )
    model.fit(X, y, sample_weight=sample_weights)

    class_counts = np.bincount(y, minlength=3)
    print(f"Class distribution (hold, long, short): {class_counts.tolist()}")

    artifact = {
        "model": model,
        "feature_columns": feature_columns,
        "numeric_columns": numeric_columns,
        "scaler": scaler,
        "future_horizon": args.future_horizon,
        "return_threshold": args.return_threshold,
    }

    output_path = args.output_path.expanduser().resolve()
    output_path.parent.mkdir(parents=True, exist_ok=True)
    joblib.dump(artifact, output_path)

    print(f"Saved XGBoost model to {output_path}")


if __name__ == "__main__":
    main()
