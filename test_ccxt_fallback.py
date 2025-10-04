#!/usr/bin/env python3
"""
CCXT Multi-Exchange Test with Fallback

Tests multiple exchanges to find one that works from current location.
"""

import ccxt
from datetime import datetime

def test_exchange(exchange_id, symbol='BTC/USDT'):
    """Test if an exchange is accessible"""
    try:
        print(f"\n🔌 Testing {exchange_id.title()}... ", end='')
        exchange_class = getattr(ccxt, exchange_id)
        exchange = exchange_class({
            'enableRateLimit': True,
            'timeout': 10000,
        })
        
        # Try to fetch ticker
        ticker = exchange.fetch_ticker(symbol)
        print(f"✅ SUCCESS!")
        print(f"   {symbol} Price: ${ticker['last']:,.2f}")
        print(f"   24h Volume: {ticker.get('baseVolume', 0):,.0f}")
        return True, exchange
        
    except Exception as e:
        error_msg = str(e)[:80]
        print(f"❌ FAILED")
        print(f"   Error: {error_msg}...")
        return False, None

def main():
    print("="*70)
    print("CCXT MULTI-EXCHANGE TEST")
    print("="*70)
    print(f"\n✅ CCXT Version: {ccxt.__version__}")
    print(f"✅ Total Exchanges: {len(ccxt.exchanges)}")
    
    # List of exchanges to try (in order of preference)
    exchanges_to_test = [
        ('kraken', 'BTC/USD'),
        ('coinbase', 'BTC/USD'),
        ('kucoin', 'BTC/USDT'),
        ('bybit', 'BTC/USDT'),
        ('okx', 'BTC/USDT'),
        ('bitfinex', 'BTC/USDT'),
        ('mexc', 'BTC/USDT'),
        ('gateio', 'BTC/USDT'),
    ]
    
    working_exchanges = []
    
    print("\n" + "="*70)
    print("TESTING EXCHANGE CONNECTIVITY")
    print("="*70)
    
    for exchange_id, symbol in exchanges_to_test:
        success, exchange = test_exchange(exchange_id, symbol)
        if success:
            working_exchanges.append((exchange_id, exchange, symbol))
    
    # Summary
    print("\n" + "="*70)
    print("RESULTS SUMMARY")
    print("="*70)
    
    if working_exchanges:
        print(f"\n✅ Found {len(working_exchanges)} working exchange(s):")
        for exchange_id, _, symbol in working_exchanges:
            print(f"   ✓ {exchange_id.title()} ({symbol})")
        
        # Test detailed features on first working exchange
        print("\n" + "="*70)
        print(f"TESTING FEATURES ON {working_exchanges[0][0].upper()}")
        print("="*70)
        
        exchange_id, exchange, symbol = working_exchanges[0]
        
        try:
            # Test OHLCV
            print(f"\n📈 Testing OHLCV data...")
            ohlcv = exchange.fetch_ohlcv(symbol, '1h', limit=5)
            print(f"   ✅ Fetched {len(ohlcv)} hourly bars")
            for bar in ohlcv[-3:]:
                dt = datetime.fromtimestamp(bar[0]/1000)
                print(f"   - {dt.strftime('%Y-%m-%d %H:%M')}: ${bar[4]:,.2f}")
            
            # Test order book
            print(f"\n📖 Testing Order Book...")
            orderbook = exchange.fetch_order_book(symbol, limit=3)
            print(f"   ✅ Fetched {len(orderbook['bids'])} bids, {len(orderbook['asks'])} asks")
            print(f"   Best Bid: ${orderbook['bids'][0][0]:,.2f}")
            print(f"   Best Ask: ${orderbook['asks'][0][0]:,.2f}")
            
            # Test trades
            print(f"\n💱 Testing Recent Trades...")
            trades = exchange.fetch_trades(symbol, limit=3)
            print(f"   ✅ Fetched {len(trades)} recent trades")
            
            # Exchange capabilities
            print(f"\n🏦 Exchange Capabilities:")
            print(f"   fetchOHLCV: {'✓' if exchange.has['fetchOHLCV'] else '✗'}")
            print(f"   fetchTicker: {'✓' if exchange.has['fetchTicker'] else '✗'}")
            print(f"   fetchOrderBook: {'✓' if exchange.has['fetchOrderBook'] else '✗'}")
            print(f"   fetchTrades: {'✓' if exchange.has['fetchTrades'] else '✗'}")
            
            if hasattr(exchange, 'timeframes'):
                timeframes = list(exchange.timeframes.keys())
                print(f"\n⏰ Available Timeframes ({len(timeframes)}):")
                print(f"   {', '.join(timeframes[:10])}")
            
            print("\n" + "="*70)
            print("✅ CCXT IS FULLY FUNCTIONAL!")
            print("="*70)
            print(f"\n💡 Recommendation:")
            print(f"   Use {exchange_id.upper()} for market data")
            print(f"   Symbol format: {symbol}")
            print("="*70)
            
        except Exception as e:
            print(f"\n⚠️  Error testing features: {e}")
    
    else:
        print("\n❌ No working exchanges found!")
        print("\n💡 Troubleshooting:")
        print("   1. Check internet connection")
        print("   2. Try using a VPN")
        print("   3. Use Nautilus built-in adapters")
        print("   4. Use historical data for backtesting")
    
    print("\n" + "="*70)
    print("TEST COMPLETE")
    print("="*70)
    
    return len(working_exchanges) > 0

if __name__ == "__main__":
    success = main()
    exit(0 if success else 1)
