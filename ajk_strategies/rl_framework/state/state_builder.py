# -------------------------------------------------------------------------------------------------
#  State Builder for RL Agents
#  Constructs normalized state vectors from market data and portfolio state
# -------------------------------------------------------------------------------------------------

from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING

import numpy as np

if TYPE_CHECKING:
    from nautilus_trader.model.data import Bar
    from nautilus_trader.trading.portfolio import Portfolio
    from nautilus_trader.model.position import Position


@dataclass
class StateConfig:
    """Configuration for state construction."""
    lookback_bars: int = 10
    indicators: list[str] = field(default_factory=lambda: ["ema_20", "rsi_14", "atr_14"])
    include_portfolio_state: bool = True
    include_position_state: bool = True
    normalize_prices: bool = True
    clip_range: float = 5.0


class StateBuilder:
    """
    Build state vectors for RL agents from market and portfolio data.

    The state vector includes:
    - OHLCV features (normalized as returns)
    - Technical indicators
    - Portfolio state (cash ratio, position count, unrealized P&L)
    - Position-specific state (P&L ratio, holding time, MFE, MAE)
    """

    def __init__(self, config: StateConfig | None = None):
        """
        Initialize StateBuilder.

        Parameters
        ----------
        config : StateConfig, optional
            Configuration for state construction.
        """
        self.config = config or StateConfig()
        self._price_cache: dict[str, list[float]] = {}

    @property
    def state_dim(self) -> int:
        """Calculate the total state dimension."""
        ohlcv_dim = self.config.lookback_bars * 5  # OHLCV
        indicator_dim = len(self.config.indicators)
        portfolio_dim = 3 if self.config.include_portfolio_state else 0
        position_dim = 4 if self.config.include_position_state else 0
        return ohlcv_dim + indicator_dim + portfolio_dim + position_dim

    def build_state(
        self,
        bars: list[Bar],
        portfolio: Portfolio | None = None,
        position: Position | None = None,
        account_value: float = 100000.0,
    ) -> np.ndarray:
        """
        Build normalized state vector from market and portfolio data.

        Parameters
        ----------
        bars : list[Bar]
            Recent price bars (most recent last).
        portfolio : Portfolio, optional
            Current portfolio for portfolio state features.
        position : Position, optional
            Current position for position-specific features.
        account_value : float
            Total account value for normalization.

        Returns
        -------
        np.ndarray
            Normalized state vector of shape (state_dim,).
        """
        features = []

        # OHLCV features (normalized as returns)
        ohlcv = self._extract_ohlcv_features(bars)
        features.append(ohlcv)

        # Technical indicators
        indicators = self._calculate_indicators(bars)
        features.append(indicators)

        # Portfolio state
        if self.config.include_portfolio_state:
            portfolio_state = self._build_portfolio_state(portfolio, account_value)
            features.append(portfolio_state)

        # Position-specific state
        if self.config.include_position_state:
            position_state = self._build_position_state(position)
            features.append(position_state)

        # Concatenate and normalize
        state = np.concatenate(features)
        state = self._normalize_state(state)

        return state.astype(np.float32)

    def _extract_ohlcv_features(self, bars: list[Bar]) -> np.ndarray:
        """Extract OHLCV features from bars, normalized as returns."""
        if not bars or len(bars) < 2:
            return np.zeros(self.config.lookback_bars * 5)

        # Take last N bars
        bars_to_use = bars[-self.config.lookback_bars:]

        features = []
        for i, bar in enumerate(bars_to_use):
            if i == 0:
                # First bar: use 0 for returns
                features.extend([0.0, 0.0, 0.0, 0.0, 0.0])
            else:
                prev_bar = bars_to_use[i - 1]
                prev_close = float(prev_bar.close)

                if prev_close > 0:
                    open_ret = (float(bar.open) - prev_close) / prev_close
                    high_ret = (float(bar.high) - prev_close) / prev_close
                    low_ret = (float(bar.low) - prev_close) / prev_close
                    close_ret = (float(bar.close) - prev_close) / prev_close
                    # Volume normalized by average
                    vol_norm = float(bar.volume) / 1e6 if bar.volume else 0.0
                else:
                    open_ret = high_ret = low_ret = close_ret = vol_norm = 0.0

                features.extend([open_ret, high_ret, low_ret, close_ret, vol_norm])

        # Pad if not enough bars
        while len(features) < self.config.lookback_bars * 5:
            features.insert(0, 0.0)

        return np.array(features[:self.config.lookback_bars * 5])

    def _calculate_indicators(self, bars: list[Bar]) -> np.ndarray:
        """Calculate technical indicators from bars."""
        if not bars or len(bars) < 2:
            return np.zeros(len(self.config.indicators))

        closes = np.array([float(b.close) for b in bars])
        highs = np.array([float(b.high) for b in bars])
        lows = np.array([float(b.low) for b in bars])

        indicators = []

        for indicator_name in self.config.indicators:
            if indicator_name.startswith("ema_"):
                period = int(indicator_name.split("_")[1])
                value = self._calculate_ema(closes, period)
                # Normalize relative to current price
                if closes[-1] > 0:
                    value = (value - closes[-1]) / closes[-1]
                indicators.append(value)

            elif indicator_name.startswith("rsi_"):
                period = int(indicator_name.split("_")[1])
                value = self._calculate_rsi(closes, period)
                # Normalize to [-1, 1] range
                indicators.append((value - 50) / 50)

            elif indicator_name.startswith("atr_"):
                period = int(indicator_name.split("_")[1])
                value = self._calculate_atr(highs, lows, closes, period)
                # Normalize by price
                if closes[-1] > 0:
                    value = value / closes[-1]
                indicators.append(value)

        return np.array(indicators)

    def _build_portfolio_state(
        self,
        portfolio: Portfolio | None,
        account_value: float,
    ) -> np.ndarray:
        """Build portfolio state features."""
        if portfolio is None:
            return np.zeros(3)

        try:
            # Cash ratio
            cash = float(portfolio.balance())
            cash_ratio = cash / account_value if account_value > 0 else 0.0

            # Open positions count (normalized)
            open_positions = len([p for p in portfolio.positions_open()])
            position_count_norm = open_positions / 10.0  # Normalize by max positions

            # Unrealized P&L ratio
            unrealized_pnl = float(portfolio.unrealized_pnl())
            pnl_ratio = unrealized_pnl / account_value if account_value > 0 else 0.0

            return np.array([cash_ratio, position_count_norm, pnl_ratio])
        except Exception:
            return np.zeros(3)

    def _build_position_state(self, position: Position | None) -> np.ndarray:
        """Build position-specific state features."""
        if position is None:
            return np.zeros(4)

        try:
            # P&L ratio
            entry_value = float(position.quantity) * float(position.avg_px_open)
            pnl = float(position.unrealized_pnl())
            pnl_ratio = pnl / entry_value if entry_value > 0 else 0.0

            # Holding time (normalized by 100 bars)
            # This would need actual tracking - placeholder
            holding_time_norm = 0.0

            # Max favorable excursion (placeholder - needs tracking)
            mfe = 0.0

            # Max adverse excursion (placeholder - needs tracking)
            mae = 0.0

            return np.array([pnl_ratio, holding_time_norm, mfe, mae])
        except Exception:
            return np.zeros(4)

    def _normalize_state(self, state: np.ndarray) -> np.ndarray:
        """Normalize state values and handle edge cases."""
        # Replace NaN and inf
        state = np.nan_to_num(state, nan=0.0, posinf=self.config.clip_range, neginf=-self.config.clip_range)

        # Clip to range
        state = np.clip(state, -self.config.clip_range, self.config.clip_range)

        return state

    @staticmethod
    def _calculate_ema(data: np.ndarray, period: int) -> float:
        """Calculate Exponential Moving Average."""
        if len(data) < period:
            return float(data[-1]) if len(data) > 0 else 0.0

        alpha = 2.0 / (period + 1)
        ema = data[0]
        for price in data[1:]:
            ema = alpha * price + (1 - alpha) * ema
        return float(ema)

    @staticmethod
    def _calculate_rsi(data: np.ndarray, period: int) -> float:
        """Calculate Relative Strength Index."""
        if len(data) < period + 1:
            return 50.0  # Neutral

        deltas = np.diff(data[-period - 1:])
        gains = np.where(deltas > 0, deltas, 0)
        losses = np.where(deltas < 0, -deltas, 0)

        avg_gain = np.mean(gains)
        avg_loss = np.mean(losses)

        if avg_loss == 0:
            return 100.0

        rs = avg_gain / avg_loss
        rsi = 100.0 - (100.0 / (1.0 + rs))
        return float(rsi)

    @staticmethod
    def _calculate_atr(
        highs: np.ndarray,
        lows: np.ndarray,
        closes: np.ndarray,
        period: int,
    ) -> float:
        """Calculate Average True Range."""
        if len(closes) < period + 1:
            return 0.0

        true_ranges = []
        for i in range(1, min(len(closes), period + 1)):
            high_low = highs[i] - lows[i]
            high_prev_close = abs(highs[i] - closes[i - 1])
            low_prev_close = abs(lows[i] - closes[i - 1])
            tr = max(high_low, high_prev_close, low_prev_close)
            true_ranges.append(tr)

        return float(np.mean(true_ranges)) if true_ranges else 0.0
