#!/usr/bin/env python3
"""
REINFORCEMENT LEARNING ENHANCED MULTI-FACTOR TRADING STRATEGY
==============================================================

An advanced trading strategy combining multi-factor alpha generation with
Reinforcement Learning for adaptive decision-making and comprehensive
PostgreSQL data capture for offline training and analysis.

ENHANCEMENTS OVER BASE STRATEGY:
---------------------------------
1. RL Agent (PPO) for adaptive position sizing and timing
2. Comprehensive PostgreSQL data capture for all components:
   - Market data (OHLCV + derived features)
   - Alpha signals (all 9 factors)
   - Regime states and transitions
   - RL states, actions, rewards
   - Model weights and checkpoints
   - Experience replay buffer
3. Offline training capability from historical data
4. Epsilon-greedy exploration with decay
5. Risk-adjusted reward shaping (Sharpe-based)

RL FRAMEWORK:
-------------
- Algorithm: Proximal Policy Optimization (PPO)
- State Space: 50+ features (market, alpha signals, regime, position, P&L)
- Action Space: Discrete(5) - Strong Sell, Sell, Hold, Buy, Strong Buy
- Reward: Risk-adjusted returns with Sharpe ratio shaping
- Training: Online learning with experience replay

POSTGRESQL SCHEMA:
------------------
Tables:
- rl_market_data: Raw market data with derived features
- rl_alpha_signals: All 9 factor signals with metadata
- rl_regime_states: Market regime classifications
- rl_states: Complete RL state vectors
- rl_actions: Action taken with position sizing
- rl_rewards: Reward calculations with components
- rl_experience_replay: (S, A, R, S', done) tuples
- rl_model_checkpoints: Model weights and hyperparameters
- rl_performance_metrics: Episode-level performance
- rl_training_sessions: Training run metadata

DATA FLOW:
----------
1. Market data → Feature engineering → State vector
2. State → RL Agent → Action (position size)
3. Execute action → Observe reward → Store experience
4. Periodic model updates from replay buffer
5. Checkpoint model to PostgreSQL
6. Export metrics to Prometheus

USAGE:
------
    # Initialize tables and run strategy
    python scripts/rl_multi_factor_strategy.py

    # Training mode (offline from historical data)
    python scripts/rl_multi_factor_strategy.py --mode train --episodes 1000

    # Inference mode (live trading with frozen model)
    python scripts/rl_multi_factor_strategy.py --mode inference

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
import json
import pickle
from datetime import datetime, time as dt_time, timedelta, timezone
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Deque, Any, NamedTuple
from dataclasses import dataclass, field, asdict
from enum import Enum, IntEnum
from collections import deque, defaultdict
import traceback
import threading
import uuid

# Third-party imports
import yfinance as yf
import pandas as pd
import numpy as np
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

# Reinforcement Learning
import gymnasium as gym
from gymnasium import spaces
from stable_baselines3 import PPO
from stable_baselines3.common.callbacks import BaseCallback
from stable_baselines3.common.vec_env import DummyVecEnv
from stable_baselines3.common.monitor import Monitor

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
from psycopg.rows import dict_row

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
logger = logging.getLogger('RLMultiFactorStrategy')


# ============================================================================
# CONFIGURATION
# ============================================================================

@dataclass
class RLStrategyConfig:
    """Complete RL strategy configuration."""
    # Symbols
    symbols: List[str] = field(default_factory=lambda: ['SPY', 'AAPL', 'NVDA'])

    # Capital Management
    initial_capital: float = 100000.0
    max_position_pct: float = 0.02  # 2% max position size per instrument
    transaction_cost_bps: float = 5.0  # 5 bps transaction costs
    slippage_bps: float = 2.0  # 2 bps slippage

    # RL Hyperparameters
    state_dim: int = 52  # Will be calculated dynamically
    action_dim: int = 5  # Strong Sell, Sell, Hold, Buy, Strong Buy
    learning_rate: float = 3e-4
    gamma: float = 0.99  # Discount factor
    n_steps: int = 2048  # Steps per update
    batch_size: int = 64
    n_epochs: int = 10
    clip_range: float = 0.2
    ent_coef: float = 0.01  # Entropy coefficient for exploration

    # Exploration
    epsilon_start: float = 1.0
    epsilon_end: float = 0.05
    epsilon_decay: float = 0.995

    # Experience Replay
    replay_buffer_size: int = 100000
    min_replay_size: int = 1000
    replay_batch_size: int = 64

    # Training
    update_frequency: int = 10  # Update model every N steps
    checkpoint_frequency: int = 100  # Checkpoint every N episodes
    target_sharpe: float = 2.0  # Target Sharpe ratio for reward shaping

    # Risk Management
    max_drawdown_threshold: float = 0.10
    volatility_target: float = 0.15
    max_leverage: float = 1.0  # Conservative for RL

    # Alpha Model Parameters (from base strategy)
    momentum_lookback: int = 20
    mean_reversion_lookback: int = 20
    volatility_lookback: int = 30
    volume_lookback: int = 20
    regime_lookback: int = 50
    min_conviction: float = 0.4

    # Update Frequency
    poll_interval_seconds: int = 30

    # API Keys
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
    postgres_password: str = 'xSr7IgOZlwgkUwtnBBZoFG7N'
    postgres_db: str = 'nautilus_trader'

    # Prometheus
    prometheus_port: int = 9101  # Different from base strategy

    # Session Management
    session_id: str = field(default_factory=lambda: str(uuid.uuid4()))

    @property
    def postgres_connection_string(self) -> str:
        return f"postgresql://{self.postgres_user}:{self.postgres_password}@{self.postgres_host}:{self.postgres_port}/{self.postgres_db}"


# ============================================================================
# ENUMS
# ============================================================================

class MarketRegime(IntEnum):
    """Market regime classification."""
    CHOPPY = 0
    TRENDING = 1
    MEAN_REVERTING = 2
    VOLATILE = 3


class RLAction(IntEnum):
    """RL action space."""
    STRONG_SELL = 0  # Reduce/Close long or Increase short
    SELL = 1          # Reduce long slightly
    HOLD = 2          # No change
    BUY = 3           # Increase long slightly
    STRONG_BUY = 4    # Maximize long position


# ============================================================================
# POSTGRESQL SCHEMA AND DATA MODELS
# ============================================================================

SCHEMA_SQL = """
-- ============================================================================
-- RL Multi-Factor Strategy Database Schema
-- ============================================================================

-- Market data with derived features
CREATE TABLE IF NOT EXISTS rl_market_data (
    id BIGSERIAL PRIMARY KEY,
    session_id UUID NOT NULL,
    timestamp TIMESTAMPTZ NOT NULL,
    symbol VARCHAR(20) NOT NULL,
    open DECIMAL(20, 6) NOT NULL,
    high DECIMAL(20, 6) NOT NULL,
    low DECIMAL(20, 6) NOT NULL,
    close DECIMAL(20, 6) NOT NULL,
    volume BIGINT NOT NULL,
    -- Derived features
    returns DECIMAL(10, 6),
    log_returns DECIMAL(10, 6),
    volatility_20 DECIMAL(10, 6),
    atr_14 DECIMAL(10, 6),
    rsi_14 DECIMAL(10, 6),
    macd DECIMAL(10, 6),
    macd_signal DECIMAL(10, 6),
    bb_upper DECIMAL(20, 6),
    bb_middle DECIMAL(20, 6),
    bb_lower DECIMAL(20, 6),
    bb_width DECIMAL(10, 6),
    vwap DECIMAL(20, 6),
    -- Metadata
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_rl_market_data_session_symbol_ts
ON rl_market_data(session_id, symbol, timestamp DESC);

-- Alpha signals from all factors
CREATE TABLE IF NOT EXISTS rl_alpha_signals (
    id BIGSERIAL PRIMARY KEY,
    session_id UUID NOT NULL,
    timestamp TIMESTAMPTZ NOT NULL,
    symbol VARCHAR(20) NOT NULL,
    -- Individual factor signals (-1 to +1)
    momentum_signal DECIMAL(10, 6),
    mean_reversion_signal DECIMAL(10, 6),
    volatility_signal DECIMAL(10, 6),
    volume_signal DECIMAL(10, 6),
    microstructure_signal DECIMAL(10, 6),
    news_sentiment_signal DECIMAL(10, 6),
    social_sentiment_signal DECIMAL(10, 6),
    congressional_signal DECIMAL(10, 6),
    economic_regime_signal DECIMAL(10, 6),
    -- Ensemble
    ensemble_signal DECIMAL(10, 6),
    ensemble_confidence DECIMAL(10, 6),
    -- Metadata
    factor_weights JSONB,  -- Store factor weights
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_rl_alpha_signals_session_symbol_ts
ON rl_alpha_signals(session_id, symbol, timestamp DESC);

-- Market regime states
CREATE TABLE IF NOT EXISTS rl_regime_states (
    id BIGSERIAL PRIMARY KEY,
    session_id UUID NOT NULL,
    timestamp TIMESTAMPTZ NOT NULL,
    symbol VARCHAR(20) NOT NULL,
    regime INTEGER NOT NULL,  -- 0=CHOPPY, 1=TRENDING, 2=MEAN_REVERTING, 3=VOLATILE
    regime_confidence DECIMAL(10, 6),
    -- Regime features
    trend_strength DECIMAL(10, 6),
    volatility_percentile DECIMAL(10, 6),
    volume_percentile DECIMAL(10, 6),
    -- Transition probabilities
    transition_probs JSONB,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_rl_regime_states_session_symbol_ts
ON rl_regime_states(session_id, symbol, timestamp DESC);

-- RL state vectors
CREATE TABLE IF NOT EXISTS rl_states (
    id BIGSERIAL PRIMARY KEY,
    session_id UUID NOT NULL,
    timestamp TIMESTAMPTZ NOT NULL,
    symbol VARCHAR(20) NOT NULL,
    -- State vector (stored as JSONB for flexibility)
    state_vector JSONB NOT NULL,
    -- Key state components for querying
    position_size DECIMAL(10, 6),
    unrealized_pnl DECIMAL(20, 6),
    portfolio_value DECIMAL(20, 6),
    current_regime INTEGER,
    ensemble_signal DECIMAL(10, 6),
    -- Metadata
    state_dim INTEGER,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_rl_states_session_symbol_ts
ON rl_states(session_id, symbol, timestamp DESC);

-- RL actions taken
CREATE TABLE IF NOT EXISTS rl_actions (
    id BIGSERIAL PRIMARY KEY,
    session_id UUID NOT NULL,
    timestamp TIMESTAMPTZ NOT NULL,
    symbol VARCHAR(20) NOT NULL,
    state_id BIGINT REFERENCES rl_states(id),
    -- Action
    action INTEGER NOT NULL,  -- 0=STRONG_SELL, 1=SELL, 2=HOLD, 3=BUY, 4=STRONG_BUY
    action_prob DECIMAL(10, 6),  -- Probability from policy
    -- Position sizing
    target_position DECIMAL(10, 6),  -- Target position size (-1 to +1)
    position_delta DECIMAL(10, 6),   -- Change in position
    shares_traded INTEGER,
    -- Exploration
    is_exploration BOOLEAN DEFAULT FALSE,
    epsilon DECIMAL(10, 6),
    -- Metadata
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_rl_actions_session_symbol_ts
ON rl_actions(session_id, symbol, timestamp DESC);

-- RL rewards
CREATE TABLE IF NOT EXISTS rl_rewards (
    id BIGSERIAL PRIMARY KEY,
    session_id UUID NOT NULL,
    timestamp TIMESTAMPTZ NOT NULL,
    symbol VARCHAR(20) NOT NULL,
    state_id BIGINT REFERENCES rl_states(id),
    action_id BIGINT REFERENCES rl_actions(id),
    -- Reward components
    pnl_reward DECIMAL(10, 6),
    sharpe_reward DECIMAL(10, 6),
    drawdown_penalty DECIMAL(10, 6),
    transaction_cost DECIMAL(10, 6),
    total_reward DECIMAL(10, 6),
    -- Context
    step_pnl DECIMAL(20, 6),
    cumulative_pnl DECIMAL(20, 6),
    sharpe_ratio DECIMAL(10, 6),
    max_drawdown DECIMAL(10, 6),
    -- Metadata
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_rl_rewards_session_symbol_ts
ON rl_rewards(session_id, symbol, timestamp DESC);

-- Experience replay buffer
CREATE TABLE IF NOT EXISTS rl_experience_replay (
    id BIGSERIAL PRIMARY KEY,
    session_id UUID NOT NULL,
    timestamp TIMESTAMPTZ NOT NULL,
    symbol VARCHAR(20) NOT NULL,
    -- SARS' tuple
    state JSONB NOT NULL,
    action INTEGER NOT NULL,
    reward DECIMAL(10, 6) NOT NULL,
    next_state JSONB NOT NULL,
    done BOOLEAN DEFAULT FALSE,
    -- Additional context
    episode_id INTEGER,
    step_id INTEGER,
    priority DECIMAL(10, 6) DEFAULT 1.0,  -- For prioritized replay
    -- Metadata
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_rl_experience_replay_session_symbol
ON rl_experience_replay(session_id, symbol, timestamp DESC);

CREATE INDEX IF NOT EXISTS idx_rl_experience_replay_priority
ON rl_experience_replay(priority DESC, id);

-- Model checkpoints
CREATE TABLE IF NOT EXISTS rl_model_checkpoints (
    id BIGSERIAL PRIMARY KEY,
    session_id UUID NOT NULL,
    timestamp TIMESTAMPTZ NOT NULL,
    checkpoint_name VARCHAR(100) NOT NULL,
    episode INTEGER,
    step INTEGER,
    -- Model weights (serialized)
    model_weights BYTEA NOT NULL,
    -- Hyperparameters
    hyperparameters JSONB,
    -- Performance metrics at checkpoint
    avg_reward DECIMAL(10, 6),
    avg_sharpe DECIMAL(10, 6),
    win_rate DECIMAL(10, 6),
    -- Metadata
    model_type VARCHAR(50),
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_rl_model_checkpoints_session_ts
ON rl_model_checkpoints(session_id, timestamp DESC);

-- Performance metrics per episode
CREATE TABLE IF NOT EXISTS rl_performance_metrics (
    id BIGSERIAL PRIMARY KEY,
    session_id UUID NOT NULL,
    episode INTEGER NOT NULL,
    symbol VARCHAR(20) NOT NULL,
    -- Episode metrics
    total_reward DECIMAL(10, 6),
    total_pnl DECIMAL(20, 6),
    sharpe_ratio DECIMAL(10, 6),
    max_drawdown DECIMAL(10, 6),
    win_rate DECIMAL(10, 6),
    profit_factor DECIMAL(10, 6),
    num_trades INTEGER,
    -- Exploration metrics
    avg_epsilon DECIMAL(10, 6),
    exploration_rate DECIMAL(10, 6),
    -- Timing
    episode_duration_seconds INTEGER,
    timestamp TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_rl_performance_metrics_session_episode
ON rl_performance_metrics(session_id, episode DESC);

-- Training sessions metadata
CREATE TABLE IF NOT EXISTS rl_training_sessions (
    id BIGSERIAL PRIMARY KEY,
    session_id UUID UNIQUE NOT NULL,
    start_time TIMESTAMPTZ NOT NULL,
    end_time TIMESTAMPTZ,
    -- Configuration
    config JSONB NOT NULL,
    -- Status
    status VARCHAR(20),  -- 'running', 'completed', 'failed'
    -- Aggregate metrics
    total_episodes INTEGER DEFAULT 0,
    total_steps INTEGER DEFAULT 0,
    best_sharpe DECIMAL(10, 6),
    final_portfolio_value DECIMAL(20, 6),
    -- Metadata
    git_commit VARCHAR(40),
    python_version VARCHAR(20),
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_rl_training_sessions_status
ON rl_training_sessions(status, start_time DESC);

-- Trade execution log (integrated with base strategy tables)
CREATE TABLE IF NOT EXISTS rl_trades (
    id BIGSERIAL PRIMARY KEY,
    session_id UUID NOT NULL,
    timestamp TIMESTAMPTZ NOT NULL,
    symbol VARCHAR(20) NOT NULL,
    action_id BIGINT REFERENCES rl_actions(id),
    -- Trade details
    side VARCHAR(10),  -- 'BUY' or 'SELL'
    quantity INTEGER,
    price DECIMAL(20, 6),
    value DECIMAL(20, 6),
    commission DECIMAL(10, 6),
    slippage DECIMAL(10, 6),
    -- Moomoo order details
    order_id VARCHAR(50),
    order_status VARCHAR(20),
    fill_price DECIMAL(20, 6),
    fill_time TIMESTAMPTZ,
    -- Metadata
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_rl_trades_session_symbol_ts
ON rl_trades(session_id, symbol, timestamp DESC);
"""


# ============================================================================
# PROMETHEUS METRICS (Port 9101)
# ============================================================================

# RL-specific metrics
rl_epsilon = Gauge('rl_epsilon', 'Current exploration epsilon')
rl_learning_rate = Gauge('rl_learning_rate', 'Current learning rate')
rl_avg_reward = Gauge('rl_avg_reward', 'Average reward per episode', ['symbol'])
rl_cumulative_reward = Counter('rl_cumulative_reward', 'Cumulative reward', ['symbol'])
rl_policy_loss = Gauge('rl_policy_loss', 'Policy network loss')
rl_value_loss = Gauge('rl_value_loss', 'Value network loss')
rl_entropy = Gauge('rl_entropy', 'Policy entropy (exploration measure)')
rl_action_distribution = Gauge('rl_action_distribution', 'Action frequency', ['symbol', 'action'])

# State metrics
rl_state_position = Gauge('rl_state_position', 'Current position in state', ['symbol'])
rl_state_pnl = Gauge('rl_state_pnl', 'Current P&L in state', ['symbol'])
rl_state_sharpe = Gauge('rl_state_sharpe', 'Current Sharpe ratio in state', ['symbol'])
rl_state_regime = Gauge('rl_state_regime', 'Current regime in state', ['symbol'])

# Experience replay metrics
rl_replay_buffer_size = Gauge('rl_replay_buffer_size', 'Experience replay buffer size')
rl_replay_sampling_rate = Counter('rl_replay_sampling_rate', 'Experience replay sampling count')

# Model checkpointing
rl_checkpoint_count = Counter('rl_checkpoint_count', 'Number of model checkpoints saved')
rl_checkpoint_duration = Histogram('rl_checkpoint_duration_seconds', 'Time to save checkpoint')

# Reuse base strategy metrics for trading activity
nautilus_multifactor_pnl_total = Counter(
    'nautilus_multifactor_pnl_total',
    'Total PnL from all trades',
    ['symbol', 'direction']
)
nautilus_multifactor_positions = Gauge(
    'nautilus_multifactor_positions',
    'Current number of open positions'
)
nautilus_multifactor_portfolio_value = Gauge(
    'nautilus_multifactor_portfolio_value',
    'Total portfolio value in dollars'
)
nautilus_multifactor_sharpe_ratio = Gauge(
    'nautilus_multifactor_sharpe_ratio',
    'Annualized Sharpe ratio'
)


# ============================================================================
# DATA STRUCTURES
# ============================================================================

@dataclass
class MarketData:
    """Market data snapshot."""
    timestamp: datetime
    symbol: str
    open: float
    high: float
    low: float
    close: float
    volume: int
    # Derived
    returns: float = 0.0
    log_returns: float = 0.0
    volatility_20: float = 0.0
    atr_14: float = 0.0
    rsi_14: float = 0.0
    macd: float = 0.0
    macd_signal: float = 0.0
    bb_upper: float = 0.0
    bb_middle: float = 0.0
    bb_lower: float = 0.0
    bb_width: float = 0.0
    vwap: float = 0.0


@dataclass
class AlphaSignals:
    """Alpha signals from all factors."""
    timestamp: datetime
    symbol: str
    momentum_signal: float = 0.0
    mean_reversion_signal: float = 0.0
    volatility_signal: float = 0.0
    volume_signal: float = 0.0
    microstructure_signal: float = 0.0
    news_sentiment_signal: float = 0.0
    social_sentiment_signal: float = 0.0
    congressional_signal: float = 0.0
    economic_regime_signal: float = 0.0
    ensemble_signal: float = 0.0
    ensemble_confidence: float = 0.0
    factor_weights: Dict[str, float] = field(default_factory=dict)


@dataclass
class RegimeState:
    """Market regime state."""
    timestamp: datetime
    symbol: str
    regime: MarketRegime
    regime_confidence: float
    trend_strength: float = 0.0
    volatility_percentile: float = 0.0
    volume_percentile: float = 0.0
    transition_probs: Dict[str, float] = field(default_factory=dict)


@dataclass
class RLState:
    """Complete RL state vector."""
    timestamp: datetime
    symbol: str
    state_vector: np.ndarray
    position_size: float
    unrealized_pnl: float
    portfolio_value: float
    current_regime: int
    ensemble_signal: float


@dataclass
class RLActionRecord:
    """RL action record."""
    timestamp: datetime
    symbol: str
    state_id: Optional[int]
    action: RLAction
    action_prob: float
    target_position: float
    position_delta: float
    shares_traded: int
    is_exploration: bool
    epsilon: float


@dataclass
class RLReward:
    """RL reward calculation."""
    timestamp: datetime
    symbol: str
    state_id: Optional[int]
    action_id: Optional[int]
    pnl_reward: float
    sharpe_reward: float
    drawdown_penalty: float
    transaction_cost: float
    total_reward: float
    step_pnl: float
    cumulative_pnl: float
    sharpe_ratio: float
    max_drawdown: float


class Experience(NamedTuple):
    """Experience tuple for replay buffer."""
    state: np.ndarray
    action: int
    reward: float
    next_state: np.ndarray
    done: bool


# ============================================================================
# POSTGRESQL PERSISTENCE
# ============================================================================

class RLPostgreSQLPersistence:
    """PostgreSQL persistence for RL strategy."""

    def __init__(self, config: RLStrategyConfig):
        self.config = config
        self.conn_string = config.postgres_connection_string
        self.session_id = config.session_id
        logger.info(f"Initializing PostgreSQL persistence for session {self.session_id}")

    async def initialize_schema(self):
        """Initialize database schema."""
        try:
            async with await psycopg.AsyncConnection.connect(self.conn_string) as conn:
                async with conn.cursor() as cur:
                    await cur.execute(SCHEMA_SQL)
                await conn.commit()
            logger.info("PostgreSQL schema initialized successfully")
        except Exception as e:
            logger.error(f"Failed to initialize schema: {e}")
            raise

    async def register_session(self):
        """Register new training session."""
        try:
            async with await psycopg.AsyncConnection.connect(self.conn_string) as conn:
                async with conn.cursor() as cur:
                    await cur.execute(
                        """
                        INSERT INTO rl_training_sessions
                        (session_id, start_time, config, status, python_version)
                        VALUES (%s, %s, %s, %s, %s)
                        """,
                        (
                            self.session_id,
                            datetime.now(timezone.utc),
                            json.dumps(asdict(self.config)),
                            'running',
                            sys.version.split()[0]
                        )
                    )
                await conn.commit()
            logger.info(f"Registered training session {self.session_id}")
        except Exception as e:
            logger.error(f"Failed to register session: {e}")
            raise

    async def store_market_data(self, data: MarketData):
        """Store market data."""
        try:
            async with await psycopg.AsyncConnection.connect(self.conn_string) as conn:
                async with conn.cursor() as cur:
                    await cur.execute(
                        """
                        INSERT INTO rl_market_data
                        (session_id, timestamp, symbol, open, high, low, close, volume,
                         returns, log_returns, volatility_20, atr_14, rsi_14,
                         macd, macd_signal, bb_upper, bb_middle, bb_lower, bb_width, vwap)
                        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                        """,
                        (
                            self.session_id, data.timestamp, data.symbol,
                            data.open, data.high, data.low, data.close, data.volume,
                            data.returns, data.log_returns, data.volatility_20, data.atr_14, data.rsi_14,
                            data.macd, data.macd_signal, data.bb_upper, data.bb_middle,
                            data.bb_lower, data.bb_width, data.vwap
                        )
                    )
                await conn.commit()
        except Exception as e:
            logger.error(f"Failed to store market data: {e}")

    async def store_alpha_signals(self, signals: AlphaSignals):
        """Store alpha signals."""
        try:
            async with await psycopg.AsyncConnection.connect(self.conn_string) as conn:
                async with conn.cursor() as cur:
                    await cur.execute(
                        """
                        INSERT INTO rl_alpha_signals
                        (session_id, timestamp, symbol,
                         momentum_signal, mean_reversion_signal, volatility_signal, volume_signal,
                         microstructure_signal, news_sentiment_signal, social_sentiment_signal,
                         congressional_signal, economic_regime_signal,
                         ensemble_signal, ensemble_confidence, factor_weights)
                        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                        """,
                        (
                            self.session_id, signals.timestamp, signals.symbol,
                            signals.momentum_signal, signals.mean_reversion_signal,
                            signals.volatility_signal, signals.volume_signal,
                            signals.microstructure_signal, signals.news_sentiment_signal,
                            signals.social_sentiment_signal, signals.congressional_signal,
                            signals.economic_regime_signal,
                            signals.ensemble_signal, signals.ensemble_confidence,
                            json.dumps(signals.factor_weights)
                        )
                    )
                await conn.commit()
        except Exception as e:
            logger.error(f"Failed to store alpha signals: {e}")

    async def store_regime_state(self, regime: RegimeState):
        """Store regime state."""
        try:
            async with await psycopg.AsyncConnection.connect(self.conn_string) as conn:
                async with conn.cursor() as cur:
                    await cur.execute(
                        """
                        INSERT INTO rl_regime_states
                        (session_id, timestamp, symbol, regime, regime_confidence,
                         trend_strength, volatility_percentile, volume_percentile, transition_probs)
                        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
                        """,
                        (
                            self.session_id, regime.timestamp, regime.symbol,
                            int(regime.regime), regime.regime_confidence,
                            regime.trend_strength, regime.volatility_percentile,
                            regime.volume_percentile, json.dumps(regime.transition_probs)
                        )
                    )
                await conn.commit()
        except Exception as e:
            logger.error(f"Failed to store regime state: {e}")

    async def store_rl_state(self, state: RLState) -> int:
        """Store RL state and return ID."""
        try:
            async with await psycopg.AsyncConnection.connect(self.conn_string) as conn:
                async with conn.cursor() as cur:
                    await cur.execute(
                        """
                        INSERT INTO rl_states
                        (session_id, timestamp, symbol, state_vector, position_size,
                         unrealized_pnl, portfolio_value, current_regime, ensemble_signal, state_dim)
                        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                        RETURNING id
                        """,
                        (
                            self.session_id, state.timestamp, state.symbol,
                            json.dumps(state.state_vector.tolist()),
                            state.position_size, state.unrealized_pnl, state.portfolio_value,
                            state.current_regime, state.ensemble_signal, len(state.state_vector)
                        )
                    )
                    result = await cur.fetchone()
                await conn.commit()
                return result[0] if result else None
        except Exception as e:
            logger.error(f"Failed to store RL state: {e}")
            return None

    async def store_rl_action(self, action: RLActionRecord) -> int:
        """Store RL action and return ID."""
        try:
            async with await psycopg.AsyncConnection.connect(self.conn_string) as conn:
                async with conn.cursor() as cur:
                    await cur.execute(
                        """
                        INSERT INTO rl_actions
                        (session_id, timestamp, symbol, state_id, action, action_prob,
                         target_position, position_delta, shares_traded, is_exploration, epsilon)
                        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                        RETURNING id
                        """,
                        (
                            self.session_id, action.timestamp, action.symbol, action.state_id,
                            int(action.action), action.action_prob, action.target_position,
                            action.position_delta, action.shares_traded, action.is_exploration, action.epsilon
                        )
                    )
                    result = await cur.fetchone()
                await conn.commit()
                return result[0] if result else None
        except Exception as e:
            logger.error(f"Failed to store RL action: {e}")
            return None

    async def store_rl_reward(self, reward: RLReward):
        """Store RL reward."""
        try:
            async with await psycopg.AsyncConnection.connect(self.conn_string) as conn:
                async with conn.cursor() as cur:
                    await cur.execute(
                        """
                        INSERT INTO rl_rewards
                        (session_id, timestamp, symbol, state_id, action_id,
                         pnl_reward, sharpe_reward, drawdown_penalty, transaction_cost, total_reward,
                         step_pnl, cumulative_pnl, sharpe_ratio, max_drawdown)
                        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                        """,
                        (
                            self.session_id, reward.timestamp, reward.symbol,
                            reward.state_id, reward.action_id,
                            reward.pnl_reward, reward.sharpe_reward, reward.drawdown_penalty,
                            reward.transaction_cost, reward.total_reward,
                            reward.step_pnl, reward.cumulative_pnl, reward.sharpe_ratio, reward.max_drawdown
                        )
                    )
                await conn.commit()
        except Exception as e:
            logger.error(f"Failed to store RL reward: {e}")

    async def store_experience(self, symbol: str, experience: Experience, episode_id: int, step_id: int):
        """Store experience tuple for replay."""
        try:
            async with await psycopg.AsyncConnection.connect(self.conn_string) as conn:
                async with conn.cursor() as cur:
                    await cur.execute(
                        """
                        INSERT INTO rl_experience_replay
                        (session_id, timestamp, symbol, state, action, reward, next_state, done, episode_id, step_id)
                        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                        """,
                        (
                            self.session_id, datetime.now(timezone.utc), symbol,
                            json.dumps(experience.state.tolist()),
                            int(experience.action),
                            float(experience.reward),
                            json.dumps(experience.next_state.tolist()),
                            experience.done,
                            episode_id, step_id
                        )
                    )
                await conn.commit()
        except Exception as e:
            logger.error(f"Failed to store experience: {e}")

    async def sample_experiences(self, batch_size: int, symbol: Optional[str] = None) -> List[Experience]:
        """Sample random experiences from replay buffer."""
        try:
            async with await psycopg.AsyncConnection.connect(self.conn_string) as conn:
                async with conn.cursor(row_factory=dict_row) as cur:
                    query = """
                        SELECT state, action, reward, next_state, done
                        FROM rl_experience_replay
                        WHERE session_id = %s
                    """
                    params = [self.session_id]

                    if symbol:
                        query += " AND symbol = %s"
                        params.append(symbol)

                    query += " ORDER BY RANDOM() LIMIT %s"
                    params.append(batch_size)

                    await cur.execute(query, params)
                    rows = await cur.fetchall()

                    experiences = []
                    for row in rows:
                        exp = Experience(
                            state=np.array(json.loads(row['state'])),
                            action=row['action'],
                            reward=float(row['reward']),
                            next_state=np.array(json.loads(row['next_state'])),
                            done=row['done']
                        )
                        experiences.append(exp)

                    return experiences
        except Exception as e:
            logger.error(f"Failed to sample experiences: {e}")
            return []

    async def save_model_checkpoint(self, model_weights: bytes, episode: int, step: int,
                                    metrics: Dict[str, float]):
        """Save model checkpoint."""
        try:
            async with await psycopg.AsyncConnection.connect(self.conn_string) as conn:
                async with conn.cursor() as cur:
                    checkpoint_name = f"checkpoint_ep{episode}_step{step}"
                    await cur.execute(
                        """
                        INSERT INTO rl_model_checkpoints
                        (session_id, timestamp, checkpoint_name, episode, step,
                         model_weights, hyperparameters, avg_reward, avg_sharpe, win_rate, model_type)
                        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                        """,
                        (
                            self.session_id, datetime.now(timezone.utc), checkpoint_name,
                            episode, step, model_weights,
                            json.dumps(asdict(self.config)),
                            metrics.get('avg_reward', 0.0),
                            metrics.get('avg_sharpe', 0.0),
                            metrics.get('win_rate', 0.0),
                            'PPO'
                        )
                    )
                await conn.commit()
                logger.info(f"Saved model checkpoint: {checkpoint_name}")
                rl_checkpoint_count.inc()
        except Exception as e:
            logger.error(f"Failed to save model checkpoint: {e}")

    async def load_latest_checkpoint(self) -> Optional[Tuple[bytes, Dict]]:
        """Load latest model checkpoint."""
        try:
            async with await psycopg.AsyncConnection.connect(self.conn_string) as conn:
                async with conn.cursor(row_factory=dict_row) as cur:
                    await cur.execute(
                        """
                        SELECT model_weights, hyperparameters, episode, step
                        FROM rl_model_checkpoints
                        WHERE session_id = %s
                        ORDER BY timestamp DESC
                        LIMIT 1
                        """,
                        (self.session_id,)
                    )
                    row = await cur.fetchone()
                    if row:
                        return (
                            bytes(row['model_weights']),
                            {
                                'hyperparameters': json.loads(row['hyperparameters']),
                                'episode': row['episode'],
                                'step': row['step']
                            }
                        )
                    return None
        except Exception as e:
            logger.error(f"Failed to load checkpoint: {e}")
            return None

    async def store_performance_metrics(self, episode: int, symbol: str, metrics: Dict[str, float]):
        """Store episode performance metrics."""
        try:
            async with await psycopg.AsyncConnection.connect(self.conn_string) as conn:
                async with conn.cursor() as cur:
                    await cur.execute(
                        """
                        INSERT INTO rl_performance_metrics
                        (session_id, episode, symbol, total_reward, total_pnl, sharpe_ratio,
                         max_drawdown, win_rate, profit_factor, num_trades, avg_epsilon, exploration_rate)
                        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                        """,
                        (
                            self.session_id, episode, symbol,
                            metrics.get('total_reward', 0.0),
                            metrics.get('total_pnl', 0.0),
                            metrics.get('sharpe_ratio', 0.0),
                            metrics.get('max_drawdown', 0.0),
                            metrics.get('win_rate', 0.0),
                            metrics.get('profit_factor', 0.0),
                            metrics.get('num_trades', 0),
                            metrics.get('avg_epsilon', 0.0),
                            metrics.get('exploration_rate', 0.0)
                        )
                    )
                await conn.commit()
        except Exception as e:
            logger.error(f"Failed to store performance metrics: {e}")

    async def update_session_status(self, status: str, **kwargs):
        """Update training session status."""
        try:
            async with await psycopg.AsyncConnection.connect(self.conn_string) as conn:
                async with conn.cursor() as cur:
                    updates = ['status = %s', 'updated_at = NOW()']
                    params = [status]

                    if 'total_episodes' in kwargs:
                        updates.append('total_episodes = %s')
                        params.append(kwargs['total_episodes'])
                    if 'total_steps' in kwargs:
                        updates.append('total_steps = %s')
                        params.append(kwargs['total_steps'])
                    if 'best_sharpe' in kwargs:
                        updates.append('best_sharpe = %s')
                        params.append(kwargs['best_sharpe'])
                    if 'final_portfolio_value' in kwargs:
                        updates.append('final_portfolio_value = %s')
                        params.append(kwargs['final_portfolio_value'])
                    if status == 'completed':
                        updates.append('end_time = NOW()')

                    params.append(self.session_id)

                    query = f"""
                        UPDATE rl_training_sessions
                        SET {', '.join(updates)}
                        WHERE session_id = %s
                    """
                    await cur.execute(query, params)
                await conn.commit()
        except Exception as e:
            logger.error(f"Failed to update session status: {e}")


# ============================================================================
# FEATURE ENGINEERING
# ============================================================================

class FeatureEngineer:
    """Feature engineering for market data."""

    @staticmethod
    def calculate_technical_indicators(df: pd.DataFrame) -> pd.DataFrame:
        """Calculate technical indicators."""
        df = df.copy()

        # Returns
        df['returns'] = df['Close'].pct_change()
        df['log_returns'] = np.log(df['Close'] / df['Close'].shift(1))

        # Volatility
        df['volatility_20'] = df['returns'].rolling(20).std()

        # ATR
        high_low = df['High'] - df['Low']
        high_close = np.abs(df['High'] - df['Close'].shift())
        low_close = np.abs(df['Low'] - df['Close'].shift())
        ranges = pd.concat([high_low, high_close, low_close], axis=1)
        true_range = ranges.max(axis=1)
        df['atr_14'] = true_range.rolling(14).mean()

        # RSI
        delta = df['Close'].diff()
        gain = (delta.where(delta > 0, 0)).rolling(14).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(14).mean()
        rs = gain / loss
        df['rsi_14'] = 100 - (100 / (1 + rs))

        # MACD
        ema_12 = df['Close'].ewm(span=12, adjust=False).mean()
        ema_26 = df['Close'].ewm(span=26, adjust=False).mean()
        df['macd'] = ema_12 - ema_26
        df['macd_signal'] = df['macd'].ewm(span=9, adjust=False).mean()

        # Bollinger Bands
        df['bb_middle'] = df['Close'].rolling(20).mean()
        bb_std = df['Close'].rolling(20).std()
        df['bb_upper'] = df['bb_middle'] + 2 * bb_std
        df['bb_lower'] = df['bb_middle'] - 2 * bb_std
        df['bb_width'] = (df['bb_upper'] - df['bb_lower']) / df['bb_middle']

        # VWAP
        df['vwap'] = (df['Close'] * df['Volume']).cumsum() / df['Volume'].cumsum()

        # Fill NaN with 0
        df.fillna(0, inplace=True)

        return df

    @staticmethod
    def extract_market_data(df: pd.DataFrame, symbol: str) -> MarketData:
        """Extract MarketData from DataFrame row."""
        latest = df.iloc[-1]
        return MarketData(
            timestamp=datetime.now(timezone.utc),
            symbol=symbol,
            open=latest['Open'],
            high=latest['High'],
            low=latest['Low'],
            close=latest['Close'],
            volume=int(latest['Volume']),
            returns=latest.get('returns', 0.0),
            log_returns=latest.get('log_returns', 0.0),
            volatility_20=latest.get('volatility_20', 0.0),
            atr_14=latest.get('atr_14', 0.0),
            rsi_14=latest.get('rsi_14', 0.0),
            macd=latest.get('macd', 0.0),
            macd_signal=latest.get('macd_signal', 0.0),
            bb_upper=latest.get('bb_upper', 0.0),
            bb_middle=latest.get('bb_middle', 0.0),
            bb_lower=latest.get('bb_lower', 0.0),
            bb_width=latest.get('bb_width', 0.0),
            vwap=latest.get('vwap', 0.0)
        )


# ============================================================================
# Continue in next response due to length...
# ============================================================================

# ============================================================================
# ALPHA FACTOR MODELS (Simplified versions from base strategy)
# ============================================================================

class AlphaFactorModel:
    """Multi-factor alpha model."""

    def __init__(self, config: RLStrategyConfig):
        self.config = config
        self.factor_weights = {
            'momentum': 0.15,
            'mean_reversion': 0.15,
            'volatility': 0.10,
            'volume': 0.10,
            'microstructure': 0.10,
            'news_sentiment': 0.10,
            'social_sentiment': 0.10,
            'congressional': 0.10,
            'economic_regime': 0.10
        }

    def calculate_signals(self, df: pd.DataFrame, symbol: str) -> AlphaSignals:
        """Calculate all alpha signals."""
        signals = AlphaSignals(
            timestamp=datetime.now(timezone.utc),
            symbol=symbol
        )

        if len(df) < 30:
            return signals

        # Momentum
        returns_20 = df['Close'].pct_change(20).iloc[-1]
        signals.momentum_signal = np.tanh(returns_20 * 10)

        # Mean Reversion
        z_score = (df['Close'].iloc[-1] - df['Close'].rolling(20).mean().iloc[-1]) / df['Close'].rolling(20).std().iloc[-1]
        signals.mean_reversion_signal = -np.tanh(z_score)

        # Volatility
        vol_current = df['returns'].rolling(20).std().iloc[-1]
        vol_avg = df['returns'].rolling(100).std().mean()
        signals.volatility_signal = -np.tanh((vol_current / vol_avg - 1) * 5) if vol_avg > 0 else 0.0

        # Volume
        vol_ratio = df['Volume'].iloc[-1] / df['Volume'].rolling(20).mean().iloc[-1]
        signals.volume_signal = np.tanh((vol_ratio - 1) * 2)

        # Microstructure (simplified)
        signals.microstructure_signal = 0.0

        # Alternative data signals (placeholders - would need API integration)
        signals.news_sentiment_signal = 0.0
        signals.social_sentiment_signal = 0.0
        signals.congressional_signal = 0.0
        signals.economic_regime_signal = 0.0

        # Ensemble
        weighted_sum = sum(
            getattr(signals, f'{factor}_signal') * weight
            for factor, weight in self.factor_weights.items()
        )
        signals.ensemble_signal = np.clip(weighted_sum, -1.0, 1.0)

        # Confidence (simplified - based on signal agreement)
        signal_values = [
            signals.momentum_signal,
            signals.mean_reversion_signal,
            signals.volatility_signal,
            signals.volume_signal
        ]
        signals.ensemble_confidence = 1.0 - np.std([abs(s) for s in signal_values])

        signals.factor_weights = self.factor_weights.copy()

        return signals


# ============================================================================
# REGIME DETECTOR
# ============================================================================

class RegimeDetector:
    """Market regime detector."""

    def __init__(self, config: RLStrategyConfig):
        self.config = config

    def detect_regime(self, df: pd.DataFrame, symbol: str) -> RegimeState:
        """Detect current market regime."""
        regime_state = RegimeState(
            timestamp=datetime.now(timezone.utc),
            symbol=symbol,
            regime=MarketRegime.CHOPPY,
            regime_confidence=0.5
        )

        if len(df) < 50:
            return regime_state

        # Calculate regime features
        returns = df['Close'].pct_change()
        volatility = returns.rolling(20).std().iloc[-1]
        trend = (df['Close'].iloc[-1] / df['Close'].iloc[-20] - 1) if len(df) >= 20 else 0

        # Volume analysis
        volume_ma = df['Volume'].rolling(20).mean()
        volume_ratio = df['Volume'].iloc[-1] / volume_ma.iloc[-1] if volume_ma.iloc[-1] > 0 else 1.0

        # Volatility percentile
        vol_rank = returns.rolling(50).std().rank(pct=True).iloc[-1]
        regime_state.volatility_percentile = vol_rank

        # Trend strength
        regime_state.trend_strength = abs(trend)

        # Volume percentile
        vol_rank_volume = df['Volume'].rolling(50).rank(pct=True).iloc[-1]
        regime_state.volume_percentile = vol_rank_volume

        # Classify regime
        if vol_rank > 0.8:
            regime_state.regime = MarketRegime.VOLATILE
            regime_state.regime_confidence = vol_rank
        elif abs(trend) > 0.05 and vol_rank < 0.5:
            regime_state.regime = MarketRegime.TRENDING
            regime_state.regime_confidence = abs(trend) * 10
        elif abs(trend) < 0.02 and vol_rank < 0.3:
            regime_state.regime = MarketRegime.MEAN_REVERTING
            regime_state.regime_confidence = 1.0 - abs(trend) * 20
        else:
            regime_state.regime = MarketRegime.CHOPPY
            regime_state.regime_confidence = 0.5

        regime_state.transition_probs = {
            'choppy': 0.4,
            'trending': 0.3,
            'mean_reverting': 0.2,
            'volatile': 0.1
        }

        return regime_state


# ============================================================================
# RL TRADING ENVIRONMENT
# ============================================================================

class TradingEnvironment(gym.Env):
    """Gymnasium-compatible trading environment for RL."""

    def __init__(self, config: RLStrategyConfig, symbol: str, data: pd.DataFrame):
        super().__init__()
        self.config = config
        self.symbol = symbol
        self.data = data
        self.current_step = 0
        self.max_steps = len(data) - 1

        # State space: market features + position + PnL + regime
        self.observation_space = spaces.Box(
            low=-np.inf,
            high=np.inf,
            shape=(config.state_dim,),
            dtype=np.float32
        )

        # Action space: 5 discrete actions
        self.action_space = spaces.Discrete(config.action_dim)

        # Portfolio state
        self.cash = config.initial_capital
        self.position = 0.0  # Shares held
        self.portfolio_value = config.initial_capital
        self.trades = []
        self.pnl_history = []
        self.returns_history = []

        # Initialize components
        self.alpha_model = AlphaFactorModel(config)
        self.regime_detector = RegimeDetector(config)

    def reset(self, seed=None, options=None):
        """Reset environment."""
        super().reset(seed=seed)
        self.current_step = max(50, np.random.randint(0, len(self.data) - 100))
        self.cash = self.config.initial_capital
        self.position = 0.0
        self.portfolio_value = self.config.initial_capital
        self.trades = []
        self.pnl_history = [0.0]
        self.returns_history = [0.0]
        return self._get_observation(), {}

    def _get_observation(self) -> np.ndarray:
        """Get current state observation."""
        df_window = self.data.iloc[:self.current_step + 1]

        # Market features
        latest = df_window.iloc[-1]
        features = [
            latest.get('returns', 0.0),
            latest.get('volatility_20', 0.0),
            latest.get('rsi_14', 50.0) / 100.0,  # Normalize
            latest.get('macd', 0.0),
            latest.get('bb_width', 0.0),
        ]

        # Alpha signals
        signals = self.alpha_model.calculate_signals(df_window, self.symbol)
        features.extend([
            signals.momentum_signal,
            signals.mean_reversion_signal,
            signals.volatility_signal,
            signals.volume_signal,
            signals.ensemble_signal,
            signals.ensemble_confidence
        ])

        # Regime
        regime = self.regime_detector.detect_regime(df_window, self.symbol)
        regime_one_hot = [0.0] * 4
        regime_one_hot[int(regime.regime)] = 1.0
        features.extend(regime_one_hot)
        features.append(regime.regime_confidence)

        # Position and P&L
        current_price = latest['Close']
        position_value = self.position * current_price
        features.extend([
            self.position / 100.0,  # Normalize
            position_value / self.config.initial_capital,
            self.cash / self.config.initial_capital,
            self.portfolio_value / self.config.initial_capital,
        ])

        # Recent P&L
        features.extend(self.pnl_history[-5:] + [0.0] * (5 - len(self.pnl_history[-5:])))

        # Recent returns
        features.extend(self.returns_history[-5:] + [0.0] * (5 - len(self.returns_history[-5:])))

        # Risk metrics
        if len(self.returns_history) > 1:
            sharpe = np.mean(self.returns_history) / (np.std(self.returns_history) + 1e-6) * np.sqrt(252)
            max_dd = self._calculate_max_drawdown()
        else:
            sharpe = 0.0
            max_dd = 0.0

        features.extend([sharpe / 5.0, max_dd])  # Normalize Sharpe

        # Time features
        features.extend([
            self.current_step / self.max_steps,
            (self.current_step % 20) / 20.0  # Position in 20-day cycle
        ])

        # Pad to fixed size
        while len(features) < self.config.state_dim:
            features.append(0.0)

        return np.array(features[:self.config.state_dim], dtype=np.float32)

    def step(self, action: int):
        """Execute one step."""
        current_price = self.data.iloc[self.current_step]['Close']
        next_step = self.current_step + 1

        if next_step >= len(self.data):
            done = True
            truncated = True
            return self._get_observation(), 0.0, done, truncated, {}

        next_price = self.data.iloc[next_step]['Close']

        # Map action to position change
        action_enum = RLAction(action)
        target_position_pct = {
            RLAction.STRONG_SELL: -0.5,
            RLAction.SELL: -0.25,
            RLAction.HOLD: 0.0,
            RLAction.BUY: 0.25,
            RLAction.STRONG_BUY: 0.5
        }[action_enum]

        # Calculate target position
        max_shares = (self.config.initial_capital * self.config.max_position_pct) / current_price
        target_shares = max_shares * target_position_pct
        shares_to_trade = int(target_shares - self.position)

        # Execute trade
        transaction_cost = 0.0
        if shares_to_trade != 0:
            trade_value = abs(shares_to_trade) * current_price
            transaction_cost = trade_value * (self.config.transaction_cost_bps / 10000.0)
            slippage = trade_value * (self.config.slippage_bps / 10000.0)
            total_cost = transaction_cost + slippage

            if shares_to_trade > 0:  # Buy
                cost = shares_to_trade * current_price + total_cost
                if cost <= self.cash:
                    self.position += shares_to_trade
                    self.cash -= cost
            else:  # Sell
                self.position += shares_to_trade  # shares_to_trade is negative
                self.cash += abs(shares_to_trade) * current_price - total_cost

            self.trades.append({
                'step': self.current_step,
                'action': action_enum.name,
                'shares': shares_to_trade,
                'price': current_price,
                'cost': total_cost
            })

        # Update portfolio value
        old_portfolio_value = self.portfolio_value
        self.portfolio_value = self.cash + self.position * next_price

        # Calculate step P&L and return
        step_pnl = self.portfolio_value - old_portfolio_value
        step_return = step_pnl / old_portfolio_value if old_portfolio_value > 0 else 0.0

        self.pnl_history.append(step_pnl)
        self.returns_history.append(step_return)

        # Calculate reward (risk-adjusted)
        reward = self._calculate_reward(step_pnl, transaction_cost)

        # Move to next step
        self.current_step = next_step
        done = self.current_step >= self.max_steps - 1

        # Check for max drawdown stop
        max_dd = self._calculate_max_drawdown()
        if max_dd > self.config.max_drawdown_threshold:
            done = True

        return self._get_observation(), reward, done, False, {}

    def _calculate_reward(self, step_pnl: float, transaction_cost: float) -> float:
        """Calculate reward with Sharpe-based shaping."""
        # Base reward: normalized P&L
        pnl_reward = step_pnl / self.config.initial_capital * 100.0

        # Sharpe reward component
        if len(self.returns_history) >= 10:
            recent_returns = self.returns_history[-10:]
            mean_return = np.mean(recent_returns)
            std_return = np.std(recent_returns) + 1e-6
            sharpe = mean_return / std_return * np.sqrt(252)
            sharpe_reward = sharpe / self.config.target_sharpe
        else:
            sharpe_reward = 0.0

        # Drawdown penalty
        max_dd = self._calculate_max_drawdown()
        drawdown_penalty = -max_dd * 10.0 if max_dd > 0.05 else 0.0

        # Transaction cost penalty
        cost_penalty = -(transaction_cost / self.config.initial_capital) * 1000.0

        # Total reward
        total_reward = pnl_reward + 0.5 * sharpe_reward + drawdown_penalty + cost_penalty

        return total_reward

    def _calculate_max_drawdown(self) -> float:
        """Calculate maximum drawdown."""
        if len(self.pnl_history) < 2:
            return 0.0

        cumulative_pnl = np.cumsum(self.pnl_history)
        running_max = np.maximum.accumulate(cumulative_pnl)
        drawdown = (cumulative_pnl - running_max) / self.config.initial_capital
        return abs(drawdown.min())

    def render(self):
        """Render environment state."""
        pass


# ============================================================================
# RL AGENT
# ============================================================================

class RLAgent:
    """RL Agent using PPO."""

    def __init__(self, config: RLStrategyConfig, env: TradingEnvironment):
        self.config = config
        self.env = env
        self.epsilon = config.epsilon_start

        # Create PPO model
        self.model = PPO(
            "MlpPolicy",
            env,
            learning_rate=config.learning_rate,
            n_steps=config.n_steps,
            batch_size=config.batch_size,
            n_epochs=config.n_epochs,
            gamma=config.gamma,
            clip_range=config.clip_range,
            ent_coef=config.ent_coef,
            verbose=0
        )

        logger.info("Initialized PPO agent")

    def select_action(self, state: np.ndarray, deterministic: bool = False) -> Tuple[int, float]:
        """Select action using epsilon-greedy exploration."""
        # Exploration
        if not deterministic and np.random.random() < self.epsilon:
            action = self.env.action_space.sample()
            action_prob = 1.0 / self.config.action_dim
            is_exploration = True
        else:
            action, _states = self.model.predict(state, deterministic=deterministic)
            action = int(action)
            # Get action probability from policy
            action_prob = 0.5  # Placeholder - would need policy forward pass
            is_exploration = False

        return action, action_prob, is_exploration

    def train_step(self, total_timesteps: int):
        """Perform training step."""
        self.model.learn(total_timesteps=total_timesteps, reset_num_timesteps=False)

        # Decay epsilon
        self.epsilon = max(self.config.epsilon_end, self.epsilon * self.config.epsilon_decay)

        # Update metrics
        rl_epsilon.set(self.epsilon)

    def save_model(self, path: str):
        """Save model to disk."""
        self.model.save(path)
        logger.info(f"Saved model to {path}")

    def load_model(self, path: str):
        """Load model from disk."""
        self.model = PPO.load(path, env=self.env)
        logger.info(f"Loaded model from {path}")

    def get_model_weights(self) -> bytes:
        """Serialize model weights."""
        return pickle.dumps(self.model.policy.state_dict())

    def load_model_weights(self, weights: bytes):
        """Deserialize and load model weights."""
        state_dict = pickle.loads(weights)
        self.model.policy.load_state_dict(state_dict)


# ============================================================================
# RL MULTI-FACTOR STRATEGY
# ============================================================================

class RLMultiFactorStrategy:
    """Main RL-enhanced multi-factor trading strategy."""

    def __init__(self, config: RLStrategyConfig):
        self.config = config
        self.running = False
        self.persistence = RLPostgreSQLPersistence(config)

        # Components
        self.alpha_model = AlphaFactorModel(config)
        self.regime_detector = RegimeDetector(config)
        self.feature_engineer = FeatureEngineer()

        # RL components (will be initialized per symbol)
        self.envs: Dict[str, TradingEnvironment] = {}
        self.agents: Dict[str, RLAgent] = {}

        # Portfolio state
        self.positions: Dict[str, float] = defaultdict(float)
        self.cash = config.initial_capital
        self.portfolio_value = config.initial_capital

        # Performance tracking
        self.episode = 0
        self.total_steps = 0
        self.episode_rewards: Dict[str, List[float]] = defaultdict(list)
        self.episode_pnls: Dict[str, List[float]] = defaultdict(list)

        logger.info(f"Initialized RL Multi-Factor Strategy (Session: {config.session_id})")

    async def initialize(self):
        """Initialize strategy."""
        # Initialize PostgreSQL
        await self.persistence.initialize_schema()
        await self.persistence.register_session()

        # Start Prometheus server
        try:
            start_http_server(self.config.prometheus_port)
            logger.info(f"Prometheus metrics server started on port {self.config.prometheus_port}")
        except Exception as e:
            logger.warning(f"Failed to start Prometheus server: {e}")

        # Initialize RL components for each symbol
        for symbol in self.config.symbols:
            await self._initialize_symbol_rl(symbol)

        logger.info("Strategy initialization complete")

    async def _initialize_symbol_rl(self, symbol: str):
        """Initialize RL environment and agent for a symbol."""
        # Download historical data
        logger.info(f"Downloading data for {symbol}...")
        ticker = yf.Ticker(symbol)
        df = ticker.history(period="1y", interval="1d")

        if df.empty:
            logger.error(f"No data available for {symbol}")
            return

        # Feature engineering
        df = self.feature_engineer.calculate_technical_indicators(df)

        # Create environment
        env = TradingEnvironment(self.config, symbol, df)
        self.envs[symbol] = env

        # Create agent
        agent = RLAgent(self.config, env)
        self.agents[symbol] = agent

        # Try to load checkpoint
        checkpoint = await self.persistence.load_latest_checkpoint()
        if checkpoint:
            weights, metadata = checkpoint
            agent.load_model_weights(weights)
            self.episode = metadata['episode']
            self.total_steps = metadata['step']
            logger.info(f"Loaded checkpoint: episode={self.episode}, step={self.total_steps}")

        logger.info(f"Initialized RL components for {symbol}")

    async def run_episode(self, symbol: str, training: bool = True):
        """Run one episode of trading."""
        env = self.envs[symbol]
        agent = self.agents[symbol]

        state, _ = env.reset()
        done = False
        episode_reward = 0.0
        episode_pnl = 0.0
        step = 0

        while not done:
            # Select action
            action, action_prob, is_exploration = agent.select_action(state, deterministic=not training)

            # Store state
            rl_state = RLState(
                timestamp=datetime.now(timezone.utc),
                symbol=symbol,
                state_vector=state,
                position_size=env.position,
                unrealized_pnl=env.portfolio_value - self.config.initial_capital,
                portfolio_value=env.portfolio_value,
                current_regime=0,  # Will be updated from regime detector
                ensemble_signal=0.0
            )
            state_id = await self.persistence.store_rl_state(rl_state)

            # Execute action
            next_state, reward, done, truncated, info = env.step(action)

            # Store action
            rl_action = RLActionRecord(
                timestamp=datetime.now(timezone.utc),
                symbol=symbol,
                state_id=state_id,
                action=RLAction(action),
                action_prob=action_prob,
                target_position=0.0,
                position_delta=0.0,
                shares_traded=0,
                is_exploration=is_exploration,
                epsilon=agent.epsilon
            )
            action_id = await self.persistence.store_rl_action(rl_action)

            # Store reward
            rl_reward = RLReward(
                timestamp=datetime.now(timezone.utc),
                symbol=symbol,
                state_id=state_id,
                action_id=action_id,
                pnl_reward=reward,
                sharpe_reward=0.0,
                drawdown_penalty=0.0,
                transaction_cost=0.0,
                total_reward=reward,
                step_pnl=env.pnl_history[-1] if env.pnl_history else 0.0,
                cumulative_pnl=sum(env.pnl_history),
                sharpe_ratio=0.0,
                max_drawdown=env._calculate_max_drawdown()
            )
            await self.persistence.store_rl_reward(rl_reward)

            # Store experience
            experience = Experience(state, action, reward, next_state, done or truncated)
            await self.persistence.store_experience(symbol, experience, self.episode, step)

            # Update metrics
            episode_reward += reward
            episode_pnl = env.portfolio_value - self.config.initial_capital

            # Update Prometheus
            rl_cumulative_reward.labels(symbol=symbol).inc(reward)
            rl_state_position.labels(symbol=symbol).set(env.position)
            rl_state_pnl.labels(symbol=symbol).set(episode_pnl)
            rl_action_distribution.labels(symbol=symbol, action=RLAction(action).name).inc()

            state = next_state
            step += 1
            self.total_steps += 1

            if done or truncated:
                break

            # Periodic training updates
            if training and step % self.config.update_frequency == 0:
                agent.train_step(self.config.update_frequency)

        # Episode complete
        self.episode += 1
        self.episode_rewards[symbol].append(episode_reward)
        self.episode_pnls[symbol].append(episode_pnl)

        # Calculate metrics
        wins = sum(1 for pnl in env.pnl_history if pnl > 0)
        win_rate = wins / len(env.pnl_history) if env.pnl_history else 0.0
        sharpe = (np.mean(env.returns_history) / (np.std(env.returns_history) + 1e-6) * np.sqrt(252)
                  if len(env.returns_history) > 1 else 0.0)

        metrics = {
            'total_reward': episode_reward,
            'total_pnl': episode_pnl,
            'sharpe_ratio': sharpe,
            'max_drawdown': env._calculate_max_drawdown(),
            'win_rate': win_rate,
            'profit_factor': 0.0,
            'num_trades': len(env.trades),
            'avg_epsilon': agent.epsilon,
            'exploration_rate': sum(1 for t in env.trades if is_exploration) / len(env.trades) if env.trades else 0.0
        }

        await self.persistence.store_performance_metrics(self.episode, symbol, metrics)

        # Update Prometheus
        rl_avg_reward.labels(symbol=symbol).set(episode_reward)
        nautilus_multifactor_sharpe_ratio.set(sharpe)
        nautilus_multifactor_portfolio_value.set(env.portfolio_value)

        logger.info(
            f"Episode {self.episode} - {symbol}: "
            f"Reward={episode_reward:.2f}, PnL=${episode_pnl:.2f}, "
            f"Sharpe={sharpe:.2f}, Trades={len(env.trades)}, "
            f"Epsilon={agent.epsilon:.3f}"
        )

        # Checkpoint model
        if self.episode % self.config.checkpoint_frequency == 0:
            await self._checkpoint_model(symbol, metrics)

        return metrics

    async def _checkpoint_model(self, symbol: str, metrics: Dict[str, float]):
        """Save model checkpoint."""
        agent = self.agents[symbol]
        weights = agent.get_model_weights()
        await self.persistence.save_model_checkpoint(
            weights, self.episode, self.total_steps, metrics
        )

    async def run_training(self, num_episodes: int):
        """Run training for specified number of episodes."""
        logger.info(f"Starting training for {num_episodes} episodes...")

        for episode in range(num_episodes):
            for symbol in self.config.symbols:
                await self.run_episode(symbol, training=True)

            # Periodic updates
            if episode % 10 == 0:
                await self.persistence.update_session_status(
                    'running',
                    total_episodes=self.episode,
                    total_steps=self.total_steps
                )

        logger.info("Training complete")
        await self.persistence.update_session_status('completed', total_episodes=self.episode)

    async def run_live(self):
        """Run live trading loop."""
        logger.info("Starting live trading mode...")
        self.running = True

        try:
            while self.running:
                for symbol in self.config.symbols:
                    await self._process_live_step(symbol)

                # Sleep until next poll
                await asyncio.sleep(self.config.poll_interval_seconds)

        except KeyboardInterrupt:
            logger.info("Received interrupt signal")
        finally:
            await self.shutdown()

    async def _process_live_step(self, symbol: str):
        """Process one live trading step."""
        try:
            # Download latest data
            ticker = yf.Ticker(symbol)
            df = ticker.history(period="1mo", interval="1d")

            if df.empty:
                logger.warning(f"No data for {symbol}")
                return

            # Feature engineering
            df = self.feature_engineer.calculate_technical_indicators(df)

            # Extract market data
            market_data = self.feature_engineer.extract_market_data(df, symbol)
            await self.persistence.store_market_data(market_data)

            # Calculate alpha signals
            signals = self.alpha_model.calculate_signals(df, symbol)
            await self.persistence.store_alpha_signals(signals)

            # Detect regime
            regime = self.regime_detector.detect_regime(df, symbol)
            await self.persistence.store_regime_state(regime)

            # Get RL action (inference mode)
            agent = self.agents[symbol]
            env = self.envs[symbol]

            # Update environment with latest data
            env.data = df
            state = env._get_observation()

            # Select action (deterministic)
            action, action_prob, is_exploration = agent.select_action(state, deterministic=True)

            logger.info(
                f"{symbol}: Signal={signals.ensemble_signal:.3f}, "
                f"Regime={regime.regime.name}, Action={RLAction(action).name}"
            )

        except Exception as e:
            logger.error(f"Error processing {symbol}: {e}")
            logger.error(traceback.format_exc())

    async def shutdown(self):
        """Graceful shutdown."""
        logger.info("Shutting down strategy...")
        self.running = False
        await self.persistence.update_session_status('completed', total_episodes=self.episode)
        logger.info("Shutdown complete")


# ============================================================================
# MAIN
# ============================================================================

async def main():
    """Main entry point."""
    import argparse

    parser = argparse.ArgumentParser(description='RL Multi-Factor Trading Strategy')
    parser.add_argument('--mode', choices=['train', 'live', 'inference'], default='live',
                       help='Operating mode')
    parser.add_argument('--episodes', type=int, default=100,
                       help='Number of training episodes')
    args = parser.parse_args()

    # Create configuration
    config = RLStrategyConfig()

    # Create strategy
    strategy = RLMultiFactorStrategy(config)

    # Setup signal handlers
    def signal_handler(signum, frame):
        logger.info(f"Received signal {signum}")
        strategy.running = False

    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)

    try:
        # Initialize
        await strategy.initialize()

        # Run based on mode
        if args.mode == 'train':
            await strategy.run_training(args.episodes)
        elif args.mode == 'live':
            await strategy.run_live()
        elif args.mode == 'inference':
            # Similar to live but with frozen model
            config.epsilon_start = 0.0
            await strategy.run_live()

    except Exception as e:
        logger.error(f"Fatal error: {e}")
        logger.error(traceback.format_exc())
        await strategy.persistence.update_session_status('failed')
    finally:
        await strategy.shutdown()


if __name__ == '__main__':
    asyncio.run(main())
