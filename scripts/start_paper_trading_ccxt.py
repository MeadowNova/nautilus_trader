#!/usr/bin/env python3
"""
Paper Trading with CCXT Market Data

Uses CCXT library to fetch public market data from any exchange (no API keys needed).
Combines CCXT public data with Sandbox execution for complete paper trading.

Supported exchanges: Binance, Bybit, OKX, Coinbase, Kraken, and 100+ more!

Usage:
    python scripts/start_paper_trading_ccxt.py
"""

import os
import sys
from pathlib import Path
from decimal import Decimal
import asyncio
from datetime import datetime, timezone

# Add project root to path
project_root = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(project_root))

from nautilus_trader.live.node import TradingNode
from nautilus_trader.config import (
    TradingNodeConfig,
    LoggingConfig,
    InstrumentProviderConfig,
)
from nautilus_trader.adapters.sandbox.config import SandboxExecutionClientConfig
from nautilus_trader.adapters.sandbox.factory import SandboxLiveExecClientFactory
from nautilus_trader.model.identifiers import InstrumentId, TraderId, Venue
from nautilus_trader.model.data import Bar, BarType
from nautilus_trader.model.instruments import CryptoFuture, CryptoPerpetual
from nautilus_trader.model.objects import Price, Quantity, Money, Currency
from nautilus_trader.core.datetime import dt_to_unix_nanos

from ajk_strategies.ai_adaptive_stragey_v3 import AIAdaptiveStrategyConfigV3, AIAdaptiveStrategyV3

import ccxt


class CCXTDataFeed:
    """
    Fetches public market data from any CCXT-supported exchange
    """
    
    def __init__(self, exchange_id: str = 'bybit', symbol: str = 'BTC/USDT:USDT', timeframe: str = '1m'):
        """
        Initialize CCXT data feed
        
        Args:
            exchange_id: Exchange name (bybit, binance, okx, coinbase, etc.)
            symbol: Trading pair (BTC/USDT:USDT for perpetuals)
            timeframe: Candlestick interval (1m, 5m, 15m, 1h, etc.)
        """
        self.exchange_id = exchange_id
        self.symbol = symbol
        self.timeframe = timeframe
        
        # Initialize exchange (public data only - no API keys)
        exchange_class = getattr(ccxt, exchange_id)
        self.exchange = exchange_class({
            'enableRateLimit': True,
            'options': {
                'defaultType': 'future',  # For perpetual futures
            }
        })
        
        print(f"✅ CCXT initialized: {exchange_id}")
        print(f"   Symbol: {symbol}")
        print(f"   Timeframe: {timeframe}")
    
    async def fetch_latest_bars(self, limit: int = 100):
        """Fetch latest OHLCV bars from exchange"""
        try:
            # Fetch OHLCV data (public - no auth required)
            ohlcv = await asyncio.to_thread(
                self.exchange.fetch_ohlcv,
                self.symbol,
                self.timeframe,
                limit=limit
            )
            
            print(f"📊 Fetched {len(ohlcv)} bars from {self.exchange_id}")
            return ohlcv
            
        except Exception as e:
            print(f"❌ Error fetching data: {e}")
            return []
    
    def convert_to_nautilus_bar(self, ohlcv, bar_type: BarType, instrument_id: InstrumentId):
        """Convert CCXT OHLCV to NautilusTrader Bar"""
        timestamp_ms, open_price, high, low, close, volume = ohlcv
        
        # Convert to NautilusTrader types
        ts_event = dt_to_unix_nanos(datetime.fromtimestamp(timestamp_ms / 1000, tz=timezone.utc))
        ts_init = ts_event
        
        bar = Bar(
            bar_type=bar_type,
            open=Price.from_str(str(open_price)),
            high=Price.from_str(str(high)),
            low=Price.from_str(str(low)),
            close=Price.from_str(str(close)),
            volume=Quantity.from_str(str(volume)),
            ts_event=ts_event,
            ts_init=ts_init,
        )
        
        return bar


async def start_ccxt_paper_trading(exchange_id: str = 'bybit'):
    """Start paper trading with CCXT market data"""
    
    venue_name = "CCXT"
    symbol = 'BTC/USDT:USDT'  # Perpetual futures format
    instrument_str = f"BTCUSDT-PERP.{venue_name}"
    
    # Configure trading node
    config = TradingNodeConfig(
        trader_id=TraderId("CCXT-TRADER-001"),
        
        logging=LoggingConfig(
            log_level="INFO",
            log_level_file="DEBUG",
            log_directory="logs",
            log_colors=True,
        ),
        
        # Sandbox execution (simulated trading)
        exec_clients={
            venue_name: SandboxExecutionClientConfig(
                venue=venue_name,
                starting_balances=["100000 USDT", "10 BTC"],
                account_type="MARGIN",
                oms_type="NETTING",
                default_leverage=Decimal("1.0"),
                bar_execution=True,
                support_contingent_orders=True,
            )
        },
    )
    
    # Create trading node
    print("\n🔧 Initializing trading node...")
    node = TradingNode(config=config)
    
    # Register sandbox execution factory
    node.add_exec_client_factory(venue_name, SandboxLiveExecClientFactory)
    
    # Create instrument manually (since we're not using exchange adapter)
    instrument_id = InstrumentId.from_str(instrument_str)
    
    # Build node
    node.build()
    
    # Configure strategy
    print("\n📊 Configuring AI-Adaptive strategy...")
    strategy_config = AIAdaptiveStrategyConfigV3(
        instrument_id=instrument_str,
        bar_type=f"{instrument_str}-1-MINUTE-LAST-INTERNAL",
        venue=venue_name,
        confidence_threshold=0.75,
        enable_monte_carlo=True,
        max_bars_in_position=50,
        max_bars_per_run=None,
    )
    
    strategy = AIAdaptiveStrategyV3(config=strategy_config)
    node.trader.add_strategy(strategy)
    
    # Initialize CCXT data feed
    print("\n📡 Initializing CCXT data feed...")
    ccxt_feed = CCXTDataFeed(exchange_id=exchange_id, symbol=symbol, timeframe='1m')
    
    # Fetch initial historical bars
    print("\n📥 Fetching historical data...")
    ohlcv_data = await ccxt_feed.fetch_latest_bars(limit=200)
    
    if not ohlcv_data:
        raise RuntimeError("Failed to fetch historical data from exchange")
    
    print(f"✅ Loaded {len(ohlcv_data)} historical bars")
    
    # TODO: Feed bars to strategy
    # This would require creating a custom data client or feeding bars directly
    # For now, this demonstrates the concept
    
    print("\n✅ CCXT Paper Trading Ready!")
    print("\n💡 Features:")
    print("   ✅ Public market data from CCXT")
    print("   ✅ No API keys required")
    print("   ✅ Supports 100+ exchanges")
    print("   ✅ Simulated execution")
    print("   ✅ Full monitoring integration")
    print("\n⚠️  Press Ctrl+C to stop\n")
    
    # Note: Full implementation would require:
    # 1. Custom data client that feeds CCXT bars
    # 2. Periodic polling for new bars
    # 3. WebSocket support for real-time updates
    
    print("⚠️  Note: This is a proof-of-concept showing CCXT integration")
    print("    Full implementation requires custom data client development")


def main():
    print("""
╔══════════════════════════════════════════════════════════════════╗
║                                                                  ║
║              CCXT PAPER TRADING SYSTEM (CONCEPT)                 ║
║                                                                  ║
║  Data Source: CCXT (Public data - no API keys)                  ║
║  Execution: Sandbox (Simulated)                                 ║
║  Exchanges: 100+ supported                                      ║
║                                                                  ║
╚══════════════════════════════════════════════════════════════════╝
    """)
    
    try:
        # Run async
        asyncio.run(start_ccxt_paper_trading(exchange_id='bybit'))
        
    except KeyboardInterrupt:
        print("\n\n⏸️  Shutdown signal received...")
    except Exception as e:
        print(f"\n\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
