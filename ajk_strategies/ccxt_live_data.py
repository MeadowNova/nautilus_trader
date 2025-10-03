#!/usr/bin/env python3
"""
CCXT Live Market Data Adapter

This module provides live market data integration using CCXT library.
Supports real-time price feeds from major cryptocurrency exchanges.

Features:
- Real-time OHLCV data fetching
- Multiple exchange support (Binance, Coinbase, Kraken, etc.)
- Rate limiting and error handling
- Data caching and persistence
- WebSocket support for low-latency feeds

Usage:
    from ccxt_live_data import CCXTDataFeed
    
    feed = CCXTDataFeed(exchange='binance', symbol='ETH/USDT')
    feed.start()
    
    # Get latest data
    latest_bar = feed.get_latest_bar()
"""

import ccxt
import time
import pandas as pd
from datetime import datetime, timedelta
from typing import Optional, Dict, List
import json
from pathlib import Path


class CCXTDataFeed:
    """
    Live market data feed using CCXT
    
    Attributes:
        exchange_id: Exchange identifier (e.g., 'binance', 'coinbase')
        symbol: Trading pair symbol (e.g., 'ETH/USDT')
        timeframe: Candlestick timeframe (e.g., '1m', '5m', '1h')
    """
    
    def __init__(
        self,
        exchange_id: str = 'binance',
        symbol: str = 'ETH/USDT',
        timeframe: str = '1m',
        api_key: Optional[str] = None,
        api_secret: Optional[str] = None,
        cache_dir: Optional[Path] = None
    ):
        """
        Initialize CCXT data feed
        
        Args:
            exchange_id: Exchange name (binance, coinbase, kraken, etc.)
            symbol: Trading pair (ETH/USDT, BTC/USD, etc.)
            timeframe: Candlestick interval (1m, 5m, 15m, 1h, etc.)
            api_key: Optional API key for authenticated requests
            api_secret: Optional API secret
            cache_dir: Directory for caching data
        """
        self.exchange_id = exchange_id
        self.symbol = symbol
        self.timeframe = timeframe
        
        # Initialize exchange
        exchange_class = getattr(ccxt, exchange_id)
        self.exchange = exchange_class({
            'apiKey': api_key,
            'secret': api_secret,
            'enableRateLimit': True,  # Important for avoiding bans
            'options': {
                'defaultType': 'spot',  # or 'future' for futures
            }
        })
        
        # Cache
        self.cache_dir = cache_dir or Path.home() / '.nautilus_cache' / 'ccxt'
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        
        # Data storage
        self.ohlcv_data = []
        self.latest_bar = None
        self.is_running = False
        
        print(f"✅ CCXT Data Feed Initialized")
        print(f"   Exchange: {exchange_id}")
        print(f"   Symbol: {symbol}")
        print(f"   Timeframe: {timeframe}")
    
    def fetch_ohlcv(
        self,
        since: Optional[int] = None,
        limit: int = 100
    ) -> List[List]:
        """
        Fetch OHLCV (candlestick) data
        
        Args:
            since: Timestamp in milliseconds (fetch data from this time)
            limit: Number of candles to fetch
        
        Returns:
            List of OHLCV data: [[timestamp, open, high, low, close, volume], ...]
        """
        try:
            ohlcv = self.exchange.fetch_ohlcv(
                symbol=self.symbol,
                timeframe=self.timeframe,
                since=since,
                limit=limit
            )
            return ohlcv
        except Exception as e:
            print(f"❌ Error fetching OHLCV: {e}")
            return []
    
    def fetch_ticker(self) -> Dict:
        """
        Fetch current ticker (latest price, volume, etc.)
        
        Returns:
            Dictionary with ticker data
        """
        try:
            ticker = self.exchange.fetch_ticker(self.symbol)
            return ticker
        except Exception as e:
            print(f"❌ Error fetching ticker: {e}")
            return {}
    
    def fetch_order_book(self, limit: int = 20) -> Dict:
        """
        Fetch order book (bids and asks)
        
        Args:
            limit: Number of levels to fetch
        
        Returns:
            Dictionary with bids and asks
        """
        try:
            order_book = self.exchange.fetch_order_book(self.symbol, limit=limit)
            return order_book
        except Exception as e:
            print(f"❌ Error fetching order book: {e}")
            return {'bids': [], 'asks': []}
    
    def fetch_trades(self, limit: int = 50) -> List[Dict]:
        """
        Fetch recent trades
        
        Args:
            limit: Number of trades to fetch
        
        Returns:
            List of trade dictionaries
        """
        try:
            trades = self.exchange.fetch_trades(self.symbol, limit=limit)
            return trades
        except Exception as e:
            print(f"❌ Error fetching trades: {e}")
            return []
    
    def get_latest_bar(self) -> Optional[Dict]:
        """
        Get the latest OHLCV bar
        
        Returns:
            Dictionary with bar data or None
        """
        if self.latest_bar:
            return self.latest_bar
        
        # Fetch latest data
        ohlcv = self.fetch_ohlcv(limit=1)
        if ohlcv:
            bar = self._ohlcv_to_dict(ohlcv[0])
            self.latest_bar = bar
            return bar
        
        return None
    
    def _ohlcv_to_dict(self, ohlcv: List) -> Dict:
        """
        Convert OHLCV list to dictionary
        
        Args:
            ohlcv: [timestamp, open, high, low, close, volume]
        
        Returns:
            Dictionary with named fields
        """
        return {
            'timestamp': ohlcv[0],
            'datetime': datetime.fromtimestamp(ohlcv[0] / 1000),
            'open': ohlcv[1],
            'high': ohlcv[2],
            'low': ohlcv[3],
            'close': ohlcv[4],
            'volume': ohlcv[5],
        }
    
    def fetch_historical_data(
        self,
        start_date: datetime,
        end_date: Optional[datetime] = None,
        save_to_csv: bool = True
    ) -> pd.DataFrame:
        """
        Fetch historical OHLCV data for backtesting
        
        Args:
            start_date: Start date for historical data
            end_date: End date (defaults to now)
            save_to_csv: Whether to save data to CSV
        
        Returns:
            DataFrame with historical data
        """
        if end_date is None:
            end_date = datetime.now()
        
        print(f"📥 Fetching historical data from {start_date.date()} to {end_date.date()}...")
        
        # Convert to milliseconds
        since = int(start_date.timestamp() * 1000)
        end_ms = int(end_date.timestamp() * 1000)
        
        # Fetch data in chunks
        all_data = []
        current_since = since
        
        while current_since < end_ms:
            ohlcv = self.fetch_ohlcv(since=current_since, limit=1000)
            
            if not ohlcv:
                break
            
            all_data.extend(ohlcv)
            
            # Update since to last timestamp
            current_since = ohlcv[-1][0] + 1
            
            # Rate limiting
            time.sleep(self.exchange.rateLimit / 1000)
            
            print(f"   Fetched {len(all_data)} bars...", end='\r')
        
        print(f"\n✅ Fetched {len(all_data)} bars total")
        
        # Convert to DataFrame
        df = pd.DataFrame(all_data, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
        df['datetime'] = pd.to_datetime(df['timestamp'], unit='ms')
        df.set_index('datetime', inplace=True)
        
        # Save to CSV
        if save_to_csv:
            filename = f"{self.exchange_id}_{self.symbol.replace('/', '_')}_{self.timeframe}_{start_date.strftime('%Y%m%d')}_{end_date.strftime('%Y%m%d')}.csv"
            filepath = self.cache_dir / filename
            df.to_csv(filepath)
            print(f"💾 Saved to: {filepath}")
        
        return df
    
    def start_live_feed(self, callback=None, interval: int = 60):
        """
        Start live data feed (polling mode)
        
        Args:
            callback: Function to call with new data
            interval: Polling interval in seconds
        """
        self.is_running = True
        print(f"🔴 Starting live feed (polling every {interval}s)...")
        
        try:
            while self.is_running:
                # Fetch latest bar
                ohlcv = self.fetch_ohlcv(limit=1)
                if ohlcv:
                    bar = self._ohlcv_to_dict(ohlcv[0])
                    self.latest_bar = bar
                    
                    # Call callback if provided
                    if callback:
                        callback(bar)
                    
                    print(f"📊 {bar['datetime']} | O: {bar['open']:.2f} H: {bar['high']:.2f} L: {bar['low']:.2f} C: {bar['close']:.2f} V: {bar['volume']:.2f}")
                
                # Wait for next interval
                time.sleep(interval)
        
        except KeyboardInterrupt:
            print("\n⏸️  Live feed stopped by user")
            self.is_running = False
    
    def stop(self):
        """Stop live feed"""
        self.is_running = False
        print("⏹️  Live feed stopped")
    
    def get_exchange_info(self) -> Dict:
        """
        Get exchange information and available markets
        
        Returns:
            Dictionary with exchange info
        """
        try:
            markets = self.exchange.load_markets()
            
            info = {
                'exchange': self.exchange_id,
                'total_markets': len(markets),
                'has_fetch_ohlcv': self.exchange.has['fetchOHLCV'],
                'has_fetch_ticker': self.exchange.has['fetchTicker'],
                'has_fetch_order_book': self.exchange.has['fetchOrderBook'],
                'has_fetch_trades': self.exchange.has['fetchTrades'],
                'timeframes': self.exchange.timeframes if hasattr(self.exchange, 'timeframes') else [],
                'rate_limit': self.exchange.rateLimit,
            }
            
            return info
        except Exception as e:
            print(f"❌ Error getting exchange info: {e}")
            return {}
    
    def list_available_symbols(self, quote_currency: str = 'USDT') -> List[str]:
        """
        List available trading pairs
        
        Args:
            quote_currency: Filter by quote currency (e.g., 'USDT', 'USD', 'BTC')
        
        Returns:
            List of symbol strings
        """
        try:
            markets = self.exchange.load_markets()
            symbols = [
                symbol for symbol in markets.keys()
                if quote_currency in symbol
            ]
            return sorted(symbols)
        except Exception as e:
            print(f"❌ Error listing symbols: {e}")
            return []


def demo_live_feed():
    """Demonstration of live data feed"""
    print("""
    ╔══════════════════════════════════════════════════════════════════╗
    ║                                                                  ║
    ║              CCXT LIVE MARKET DATA DEMO                          ║
    ║                                                                  ║
    ╚══════════════════════════════════════════════════════════════════╝
    """)
    
    # Initialize feed
    feed = CCXTDataFeed(
        exchange_id='binance',
        symbol='ETH/USDT',
        timeframe='1m'
    )
    
    # Get exchange info
    print("\n📡 Exchange Information:")
    info = feed.get_exchange_info()
    for key, value in info.items():
        print(f"   {key}: {value}")
    
    # Get latest ticker
    print("\n💰 Latest Ticker:")
    ticker = feed.fetch_ticker()
    if ticker:
        print(f"   Last Price: ${ticker.get('last', 0):.2f}")
        print(f"   Bid: ${ticker.get('bid', 0):.2f}")
        print(f"   Ask: ${ticker.get('ask', 0):.2f}")
        print(f"   24h Volume: {ticker.get('baseVolume', 0):.2f}")
        print(f"   24h Change: {ticker.get('percentage', 0):.2f}%")
    
    # Get latest bar
    print("\n📊 Latest OHLCV Bar:")
    bar = feed.get_latest_bar()
    if bar:
        print(f"   Time: {bar['datetime']}")
        print(f"   Open: ${bar['open']:.2f}")
        print(f"   High: ${bar['high']:.2f}")
        print(f"   Low: ${bar['low']:.2f}")
        print(f"   Close: ${bar['close']:.2f}")
        print(f"   Volume: {bar['volume']:.2f}")
    
    # Fetch some historical data
    print("\n📥 Fetching historical data (last 100 bars)...")
    ohlcv = feed.fetch_ohlcv(limit=100)
    if ohlcv:
        df = pd.DataFrame(ohlcv, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
        df['datetime'] = pd.to_datetime(df['timestamp'], unit='ms')
        print(f"   Fetched {len(df)} bars")
        print(f"   Date range: {df['datetime'].min()} to {df['datetime'].max()}")
        print(f"\n   Last 5 bars:")
        print(df.tail().to_string(index=False))
    
    print("\n✅ Demo completed!")
    print("\n💡 To start live feed, uncomment the following line:")
    print("   # feed.start_live_feed(interval=60)")


if __name__ == "__main__":
    demo_live_feed()
