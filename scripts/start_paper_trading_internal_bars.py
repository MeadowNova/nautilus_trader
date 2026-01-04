#!/usr/bin/env python3
"""
Paper trading with INTERNAL bar aggregation.

This script subscribes to TRADE TICKS and lets NautilusTrader aggregate bars,
bypassing the testnet WebSocket kline streaming issues.

Strategy: AI Adaptive Strategy V3
Exchange: Bybit Testnet (proven to work)
Bars: 1-MINUTE (INTERNAL aggregation from trade ticks)
Confidence Threshold: 50%
"""

import os
import sys
from decimal import Decimal
from pathlib import Path
from dotenv import load_dotenv

# Add project root to path FIRST
project_root = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(project_root))

# Load environment variables from .env.local
env_file = project_root / "infrastructure" / ".env.local"
if env_file.exists():
    load_dotenv(env_file)
    print(f"✅ Loaded environment from: {env_file}")
else:
    print(f"⚠️  Warning: {env_file} not found")

from nautilus_trader.adapters.bybit.common.enums import BybitProductType
from nautilus_trader.adapters.bybit.config import BybitDataClientConfig
from nautilus_trader.adapters.bybit.config import BybitExecClientConfig
from nautilus_trader.adapters.bybit.factories import BybitLiveDataClientFactory
from nautilus_trader.adapters.bybit.factories import BybitLiveExecClientFactory
from nautilus_trader.config import InstrumentProviderConfig
from nautilus_trader.config import LiveExecEngineConfig
from nautilus_trader.config import LoggingConfig
from nautilus_trader.config import TradingNodeConfig
from nautilus_trader.live.node import TradingNode
from nautilus_trader.model.identifiers import InstrumentId
from nautilus_trader.model.identifiers import TraderId
from nautilus_trader.model.data import BarType
from nautilus_trader.model.enums import AggregationSource
from nautilus_trader.core.datetime import secs_to_nanos

# Import strategy components
from ajk_strategies.ai_adaptive_stragey_v3 import AIAdaptiveStrategyV3, AIAdaptiveStrategyConfigV3
from ajk_strategies.monitoring.live_trading_monitor import LiveTradingMonitor

BYBIT = "BYBIT"


def verify_credentials():
    """Verify Bybit testnet credentials are present."""
    api_key = os.getenv("BYBIT_API_KEY")
    api_secret = os.getenv("BYBIT_API_SECRET")
    testnet = os.getenv("BYBIT_TESTNET", "false").lower() == "true"
    
    print("\n✅ Credentials Check:")
    print(f"   API Key: {'Present ✓' if api_key else 'MISSING ✗'}")
    print(f"   API Secret: {'Present ✓' if api_secret else 'MISSING ✗'}")
    print(f"   Testnet Mode: {'Enabled ✓' if testnet else 'DISABLED ✗ (WARNING!)'}")
    
    if not api_key or not api_secret:
        raise ValueError("Missing BYBIT_API_KEY or BYBIT_API_SECRET environment variables")
    
    if not testnet:
        raise ValueError("BYBIT_TESTNET must be set to 'true' for paper trading")
    
    return api_key, api_secret


def verify_testnet_mode(config):
    """Verify all clients are in testnet mode."""
    print("\n🔒 Safety Check - Testnet Mode Verification:")
    
    # Check data client
    data_testnet = config.data_clients[BYBIT].testnet
    print(f"   Data Client Testnet: {data_testnet} {'✓' if data_testnet else '✗ DANGER'}")
    
    # Check execution client
    exec_testnet = config.exec_clients[BYBIT].testnet
    print(f"   Exec Client Testnet: {exec_testnet} {'✓' if exec_testnet else '✗ DANGER'}")
    
    if not data_testnet or not exec_testnet:
        raise ValueError("ALL clients MUST be in testnet mode for paper trading!")
    
    print("   ✅ All clients verified as testnet mode\n")


def create_bybit_internal_bars_config(api_key: str, api_secret: str):
    """
    Create configuration for Bybit paper trading with INTERNAL bar aggregation.
    
    INTERNAL bars = NautilusTrader aggregates bars from trade ticks
    This bypasses the testnet WebSocket kline streaming issues.
    """
    # Bybit LINEAR (perpetual futures)
    product_type = BybitProductType.LINEAR
    
    # Strategy configuration with INTERNAL bars
    strategy_config = AIAdaptiveStrategyConfigV3(
        instrument_id="BTCUSDT-LINEAR.BYBIT",
        bar_type="BTCUSDT-LINEAR.BYBIT-1-MINUTE-LAST-INTERNAL",  # INTERNAL aggregation!
        venue="BYBIT",
        confidence_threshold=0.50,  # 50% - triggers trades at observed levels
        enable_monte_carlo=True,
        max_bars_in_position=30,  # 30 minutes max hold
        max_bars_per_run=None,
    )
    
    # Trading node configuration
    config = TradingNodeConfig(
        trader_id=TraderId("PAPER-TRADER-001"),
        logging=LoggingConfig(
            log_level="INFO",
            log_level_file="DEBUG",
            log_directory="logs",
        ),
        exec_engine=LiveExecEngineConfig(
            reconciliation=True,
            inflight_check_interval_ms=2000,
        ),
        # Bybit data client (testnet)
        data_clients={
            BYBIT: BybitDataClientConfig(
                api_key=api_key,
                api_secret=api_secret,
                testnet=True,
                product_types=[product_type],
                instrument_provider=InstrumentProviderConfig(
                    load_all=False,
                    load_ids=("BTCUSDT-LINEAR.BYBIT",),
                ),
            )
        },
        # Bybit execution client (testnet)
        exec_clients={
            BYBIT: BybitExecClientConfig(
                api_key=api_key,
                api_secret=api_secret,
                testnet=True,
                product_types=[product_type],
                instrument_provider=InstrumentProviderConfig(
                    load_all=False,
                    load_ids=("BTCUSDT-LINEAR.BYBIT",),
                ),
                max_retries=3,
            )
        },
    )
    
    return config, strategy_config


def main():
    print("""
╔══════════════════════════════════════════════════════════════════╗
║                                                                  ║
║         BYBIT TESTNET - INTERNAL BAR AGGREGATION                 ║
║                                                                  ║
║  MODE: Paper Trading (Testnet Only)                              ║
║  Exchange: Bybit Testnet (LINEAR)                                ║
║  Data Source: TRADE TICKS → INTERNAL BARS                        ║
║  Bars: 1-MINUTE (aggregated by NautilusTrader)                   ║
║  Confidence: 50% (triggers trades)                               ║
║                                                                  ║
║  WHY: Bypasses testnet WebSocket kline streaming issues          ║
║  HOW: Subscribes to trade ticks, aggregates bars locally         ║
║                                                                  ║
╚══════════════════════════════════════════════════════════════════╝
    """)
    
    try:
        # Verify credentials
        api_key, api_secret = verify_credentials()
        
        # Create configuration
        print("\n⚙️  Creating Bybit testnet configuration (INTERNAL bars)...")
        config, strategy_config = create_bybit_internal_bars_config(api_key, api_secret)
        
        # Critical safety check
        verify_testnet_mode(config)
        
        # Create trading node
        print("\n🔧 Initializing trading node...")
        node = TradingNode(config=config)
        
        # Add strategy BEFORE building
        print("📊 Adding AI Adaptive Strategy V3...")
        strategy = AIAdaptiveStrategyV3(config=strategy_config)
        node.trader.add_strategy(strategy)
        
        # Add Bybit factories
        node.add_data_client_factory(BYBIT, BybitLiveDataClientFactory)
        node.add_exec_client_factory(BYBIT, BybitLiveExecClientFactory)
        
        # Build the node
        print("🔨 Building trading node...")
        node.build()
        
        # Initialize monitoring (subscribes to events automatically)
        print("📈 Initializing Live Trading Monitor...")
        monitor = LiveTradingMonitor(
            msgbus=node.kernel.msgbus,
            trader_id=config.trader_id,
            strategy_id=strategy.id,
            environment="TESTNET",
        )
        
        print("""
╔══════════════════════════════════════════════════════════════════╗
║                     🚀 STARTING PAPER TRADING                     ║
╚══════════════════════════════════════════════════════════════════╝

What to expect:
  • Trade ticks will start streaming immediately
  • Bars will be aggregated every minute from ticks
  • Strategy will calculate probabilities on each bar
  • Orders submitted when confidence > 50%

Monitoring:
  • Logs: logs/PAPER-TRADER-001_*.log
  • Database: Docker container nautilus_postgres
  • Grafana: http://localhost:3000

Press Ctrl+C to stop
        """)
        
        # Start the trading node (blocks until interrupted)
        node.run()
        
        # Stop monitoring on shutdown
        monitor.stop()
        
    except KeyboardInterrupt:
        print("\n\n⏹️  Shutting down gracefully...")
        if 'monitor' in locals():
            monitor.stop()
        if 'node' in locals():
            node.stop()
    except Exception as e:
        print(f"\n\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
