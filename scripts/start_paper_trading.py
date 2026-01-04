#!/usr/bin/env python3
"""
Paper Trading Launcher for AI-Adaptive Strategy

SAFETY: This script includes multiple safety checks to prevent accidental live trading.
Always verify testnet mode before starting.

Usage:
    python scripts/start_paper_trading.py

Environment Variables Required:
    BYBIT_TESTNET_API_KEY - Your Bybit testnet API key
    BYBIT_TESTNET_API_SECRET - Your Bybit testnet API secret

Get testnet keys from: https://testnet.bybit.com/
"""

import os
import sys
from pathlib import Path
from dotenv import load_dotenv

# Add project root to path
project_root = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(project_root))

# Load environment variables from .env.local
env_file = project_root / "infrastructure" / ".env.local"
if env_file.exists():
    load_dotenv(env_file)
    print(f"✅ Loaded environment from: {env_file}")
else:
    print(f"⚠️  No .env.local found at: {env_file}")
    print("   Will use system environment variables")

from nautilus_trader.live.node import TradingNode
from nautilus_trader.config import TradingNodeConfig, LoggingConfig, InstrumentProviderConfig
from nautilus_trader.adapters.bybit import BYBIT
from nautilus_trader.adapters.bybit.config import (
    BybitDataClientConfig,
    BybitExecClientConfig,
)
from nautilus_trader.adapters.bybit.common.enums import BybitProductType
from nautilus_trader.adapters.bybit.factories import (
    BybitLiveDataClientFactory,
    BybitLiveExecClientFactory,
)
from nautilus_trader.model.identifiers import InstrumentId, TraderId

from ajk_strategies.ai_adaptive_stragey_v3 import AIAdaptiveStrategyConfigV3


def verify_testnet_mode(config):
    """Verify all clients are in testnet mode"""
    for client_name, client_config in config.data_clients.items():
        if not getattr(client_config, 'testnet', False):
            raise RuntimeError(
                f"❌ CRITICAL: {client_name} data client NOT in testnet mode!\n"
                f"   For safety, paper trading requires testnet=True.\n"
                f"   Aborting to prevent accidental live trading."
            )
    
    for client_name, client_config in config.exec_clients.items():
        if not getattr(client_config, 'testnet', False):
            raise RuntimeError(
                f"❌ CRITICAL: {client_name} execution client NOT in testnet mode!\n"
                f"   For safety, paper trading requires testnet=True.\n"
                f"   Aborting to prevent accidental live trading."
            )
    
    print("✅ All clients verified as testnet mode")


def verify_credentials():
    """Check API credentials are set"""
    # Try both naming conventions
    api_key = os.getenv("BYBIT_TESTNET_API_KEY") or os.getenv("BYBIT_API_KEY")
    api_secret = os.getenv("BYBIT_TESTNET_API_SECRET") or os.getenv("BYBIT_API_SECRET")
    
    if not api_key:
        raise RuntimeError(
            "❌ BYBIT API KEY not set!\n"
            "   Add to infrastructure/.env.local: BYBIT_API_KEY=your-key\n"
            "   Or export: BYBIT_TESTNET_API_KEY='your-key-here'\n"
            "   Get testnet keys from: https://testnet.bybit.com/"
        )
    
    if not api_secret:
        raise RuntimeError(
            "❌ BYBIT API SECRET not set!\n"
            "   Add to infrastructure/.env.local: BYBIT_API_SECRET=your-secret\n"
            "   Or export: BYBIT_TESTNET_API_SECRET='your-secret-here'"
        )
    
    # Set standardized env vars for NautilusTrader
    os.environ["BYBIT_TESTNET_API_KEY"] = api_key
    os.environ["BYBIT_TESTNET_API_SECRET"] = api_secret
    
    print("✅ API credentials verified")
    print(f"   Using API key: {api_key[:8]}...")
    return api_key, api_secret


def create_paper_trading_config(api_key, api_secret):
    """Create paper trading configuration"""
    
    # Use LINEAR for perpetual futures (better liquidity than SPOT)
    product_type = BybitProductType.LINEAR
    
    config = TradingNodeConfig(
        trader_id=TraderId("PAPER-TRADER-001"),
        
        # Logging configuration
        logging=LoggingConfig(
            log_level="INFO",
            log_level_file="DEBUG",
            log_directory="logs",
        ),
        
        # Data client (Bybit testnet)
        data_clients={
            BYBIT: BybitDataClientConfig(
                api_key=api_key,
                api_secret=api_secret,
                testnet=True,  # CRITICAL: Always use testnet for paper trading
                product_types=[product_type],
                instrument_provider=InstrumentProviderConfig(load_all=True),
            )
        },
        
        # Execution client (Bybit testnet)
        exec_clients={
            BYBIT: BybitExecClientConfig(
                api_key=api_key,
                api_secret=api_secret,
                testnet=True,  # CRITICAL: Always use testnet
                product_types=[product_type],
                instrument_provider=InstrumentProviderConfig(load_all=True),
                max_retries=3,
            )
        },
    )
    
    return config


def main():
    print("""
╔══════════════════════════════════════════════════════════════════╗
║                                                                  ║
║              AI-ADAPTIVE PAPER TRADING SYSTEM                    ║
║                                                                  ║
║  SAFETY MODE: Testnet Only                                       ║
║  Exchange: Bybit Testnet (LINEAR Perpetuals)                     ║
║                                                                  ║
╚══════════════════════════════════════════════════════════════════╝
    """)
    
    try:
        # Verify credentials
        api_key, api_secret = verify_credentials()
        
        # Create configuration
        config = create_paper_trading_config(api_key, api_secret)
        
        # Critical safety check
        verify_testnet_mode(config)
        
        # Create trading node
        print("\n🔧 Initializing trading node...")
        node = TradingNode(config=config)
        
        # Configure strategy (conservative for paper trading)
        print("\n📊 Configuring AI-Adaptive strategy...")
        from ajk_strategies.ai_adaptive_stragey_v3 import AIAdaptiveStrategyV3
        
        strategy_config = AIAdaptiveStrategyConfigV3(
            instrument_id="BTCUSDT-LINEAR.BYBIT",  # String, not InstrumentId object
            bar_type="BTCUSDT-LINEAR.BYBIT-1-MINUTE-LAST-EXTERNAL",
            venue="BYBIT",
            confidence_threshold=0.80,  # Higher threshold for paper trading
            enable_monte_carlo=True,     # Enable risk assessment
            max_bars_in_position=50,     # Shorter hold time
            max_bars_per_run=None,       # No limit for live trading
        )
        
        # Instantiate strategy
        strategy = AIAdaptiveStrategyV3(config=strategy_config)
        
        # Add strategy to trader
        node.trader.add_strategy(strategy)
        
        # Register Bybit client factories
        node.add_data_client_factory(BYBIT, BybitLiveDataClientFactory)
        node.add_exec_client_factory(BYBIT, BybitLiveExecClientFactory)
        node.build()
        
        print("\n✅ Paper trading system ready!")
        print("\n📊 Monitoring:")
        print("   - Grafana: http://localhost:3000")
        print("   - Prometheus: http://localhost:9090")
        print("   - Logs: ./logs/")
        print("\n⚠️  Press Ctrl+C to stop trading\n")
        
        # Run trading node (blocks until interrupted)
        node.run()
    
    except KeyboardInterrupt:
        print("\n\n⏸️  Shutdown signal received...")
    
    except Exception as e:
        print(f"\n\n❌ Error: {e}")
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
