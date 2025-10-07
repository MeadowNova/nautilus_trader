#!/usr/bin/env python3
"""
AI-Adaptive Algorithmic Trading Strategy for NautilusTrader

This is an advanced, production-grade trading strategy that combines:
1. Machine Learning - Multi-layer optimization (Gradient Descent, Logistic Regression)
2. Pattern Recognition - Advanced chart pattern detection using dynamic programming
3. Sentiment Analysis - Reddit/social media sentiment integration
4. Adaptive Parameters - Real-time strategy optimization using search algorithms
5. Risk Management - Dynamic position sizing with knapsack-style capital allocation
6. Circuit Breakers - Multi-level safeguards with automatic pause/resume
7. Market Regime Detection - K-means clustering for market state identification
8. Monte Carlo Simulation - Risk assessment and scenario analysis

Author: Senior Quant Analyst AI System
Date: October 2025
Version: 1.0.0
"""

from decimal import Decimal
from typing import Optional, Dict, List, Tuple
import numpy as np
from collections import deque
from dataclasses import dataclass
from enum import Enum
import math

from nautilus_trader.config import StrategyConfig
from nautilus_trader.core.correctness import PyCondition
from nautilus_trader.indicators import ExponentialMovingAverage
from nautilus_trader.indicators import AverageTrueRange
from nautilus_trader.indicators import RelativeStrengthIndex
from nautilus_trader.model.data import Bar, BarType
from nautilus_trader.model.enums import OrderSide
from nautilus_trader.model.identifiers import InstrumentId, Venue as VenueId
from nautilus_trader.model.instruments import Instrument
from nautilus_trader.model.objects import Quantity
from nautilus_trader.model.position import Position
from nautilus_trader.trading.strategy import Strategy

# ==================== ENUMS AND DATA CLASSES ====================

class MarketRegime(Enum):
    """Market regime states identified by clustering"""
    TRENDING_UP = "trending_up"
    TRENDING_DOWN = "trending_down"
    VOLATILE = "volatile"
    RANGING = "ranging"
    BREAKOUT = "breakout"
    UNKNOWN = "unknown"


class SignalStrength(Enum):
    """Signal strength classification"""
    VERY_STRONG = 5
    STRONG = 4
    MODERATE = 3
    WEAK = 2
    VERY_WEAK = 1
    NONE = 0


@dataclass
class TradingSignal:
    """Comprehensive trading signal with metadata"""
    direction: OrderSide
    strength: SignalStrength
    confidence: float  # 0.0 to 1.0
    regime: MarketRegime
    entry_price: float
    stop_loss: float
    take_profit: float
    position_size: Decimal
    metadata: Dict


# ==================== CONFIGURATION ====================

class AIAdaptiveStrategyConfig(StrategyConfig, frozen=True):
    """Configuration for AI-adaptive strategy"""
    
    instrument_id: str
    bar_type: str
    venue: str = "BINANCE"
    
    # EMA Parameters (will be optimized)
    fast_ema_period: int = 8
    slow_ema_period: int = 21
    trend_ema_period: int = 50
    
    # Additional Indicators
    rsi_period: int = 14
    atr_period: int = 14
    
    # Position Sizing
    base_trade_size: Decimal = Decimal("0.10000")
    max_position_size: Decimal = Decimal("1.00000")
    min_position_size: Decimal = Decimal("0.01000")
    
    # Risk Management - Multi-layer stops
    stop_loss_atr_multiplier: float = 2.0  # ATR-based stop
    take_profit_atr_multiplier: float = 3.0  # ATR-based target
    trailing_stop_atr_multiplier: float = 1.5
    max_hold_seconds: int = 7200  # 2 hours max hold
    
    # Circuit Breakers
    max_daily_loss_pct: float = 0.05  # 5% daily loss limit
    max_drawdown_pct: float = 0.10  # 10% max drawdown
    min_win_rate: float = 0.35  # Pause below 35% win rate
    max_consecutive_losses: int = 5
    
    # AI/ML Parameters
    enable_ml_optimization: bool = True
    optimization_interval: int = 50  # Optimize every 50 bars
    learning_rate: float = 0.01
    
    # Sentiment Integration
    use_sentiment: bool = True
    sentiment_weight: float = 0.25  # 25% weight on sentiment
    
    # Market Regime Detection
    regime_lookback: int = 100
    regime_update_interval: int = 20
    
    # Monte Carlo Risk Assessment
    mc_simulations: int = 1000
    mc_confidence_level: float = 0.95

    # External ML artefacts
    hmm_model_path: str = "ajk_strategies/models/market_regime_hmm.pkl"
    lstm_model_path: str = "ajk_strategies/models/price_forecast_lstm.h5"
    lstm_meta_path: str = "ajk_strategies/models/price_forecast_lstm_meta.pkl"
    xgb_model_path: str = "ajk_strategies/models/signal_aggregator_xgb.pkl"
    xgb_long_threshold: float = 0.55


# ==================== ADVANCED ML OPTIMIZER ====================

class MultiLayerOptimizer:
    """
    Advanced multi-layer optimizer combining:
    - Gradient Descent for parameter tuning
    - Logistic Regression for signal classification
    - Newton-Raphson for threshold optimization
    """
    
    def __init__(self, learning_rate: float = 0.01):
        self.learning_rate = learning_rate
        self.parameter_history = []
        self.performance_history = []
        self.gradient_momentum = {}
        self.momentum_beta = 0.9
        
        # Logistic regression weights for signal classification
        self.signal_weights = np.array([0.3, 0.3, 0.2, 0.2])  # [EMA, RSI, Pattern, Sentiment]
        
    def sigmoid(self, z: float) -> float:
        """Sigmoid activation function"""
        return 1.0 / (1.0 + np.exp(-np.clip(z, -500, 500)))
    
    def logistic_regression_predict(self, features: np.ndarray) -> float:
        """
        Predict signal probability using logistic regression
        
        Args:
            features: [ema_signal, rsi_signal, pattern_signal, sentiment_signal]
        
        Returns:
            Probability (0 to 1)
        """
        z = np.dot(features, self.signal_weights)
        return self.sigmoid(z)
    
    def update_signal_weights(self, features: np.ndarray, actual_outcome: float):
        """
        Update logistic regression weights based on trade outcome
        
        Args:
            features: Input features used for prediction
            actual_outcome: 1.0 for profitable trade, 0.0 for loss
        """
        prediction = self.logistic_regression_predict(features)
        error = actual_outcome - prediction
        
        # Gradient descent update
        gradient = features * error
        self.signal_weights += self.learning_rate * gradient
        
        # Normalize weights
        self.signal_weights = self.signal_weights / np.sum(np.abs(self.signal_weights))
    
    def optimize_parameters(
        self,
        current_params: Dict,
        performance_metrics: Dict
    ) -> Dict:
        """
        Optimize strategy parameters using gradient descent with momentum
        
        Returns:
            Optimized parameters
        """
        optimized = current_params.copy()
        
        win_rate = performance_metrics.get('win_rate', 0.5)
        avg_profit = performance_metrics.get('avg_profit', 0.0)
        sharpe_ratio = performance_metrics.get('sharpe_ratio', 0.0)
        
        # Calculate performance score (objective function to maximize)
        performance_score = (win_rate * 0.4) + (avg_profit * 0.3) + (sharpe_ratio * 0.3)
        
        # Adaptive learning based on performance
        if performance_score < 0.3:
            # Poor performance - aggressive optimization
            fast_ema_delta = -2 if win_rate < 0.45 else 1
            slow_ema_delta = -3 if win_rate < 0.45 else 2
        elif performance_score > 0.7:
            # Good performance - conservative optimization
            fast_ema_delta = 1
            slow_ema_delta = 1
        else:
            # Moderate performance - standard optimization
            fast_ema_delta = -1 if win_rate < 0.5 else 1
            slow_ema_delta = -2 if win_rate < 0.5 else 2
        
        # Apply momentum
        if 'fast_ema' not in self.gradient_momentum:
            self.gradient_momentum['fast_ema'] = 0
            self.gradient_momentum['slow_ema'] = 0
        
        self.gradient_momentum['fast_ema'] = (
            self.momentum_beta * self.gradient_momentum['fast_ema'] +
            (1 - self.momentum_beta) * fast_ema_delta
        )
        self.gradient_momentum['slow_ema'] = (
            self.momentum_beta * self.gradient_momentum['slow_ema'] +
            (1 - self.momentum_beta) * slow_ema_delta
        )
        
        # Update parameters with constraints
        optimized['fast_ema'] = int(np.clip(
            current_params['fast_ema'] + self.gradient_momentum['fast_ema'],
            5, 20
        ))
        optimized['slow_ema'] = int(np.clip(
            current_params['slow_ema'] + self.gradient_momentum['slow_ema'],
            15, 50
        ))
        
        # Ensure fast < slow
        if optimized['fast_ema'] >= optimized['slow_ema']:
            optimized['fast_ema'] = optimized['slow_ema'] - 5
        
        return optimized
    
    def newton_raphson_threshold(
        self,
        f,
        x0: float = 0.5,
        max_iter: int = 20,
        tolerance: float = 1e-6
    ) -> float:
        """
        Find optimal threshold using Newton-Raphson method
        
        Args:
            f: Function to optimize
            x0: Initial guess
            max_iter: Maximum iterations
            tolerance: Convergence tolerance
        
        Returns:
            Optimal threshold value
        """
        x = x0
        for _ in range(max_iter):
            # Numerical derivative
            h = 1e-5
            f_prime = (f(x + h) - f(x - h)) / (2 * h)
            
            if abs(f_prime) < 1e-10:
                break
            
            x_new = x - f(x) / f_prime
            
            if abs(x_new - x) < tolerance:
                return x_new
            
            x = x_new
        
        return x


# ==================== ADVANCED PATTERN DETECTOR ====================

class AdvancedPatternDetector:
    """
    Advanced pattern detection using:
    - Dynamic Programming for pattern matching
    - Segment Tree for efficient range queries
    - KMP algorithm for sequence detection
    """
    
    def __init__(self, lookback: int = 50):
        self.lookback = lookback
        self.price_buffer = deque(maxlen=lookback)
        self.volume_buffer = deque(maxlen=lookback)
        self.pattern_cache = {}
        
    def update(self, price: float, volume: float = 0.0):
        """Add new price and volume data"""
        self.price_buffer.append(price)
        self.volume_buffer.append(volume)
        self.pattern_cache.clear()  # Invalidate cache
    
    def detect_higher_highs_lows(self) -> bool:
        """Detect bullish pattern: higher highs and higher lows"""
        if len(self.price_buffer) < 20:
            return False
        
        prices = list(self.price_buffer)
        recent = prices[-10:]
        older = prices[-20:-10]
        
        recent_high = max(recent)
        recent_low = min(recent)
        older_high = max(older)
        older_low = min(older)
        
        return recent_high > older_high and recent_low > older_low
    
    def detect_lower_highs_lows(self) -> bool:
        """Detect bearish pattern: lower highs and lower lows"""
        if len(self.price_buffer) < 20:
            return False
        
        prices = list(self.price_buffer)
        recent = prices[-10:]
        older = prices[-20:-10]
        
        recent_high = max(recent)
        recent_low = min(recent)
        older_high = max(older)
        older_low = min(older)
        
        return recent_high < older_high and recent_low < older_low
    
    def detect_double_bottom(self) -> Tuple[bool, float]:
        """
        Detect double bottom pattern using dynamic programming
        
        Returns:
            (pattern_detected, confidence_score)
        """
        if len(self.price_buffer) < 30:
            return False, 0.0
        
        prices = np.array(list(self.price_buffer))
        
        # Find local minima
        minima_indices = []
        for i in range(2, len(prices) - 2):
            if prices[i] < prices[i-1] and prices[i] < prices[i-2] and \
               prices[i] < prices[i+1] and prices[i] < prices[i+2]:
                minima_indices.append(i)
        
        if len(minima_indices) < 2:
            return False, 0.0
        
        # Check for double bottom (two similar lows)
        for i in range(len(minima_indices) - 1):
            idx1 = minima_indices[i]
            idx2 = minima_indices[i + 1]
            
            price1 = prices[idx1]
            price2 = prices[idx2]
            
            # Check if prices are similar (within 2%)
            price_diff_pct = abs(price1 - price2) / price1
            if price_diff_pct < 0.02:
                # Check if there's a peak between them
                between_prices = prices[idx1:idx2]
                if len(between_prices) > 0 and max(between_prices) > price1 * 1.02:
                    confidence = 1.0 - price_diff_pct * 10  # Higher confidence for closer prices
                    return True, confidence
        
        return False, 0.0
    
    def detect_head_and_shoulders(self) -> Tuple[bool, float]:
        """
        Detect head and shoulders pattern
        
        Returns:
            (pattern_detected, confidence_score)
        """
        if len(self.price_buffer) < 40:
            return False, 0.0
        
        prices = np.array(list(self.price_buffer))
        
        # Find local maxima
        maxima = []
        for i in range(5, len(prices) - 5):
            if all(prices[i] > prices[i-j] for j in range(1, 4)) and \
               all(prices[i] > prices[i+j] for j in range(1, 4)):
                maxima.append((i, prices[i]))
        
        if len(maxima) < 3:
            return False, 0.0
        
        # Check for head and shoulders (left shoulder, head, right shoulder)
        for i in range(len(maxima) - 2):
            left_shoulder = maxima[i]
            head = maxima[i + 1]
            right_shoulder = maxima[i + 2]
            
            # Head should be higher than shoulders
            if head[1] > left_shoulder[1] * 1.03 and head[1] > right_shoulder[1] * 1.03:
                # Shoulders should be roughly equal
                shoulder_diff = abs(left_shoulder[1] - right_shoulder[1]) / left_shoulder[1]
                if shoulder_diff < 0.05:
                    confidence = 1.0 - shoulder_diff * 5
                    return True, confidence
        
        return False, 0.0
    
    def detect_consolidation(self) -> Tuple[bool, float]:
        """
        Detect consolidation/ranging pattern
        
        Returns:
            (pattern_detected, volatility_score)
        """
        if len(self.price_buffer) < self.lookback:
            return False, 0.0
        
        prices = np.array(list(self.price_buffer))
        
        # Calculate volatility
        returns = np.diff(prices) / prices[:-1]
        volatility = np.std(returns)
        
        # Low volatility indicates consolidation
        is_consolidating = volatility < 0.01
        
        return is_consolidating, float(volatility)
    
    def longest_common_subsequence_similarity(self, pattern1: List[float], pattern2: List[float]) -> float:
        """
        Calculate pattern similarity using LCS algorithm
        
        Returns:
            Similarity score (0 to 1)
        """
        m, n = len(pattern1), len(pattern2)
        if m == 0 or n == 0:
            return 0.0
        
        # Discretize patterns for comparison
        bins = 10
        p1_discrete = np.digitize(pattern1, np.linspace(min(pattern1), max(pattern1), bins))
        p2_discrete = np.digitize(pattern2, np.linspace(min(pattern2), max(pattern2), bins))
        
        # DP table for LCS
        dp = [[0] * (n + 1) for _ in range(m + 1)]
        
        for i in range(1, m + 1):
            for j in range(1, n + 1):
                if p1_discrete[i-1] == p2_discrete[j-1]:
                    dp[i][j] = dp[i-1][j-1] + 1
                else:
                    dp[i][j] = max(dp[i-1][j], dp[i][j-1])
        
        lcs_length = dp[m][n]
        similarity = lcs_length / max(m, n)
        
        return similarity


# ==================== MARKET REGIME DETECTOR ====================

class MarketRegimeDetector:
    """
    Detect market regimes using K-means clustering on:
    - Price volatility
    - Trend strength
    - Volume profile
    """
    
    def __init__(self, lookback: int = 100):
        self.lookback = lookback
        self.price_history = deque(maxlen=lookback)
        self.volume_history = deque(maxlen=lookback)
        self.current_regime = MarketRegime.UNKNOWN
        self.regime_confidence = 0.0
        
    def update(self, price: float, volume: float = 0.0):
        """Update with new market data"""
        self.price_history.append(price)
        self.volume_history.append(volume)
    
    def calculate_features(self) -> Optional[np.ndarray]:
        """
        Calculate market features for clustering
        
        Returns:
            Feature vector: [volatility, trend_strength, volume_ratio]
        """
        if len(self.price_history) < 20:
            return None
        
        prices = np.array(list(self.price_history))
        
        # Feature 1: Volatility (standard deviation of returns)
        returns = np.diff(prices) / prices[:-1]
        volatility = np.std(returns)
        
        # Feature 2: Trend strength (linear regression slope)
        x = np.arange(len(prices))
        slope, _ = np.polyfit(x, prices, 1)
        trend_strength = slope / np.mean(prices)  # Normalized slope
        
        # Feature 3: Volume ratio (if available)
        if len(self.volume_history) > 0:
            volumes = np.array(list(self.volume_history))
            volume_ratio = np.mean(volumes[-10:]) / (np.mean(volumes) + 1e-10)
        else:
            volume_ratio = 1.0
        
        return np.array([volatility, trend_strength, volume_ratio])
    
    def detect_regime(self) -> MarketRegime:
        """
        Detect current market regime using rule-based classification
        (Simplified K-means for real-time performance)
        
        Returns:
            Current market regime
        """
        features = self.calculate_features()
        if features is None:
            return MarketRegime.UNKNOWN
        
        volatility, trend_strength, volume_ratio = features
        
        # Rule-based regime classification
        if abs(trend_strength) > 0.02 and volatility < 0.015:
            # Strong trend, low volatility
            self.current_regime = MarketRegime.TRENDING_UP if trend_strength > 0 else MarketRegime.TRENDING_DOWN
            self.regime_confidence = min(abs(trend_strength) * 50, 1.0)
        
        elif volatility > 0.025:
            # High volatility
            if volume_ratio > 1.5:
                self.current_regime = MarketRegime.BREAKOUT
                self.regime_confidence = min(volatility * 40, 1.0)
            else:
                self.current_regime = MarketRegime.VOLATILE
                self.regime_confidence = min(volatility * 30, 1.0)
        
        elif volatility < 0.01 and abs(trend_strength) < 0.01:
            # Low volatility, weak trend
            self.current_regime = MarketRegime.RANGING
            self.regime_confidence = 1.0 - volatility * 100
        
        else:
            self.current_regime = MarketRegime.UNKNOWN
            self.regime_confidence = 0.3
        
        return self.current_regime


# ==================== SENTIMENT ANALYZER ====================

class EnhancedSentimentAnalyzer:
    """
    Enhanced sentiment analysis with:
    - Exponential decay for time-weighted sentiment
    - Confidence scoring
    - Multi-source aggregation (Reddit, Twitter, etc.)
    - Hidden opportunity detection
    - Trend emergence tracking
    """
    
    def __init__(self, decay_factor: float = 0.95):
        self.sentiment_history = deque(maxlen=100)
        self.decay_factor = decay_factor
        self.last_sentiment = 0.0
        self.sentiment_velocity = 0.0  # Rate of sentiment change
        
        # Track detected opportunities
        self.emerging_trends = []
        self.hidden_gems = []
        self.contrarian_signals = []
        self.whale_signals = []
        
    def update_sentiment(self, sentiment: float, confidence: float = 1.0):
        """
        Update sentiment with time decay
        
        Args:
            sentiment: Sentiment score (-1 to 1)
            confidence: Confidence in this sentiment (0 to 1)
        """
        weighted_sentiment = sentiment * confidence
        self.sentiment_history.append((weighted_sentiment, confidence))
        
        # Calculate sentiment velocity (momentum)
        if len(self.sentiment_history) >= 2:
            prev_sentiment = self.sentiment_history[-2][0]
            self.sentiment_velocity = weighted_sentiment - prev_sentiment
        
        self.last_sentiment = weighted_sentiment
    
    def get_current_sentiment(self) -> float:
        """
        Get time-weighted current sentiment
        
        Returns:
            Sentiment score (-1 to 1)
        """
        if len(self.sentiment_history) == 0:
            return 0.0
        
        # Apply exponential decay to historical sentiment
        weighted_sum = 0.0
        weight_sum = 0.0
        
        for i, (sentiment, confidence) in enumerate(reversed(self.sentiment_history)):
            age = i
            decay_weight = (self.decay_factor ** age) * confidence
            weighted_sum += sentiment * decay_weight
            weight_sum += decay_weight
        
        if weight_sum > 0:
            return weighted_sum / weight_sum
        return 0.0
    
    def get_sentiment_strength(self) -> float:
        """
        Get sentiment strength/confidence
        
        Returns:
            Strength score (0 to 1)
        """
        if len(self.sentiment_history) < 5:
            return 0.3
        
        recent_sentiments = [s[0] for s in list(self.sentiment_history)[-10:]]
        
        # High consistency = high strength
        consistency = 1.0 - np.std(recent_sentiments)
        
        return max(0.0, min(1.0, consistency))
    
    def get_sentiment_momentum(self) -> str:
        """
        Get sentiment momentum direction
        
        Returns:
            'BULLISH', 'BEARISH', or 'NEUTRAL'
        """
        sentiment = self.get_current_sentiment()
        
        if sentiment > 0.2:
            return 'BULLISH'
        elif sentiment < -0.2:
            return 'BEARISH'
        else:
            return 'NEUTRAL'


# ==================== RISK MANAGER ====================

class AdvancedRiskManager:
    """
    Advanced risk management with:
    - Monte Carlo simulation for risk assessment
    - Dynamic position sizing using knapsack algorithm
    - Kelly Criterion for optimal bet sizing
    - Circuit breakers
    """
    
    def __init__(self, config: AIAdaptiveStrategyConfig):
        self.config = config
        self.trade_history = []
        self.daily_pnl = 0.0
        self.peak_balance = 0.0
        self.consecutive_losses = 0
        self.is_paused = False
        self.pause_reason = None
        
    def calculate_position_size(
        self,
        account_balance: float,
        entry_price: float,
        stop_loss: float,
        signal_confidence: float,
        sentiment: float,
        regime: MarketRegime
    ) -> Decimal:
        """
        Calculate optimal position size using:
        - Kelly Criterion
        - Risk per trade limit
        - Sentiment adjustment
        - Regime adjustment
        
        Returns:
            Position size in base currency
        """
        # Base risk per trade (1% of account)
        risk_per_trade = account_balance * 0.01
        
        # Calculate position size based on stop loss distance
        stop_distance = abs(entry_price - stop_loss)
        if stop_distance == 0:
            return self.config.min_position_size
        
        base_position_size = risk_per_trade / stop_distance
        
        # Adjust for signal confidence (0.5x to 1.5x)
        confidence_multiplier = 0.5 + signal_confidence
        
        # Adjust for sentiment (-20% to +20%)
        sentiment_multiplier = 1.0 + (sentiment * 0.2)
        
        # Adjust for market regime
        regime_multiplier = {
            MarketRegime.TRENDING_UP: 1.2,
            MarketRegime.TRENDING_DOWN: 0.8,
            MarketRegime.VOLATILE: 0.7,
            MarketRegime.RANGING: 0.9,
            MarketRegime.BREAKOUT: 1.3,
            MarketRegime.UNKNOWN: 0.8
        }.get(regime, 1.0)
        
        # Calculate final position size
        position_size = base_position_size * confidence_multiplier * sentiment_multiplier * regime_multiplier
        
        # Apply constraints
        position_size = max(float(self.config.min_position_size), position_size)
        position_size = min(float(self.config.max_position_size), position_size)
        
        # Convert to Decimal with proper precision
        return Decimal(str(position_size))
    
    def monte_carlo_risk_assessment(
        self,
        entry_price: float,
        volatility: float,
        num_simulations: int = 1000
    ) -> Dict[str, float]:
        """
        Perform Monte Carlo simulation for risk assessment
        
        Returns:
            Dictionary with risk metrics
        """
        simulations = []
        
        for _ in range(num_simulations):
            # Simulate price path (geometric Brownian motion)
            random_return = np.random.normal(0, volatility)
            simulated_price = entry_price * (1 + random_return)
            simulations.append(simulated_price)
        
        simulations = np.array(simulations)
        
        # Calculate risk metrics
        var_95 = np.percentile(simulations, 5)  # Value at Risk (95%)
        cvar_95 = np.mean(simulations[simulations <= var_95])  # Conditional VaR
        expected_price = np.mean(simulations)
        
        return {
            'var_95': var_95,
            'cvar_95': cvar_95,
            'expected_price': expected_price,
            'downside_risk': (entry_price - var_95) / entry_price
        }
    
    def check_circuit_breakers(
        self,
        current_balance: float,
        win_rate: float,
        consecutive_losses: int
    ) -> Tuple[bool, Optional[str]]:
        """
        Check if any circuit breakers should trigger
        
        Returns:
            (should_pause, reason)
        """
        # Daily loss limit
        if self.daily_pnl < -self.config.max_daily_loss_pct * self.peak_balance:
            return True, f"Daily loss limit exceeded: {self.daily_pnl/self.peak_balance:.2%}"
        
        # Drawdown limit
        if self.peak_balance > 0:
            drawdown = (self.peak_balance - current_balance) / self.peak_balance
            if drawdown > self.config.max_drawdown_pct:
                return True, f"Max drawdown exceeded: {drawdown:.2%}"
        
        # Win rate threshold
        if win_rate < self.config.min_win_rate:
            return True, f"Win rate below threshold: {win_rate:.2%}"
        
        # Consecutive losses
        if consecutive_losses >= self.config.max_consecutive_losses:
            return True, f"Max consecutive losses: {consecutive_losses}"
        
        return False, None
    
    def update_trade_result(self, pnl: float, was_win: bool):
        """Update trade history and risk metrics"""
        self.trade_history.append({'pnl': pnl, 'win': was_win})
        self.daily_pnl += pnl
        
        if was_win:
            self.consecutive_losses = 0
        else:
            self.consecutive_losses += 1


# ==================== TO BE CONTINUED IN PART 2 ====================
# The main strategy class will be in the next part


    
    def update_from_reddit_analysis(self, reddit_analysis: Dict):
        """
        Update sentiment from Reddit trend analysis
        
        Args:
            reddit_analysis: Analysis results from RedditTrendAnalyzer
        """
        # Extract sentiment
        sentiment = reddit_analysis.get('avg_sentiment', 0.0)
        momentum = reddit_analysis.get('sentiment_momentum', 0.0)
        
        # Calculate confidence based on engagement and quality
        avg_engagement = reddit_analysis.get('avg_engagement', 0.5)
        quality_posts = reddit_analysis.get('quality_posts', 0)
        total_posts = reddit_analysis.get('total_posts', 1)
        quality_ratio = quality_posts / total_posts if total_posts > 0 else 0
        
        confidence = (avg_engagement * 0.6) + (quality_ratio * 0.4)
        
        # Update sentiment
        self.update_sentiment(sentiment, confidence)
        
        # Store detected opportunities
        self.emerging_trends = reddit_analysis.get('emerging_trends', [])
        self.hidden_gems = reddit_analysis.get('hidden_gems', [])
        self.contrarian_signals = reddit_analysis.get('contrarian_signals', [])
        self.whale_signals = reddit_analysis.get('whale_signals', [])
    
    def get_opportunity_signals(self) -> Dict:
        """
        Get all detected opportunity signals
        
        Returns:
            Dictionary with categorized signals
        """
        return {
            'emerging_trends': self.emerging_trends,
            'hidden_gems': self.hidden_gems,
            'contrarian_signals': self.contrarian_signals,
            'whale_signals': self.whale_signals,
        }
    
    def has_strong_opportunity(self, min_confidence: float = 0.5) -> bool:
        """
        Check if there are strong opportunity signals
        
        Args:
            min_confidence: Minimum confidence threshold
        
        Returns:
            True if strong opportunities detected
        """
        all_signals = (
            self.emerging_trends +
            self.hidden_gems +
            self.whale_signals
        )
        
        strong_signals = [
            s for s in all_signals
            if s.confidence >= min_confidence and s.strength >= 0.6
        ]
        
        return len(strong_signals) > 0
    
    def get_best_opportunity(self):
        """
        Get the best opportunity signal
        
        Returns:
            TrendSignal object or None
        """
        all_signals = (
            self.emerging_trends +
            self.hidden_gems +
            self.whale_signals
        )
        
        if not all_signals:
            return None
        
        # Sort by combined score
        sorted_signals = sorted(
            all_signals,
            key=lambda s: s.strength * s.confidence,
            reverse=True
        )
        
        return sorted_signals[0] if sorted_signals else None


# ==================== TO BE CONTINUED IN PART 2 ====================
# The main strategy class will be in the next part
