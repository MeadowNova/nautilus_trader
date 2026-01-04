from __future__ import annotations

import argparse
import sys
import hashlib
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict

if __package__ is None:  # pragma: no cover
    sys.path.append(str(Path(__file__).resolve().parents[2]))

import joblib
import numpy as np
import pandas as pd

try:
    from hmmlearn.hmm import GaussianHMM
except ImportError as exc:  # pragma: no cover
    raise SystemExit("Install hmmlearn to run this training script.") from exc

try:
    from sklearn.preprocessing import StandardScaler
except ImportError as exc:  # pragma: no cover
    raise SystemExit("Install scikit-learn to run this training script.") from exc

from ajk_strategies.market_regime import MarketRegime
from ajk_strategies.training.features import (
    compute_regime_features,
    load_price_frame,
    resolve_input_files,
)
from ajk_strategies.training import persist_training_run


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Train HMM market regime model.")
    parser.add_argument("--input-path", type=Path, required=True, help="Path to parquet file or directory.")
    parser.add_argument("--pattern", default="*.parquet", help="Filename glob when input is a directory.")
    parser.add_argument("--instrument", default=None, help="Optional instrument filter when column exists.")
    parser.add_argument("--output-path", type=Path, default=Path("ajk_strategies/models/market_regime_hmm.pkl"))
    parser.add_argument("--volatility-window", type=int, default=30)
    parser.add_argument("--n-components", type=int, default=5)
    parser.add_argument("--max-files", type=int, default=None)
    parser.add_argument("--max-rows", type=int, default=None)
    parser.add_argument("--random-state", type=int, default=42)
    return parser.parse_args()


def trim_frame(frame: pd.DataFrame, max_rows: int | None) -> pd.DataFrame:
    if max_rows is None or len(frame) <= max_rows:
        return frame
    step = len(frame) // max_rows
    return frame.iloc[:: max(step, 1)].head(max_rows)


def assign_state_mapping(model: GaussianHMM, scaler: StandardScaler) -> Dict[int, int]:
    means = scaler.inverse_transform(model.means_)
    vol = means[:, 0]
    trend = means[:, 1]
    vol_threshold = float(np.median(vol))
    trend_threshold = float(np.median(trend))

    mapping: Dict[int, int] = {}
    for idx, (v, t) in enumerate(zip(vol, trend, strict=False)):
        if t >= trend_threshold and v < vol_threshold:
            label = MarketRegime.LOW_VOL_BULL.value
        elif t >= trend_threshold and v >= vol_threshold:
            label = MarketRegime.HIGH_VOL_BULL.value
        elif t < trend_threshold and v < vol_threshold:
            label = MarketRegime.LOW_VOL_BEAR.value
        elif t < trend_threshold and v >= vol_threshold:
            label = MarketRegime.HIGH_VOL_BEAR.value
        else:
            label = MarketRegime.RANGING.value
        mapping[idx] = label

    if MarketRegime.RANGING.value not in mapping.values():
        neutral_idx = int(np.argmin(np.abs(trend)))
        mapping[neutral_idx] = MarketRegime.RANGING.value

    return mapping


def main() -> None:
    args = parse_args()
    started_at = datetime.now(timezone.utc)

    files = resolve_input_files(args.input_path.expanduser().resolve(), args.pattern, args.max_files)
    price_frame = load_price_frame(files, instrument=args.instrument)
    feature_frame = compute_regime_features(
        price_frame["close"],
        volatility_window=args.volatility_window,
    )
    if feature_frame.empty:
        raise ValueError("No usable feature rows were produced from provided files.")
    feature_frame = feature_frame.sort_index()
    feature_frame = trim_frame(feature_frame, args.max_rows)

    scaler = StandardScaler()
    scaled = scaler.fit_transform(feature_frame.values)

    model = GaussianHMM(
        n_components=args.n_components,
        covariance_type="full",
        n_iter=512,
        random_state=args.random_state,
        verbose=False,
        min_covar=1e-4,
    )
    model.fit(scaled)

    mapping = assign_state_mapping(model, scaler)
    model.state_label_map = mapping  # type: ignore[attr-defined]
    model.training_columns = list(feature_frame.columns)  # type: ignore[attr-defined]

    decoded = model.predict(scaled)
    counts = np.bincount(decoded, minlength=model.n_components)
    summary = {
        "rows_used": int(feature_frame.shape[0]),
        "state_counts": counts.tolist(),
        "state_mapping": mapping,
    }

    output_path = args.output_path.expanduser().resolve()
    output_path.parent.mkdir(parents=True, exist_ok=True)
    joblib.dump((model, scaler, summary), output_path)

    print(f"Saved HMM model to {output_path}")
    print(summary)

    dataset_start = feature_frame.index.min().to_pydatetime() if not feature_frame.empty else None
    dataset_end = feature_frame.index.max().to_pydatetime() if not feature_frame.empty else None
    feature_hash = hashlib.sha256(
        np.ascontiguousarray(feature_frame.to_numpy(dtype=float)).tobytes()
    ).hexdigest()

    hyperparameters = {
        "volatility_window": args.volatility_window,
        "n_components": args.n_components,
        "max_rows": args.max_rows,
        "random_state": args.random_state,
    }
    metrics = {
        "rows_used": summary["rows_used"],
        "state_counts": summary["state_counts"],
    }

    completed_at = datetime.now(timezone.utc)
    model_version = started_at.strftime("%Y%m%d%H%M%S")

    run_id = persist_training_run(
        strategy_id="ai_adaptive_strategy",
        model_name="market_regime_hmm",
        model_version=model_version,
        dataset_source=str(args.input_path),
        dataset_files=files,
        dataset_start=dataset_start,
        dataset_end=dataset_end,
        hyperparameters=hyperparameters,
        metrics=metrics,
        feature_hash=feature_hash,
        completed_at=completed_at,
        artifacts=[("hmm_model", output_path)],
    )
    if run_id:
        print(f"Persisted HMM training run with id {run_id}")


if __name__ == "__main__":
    main()
