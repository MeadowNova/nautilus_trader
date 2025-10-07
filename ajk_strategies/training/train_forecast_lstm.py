from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import Tuple

if __package__ is None:  # pragma: no cover
    sys.path.append(str(Path(__file__).resolve().parents[2]))

import joblib
import numpy as np
import pandas as pd

try:
    from sklearn.preprocessing import StandardScaler
except ImportError as exc:  # pragma: no cover
    raise SystemExit("Install scikit-learn to run this training script.") from exc

try:
    import tensorflow as tf
    from tensorflow import keras
except ImportError as exc:  # pragma: no cover
    raise SystemExit("Install tensorflow to run this training script.") from exc

from ajk_strategies.training.features import load_price_frame, resolve_input_files


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Train LSTM price forecast model.")
    parser.add_argument("--input-path", type=Path, required=True, help="Path to parquet file or directory.")
    parser.add_argument("--pattern", default="*.parquet", help="Filename glob when input is a directory.")
    parser.add_argument("--instrument", default=None, help="Optional instrument filter when column exists.")
    parser.add_argument("--max-files", type=int, default=None)
    parser.add_argument("--max-rows", type=int, default=None)
    parser.add_argument("--sequence-length", type=int, default=50)
    parser.add_argument("--epochs", type=int, default=10)
    parser.add_argument("--batch-size", type=int, default=128)
    parser.add_argument("--learning-rate", type=float, default=1e-3)
    parser.add_argument("--train-split", type=float, default=0.8)
    parser.add_argument("--random-state", type=int, default=42)
    parser.add_argument("--output-model", type=Path, default=Path("ajk_strategies/models/price_forecast_lstm.h5"))
    parser.add_argument("--output-meta", type=Path, default=Path("ajk_strategies/models/price_forecast_lstm_meta.pkl"))
    return parser.parse_args()


def set_random_seeds(seed: int) -> None:
    np.random.seed(seed)
    tf.random.set_seed(seed)


def build_sequences(returns: np.ndarray, sequence_length: int) -> Tuple[np.ndarray, np.ndarray]:
    if len(returns) <= sequence_length:
        raise ValueError("Not enough data to form LSTM sequences.")
    x_list = []
    y_list = []
    for idx in range(sequence_length, len(returns)):
        x_list.append(returns[idx - sequence_length : idx])
        y_list.append(returns[idx])
    X = np.asarray(x_list, dtype=np.float32)
    y = np.asarray(y_list, dtype=np.float32)
    return X[..., np.newaxis], y


def main() -> None:
    args = parse_args()
    set_random_seeds(args.random_state)

    files = resolve_input_files(args.input_path.expanduser().resolve(), args.pattern, args.max_files)
    price_frame = load_price_frame(files, instrument=args.instrument)

    if args.max_rows is not None and len(price_frame) > args.max_rows:
        price_frame = price_frame.tail(args.max_rows)

    close_series = price_frame["close"].astype(float)
    returns = close_series.pct_change().fillna(0.0)

    input_scaler = StandardScaler()
    scaled_returns = input_scaler.fit_transform(returns.values.reshape(-1, 1)).flatten()

    X, y = build_sequences(scaled_returns, args.sequence_length)

    target_scaler = StandardScaler()
    y_scaled = target_scaler.fit_transform(y.reshape(-1, 1)).flatten()

    split_idx = int(len(X) * args.train_split)
    if split_idx == 0 or split_idx == len(X):
        raise ValueError("Train split produced empty train/test sets. Adjust --train-split or provide more data.")

    X_train, X_val = X[:split_idx], X[split_idx:]
    y_train, y_val = y_scaled[:split_idx], y_scaled[split_idx:]

    model = keras.Sequential(
        [
            keras.layers.Input(shape=(args.sequence_length, 1)),
            keras.layers.LSTM(64, return_sequences=False),
            keras.layers.Dropout(0.2),
            keras.layers.Dense(32, activation="relu"),
            keras.layers.Dense(1),
        ]
    )
    model.compile(optimizer=keras.optimizers.Adam(learning_rate=args.learning_rate), loss="mse")

    callbacks = [
        keras.callbacks.EarlyStopping(monitor="val_loss", patience=3, restore_best_weights=True),
    ]

    history = model.fit(
        X_train,
        y_train,
        validation_data=(X_val, y_val),
        epochs=args.epochs,
        batch_size=args.batch_size,
        verbose=2,
        callbacks=callbacks,
    )

    val_loss = history.history.get("val_loss", [np.nan])[-1]
    print(f"Validation MSE: {val_loss:.6f}")

    output_model = args.output_model.expanduser().resolve()
    output_model.parent.mkdir(parents=True, exist_ok=True)
    model.save(output_model)

    meta = {
        "input_scaler": input_scaler,
        "target_scaler": target_scaler,
        "sequence_length": args.sequence_length,
        "train_split": args.train_split,
    }
    output_meta = args.output_meta.expanduser().resolve()
    joblib.dump(meta, output_meta)

    print(f"Saved LSTM model to {output_model}")
    print(f"Saved LSTM metadata to {output_meta}")


if __name__ == "__main__":
    main()
