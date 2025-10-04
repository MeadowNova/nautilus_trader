#!/usr/bin/env python3
"""
CCXT Integration Test Script

This script tests CCXT installation and basic functionality
with Binance exchange to verify market data access.
"""

import ccxt
from datetime import datetime, timedelta
import pandas as pd

def test_ccxt_basic():
    """Test basic CCXT functionality"""
    print("="*70)
    print("CCXT INTEGRATION TEST")
    print("="*70)
    
    # Test 1: Version and exchanges
    print(f"\n✅ CCXT Version: {ccxt.__version__}")
    print(f"✅ Total Exchanges Available: {len(ccxt.exchanges)}")
    print(f"\n📋 Popular Crypto Exchanges:")
    popular = ['binance', 'coinbase', 'kraken', 'bybit', 'okx', 'kucoin', 'bitfinex', 'huobi']
    for exchange_id in popular:
        if exchange_id in ccxt.exchanges:
            print(f"   ✓ {exchange_id.title()}")
    
    # Test 2: Connect to Binance
    print(f"\n🔌 Testing Connection to Binance...")
    try:
        exchange = ccxt.binance({
            'enableRateLimit': True,
            'options': {'defaultType': 'spot'}
        })
        
        # Fetch ticker
        print(f"\n📊 Fetching ETH/USDT Ticker...")
        ticker = exchange.fetch_ticker('ETH/USDT')
        print(f"   Last Price: ${ticker['last']:,.2f}")
        print(f"   Bid: ${ticker['bid']:,.2f}")
        print(f"   Ask: ${ticker['ask']:,.2f}")
        print(f"   24h Volume: {ticker['baseVolume']:,.0f} ETH")
        print(f"   24h Change: {ticker['percentage']:.2f}%")
        
        # Fetch recent trades
        print(f"\n💱 Fetching Recent Trades...")
        trades = exchange.fetch_trades('ETH/USDT', limit=5)
        print(f"   Recent {len(trades)} trades:")
        for trade in trades[:3]:
            timestamp = datetime.fromtimestamp(trade['timestamp']/1000)
            print(f"   - {timestamp.strftime('%H:%M:%S')}: ${trade['price']:,.2f} x {trade['amount']:.4f} ETH")
        
        # Fetch order book
        print(f"\n📖 Fetching Order Book...")
        orderbook = exchange.fetch_order_book('ETH/USDT', limit=5)
        print(f"   Top 3 Bids:")
        for bid in orderbook['bids'][:3]:
            print(f"   - ${bid[0]:,.2f} x {bid[1]:.4f} ETH")
        print(f"   Top 3 Asks:")
        for ask in orderbook['asks'][:3]:
            print(f"   - ${ask[0]:,.2f} x {ask[1]:.4f} ETH")
        
        # Fetch OHLCV (historical bars)
        print(f"\n📈 Fetching Historical OHLCV Data...")
        ohlcv = exchange.fetch_ohlcv('ETH/USDT', '1h', limit=10)
        print(f"   Fetched {len(ohlcv)} hourly bars")
        
        # Convert to DataFrame for display
        df = pd.DataFrame(ohlcv, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
        df['datetime'] = pd.to_datetime(df['timestamp'], unit='ms')
        print(f"\n   Last 5 bars:")
        print(df[['datetime', 'close', 'volume']].tail().to_string(index=False))
        
        # Test exchange info
        print(f"\n🏦 Exchange Capabilities:")
        print(f"   Has fetchOHLCV: {exchange.has['fetchOHLCV']}")
        print(f"   Has fetchTicker: {exchange.has['fetchTicker']}")
        print(f"   Has fetchOrderBook: {exchange.has['fetchOrderBook']}")
        print(f"   Has fetchTrades: {exchange.has['fetchTrades']}")
        print(f"   Rate Limit: {exchange.rateLimit}ms between requests")
        
        # Test available timeframes
        if hasattr(exchange, 'timeframes'):
            print(f"\n⏰ Available Timeframes:")
            print(f"   {', '.join(list(exchange.timeframes.keys())[:15])}")
        
        print(f"\n{'='*70}")
        print("✅ ALL TESTS PASSED - CCXT IS WORKING!")
        print("{'='*70}")
        
        return True
        
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_multiple_exchanges():
    """Test connection to multiple exchanges"""
    print(f"\n{'='*70}")
    print("TESTING MULTIPLE EXCHANGES")
    print(f"{'='*70}")
    
    test_exchanges = ['binance', 'coinbase', 'kraken']
    results = {}
    
    for exchange_id in test_exchanges:
        try:
            print(f"\n🔌 Testing {exchange_id.title()}...")
            exchange_class = getattr(ccxt, exchange_id)
            exchange = exchange_class({'enableRateLimit': True})
            
            # Try to fetch BTC ticker
            ticker = exchange.fetch_ticker('BTC/USDT' if exchange_id != 'coinbase' else 'BTC/USD')
            print(f"   ✅ Success! BTC Price: ${ticker['last']:,.2f}")
            results[exchange_id] = 'Success'
            
        except Exception as e:
            print(f"   ⚠️  Error: {str(e)[:50]}...")
            results[exchange_id] = 'Failed'
    
    print(f"\n{'='*70}")
    print("RESULTS SUMMARY:")
    for exchange_id, status in results.items():
        emoji = "✅" if status == "Success" else "⚠️"
        print(f"   {emoji} {exchange_id.title()}: {status}")
    print(f"{'='*70}")

if __name__ == "__main__":
    # Run basic tests
    success = test_ccxt_basic()
    
    # Run multi-exchange tests
    if success:
        test_multiple_exchanges()
    
    print("\n" + "="*70)
    print("🎓 CCXT Integration Test Complete!")
    print("="*70)
    print("\n💡 Next Steps:")
    print("   1. Download historical data for backtesting")
    print("   2. Run baseline backtest with simple EMA cross")
    print("   3. Test AI-adaptive strategy")
    print("   4. Integrate Reddit sentiment analysis")
    print("\n📚 Documentation:")
    print("   - Analysis: ai-working/learning path/research/analysis.md")
    print("   - Plan: ai-working/learning path/plan.md")
    print("="*70)
