#!/usr/bin/env python3
"""
Sandbox Paper Trading Launcher for AI-Adaptive Strategy

This version uses NautilusTrader's Sandbox execution client for simulated trading
without requiring any exchange API keys. Perfect for testing the monitoring pipeline
or when geo-restricted from exchanges.

Features:
- Uses historical data for market replay
- Simulates order execution in sandbox
- Full monitoring integration (PostgreSQL, Prometheus, Grafana)
- No API keys required
- No geo-restrictions

Usage:
    python scripts/start_paper_trading_sandbox.py

Data:
    Uses existing historical data from: data/nautilus/
"""

import os
import sys
from pathlib import Path
from decimal import Decimal
from dotenv import load_dotenv

# Add project root to path
project_root = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(project_root))

# Load environment variables from .env.local
env_file = project_root / "infrastructure" / ".env.local"
if env_file.exists():
    load_dotenv(env_file)
    print(f"✅ Loaded environment from: {env_file}")

from nautilus_trader.live.node import TradingNode
from nautilus_trader.config import (
    TradingNodeConfig,
    LoggingConfig,
    InstrumentProviderConfig,
)
from nautilus_trader.adapters.sandbox.config import SandboxExecutionClientConfig
from nautilus_trader.adapters.sandbox.factory import SandboxLiveExecClientFactory
from nautilus_trader.adapters.bybit import BYBIT
from nautilus_trader.adapters.bybit.config import BybitDataClientConfig
from nautilus_trader.adapters.bybit.factories import BybitLiveDataClientFactory
from nautilus_trader.adapters.bybit.common.enums import BybitProductType
from nautilus_trader.model.identifiers import InstrumentId, TraderId, Venue

from ajk_strategies.ai_adaptive_stragey_v3 import AIAdaptiveStrategyConfigV3


def verify_vpn():
    """Verify VPN is active (optional - only warns if not)"""
    import urllib.request
    try:
        response = urllib.request.urlopen('https://api-testnet.bybit.com/v5/market/time', timeout=5)
        if response.status == 200:
            print("✅ Connection to Bybit testnet successful")
            return True
    except Exception as e:
        print(f"⚠️  Warning: Cannot reach Bybit testnet: {e}")
        print("   If you're geo-restricted, enable VPN")
        return False


def create_sandbox_trading_config():
    """Create sandbox paper trading configuration"""
    
    # Use Bybit for data, Sandbox for execution
    product_type = BybitProductType.LINEAR
    
    # Get API keys from environment (for public data - authentication not critical)
    api_key = os.getenv("BYBIT_TESTNET_API_KEY") or os.getenv("BYBIT_API_KEY") or "test"
    api_secret = os.getenv("BYBIT_TESTNET_API_SECRET") or os.getenv("BYBIT_API_SECRET") or "test"
    
    config = TradingNodeConfig(
        trader_id=TraderId("SANDBOX-TRADER-001"),
        
        # Logging configuration
        logging=LoggingConfig(
            log_level="INFO",
            log_level_file="DEBUG",
            log_directory="logs",
            log_colors=True,
        ),
        
        # Bybit data client (PUBLIC data - uses existing keys)
        data_clients={
            BYBIT: BybitDataClientConfig(
                api_key=api_key,  # Use your keys for public data (works fine)
                api_secret=api_secret,
                testnet=True,
                product_types=[product_type],
                instrument_provider=InstrumentProviderConfig(
                    load_all=False,
                    load_ids=("BTCUSDT-LINEAR.BYBIT",),  # Tuple for hashability
                ),
            )
        },
        
        # Sandbox execution client (simulated trading)
        exec_clients={
            BYBIT: SandboxExecutionClientConfig(
                venue=BYBIT,
                starting_balances=[
                    "100000 USDT",  # Starting capital
                    "10 BTC",
                ],
                account_type="MARGIN",
                oms_type="NETTING",
                default_leverage=Decimal("1.0"),
                bar_execution=True,
                reject_stop_orders=False,
                support_gtd_orders=True,
                support_contingent_orders=True,
                use_position_ids=True,
            )
        },
    )
    
    return config


def main():
    print("""
╔══════════════════════════════════════════════════════════════════╗
║                                                                  ║
║           AI-ADAPTIVE SANDBOX PAPER TRADING SYSTEM               ║
║                                                                  ║
║  MODE: Sandbox Simulation (No API Keys Required)                ║
║  Data: Historical Replay                                         ║
║  Execution: Fully Simulated                                      ║
║                                                                  ║
╚══════════════════════════════════════════════════════════════════╝
    """)
    
    try:
        # Verify connection (optional)
        print("\n🔍 Checking Bybit testnet connection...")
        verify_vpn()
        
        # Create configuration
        print("\n⚙️  Creating sandbox configuration...")
        config = create_sandbox_trading_config()
        
        # Create trading node
        print("\n🔧 Initializing sandbox trading node...")
        node = TradingNode(config=config)
        
        # Configure strategy
        print("\n📊 Configuring AI-Adaptive strategy...")
        from ajk_strategies.ai_adaptive_stragey_v3 import AIAdaptiveStrategyV3
        
        strategy_config = AIAdaptiveStrategyConfigV3(
            instrument_id="BTCUSDT-LINEAR.BYBIT",  # Use Bybit instrument
            bar_type="BTCUSDT-LINEAR.BYBIT-1-MINUTE-LAST-EXTERNAL",  # Fastest Bybit supports
            venue="BYBIT",
            confidence_threshold=0.65,  # Lowered for more signals (was 0.75)
            enable_monte_carlo=True,
            max_bars_in_position=20,  # Shorter hold time (was 50 = 50min, now 30min)
            max_bars_per_run=None,  # No limit for live trading
        )
        
        # Instantiate strategy
        strategy = AIAdaptiveStrategyV3(config=strategy_config)
        
        # Add strategy to trader
        node.trader.add_strategy(strategy)
        
        # Register data and execution factories
        node.add_data_client_factory(BYBIT, BybitLiveDataClientFactory)
        node.add_exec_client_factory(BYBIT, SandboxLiveExecClientFactory)
        
        node.build()
        
        # Initialize monitoring
        print("\n📊 Initializing database monitoring...")
        from ajk_strategies.monitoring.live_trading_monitor import LiveTradingMonitor
        
        monitor = LiveTradingMonitor(
            msgbus=node.kernel.msgbus,
            trader_id=config.trader_id,
            strategy_id=strategy.id,
            environment="TESTNET",
        )
        
        print("\n✅ Sandbox paper trading system ready!")
        print("\n📊 Monitoring:")
        print("   - Grafana: http://localhost:3000")
        print("   - Prometheus: http://localhost:9090")
        print("   - Logs: ./logs/")
        print("\n💡 Features:")
        print("   ✅ Real market data from Bybit")
        print("   ✅ Simulated order execution")
        print("   ✅ Database monitoring active")
        print("   ✅ Metrics pipeline connected")
        print("   ✅ Safe - 100% paper trading")
        print("\n⚠️  Press Ctrl+C to stop trading\n")
        
        # Run trading node (blocks until interrupted)
        node.run()
        
        # Stop monitoring on shutdown
        monitor.stop()
    
    except KeyboardInterrupt:
        print("\n\n⏸️  Shutdown signal received...")
    
    except Exception as e:
        print(f"\n\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
    
    finally:
        try:
            print("🛑 Stopping trading node...")
            node.dispose()
            print("✅ Shutdown complete\n")
        except Exception as e:
            print(f"Error during shutdown: {e}")


if __name__ == "__main__":
    main()
