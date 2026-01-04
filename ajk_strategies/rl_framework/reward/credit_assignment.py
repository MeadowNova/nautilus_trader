# -------------------------------------------------------------------------------------------------
#  N-Step Credit Assignment for RL Trading
#  Attributes delayed rewards back through trajectory
# -------------------------------------------------------------------------------------------------

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class Experience:
    """Single experience tuple for replay buffer."""
    state: list[float]
    action: int
    immediate_reward: float
    next_state: list[float]
    done: bool
    n_step_return: float = 0.0
    priority: float = 1.0
    instrument_id: str | None = None
    timestamp: int = 0


class NStepCreditAssignment:
    """
    N-step TD learning for credit assignment in trading.

    In trading, the final reward (trade P&L) comes at trade close,
    but we need to assign credit to decisions made throughout the trade.
    This class handles backward propagation of delayed rewards.
    """

    def __init__(self, n: int = 10, gamma: float = 0.99):
        """
        Initialize N-step credit assignment.

        Parameters
        ----------
        n : int
            Number of steps for n-step returns. Default is 10.
        gamma : float
            Discount factor. Default is 0.99.
        """
        self.n = n
        self.gamma = gamma

    def assign_rewards(
        self,
        trajectory: list[Experience],
        final_reward: float,
    ) -> list[Experience]:
        """
        Assign delayed reward back through trajectory using n-step returns.

        Parameters
        ----------
        trajectory : list[Experience]
            List of experiences from trade entry to exit.
        final_reward : float
            The final reward from trade close.

        Returns
        -------
        list[Experience]
            Trajectory with n_step_return values computed.
        """
        T = len(trajectory)
        if T == 0:
            return trajectory

        for t in range(T):
            n_step_return = 0.0

            # Sum discounted immediate rewards over n steps
            for i in range(min(self.n, T - t)):
                step_reward = trajectory[t + i].immediate_reward
                n_step_return += (self.gamma ** i) * step_reward

            # Add discounted final reward if within n steps of end
            if t + self.n >= T:
                steps_to_end = T - t
                n_step_return += (self.gamma ** steps_to_end) * final_reward

            trajectory[t].n_step_return = n_step_return

        return trajectory

    def compute_td_target(
        self,
        experience: Experience,
        value_estimate: float,
    ) -> float:
        """
        Compute TD target for a single experience.

        Parameters
        ----------
        experience : Experience
            The experience to compute target for.
        value_estimate : float
            Bootstrap value estimate (V(s') or 0 if terminal).

        Returns
        -------
        float
            TD target value.
        """
        if experience.done:
            return experience.n_step_return

        return experience.n_step_return + (self.gamma ** self.n) * value_estimate

    def compute_advantage(
        self,
        experience: Experience,
        value_current: float,
        value_next: float,
    ) -> float:
        """
        Compute advantage for policy gradient methods.

        Parameters
        ----------
        experience : Experience
            The experience tuple.
        value_current : float
            Value estimate for current state.
        value_next : float
            Value estimate for next state.

        Returns
        -------
        float
            Advantage estimate.
        """
        if experience.done:
            td_target = experience.immediate_reward
        else:
            td_target = experience.immediate_reward + self.gamma * value_next

        return td_target - value_current


class GAE:
    """
    Generalized Advantage Estimation for more stable training.

    GAE provides a better bias-variance tradeoff for advantage estimation
    compared to pure n-step returns.
    """

    def __init__(self, gamma: float = 0.99, lam: float = 0.95):
        """
        Initialize GAE.

        Parameters
        ----------
        gamma : float
            Discount factor. Default is 0.99.
        lam : float
            GAE lambda parameter (0=TD, 1=MC). Default is 0.95.
        """
        self.gamma = gamma
        self.lam = lam

    def compute_advantages(
        self,
        rewards: list[float],
        values: list[float],
        dones: list[bool],
    ) -> list[float]:
        """
        Compute GAE advantages for a trajectory.

        Parameters
        ----------
        rewards : list[float]
            Rewards at each step.
        values : list[float]
            Value estimates at each step.
        dones : list[bool]
            Done flags at each step.

        Returns
        -------
        list[float]
            GAE advantage estimates.
        """
        T = len(rewards)
        if T == 0:
            return []

        advantages = [0.0] * T
        last_gae = 0.0

        # Backward pass
        for t in reversed(range(T)):
            if dones[t]:
                next_value = 0.0
                last_gae = 0.0
            else:
                next_value = values[t + 1] if t + 1 < len(values) else 0.0

            # TD error
            delta = rewards[t] + self.gamma * next_value - values[t]

            # GAE formula
            advantages[t] = last_gae = delta + self.gamma * self.lam * last_gae

        return advantages

    def compute_returns(
        self,
        advantages: list[float],
        values: list[float],
    ) -> list[float]:
        """
        Compute returns from advantages and values.

        Parameters
        ----------
        advantages : list[float]
            GAE advantages.
        values : list[float]
            Value estimates.

        Returns
        -------
        list[float]
            Returns (advantages + values).
        """
        return [adv + val for adv, val in zip(advantages, values)]
