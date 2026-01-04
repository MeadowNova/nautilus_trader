#!/usr/bin/env python3
"""
Binance Testnet Paper Trading with 1-Second Bars

MAXIMUM DATA COLLECTION MODE:
- 1-second bars = 3,600 bars/hour (60x more than 1-minute!)
- Expected: 50-200 trades per day
- Aggressive settings for rapid data collection

SAFETY: This script includes multiple safety checks to prevent accidental live trading.
Always verify testnet mode before starting.

Usage:
    python scripts/start_paper_trading_binance.py

Environment Variables Required:
    BINANCE_API_KEY - Your Binance testnet API key
    BINANCE_API_SECRET - Your Binance testnet API secret

Get testnet keys from: https://testnet.binance.vision/
Activate keys at: https://testnet.binance.vision/ (ensure API trading enabled)
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
from nautilus_trader.adapters.binance import BINANCE
from nautilus_trader.adapters.binance.config import (
    BinanceDataClientConfig,
    BinanceExecClientConfig,
)
from nautilus_trader.adapters.binance.common.enums import BinanceAccountType
from nautilus_trader.adapters.binance.factories import (
    BinanceLiveDataClientFactory,
    BinanceLiveExecClientFactory,
)
from nautilus_trader.model.identifiers import TraderId

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
    api_key = os.getenv("BINANCE_API_KEY")
    api_secret = os.getenv("BINANCE_API_SECRET")
    
    if not api_key:
        raise RuntimeError(
            "❌ BINANCE_API_KEY not set!\n"
            "   Add to infrastructure/.env.local: BINANCE_API_KEY=your-key\n"
            "   Get testnet keys from: https://testnet.binance.vision/"
        )
    
    if not api_secret:
        raise RuntimeError(
            "❌ BINANCE_API_SECRET not set!\n"
            "   Add to infrastructure/.env.local: BINANCE_API_SECRET=your-secret\n"
            "   Get from: https://testnet.binance.vision/"
        )
    
    print("✅ API credentials verified")
    print(f"   Using API key: {api_key[:10]}...")
    return api_key, api_secret


def create_binance_paper_trading_config(api_key, api_secret):
    """Create Binance paper trading configuration with 1-second bars"""
    
    config = TradingNodeConfig(
        trader_id=TraderId("PAPER-TRADER-001"),
        
        # Logging configuration
        logging=LoggingConfig(
            log_level="INFO",
            log_level_file="DEBUG",
            log_directory="logs",
            log_colors=True,
        ),
        
        # Binance data client (SPOT testnet)
        data_clients={
            BINANCE: BinanceDataClientConfig(
                api_key=api_key,
                api_secret=api_secret,
                testnet=True,  # CRITICAL: Always use testnet for paper trading
                account_type=BinanceAccountType.SPOT,
                instrument_provider=InstrumentProviderConfig(
                    load_all=False,
                    load_ids=("BTCUSDT.BINANCE",),
                ),
            )
        },
        
        # Binance execution client (SPOT testnet)
        exec_clients={
            BINANCE: BinanceExecClientConfig(
                api_key=api_key,
                api_secret=api_secret,
                testnet=True,  # CRITICAL: Always use testnet
                account_type=BinanceAccountType.SPOT,
                instrument_provider=InstrumentProviderConfig(
                    load_all=False,
                    load_ids=("BTCUSDT.BINANCE",),
                ),
                max_retries=3,
            )
        },
    )
    
    return config


def main():
    print("""
╔══════════════════════════════════════════════════════════════════╗
║                                                                  ║
║         BINANCE TESTNET PAPER TRADING - 1-MINUTE BARS            ║
║                                                                  ║
║  MODE: Reliable Data Collection                                  ║
║  Exchange: Binance Testnet (SPOT)                                ║
║  Bars: 1-MINUTE (60/hour - testnet proven)                       ║
║  Confidence: 50% (lowered to trigger trades)                     ║
║  Expected: 20-60 trades per day                                  ║
║                                                                  ║
╚══════════════════════════════════════════════════════════════════╝
    """)
    
    try:
        # Verify credentials
        api_key, api_secret = verify_credentials()
        
        # Create configuration
        print("\n⚙️  Creating Binance testnet configuration...")
        config = create_binance_paper_trading_config(api_key, api_secret)
        
        # Critical safety check
        verify_testnet_mode(config)
        
        # Create trading node
        print("\n🔧 Initializing trading node...")
        node = TradingNode(config=config)
        
        # Configure strategy with AGGRESSIVE settings for 1-second bars
        print("\n📊 Configuring AI-Adaptive strategy (1-SECOND BARS)...")
        from ajk_strategies.ai_adaptive_stragey_v3 import AIAdaptiveStrategyV3
        
        strategy_config = AIAdaptiveStrategyConfigV3(
            instrument_id="BTCUSDT.BINANCE",  # Binance SPOT
            bar_type="BTCUSDT.BINANCE-1-MINUTE-LAST-EXTERNAL",  # 1-MINUTE (reliable on testnet)
            venue="BINANCE",
            confidence_threshold=0.50,  # Lower threshold to trigger trades
            enable_monte_carlo=True,
            max_bars_in_position=30,    # 30 minutes max hold
            max_bars_per_run=None,      # No limit for live trading
        )
        
        # Instantiate strategy
        strategy = AIAdaptiveStrategyV3(config=strategy_config)
        
        # Add strategy to trader
        node.trader.add_strategy(strategy)
        
        # Register Binance client factories
        node.add_data_client_factory(BINANCE, BinanceLiveDataClientFactory)
        node.add_exec_client_factory(BINANCE, BinanceLiveExecClientFactory)
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
        
        print("\n✅ Binance paper trading system ready!")
        print("\n📊 Configuration:")
        print("   - Exchange: Binance Testnet (SPOT)")
        print("   - Bar interval: 1 MINUTE (testnet reliable)")
        print("   - Bars per hour: 60")
        print("   - Bars per day: 1,440")
        print("   - Expected trades: 20-60/day")
        print("   - Confidence threshold: 0.50 (50% for more trades)")
        print("   - Max position time: 30 minutes")
        print("\n📊 Monitoring:")
        print("   - Grafana: http://localhost:3000/d/live-trading-monitor")
        print("   - Prometheus: http://localhost:9090")
        print("   - Logs: ./logs/PAPER-TRADER-001_*.log")
        print("\n💡 Tips:")
        print("   - Bars arrive every MINUTE (60/hour)")
        print("   - Confidence 50% = more trades than 60%")
        print("   - Monitor Grafana dashboard for real-time updates")
        print("   - First trades should appear within 30-60 minutes")
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
