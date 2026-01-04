from __future__ import annotations

from collections import deque
from pathlib import Path
from typing import Iterable, List, Tuple

import numpy as np
import pandas as pd


DEFAULT_IIR_B_COEFFS: Tuple[float, ...] = (0.0007, 0.0021, 0.0021, 0.0007)
DEFAULT_IIR_A_COEFFS: Tuple[float, ...] = (1.0, -2.4274, 2.0112, -0.5581)


class IIRFilter:
    def __init__(self, b_coeffs: Iterable[float], a_coeffs: Iterable[float]):
        self.b = tuple(b_coeffs)
        self.a = tuple(a_coeffs)
        self.x_hist: deque[float] = deque([0.0] * len(self.b), maxlen=len(self.b))
        self.y_hist: deque[float] = deque([0.0] * (len(self.a) - 1), maxlen=len(self.a) - 1)

    def apply(self, x_n: float) -> float:
        self.x_hist.appendleft(x_n)
        y_n = sum(b_i * x_i for b_i, x_i in zip(self.b, self.x_hist))
        y_n -= sum(a_i * y_i for a_i, y_i in zip(self.a[1:], self.y_hist))
        self.y_hist.appendleft(y_n)
        return y_n


def compute_regime_features(
    close: pd.Series,
    *,
    b_coeffs: Tuple[float, ...] = DEFAULT_IIR_B_COEFFS,
    a_coeffs: Tuple[float, ...] = DEFAULT_IIR_A_COEFFS,
    volatility_window: int = 30,
) -> pd.DataFrame:
    prices = close.astype(float).to_numpy()
    filter_ = IIRFilter(b_coeffs, a_coeffs)
    dsp_values = np.zeros_like(prices, dtype=float)

    for idx, price in enumerate(prices):
        filtered = filter_.apply(price)
        prev = filter_.y_hist[1] if len(filter_.y_hist) > 1 else 0.0
        if filtered != 0.0 and prev != 0.0:
            dsp_values[idx] = (filtered - prev) / filtered
        else:
            dsp_values[idx] = 0.0

    returns = pd.Series(prices, index=close.index).pct_change().fillna(0.0)
    volatility = returns.rolling(window=volatility_window, min_periods=volatility_window).std()

    features = pd.DataFrame(
        {
            "volatility": volatility.values,
            "dsp_trend": dsp_values,
        },
        index=close.index,
    )

    return features.dropna()


def resolve_input_files(input_path: Path, pattern: str, max_files: int | None) -> List[Path]:
    if input_path.is_file():
        return [input_path]
    files = sorted(input_path.rglob(pattern))
    if max_files is not None:
        files = files[:max_files]
    if not files:
        raise FileNotFoundError(f"No parquet files found in {input_path} matching {pattern}.")
    return files


def load_price_frame(files: Iterable[Path], instrument: str | None = None) -> pd.DataFrame:
    frames: List[pd.DataFrame] = []
    for file in files:
        columns = ["timestamp", "close"]
        if instrument:
            columns.append("instrument")
        try:
            df = pd.read_parquet(file, columns=columns)
        except (ValueError, KeyError):
            df = pd.read_parquet(file)

        if instrument:
            for col in ("instrument", "symbol", "instrument_id"):
                if col in df.columns:
                    df = df[df[col] == instrument]
                    break

        if "timestamp" not in df.columns:
            if "ts_event" in df.columns:
                df = df.rename(columns={"ts_event": "timestamp"})
            elif "time" in df.columns:
                df = df.rename(columns={"time": "timestamp"})

        if df.empty or "close" not in df.columns or "timestamp" not in df.columns:
            continue

        frame = df[["timestamp", "close"]].copy()
        frame["timestamp"] = pd.to_datetime(frame["timestamp"])
        frame["close"] = frame["close"].astype(float)
        frames.append(frame)

    if not frames:
        raise ValueError("No price data available for training from provided files.")

    combined = pd.concat(frames, ignore_index=True)
    combined = combined.sort_values("timestamp")
    combined = combined.drop_duplicates(subset="timestamp", keep="last")
    combined = combined.set_index("timestamp")
    return combined
