# -------------------------------------------------------------------------------------------------
#  Base RL Agent for Trading
#  Abstract base class for PPO, SAC, and DQN implementations
# -------------------------------------------------------------------------------------------------

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from enum import IntEnum
from pathlib import Path
from typing import TYPE_CHECKING

import numpy as np

if TYPE_CHECKING:
    from ajk_strategies.rl_framework.state.state_builder import StateBuilder


class Action(IntEnum):
    """Trading action space."""
    HOLD = 0
    BUY = 1
    SELL = 2
    EXIT = 3  # Close position


@dataclass
class AgentConfig:
    """Configuration for RL agents."""
    state_dim: int = 67  # From StateBuilder
    action_dim: int = 4  # HOLD, BUY, SELL, EXIT
    hidden_dims: list[int] = None  # Neural network hidden layers
    learning_rate: float = 3e-4
    gamma: float = 0.99
    epsilon: float = 0.1  # Exploration rate
    epsilon_min: float = 0.01
    epsilon_decay: float = 0.995
    device: str = "cpu"

    def __post_init__(self):
        if self.hidden_dims is None:
            self.hidden_dims = [256, 256]


class RLAgent(ABC):
    """
    Abstract base class for reinforcement learning trading agents.

    Provides interface for:
    - Action prediction from state
    - Training from experience batches
    - Model persistence
    - Exploration control
    """

    def __init__(self, config: AgentConfig | None = None):
        """
        Initialize RLAgent.

        Parameters
        ----------
        config : AgentConfig | None
            Agent configuration.
        """
        self.config = config or AgentConfig()
        self.epsilon = self.config.epsilon
        self._training = True
        self._step_count = 0

    @abstractmethod
    def predict(self, state: np.ndarray) -> Action:
        """
        Predict action from state.

        Parameters
        ----------
        state : np.ndarray
            The current state vector.

        Returns
        -------
        Action
            The predicted action.
        """
        pass

    @abstractmethod
    def predict_probs(self, state: np.ndarray) -> np.ndarray:
        """
        Predict action probabilities from state.

        Parameters
        ----------
        state : np.ndarray
            The current state vector.

        Returns
        -------
        np.ndarray
            Action probabilities.
        """
        pass

    @abstractmethod
    def compute_loss(self, batch: dict) -> float:
        """
        Compute loss from experience batch.

        Parameters
        ----------
        batch : dict
            Batch of experiences.

        Returns
        -------
        float
            The computed loss.
        """
        pass

    @abstractmethod
    def train_step(self, batch: dict) -> dict:
        """
        Perform a training step.

        Parameters
        ----------
        batch : dict
            Batch of experiences.

        Returns
        -------
        dict
            Training metrics.
        """
        pass

    @abstractmethod
    def save(self, path: str) -> None:
        """Save model weights to path."""
        pass

    @abstractmethod
    def load(self, path: str) -> None:
        """Load model weights from path."""
        pass

    def act(self, state: np.ndarray, explore: bool = True) -> Action:
        """
        Select action with optional exploration.

        Parameters
        ----------
        state : np.ndarray
            The current state vector.
        explore : bool
            Whether to use epsilon-greedy exploration.

        Returns
        -------
        Action
            The selected action.
        """
        self._step_count += 1

        if explore and self._training and np.random.random() < self.epsilon:
            # Random exploration
            return Action(np.random.randint(0, self.config.action_dim))

        return self.predict(state)

    def decay_epsilon(self) -> None:
        """Decay exploration rate."""
        self.epsilon = max(
            self.config.epsilon_min,
            self.epsilon * self.config.epsilon_decay
        )

    def increase_exploration(self, factor: float = 2.0, duration_steps: int = 1000) -> None:
        """
        Temporarily increase exploration rate.

        Used when regime change is detected.

        Parameters
        ----------
        factor : float
            Multiplication factor for epsilon.
        duration_steps : int
            Number of steps before decay resumes.
        """
        self.epsilon = min(1.0, self.epsilon * factor)

    def set_training(self, training: bool) -> None:
        """Set training mode."""
        self._training = training

    def get_weights(self) -> dict:
        """Get model weights as dictionary."""
        return {}

    def set_weights(self, weights: dict) -> None:
        """Set model weights from dictionary."""
        pass


class SimpleRuleAgent(RLAgent):
    """
    Simple rule-based agent for baseline comparison.

    Uses configurable rules instead of learned policy.
    Useful for pre-training and comparison.
    """

    def __init__(
        self,
        config: AgentConfig | None = None,
        buy_threshold: float = 0.02,
        sell_threshold: float = -0.01,
    ):
        super().__init__(config)
        self.buy_threshold = buy_threshold
        self.sell_threshold = sell_threshold

    def predict(self, state: np.ndarray) -> Action:
        """
        Predict action based on simple rules.

        Uses momentum (price change) as primary signal.
        """
        if len(state) < 5:
            return Action.HOLD

        # Extract recent price change (close return)
        # Assuming state structure from StateBuilder
        recent_return = state[4] if len(state) > 4 else 0.0

        # Position P&L ratio (if available)
        position_pnl = state[-4] if len(state) >= 4 else 0.0

        # Decision logic
        if position_pnl > 0.05:  # 5% profit
            return Action.EXIT  # Take profit
        elif position_pnl < -0.02:  # 2% loss
            return Action.EXIT  # Cut loss
        elif recent_return > self.buy_threshold:
            return Action.BUY
        elif recent_return < self.sell_threshold:
            return Action.SELL
        else:
            return Action.HOLD

    def predict_probs(self, state: np.ndarray) -> np.ndarray:
        """Return deterministic probabilities."""
        action = self.predict(state)
        probs = np.zeros(self.config.action_dim)
        probs[action] = 1.0
        return probs

    def compute_loss(self, batch: dict) -> float:
        """No loss for rule-based agent."""
        return 0.0

    def train_step(self, batch: dict) -> dict:
        """No training for rule-based agent."""
        return {"loss": 0.0}

    def save(self, path: str) -> None:
        """Save configuration."""
        import json
        config = {
            "buy_threshold": self.buy_threshold,
            "sell_threshold": self.sell_threshold,
        }
        Path(path).write_text(json.dumps(config))

    def load(self, path: str) -> None:
        """Load configuration."""
        import json
        config = json.loads(Path(path).read_text())
        self.buy_threshold = config.get("buy_threshold", 0.02)
        self.sell_threshold = config.get("sell_threshold", -0.01)
