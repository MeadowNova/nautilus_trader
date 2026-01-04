#!/usr/bin/env python3
"""
INSTITUTIONAL-GRADE LIVE MULTI-FACTOR TRADING STRATEGY
=======================================================

A comprehensive live trading strategy that combines multiple data sources
for enhanced alpha generation with institutional-grade risk management.

DATA SOURCES:
-------------
1. yfinance - Primary price/volume data (free, real-time)
2. Finnhub - News sentiment, social sentiment, alternative data
   - API Rate: 60 calls/min (free tier)
   - Endpoints: news sentiment, social sentiment, congressional trades
3. Alpha Vantage - Economic indicators, sector data
   - API Rate: 5 calls/min (free tier)
   - Endpoints: economic indicators, sector performance

STRATEGY COMPONENTS:
--------------------
1. RegimeDetector - HMM-like market regime classification
2. MultiFactorAlphaModel - Combines traditional and alternative factors:
   - Traditional: Momentum, Mean Reversion, Volatility, Volume, Microstructure
   - Alternative: News Sentiment, Social Sentiment, Congressional Trading, Economic Regime
3. AdaptivePositionSizer - Fractional Kelly with volatility scaling
4. RiskManager - ATR stops, trailing stops, time stops
5. PerformanceTracker - MAE/MFE analysis, R-multiples

INFRASTRUCTURE:
---------------
- Prometheus Metrics: Export on port 9100
  - nautilus_multifactor_pnl_total
  - nautilus_multifactor_positions
  - nautilus_multifactor_signals
  - nautilus_multifactor_regime
  - nautilus_multifactor_sentiment

- PostgreSQL Persistence:
  - Host: localhost:5435
  - User: nautilus
  - Password: nautilus_pass
  - Database: nautilus_trader
  - Tables: multi_factor_trades, portfolio_snapshots, risk_alerts

- Moomoo Execution:
  - Stock Account: 1252643 (paper trading)
  - Options Account: 1252648 (paper trading)
  - OpenD: 127.0.0.1:11111

TARGET SYMBOLS: SPY, AAPL, NVDA

CONFIGURATION:
--------------
- Initial Capital: $100,000
- Max Position Size: 2% per instrument
- Kelly Fraction: 0.35
- Poll Interval: 30 seconds
- Market Hours: 9:30 AM - 4:00 PM ET

USAGE:
------
    python scripts/live_multi_factor_strategy.py

    # With custom environment variables
    FINNHUB_API_KEY=xxx ALPHA_VANTAGE_API_KEY=xxx python scripts/live_multi_factor_strategy.py

Author: Quantitative Research Team
Date: 2025-12-09
"""

import asyncio
import os
import sys
import signal
import warnings
import logging
import time
from datetime import datetime, time as dt_time, timedelta, timezone
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Deque, Any
from dataclasses import dataclass, field
from enum import Enum
from collections import deque
import traceback
import threading

# Third-party imports
import yfinance as yf
import pandas as pd
import numpy as np
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

# Prometheus metrics
from prometheus_client import (
    Counter,
    Gauge,
    Histogram,
    Summary,
    Info,
    start_http_server,
    REGISTRY,
)

# PostgreSQL
import psycopg
from psycopg import sql

# Moomoo
from moomoo import (
    OpenQuoteContext,
    OpenSecTradeContext,
    TrdEnv,
    TrdMarket,
    OrderType,
    TrdSide,
)

warnings.filterwarnings('ignore')

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(name)s: %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
logger = logging.getLogger('MultiFactorStrategy')


# ============================================================================
# CONFIGURATION
# ============================================================================

@dataclass
class StrategyConfig:
    """Complete strategy configuration."""
    # Symbols
    symbols: List[str] = field(default_factory=lambda: ['SPY', 'AAPL', 'NVDA'])

    # Capital Management
    initial_capital: float = 100000.0
    kelly_fraction: float = 0.35
    max_leverage: float = 2.0
    volatility_target: float = 0.15
    max_portfolio_heat: float = 0.02  # 2% max risk per trade
    max_position_pct: float = 0.02  # 2% max position size per instrument
    drawdown_threshold: float = 0.10

    # Alpha Model Parameters
    momentum_lookback: int = 20
    mean_reversion_lookback: int = 20
    volatility_lookback: int = 30
    volume_lookback: int = 20

    # Risk Management
    atr_multiplier: float = 2.0
    time_stop_bars: int = 50
    trailing_stop_activation: float = 0.02
    profit_target_multiplier: float = 3.0

    # Regime Detection
    regime_lookback: int = 50

    # Signal Filtering
    min_conviction: float = 0.4

    # Update Frequency
    poll_interval_seconds: int = 30

    # API Keys (from environment)
    finnhub_api_key: str = field(default_factory=lambda: os.getenv('FINNHUB_API_KEY', ''))
    alpha_vantage_api_key: str = field(default_factory=lambda: os.getenv('ALPHA_VANTAGE_API_KEY', ''))

    # Moomoo Connection
    moomoo_host: str = '127.0.0.1'
    moomoo_port: int = 11111
    stock_account_id: int = 1252643
    options_account_id: int = 1252648

    # PostgreSQL Connection
    postgres_host: str = 'localhost'
    postgres_port: int = 5435
    postgres_user: str = 'nautilus'
    postgres_password: str = 'nautilus_pass'
    postgres_db: str = 'nautilus_trader'

    # Prometheus
    prometheus_port: int = 9100

    @property
    def postgres_connection_string(self) -> str:
        return f"postgresql://{self.postgres_user}:{self.postgres_password}@{self.postgres_host}:{self.postgres_port}/{self.postgres_db}"


# ============================================================================
# PROMETHEUS METRICS (Port 9100)
# ============================================================================

# Trading metrics
nautilus_multifactor_pnl_total = Counter(
    'nautilus_multifactor_pnl_total',
    'Total PnL from all trades',
    ['symbol', 'direction']
)
nautilus_multifactor_trades_total = Counter(
    'nautilus_multifactor_trades_total',
    'Total number of trades executed',
    ['symbol', 'direction', 'exit_reason']
)
nautilus_multifactor_positions = Gauge(
    'nautilus_multifactor_positions',
    'Current number of open positions'
)
nautilus_multifactor_position_value = Gauge(
    'nautilus_multifactor_position_value',
    'Current position value in dollars',
    ['symbol']
)

# Signal metrics
nautilus_multifactor_signals = Gauge(
    'nautilus_multifactor_signals',
    'Alpha signal values (-1 to +1)',
    ['symbol', 'factor']
)
nautilus_multifactor_ensemble_signal = Gauge(
    'nautilus_multifactor_ensemble_signal',
    'Ensemble alpha signal',
    ['symbol']
)
nautilus_multifactor_confidence = Gauge(
    'nautilus_multifactor_confidence',
    'Signal confidence (0 to 1)',
    ['symbol']
)

# Regime metrics
nautilus_multifactor_regime = Gauge(
    'nautilus_multifactor_regime',
    'Current market regime (0=choppy, 1=trending, 2=mean_reverting, 3=volatile)',
    ['symbol']
)
nautilus_multifactor_regime_confidence = Gauge(
    'nautilus_multifactor_regime_confidence',
    'Regime detection confidence',
    ['symbol']
)

# Sentiment metrics
nautilus_multifactor_sentiment = Gauge(
    'nautilus_multifactor_sentiment',
    'Sentiment scores from alternative data',
    ['symbol', 'source']
)
nautilus_multifactor_news_sentiment = Gauge(
    'nautilus_multifactor_news_sentiment',
    'News sentiment score (-1 to +1)',
    ['symbol']
)
nautilus_multifactor_social_sentiment = Gauge(
    'nautilus_multifactor_social_sentiment',
    'Social media sentiment score (-1 to +1)',
    ['symbol']
)
nautilus_multifactor_congressional_signal = Gauge(
    'nautilus_multifactor_congressional_signal',
    'Congressional trading signal (-1 to +1)',
    ['symbol']
)
nautilus_multifactor_economic_regime = Gauge(
    'nautilus_multifactor_economic_regime',
    'Economic regime indicator',
)

# Portfolio metrics
nautilus_multifactor_portfolio_value = Gauge(
    'nautilus_multifactor_portfolio_value',
    'Total portfolio value in dollars'
)
nautilus_multifactor_cash_balance = Gauge(
    'nautilus_multifactor_cash_balance',
    'Available cash balance'
)
nautilus_multifactor_leverage = Gauge(
    'nautilus_multifactor_leverage',
    'Current portfolio leverage'
)
nautilus_multifactor_max_drawdown = Gauge(
    'nautilus_multifactor_max_drawdown',
    'Maximum drawdown percentage'
)
nautilus_multifactor_sharpe_ratio = Gauge(
    'nautilus_multifactor_sharpe_ratio',
    'Annualized Sharpe ratio'
)
nautilus_multifactor_win_rate = Gauge(
    'nautilus_multifactor_win_rate',
    'Winning trade percentage',
    ['symbol']
)

# System metrics
nautilus_multifactor_data_updates = Counter(
    'nautilus_multifactor_data_updates',
    'Total data updates from various sources',
    ['source', 'symbol']
)
nautilus_multifactor_api_latency = Histogram(
    'nautilus_multifactor_api_latency_seconds',
    'API call latency in seconds',
    ['source'],
    buckets=[0.1, 0.25, 0.5, 1.0, 2.0, 5.0, 10.0]
)
nautilus_multifactor_strategy_iterations = Counter(
    'nautilus_multifactor_strategy_iterations',
    'Total strategy processing iterations'
)
nautilus_multifactor_errors = Counter(
    'nautilus_multifactor_errors',
    'Total errors encountered',
    ['component', 'error_type']
)

# System info
nautilus_multifactor_info = Info(
    'nautilus_multifactor',
    'Strategy configuration information'
)


# ============================================================================
# REGIME DETECTION
# ============================================================================

class MarketRegime(Enum):
    """Market regime classification"""
    CHOPPY = 0
    TRENDING = 1
    MEAN_REVERTING = 2
    VOLATILE = 3


@dataclass
class RegimeState:
    """State vector for regime detection"""
    regime: MarketRegime
    confidence: float
    volatility_percentile: float
    trend_strength: float
    mean_reversion_score: float


class RegimeDetector:
    """
    Advanced regime detection using rolling statistics and state persistence.
    Combines multiple metrics to classify market conditions.
    """

    def __init__(self, lookback: int = 50):
        self.lookback = lookback
        self.regime_history: Deque[RegimeState] = deque(maxlen=100)

    def detect_regime(self, prices: np.ndarray, volumes: np.ndarray) -> RegimeState:
        """
        Detect current market regime using multiple indicators.
        """
        if len(prices) < self.lookback:
            return RegimeState(MarketRegime.CHOPPY, 0.5, 0.5, 0.0, 0.0)

        recent_prices = prices[-self.lookback:]

        # Calculate returns and volatility
        returns = np.diff(np.log(recent_prices))

        # Trend strength (directional movement index)
        trend_strength = self._calculate_trend_strength(recent_prices)

        # Mean reversion score (using lag-1 autocorrelation)
        mean_reversion_score = self._calculate_mean_reversion_score(returns)

        # Volatility percentile
        if len(prices) >= 252:
            vol_history = pd.Series(prices[-252:]).pct_change().rolling(20).std()
            current_vol = vol_history.iloc[-1]
            volatility_percentile = (vol_history <= current_vol).sum() / len(vol_history)
        else:
            volatility_percentile = 0.5

        # Regime classification
        regime, confidence = self._classify_regime(
            trend_strength, mean_reversion_score, volatility_percentile
        )

        state = RegimeState(
            regime=regime,
            confidence=confidence,
            volatility_percentile=volatility_percentile,
            trend_strength=trend_strength,
            mean_reversion_score=mean_reversion_score
        )

        self.regime_history.append(state)
        return state

    def _calculate_trend_strength(self, prices: np.ndarray) -> float:
        """Calculate trend strength using directional movement."""
        highs = np.maximum.accumulate(prices)
        lows = np.minimum.accumulate(prices[::-1])[::-1]

        up_moves = highs[1:] - highs[:-1]
        down_moves = lows[:-1] - lows[1:]

        total_move = np.sum(np.abs(np.diff(prices)))
        directional_move = np.abs(np.sum(up_moves) - np.sum(down_moves))

        if total_move == 0:
            return 0.0

        return min(directional_move / total_move, 1.0)

    def _calculate_mean_reversion_score(self, returns: np.ndarray) -> float:
        """Calculate mean reversion tendency using autocorrelation."""
        if len(returns) < 2:
            return 0.0

        returns_centered = returns - np.mean(returns)
        if np.std(returns_centered) == 0:
            return 0.0

        autocorr = np.corrcoef(returns_centered[:-1], returns_centered[1:])[0, 1]
        if np.isnan(autocorr):
            return 0.0

        return max(-autocorr, 0.0)

    def _classify_regime(self, trend_strength: float, mean_reversion: float,
                        vol_percentile: float) -> Tuple[MarketRegime, float]:
        """Classify market regime based on computed metrics."""
        # High volatility regime
        if vol_percentile > 0.8:
            return MarketRegime.VOLATILE, vol_percentile

        # Trending regime
        if trend_strength > 0.6 and mean_reversion < 0.4:
            confidence = (trend_strength + (1 - mean_reversion)) / 2
            return MarketRegime.TRENDING, confidence

        # Mean reverting regime
        if trend_strength < 0.4 and mean_reversion > 0.6:
            confidence = (mean_reversion + (1 - trend_strength)) / 2
            return MarketRegime.MEAN_REVERTING, confidence

        # Choppy regime
        confidence = 1.0 - abs(trend_strength - mean_reversion)
        return MarketRegime.CHOPPY, confidence


# ============================================================================
# MULTI-SOURCE DATA AGGREGATOR
# ============================================================================

class MultiSourceDataAggregator:
    """
    Aggregates data from multiple sources:
    - yfinance: Core price/OHLCV data
    - Finnhub: Sentiment signals (news, Reddit, Twitter)
    - Alpha Vantage: Economic indicators
    """

    def __init__(self, config: StrategyConfig):
        self.config = config
        self.symbols = config.symbols

        # yfinance tickers
        self.tickers = {sym: yf.Ticker(sym) for sym in self.symbols}

        # Data storage
        self.price_history: Dict[str, pd.DataFrame] = {}
        self.volume_history: Dict[str, pd.DataFrame] = {}
        self.last_prices: Dict[str, float] = {}

        # Sentiment data
        self.news_sentiment: Dict[str, float] = {sym: 0.0 for sym in self.symbols}
        self.social_sentiment: Dict[str, float] = {sym: 0.0 for sym in self.symbols}
        self.congressional_signals: Dict[str, float] = {sym: 0.0 for sym in self.symbols}

        # Economic indicators
        self.economic_indicators: Dict[str, float] = {}
        self.sector_data: Dict[str, Dict[str, float]] = {}

        # Rate limiting
        self.finnhub_last_call = 0.0
        self.finnhub_min_interval = 1.0  # 60 calls/min = 1 call/sec
        self.alpha_vantage_last_call = 0.0
        self.alpha_vantage_min_interval = 12.0  # 5 calls/min = 12 sec interval

        # HTTP session with retry
        self.session = self._create_session()

        logger.info(f"DataAggregator initialized for symbols: {self.symbols}")

    def _create_session(self) -> requests.Session:
        """Create HTTP session with retry logic."""
        session = requests.Session()
        retries = Retry(
            total=3,
            backoff_factor=0.5,
            status_forcelist=[429, 500, 502, 503, 504]
        )
        adapter = HTTPAdapter(max_retries=retries)
        session.mount('http://', adapter)
        session.mount('https://', adapter)
        return session

    def update_all_data(self):
        """Update all data sources."""
        logger.info("Updating all data sources...")

        # Update yfinance data (always)
        self._update_yfinance_data()

        # Update Finnhub data (with rate limiting)
        if self.config.finnhub_api_key:
            self._update_finnhub_data()

        # Update Alpha Vantage data (with rate limiting)
        if self.config.alpha_vantage_api_key:
            self._update_alpha_vantage_data()

    def _update_yfinance_data(self):
        """Fetch latest prices and historical data from yfinance."""
        for symbol in self.symbols:
            try:
                start_time = time.time()
                ticker = self.tickers[symbol]

                # Get historical data
                hist_intraday = ticker.history(period="5d", interval="1h")
                hist_daily = ticker.history(period="60d", interval="1d")

                if not hist_intraday.empty:
                    self.last_prices[symbol] = float(hist_intraday['Close'].iloc[-1])

                    # Combine for comprehensive history
                    combined_hist = pd.concat([hist_daily[:-5], hist_intraday])
                    self.price_history[symbol] = combined_hist['Close']
                    self.volume_history[symbol] = combined_hist['Volume']

                    logger.debug(f"{symbol}: ${self.last_prices[symbol]:.2f} "
                                f"(history: {len(self.price_history[symbol])} bars)")

                    # Update metrics
                    nautilus_multifactor_data_updates.labels(source='yfinance', symbol=symbol).inc()

                latency = time.time() - start_time
                nautilus_multifactor_api_latency.labels(source='yfinance').observe(latency)

            except Exception as e:
                logger.error(f"Error fetching yfinance data for {symbol}: {e}")
                nautilus_multifactor_errors.labels(component='data_aggregator', error_type='yfinance').inc()

    def _update_finnhub_data(self):
        """Fetch sentiment data from Finnhub."""
        # Rate limiting
        elapsed = time.time() - self.finnhub_last_call
        if elapsed < self.finnhub_min_interval:
            time.sleep(self.finnhub_min_interval - elapsed)

        api_key = self.config.finnhub_api_key
        base_url = "https://finnhub.io/api/v1"

        for symbol in self.symbols:
            try:
                start_time = time.time()

                # News Sentiment
                url = f"{base_url}/news-sentiment?symbol={symbol}&token={api_key}"
                response = self.session.get(url, timeout=10)

                if response.status_code == 200:
                    data = response.json()
                    if 'sentiment' in data:
                        # Finnhub returns sentiment as buzz, companyNewsScore, sectorAverageNewsScore
                        sentiment_score = data['sentiment'].get('bullishPercent', 0.5)
                        # Convert to -1 to +1 scale
                        self.news_sentiment[symbol] = (sentiment_score - 0.5) * 2

                        nautilus_multifactor_news_sentiment.labels(symbol=symbol).set(
                            self.news_sentiment[symbol]
                        )
                        nautilus_multifactor_sentiment.labels(symbol=symbol, source='news').set(
                            self.news_sentiment[symbol]
                        )

                self.finnhub_last_call = time.time()

                # Social Sentiment (Reddit + Twitter)
                time.sleep(self.finnhub_min_interval)  # Rate limit between calls

                url = f"{base_url}/stock/social-sentiment?symbol={symbol}&token={api_key}"
                response = self.session.get(url, timeout=10)

                if response.status_code == 200:
                    data = response.json()
                    if 'reddit' in data and len(data['reddit']) > 0:
                        # Average recent Reddit sentiment
                        reddit_scores = [r.get('score', 0) for r in data['reddit'][-10:]]
                        avg_reddit = np.mean(reddit_scores) if reddit_scores else 0
                        # Normalize to -1 to +1
                        self.social_sentiment[symbol] = np.tanh(avg_reddit / 100)

                    if 'twitter' in data and len(data['twitter']) > 0:
                        # Include Twitter if available
                        twitter_scores = [t.get('score', 0) for t in data['twitter'][-10:]]
                        avg_twitter = np.mean(twitter_scores) if twitter_scores else 0
                        twitter_norm = np.tanh(avg_twitter / 100)
                        # Combine Reddit and Twitter
                        self.social_sentiment[symbol] = (self.social_sentiment[symbol] + twitter_norm) / 2

                    nautilus_multifactor_social_sentiment.labels(symbol=symbol).set(
                        self.social_sentiment[symbol]
                    )
                    nautilus_multifactor_sentiment.labels(symbol=symbol, source='social').set(
                        self.social_sentiment[symbol]
                    )

                self.finnhub_last_call = time.time()

                # Congressional Trading Data
                time.sleep(self.finnhub_min_interval)

                url = f"{base_url}/stock/congressional-trading?symbol={symbol}&token={api_key}"
                response = self.session.get(url, timeout=10)

                if response.status_code == 200:
                    data = response.json()
                    if 'data' in data and len(data['data']) > 0:
                        # Analyze recent congressional trades
                        recent_trades = data['data'][:20]  # Last 20 trades
                        buy_count = sum(1 for t in recent_trades if t.get('transactionType') == 'purchase')
                        sell_count = sum(1 for t in recent_trades if t.get('transactionType') == 'sale')

                        if buy_count + sell_count > 0:
                            # Signal: positive if more buys, negative if more sells
                            self.congressional_signals[symbol] = (buy_count - sell_count) / (buy_count + sell_count)

                        nautilus_multifactor_congressional_signal.labels(symbol=symbol).set(
                            self.congressional_signals[symbol]
                        )
                        nautilus_multifactor_sentiment.labels(symbol=symbol, source='congressional').set(
                            self.congressional_signals[symbol]
                        )

                self.finnhub_last_call = time.time()

                # Update metrics
                nautilus_multifactor_data_updates.labels(source='finnhub', symbol=symbol).inc()

                latency = time.time() - start_time
                nautilus_multifactor_api_latency.labels(source='finnhub').observe(latency)

            except Exception as e:
                logger.error(f"Error fetching Finnhub data for {symbol}: {e}")
                nautilus_multifactor_errors.labels(component='data_aggregator', error_type='finnhub').inc()

    def _update_alpha_vantage_data(self):
        """Fetch economic indicators and sector data from Alpha Vantage."""
        # Rate limiting
        elapsed = time.time() - self.alpha_vantage_last_call
        if elapsed < self.alpha_vantage_min_interval:
            time.sleep(self.alpha_vantage_min_interval - elapsed)

        api_key = self.config.alpha_vantage_api_key
        base_url = "https://www.alphavantage.co/query"

        try:
            start_time = time.time()

            # Federal Funds Rate (interest rate environment)
            params = {
                'function': 'FEDERAL_FUNDS_RATE',
                'apikey': api_key,
                'datatype': 'json'
            }
            response = self.session.get(base_url, params=params, timeout=15)

            if response.status_code == 200:
                data = response.json()
                if 'data' in data and len(data['data']) > 0:
                    self.economic_indicators['fed_funds_rate'] = float(data['data'][0].get('value', 0))

            self.alpha_vantage_last_call = time.time()
            time.sleep(self.alpha_vantage_min_interval)

            # Treasury Yield (10-year)
            params = {
                'function': 'TREASURY_YIELD',
                'interval': 'daily',
                'maturity': '10year',
                'apikey': api_key,
                'datatype': 'json'
            }
            response = self.session.get(base_url, params=params, timeout=15)

            if response.status_code == 200:
                data = response.json()
                if 'data' in data and len(data['data']) > 0:
                    self.economic_indicators['treasury_10y'] = float(data['data'][0].get('value', 0))

            self.alpha_vantage_last_call = time.time()
            time.sleep(self.alpha_vantage_min_interval)

            # CPI (inflation)
            params = {
                'function': 'CPI',
                'apikey': api_key,
                'datatype': 'json'
            }
            response = self.session.get(base_url, params=params, timeout=15)

            if response.status_code == 200:
                data = response.json()
                if 'data' in data and len(data['data']) > 1:
                    current_cpi = float(data['data'][0].get('value', 0))
                    prev_cpi = float(data['data'][1].get('value', 0))
                    if prev_cpi > 0:
                        self.economic_indicators['cpi_yoy'] = (current_cpi - prev_cpi) / prev_cpi * 100

            self.alpha_vantage_last_call = time.time()
            time.sleep(self.alpha_vantage_min_interval)

            # Sector Performance
            params = {
                'function': 'SECTOR',
                'apikey': api_key
            }
            response = self.session.get(base_url, params=params, timeout=15)

            if response.status_code == 200:
                data = response.json()
                if 'Rank A: Real-Time Performance' in data:
                    self.sector_data['realtime'] = data['Rank A: Real-Time Performance']
                if 'Rank B: 1 Day Performance' in data:
                    self.sector_data['1day'] = data['Rank B: 1 Day Performance']

            self.alpha_vantage_last_call = time.time()

            # Calculate economic regime indicator
            self._calculate_economic_regime()

            # Update metrics
            nautilus_multifactor_data_updates.labels(source='alpha_vantage', symbol='ECONOMY').inc()

            latency = time.time() - start_time
            nautilus_multifactor_api_latency.labels(source='alpha_vantage').observe(latency)

        except Exception as e:
            logger.error(f"Error fetching Alpha Vantage data: {e}")
            nautilus_multifactor_errors.labels(component='data_aggregator', error_type='alpha_vantage').inc()

    def _calculate_economic_regime(self):
        """Calculate composite economic regime indicator."""
        # Simple economic regime: based on rates and inflation
        fed_rate = self.economic_indicators.get('fed_funds_rate', 0)
        treasury_10y = self.economic_indicators.get('treasury_10y', 0)
        cpi_yoy = self.economic_indicators.get('cpi_yoy', 0)

        # Regime score: -1 (bearish) to +1 (bullish)
        # Low rates + low inflation = bullish
        # High rates + high inflation = bearish
        rate_score = -np.tanh((fed_rate - 2.5) / 2)  # Neutral at 2.5%
        inflation_score = -np.tanh((cpi_yoy - 2.0) / 2)  # Neutral at 2%

        economic_regime = (rate_score + inflation_score) / 2
        self.economic_indicators['regime'] = economic_regime

        nautilus_multifactor_economic_regime.set(economic_regime)

    def get_price_array(self, symbol: str) -> Optional[np.ndarray]:
        """Get price history as numpy array."""
        if symbol not in self.price_history:
            return None
        return self.price_history[symbol].values

    def get_volume_array(self, symbol: str) -> Optional[np.ndarray]:
        """Get volume history as numpy array."""
        if symbol not in self.volume_history:
            return None
        return self.volume_history[symbol].values

    def get_last_price(self, symbol: str) -> Optional[float]:
        """Get most recent price."""
        return self.last_prices.get(symbol)

    def get_sentiment_data(self, symbol: str) -> Dict[str, float]:
        """Get all sentiment data for a symbol."""
        return {
            'news_sentiment': self.news_sentiment.get(symbol, 0.0),
            'social_sentiment': self.social_sentiment.get(symbol, 0.0),
            'congressional_signal': self.congressional_signals.get(symbol, 0.0),
            'economic_regime': self.economic_indicators.get('regime', 0.0)
        }


# ============================================================================
# MULTI-FACTOR ALPHA MODEL (Extended with Alternative Data)
# ============================================================================

@dataclass
class AlphaSignal:
    """Individual alpha signal with metadata"""
    name: str
    value: float  # -1 to +1
    confidence: float  # 0 to 1
    weight: float  # Factor weight in ensemble


class MultiFactorAlphaModel:
    """
    Extended multi-factor alpha model combining traditional and alternative signals.

    Traditional Factors:
    - Momentum
    - Mean Reversion
    - Volatility
    - Volume
    - Microstructure

    Alternative Factors (from Finnhub + Alpha Vantage):
    - News Sentiment
    - Social Media Sentiment
    - Congressional Trading
    - Economic Regime
    """

    def __init__(self, config: StrategyConfig):
        self.momentum_lookback = config.momentum_lookback
        self.mean_reversion_lookback = config.mean_reversion_lookback
        self.volatility_lookback = config.volatility_lookback
        self.volume_lookback = config.volume_lookback

        # Factor weights (traditional + alternative)
        self.factor_weights = {
            # Traditional factors (60% total)
            'momentum': 0.15,
            'mean_reversion': 0.15,
            'volatility': 0.12,
            'volume': 0.12,
            'microstructure': 0.06,
            # Alternative factors (40% total)
            'news_sentiment': 0.12,
            'social_sentiment': 0.08,
            'congressional': 0.10,
            'economic_regime': 0.10
        }

    def generate_signals(self, prices: np.ndarray, volumes: np.ndarray,
                        regime: RegimeState,
                        sentiment_data: Dict[str, float]) -> Dict[str, AlphaSignal]:
        """Generate all alpha signals including alternative data factors."""
        signals = {}

        # Traditional factors
        signals['momentum'] = self._momentum_signal(prices, regime)
        signals['mean_reversion'] = self._mean_reversion_signal(prices, regime)
        signals['volatility'] = self._volatility_signal(prices, regime)
        signals['volume'] = self._volume_signal(prices, volumes, regime)
        signals['microstructure'] = self._microstructure_signal(prices, volumes, regime)

        # Alternative data factors
        signals['news_sentiment'] = self._news_sentiment_signal(
            sentiment_data.get('news_sentiment', 0.0), regime
        )
        signals['social_sentiment'] = self._social_sentiment_signal(
            sentiment_data.get('social_sentiment', 0.0), regime
        )
        signals['congressional'] = self._congressional_signal(
            sentiment_data.get('congressional_signal', 0.0), regime
        )
        signals['economic_regime'] = self._economic_regime_signal(
            sentiment_data.get('economic_regime', 0.0), regime
        )

        return signals

    def _momentum_signal(self, prices: np.ndarray, regime: RegimeState) -> AlphaSignal:
        """Multi-scale momentum signal."""
        if len(prices) < self.momentum_lookback:
            return AlphaSignal('momentum', 0.0, 0.0, self.factor_weights['momentum'])

        recent_prices = prices[-self.momentum_lookback:]

        # Price momentum (ROC)
        roc = (recent_prices[-1] - recent_prices[0]) / recent_prices[0]
        roc_normalized = np.tanh(roc * 10)

        # Momentum acceleration
        mid_idx = len(recent_prices) // 2
        mid_price = recent_prices[mid_idx]
        first_half_momentum = (mid_price - recent_prices[0]) / recent_prices[0]
        second_half_momentum = (recent_prices[-1] - mid_price) / mid_price
        acceleration = second_half_momentum - first_half_momentum
        accel_normalized = np.tanh(acceleration * 20)

        # Moving average crossover
        fast_ma = np.mean(recent_prices[-5:])
        slow_ma = np.mean(recent_prices[-20:]) if len(recent_prices) >= 20 else np.mean(recent_prices)
        ma_signal = (fast_ma - slow_ma) / slow_ma if slow_ma != 0 else 0
        ma_normalized = np.tanh(ma_signal * 10)

        signal_value = 0.5 * roc_normalized + 0.3 * accel_normalized + 0.2 * ma_normalized

        # Confidence based on regime
        if regime.regime == MarketRegime.TRENDING:
            confidence = regime.confidence * (0.5 + 0.5 * abs(signal_value))
        else:
            confidence = 0.3 * abs(signal_value)

        return AlphaSignal('momentum', signal_value, confidence, self.factor_weights['momentum'])

    def _mean_reversion_signal(self, prices: np.ndarray, regime: RegimeState) -> AlphaSignal:
        """Mean reversion signal using multiple indicators."""
        if len(prices) < self.mean_reversion_lookback:
            return AlphaSignal('mean_reversion', 0.0, 0.0, self.factor_weights['mean_reversion'])

        recent_prices = prices[-self.mean_reversion_lookback:]
        current_price = recent_prices[-1]

        # Bollinger Band position
        ma = np.mean(recent_prices)
        std = np.std(recent_prices)
        bb_position = (current_price - ma) / (2 * std) if std > 0 else 0
        bb_signal = -np.tanh(bb_position)

        # RSI calculation
        returns = np.diff(recent_prices)
        gains = np.where(returns > 0, returns, 0)
        losses = np.where(returns < 0, -returns, 0)
        avg_gain = np.mean(gains[-14:]) if len(gains) >= 14 else np.mean(gains)
        avg_loss = np.mean(losses[-14:]) if len(losses) >= 14 else np.mean(losses)

        if avg_loss == 0:
            rsi = 100
        else:
            rs = avg_gain / avg_loss
            rsi = 100 - (100 / (1 + rs))

        rsi_signal = 0.0
        if rsi < 30:
            rsi_signal = (30 - rsi) / 30
        elif rsi > 70:
            rsi_signal = -(rsi - 70) / 30

        # Z-score
        z_score = (current_price - ma) / std if std > 0 else 0
        z_signal = -np.tanh(z_score * 0.5)

        signal_value = 0.4 * bb_signal + 0.4 * rsi_signal + 0.2 * z_signal

        # Confidence based on regime
        if regime.regime == MarketRegime.MEAN_REVERTING:
            confidence = regime.confidence * (0.6 + 0.4 * abs(signal_value))
        else:
            confidence = 0.4 * abs(signal_value)

        return AlphaSignal('mean_reversion', signal_value, confidence, self.factor_weights['mean_reversion'])

    def _volatility_signal(self, prices: np.ndarray, regime: RegimeState) -> AlphaSignal:
        """Volatility-based signal for regime-adapted trading."""
        if len(prices) < self.volatility_lookback:
            return AlphaSignal('volatility', 0.0, 0.0, self.factor_weights['volatility'])

        recent_prices = prices[-self.volatility_lookback:]
        returns = np.diff(np.log(recent_prices))

        current_vol = np.std(returns[-10:]) if len(returns) >= 10 else np.std(returns)
        historical_vol = np.std(returns)
        vol_ratio = current_vol / historical_vol if historical_vol > 0 else 1.0

        if vol_ratio < 0.8:
            signal_value = 0.5
        elif vol_ratio > 1.5:
            signal_value = -0.5
        else:
            signal_value = 0.0

        confidence = min(abs(vol_ratio - 1.0), 1.0) * 0.7

        return AlphaSignal('volatility', signal_value, confidence, self.factor_weights['volatility'])

    def _volume_signal(self, prices: np.ndarray, volumes: np.ndarray,
                      regime: RegimeState) -> AlphaSignal:
        """Volume-based signals for confirmation and divergence."""
        if len(prices) < self.volume_lookback or len(volumes) < self.volume_lookback:
            return AlphaSignal('volume', 0.0, 0.0, self.factor_weights['volume'])

        recent_prices = prices[-self.volume_lookback:]
        recent_volumes = volumes[-self.volume_lookback:]

        # On-Balance Volume
        price_changes = np.diff(recent_prices)
        obv = np.zeros(len(recent_volumes))
        for i in range(1, len(obv)):
            if price_changes[i-1] > 0:
                obv[i] = obv[i-1] + recent_volumes[i]
            elif price_changes[i-1] < 0:
                obv[i] = obv[i-1] - recent_volumes[i]
            else:
                obv[i] = obv[i-1]

        obv_std = np.std(obv)
        obv_slope = (obv[-1] - obv[0]) / len(obv)
        obv_signal = np.tanh(obv_slope / obv_std) if obv_std > 0 else 0.0

        # Volume momentum
        vol_ma_fast = np.mean(recent_volumes[-5:])
        vol_ma_slow = np.mean(recent_volumes[-20:]) if len(recent_volumes) >= 20 else np.mean(recent_volumes)
        vol_momentum = (vol_ma_fast - vol_ma_slow) / vol_ma_slow if vol_ma_slow > 0 else 0.0
        vol_signal = np.tanh(vol_momentum)

        # VWAP deviation
        total_vol = np.sum(recent_volumes)
        vwap = np.sum(recent_prices * recent_volumes) / total_vol if total_vol > 0 else recent_prices[-1]
        vwap_dev = (recent_prices[-1] - vwap) / vwap if vwap > 0 else 0
        vwap_signal = -np.tanh(vwap_dev * 5)

        signal_value = 0.4 * obv_signal + 0.3 * vol_signal + 0.3 * vwap_signal

        avg_volume = np.mean(recent_volumes)
        current_volume = recent_volumes[-1]
        volume_strength = min(current_volume / avg_volume, 2.0) / 2.0 if avg_volume > 0 else 0.5
        confidence = volume_strength * 0.7

        return AlphaSignal('volume', signal_value, confidence, self.factor_weights['volume'])

    def _microstructure_signal(self, prices: np.ndarray, volumes: np.ndarray,
                              regime: RegimeState) -> AlphaSignal:
        """Microstructure signals for market quality."""
        if len(prices) < 20 or len(volumes) < 20:
            return AlphaSignal('microstructure', 0.0, 0.0, self.factor_weights['microstructure'])

        recent_prices = prices[-20:]
        recent_volumes = volumes[-20:]

        price_changes = np.diff(recent_prices)
        volume_changes = np.diff(recent_volumes)

        if len(price_changes) > 1:
            pv_corr = np.corrcoef(price_changes, volume_changes)[0, 1]
            if np.isnan(pv_corr):
                pv_corr = 0.0
        else:
            pv_corr = 0.0

        liquidity_signal = pv_corr

        price_range = (np.max(recent_prices[-5:]) - np.min(recent_prices[-5:])) / recent_prices[-1]
        avg_volume = np.mean(recent_volumes[-5:])
        overall_avg = np.mean(recent_volumes)
        spread_proxy = price_range / (avg_volume / overall_avg) if overall_avg > 0 else 0
        spread_signal = -np.tanh(spread_proxy * 10)

        signal_value = 0.6 * liquidity_signal + 0.4 * spread_signal
        confidence = 0.5

        return AlphaSignal('microstructure', signal_value, confidence, self.factor_weights['microstructure'])

    def _news_sentiment_signal(self, news_sentiment: float, regime: RegimeState) -> AlphaSignal:
        """
        News sentiment factor from Finnhub.
        Positive news -> positive signal, with regime-based confidence adjustment.
        """
        signal_value = np.clip(news_sentiment, -1.0, 1.0)

        # Higher confidence in trending regimes (momentum follows sentiment)
        if regime.regime == MarketRegime.TRENDING:
            confidence = 0.7
        elif regime.regime == MarketRegime.VOLATILE:
            confidence = 0.4  # News can be noisy in volatile markets
        else:
            confidence = 0.5

        return AlphaSignal('news_sentiment', signal_value, confidence, self.factor_weights['news_sentiment'])

    def _social_sentiment_signal(self, social_sentiment: float, regime: RegimeState) -> AlphaSignal:
        """
        Social media sentiment factor from Finnhub (Reddit + Twitter).
        Treated as contrarian indicator in extreme readings.
        """
        signal_value = np.clip(social_sentiment, -1.0, 1.0)

        # Contrarian at extremes
        if abs(signal_value) > 0.8:
            signal_value = -signal_value * 0.5  # Fade extreme sentiment
            confidence = 0.6
        else:
            confidence = 0.4  # Lower confidence for moderate readings

        return AlphaSignal('social_sentiment', signal_value, confidence, self.factor_weights['social_sentiment'])

    def _congressional_signal(self, congressional_signal: float, regime: RegimeState) -> AlphaSignal:
        """
        Congressional trading signal from Finnhub.
        Smart money indicator - follow congressional trades.
        """
        signal_value = np.clip(congressional_signal, -1.0, 1.0)

        # Congressional trades have historically been informative
        confidence = 0.6 if abs(signal_value) > 0.3 else 0.3

        return AlphaSignal('congressional', signal_value, confidence, self.factor_weights['congressional'])

    def _economic_regime_signal(self, economic_regime: float, regime: RegimeState) -> AlphaSignal:
        """
        Economic regime indicator from Alpha Vantage.
        Based on interest rates and inflation.
        """
        signal_value = np.clip(economic_regime, -1.0, 1.0)

        # Economic regime affects all assets similarly
        confidence = 0.5

        return AlphaSignal('economic_regime', signal_value, confidence, self.factor_weights['economic_regime'])

    def compute_ensemble_signal(self, signals: Dict[str, AlphaSignal],
                               regime: RegimeState) -> Tuple[float, float]:
        """Combine all alpha signals into ensemble signal with confidence."""
        adjusted_weights = self._adjust_weights_for_regime(regime)

        total_signal = 0.0
        total_weight = 0.0
        total_confidence = 0.0

        for name, signal in signals.items():
            weight = adjusted_weights.get(name, signal.weight)
            confidence_adjusted_weight = weight * signal.confidence

            total_signal += signal.value * confidence_adjusted_weight
            total_weight += confidence_adjusted_weight
            total_confidence += signal.confidence * weight

        if total_weight == 0:
            return 0.0, 0.0

        ensemble_signal = total_signal / total_weight
        ensemble_confidence = total_confidence / sum(adjusted_weights.values())

        return ensemble_signal, ensemble_confidence

    def _adjust_weights_for_regime(self, regime: RegimeState) -> Dict[str, float]:
        """Dynamically adjust factor weights based on market regime."""
        weights = self.factor_weights.copy()

        if regime.regime == MarketRegime.TRENDING:
            weights['momentum'] *= 1.5
            weights['volume'] *= 1.3
            weights['mean_reversion'] *= 0.5
            weights['news_sentiment'] *= 1.2  # News follows trends

        elif regime.regime == MarketRegime.MEAN_REVERTING:
            weights['mean_reversion'] *= 1.8
            weights['momentum'] *= 0.4
            weights['social_sentiment'] *= 1.3  # Contrarian in range

        elif regime.regime == MarketRegime.VOLATILE:
            weights['volatility'] *= 1.5
            weights['momentum'] *= 0.6
            weights['mean_reversion'] *= 0.7
            weights['news_sentiment'] *= 0.7  # Reduce news weight
            weights['economic_regime'] *= 1.4  # Macro matters more

        # Normalize weights
        total = sum(weights.values())
        return {k: v/total for k, v in weights.items()}


# ============================================================================
# POSITION SIZING & RISK MANAGEMENT
# ============================================================================

@dataclass
class PositionSizeResult:
    """Result of position sizing calculation"""
    shares: float
    notional: float
    leverage: float
    risk_limit_used: float
    sizing_method: str


class AdaptivePositionSizer:
    """Sophisticated position sizing using Kelly Criterion."""

    def __init__(self, config: StrategyConfig):
        self.kelly_fraction = config.kelly_fraction
        self.max_leverage = config.max_leverage
        self.volatility_target = config.volatility_target
        self.max_portfolio_heat = config.max_portfolio_heat
        self.max_position_pct = config.max_position_pct
        self.drawdown_threshold = config.drawdown_threshold

        self.peak_portfolio_value = None

    def calculate_position_size(self, signal: float, confidence: float,
                               current_price: float, portfolio_value: float,
                               volatility: float, stop_loss_pct: float) -> PositionSizeResult:
        """Calculate optimal position size using multi-factor approach."""
        # Kelly Criterion base sizing
        edge = confidence * abs(signal)
        odds = stop_loss_pct
        kelly_size = (edge / odds) * self.kelly_fraction if odds > 0 else 0

        # Volatility scaling
        if volatility > 0:
            vol_scalar = self.volatility_target / volatility
            vol_scalar = np.clip(vol_scalar, 0.5, 2.0)
        else:
            vol_scalar = 1.0

        # Drawdown adjustment
        drawdown_scalar = self._calculate_drawdown_adjustment(portfolio_value)

        # Confidence scaling
        confidence_scalar = 0.5 + 0.5 * confidence

        # Combine all factors
        combined_scalar = kelly_size * vol_scalar * drawdown_scalar * confidence_scalar

        # Calculate notional and shares
        max_notional_leverage = portfolio_value * self.max_leverage
        max_notional_position = portfolio_value * self.max_position_pct
        target_notional = portfolio_value * combined_scalar

        # Apply portfolio heat limit
        max_risk = portfolio_value * self.max_portfolio_heat
        risk_adjusted_notional = max_risk / stop_loss_pct if stop_loss_pct > 0 else 0

        # Take minimum of all constraints
        final_notional = min(target_notional, max_notional_leverage,
                            max_notional_position, risk_adjusted_notional)
        final_notional = max(final_notional, 0)

        shares = (final_notional / current_price) if current_price > 0 else 0
        leverage = final_notional / portfolio_value if portfolio_value > 0 else 0
        risk_limit_used = (final_notional * stop_loss_pct) / max_risk if max_risk > 0 else 0

        return PositionSizeResult(
            shares=shares,
            notional=final_notional,
            leverage=leverage,
            risk_limit_used=risk_limit_used,
            sizing_method="adaptive_kelly"
        )

    def _calculate_drawdown_adjustment(self, portfolio_value: float) -> float:
        """Reduce position size during drawdowns."""
        if self.peak_portfolio_value is None:
            self.peak_portfolio_value = portfolio_value
        else:
            self.peak_portfolio_value = max(self.peak_portfolio_value, portfolio_value)

        drawdown = (self.peak_portfolio_value - portfolio_value) / self.peak_portfolio_value

        if drawdown < self.drawdown_threshold:
            return 1.0
        else:
            reduction = 1.0 - min((drawdown - self.drawdown_threshold) / self.drawdown_threshold, 0.5)
            return reduction


class RiskManager:
    """Advanced risk management with multiple protection layers."""

    def __init__(self, config: StrategyConfig):
        self.atr_multiplier = config.atr_multiplier
        self.time_stop_bars = config.time_stop_bars
        self.trailing_stop_activation = config.trailing_stop_activation
        self.profit_target_multiplier = config.profit_target_multiplier

    def calculate_stop_loss(self, entry_price: float, direction: int,
                           atr: float, regime: RegimeState) -> float:
        """Calculate dynamic stop loss based on ATR and regime."""
        multiplier = self.atr_multiplier

        if regime.regime == MarketRegime.VOLATILE:
            multiplier *= 1.5
        elif regime.regime == MarketRegime.CHOPPY:
            multiplier *= 1.2

        stop_distance = atr * multiplier

        if direction > 0:
            stop_loss = entry_price - stop_distance
        else:
            stop_loss = entry_price + stop_distance

        return stop_loss

    def calculate_profit_target(self, entry_price: float, stop_loss: float,
                               direction: int) -> float:
        """Calculate profit target based on risk-reward ratio."""
        risk = abs(entry_price - stop_loss)
        reward = risk * self.profit_target_multiplier

        if direction > 0:
            return entry_price + reward
        else:
            return entry_price - reward

    def update_trailing_stop(self, entry_price: float, current_price: float,
                            current_stop: float, direction: int, atr: float) -> float:
        """Update trailing stop based on favorable price movement."""
        if direction > 0:
            profit_pct = (current_price - entry_price) / entry_price

            if profit_pct >= self.trailing_stop_activation:
                new_stop = current_price - (atr * self.atr_multiplier * 0.7)
                return max(new_stop, current_stop)
        else:
            profit_pct = (entry_price - current_price) / entry_price

            if profit_pct >= self.trailing_stop_activation:
                new_stop = current_price + (atr * self.atr_multiplier * 0.7)
                return min(new_stop, current_stop)

        return current_stop


# ============================================================================
# TRADE TRACKING & POSTGRESQL PERSISTENCE
# ============================================================================

@dataclass
class Trade:
    """Complete trade record"""
    entry_time: datetime
    entry_price: float
    symbol: str
    exit_time: Optional[datetime] = None
    exit_price: Optional[float] = None
    direction: int = 0
    shares: float = 0.0
    stop_loss: float = 0.0
    profit_target: float = 0.0

    pnl: float = 0.0
    pnl_pct: float = 0.0
    mae: float = 0.0
    mae_pct: float = 0.0
    mfe: float = 0.0
    mfe_pct: float = 0.0

    entry_regime: Optional[MarketRegime] = None
    entry_confidence: float = 0.0
    exit_reason: str = ""
    bars_held: int = 0
    order_id: Optional[str] = None

    # Alternative data at entry
    news_sentiment_entry: float = 0.0
    social_sentiment_entry: float = 0.0
    congressional_signal_entry: float = 0.0


class PostgreSQLPersistence:
    """Persist trades, portfolio snapshots, and risk alerts to PostgreSQL."""

    def __init__(self, connection_string: str):
        self.connection_string = connection_string
        self._ensure_tables()
        logger.info(f"PostgreSQL persistence initialized")

    def _ensure_tables(self):
        """Create tables if they don't exist."""
        try:
            with psycopg.connect(self.connection_string) as conn:
                with conn.cursor() as cur:
                    # Multi-factor trades table
                    cur.execute("""
                        CREATE TABLE IF NOT EXISTS multi_factor_trades (
                            id SERIAL PRIMARY KEY,
                            symbol VARCHAR(10) NOT NULL,
                            entry_time TIMESTAMP NOT NULL,
                            entry_price NUMERIC(12, 4) NOT NULL,
                            exit_time TIMESTAMP,
                            exit_price NUMERIC(12, 4),
                            direction INTEGER NOT NULL,
                            shares NUMERIC(12, 4) NOT NULL,
                            stop_loss NUMERIC(12, 4),
                            profit_target NUMERIC(12, 4),
                            pnl NUMERIC(12, 4),
                            pnl_pct NUMERIC(10, 6),
                            mae NUMERIC(12, 4),
                            mae_pct NUMERIC(10, 6),
                            mfe NUMERIC(12, 4),
                            mfe_pct NUMERIC(10, 6),
                            entry_regime VARCHAR(20),
                            entry_confidence NUMERIC(10, 6),
                            exit_reason VARCHAR(50),
                            bars_held INTEGER,
                            order_id VARCHAR(50),
                            news_sentiment_entry NUMERIC(10, 6),
                            social_sentiment_entry NUMERIC(10, 6),
                            congressional_signal_entry NUMERIC(10, 6),
                            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                        )
                    """)

                    # Portfolio snapshots table
                    cur.execute("""
                        CREATE TABLE IF NOT EXISTS portfolio_snapshots (
                            id SERIAL PRIMARY KEY,
                            timestamp TIMESTAMP NOT NULL,
                            portfolio_value NUMERIC(14, 4) NOT NULL,
                            cash_balance NUMERIC(14, 4) NOT NULL,
                            positions_count INTEGER,
                            leverage NUMERIC(10, 6),
                            max_drawdown NUMERIC(10, 6),
                            sharpe_ratio NUMERIC(10, 6),
                            total_pnl NUMERIC(14, 4),
                            win_rate NUMERIC(10, 6),
                            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                        )
                    """)

                    # Risk alerts table
                    cur.execute("""
                        CREATE TABLE IF NOT EXISTS risk_alerts (
                            id SERIAL PRIMARY KEY,
                            timestamp TIMESTAMP NOT NULL,
                            alert_type VARCHAR(50) NOT NULL,
                            severity VARCHAR(20) NOT NULL,
                            symbol VARCHAR(10),
                            message TEXT,
                            current_value NUMERIC(14, 4),
                            threshold NUMERIC(14, 4),
                            acknowledged BOOLEAN DEFAULT FALSE,
                            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                        )
                    """)

                    # Create indexes
                    cur.execute("""
                        CREATE INDEX IF NOT EXISTS idx_trades_symbol ON multi_factor_trades(symbol);
                        CREATE INDEX IF NOT EXISTS idx_trades_entry_time ON multi_factor_trades(entry_time);
                        CREATE INDEX IF NOT EXISTS idx_snapshots_timestamp ON portfolio_snapshots(timestamp);
                        CREATE INDEX IF NOT EXISTS idx_alerts_timestamp ON risk_alerts(timestamp);
                    """)

                    conn.commit()
                    logger.info("Database tables created/verified")

        except Exception as e:
            logger.error(f"Failed to create database tables: {e}")
            raise

    def save_trade(self, trade: Trade):
        """Save completed trade to database."""
        try:
            with psycopg.connect(self.connection_string) as conn:
                with conn.cursor() as cur:
                    cur.execute("""
                        INSERT INTO multi_factor_trades (
                            symbol, entry_time, entry_price, exit_time, exit_price,
                            direction, shares, stop_loss, profit_target,
                            pnl, pnl_pct, mae, mae_pct, mfe, mfe_pct,
                            entry_regime, entry_confidence, exit_reason, bars_held, order_id,
                            news_sentiment_entry, social_sentiment_entry, congressional_signal_entry
                        ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                    """, (
                        trade.symbol, trade.entry_time, trade.entry_price,
                        trade.exit_time, trade.exit_price,
                        trade.direction, trade.shares, trade.stop_loss, trade.profit_target,
                        trade.pnl, trade.pnl_pct, trade.mae, trade.mae_pct, trade.mfe, trade.mfe_pct,
                        trade.entry_regime.name if trade.entry_regime else None,
                        trade.entry_confidence, trade.exit_reason, trade.bars_held, trade.order_id,
                        trade.news_sentiment_entry, trade.social_sentiment_entry, trade.congressional_signal_entry
                    ))
                    conn.commit()
                    logger.debug(f"Trade saved: {trade.symbol} PnL=${trade.pnl:.2f}")
        except Exception as e:
            logger.error(f"Failed to save trade: {e}")
            nautilus_multifactor_errors.labels(component='persistence', error_type='save_trade').inc()

    def save_portfolio_snapshot(self, portfolio_value: float, cash_balance: float,
                               positions_count: int, leverage: float,
                               max_dd: float, sharpe: float,
                               total_pnl: float, win_rate: float):
        """Save portfolio snapshot to database."""
        try:
            with psycopg.connect(self.connection_string) as conn:
                with conn.cursor() as cur:
                    cur.execute("""
                        INSERT INTO portfolio_snapshots (
                            timestamp, portfolio_value, cash_balance, positions_count,
                            leverage, max_drawdown, sharpe_ratio, total_pnl, win_rate
                        ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
                    """, (
                        datetime.now(), portfolio_value, cash_balance, positions_count,
                        leverage, max_dd, sharpe, total_pnl, win_rate
                    ))
                    conn.commit()
        except Exception as e:
            logger.error(f"Failed to save portfolio snapshot: {e}")
            nautilus_multifactor_errors.labels(component='persistence', error_type='save_snapshot').inc()

    def save_risk_alert(self, alert_type: str, severity: str,
                       message: str, symbol: Optional[str] = None,
                       current_value: Optional[float] = None,
                       threshold: Optional[float] = None):
        """Save risk alert to database."""
        try:
            with psycopg.connect(self.connection_string) as conn:
                with conn.cursor() as cur:
                    cur.execute("""
                        INSERT INTO risk_alerts (
                            timestamp, alert_type, severity, symbol, message,
                            current_value, threshold
                        ) VALUES (%s, %s, %s, %s, %s, %s, %s)
                    """, (
                        datetime.now(), alert_type, severity, symbol, message,
                        current_value, threshold
                    ))
                    conn.commit()
                    logger.warning(f"Risk alert saved: [{severity}] {alert_type}: {message}")
        except Exception as e:
            logger.error(f"Failed to save risk alert: {e}")
            nautilus_multifactor_errors.labels(component='persistence', error_type='save_alert').inc()


class PerformanceTracker:
    """Comprehensive performance tracking."""

    def __init__(self):
        self.trades: List[Trade] = []
        self.equity_curve: List[float] = []
        self.daily_returns: List[float] = []

    def add_trade(self, trade: Trade):
        """Record completed trade"""
        self.trades.append(trade)

    def add_equity_point(self, equity: float):
        """Record equity at point in time"""
        self.equity_curve.append(equity)

        if len(self.equity_curve) > 1:
            ret = (equity - self.equity_curve[-2]) / self.equity_curve[-2]
            self.daily_returns.append(ret)

    def calculate_metrics(self) -> Dict:
        """Calculate comprehensive performance metrics"""
        if len(self.trades) == 0:
            return {
                'total_trades': 0,
                'win_rate': 0.0,
                'total_pnl': 0.0,
                'sharpe_ratio': 0.0,
                'max_drawdown': 0.0
            }

        metrics = {}

        winning_trades = [t for t in self.trades if t.pnl > 0]
        losing_trades = [t for t in self.trades if t.pnl < 0]

        metrics['total_trades'] = len(self.trades)
        metrics['winning_trades'] = len(winning_trades)
        metrics['losing_trades'] = len(losing_trades)
        metrics['win_rate'] = len(winning_trades) / len(self.trades) if self.trades else 0

        total_pnl = sum(t.pnl for t in self.trades)
        metrics['total_pnl'] = total_pnl
        metrics['avg_pnl'] = total_pnl / len(self.trades)

        if winning_trades:
            metrics['avg_win'] = sum(t.pnl for t in winning_trades) / len(winning_trades)
            metrics['largest_win'] = max(t.pnl for t in winning_trades)

        if losing_trades:
            metrics['avg_loss'] = sum(t.pnl for t in losing_trades) / len(losing_trades)
            metrics['largest_loss'] = min(t.pnl for t in losing_trades)

        gross_profit = sum(t.pnl for t in winning_trades) if winning_trades else 0
        gross_loss = abs(sum(t.pnl for t in losing_trades)) if losing_trades else 0
        metrics['profit_factor'] = gross_profit / gross_loss if gross_loss > 0 else float('inf')

        if len(self.daily_returns) > 0:
            returns_array = np.array(self.daily_returns)
            if np.std(returns_array) > 0:
                metrics['sharpe_ratio'] = np.mean(returns_array) / np.std(returns_array) * np.sqrt(252)
            else:
                metrics['sharpe_ratio'] = 0

        if len(self.equity_curve) > 0:
            equity_array = np.array(self.equity_curve)
            running_max = np.maximum.accumulate(equity_array)
            drawdown = (equity_array - running_max) / running_max
            metrics['max_drawdown'] = abs(np.min(drawdown))
            metrics['current_drawdown'] = abs(drawdown[-1])

        return metrics


# ============================================================================
# MOOMOO EXECUTION CLIENT
# ============================================================================

class MoomooExecutionClient:
    """Execute trades via Moomoo OpenD with paper trading accounts."""

    def __init__(self, config: StrategyConfig):
        self.config = config
        self.host = config.moomoo_host
        self.port = config.moomoo_port
        self.quote_ctx: Optional[OpenQuoteContext] = None
        self.trade_ctx: Optional[OpenSecTradeContext] = None
        self.stock_account_id: Optional[str] = None
        self.options_account_id: Optional[str] = None

        # Transaction costs
        self.commission_rate = 0.0005  # 5 bps
        self.slippage_bps = 5.0  # 5 bps

    def connect(self):
        """Connect to Moomoo OpenD."""
        logger.info(f"Connecting to Moomoo OpenD at {self.host}:{self.port}...")

        self.quote_ctx = OpenQuoteContext(host=self.host, port=self.port)
        ret, data = self.quote_ctx.get_global_state()

        if ret != 0:
            raise RuntimeError(f"Quote context error: {data}")

        market_state = data.get('market_us', 'UNKNOWN')
        logger.info(f"US Market state: {market_state}")

        self.trade_ctx = OpenSecTradeContext(
            host=self.host,
            port=self.port,
            filter_trdmarket=TrdMarket.US
        )

        ret, data = self.trade_ctx.get_acc_list()

        if ret != 0:
            raise RuntimeError(f"Could not get account list: {data}")

        # Find paper trading accounts
        paper_accounts = data[data['trd_env'] == TrdEnv.SIMULATE]
        if paper_accounts.empty:
            raise RuntimeError("No paper trading accounts found!")

        # Look for specified accounts or use first available
        for _, row in paper_accounts.iterrows():
            acc_id = row['acc_id']
            sim_type = row.get('sim_acc_type', '')

            if acc_id == self.config.stock_account_id or sim_type != 'OPTION':
                if self.stock_account_id is None:
                    self.stock_account_id = acc_id
                    logger.info(f"Stock Account: {self.stock_account_id}")

            if acc_id == self.config.options_account_id or sim_type == 'OPTION':
                if self.options_account_id is None:
                    self.options_account_id = acc_id
                    logger.info(f"Options Account: {self.options_account_id}")

        if self.stock_account_id is None:
            raise RuntimeError("Could not find stock trading account")

    def disconnect(self):
        """Disconnect from Moomoo OpenD."""
        if self.quote_ctx:
            self.quote_ctx.close()
        if self.trade_ctx:
            self.trade_ctx.close()
        logger.info("Disconnected from Moomoo OpenD")

    def place_order(self, symbol: str, side: str, shares: int, price: float,
                   order_type: str = "LIMIT") -> Optional[str]:
        """Place order via Moomoo."""
        if not self.trade_ctx or not self.stock_account_id:
            logger.error("Moomoo not connected")
            return None

        try:
            moomoo_symbol = f"US.{symbol}"
            trd_side = TrdSide.BUY if side == "BUY" else TrdSide.SELL

            # Apply slippage
            slippage_factor = self.slippage_bps / 10000
            if side == "BUY":
                adjusted_price = price * (1 + slippage_factor)
            else:
                adjusted_price = price * (1 - slippage_factor)

            logger.info(f"Placing {order_type} order: {moomoo_symbol} {side} {shares} @ ${adjusted_price:.2f}")

            ret, data = self.trade_ctx.place_order(
                price=adjusted_price,
                qty=shares,
                code=moomoo_symbol,
                trd_side=trd_side,
                order_type=OrderType.NORMAL if order_type == "LIMIT" else OrderType.MARKET,
                trd_env=TrdEnv.SIMULATE,
            )

            if ret != 0:
                logger.error(f"Order placement failed: {data}")
                nautilus_multifactor_errors.labels(component='execution', error_type='order_failed').inc()
                return None

            order_id = str(data['order_id'].iloc[0]) if 'order_id' in data else None
            logger.info(f"Order placed successfully: {order_id}")
            return order_id

        except Exception as e:
            logger.error(f"Order placement error: {e}")
            nautilus_multifactor_errors.labels(component='execution', error_type='order_exception').inc()
            return None

    def get_account_info(self) -> Dict:
        """Get account balance and positions."""
        if not self.trade_ctx or not self.stock_account_id:
            return {}

        try:
            ret, data = self.trade_ctx.accinfo_query(trd_env=TrdEnv.SIMULATE)

            if ret != 0:
                logger.error(f"Account info error: {data}")
                return {}

            if not data.empty:
                row = data.iloc[0]
                return {
                    'cash': float(row.get('cash', 0.0)),
                    'power': float(row.get('power', 0.0)),
                    'total_assets': float(row.get('total_assets', 0.0)),
                    'market_val': float(row.get('market_val', 0.0)),
                }

        except Exception as e:
            logger.error(f"Account info error: {e}")

        return {}


# ============================================================================
# MAIN STRATEGY ORCHESTRATOR
# ============================================================================

class LiveMultiFactorStrategy:
    """Main strategy orchestration for live multi-factor trading."""

    def __init__(self, config: StrategyConfig,
                 data_aggregator: MultiSourceDataAggregator,
                 execution_client: MoomooExecutionClient,
                 persistence: PostgreSQLPersistence):
        self.config = config
        self.data_aggregator = data_aggregator
        self.execution_client = execution_client
        self.persistence = persistence

        # Components
        self.regime_detectors = {
            symbol: RegimeDetector(lookback=config.regime_lookback)
            for symbol in config.symbols
        }
        self.alpha_model = MultiFactorAlphaModel(config)
        self.position_sizer = AdaptivePositionSizer(config)
        self.risk_manager = RiskManager(config)
        self.performance_tracker = PerformanceTracker()

        # State
        self.current_positions: Dict[str, Trade] = {}
        self.portfolio_value = config.initial_capital
        self.cash = self.portfolio_value
        self.min_conviction = config.min_conviction
        self.iteration = 0

        logger.info(f"Strategy initialized with {len(config.symbols)} symbols")

    def is_market_hours(self) -> bool:
        """Check if currently in US market hours (9:30 AM - 4:00 PM ET)."""
        # Get current time in Eastern Time
        from zoneinfo import ZoneInfo
        et_tz = ZoneInfo('America/New_York')
        now_et = datetime.now(et_tz)

        market_open = dt_time(9, 30)
        market_close = dt_time(16, 0)
        current_time = now_et.time()
        is_weekday = now_et.weekday() < 5

        return is_weekday and market_open <= current_time <= market_close

    async def run_iteration(self):
        """Run single strategy iteration."""
        self.iteration += 1
        nautilus_multifactor_strategy_iterations.inc()

        logger.info(f"{'='*60}")
        logger.info(f"ITERATION {self.iteration} - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        logger.info(f"{'='*60}")

        # Update all data sources
        self.data_aggregator.update_all_data()

        # Get account info from Moomoo
        account_info = self.execution_client.get_account_info()
        if account_info:
            self.cash = account_info.get('cash', self.cash)
            logger.info(f"Account: Cash=${self.cash:,.2f}, Market Value=${account_info.get('market_val', 0):,.2f}")

        # Process each symbol
        for symbol in self.config.symbols:
            await self.process_symbol(symbol)

        # Update portfolio metrics
        self._update_portfolio_metrics()

        # Save portfolio snapshot
        metrics = self.performance_tracker.calculate_metrics()
        self.persistence.save_portfolio_snapshot(
            self.portfolio_value,
            self.cash,
            len(self.current_positions),
            self.portfolio_value / self.cash if self.cash > 0 else 0,
            metrics.get('max_drawdown', 0),
            metrics.get('sharpe_ratio', 0),
            metrics.get('total_pnl', 0),
            metrics.get('win_rate', 0)
        )

        # Check for risk alerts
        self._check_risk_alerts(metrics)

        logger.info(f"Portfolio Value: ${self.portfolio_value:,.2f} | Positions: {len(self.current_positions)}")

    async def process_symbol(self, symbol: str):
        """Process single symbol."""
        logger.debug(f"Processing {symbol}...")

        # Get data
        prices = self.data_aggregator.get_price_array(symbol)
        volumes = self.data_aggregator.get_volume_array(symbol)
        current_price = self.data_aggregator.get_last_price(symbol)
        sentiment_data = self.data_aggregator.get_sentiment_data(symbol)

        if prices is None or volumes is None or current_price is None:
            logger.warning(f"{symbol}: No data available")
            return

        if len(prices) < 50:
            logger.warning(f"{symbol}: Insufficient history ({len(prices)} bars)")
            return

        # Detect regime
        regime = self.regime_detectors[symbol].detect_regime(prices, volumes)
        logger.info(f"{symbol}: Regime={regime.regime.name} (confidence={regime.confidence:.2f})")

        # Update Prometheus metrics
        nautilus_multifactor_regime.labels(symbol=symbol).set(regime.regime.value)
        nautilus_multifactor_regime_confidence.labels(symbol=symbol).set(regime.confidence)

        # Generate alpha signals (including alternative data factors)
        signals = self.alpha_model.generate_signals(prices, volumes, regime, sentiment_data)

        # Compute ensemble signal
        ensemble_signal, ensemble_confidence = self.alpha_model.compute_ensemble_signal(signals, regime)

        logger.info(f"{symbol}: Signal={ensemble_signal:.3f}, Confidence={ensemble_confidence:.2f}")

        # Update Prometheus metrics for signals
        nautilus_multifactor_ensemble_signal.labels(symbol=symbol).set(ensemble_signal)
        nautilus_multifactor_confidence.labels(symbol=symbol).set(ensemble_confidence)

        for name, sig in signals.items():
            nautilus_multifactor_signals.labels(symbol=symbol, factor=name).set(sig.value)

        # Manage existing position or check for new entry
        if symbol in self.current_positions:
            await self._manage_position(symbol, current_price, prices, regime)
        else:
            await self._check_entry(symbol, current_price, ensemble_signal,
                                   ensemble_confidence, regime, signals,
                                   prices, volumes, sentiment_data)

    async def _manage_position(self, symbol: str, current_price: float,
                               prices: np.ndarray, regime: RegimeState):
        """Manage existing position."""
        position = self.current_positions[symbol]

        # Update MAE/MFE
        if position.direction > 0:
            unrealized_pct = (current_price - position.entry_price) / position.entry_price
            if unrealized_pct < position.mae_pct:
                position.mae_pct = unrealized_pct
                position.mae = current_price - position.entry_price
            if unrealized_pct > position.mfe_pct:
                position.mfe_pct = unrealized_pct
                position.mfe = current_price - position.entry_price
        else:
            unrealized_pct = (position.entry_price - current_price) / position.entry_price
            if unrealized_pct < position.mae_pct:
                position.mae_pct = unrealized_pct
                position.mae = position.entry_price - current_price
            if unrealized_pct > position.mfe_pct:
                position.mfe_pct = unrealized_pct
                position.mfe = position.entry_price - current_price

        # Check exit conditions
        exit_triggered = False
        exit_reason = ""

        # Stop loss
        if position.direction > 0 and current_price <= position.stop_loss:
            exit_triggered = True
            exit_reason = "stop_loss"
        elif position.direction < 0 and current_price >= position.stop_loss:
            exit_triggered = True
            exit_reason = "stop_loss"

        # Profit target
        if not exit_triggered:
            if position.direction > 0 and current_price >= position.profit_target:
                exit_triggered = True
                exit_reason = "profit_target"
            elif position.direction < 0 and current_price <= position.profit_target:
                exit_triggered = True
                exit_reason = "profit_target"

        # Time stop
        position.bars_held = self.iteration - position.bars_held
        if not exit_triggered and position.bars_held >= self.risk_manager.time_stop_bars:
            exit_triggered = True
            exit_reason = "time_stop"

        # Update trailing stop
        if not exit_triggered:
            atr = self._calculate_atr(prices)
            new_stop = self.risk_manager.update_trailing_stop(
                position.entry_price, current_price, position.stop_loss,
                position.direction, atr
            )
            if new_stop != position.stop_loss:
                logger.info(f"{symbol}: Trailing stop ${position.stop_loss:.2f} -> ${new_stop:.2f}")
                position.stop_loss = new_stop

        if exit_triggered:
            await self._close_position(symbol, current_price, exit_reason)

    async def _check_entry(self, symbol: str, current_price: float, signal: float,
                          confidence: float, regime: RegimeState,
                          signals: Dict[str, AlphaSignal], prices: np.ndarray,
                          volumes: np.ndarray, sentiment_data: Dict[str, float]):
        """Check for new entry opportunity."""
        # Conviction filter
        if confidence < self.min_conviction:
            return

        # Signal strength filter
        if abs(signal) < 0.3:
            return

        # Market hours check
        if not self.is_market_hours():
            logger.debug(f"{symbol}: Outside market hours")
            return

        direction = 1 if signal > 0 else -1

        # Calculate position size
        volatility = self._calculate_volatility(prices)
        atr = self._calculate_atr(prices)
        stop_loss_pct = (atr * self.risk_manager.atr_multiplier) / current_price

        position_size = self.position_sizer.calculate_position_size(
            signal, confidence, current_price, self.portfolio_value,
            volatility, stop_loss_pct
        )

        # Check capital
        required_capital = position_size.notional
        transaction_cost = required_capital * self.execution_client.commission_rate

        if required_capital + transaction_cost > self.cash:
            logger.debug(f"{symbol}: Insufficient capital")
            return

        # Calculate stops
        stop_loss = self.risk_manager.calculate_stop_loss(current_price, direction, atr, regime)
        profit_target = self.risk_manager.calculate_profit_target(current_price, stop_loss, direction)

        shares = int(position_size.shares)
        if shares == 0:
            return

        logger.info(f"{symbol} ENTRY: {'LONG' if direction > 0 else 'SHORT'} {shares} @ ${current_price:.2f}")
        logger.info(f"  Stop=${stop_loss:.2f}, Target=${profit_target:.2f}, Risk=${stop_loss_pct*100:.1f}%")

        # Place order
        side = "BUY" if direction > 0 else "SELL"
        order_id = self.execution_client.place_order(symbol, side, shares, current_price, "LIMIT")

        if order_id:
            trade = Trade(
                entry_time=datetime.now(),
                entry_price=current_price,
                symbol=symbol,
                direction=direction,
                shares=shares * direction,
                stop_loss=stop_loss,
                profit_target=profit_target,
                entry_regime=regime.regime,
                entry_confidence=confidence,
                bars_held=self.iteration,
                order_id=order_id,
                news_sentiment_entry=sentiment_data.get('news_sentiment', 0.0),
                social_sentiment_entry=sentiment_data.get('social_sentiment', 0.0),
                congressional_signal_entry=sentiment_data.get('congressional_signal', 0.0)
            )

            self.current_positions[symbol] = trade
            self.cash -= (required_capital + transaction_cost)

            # Update metrics
            nautilus_multifactor_positions.set(len(self.current_positions))
            nautilus_multifactor_position_value.labels(symbol=symbol).set(required_capital)

    async def _close_position(self, symbol: str, exit_price: float, exit_reason: str):
        """Close existing position."""
        if symbol not in self.current_positions:
            return

        position = self.current_positions[symbol]

        logger.info(f"{symbol} EXIT: {exit_reason}")
        logger.info(f"  Entry=${position.entry_price:.2f}, Exit=${exit_price:.2f}")

        side = "SELL" if position.direction > 0 else "BUY"
        shares = int(abs(position.shares))

        order_id = self.execution_client.place_order(symbol, side, shares, exit_price, "LIMIT")

        if order_id:
            # Calculate PnL
            if position.direction > 0:
                pnl = (exit_price - position.entry_price) * abs(position.shares)
                pnl_pct = (exit_price - position.entry_price) / position.entry_price
            else:
                pnl = (position.entry_price - exit_price) * abs(position.shares)
                pnl_pct = (position.entry_price - exit_price) / position.entry_price

            notional = abs(position.shares) * exit_price
            transaction_cost = notional * self.execution_client.commission_rate
            pnl -= transaction_cost

            position.exit_time = datetime.now()
            position.exit_price = exit_price
            position.pnl = pnl
            position.pnl_pct = pnl_pct
            position.exit_reason = exit_reason
            position.bars_held = self.iteration - position.bars_held

            self.cash += notional + pnl - transaction_cost

            logger.info(f"  PnL=${pnl:.2f} ({pnl_pct*100:.2f}%), MAE={position.mae_pct*100:.2f}%, MFE={position.mfe_pct*100:.2f}%")

            # Update metrics
            direction_label = "LONG" if position.direction > 0 else "SHORT"
            nautilus_multifactor_trades_total.labels(
                symbol=symbol, direction=direction_label, exit_reason=exit_reason
            ).inc()
            nautilus_multifactor_pnl_total.labels(symbol=symbol, direction=direction_label).inc(pnl)

            self.performance_tracker.add_trade(position)
            self.persistence.save_trade(position)

            del self.current_positions[symbol]

            nautilus_multifactor_positions.set(len(self.current_positions))
            nautilus_multifactor_position_value.labels(symbol=symbol).set(0)

            metrics = self.performance_tracker.calculate_metrics()
            nautilus_multifactor_win_rate.labels(symbol=symbol).set(metrics.get('win_rate', 0))

    def _update_portfolio_metrics(self):
        """Update portfolio-level metrics."""
        self.portfolio_value = self.cash

        for symbol, position in self.current_positions.items():
            current_price = self.data_aggregator.get_last_price(symbol)
            if current_price:
                if position.direction > 0:
                    unrealized_pnl = (current_price - position.entry_price) * abs(position.shares)
                else:
                    unrealized_pnl = (position.entry_price - current_price) * abs(position.shares)

                notional = abs(position.shares) * position.entry_price
                self.portfolio_value += notional + unrealized_pnl

        self.performance_tracker.add_equity_point(self.portfolio_value)
        metrics = self.performance_tracker.calculate_metrics()

        # Update Prometheus
        nautilus_multifactor_portfolio_value.set(self.portfolio_value)
        nautilus_multifactor_cash_balance.set(self.cash)
        if self.cash > 0:
            nautilus_multifactor_leverage.set(self.portfolio_value / self.cash)
        nautilus_multifactor_max_drawdown.set(metrics.get('max_drawdown', 0))
        nautilus_multifactor_sharpe_ratio.set(metrics.get('sharpe_ratio', 0))

    def _check_risk_alerts(self, metrics: Dict):
        """Check for risk conditions and create alerts."""
        max_dd = metrics.get('max_drawdown', 0)

        # Drawdown alert
        if max_dd > 0.05:
            severity = "WARNING" if max_dd < 0.10 else "CRITICAL"
            self.persistence.save_risk_alert(
                alert_type="MAX_DRAWDOWN",
                severity=severity,
                message=f"Maximum drawdown reached {max_dd*100:.1f}%",
                current_value=max_dd,
                threshold=0.10
            )

        # Position concentration alert
        for symbol, position in self.current_positions.items():
            position_pct = (abs(position.shares) * position.entry_price) / self.portfolio_value
            if position_pct > self.config.max_position_pct * 1.5:
                self.persistence.save_risk_alert(
                    alert_type="POSITION_CONCENTRATION",
                    severity="WARNING",
                    symbol=symbol,
                    message=f"Position in {symbol} exceeds limit at {position_pct*100:.1f}%",
                    current_value=position_pct,
                    threshold=self.config.max_position_pct
                )

    def _calculate_volatility(self, prices: np.ndarray) -> float:
        """Calculate annualized volatility"""
        if len(prices) < 20:
            return 0.15
        returns = np.diff(np.log(prices[-20:]))
        return np.std(returns) * np.sqrt(252)

    def _calculate_atr(self, prices: np.ndarray, period: int = 14) -> float:
        """Calculate Average True Range"""
        if len(prices) < period + 1:
            return prices[-1] * 0.02

        highs = prices[-period:]
        lows = prices[-period:] * 0.98
        closes = prices[-period-1:-1]

        tr = np.maximum(
            highs - lows,
            np.maximum(abs(highs - closes), abs(lows - closes))
        )
        return np.mean(tr)


# ============================================================================
# MAIN EXECUTION
# ============================================================================

async def main():
    """Main entry point for the live multi-factor strategy."""

    print("""
    =========================================================================
    INSTITUTIONAL-GRADE LIVE MULTI-FACTOR TRADING STRATEGY
    =========================================================================

    Data Sources:
    - yfinance: Core price/OHLCV data
    - Finnhub: News sentiment, social sentiment, congressional trades
    - Alpha Vantage: Economic indicators, sector data

    Infrastructure:
    - Prometheus Metrics: http://localhost:9100/metrics
    - PostgreSQL: localhost:5435 (nautilus_trader)
    - Moomoo OpenD: 127.0.0.1:11111

    Target Symbols: SPY, AAPL, NVDA

    Configuration:
    - Initial Capital: $100,000
    - Max Position Size: 2% per instrument
    - Kelly Fraction: 0.35
    - Poll Interval: 30 seconds

    Press Ctrl+C to gracefully shutdown.
    =========================================================================
    """)

    # Create configuration
    config = StrategyConfig()

    # Log API key status
    if config.finnhub_api_key:
        logger.info("Finnhub API key configured")
    else:
        logger.warning("Finnhub API key not set - sentiment data will be unavailable")

    if config.alpha_vantage_api_key:
        logger.info("Alpha Vantage API key configured")
    else:
        logger.warning("Alpha Vantage API key not set - economic data will be unavailable")

    # Initialize components
    logger.info("Initializing components...")

    # Data aggregator
    data_aggregator = MultiSourceDataAggregator(config)

    # Moomoo execution client
    execution_client = MoomooExecutionClient(config)
    try:
        execution_client.connect()
    except Exception as e:
        logger.error(f"Failed to connect to Moomoo: {e}")
        logger.warning("Continuing without execution capability - signals only")

    # PostgreSQL persistence
    try:
        persistence = PostgreSQLPersistence(config.postgres_connection_string)
    except Exception as e:
        logger.error(f"Failed to connect to PostgreSQL: {e}")
        raise

    # Start Prometheus metrics server
    logger.info(f"Starting Prometheus metrics server on port {config.prometheus_port}...")
    start_http_server(config.prometheus_port)

    # Set strategy info metric
    nautilus_multifactor_info.info({
        'symbols': ','.join(config.symbols),
        'initial_capital': str(config.initial_capital),
        'kelly_fraction': str(config.kelly_fraction),
        'version': '1.0.0'
    })

    # Initialize strategy
    strategy = LiveMultiFactorStrategy(
        config, data_aggregator, execution_client, persistence
    )

    logger.info(f"""
    =========================================================================
    LIVE TRADING ACTIVE
    =========================================================================
    Initial Capital: ${config.initial_capital:,.2f}
    Symbols: {', '.join(config.symbols)}
    Poll Interval: {config.poll_interval_seconds}s

    Metrics: http://localhost:{config.prometheus_port}/metrics
    =========================================================================
    """)

    # Graceful shutdown handler
    shutdown_event = asyncio.Event()

    def signal_handler(sig, frame):
        logger.info("Shutdown signal received...")
        shutdown_event.set()

    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)

    # Main loop
    try:
        while not shutdown_event.is_set():
            try:
                await strategy.run_iteration()
            except Exception as e:
                logger.error(f"Error in strategy iteration: {e}")
                traceback.print_exc()
                nautilus_multifactor_errors.labels(component='strategy', error_type='iteration').inc()

            # Wait for next iteration
            try:
                await asyncio.wait_for(
                    shutdown_event.wait(),
                    timeout=config.poll_interval_seconds
                )
            except asyncio.TimeoutError:
                pass  # Normal timeout, continue to next iteration

    finally:
        logger.info("Shutting down...")

        # Close any open positions
        for symbol in list(strategy.current_positions.keys()):
            current_price = strategy.data_aggregator.get_last_price(symbol)
            if current_price:
                await strategy._close_position(symbol, current_price, "shutdown")

        # Disconnect from Moomoo
        execution_client.disconnect()

        # Print final metrics
        metrics = strategy.performance_tracker.calculate_metrics()

        print(f"""
    =========================================================================
    FINAL PERFORMANCE SUMMARY
    =========================================================================
    Total Trades: {metrics.get('total_trades', 0)}
    Win Rate: {metrics.get('win_rate', 0)*100:.1f}%
    Total PnL: ${metrics.get('total_pnl', 0):,.2f}
    Sharpe Ratio: {metrics.get('sharpe_ratio', 0):.2f}
    Max Drawdown: {metrics.get('max_drawdown', 0)*100:.1f}%
    Final Portfolio Value: ${strategy.portfolio_value:,.2f}
    =========================================================================
        """)

        logger.info("Shutdown complete")


if __name__ == "__main__":
    asyncio.run(main())
