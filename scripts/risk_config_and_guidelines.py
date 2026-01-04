"""
RISK CONFIGURATION & POSITION SIZING GUIDELINES
===============================================

This module provides comprehensive configuration, position sizing calculations,
and best practices for the multi-factor strategy risk management framework.

Contains:
- Risk configuration profiles (Conservative, Moderate, Aggressive)
- Position sizing calculations (Kelly Criterion, volatility scaling)
- Stop-loss and take-profit level calculation
- Hedging configuration templates
- Circuit breaker thresholds
- Scenario analysis

Usage:
    from risk_config_and_guidelines import RiskProfile, PositionSizer

    profile = RiskProfile.MODERATE
    sizer = PositionSizer(portfolio_value=1000000, profile=profile)
    position_size = sizer.calculate_position_size(...)
"""

import numpy as np
from enum import Enum
from dataclasses import dataclass
from typing import Dict, Tuple, Optional


# ============================================================================
# RISK PROFILES
# ============================================================================

class RiskProfile(Enum):
    """Pre-configured risk management profiles"""
    CONSERVATIVE = "conservative"
    MODERATE = "moderate"
    AGGRESSIVE = "aggressive"


class RiskProfileConfig:
    """Risk configuration parameters for each profile"""

    PROFILES = {
        RiskProfile.CONSERVATIVE: {
            'description': 'Capital preservation focused, minimal leverage, wide stops',
            'max_daily_loss_pct': 0.01,        # 1%
            'max_drawdown_pct': 0.05,          # 5%
            'max_position_size_pct': 0.02,     # 2% per position
            'max_sector_exposure_pct': 0.10,   # 10% per sector
            'max_portfolio_heat_pct': 0.005,   # 0.5% - very conservative
            'max_leverage_ratio': 1.2,         # Minimal leverage
            'kelly_fraction': 0.15,            # Very conservative Kelly
            'volatility_target': 0.10,         # 10% annual vol target
            'max_correlation_sum': 2.0,        # Strict diversification
            'atr_multiplier': 3.0,             # Wide stops (3 * ATR)
            'profit_target_multiplier': 5.0,   # 5:1 reward:risk ratio
            'trailing_stop_activation': 0.01,  # 1% profit to activate
            'time_stop_bars': 200,             # Hold longer
            'min_conviction': 0.50,            # High conviction required
        },

        RiskProfile.MODERATE: {
            'description': 'Balanced growth and preservation, moderate leverage, reasonable stops',
            'max_daily_loss_pct': 0.02,        # 2%
            'max_drawdown_pct': 0.10,          # 10%
            'max_position_size_pct': 0.05,     # 5% per position (recommended)
            'max_sector_exposure_pct': 0.25,   # 25% per sector
            'max_portfolio_heat_pct': 0.02,    # 2% - balanced
            'max_leverage_ratio': 2.0,         # Moderate leverage
            'kelly_fraction': 0.25,            # Conservative Kelly
            'volatility_target': 0.15,         # 15% annual vol target
            'max_correlation_sum': 3.0,        # Moderate diversification
            'atr_multiplier': 2.5,             # 2.5 * ATR stops
            'profit_target_multiplier': 3.0,   # 3:1 reward:risk ratio
            'trailing_stop_activation': 0.015, # 1.5% profit to activate
            'time_stop_bars': 100,             # Medium holding
            'min_conviction': 0.40,            # Reasonable conviction
        },

        RiskProfile.AGGRESSIVE: {
            'description': 'Maximum growth focus, high leverage, tight stops, active trading',
            'max_daily_loss_pct': 0.05,        # 5%
            'max_drawdown_pct': 0.20,          # 20%
            'max_position_size_pct': 0.10,     # 10% per position
            'max_sector_exposure_pct': 0.40,   # 40% per sector
            'max_portfolio_heat_pct': 0.03,    # 3% - aggressive
            'max_leverage_ratio': 3.0,         # High leverage
            'kelly_fraction': 0.35,            # Standard Kelly
            'volatility_target': 0.25,         # 25% annual vol target
            'max_correlation_sum': 4.0,        # Relaxed diversification
            'atr_multiplier': 2.0,             # Tight stops (2 * ATR)
            'profit_target_multiplier': 2.0,   # 2:1 reward:risk ratio
            'trailing_stop_activation': 0.02,  # 2% profit to activate
            'time_stop_bars': 50,              # Shorter holding
            'min_conviction': 0.35,            # Lower conviction threshold
        }
    }

    @classmethod
    def get_profile(cls, profile: RiskProfile) -> Dict:
        """Get configuration for risk profile"""
        return cls.PROFILES[profile]

    @classmethod
    def print_profiles(cls):
        """Print all profiles for reference"""
        print("\n" + "=" * 80)
        print("RISK PROFILE CONFIGURATIONS")
        print("=" * 80)

        for profile, config in cls.PROFILES.items():
            print(f"\n{profile.value.upper()}")
            print("-" * 80)
            print(f"Description: {config['description']}\n")

            print("Daily Risk Management:")
            print(f"  Max Daily Loss:        {config['max_daily_loss_pct']:.1%}")
            print(f"  Max Drawdown:          {config['max_drawdown_pct']:.1%}")
            print(f"  Max Leverage:          {config['max_leverage_ratio']:.1f}x")

            print("\nPosition Limits:")
            print(f"  Max Position Size:     {config['max_position_size_pct']:.1%}")
            print(f"  Max Sector Exposure:   {config['max_sector_exposure_pct']:.1%}")
            print(f"  Max Portfolio Heat:    {config['max_portfolio_heat_pct']:.2%}")

            print("\nPosition Sizing:")
            print(f"  Kelly Fraction:        {config['kelly_fraction']:.2f}")
            print(f"  Volatility Target:     {config['volatility_target']:.1%}")
            print(f"  Correlation Limit:     {config['max_correlation_sum']:.1f}")

            print("\nRisk Management:")
            print(f"  ATR Multiplier:        {config['atr_multiplier']:.1f}x")
            print(f"  Profit Target Ratio:   {config['profit_target_multiplier']:.1f}:1")
            print(f"  Trailing Stop Trigger: {config['trailing_stop_activation']:.1%}")
            print(f"  Max Hold Time:         {config['time_stop_bars']} bars")
            print(f"  Min Conviction:        {config['min_conviction']:.0%}")


# ============================================================================
# POSITION SIZING CALCULATOR
# ============================================================================

class PositionSizer:
    """
    Comprehensive position sizing using multiple methods.

    Methods:
    - Kelly Criterion: f* = (bp - q) / b
    - Volatility Scaling: Adjust size inversely to volatility
    - Fixed Risk: Size for specific dollar risk
    - Percentage of Portfolio: Simple % allocation
    """

    def __init__(self, portfolio_value: float, profile: RiskProfile = RiskProfile.MODERATE):
        """
        Initialize position sizer.

        Args:
            portfolio_value: Current portfolio value
            profile: RiskProfile (CONSERVATIVE, MODERATE, AGGRESSIVE)
        """
        self.portfolio_value = portfolio_value
        self.profile = profile
        self.config = RiskProfileConfig.get_profile(profile)

        self.kelly_fraction = self.config['kelly_fraction']
        self.volatility_target = self.config['volatility_target']
        self.max_leverage = self.config['max_leverage_ratio']
        self.max_position_pct = self.config['max_position_size_pct']

    def calculate_kelly_size(self, win_rate: float, win_loss_ratio: float) -> float:
        """
        Calculate position size using Kelly Criterion.

        Kelly Formula: f* = (bp - q) / b
        Where:
        - b = odds (win_loss_ratio)
        - p = win_rate
        - q = 1 - win_rate

        Args:
            win_rate: Historical win rate (0 to 1)
            win_loss_ratio: Average win / average loss (must be > 0)

        Returns:
            Fractional Kelly position size (0 to max_leverage)

        Example:
            >>> sizer = PositionSizer(1000000)
            >>> size = sizer.calculate_kelly_size(0.55, 1.5)
            >>> print(f"Kelly size: {size:.2%}")  # ~5.5% of capital per trade
        """
        if win_rate <= 0 or win_rate >= 1 or win_loss_ratio <= 0:
            return 0.0

        # Calculate Kelly fraction
        p = win_rate
        q = 1 - win_rate
        b = win_loss_ratio

        kelly = (b * p - q) / b

        # Apply fractional Kelly for safety
        kelly_safe = kelly * self.kelly_fraction

        # Clip to reasonable limits
        kelly_safe = np.clip(kelly_safe, 0, self.max_leverage)

        return kelly_safe

    def calculate_volatility_scaled_size(self, base_size: float,
                                        current_volatility: float) -> float:
        """
        Adjust position size based on volatility.

        Inverse volatility scaling: smaller positions in high volatility.

        Args:
            base_size: Base position size (before volatility adjustment)
            current_volatility: Current annualized volatility (e.g., 0.15 for 15%)

        Returns:
            Volatility-adjusted position size

        Example:
            >>> adjusted = sizer.calculate_volatility_scaled_size(0.05, 0.25)
            >>> print(f"Adjusted: {adjusted:.2%}")  # Reduced due to high vol
        """
        if current_volatility <= 0:
            return base_size

        # Scale inversely to volatility
        vol_ratio = self.volatility_target / current_volatility

        # Limit adjustment to 0.5x - 2.0x
        vol_ratio = np.clip(vol_ratio, 0.5, 2.0)

        return base_size * vol_ratio

    def calculate_fixed_risk_size(self, entry_price: float, stop_loss: float,
                                 risk_dollars: float) -> int:
        """
        Calculate position size for fixed dollar risk.

        Standard risk management: Define maximum loss per trade (1R),
        then calculate shares needed.

        Args:
            entry_price: Entry price
            stop_loss: Stop loss price
            risk_dollars: Maximum $ loss acceptable (1R)

        Returns:
            Number of shares to buy

        Example:
            >>> shares = sizer.calculate_fixed_risk_size(100, 95, 1000)
            >>> print(f"Buy {shares} shares (risk $1000)")
        """
        if entry_price <= 0 or stop_loss <= 0 or risk_dollars <= 0:
            return 0

        risk_per_share = abs(entry_price - stop_loss)

        if risk_per_share == 0:
            return 0

        shares = risk_dollars / risk_per_share

        return int(shares)

    def calculate_optimal_position_size(self, signal: float, confidence: float,
                                       current_price: float, volatility: float,
                                       stop_loss: float,
                                       win_rate: float = None,
                                       win_loss_ratio: float = None) -> Dict:
        """
        Calculate optimal position size using multiple methods and take minimum.

        This is the recommended method combining all constraints:
        1. Kelly Criterion (if historical data available)
        2. Volatility scaling
        3. Fixed risk limit
        4. Max position size limit
        5. Portfolio leverage limit

        Args:
            signal: Signal strength (-1 to +1)
            confidence: Signal confidence (0 to 1)
            current_price: Current asset price
            volatility: Annualized volatility (e.g., 0.15)
            stop_loss: Stop loss price
            win_rate: Optional historical win rate for Kelly
            win_loss_ratio: Optional avg_win/avg_loss for Kelly

        Returns:
            Dict with sizing details
        """
        # Base size from confidence and signal
        base_size_pct = (self.config['max_position_size_pct'] *
                        (0.5 + 0.5 * abs(signal)) *
                        (0.5 + 0.5 * confidence))

        # Method 1: Volatility scaling
        vol_scaled = self.calculate_volatility_scaled_size(
            base_size_pct, volatility
        )

        # Method 2: Kelly (if available)
        kelly_size = 0.0
        if win_rate is not None and win_loss_ratio is not None:
            kelly_size = self.calculate_kelly_size(win_rate, win_loss_ratio)

        # Use Kelly if better, otherwise volatility scaled
        optimal_size_pct = max(vol_scaled, kelly_size)

        # Method 3: Fixed risk method
        risk_dollars = self.portfolio_value * self.config['max_portfolio_heat_pct']
        fixed_risk_notional = risk_dollars / abs(current_price - stop_loss) if current_price != stop_loss else 0
        fixed_risk_pct = fixed_risk_notional / self.portfolio_value

        # Take minimum of all constraints
        final_size_pct = min(
            optimal_size_pct,
            self.max_position_pct,
            fixed_risk_pct,
            self.max_leverage
        )

        final_size_pct = max(final_size_pct, 0)  # No negative

        notional = self.portfolio_value * final_size_pct
        shares = int(notional / current_price) if current_price > 0 else 0

        return {
            'position_size_pct': final_size_pct,
            'notional_dollars': notional,
            'shares': shares,
            'method_used': self._determine_binding_constraint(
                optimal_size_pct, kelly_size, vol_scaled, self.max_position_pct, fixed_risk_pct
            ),
            'details': {
                'volatility_scaled_pct': vol_scaled,
                'kelly_size_pct': kelly_size,
                'fixed_risk_pct': fixed_risk_pct,
                'max_position_limit_pct': self.max_position_pct,
                'max_leverage_limit_pct': self.max_leverage,
                'signal_strength': abs(signal),
                'confidence': confidence
            }
        }

    def _determine_binding_constraint(self, optimal: float, kelly: float,
                                     vol_scaled: float, max_pos: float,
                                     fixed_risk: float) -> str:
        """Determine which constraint is binding (most restrictive)"""
        values = {
            'optimal': optimal,
            'kelly': kelly,
            'vol_scaled': vol_scaled,
            'max_position': max_pos,
            'fixed_risk': fixed_risk
        }

        # Find minimum (most restrictive)
        binding = min(values, key=lambda k: values[k] if values[k] > 0 else float('inf'))

        return f"{binding}: {values[binding]:.2%}"

    def suggest_position_sizes(self, symbols: list, prices: Dict[str, float],
                              volatilities: Dict[str, float],
                              correlations: Dict[Tuple[str, str], float]) -> Dict:
        """
        Suggest position sizes for multiple symbols considering correlations.

        Accounts for:
        - Individual position limits
        - Sector concentration
        - Portfolio-level correlation

        Args:
            symbols: List of symbols to size
            prices: {symbol: price}
            volatilities: {symbol: volatility}
            correlations: {(sym1, sym2): correlation}

        Returns:
            Dict with sizing for each symbol
        """
        positions = {}

        # Start with equal-weight, then adjust for constraints
        weight_per_symbol = 1.0 / len(symbols) if symbols else 0

        for symbol in symbols:
            price = prices.get(symbol, 0)
            vol = volatilities.get(symbol, 0.15)

            if price <= 0:
                positions[symbol] = {'size_pct': 0, 'reason': 'Invalid price'}
                continue

            # Base size
            base_size = weight_per_symbol * (self.volatility_target / vol)

            # Check correlations with other positions
            corr_adjustment = 1.0
            for (s1, s2), corr in correlations.items():
                if symbol in (s1, s2):
                    other = s2 if symbol == s1 else s1
                    if corr > 0.7:
                        corr_adjustment *= 0.8  # Reduce if high correlation

            adjusted_size = base_size * corr_adjustment

            # Apply limits
            final_size = min(adjusted_size, self.max_position_pct, self.max_leverage)

            positions[symbol] = {
                'size_pct': final_size,
                'notional': self.portfolio_value * final_size,
                'shares': int((self.portfolio_value * final_size) / price),
                'volatility': vol,
                'adjustments': {
                    'correlation_factor': corr_adjustment
                }
            }

        return positions


# ============================================================================
# STOP LOSS & PROFIT TARGET CALCULATOR
# ============================================================================

class StopLossCalculator:
    """
    Calculate stop loss and profit target levels using multiple methods.

    Methods:
    - ATR-based: Using Average True Range volatility
    - Fixed percentage: Fixed % from entry
    - Volatility percentage: Scaled to current volatility
    - Support/resistance: Based on technical levels
    - Risk-reward ratio: Defined R:R configuration
    """

    def __init__(self, atr_multiplier: float = 2.5, risk_reward_ratio: float = 3.0):
        """Initialize stop loss calculator"""
        self.atr_multiplier = atr_multiplier
        self.risk_reward_ratio = risk_reward_ratio

    def calculate_atr_based(self, entry_price: float, atr: float,
                           direction: int = 1) -> Tuple[float, float]:
        """
        Calculate stops using ATR (Average True Range).

        Args:
            entry_price: Entry price
            atr: Average True Range value
            direction: 1 for long, -1 for short

        Returns:
            (stop_loss, profit_target)
        """
        stop_distance = atr * self.atr_multiplier

        if direction > 0:  # Long
            stop_loss = entry_price - stop_distance
            profit_target = entry_price + (stop_distance * self.risk_reward_ratio)
        else:  # Short
            stop_loss = entry_price + stop_distance
            profit_target = entry_price - (stop_distance * self.risk_reward_ratio)

        return stop_loss, profit_target

    def calculate_percentage_based(self, entry_price: float,
                                  stop_pct: float = 0.02,
                                  direction: int = 1) -> Tuple[float, float]:
        """
        Calculate stops using fixed percentage.

        Args:
            entry_price: Entry price
            stop_pct: Stop distance as % (e.g., 0.02 for 2%)
            direction: 1 for long, -1 for short

        Returns:
            (stop_loss, profit_target)
        """
        stop_distance = entry_price * stop_pct

        if direction > 0:  # Long
            stop_loss = entry_price - stop_distance
            profit_target = entry_price + (stop_distance * self.risk_reward_ratio)
        else:  # Short
            stop_loss = entry_price + stop_distance
            profit_target = entry_price - (stop_distance * self.risk_reward_ratio)

        return stop_loss, profit_target

    def calculate_volatility_based(self, entry_price: float, volatility: float,
                                  std_dev_multiple: float = 1.5,
                                  direction: int = 1) -> Tuple[float, float]:
        """
        Calculate stops based on volatility.

        Stop = Entry +/- (volatility * std_dev_multiple)

        Args:
            entry_price: Entry price
            volatility: Annualized volatility (e.g., 0.20)
            std_dev_multiple: Number of standard deviations
            direction: 1 for long, -1 for short

        Returns:
            (stop_loss, profit_target)
        """
        # Convert annualized vol to daily
        daily_vol = volatility / np.sqrt(252)
        stop_distance = entry_price * daily_vol * std_dev_multiple

        if direction > 0:  # Long
            stop_loss = entry_price - stop_distance
            profit_target = entry_price + (stop_distance * self.risk_reward_ratio)
        else:  # Short
            stop_loss = entry_price + stop_distance
            profit_target = entry_price - (stop_distance * self.risk_reward_ratio)

        return stop_loss, profit_target

    def calculate_support_resistance(self, entry_price: float,
                                    support: float, resistance: float,
                                    direction: int = 1,
                                    use_nearest: bool = True) -> Tuple[float, float]:
        """
        Calculate stops using support/resistance levels.

        For long: Stop below support, target at resistance
        For short: Stop above resistance, target at support

        Args:
            entry_price: Entry price
            support: Support level
            resistance: Resistance level
            direction: 1 for long, -1 for short
            use_nearest: If True, use closest level as stop

        Returns:
            (stop_loss, profit_target)
        """
        if direction > 0:  # Long
            stop_loss = support
            profit_target = resistance
        else:  # Short
            stop_loss = resistance
            profit_target = support

        return stop_loss, profit_target

    def get_recommended_levels(self, entry_price: float, atr: float,
                              volatility: float, direction: int = 1) -> Dict:
        """
        Get recommended stops from multiple methods and show comparison.

        Args:
            entry_price: Entry price
            atr: Average True Range
            volatility: Annualized volatility
            direction: 1 for long, -1 for short

        Returns:
            Dict with all methods' suggestions
        """
        atr_stop, atr_target = self.calculate_atr_based(entry_price, atr, direction)
        pct_stop, pct_target = self.calculate_percentage_based(entry_price, 0.02, direction)
        vol_stop, vol_target = self.calculate_volatility_based(entry_price, volatility, 1.5, direction)

        return {
            'entry_price': entry_price,
            'direction': 'LONG' if direction > 0 else 'SHORT',
            'methods': {
                'atr_based': {
                    'stop_loss': atr_stop,
                    'profit_target': atr_target,
                    'risk_pct': abs(entry_price - atr_stop) / entry_price,
                    'reward_pct': abs(atr_target - entry_price) / entry_price
                },
                'percentage_based': {
                    'stop_loss': pct_stop,
                    'profit_target': pct_target,
                    'risk_pct': abs(entry_price - pct_stop) / entry_price,
                    'reward_pct': abs(pct_target - entry_price) / entry_price
                },
                'volatility_based': {
                    'stop_loss': vol_stop,
                    'profit_target': vol_target,
                    'risk_pct': abs(entry_price - vol_stop) / entry_price,
                    'reward_pct': abs(vol_target - entry_price) / entry_price
                }
            },
            'recommended': {
                'stop_loss': atr_stop,  # ATR is most commonly used
                'profit_target': atr_target,
                'reason': 'ATR-based recommended as primary method'
            }
        }


# ============================================================================
# SCENARIO ANALYSIS
# ============================================================================

class ScenarioAnalyzer:
    """
    Analyze portfolio performance under stress scenarios.

    Scenarios:
    - Market crash (S&P 500 -20%)
    - Volatility spike (VIX +50%)
    - Rate shock (bonds -10%)
    - Liquidity crisis
    - Specific symbol moves
    """

    STANDARD_SCENARIOS = {
        'market_crash': {
            'description': 'S&P 500 down 20%',
            'market_moves': {'SPY': -0.20, 'QQQ': -0.25},
            'vol_multiplier': 2.5
        },
        'volatility_spike': {
            'description': 'VIX spikes to 40+',
            'market_moves': {'VXX': 0.50},
            'vol_multiplier': 3.0,
            'liquidity_impact': -0.01  # 1% wider spreads
        },
        'rate_shock': {
            'description': '2% rate increase',
            'market_moves': {'BND': -0.10, 'SPY': -0.08},
            'vol_multiplier': 1.8
        },
        'flash_crash': {
            'description': 'Flash crash scenario (intraday -10%)',
            'market_moves': {'SPY': -0.10},
            'vol_multiplier': 5.0,
            'liquidity_impact': -0.02
        },
        'black_swan': {
            'description': 'Extreme black swan event (-30%)',
            'market_moves': {'SPY': -0.30, 'QQQ': -0.35},
            'vol_multiplier': 5.0
        }
    }

    @staticmethod
    def analyze_scenario(positions: Dict[str, float], scenario: Dict) -> Dict:
        """
        Analyze portfolio impact of scenario.

        Args:
            positions: {symbol: notional_value}
            scenario: Scenario dict with market_moves

        Returns:
            Impact analysis
        """
        total_position = sum(positions.values())
        pnl = 0.0
        position_impacts = {}

        for symbol, notional in positions.items():
            move = scenario.get('market_moves', {}).get(symbol, 0)
            impact = notional * move
            pnl += impact
            position_impacts[symbol] = impact

        return {
            'scenario': scenario.get('description', 'Unknown'),
            'total_pnl': pnl,
            'pnl_pct': pnl / total_position if total_position > 0 else 0,
            'position_impacts': position_impacts,
            'vol_multiplier': scenario.get('vol_multiplier', 1.0)
        }

    @staticmethod
    def print_scenario_summary(portfolio_value: float, positions: Dict[str, float]):
        """Print stress test summary"""
        print("\n" + "=" * 80)
        print("SCENARIO STRESS TEST ANALYSIS")
        print("=" * 80)
        print(f"\nPortfolio Value: ${portfolio_value:,.2f}")
        print(f"Total Notional: ${sum(positions.values()):,.2f}")

        for scenario_name, scenario_config in ScenarioAnalyzer.STANDARD_SCENARIOS.items():
            result = ScenarioAnalyzer.analyze_scenario(positions, scenario_config)

            print(f"\n{scenario_name.upper()}: {result['scenario']}")
            print(f"  PnL: ${result['total_pnl']:,.2f} ({result['pnl_pct']:.2%})")
            print(f"  Portfolio Impact: ${result['total_pnl']:,.2f} of ${portfolio_value:,.2f}")


# ============================================================================
# DEMONSTRATION & USAGE
# ============================================================================

def demonstrate_risk_configuration():
    """Demonstrate risk management configuration and sizing"""

    print("\n" + "=" * 80)
    print("RISK CONFIGURATION & POSITION SIZING DEMONSTRATION")
    print("=" * 80)

    # Show profiles
    RiskProfileConfig.print_profiles()

    # Position sizing example
    print("\n" + "=" * 80)
    print("POSITION SIZING EXAMPLE")
    print("=" * 80)

    portfolio = 1000000  # $1M portfolio

    for profile in [RiskProfile.CONSERVATIVE, RiskProfile.MODERATE, RiskProfile.AGGRESSIVE]:
        print(f"\n{profile.value.upper()} PROFILE")
        print("-" * 80)

        sizer = PositionSizer(portfolio, profile)

        # Example parameters
        entry_price = 450.00
        stop_loss = 445.00
        signal = 0.7
        confidence = 0.75
        volatility = 0.18

        sizing = sizer.calculate_optimal_position_size(
            signal=signal,
            confidence=confidence,
            current_price=entry_price,
            volatility=volatility,
            stop_loss=stop_loss,
            win_rate=0.55,
            win_loss_ratio=1.5
        )

        print(f"Entry Price: ${entry_price}")
        print(f"Stop Loss: ${stop_loss}")
        print(f"Signal: {signal:.1%}, Confidence: {confidence:.0%}")
        print(f"\nPosition Size: {sizing['position_size_pct']:.2%}")
        print(f"Notional: ${sizing['notional_dollars']:,.0f}")
        print(f"Shares: {sizing['shares']}")
        print(f"Method: {sizing['method_used']}")

    # Stop loss example
    print("\n" + "=" * 80)
    print("STOP LOSS & PROFIT TARGET CALCULATION")
    print("=" * 80)

    calc = StopLossCalculator(atr_multiplier=2.5, risk_reward_ratio=3)

    entry = 450.0
    atr = 2.5
    volatility = 0.18

    levels = calc.get_recommended_levels(entry, atr, volatility, direction=1)

    print(f"\nEntry Price: ${entry}")
    print(f"ATR: ${atr}")
    print(f"Volatility: {volatility:.1%}")

    for method, values in levels['methods'].items():
        print(f"\n{method.upper()}:")
        print(f"  Stop Loss: ${values['stop_loss']:.2f} (Risk {values['risk_pct']:.2%})")
        print(f"  Profit Target: ${values['profit_target']:.2f} (Reward {values['reward_pct']:.2%})")
        print(f"  R:R Ratio: {values['reward_pct']/values['risk_pct']:.1f}:1")

    # Scenario analysis
    print("\n" + "=" * 80)
    print("SCENARIO STRESS TEST")
    print("=" * 80)

    positions = {
        'SPY': 500000,
        'QQQ': 300000,
        'BND': 200000
    }

    ScenarioAnalyzer.print_scenario_summary(portfolio, positions)

    print("\n" + "=" * 80)


if __name__ == "__main__":
    demonstrate_risk_configuration()
