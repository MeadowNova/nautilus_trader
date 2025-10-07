#!/usr/bin/env python3
"""
AI-Adaptive Strategy - Main Strategy Class

This file contains the main strategy implementation that orchestrates
all the advanced components.
"""

from collections import deque
from decimal import Decimal
from typing import Optional
import numpy as np
from pathlib import Path

import joblib
from sklearn.preprocessing import StandardScaler
from xgboost import XGBClassifier
from tensorflow import keras

from nautilus_trader.model.data import Bar
from nautilus_trader.model.enums import OrderSide
from nautilus_trader.model.identifiers import InstrumentId, Venue as VenueId
from nautilus_trader.model.objects import Quantity
from nautilus_trader.trading.strategy import Strategy
from nautilus_trader.indicators import ExponentialMovingAverage
from nautilus_trader.indicators import AverageTrueRange
from nautilus_trader.indicators import RelativeStrengthIndex
from nautilus_trader.model.data import BarType

from ajk_strategies.market_regime import MarketRegime as HMMMarketRegime
from ajk_strategies.training.features import (
    DEFAULT_IIR_A_COEFFS,
    DEFAULT_IIR_B_COEFFS,
    IIRFilter,
)

from ai_adaptive_strategy import (
    AIAdaptiveStrategyConfig,
    MultiLayerOptimizer,
    AdvancedPatternDetector,
    MarketRegimeDetector,
    EnhancedSentimentAnalyzer,
    AdvancedRiskManager,
    MarketRegime,
    SignalStrength,
    TradingSignal,
)


class AIAdaptiveStrategy(Strategy):
    """
    AI-Adaptive Algorithmic Trading Strategy
    
    This strategy combines multiple advanced algorithms:
    - Machine Learning optimization
    - Pattern recognition
    - Market regime detection
    - Sentiment analysis
    - Advanced risk management
    - Monte Carlo simulation
    
    The strategy continuously adapts its parameters based on market conditions
    and performance metrics.
    """
    
    def __init__(self, config: AIAdaptiveStrategyConfig):
        super().__init__(config)
        
        # Configuration
        self.instrument_id = InstrumentId.from_str(config.instrument_id)
        self.instrument: Optional[Instrument] = None # Will be loaded in on_start
        
        # Indicators (initialized in on_start)
        self.fast_ema: Optional[ExponentialMovingAverage] = None
        self.slow_ema: Optional[ExponentialMovingAverage] = None
        self.trend_ema: Optional[ExponentialMovingAverage] = None
        self.rsi: Optional[RelativeStrengthIndex] = None
        self.atr: Optional[AverageTrueRange] = None
        
        # Advanced Components
        self.ml_optimizer = MultiLayerOptimizer(learning_rate=config.learning_rate)
        self.pattern_detector = AdvancedPatternDetector(lookback=50)
        self.regime_detector = MarketRegimeDetector(lookback=config.regime_lookback)
        self.sentiment_analyzer = EnhancedSentimentAnalyzer()
        self.risk_manager = AdvancedRiskManager(config)
        
        # Trading State
        self.position_entry_price: Optional[float] = None
        self.position_entry_time: Optional[int] = None
        self.position_stop_loss: Optional[float] = None
        self.position_take_profit: Optional[float] = None
        self.trailing_stop_price: Optional[float] = None
        
        # Performance Tracking
        self.trades_won = 0
        self.trades_lost = 0
        self.total_profit = 0.0
        self.trade_pnls = []
        self.bar_count = 0
        self.last_optimization_bar = 0
        self.last_regime_update_bar = 0
        
        # Current Parameters (adaptive)
        self.current_fast_period = config.fast_ema_period
        self.current_slow_period = config.slow_ema_period
        
        # Signal tracking for ML
        self.last_signal_features = None

        # External model artefacts & feature buffers
        self.hmm_model = None
        self.hmm_scaler: Optional[StandardScaler] = None
        self.hmm_state_mapping = {}
        self.hmm_feature_history: deque[list[float]] = deque(maxlen=500)
        self.dsp_filter = IIRFilter(DEFAULT_IIR_B_COEFFS, DEFAULT_IIR_A_COEFFS)
        self.return_history: deque[float] = deque(maxlen=2000)
        self.scaled_return_history: deque[float] = deque(maxlen=5000)
        self.previous_close: Optional[float] = None
        self.latest_volatility: Optional[float] = None
        self.latest_dsp_trend: Optional[float] = None
        self.latest_lstm_forecast: Optional[float] = None
        self.latest_regime_numeric: float = float(HMMMarketRegime.UNKNOWN.value)
        self.lstm_model = None
        self.lstm_input_scaler: Optional[StandardScaler] = None
        self.lstm_target_scaler: Optional[StandardScaler] = None
        self.lstm_sequence_length: int = 0
        self.xgb_model: Optional[XGBClassifier] = None
        self.xgb_scaler: Optional[StandardScaler] = None
        self.xgb_numeric_columns = ("dsp_trend", "volatility", "lstm_forecast")
        self.regime_vol_window = 30
        self.latest_xgb_probs: Optional[np.ndarray] = None
        
    def on_start(self):
        """Initialize strategy components"""
        # Load the instrument
        self.instrument = self.cache.instrument(self.instrument_id)
        if self.instrument is None:
            self.log.error(f"Could not find instrument for {self.instrument_id}")
            self.stop()
            return

        # Initialize indicators
        self.fast_ema = ExponentialMovingAverage(self.current_fast_period)
        self.slow_ema = ExponentialMovingAverage(self.current_slow_period)
        self.trend_ema = ExponentialMovingAverage(self.config.trend_ema_period)
        self.rsi = RelativeStrengthIndex(self.config.rsi_period)
        self.atr = AverageTrueRange(self.config.atr_period)
        
        # Subscribe to data
        bar_type = BarType.from_str(self.config.bar_type) if isinstance(self.config.bar_type, str) else self.config.bar_type
        self.subscribe_bars(bar_type)

        self._load_models()
        
        self.log.info(
            f"🚀 AI-Adaptive Strategy Started\n"
            f"   EMA: {self.current_fast_period}/{self.current_slow_period}/{self.config.trend_ema_period}\n"
            f"   RSI: {self.config.rsi_period} | ATR: {self.config.atr_period}\n"
            f"   ML Optimization: {self.config.enable_ml_optimization}\n"
            f"   Sentiment: {self.config.use_sentiment}\n"
            f"   Risk Management: Multi-layer with circuit breakers"
        )
    
    def on_bar(self, bar: Bar):
        """Process new bar data"""
        self.bar_count += 1
        
        # Update all indicators and detectors
        self._update_indicators(bar)
        
        # Wait for indicators to warm up
        if not self._indicators_ready():
            return
        
        # Check circuit breakers
        if self.risk_manager.is_paused:
            self._check_resume_conditions()
            return
        
        # Update market regime periodically
        if self.bar_count - self.last_regime_update_bar >= self.config.regime_update_interval:
            self._update_market_regime()
            self.last_regime_update_bar = self.bar_count
        
        # Get current sentiment
        sentiment = self._get_current_sentiment()
        
        # Check for exits first (if in position)
        if not self.portfolio.is_flat(self.instrument_id):
            self._check_exit_conditions(bar, sentiment)
        else:
            # Check for entries
            self._check_entry_conditions(bar, sentiment)
        
        # Periodic ML optimization
        if self.config.enable_ml_optimization and \
           self.bar_count - self.last_optimization_bar >= self.config.optimization_interval:
            self._optimize_parameters()
            self.last_optimization_bar = self.bar_count
        
        # Update risk metrics
        self._update_risk_metrics(bar)
    
    def _load_models(self) -> None:
        """Load external ML artefacts for regime detection and signal scoring."""
        # HMM Regime Model
        try:
            hmm_path = Path(self.config.hmm_model_path).expanduser()
            if not hmm_path.is_absolute():
                hmm_path = Path.cwd() / hmm_path
            if hmm_path.exists():
                hmm_bundle = joblib.load(hmm_path)
                if isinstance(hmm_bundle, tuple) and len(hmm_bundle) >= 3:
                    self.hmm_model = hmm_bundle[0]
                    self.hmm_scaler = hmm_bundle[1]
                    summary = hmm_bundle[2]
                    if isinstance(summary, dict):
                        self.hmm_state_mapping = summary.get("state_mapping", {})
                    self.log.info(f"Loaded HMM regime model from {hmm_path}")
                else:
                    self.log.warning(f"HMM bundle at {hmm_path} missing expected components; fallback to heuristic regimes.")
            else:
                self.log.warning(f"HMM model not found at {hmm_path}; using heuristic regimes.")
        except Exception as exc:  # pragma: no cover - defensive
            self.log.exception(f"Failed to load HMM model: {exc}")
            self.hmm_model = None

        # LSTM Forecast Model
        try:
            lstm_path = Path(self.config.lstm_model_path).expanduser()
            if not lstm_path.is_absolute():
                lstm_path = Path.cwd() / lstm_path
            meta_path = Path(self.config.lstm_meta_path).expanduser()
            if not meta_path.is_absolute():
                meta_path = Path.cwd() / meta_path
            if lstm_path.exists() and meta_path.exists():
                self.lstm_model = keras.models.load_model(lstm_path, compile=False)
                meta = joblib.load(meta_path)
                self.lstm_input_scaler = meta.get("input_scaler")
                self.lstm_target_scaler = meta.get("target_scaler")
                self.lstm_sequence_length = int(meta.get("sequence_length", 0))
                self.log.info(f"Loaded LSTM forecast model from {lstm_path}")
            else:
                self.log.warning("LSTM artefacts missing; forecasts disabled.")
        except Exception as exc:  # pragma: no cover - defensive
            self.log.exception(f"Failed to load LSTM model: {exc}")
            self.lstm_model = None

        # XGBoost Signal Aggregator
        try:
            xgb_path = Path(self.config.xgb_model_path).expanduser()
            if not xgb_path.is_absolute():
                xgb_path = Path.cwd() / xgb_path
            if xgb_path.exists():
                artifact = joblib.load(xgb_path)
                if isinstance(artifact, dict) and "model" in artifact and "scaler" in artifact:
                    self.xgb_model = artifact["model"]
                    self.xgb_scaler = artifact["scaler"]
                    self.log.info(f"Loaded XGBoost signal model from {xgb_path}")
                else:
                    self.log.warning(f"Unexpected XGB artifact format at {xgb_path}; using logistic fallback.")
            else:
                self.log.warning("XGBoost model not found; using logistic optimizer fallback.")
        except Exception as exc:  # pragma: no cover - defensive
            self.log.exception(f"Failed to load XGB model: {exc}")
            self.xgb_model = None

    def _update_indicators(self, bar: Bar):
        """Update all indicators with new bar data"""
        price = bar.close.as_double()
        high = bar.high.as_double()
        low = bar.low.as_double()
        
        # Update technical indicators
        self.fast_ema.update_raw(price)
        self.slow_ema.update_raw(price)
        self.trend_ema.update_raw(price)
        self.rsi.update_raw(price)
        self.atr.update_raw(high, low, price)
        
        # Update pattern detector
        volume = float(bar.volume.as_double()) if hasattr(bar, 'volume') else 0.0
        self.pattern_detector.update(price, volume)
        
        # Update regime detector
        self.regime_detector.update(price, volume)

        self._update_ml_internals(price)
    
    def _indicators_ready(self) -> bool:
        """Check if all indicators are initialized"""
        return (
            self.fast_ema.initialized and
            self.slow_ema.initialized and
            self.trend_ema.initialized and
            self.rsi.initialized and
            self.atr.initialized
        )

    def _update_ml_internals(self, price: float) -> None:
        """Update streaming features used by external ML models."""
        if self.dsp_filter is not None:
            filtered_price = self.dsp_filter.apply(price)
            prev_filtered = self.dsp_filter.y_hist[1] if len(self.dsp_filter.y_hist) > 1 else filtered_price
            dsp_trend = 0.0
            if filtered_price not in (0.0, None):
                dsp_trend = (filtered_price - prev_filtered) / filtered_price if prev_filtered is not None else 0.0
            self.latest_dsp_trend = float(np.clip(dsp_trend, -1.0, 1.0))

        if self.previous_close is not None and self.previous_close != 0.0:
            ret = (price - self.previous_close) / self.previous_close
            self.return_history.append(ret)
            if self.lstm_input_scaler is not None:
                scaled_ret = self.lstm_input_scaler.transform(np.array([[ret]])).flatten()[0]
                self.scaled_return_history.append(scaled_ret)
        self.previous_close = price

        if len(self.return_history) >= self.regime_vol_window:
            recent_returns = list(self.return_history)[-self.regime_vol_window:]
            self.latest_volatility = float(np.std(recent_returns))

        if (
            self.lstm_model is not None
            and self.lstm_input_scaler is not None
            and self.lstm_target_scaler is not None
            and self.lstm_sequence_length > 0
            and len(self.scaled_return_history) >= self.lstm_sequence_length
        ):
            window = np.array(list(self.scaled_return_history)[-self.lstm_sequence_length:])
            lstm_input = window.reshape(1, self.lstm_sequence_length, 1)
            pred_scaled = self.lstm_model.predict(lstm_input, verbose=0)[0][0]
            forecast = self.lstm_target_scaler.inverse_transform(np.array([[pred_scaled]])).flatten()[0]
            self.latest_lstm_forecast = float(forecast)

        if self.latest_volatility is not None and self.latest_dsp_trend is not None:
            self.hmm_feature_history.append([self.latest_volatility, self.latest_dsp_trend])
    
    def _update_market_regime(self):
        """Update current market regime"""
        if (
            self.hmm_model is not None
            and self.hmm_scaler is not None
            and len(self.hmm_feature_history) >= max(self.hmm_model.n_components, 10)
        ):
            features_array = np.array(self.hmm_feature_history)
            scaled = self.hmm_scaler.transform(features_array)
            states = self.hmm_model.predict(scaled)
            state = int(states[-1])
            hmm_label = self.hmm_state_mapping.get(state, HMMMarketRegime.UNKNOWN.value)
            self.current_regime = self._map_hmm_to_strategy(hmm_label)
            self.latest_regime_numeric = float(hmm_label)
            try:
                probs = self.hmm_model.predict_proba(scaled)[-1]
                self.regime_confidence = float(np.max(probs))
            except Exception:  # pragma: no cover - hmmlearn optional
                self.regime_confidence = 0.6

            self.log.info(
                f"📊 Market Regime (HMM): {self.current_regime.value.upper()} "
                f"(State {hmm_label}, Confidence: {self.regime_confidence:.2%})"
            )
            return

        regime = self.regime_detector.detect_regime()
        confidence = self.regime_detector.regime_confidence
        self.current_regime = regime
        self.regime_confidence = confidence
        self.latest_regime_numeric = self._strategy_regime_to_numeric(regime)
        
        self.log.info(
            f"📊 Market Regime: {regime.value.upper()} "
            f"(Confidence: {confidence:.2%})"
        )
    
    def _map_hmm_to_strategy(self, hmm_label: int) -> MarketRegime:
        try:
            hmm_regime = HMMMarketRegime(hmm_label)
        except ValueError:
            return MarketRegime.UNKNOWN

        mapping = {
            HMMMarketRegime.LOW_VOL_BULL: MarketRegime.TRENDING_UP,
            HMMMarketRegime.HIGH_VOL_BULL: MarketRegime.BREAKOUT,
            HMMMarketRegime.LOW_VOL_BEAR: MarketRegime.TRENDING_DOWN,
            HMMMarketRegime.HIGH_VOL_BEAR: MarketRegime.VOLATILE,
            HMMMarketRegime.RANGING: MarketRegime.RANGING,
            HMMMarketRegime.UNKNOWN: MarketRegime.UNKNOWN,
        }
        return mapping.get(hmm_regime, MarketRegime.UNKNOWN)

    def _strategy_regime_to_numeric(self, regime: MarketRegime) -> float:
        reverse_mapping = {
            MarketRegime.TRENDING_UP: float(HMMMarketRegime.LOW_VOL_BULL.value),
            MarketRegime.BREAKOUT: float(HMMMarketRegime.HIGH_VOL_BULL.value),
            MarketRegime.TRENDING_DOWN: float(HMMMarketRegime.LOW_VOL_BEAR.value),
            MarketRegime.VOLATILE: float(HMMMarketRegime.HIGH_VOL_BEAR.value),
            MarketRegime.RANGING: float(HMMMarketRegime.RANGING.value),
        }
        return reverse_mapping.get(regime, float(HMMMarketRegime.UNKNOWN.value))

    def _get_xgb_features(self) -> Optional[np.ndarray]:
        if self.latest_dsp_trend is None or self.latest_volatility is None:
            return None
        regime_value = self.latest_regime_numeric
        lstm_forecast = self.latest_lstm_forecast if self.latest_lstm_forecast is not None else 0.0
        return np.array([
            float(self.latest_dsp_trend),
            float(self.latest_volatility),
            float(lstm_forecast),
            float(regime_value),
        ], dtype=float)
    
    def _get_current_sentiment(self) -> float:
        """Get current market sentiment"""
        if not self.config.use_sentiment:
            return 0.0
        
        # Simulate sentiment (in production, this would call Reddit API)
        # For now, use a combination of RSI and recent price action
        rsi_value = self.rsi.value
        
        # RSI-based sentiment
        if rsi_value > 70:
            sentiment = 0.5  # Overbought = moderately bullish
        elif rsi_value < 30:
            sentiment = -0.5  # Oversold = moderately bearish
        else:
            # Neutral zone
            sentiment = (rsi_value - 50) / 50 * 0.3
        
        # Add some noise to simulate real sentiment
        sentiment += np.random.normal(0, 0.1)
        sentiment = np.clip(sentiment, -1.0, 1.0)
        
        self.sentiment_analyzer.update_sentiment(sentiment, confidence=0.7)
        
        return self.sentiment_analyzer.get_current_sentiment()
    
    def _check_entry_conditions(self, bar: Bar, sentiment: float):
        """
        Check if entry conditions are met
        
        Entry requires:
        1. Technical signal (EMA crossover + RSI confirmation)
        2. Pattern confirmation OR positive sentiment
        3. Favorable market regime
        4. Risk management approval
        """
        if self.position_entry_price is not None:
            return  # Already in position
        
        current_price = bar.close.as_double()
        
        # Get technical signals
        ema_signal = self._get_ema_signal()
        rsi_signal = self._get_rsi_signal()
        pattern_signal = self._get_pattern_signal()
        sentiment_signal = sentiment
        
        # Calculate combined signal using ML
        features = np.array([ema_signal, rsi_signal, pattern_signal, sentiment_signal])
        logistic_probability = self.ml_optimizer.logistic_regression_predict(features)
        signal_probability = logistic_probability
        direction = OrderSide.BUY if ema_signal > 0 and rsi_signal > -0.9 else None

        # Enhanced classifier via XGBoost (if available)
        xgb_long_prob = None
        if (
            self.xgb_model is not None
            and self.xgb_scaler is not None
        ):
            xgb_vector = self._get_xgb_features()
            if xgb_vector is not None and direction is not None:
                numeric = xgb_vector[:3].reshape(1, -1)
                scaled_numeric = self.xgb_scaler.transform(numeric)
                model_input = np.column_stack([scaled_numeric, [[xgb_vector[3]]]])
                probs = self.xgb_model.predict_proba(model_input)[0]
                self.latest_xgb_probs = probs
                hold_prob, long_prob, short_prob = probs
                xgb_long_prob = float(long_prob)
                signal_probability = xgb_long_prob
                if xgb_long_prob < self.config.xgb_long_threshold or xgb_long_prob <= float(short_prob):
                    return
            else:
                # Insufficient data for XGB; fall back to logistic
                self.latest_xgb_probs = None
        else:
            self.latest_xgb_probs = None

        # Fallback threshold when relying on logistic regression
        if direction is None or signal_probability < 0.51:
            return

        # Store features for later learning
        self.last_signal_features = features
        
        # Get current market regime
        regime = self.regime_detector.current_regime
        regime_confidence = self.regime_detector.regime_confidence
        
        # Check if regime is favorable
        if regime == MarketRegime.TRENDING_DOWN and direction == OrderSide.BUY:
            return  # Don't buy in downtrend
        
        # Calculate stop loss and take profit using ATR
        atr_value = self.atr.value
        stop_loss = current_price - (atr_value * self.config.stop_loss_atr_multiplier)
        take_profit = current_price + (atr_value * self.config.take_profit_atr_multiplier)
        
        # Get account balance for position sizing
        account = self.portfolio.account(VenueId(self.config.venue))
        if not account:
            return
        
        # Get account balance (sum of all balances)
        account_balance = sum(float(b.total.as_double()) for b in account.balances().values())
        
        # Calculate position size
        position_size = self.risk_manager.calculate_position_size(
            account_balance=account_balance,
            entry_price=current_price,
            stop_loss=stop_loss,
            signal_confidence=signal_probability,
            sentiment=sentiment,
            regime=regime
        )
        
        # Execute entry
        self._execute_buy(bar, position_size, signal_confidence, regime)

        xgb_log_line = ""
        if self.latest_xgb_probs is not None and xgb_long_prob is not None:
            hold_prob, long_prob, short_prob = self.latest_xgb_probs
            xgb_log_line = (
                f"   XGB Probs → hold:{hold_prob:.2%} long:{long_prob:.2%} short:{short_prob:.2%}\n"
            )
        
        self.log.info(
            f"🟢 ENTRY SIGNAL\n"
            f"   Price: {current_price:.2f}\n"
            f"   Signal Probability: {signal_probability:.2%}\n"
            f"   EMA: {ema_signal:.2f} | RSI: {rsi_signal:.2f}\n"
            f"   Pattern: {pattern_signal:.2f} | Sentiment: {sentiment:.2f}\n"
            f"   Regime: {regime.value} ({regime_confidence:.2%})\n"
            f"   Position Size: {position_size}\n"
            f"   Stop Loss: {stop_loss:.2f} | Take Profit: {take_profit:.2f}\n"
            f"{xgb_log_line}".rstrip()
        )
    
    def _get_ema_signal(self) -> float:
        """
        Get EMA signal strength
        
        Returns:
            Signal from -1 (bearish) to 1 (bullish)
        """
        fast = self.fast_ema.value
        slow = self.slow_ema.value
        trend = self.trend_ema.value
        
        # Calculate crossover strength
        crossover = (fast - slow) / slow
        
        # Check trend alignment
        trend_alignment = 1.0 if fast > trend else -0.5
        
        signal = np.tanh(crossover * 10) * trend_alignment
        
        return float(signal)
    
    def _get_rsi_signal(self) -> float:
        """
        Get RSI signal strength
        
        Returns:
            Signal from -1 (oversold) to 1 (overbought)
        """
        rsi_value = self.rsi.value
        
        # Normalize RSI to -1 to 1
        signal = (rsi_value - 50) / 50
        
        return float(signal)
    
    def _get_pattern_signal(self) -> float:
        """
        Get pattern recognition signal
        
        Returns:
            Signal from -1 (bearish) to 1 (bullish)
        """
        # Check various patterns
        higher_highs = self.pattern_detector.detect_higher_highs_lows()
        lower_lows = self.pattern_detector.detect_lower_highs_lows()
        double_bottom_detected, double_bottom_conf = self.pattern_detector.detect_double_bottom()
        head_shoulders_detected, head_shoulders_conf = self.pattern_detector.detect_head_and_shoulders()
        
        signal = 0.0
        
        if higher_highs:
            signal += 0.5
        if lower_lows:
            signal -= 0.5
        if double_bottom_detected:
            signal += 0.3 * double_bottom_conf
        if head_shoulders_detected:
            signal -= 0.3 * head_shoulders_conf
        
        return float(np.clip(signal, -1.0, 1.0))
    
    def _check_exit_conditions(self, bar: Bar, sentiment: float):
        """
        Check multiple exit conditions
        
        Exits on:
        1. Stop loss hit
        2. Take profit hit
        3. Trailing stop hit
        4. Max hold time exceeded
        5. Technical reversal
        6. Regime change
        """
        if self.position_entry_price is None:
            return
        
        if self.portfolio.is_flat(self.instrument_id):
            self._reset_position_tracking()
            return
        
        current_price = bar.close.as_double()
        entry_price = self.position_entry_price
        
        # Calculate P&L
        pnl_pct = (current_price - entry_price) / entry_price
        
        # 1. Stop Loss
        if self.position_stop_loss and current_price <= self.position_stop_loss:
            self._execute_sell(bar, "Stop Loss Hit", pnl_pct)
            return
        
        # 2. Take Profit
        if self.position_take_profit and current_price >= self.position_take_profit:
            self._execute_sell(bar, "Take Profit Hit", pnl_pct)
            return
        
        # 3. Trailing Stop
        if self.trailing_stop_price and current_price < self.trailing_stop_price:
            self._execute_sell(bar, "Trailing Stop Hit", pnl_pct)
            return
        
        # Update trailing stop if in profit
        if pnl_pct > 0.01:  # At least 1% profit
            atr_value = self.atr.value
            new_trailing_stop = current_price - (atr_value * self.config.trailing_stop_atr_multiplier)
            if self.trailing_stop_price is None or new_trailing_stop > self.trailing_stop_price:
                self.trailing_stop_price = new_trailing_stop
        
        # 4. Max Hold Time
        if self.position_entry_time:
            time_held = (bar.ts_init - self.position_entry_time) / 1_000_000_000
            if time_held > self.config.max_hold_seconds:
                self._execute_sell(bar, "Max Hold Time", pnl_pct)
                return
        
        # 5. Technical Reversal
        ema_signal = self._get_ema_signal()
        if ema_signal < -0.3:  # Strong bearish signal
            self._execute_sell(bar, "Technical Reversal", pnl_pct)
            return
        
        # 6. Regime Change
        regime = self.regime_detector.current_regime
        if regime == MarketRegime.TRENDING_DOWN:
            self._execute_sell(bar, "Regime Change to Downtrend", pnl_pct)
            return
        
        # 7. Strong Negative Sentiment
        if sentiment < -0.4:
            self._execute_sell(bar, "Strong Negative Sentiment", pnl_pct)
            return
    
    def _execute_buy(self, bar: Bar, quantity: Decimal, signal_confidence: float, regime: MarketRegime):
        """Execute buy order and record entry"""
        order = self.order_factory.market(
            instrument_id=self.instrument_id,
            order_side=OrderSide.BUY,
            quantity=self.instrument.make_qty(quantity),
        )
        self.submit_order(order)
        
        # Record entry details
        current_price = bar.close.as_double()
        atr_value = self.atr.value
        
        self.position_entry_price = current_price
        self.position_entry_time = bar.ts_init
        self.position_stop_loss = current_price - (atr_value * self.config.stop_loss_atr_multiplier)
        self.position_take_profit = current_price + (atr_value * self.config.take_profit_atr_multiplier)
        self.trailing_stop_price = None
    
    def _execute_sell(self, bar: Bar, reason: str, pnl_pct: float):
        """Execute sell order and update performance"""
        if self.portfolio.is_flat(self.instrument_id):
            return
        
        # Close all positions
        self.close_all_positions(self.instrument_id)
        
        # Update performance
        was_win = pnl_pct > 0
        
        if was_win:
            self.trades_won += 1
        else:
            self.trades_lost += 1
        
        self.total_profit += pnl_pct
        self.trade_pnls.append(pnl_pct)
        
        # Update risk manager
        self.risk_manager.update_trade_result(pnl_pct, was_win)
        
        # Update ML model with trade outcome
        if self.last_signal_features is not None:
            outcome = 1.0 if was_win else 0.0
            self.ml_optimizer.update_signal_weights(self.last_signal_features, outcome)
        
        # Log exit
        self.log.info(
            f"🔴 EXIT: {reason}\n"
            f"   P&L: {pnl_pct*100:.2f}%\n"
            f"   Win Rate: {self.trades_won}/{self.trades_won + self.trades_lost}"
        )
        
        # Reset position tracking
        self._reset_position_tracking()
    
    def _reset_position_tracking(self):
        """Reset position tracking variables"""
        self.position_entry_price = None
        self.position_entry_time = None
        self.position_stop_loss = None
        self.position_take_profit = None
        self.trailing_stop_price = None
    
    def _optimize_parameters(self):
        """Optimize strategy parameters using ML"""
        total_trades = self.trades_won + self.trades_lost
        if total_trades < 10:
            return
        
        # Calculate performance metrics
        win_rate = self.trades_won / total_trades
        avg_profit = self.total_profit / total_trades if total_trades > 0 else 0
        
        # Calculate Sharpe ratio
        if len(self.trade_pnls) > 1:
            returns_std = np.std(self.trade_pnls)
            sharpe_ratio = (avg_profit / returns_std) if returns_std > 0 else 0
        else:
            sharpe_ratio = 0
        
        metrics = {
            'win_rate': win_rate,
            'avg_profit': avg_profit,
            'sharpe_ratio': sharpe_ratio
        }
        
        # Current parameters
        current_params = {
            'fast_ema': self.current_fast_period,
            'slow_ema': self.current_slow_period
        }
        
        # Optimize
        optimized_params = self.ml_optimizer.optimize_parameters(current_params, metrics)
        
        # Check if parameters changed
        if optimized_params != current_params:
            self.current_fast_period = optimized_params['fast_ema']
            self.current_slow_period = optimized_params['slow_ema']
            
            # Reinitialize EMAs
            self.fast_ema = ExponentialMovingAverage(self.current_fast_period)
            self.slow_ema = ExponentialMovingAverage(self.current_slow_period)
            
            self.log.info(
                f"🔄 PARAMETERS OPTIMIZED\n"
                f"   EMA: {self.current_fast_period}/{self.current_slow_period}\n"
                f"   Win Rate: {win_rate:.2%} | Sharpe: {sharpe_ratio:.2f}"
            )
    
    def _update_risk_metrics(self, bar: Bar):
        """Update and check risk metrics"""
        account = self.portfolio.account(VenueId(self.config.venue))
        if not account:
            return
        
        current_balance = sum(float(b.total.as_double()) for b in account.balances().values())
        
        # Update peak balance
        if current_balance > self.risk_manager.peak_balance:
            self.risk_manager.peak_balance = current_balance
        
        # Calculate win rate
        total_trades = self.trades_won + self.trades_lost
        win_rate = self.trades_won / total_trades if total_trades > 0 else 0.5
        
        # Check circuit breakers
        should_pause, reason = self.risk_manager.check_circuit_breakers(
            current_balance=current_balance,
            win_rate=win_rate,
            consecutive_losses=self.risk_manager.consecutive_losses
        )
        
        if should_pause:
            self.risk_manager.is_paused = True
            self.risk_manager.pause_reason = reason
            
            # Close any open positions
            if not self.portfolio.is_flat(self.instrument_id):
                self.close_all_positions(self.instrument_id)
            
            self.log.warning(f"🚨 CIRCUIT BREAKER TRIGGERED: {reason}")
    
    def _check_resume_conditions(self):
        """Check if strategy should resume after pause"""
        # Simple resume after cooldown period
        if self.bar_count % 100 == 0:
            self.risk_manager.is_paused = False
            self.risk_manager.pause_reason = None
            self.risk_manager.consecutive_losses = 0
            self.log.info("✅ STRATEGY RESUMED after cooldown")
    
    def on_stop(self):
        """Strategy cleanup and final stats"""
        total_trades = self.trades_won + self.trades_lost
        win_rate = self.trades_won / total_trades if total_trades > 0 else 0
        
        # Calculate additional metrics
        if len(self.trade_pnls) > 0:
            avg_win = np.mean([p for p in self.trade_pnls if p > 0]) if self.trades_won > 0 else 0
            avg_loss = np.mean([p for p in self.trade_pnls if p < 0]) if self.trades_lost > 0 else 0
            profit_factor = abs(avg_win / avg_loss) if avg_loss != 0 else 0
        else:
            avg_win = avg_loss = profit_factor = 0
        
        self.log.info(
            f"\n{'='*70}\n"
            f"📊 FINAL PERFORMANCE STATISTICS\n"
            f"{'='*70}\n"
            f"Total Trades: {total_trades}\n"
            f"Wins: {self.trades_won} | Losses: {self.trades_lost}\n"
            f"Win Rate: {win_rate:.2%}\n"
            f"Total P&L: {self.total_profit:.4f}\n"
            f"Avg Win: {avg_win:.4f} | Avg Loss: {avg_loss:.4f}\n"
            f"Profit Factor: {profit_factor:.2f}\n"
            f"Final EMA Periods: {self.current_fast_period}/{self.current_slow_period}\n"
            f"{'='*70}"
        )
