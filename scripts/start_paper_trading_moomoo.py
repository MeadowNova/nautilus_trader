#!/usr/bin/env python3
"""
Moomoo OpenD Paper Trading with RL-Enhanced Strategies

This script orchestrates paper trading using the Moomoo OpenD API
with reinforcement learning enhanced strategies for:
1. Statistical Arbitrage Pairs Trading (XLE/XLF)
2. Momentum Breakout Trading (NVDA, AMD, META)
3. (Optional) Covered Call Income Strategy

REQUIREMENTS:
- OpenD running on localhost:11111
- Moomoo account with paper trading enabled
- moomoo-api Python package installed

Usage:
    python scripts/start_paper_trading_moomoo.py

Environment Variables (optional):
    MOOMOO_HOST - OpenD host (default: 127.0.0.1)
    MOOMOO_PORT - OpenD port (default: 11111)
"""

import asyncio
import os
import sys
import signal
from datetime import datetime
from pathlib import Path

# Add project root to path
project_root = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(project_root))

from nautilus_trader.live.node import TradingNode
from nautilus_trader.config import (
    TradingNodeConfig,
    LoggingConfig,
    InstrumentProviderConfig,
)
from nautilus_trader.model.identifiers import TraderId

# Import Moomoo adapter components
from nautilus_trader.adapters.moomoo import MOOMOO
from nautilus_trader.adapters.moomoo.config import (
    MoomooGatewayConfig,
    MoomooDataClientConfig,
    MoomooExecClientConfig,
)
from nautilus_trader.adapters.moomoo.factories import (
    MoomooLiveDataClientFactory,
    MoomooLiveExecClientFactory,
)

# Import RL strategies
from ajk_strategies.rl_strategies import (
    RLPairsTradingStrategy,
    RLPairsTradingConfig,
    RLMomentumBreakoutStrategy,
    RLMomentumBreakoutConfig,
)

# Import RL framework components
from ajk_strategies.rl_framework.training.experience_buffer import PrioritizedReplayBuffer
from ajk_strategies.rl_framework.training.trainer import RLTrainer, TrainingConfig
from ajk_strategies.rl_framework.agents.base_agent import SimpleRuleAgent, AgentConfig


def verify_openD_connection():
    """Verify OpenD is running and accessible."""
    try:
        from moomoo import OpenQuoteContext, OpenSecTradeContext, TrdEnv

        host = os.getenv("MOOMOO_HOST", "127.0.0.1")
        port = int(os.getenv("MOOMOO_PORT", "11111"))

        print(f"Verifying OpenD connection at {host}:{port}...")

        # Test quote context
        quote_ctx = OpenQuoteContext(host=host, port=port)
        ret, data = quote_ctx.get_global_state()

        if ret != 0:
            raise RuntimeError(f"OpenD quote context error: {data}")

        market_state = data.get('market_us', 'UNKNOWN')
        print(f"  Market state (US): {market_state}")

        # Test trade context (paper trading)
        trade_ctx = OpenSecTradeContext(host=host, port=port)
        ret, data = trade_ctx.get_acc_list()

        if ret != 0:
            print(f"  Warning: Could not get account list: {data}")
        else:
            # data is a DataFrame, filter for paper trading accounts
            if hasattr(data, 'iterrows'):
                paper_accounts = [row for _, row in data.iterrows() if row.get('trd_env') == TrdEnv.SIMULATE]
                print(f"  Paper trading accounts: {len(paper_accounts)}")
            else:
                print(f"  Account list retrieved: {type(data)}")

        quote_ctx.close()
        trade_ctx.close()

        print("OpenD connection verified successfully")
        return True

    except ImportError:
        raise RuntimeError(
            "moomoo-api package not installed!\n"
            "Install with: pip install moomoo-api"
        )
    except Exception as e:
        raise RuntimeError(f"OpenD connection failed: {e}")


def create_moomoo_paper_trading_config():
    """Create Moomoo paper trading configuration."""

    host = os.getenv("MOOMOO_HOST", "127.0.0.1")
    port = int(os.getenv("MOOMOO_PORT", "11111"))

    # Gateway configuration
    gateway_config = MoomooGatewayConfig(
        host=host,
        port=port,
        trading_mode="SIMULATE",  # Paper trading
    )

    # Instruments to trade
    pairs_instruments = ("XLE.MOOMOO", "XLF.MOOMOO")
    momentum_instruments = ("NVDA.MOOMOO", "AMD.MOOMOO", "META.MOOMOO")
    benchmark_instrument = ("SPY.MOOMOO",)
    all_instruments = pairs_instruments + momentum_instruments + benchmark_instrument

    config = TradingNodeConfig(
        trader_id=TraderId("MOOMOO-RL-PAPER-001"),

        # Logging configuration
        logging=LoggingConfig(
            log_level="INFO",
            log_level_file="DEBUG",
            log_directory="logs",
            log_colors=True,
        ),

        # Moomoo data client
        data_clients={
            "MOOMOO": MoomooDataClientConfig(
                gateway=gateway_config,
                use_extended_hours=False,
                subscription_quota=1000,
                instrument_provider=InstrumentProviderConfig(
                    load_all=False,
                    load_ids=all_instruments,
                ),
            )
        },

        # Moomoo execution client
        exec_clients={
            "MOOMOO": MoomooExecClientConfig(
                gateway=gateway_config,
                filter_trd_market="US",
                max_orders_per_30s=15,
                instrument_provider=InstrumentProviderConfig(
                    load_all=False,
                    load_ids=all_instruments,
                ),
            )
        },
    )

    return config


def create_rl_components():
    """Create shared RL components for strategies."""

    # Create experience buffer (shared across strategies)
    experience_buffer = PrioritizedReplayBuffer(
        capacity=100000,
        alpha=0.6,
        beta=0.4,
    )

    # Create RL agent (start with simple rule-based agent)
    # Will be replaced with trained PPO/SAC agent later
    agent_config = AgentConfig(
        state_dim=75,  # StateBuilder output + strategy-specific features
        action_dim=4,  # HOLD, BUY, SELL, EXIT
        epsilon=0.1,
        epsilon_min=0.01,
        epsilon_decay=0.995,
    )
    rl_agent = SimpleRuleAgent(config=agent_config)

    return rl_agent, experience_buffer


def create_strategies(rl_agent, experience_buffer):
    """Create RL-enhanced trading strategies."""

    strategies = []

    # 1. Pairs Trading Strategy (XLE/XLF)
    # Parameters optimized per quant-analyst recommendations
    pairs_config = RLPairsTradingConfig(
        instrument_id_a="XLE.MOOMOO",
        instrument_id_b="XLF.MOOMOO",
        lookback_period=40,           # Reduced from 60 for faster adaptation
        zscore_entry=2.25,            # Increased from 2.0 for better signal quality
        zscore_exit=0.25,             # Reduced from 0.5 for fuller mean reversion capture
        zscore_stop=3.5,              # Increased from 3.0 for wider stops
        position_size_pct=0.08,       # Reduced from 0.10 per risk-manager (8% per leg)
        max_holding_bars=80,          # Reduced from 100 for faster turnover
        use_rl=True,
    )

    pairs_strategy = RLPairsTradingStrategy(
        config=pairs_config,
        rl_agent=rl_agent,
        experience_buffer=experience_buffer,
    )
    strategies.append(pairs_strategy)

    # 2. Momentum Breakout Strategy (NVDA, AMD, META)
    # Parameters optimized per quant-analyst recommendations
    momentum_config = RLMomentumBreakoutConfig(
        instrument_ids=("NVDA.MOOMOO", "AMD.MOOMOO", "META.MOOMOO"),
        benchmark_id="SPY.MOOMOO",
        breakout_lookback=15,         # Reduced from 20 for faster breakout detection
        volume_multiplier=1.75,       # Increased from 1.5 for stronger volume confirmation
        rsi_period=14,
        rsi_min=50.0,                 # Reduced from 55.0 for wider entry window
        rsi_max=70.0,                 # Reduced from 75.0 to avoid overbought
        relative_strength_min=0.02,
        profit_target_atr=2.5,        # Increased from 2.0 for better R-multiple
        trailing_stop_atr=2.0,        # Increased from 1.5 for wider trailing
        position_size_pct=0.06,       # Reduced from 0.08 per risk-manager (6% per position)
        max_holding_bars=40,          # Reduced from 50 for faster turnover
        max_concurrent=2,             # Reduced from 3 per risk-manager
        use_rl=True,
    )

    momentum_strategy = RLMomentumBreakoutStrategy(
        config=momentum_config,
        rl_agent=rl_agent,
        experience_buffer=experience_buffer,
    )
    strategies.append(momentum_strategy)

    return strategies


class TradingOrchestrator:
    """Orchestrates paper trading with RL training."""

    def __init__(self, node, rl_agent, experience_buffer):
        self.node = node
        self.rl_agent = rl_agent
        self.experience_buffer = experience_buffer
        self.trainer = None
        self._running = False
        self._train_task = None

    def setup_trainer(self):
        """Setup RL trainer for periodic training."""
        train_config = TrainingConfig(
            batch_size=64,
            min_buffer_size=1000,
            train_every_n=100,
            epochs_per_train=10,
            learning_rate=3e-4,
            gamma=0.99,
            ewc_lambda=1000.0,
        )

        self.trainer = RLTrainer(
            agent=self.rl_agent,
            buffer=self.experience_buffer,
            config=train_config,
        )

    async def training_loop(self):
        """Background training loop."""
        print("\nStarting background RL training loop...")

        while self._running:
            try:
                # Train if enough experiences collected
                if self.trainer.should_train():
                    metrics = await self.trainer.train_step()
                    if metrics:
                        print(
                            f"Training step: epoch={metrics.epoch}, "
                            f"policy_loss={metrics.policy_loss:.4f}, "
                            f"td_error={metrics.td_error_mean:.4f}"
                        )

                # Sleep between training attempts
                await asyncio.sleep(60)  # Check every minute

            except Exception as e:
                print(f"Training loop error: {e}")
                await asyncio.sleep(60)

    def start(self):
        """Start the orchestrator."""
        self._running = True
        self.setup_trainer()

        # Start training loop in background
        loop = asyncio.get_event_loop()
        self._train_task = loop.create_task(self.training_loop())

    def stop(self):
        """Stop the orchestrator."""
        self._running = False
        if self._train_task:
            self._train_task.cancel()

        # Save model checkpoint
        if self.trainer:
            checkpoint_path = f"models/moomoo_rl_agent_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pt"
            Path("models").mkdir(exist_ok=True)
            self.trainer.save_checkpoint(checkpoint_path)
            print(f"Saved model checkpoint: {checkpoint_path}")

        # Log training summary
        if self.trainer:
            summary = self.trainer.get_training_summary()
            if summary:
                print(f"\nTraining Summary:")
                print(f"  Total epochs: {summary.get('total_epochs', 0)}")
                print(f"  Buffer size: {summary.get('buffer_size', 0)}")
                print(f"  Avg policy loss: {summary.get('avg_policy_loss', 0):.4f}")


def main():
    print("""

    MOOMOO OPEND PAPER TRADING - RL ENHANCED STRATEGIES

    MODE: Paper Trading with Reinforcement Learning
    Gateway: Moomoo OpenD (localhost:11111)

    Strategies:
    1. RL Pairs Trading (XLE/XLF)
       - Mean reversion with z-score signals
       - RL learns optimal entry/exit timing

    2. RL Momentum Breakout (NVDA, AMD, META)
       - Technical breakout with volume confirmation
       - RL learns to "see out" winning trades

    RL Features:
    - "Seeing Out" reward bonus for capturing 80%+ of moves
    - N-step TD credit assignment
    - Prioritized experience replay
    - Elastic Weight Consolidation (anti-forgetting)

    """)

    node = None
    orchestrator = None

    try:
        # Verify OpenD connection
        print("1. Verifying OpenD connection...")
        verify_openD_connection()

        # Create configuration
        print("\n2. Creating paper trading configuration...")
        config = create_moomoo_paper_trading_config()

        # Create RL components
        print("\n3. Initializing RL framework...")
        rl_agent, experience_buffer = create_rl_components()
        print(f"   Experience buffer capacity: {experience_buffer.capacity}")
        print(f"   Agent epsilon (exploration): {rl_agent.epsilon}")

        # Create trading node
        print("\n4. Initializing trading node...")
        node = TradingNode(config=config)

        # Register Moomoo client factories
        node.add_data_client_factory("MOOMOO", MoomooLiveDataClientFactory)
        node.add_exec_client_factory("MOOMOO", MoomooLiveExecClientFactory)

        # Create and add strategies
        print("\n5. Creating RL-enhanced strategies...")
        strategies = create_strategies(rl_agent, experience_buffer)
        for strategy in strategies:
            node.trader.add_strategy(strategy)
            print(f"   Added: {strategy.__class__.__name__}")

        # Build node
        node.build()

        # Create orchestrator for training management
        print("\n6. Initializing training orchestrator...")
        orchestrator = TradingOrchestrator(node, rl_agent, experience_buffer)
        orchestrator.start()

        print("\n" + "=" * 60)
        print("PAPER TRADING SYSTEM READY")
        print("=" * 60)
        print(f"\nTrader ID: {config.trader_id}")
        print(f"Log directory: ./logs/")
        print(f"Model checkpoints: ./models/")
        print("\nActive Strategies:")
        print("  - RLPairsTradingStrategy (XLE/XLF)")
        print("  - RLMomentumBreakoutStrategy (NVDA, AMD, META)")
        print("\nRL Training:")
        print("  - Background training every 100 new experiences")
        print("  - Model saved on shutdown")
        print("\nPress Ctrl+C to stop trading\n")

        # Handle graceful shutdown
        def signal_handler(sig, frame):
            print("\n\nShutdown signal received...")
            if orchestrator:
                orchestrator.stop()
            if node:
                node.dispose()
            sys.exit(0)

        signal.signal(signal.SIGINT, signal_handler)
        signal.signal(signal.SIGTERM, signal_handler)

        # Run trading node (blocks until interrupted)
        node.run()

    except KeyboardInterrupt:
        print("\n\nShutdown signal received...")

    except Exception as e:
        print(f"\n\nError: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

    finally:
        try:
            if orchestrator:
                print("Stopping orchestrator...")
                orchestrator.stop()
            if node:
                print("Stopping trading node...")
                node.dispose()
            print("Shutdown complete\n")
        except Exception as e:
            print(f"Error during shutdown: {e}")


if __name__ == "__main__":
    main()
