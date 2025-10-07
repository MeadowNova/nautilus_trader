#!/usr/bin/env python3
"""
Reddit Sentiment Analysis for Crypto Trading
Tests the reddit.py algorithm for gathering market intelligence
"""

import sys
import time
from datetime import datetime
from collections import Counter
import re

sys.path.append('/home/ajk/Nautilus/nautilus_trader')
from docs.algorithms.reddit import get_subreddit_data


def calculate_sentiment_score(posts_data):
    """
    Calculate sentiment score from Reddit posts.
    
    Returns:
        dict with sentiment metrics
    """
    total_posts = len(posts_data)
    total_score = sum(post['score'] for post in posts_data.values())
    avg_score = total_score / total_posts if total_posts > 0 else 0
    avg_upvote_ratio = sum(post['upvote_ratio'] for post in posts_data.values()) / total_posts if total_posts > 0 else 0
    
    # Count sentiment keywords
    bullish_keywords = ['moon', 'pump', 'bullish', 'buy', 'long', 'hodl', 'breakout', 'rally', 'surge', 'rocket', '🚀']
    bearish_keywords = ['dump', 'bearish', 'sell', 'crash', 'drop', 'down', 'fall', 'short', 'liquidation']
    
    bullish_count = 0
    bearish_count = 0
    
    for post in posts_data.values():
        text = (post.get('title', '') + ' ' + post.get('selftext', '')).lower()
        
        bullish_count += sum(1 for keyword in bullish_keywords if keyword in text)
        bearish_count += sum(1 for keyword in bearish_keywords if keyword in text)
    
    # Calculate sentiment score (-1 to 1)
    total_keywords = bullish_count + bearish_count
    if total_keywords > 0:
        sentiment = (bullish_count - bearish_count) / total_keywords
    else:
        sentiment = 0
    
    # Extract coin mentions
    coin_mentions = extract_coin_mentions(posts_data)
    
    return {
        'total_posts': total_posts,
        'avg_score': avg_score,
        'avg_upvote_ratio': avg_upvote_ratio,
        'sentiment': sentiment,  # -1 (bearish) to 1 (bullish)
        'bullish_signals': bullish_count,
        'bearish_signals': bearish_count,
        'coin_mentions': coin_mentions,
        'momentum': 'BULLISH' if sentiment > 0.2 else 'BEARISH' if sentiment < -0.2 else 'NEUTRAL'
    }


def extract_coin_mentions(posts_data):
    """Extract mentions of specific cryptocurrencies."""
    coins = {
        'BTC': ['bitcoin', 'btc'],
        'ETH': ['ethereum', 'eth'],
        'SOL': ['solana', 'sol'],
        'ADA': ['cardano', 'ada'],
        'DOGE': ['dogecoin', 'doge'],
        'XRP': ['ripple', 'xrp'],
        'AVAX': ['avalanche', 'avax'],
        'MATIC': ['polygon', 'matic'],
    }
    
    mentions = Counter()
    
    for post in posts_data.values():
        text = (post.get('title', '') + ' ' + post.get('selftext', '')).lower()
        
        for symbol, keywords in coins.items():
            if any(keyword in text for keyword in keywords):
                mentions[symbol] += 1
    
    return dict(mentions.most_common(5))


def test_subreddit(subreddit, limit=25):
    """Test a single subreddit for sentiment."""
    print(f"\n{'='*70}")
    print(f"📊 Analyzing: r/{subreddit}")
    print(f"{'='*70}")
    
    try:
        # Fetch data
        data = get_subreddit_data(
            subreddit,
            limit=limit,
            age='hot',
            wanted_data=['title', 'score', 'upvote_ratio', 'created_utc', 'selftext', 'url']
        )
        
        # Calculate sentiment
        sentiment = calculate_sentiment_score(data)
        
        # Display results
        print(f"\n📈 SENTIMENT ANALYSIS:")
        print(f"   Posts Analyzed: {sentiment['total_posts']}")
        print(f"   Avg Score: {sentiment['avg_score']:.1f}")
        print(f"   Avg Upvote Ratio: {sentiment['avg_upvote_ratio']:.2%}")
        print(f"   Sentiment Score: {sentiment['sentiment']:.2f} [{sentiment['momentum']}]")
        print(f"   Bullish Signals: {sentiment['bullish_signals']}")
        print(f"   Bearish Signals: {sentiment['bearish_signals']}")
        
        if sentiment['coin_mentions']:
            print(f"\n💰 TOP COIN MENTIONS:")
            for coin, count in sentiment['coin_mentions'].items():
                print(f"   {coin}: {count} mentions")
        
        # Show top posts
        print(f"\n📰 TOP 3 POSTS:")
        sorted_posts = sorted(data.items(), key=lambda x: x[1]['score'], reverse=True)[:3]
        for idx, (_, post) in enumerate(sorted_posts, 1):
            print(f"\n   {idx}. {post['title'][:60]}...")
            print(f"      Score: {post['score']} | Ratio: {post['upvote_ratio']:.0%}")
        
        return sentiment
        
    except Exception as e:
        print(f"❌ Error: {e}")
        if "429" in str(e):
            print("   Rate limited - wait a few seconds and try again")
        return None


def test_multiple_subreddits(subreddits, delay=2):
    """Test multiple subreddits with rate limiting."""
    results = {}
    
    for subreddit in subreddits:
        result = test_subreddit(subreddit)
        if result:
            results[subreddit] = result
        
        # Rate limiting
        if subreddit != subreddits[-1]:
            print(f"\n⏳ Waiting {delay}s to avoid rate limiting...")
            time.sleep(delay)
    
    return results


def generate_trading_signals(sentiment_results):
    """Generate trading signals from sentiment analysis."""
    print(f"\n\n{'='*70}")
    print(f"🎯 TRADING SIGNALS BASED ON SENTIMENT")
    print(f"{'='*70}\n")
    
    for subreddit, sentiment in sentiment_results.items():
        signal = "NONE"
        confidence = "LOW"
        
        # Generate signal based on sentiment and engagement
        if sentiment['sentiment'] > 0.3 and sentiment['avg_upvote_ratio'] > 0.8:
            signal = "BUY"
            confidence = "HIGH" if sentiment['avg_score'] > 100 else "MEDIUM"
        elif sentiment['sentiment'] < -0.3 and sentiment['avg_upvote_ratio'] > 0.7:
            signal = "SELL"
            confidence = "HIGH" if sentiment['avg_score'] > 100 else "MEDIUM"
        elif abs(sentiment['sentiment']) > 0.15:
            signal = "WEAK_" + ("BUY" if sentiment['sentiment'] > 0 else "SELL")
            confidence = "LOW"
        
        print(f"r/{subreddit}:")
        print(f"  Signal: {signal}")
        print(f"  Confidence: {confidence}")
        print(f"  Sentiment: {sentiment['sentiment']:.2f}")
        print(f"  Momentum: {sentiment['momentum']}")
        
        if sentiment['coin_mentions']:
            top_coin = list(sentiment['coin_mentions'].keys())[0]
            print(f"  Hot Coin: {top_coin}")
        print()


def main():
    print("\n" + "="*70)
    print(" REDDIT SENTIMENT ANALYSIS FOR CRYPTO TRADING")
    print("="*70)
    print("\nThis tests the reddit.py algorithm for gathering market intelligence")
    print("from crypto subreddits to drive trading strategies.\n")
    
    # Subreddits to analyze
    crypto_subreddits = [
        'CryptoCurrency',
        'Bitcoin',
        'ethereum',
        # 'solana',  # Uncomment for more (watch rate limits)
        # 'CryptoMarkets',
    ]
    
    print(f"🔍 Analyzing {len(crypto_subreddits)} subreddits...")
    print(f"⚠️  Note: Reddit API has rate limits. Using 2s delay between requests.\n")
    
    # Test multiple subreddits
    results = test_multiple_subreddits(crypto_subreddits, delay=2)
    
    # Generate trading signals
    if results:
        generate_trading_signals(results)
    
    # Summary
    print("\n" + "="*70)
    print(" INTEGRATION WITH NAUTILUSTRADER")
    print("="*70)
    print("""
✅ CAPABILITIES:
   - Real-time sentiment tracking from Reddit
   - Multi-subreddit analysis
   - Coin-specific mention tracking
   - Engagement metrics (score, upvote ratio)
   - Sentiment scoring (bullish/bearish)

⚠️  LIMITATIONS:
   - Rate limits: ~60 requests/minute (unofficial)
   - No historical data (only current hot/new/top posts)
   - Text-based sentiment only (no advanced NLP)
   - Delayed vs real-time price action
   - Susceptible to manipulation/brigading

🔧 RECOMMENDED USAGE:
   1. Use as a SUPPLEMENTARY signal (not primary)
   2. Combine with technical indicators
   3. Focus on high-engagement posts (score > 100)
   4. Track sentiment CHANGES over time
   5. Use for longer timeframes (hours/days, not minutes)
   6. Implement caching to avoid rate limits

🎯 INTEGRATION APPROACH:
   - Actor/component that polls every 5-10 minutes
   - Publishes custom SentimentData messages
   - Strategy subscribes to sentiment updates
   - Adjusts position sizing based on sentiment
   - Uses as confirmation signal for technical entries

📊 EXAMPLE STRATEGY:
   - Technical: EMA crossover generates signal
   - Sentiment: High bullish sentiment (>0.3) → Increase position size 20%
   - Sentiment: Bearish sentiment (<-0.3) → Reduce position size 50%
   - Sentiment: Neutral → Use default position size
""")
    
    print("=" * 70)
    print("✅ Test Complete!")
    print("=" * 70)


if __name__ == "__main__":
    main()
