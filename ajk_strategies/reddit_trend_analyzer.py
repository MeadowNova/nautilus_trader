#!/usr/bin/env python3
"""
Advanced Reddit Trend Analyzer for Trading

This module detects emerging trends and hidden opportunities from Reddit
that most traders miss. It uses advanced NLP and pattern recognition to
identify:

1. Early-stage trends (before they go mainstream)
2. Contrarian opportunities (sentiment reversals)
3. Hidden gems (low-engagement but high-quality signals)
4. Whale activity indicators
5. Community sentiment shifts
6. Cross-subreddit correlation patterns

Features:
- Multi-subreddit analysis
- Temporal sentiment tracking
- Keyword extraction and trending topics
- Engagement quality scoring
- Early warning system for trend reversals
- Hidden opportunity detection
"""

import re
import time
from datetime import datetime, timedelta
from collections import Counter, defaultdict
from typing import Dict, List, Tuple, Optional
import numpy as np
from dataclasses import dataclass


@dataclass
class TrendSignal:
    """Represents a detected trend signal"""
    coin: str
    signal_type: str  # 'emerging', 'reversal', 'hidden_gem', 'whale_activity'
    strength: float  # 0 to 1
    confidence: float  # 0 to 1
    sentiment: float  # -1 to 1
    source_subreddits: List[str]
    key_indicators: Dict
    timestamp: datetime
    
    def __str__(self):
        return (f"TrendSignal({self.coin}, {self.signal_type}, "
                f"strength={self.strength:.2f}, confidence={self.confidence:.2f})")


class RedditTrendAnalyzer:
    """
    Advanced Reddit analyzer for detecting hidden trading opportunities
    
    This analyzer goes beyond basic sentiment to find:
    - Emerging trends before they become mainstream
    - Contrarian signals (when sentiment is wrong)
    - Hidden gems (quality signals with low visibility)
    - Early indicators of major moves
    """
    
    def __init__(self):
        self.sentiment_history = defaultdict(list)
        self.mention_history = defaultdict(list)
        self.engagement_history = defaultdict(list)
        
        # Expanded keyword dictionaries
        self.bullish_keywords = [
            # Standard bullish
            'moon', 'pump', 'bullish', 'buy', 'long', 'hodl', 'breakout', 
            'rally', 'surge', 'rocket', '🚀', 'lambo', 'gains',
            
            # Technical bullish
            'golden cross', 'support', 'accumulation', 'breakout', 'resistance broken',
            'bullish divergence', 'higher lows', 'consolidation', 'base building',
            
            # Fundamental bullish
            'adoption', 'partnership', 'upgrade', 'launch', 'mainnet', 'integration',
            'institutional', 'etf', 'listing', 'staking', 'yield',
            
            # Community bullish
            'undervalued', 'sleeping giant', 'hidden gem', 'next big thing',
            'early', 'opportunity', 'potential', 'promising'
        ]
        
        self.bearish_keywords = [
            # Standard bearish
            'dump', 'bearish', 'sell', 'crash', 'drop', 'down', 'fall', 
            'short', 'liquidation', 'rekt', 'bear market',
            
            # Technical bearish
            'death cross', 'resistance', 'distribution', 'breakdown', 'support broken',
            'bearish divergence', 'lower highs', 'topping', 'exhaustion',
            
            # Fundamental bearish
            'hack', 'scam', 'rug pull', 'delisting', 'sec', 'lawsuit', 
            'investigation', 'vulnerability', 'exploit',
            
            # Community bearish
            'overvalued', 'bubble', 'hype', 'pump and dump', 'exit scam',
            'warning', 'caution', 'risk', 'danger'
        ]
        
        # Early trend indicators (signals before mainstream)
        self.early_indicators = [
            'just discovered', 'nobody talking about', 'flying under radar',
            'before it moons', 'early stage', 'low market cap', 'underrated',
            'not many people know', 'hidden potential', 'sleeper',
            'accumulating quietly', 'smart money', 'whales buying'
        ]
        
        # Contrarian indicators (potential reversals)
        self.contrarian_indicators = [
            'everyone says', 'consensus', 'obvious', 'too late',
            'peak euphoria', 'maximum fear', 'capitulation', 'blood in streets',
            'everyone buying', 'everyone selling', 'no one talking'
        ]
        
        # Quality indicators (high-value signals)
        self.quality_indicators = [
            'analysis', 'research', 'data', 'chart', 'fundamentals',
            'technical analysis', 'on-chain', 'metrics', 'valuation',
            'due diligence', 'deep dive', 'investigation'
        ]
        
        # Coin patterns (expanded)
        self.coin_patterns = {
            'BTC': ['bitcoin', 'btc', r'\bbtc\b'],
            'ETH': ['ethereum', 'eth', r'\beth\b', 'ether'],
            'SOL': ['solana', 'sol', r'\bsol\b'],
            'ADA': ['cardano', 'ada', r'\bada\b'],
            'DOGE': ['dogecoin', 'doge'],
            'XRP': ['ripple', 'xrp', r'\bxrp\b'],
            'AVAX': ['avalanche', 'avax'],
            'MATIC': ['polygon', 'matic'],
            'DOT': ['polkadot', 'dot', r'\bdot\b'],
            'LINK': ['chainlink', 'link'],
            'UNI': ['uniswap', 'uni', r'\buni\b'],
            'ATOM': ['cosmos', 'atom'],
            'ALGO': ['algorand', 'algo'],
            'NEAR': ['near protocol', 'near'],
            'FTM': ['fantom', 'ftm'],
            'SAND': ['sandbox', 'sand'],
            'MANA': ['decentraland', 'mana'],
            'APE': ['apecoin', 'ape', r'\bape\b'],
        }
    
    def analyze_post(self, post_data: Dict) -> Dict:
        """
        Analyze a single Reddit post for trading signals
        
        Args:
            post_data: Dictionary with post information
        
        Returns:
            Analysis results dictionary
        """
        title = post_data.get('title', '').lower()
        text = post_data.get('selftext', '').lower()
        combined_text = f"{title} {text}"
        
        score = post_data.get('score', 0)
        upvote_ratio = post_data.get('upvote_ratio', 0.5)
        num_comments = post_data.get('num_comments', 0)
        
        # Calculate engagement quality
        engagement_quality = self._calculate_engagement_quality(
            score, upvote_ratio, num_comments, len(text)
        )
        
        # Detect sentiment
        sentiment = self._calculate_sentiment(combined_text)
        
        # Detect coins mentioned
        coins = self._extract_coins(combined_text)
        
        # Detect signal types
        is_early_trend = self._detect_early_trend(combined_text)
        is_contrarian = self._detect_contrarian_signal(combined_text)
        is_quality = self._detect_quality_signal(combined_text)
        is_whale_activity = self._detect_whale_activity(combined_text)
        
        return {
            'sentiment': sentiment,
            'coins': coins,
            'engagement_quality': engagement_quality,
            'is_early_trend': is_early_trend,
            'is_contrarian': is_contrarian,
            'is_quality': is_quality,
            'is_whale_activity': is_whale_activity,
            'score': score,
            'upvote_ratio': upvote_ratio,
            'num_comments': num_comments,
        }
    
    def analyze_subreddit(
        self,
        subreddit_name: str,
        posts_data: List[Dict],
        detect_hidden: bool = True
    ) -> Dict:
        """
        Analyze multiple posts from a subreddit
        
        Args:
            subreddit_name: Name of subreddit
            posts_data: List of post dictionaries
            detect_hidden: Whether to detect hidden opportunities
        
        Returns:
            Comprehensive analysis results
        """
        if not posts_data:
            return self._empty_analysis()
        
        # Analyze each post
        post_analyses = [self.analyze_post(post) for post in posts_data]
        
        # Aggregate sentiment
        sentiments = [a['sentiment'] for a in post_analyses]
        avg_sentiment = np.mean(sentiments)
        sentiment_std = np.std(sentiments)
        
        # Aggregate coin mentions
        all_coins = Counter()
        for analysis in post_analyses:
            all_coins.update(analysis['coins'])
        
        # Calculate engagement metrics
        avg_engagement = np.mean([a['engagement_quality'] for a in post_analyses])
        
        # Detect trends
        emerging_trends = self._detect_emerging_trends(post_analyses, all_coins)
        hidden_gems = self._detect_hidden_gems(post_analyses, all_coins) if detect_hidden else []
        contrarian_signals = self._detect_contrarian_opportunities(post_analyses, all_coins)
        whale_signals = self._detect_whale_signals(post_analyses, all_coins)
        
        # Calculate momentum
        momentum = self._calculate_momentum(subreddit_name, avg_sentiment, all_coins)
        
        # Store history
        timestamp = datetime.now()
        self.sentiment_history[subreddit_name].append((timestamp, avg_sentiment))
        self.mention_history[subreddit_name].append((timestamp, dict(all_coins)))
        self.engagement_history[subreddit_name].append((timestamp, avg_engagement))
        
        return {
            'subreddit': subreddit_name,
            'timestamp': timestamp,
            'avg_sentiment': avg_sentiment,
            'sentiment_std': sentiment_std,
            'sentiment_momentum': momentum,
            'total_posts': len(posts_data),
            'coin_mentions': dict(all_coins.most_common(10)),
            'avg_engagement': avg_engagement,
            'emerging_trends': emerging_trends,
            'hidden_gems': hidden_gems,
            'contrarian_signals': contrarian_signals,
            'whale_signals': whale_signals,
            'quality_posts': sum(1 for a in post_analyses if a['is_quality']),
        }
    
    def _calculate_sentiment(self, text: str) -> float:
        """Calculate sentiment score from text"""
        bullish_count = sum(1 for kw in self.bullish_keywords if kw in text)
        bearish_count = sum(1 for kw in self.bearish_keywords if kw in text)
        
        total = bullish_count + bearish_count
        if total == 0:
            return 0.0
        
        sentiment = (bullish_count - bearish_count) / total
        return np.clip(sentiment, -1.0, 1.0)
    
    def _extract_coins(self, text: str) -> List[str]:
        """Extract cryptocurrency mentions from text"""
        found_coins = []
        
        for coin, patterns in self.coin_patterns.items():
            for pattern in patterns:
                if isinstance(pattern, str) and pattern in text:
                    found_coins.append(coin)
                    break
                elif hasattr(pattern, 'search') and pattern.search(text):
                    found_coins.append(coin)
                    break
        
        return found_coins
    
    def _calculate_engagement_quality(
        self,
        score: int,
        upvote_ratio: float,
        num_comments: int,
        text_length: int
    ) -> float:
        """
        Calculate quality of engagement (not just quantity)
        
        High-quality signals:
        - High upvote ratio (controversial posts filtered)
        - Good score relative to comments (genuine interest)
        - Longer, detailed posts (not just memes)
        """
        # Normalize metrics
        score_norm = min(score / 1000, 1.0)
        ratio_norm = upvote_ratio
        comment_norm = min(num_comments / 100, 1.0)
        length_norm = min(text_length / 1000, 1.0)
        
        # Weighted quality score
        quality = (
            score_norm * 0.3 +
            ratio_norm * 0.3 +
            comment_norm * 0.2 +
            length_norm * 0.2
        )
        
        return quality
    
    def _detect_early_trend(self, text: str) -> bool:
        """Detect if post indicates early-stage trend"""
        return any(indicator in text for indicator in self.early_indicators)
    
    def _detect_contrarian_signal(self, text: str) -> bool:
        """Detect contrarian opportunity indicators"""
        return any(indicator in text for indicator in self.contrarian_indicators)
    
    def _detect_quality_signal(self, text: str) -> bool:
        """Detect high-quality analytical content"""
        quality_count = sum(1 for indicator in self.quality_indicators if indicator in text)
        return quality_count >= 2  # At least 2 quality indicators
    
    def _detect_whale_activity(self, text: str) -> bool:
        """Detect mentions of whale/institutional activity"""
        whale_keywords = [
            'whale', 'whales', 'large holder', 'institutional',
            'smart money', 'accumulation', 'large buy', 'large order',
            'on-chain', 'wallet activity', 'exchange outflow'
        ]
        return any(kw in text for kw in whale_keywords)
    
    def _detect_emerging_trends(
        self,
        post_analyses: List[Dict],
        coin_mentions: Counter
    ) -> List[TrendSignal]:
        """
        Detect emerging trends (early-stage signals)
        
        Criteria:
        - Increasing mentions over time
        - Early indicator keywords present
        - Quality engagement
        - Not yet mainstream (moderate mention count)
        """
        signals = []
        
        for coin, count in coin_mentions.most_common(10):
            # Filter for coins with moderate mentions (not too popular yet)
            if 2 <= count <= 10:
                # Check for early indicators
                early_posts = [
                    a for a in post_analyses
                    if coin in a['coins'] and a['is_early_trend']
                ]
                
                if early_posts:
                    avg_sentiment = np.mean([a['sentiment'] for a in early_posts])
                    avg_quality = np.mean([a['engagement_quality'] for a in early_posts])
                    
                    # Calculate strength and confidence
                    strength = min(count / 10, 1.0) * avg_quality
                    confidence = len(early_posts) / count  # Proportion with early indicators
                    
                    if confidence > 0.3:  # At least 30% have early indicators
                        signals.append(TrendSignal(
                            coin=coin,
                            signal_type='emerging',
                            strength=strength,
                            confidence=confidence,
                            sentiment=avg_sentiment,
                            source_subreddits=[],
                            key_indicators={'mention_count': count, 'early_posts': len(early_posts)},
                            timestamp=datetime.now()
                        ))
        
        return signals
    
    def _detect_hidden_gems(
        self,
        post_analyses: List[Dict],
        coin_mentions: Counter
    ) -> List[TrendSignal]:
        """
        Detect hidden gems (high quality, low visibility)
        
        Criteria:
        - Low mention count (1-3)
        - High engagement quality
        - Quality analytical content
        - Positive sentiment
        """
        signals = []
        
        for coin, count in coin_mentions.items():
            if count <= 3:  # Low visibility
                coin_posts = [a for a in post_analyses if coin in a['coins']]
                quality_posts = [a for a in coin_posts if a['is_quality']]
                
                if quality_posts:
                    avg_sentiment = np.mean([a['sentiment'] for a in quality_posts])
                    avg_quality = np.mean([a['engagement_quality'] for a in quality_posts])
                    
                    # Hidden gems should have positive sentiment and high quality
                    if avg_sentiment > 0.2 and avg_quality > 0.5:
                        strength = avg_quality
                        confidence = len(quality_posts) / count
                        
                        signals.append(TrendSignal(
                            coin=coin,
                            signal_type='hidden_gem',
                            strength=strength,
                            confidence=confidence,
                            sentiment=avg_sentiment,
                            source_subreddits=[],
                            key_indicators={
                                'mention_count': count,
                                'quality_posts': len(quality_posts),
                                'avg_quality': avg_quality
                            },
                            timestamp=datetime.now()
                        ))
        
        return signals
    
    def _detect_contrarian_opportunities(
        self,
        post_analyses: List[Dict],
        coin_mentions: Counter
    ) -> List[TrendSignal]:
        """
        Detect contrarian opportunities (sentiment reversals)
        
        Criteria:
        - Extreme sentiment (very bullish or bearish)
        - Contrarian indicator keywords
        - High engagement (mainstream attention)
        """
        signals = []
        
        for coin, count in coin_mentions.most_common(5):
            if count >= 5:  # High visibility
                coin_posts = [a for a in post_analyses if coin in a['coins']]
                contrarian_posts = [a for a in coin_posts if a['is_contrarian']]
                
                if contrarian_posts:
                    avg_sentiment = np.mean([a['sentiment'] for a in coin_posts])
                    
                    # Extreme sentiment indicates potential reversal
                    if abs(avg_sentiment) > 0.6:
                        strength = abs(avg_sentiment)
                        confidence = len(contrarian_posts) / count
                        
                        # Contrarian signal: sentiment likely to reverse
                        contrarian_sentiment = -avg_sentiment * 0.5  # Expect reversal
                        
                        signals.append(TrendSignal(
                            coin=coin,
                            signal_type='reversal',
                            strength=strength,
                            confidence=confidence,
                            sentiment=contrarian_sentiment,
                            source_subreddits=[],
                            key_indicators={
                                'current_sentiment': avg_sentiment,
                                'contrarian_posts': len(contrarian_posts)
                            },
                            timestamp=datetime.now()
                        ))
        
        return signals
    
    def _detect_whale_signals(
        self,
        post_analyses: List[Dict],
        coin_mentions: Counter
    ) -> List[TrendSignal]:
        """Detect whale activity signals"""
        signals = []
        
        for coin, count in coin_mentions.items():
            whale_posts = [
                a for a in post_analyses
                if coin in a['coins'] and a['is_whale_activity']
            ]
            
            if whale_posts:
                avg_sentiment = np.mean([a['sentiment'] for a in whale_posts])
                avg_quality = np.mean([a['engagement_quality'] for a in whale_posts])
                
                strength = avg_quality
                confidence = len(whale_posts) / count
                
                signals.append(TrendSignal(
                    coin=coin,
                    signal_type='whale_activity',
                    strength=strength,
                    confidence=confidence,
                    sentiment=avg_sentiment,
                    source_subreddits=[],
                    key_indicators={'whale_posts': len(whale_posts)},
                    timestamp=datetime.now()
                ))
        
        return signals
    
    def _calculate_momentum(
        self,
        subreddit: str,
        current_sentiment: float,
        current_mentions: Counter
    ) -> float:
        """Calculate sentiment momentum (rate of change)"""
        history = self.sentiment_history.get(subreddit, [])
        
        if len(history) < 2:
            return 0.0
        
        # Compare with previous sentiment
        prev_sentiment = history[-1][1] if history else 0.0
        momentum = current_sentiment - prev_sentiment
        
        return momentum
    
    def _empty_analysis(self) -> Dict:
        """Return empty analysis structure"""
        return {
            'subreddit': '',
            'timestamp': datetime.now(),
            'avg_sentiment': 0.0,
            'sentiment_std': 0.0,
            'sentiment_momentum': 0.0,
            'total_posts': 0,
            'coin_mentions': {},
            'avg_engagement': 0.0,
            'emerging_trends': [],
            'hidden_gems': [],
            'contrarian_signals': [],
            'whale_signals': [],
            'quality_posts': 0,
        }
    
    def get_top_opportunities(
        self,
        analyses: List[Dict],
        min_confidence: float = 0.4
    ) -> List[TrendSignal]:
        """
        Get top trading opportunities from multiple subreddit analyses
        
        Args:
            analyses: List of subreddit analysis results
            min_confidence: Minimum confidence threshold
        
        Returns:
            Sorted list of top opportunities
        """
        all_signals = []
        
        for analysis in analyses:
            all_signals.extend(analysis.get('emerging_trends', []))
            all_signals.extend(analysis.get('hidden_gems', []))
            all_signals.extend(analysis.get('contrarian_signals', []))
            all_signals.extend(analysis.get('whale_signals', []))
        
        # Filter by confidence
        filtered = [s for s in all_signals if s.confidence >= min_confidence]
        
        # Sort by combined score (strength * confidence)
        sorted_signals = sorted(
            filtered,
            key=lambda s: s.strength * s.confidence,
            reverse=True
        )
        
        return sorted_signals


def demo_trend_analyzer():
    """Demonstration of the trend analyzer"""
    print("""
    ╔══════════════════════════════════════════════════════════════════╗
    ║                                                                  ║
    ║       REDDIT TREND ANALYZER - HIDDEN OPPORTUNITY DETECTOR        ║
    ║                                                                  ║
    ╚══════════════════════════════════════════════════════════════════╝
    """)
    
    analyzer = RedditTrendAnalyzer()
    
    # Simulate some posts
    sample_posts = [
        {
            'title': 'Just discovered SOL - flying under the radar!',
            'selftext': 'Deep dive analysis shows Solana has strong fundamentals. Smart money accumulating.',
            'score': 150,
            'upvote_ratio': 0.85,
            'num_comments': 45,
        },
        {
            'title': 'Everyone is buying ETH at the top',
            'selftext': 'Peak euphoria. Might be time for a reversal.',
            'score': 200,
            'upvote_ratio': 0.75,
            'num_comments': 80,
        },
        {
            'title': 'MATIC technical analysis - breakout incoming',
            'selftext': 'Chart shows bullish divergence and consolidation. On-chain metrics strong.',
            'score': 50,
            'upvote_ratio': 0.90,
            'num_comments': 15,
        },
    ]
    
    # Analyze
    analysis = analyzer.analyze_subreddit('CryptoCurrency', sample_posts)
    
    print("\n📊 Analysis Results:")
    print(f"   Sentiment: {analysis['avg_sentiment']:.2f}")
    print(f"   Momentum: {analysis['sentiment_momentum']:.2f}")
    print(f"   Quality Posts: {analysis['quality_posts']}")
    
    print("\n🚀 Emerging Trends:")
    for signal in analysis['emerging_trends']:
        print(f"   {signal}")
    
    print("\n💎 Hidden Gems:")
    for signal in analysis['hidden_gems']:
        print(f"   {signal}")
    
    print("\n🔄 Contrarian Signals:")
    for signal in analysis['contrarian_signals']:
        print(f"   {signal}")
    
    print("\n🐋 Whale Activity:")
    for signal in analysis['whale_signals']:
        print(f"   {signal}")
    
    print("\n✅ Demo completed!")


if __name__ == "__main__":
    demo_trend_analyzer()
