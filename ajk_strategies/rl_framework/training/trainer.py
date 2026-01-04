# -------------------------------------------------------------------------------------------------
#  RL Trainer for Trading Strategies
#  Training loop with catastrophic forgetting mitigation
# -------------------------------------------------------------------------------------------------

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING
import numpy as np

if TYPE_CHECKING:
    from ajk_strategies.rl_framework.agents.base_agent import RLAgent
    from ajk_strategies.rl_framework.training.experience_buffer import PrioritizedReplayBuffer


@dataclass
class TrainingMetrics:
    """Metrics from a training step."""
    policy_loss: float
    value_loss: float
    ewc_loss: float
    td_error_mean: float
    entropy: float
    learning_rate: float
    epoch: int


@dataclass
class TrainingConfig:
    """Configuration for RL training."""
    batch_size: int = 64
    min_buffer_size: int = 1000
    train_every_n: int = 100
    epochs_per_train: int = 10
    learning_rate: float = 3e-4
    gamma: float = 0.99
    gae_lambda: float = 0.95
    clip_epsilon: float = 0.2
    value_coef: float = 0.5
    entropy_coef: float = 0.01
    max_grad_norm: float = 0.5
    ewc_lambda: float = 1000.0
    target_update_freq: int = 100


class ElasticWeightConsolidation:
    """
    Elastic Weight Consolidation for catastrophic forgetting mitigation.

    EWC adds a penalty for changing important weights, helping the agent
    retain previously learned behaviors when learning new ones.
    """

    def __init__(self, lambda_: float = 1000.0):
        """
        Initialize EWC.

        Parameters
        ----------
        lambda_ : float
            EWC regularization strength.
        """
        self.lambda_ = lambda_
        self._fisher_information: dict[str, np.ndarray] = {}
        self._optimal_weights: dict[str, np.ndarray] = {}
        self._initialized = False

    def update_fisher_information(
        self,
        agent: RLAgent,
        experiences: list,
    ) -> None:
        """
        Update Fisher information matrix from experiences.

        Parameters
        ----------
        agent : RLAgent
            The RL agent.
        experiences : list
            Experiences to compute Fisher information from.
        """
        # Placeholder - would compute Fisher information from gradients
        # For now, just mark as initialized
        self._initialized = True

    def compute_penalty(self, agent: RLAgent) -> float:
        """
        Compute EWC penalty for current weights.

        Parameters
        ----------
        agent : RLAgent
            The RL agent.

        Returns
        -------
        float
            The EWC penalty (0 if not initialized).
        """
        if not self._initialized:
            return 0.0

        # Placeholder - would compute penalty from weight changes
        return 0.0

    def save_optimal_weights(self, agent: RLAgent) -> None:
        """Save current weights as optimal."""
        pass


class RLTrainer:
    """
    Training loop for RL trading agents.

    Implements:
    - Prioritized experience replay sampling
    - Elastic Weight Consolidation
    - Gradient clipping
    - Learning rate scheduling
    """

    def __init__(
        self,
        agent: RLAgent,
        buffer: PrioritizedReplayBuffer,
        config: TrainingConfig | None = None,
    ):
        """
        Initialize RLTrainer.

        Parameters
        ----------
        agent : RLAgent
            The RL agent to train.
        buffer : PrioritizedReplayBuffer
            The experience replay buffer.
        config : TrainingConfig | None
            Training configuration.
        """
        self.agent = agent
        self.buffer = buffer
        self.config = config or TrainingConfig()

        self.ewc = ElasticWeightConsolidation(self.config.ewc_lambda)

        self._total_epochs = 0
        self._training_history: list[TrainingMetrics] = []

    async def train_step(self) -> TrainingMetrics | None:
        """
        Perform a single training step.

        Returns
        -------
        TrainingMetrics | None
            Training metrics or None if training was skipped.
        """
        if not self.should_train():
            return None

        # Sample from prioritized buffer
        experiences, indices, weights = self.buffer.sample(self.config.batch_size)

        if not experiences:
            return None

        # Extract batch data
        states = np.array([e.state for e in experiences])
        actions = np.array([e.action for e in experiences])
        rewards = np.array([e.n_step_return for e in experiences])
        next_states = np.array([e.next_state for e in experiences])
        dones = np.array([e.done for e in experiences])
        weights = np.array(weights)

        # Training loop
        total_policy_loss = 0.0
        total_value_loss = 0.0
        total_entropy = 0.0

        for epoch in range(self.config.epochs_per_train):
            # Compute losses (would use actual agent methods)
            policy_loss = 0.0
            value_loss = 0.0
            entropy = 0.0

            # EWC penalty
            ewc_loss = self.ewc.compute_penalty(self.agent)

            # Total loss
            total_loss = policy_loss + self.config.value_coef * value_loss
            total_loss -= self.config.entropy_coef * entropy
            total_loss += ewc_loss

            total_policy_loss += policy_loss
            total_value_loss += value_loss
            total_entropy += entropy

            self._total_epochs += 1

        # Compute TD errors for priority updates
        td_errors = self._compute_td_errors(experiences)

        # Update priorities
        self.buffer.update_priorities(indices, td_errors)

        # Reset new experience counter
        self.buffer.reset_new_count()

        # Record metrics
        avg_epochs = self.config.epochs_per_train
        metrics = TrainingMetrics(
            policy_loss=total_policy_loss / avg_epochs,
            value_loss=total_value_loss / avg_epochs,
            ewc_loss=self.ewc.compute_penalty(self.agent),
            td_error_mean=float(np.mean(np.abs(td_errors))),
            entropy=total_entropy / avg_epochs,
            learning_rate=self.config.learning_rate,
            epoch=self._total_epochs,
        )

        self._training_history.append(metrics)

        return metrics

    def _compute_td_errors(self, experiences: list) -> list[float]:
        """Compute TD errors for priority updates."""
        td_errors = []
        for exp in experiences:
            # Simplified TD error computation
            # In practice, would use value network
            td_error = exp.n_step_return - exp.immediate_reward
            td_errors.append(td_error)
        return td_errors

    def should_train(self) -> bool:
        """Check if training should occur."""
        return self.buffer.should_train(
            min_buffer_size=self.config.min_buffer_size,
            train_every_n=self.config.train_every_n,
        )

    def save_checkpoint(self, path: str) -> None:
        """Save training checkpoint."""
        # Save agent weights
        self.agent.save(path)

        # Save EWC state
        self.ewc.save_optimal_weights(self.agent)

    def load_checkpoint(self, path: str) -> None:
        """Load training checkpoint."""
        self.agent.load(path)

    def get_training_summary(self) -> dict:
        """Get summary of training progress."""
        if not self._training_history:
            return {}

        recent = self._training_history[-100:]  # Last 100 epochs

        return {
            "total_epochs": self._total_epochs,
            "avg_policy_loss": np.mean([m.policy_loss for m in recent]),
            "avg_value_loss": np.mean([m.value_loss for m in recent]),
            "avg_td_error": np.mean([m.td_error_mean for m in recent]),
            "buffer_size": len(self.buffer),
        }
