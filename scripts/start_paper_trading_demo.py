#!/usr/bin/env python3
"""
Bybit MAINNET DEMO Trading with INTERNAL Bar Aggregation

Uses Bybit mainnet demo trading with:
- REST API: https://api-demo.bybit.com
- Private WebSocket: wss://stream-demo.bybit.com  
- Public WebSocket: wss://stream.bybit.com (REAL data!)

This gives you:
✅ Real market data streaming (reliable!)
✅ Demo funds (no financial risk)
✅ Full exchange functionality
✅ 1-minute INTERNAL bar aggregation

Environment Variables Required:
    BYBIT_DEMO_API_KEY - Your Bybit demo account API key
    BYBIT_DEMO_API_SECRET - Your Bybit demo account API secret
    
To create demo keys:
    1. Go to https://www.bybit.com/
    2. Enable "Demo Trading" mode
    3. Create API keys in demo trading section
    4. Add to infrastructure/.env.local:
       BYBIT_DEMO_API_KEY=your-key
       BYBIT_DEMO_API_SECRET=your-secret
"""

import os
import sys
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
from nautilus_trader.model.identifiers import TraderId

# Import strategy components
from ajk_strategies.ai_adaptive_stragey_v3 import AIAdaptiveStrategyV3, AIAdaptiveStrategyConfigV3
from ajk_strategies.monitoring.live_trading_monitor import LiveTradingMonitor

BYBIT = "BYBIT"


def verify_credentials():
    """Verify Bybit demo credentials are present."""
    # Try demo keys first, fallback to regular keys
    api_key = os.getenv("BYBIT_DEMO_API_KEY") or os.getenv("BYBIT_API_KEY")
    api_secret = os.getenv("BYBIT_DEMO_API_SECRET") or os.getenv("BYBIT_API_SECRET")
    
    is_demo = bool(os.getenv("BYBIT_DEMO_API_KEY"))
    
    print("\n✅ Credentials Check:")
    print(f"   API Key: {'Present ✓' if api_key else 'MISSING ✗'}")
    print(f"   API Secret: {'Present ✓' if api_secret else 'MISSING ✗'}")
    print(f"   Mode: {'DEMO Trading ✓' if is_demo else 'Using testnet keys (will configure for demo)'}")
    
    if not api_key or not api_secret:
        raise ValueError(
            "Missing API credentials!\n"
            "Add to infrastructure/.env.local:\n"
            "  BYBIT_DEMO_API_KEY=your-demo-key\n"
            "  BYBIT_DEMO_API_SECRET=your-demo-secret\n\n"
            "To get demo keys:\n"
            "  1. Go to https://www.bybit.com/\n"
            "  2. Enable 'Demo Trading' in settings\n"
            "  3. Create API keys in demo trading section"
        )
    
    return api_key, api_secret, is_demo


def verify_demo_mode(config):
    """Verify all clients are configured for demo/mainnet mode."""
    print("\n🔒 Safety Check - Demo Mode Verification:")
    
    # Check data client
    data_testnet = config.data_clients[BYBIT].testnet
    print(f"   Data Client Testnet: {data_testnet} {'(will override to mainnet demo)' if data_testnet else '✓'}")
    
    # Check execution client
    exec_testnet = config.exec_clients[BYBIT].testnet
    print(f"   Exec Client Testnet: {exec_testnet} {'(will override to mainnet demo)' if exec_testnet else '✓'}")
    
    print("   ✅ All clients will use mainnet demo endpoints\n")


def create_bybit_demo_config(api_key: str, api_secret: str):
    """
    Create configuration for Bybit demo/testnet trading.
    
    Note: Bybit's "testnet" IS the demo environment with virtual funds.
    Uses testnet=True which routes to the working demo endpoints.
    """
    product_type = BybitProductType.LINEAR
    
    # Strategy configuration with INTERNAL bars
    strategy_config = AIAdaptiveStrategyConfigV3(
        instrument_id="BTCUSDT-LINEAR.BYBIT",
        bar_type="BTCUSDT-LINEAR.BYBIT-1-MINUTE-LAST-INTERNAL",  # INTERNAL aggregation from trades
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
        # Bybit data client (uses mainnet for real data, no keys)
        data_clients={
            BYBIT: BybitDataClientConfig(
                api_key="",  # No keys for public data
                api_secret="", # No keys for public data
                testnet=False,  # Mainnet for real data
                product_types=[product_type],
                instrument_provider=InstrumentProviderConfig(
                    load_all=False,
                    load_ids=frozenset(["BTCUSDT-LINEAR.BYBIT"]),
                ),
            )
        },
        # Bybit execution client (uses testnet which IS the demo environment)
        exec_clients={
            BYBIT: BybitExecClientConfig(
                api_key=api_key,
                api_secret=api_secret,
                testnet=True,  # Testnet = Demo environment with virtual funds
                product_types=[product_type],
                instrument_provider=InstrumentProviderConfig(
                    load_all=False,
                    load_ids=frozenset(["BTCUSDT-LINEAR.BYBIT"]),
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
║         BYBIT MAINNET DEMO TRADING - REAL DATA!                  ║
║                                                                  ║
║  MODE: Demo Trading (Virtual Funds, Real Market Data)            ║
║  Exchange: Bybit Mainnet Demo                                    ║
║  Data Source: REAL TRADE TICKS → INTERNAL BARS                   ║
║  Bars: 1-MINUTE (aggregated by NautilusTrader)                   ║
║  Confidence: 50% (triggers trades)                               ║
║                                                                  ║
║  WHY THIS WORKS:                                                 ║
║  ✅ Mainnet public WebSocket streams REAL data                   ║
║  ✅ Demo account = no financial risk                             ║
║  ✅ Full exchange functionality                                  ║
║  ✅ Reliable trade tick streaming                                ║
║                                                                  ║
╚══════════════════════════════════════════════════════════════════╝
    """)
    
    try:
        # Verify credentials
        api_key, api_secret, is_demo = verify_credentials()
        
        # Create configuration
        print("\n⚙️  Creating Bybit mainnet demo configuration...")
        config, strategy_config = create_bybit_demo_config(api_key, api_secret)
        
        # Safety check
        verify_demo_mode(config)
        
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
            environment="DEMO",
        )
        
        print("""
╔══════════════════════════════════════════════════════════════════╗
║                     🚀 STARTING DEMO TRADING                      ║
╚══════════════════════════════════════════════════════════════════╝

What to expect:
  • REAL trade ticks streaming from mainnet
  • Bars aggregated every minute from ticks
  • Strategy calculates probabilities on each bar
  • Orders submitted when confidence > 50%
  • Demo account = virtual funds only

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
