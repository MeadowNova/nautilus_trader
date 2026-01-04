# -------------------------------------------------------------------------------------------------
#  Experience Replay Buffer for RL Trading
#  Implements prioritized experience replay with persistence
# -------------------------------------------------------------------------------------------------

from __future__ import annotations

import random
from dataclasses import dataclass, field
from typing import TYPE_CHECKING
import numpy as np

if TYPE_CHECKING:
    from ajk_strategies.rl_framework.reward.credit_assignment import Experience


@dataclass
class ExperienceBuffer:
    """
    Simple experience replay buffer.

    Stores experiences for batch sampling during training.
    """

    capacity: int = 100000
    _buffer: list = field(default_factory=list)
    _position: int = 0

    def add(self, experience: Experience) -> None:
        """Add an experience to the buffer."""
        if len(self._buffer) < self.capacity:
            self._buffer.append(experience)
        else:
            self._buffer[self._position] = experience

        self._position = (self._position + 1) % self.capacity

    def sample(self, batch_size: int) -> list[Experience]:
        """Sample a batch of experiences uniformly."""
        if len(self._buffer) < batch_size:
            return list(self._buffer)
        return random.sample(self._buffer, batch_size)

    def __len__(self) -> int:
        return len(self._buffer)

    def clear(self) -> None:
        """Clear the buffer."""
        self._buffer.clear()
        self._position = 0


class SumTree:
    """
    Sum tree data structure for efficient priority sampling.

    Used by PrioritizedReplayBuffer for O(log n) sampling.
    """

    def __init__(self, capacity: int):
        self.capacity = capacity
        self.tree = np.zeros(2 * capacity - 1)
        self.data = np.zeros(capacity, dtype=object)
        self.n_entries = 0
        self.write = 0

    def _propagate(self, idx: int, change: float) -> None:
        """Propagate priority change up the tree."""
        parent = (idx - 1) // 2

        self.tree[parent] += change

        if parent != 0:
            self._propagate(parent, change)

    def _retrieve(self, idx: int, s: float) -> int:
        """Retrieve leaf node index for a given cumulative priority."""
        left = 2 * idx + 1
        right = left + 1

        if left >= len(self.tree):
            return idx

        if s <= self.tree[left]:
            return self._retrieve(left, s)
        else:
            return self._retrieve(right, s - self.tree[left])

    def total(self) -> float:
        """Get total priority sum."""
        return self.tree[0]

    def add(self, priority: float, data: object) -> None:
        """Add data with priority to the tree."""
        idx = self.write + self.capacity - 1

        self.data[self.write] = data
        self.update(idx, priority)

        self.write = (self.write + 1) % self.capacity

        if self.n_entries < self.capacity:
            self.n_entries += 1

    def update(self, idx: int, priority: float) -> None:
        """Update priority at a tree index."""
        change = priority - self.tree[idx]

        self.tree[idx] = priority
        self._propagate(idx, change)

    def get(self, s: float) -> tuple[int, float, object]:
        """
        Get experience by cumulative priority.

        Returns (index, priority, data).
        """
        idx = self._retrieve(0, s)
        data_idx = idx - self.capacity + 1

        return (idx, self.tree[idx], self.data[data_idx])


class PrioritizedReplayBuffer:
    """
    Prioritized Experience Replay buffer.

    Samples experiences with probability proportional to TD-error priority.
    Implements importance sampling weights for unbiased updates.
    """

    def __init__(
        self,
        capacity: int = 100000,
        alpha: float = 0.6,
        beta: float = 0.4,
        beta_increment: float = 0.001,
        epsilon: float = 0.01,
    ):
        """
        Initialize PrioritizedReplayBuffer.

        Parameters
        ----------
        capacity : int
            Maximum number of experiences to store.
        alpha : float
            Priority exponent (0 = uniform, 1 = full priority).
        beta : float
            Importance sampling exponent (0 = no correction, 1 = full).
        beta_increment : float
            Amount to increase beta per sample.
        epsilon : float
            Small constant to ensure non-zero priorities.
        """
        self.capacity = capacity
        self.alpha = alpha
        self.beta = beta
        self.beta_increment = beta_increment
        self.epsilon = epsilon

        self._tree = SumTree(capacity)
        self._max_priority = 1.0
        self._new_experiences = 0

    def add(
        self,
        experience: Experience,
        instrument: str | None = None,
    ) -> None:
        """
        Add experience to buffer with max priority.

        Parameters
        ----------
        experience : Experience
            The experience to add.
        instrument : str | None
            Optional instrument identifier for filtering.
        """
        # New experiences get max priority
        priority = self._max_priority ** self.alpha
        self._tree.add(priority, experience)
        self._new_experiences += 1

    def sample(self, batch_size: int) -> tuple[list, list, list]:
        """
        Sample a batch of experiences with priority weighting.

        Parameters
        ----------
        batch_size : int
            Number of experiences to sample.

        Returns
        -------
        tuple[list, list, list]
            (experiences, indices, importance_weights)
        """
        batch_size = min(batch_size, self._tree.n_entries)
        if batch_size == 0:
            return [], [], []

        experiences = []
        indices = []
        priorities = []

        # Divide priority range into segments
        segment = self._tree.total() / batch_size

        # Anneal beta
        self.beta = min(1.0, self.beta + self.beta_increment)

        for i in range(batch_size):
            # Sample from segment
            a = segment * i
            b = segment * (i + 1)
            s = random.uniform(a, b)

            idx, priority, data = self._tree.get(s)

            experiences.append(data)
            indices.append(idx)
            priorities.append(priority)

        # Calculate importance sampling weights
        min_prob = min(priorities) / self._tree.total()
        max_weight = (min_prob * self._tree.n_entries) ** (-self.beta)

        weights = []
        for priority in priorities:
            prob = priority / self._tree.total()
            weight = (prob * self._tree.n_entries) ** (-self.beta)
            weights.append(weight / max_weight)  # Normalize

        return experiences, indices, weights

    def sample_diverse(
        self,
        batch_size: int,
        min_instruments: int = 1,
    ) -> tuple[list, list, list]:
        """
        Sample ensuring diversity across instruments.

        Parameters
        ----------
        batch_size : int
            Number of experiences to sample.
        min_instruments : int
            Minimum number of different instruments in batch.

        Returns
        -------
        tuple[list, list, list]
            (experiences, indices, importance_weights)
        """
        # For now, use regular sampling
        # TODO: Implement instrument-aware sampling
        return self.sample(batch_size)

    def update_priorities(
        self,
        indices: list[int],
        td_errors: list[float],
    ) -> None:
        """
        Update priorities based on TD errors.

        Parameters
        ----------
        indices : list[int]
            Tree indices to update.
        td_errors : list[float]
            TD errors for calculating new priorities.
        """
        for idx, error in zip(indices, td_errors):
            priority = (abs(error) + self.epsilon) ** self.alpha
            self._tree.update(idx, priority)
            self._max_priority = max(self._max_priority, priority)

    def __len__(self) -> int:
        return self._tree.n_entries

    @property
    def new_experiences(self) -> int:
        """Get count of new experiences since last training."""
        return self._new_experiences

    def reset_new_count(self) -> None:
        """Reset new experience counter."""
        self._new_experiences = 0

    def should_train(
        self,
        min_buffer_size: int = 1000,
        train_every_n: int = 100,
    ) -> bool:
        """
        Check if training should occur.

        Parameters
        ----------
        min_buffer_size : int
            Minimum experiences before training starts.
        train_every_n : int
            Train after this many new experiences.

        Returns
        -------
        bool
            True if training should occur.
        """
        return (
            len(self) >= min_buffer_size
            and self._new_experiences >= train_every_n
        )
