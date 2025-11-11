"""
Multi-Source Social Data Aggregator
Aggregates social sentiment and mentions from multiple sources for comprehensive analysis.

Sources:
1. StockTwits - Real-time trading-focused social network
2. Reddit - r/wallstreetbets, r/stocks, r/investing
3. Twitter/X - Public mentions (if API available)
4. Google Trends - Search volume trends

This provides a more robust view than relying on a single source.
"""
import logging
from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta
import requests
import time

logger = logging.getLogger(__name__)

# Import existing adapters
try:
    from .stocktwits_adapter import fetch_recent_messages
    from .sentiment_scanner import get_real_time_sentiment
    STOCKTWITS_AVAILABLE = True
except ImportError:
    STOCKTWITS_AVAILABLE = False
    logger.warning("StockTwits adapter not available")

def fetch_reddit_mentions(ticker: str, subreddits: List[str] = None) -> Dict[str, Any]:
    """
    Fetch Reddit mentions using Pushshift API (free, no auth required).
    
    Args:
        ticker: Stock symbol
        subreddits: List of subreddits to search (default: ['wallstreetbets', 'stocks', 'investing'])
    
    Returns:
        Dict with mention count, upvote ratio, and sentiment indicators
    """
    if subreddits is None:
        subreddits = ['wallstreetbets', 'stocks', 'investing', 'StockMarket', 'pennystocks']
    
    ticker = ticker.upper()
    total_mentions = 0
    total_upvotes = 0
    total_score = 0
    
    # Pushshift API (free, no auth)
    # Note: Pushshift may have rate limits or downtime
    base_url = "https://api.pushshift.io/reddit/search/submission/"
    
    for subreddit in subreddits:
        try:
            params = {
                'q': ticker,
                'subreddit': subreddit,
                'size': 25,
                'sort': 'created_utc',
                'sort_type': 'created_utc'
            }
            
            response = requests.get(base_url, params=params, timeout=10)
            if response.status_code == 200:
                data = response.json()
                posts = data.get('data', [])
                
                for post in posts:
                    total_mentions += 1
                    total_upvotes += post.get('ups', 0)
                    total_score += post.get('score', 0)
            
            time.sleep(0.5)  # Rate limit protection
            
        except Exception as e:
            logger.debug(f"Reddit fetch failed for r/{subreddit}: {e}")
            continue
    
    avg_upvote_ratio = (total_upvotes / total_mentions) if total_mentions > 0 else 0.0
    avg_score = (total_score / total_mentions) if total_mentions > 0 else 0.0
    
    return {
        'source': 'reddit',
        'mention_count': total_mentions,
        'avg_upvotes': avg_upvote_ratio,
        'avg_score': avg_score,
        'subreddits_searched': subreddits
    }

def fetch_google_trends(ticker: str) -> Dict[str, Any]:
    """
    Fetch Google Trends data using pytrends (if available) or simple API.
    
    Note: Google Trends API is limited. This is a placeholder for future implementation.
    
    Args:
        ticker: Stock symbol
    
    Returns:
        Dict with trend indicators
    """
    # Placeholder - would need pytrends library
    # For now, return neutral data
    return {
        'source': 'google_trends',
        'trend_score': 0.0,  # 0-100 scale
        'trend_change_7d': 0.0,  # Percentage change
        'available': False,
        'note': 'Google Trends integration requires pytrends library'
    }

def aggregate_social_data(ticker: str) -> Dict[str, Any]:
    """
    Aggregate social data from multiple sources.
    
    Args:
        ticker: Stock symbol
    
    Returns:
        Comprehensive social data dictionary with:
        - sources: List of sources used
        - total_mentions: Combined mention count
        - sentiment_score: Aggregated sentiment (-1 to 1)
        - bull_ratio: Bullish sentiment ratio
        - source_breakdown: Per-source metrics
        - confidence: Data quality indicator
    """
    ticker = ticker.upper()
    sources_used = []
    source_breakdown = {}
    total_mentions_all = 0
    weighted_sentiment = 0.0
    total_weight = 0.0
    
    # 1. StockTwits (primary source - trading-focused)
    if STOCKTWITS_AVAILABLE:
        try:
            stocktwits_data = get_real_time_sentiment(ticker, limit=100)
            if stocktwits_data.get('mention_count_total', 0) > 0:
                sources_used.append('stocktwits')
                mentions_st = stocktwits_data.get('mention_count_total', 0)
                sentiment_st = stocktwits_data.get('sentiment_score', 0.0)
                
                source_breakdown['stocktwits'] = {
                    'mentions': mentions_st,
                    'sentiment_score': sentiment_st,
                    'bullish_pct': stocktwits_data.get('bullish_pct', 0.0),
                    'bearish_pct': stocktwits_data.get('bearish_pct', 0.0),
                    'tagged_count': stocktwits_data.get('tagged_count', 0)
                }
                
                total_mentions_all += mentions_st
                # Weight by mention count (more mentions = more reliable)
                weight = min(mentions_st / 50.0, 1.0)  # Cap weight at 1.0
                weighted_sentiment += sentiment_st * weight
                total_weight += weight
        except Exception as e:
            logger.warning(f"StockTwits fetch failed: {e}")
    
    # 2. Reddit (broader retail sentiment)
    try:
        reddit_data = fetch_reddit_mentions(ticker)
        if reddit_data.get('mention_count', 0) > 0:
            sources_used.append('reddit')
            mentions_rd = reddit_data.get('mention_count', 0)
            # Convert upvote ratio to sentiment proxy (0.5 = neutral, >0.5 = bullish)
            sentiment_rd = (reddit_data.get('avg_upvotes', 0.5) - 0.5) * 2.0  # Scale to -1 to 1
            
            source_breakdown['reddit'] = {
                'mentions': mentions_rd,
                'avg_upvotes': reddit_data.get('avg_upvotes', 0.0),
                'avg_score': reddit_data.get('avg_score', 0.0),
                'sentiment_proxy': sentiment_rd,
                'subreddits': reddit_data.get('subreddits_searched', [])
            }
            
            total_mentions_all += mentions_rd
            weight = min(mentions_rd / 50.0, 1.0)
            weighted_sentiment += sentiment_rd * weight
            total_weight += weight
    except Exception as e:
        logger.warning(f"Reddit fetch failed: {e}")
    
    # 3. Google Trends (search volume - future)
    # trends_data = fetch_google_trends(ticker)
    # Would add here when implemented
    
    # Calculate aggregated metrics
    if total_weight > 0:
        aggregated_sentiment = weighted_sentiment / total_weight
    else:
        aggregated_sentiment = 0.0
    
    # Calculate bull ratio from available sources
    bull_count = 0
    bear_count = 0
    for source_data in source_breakdown.values():
        if 'bullish_pct' in source_data:
            bull_count += source_data.get('bullish_pct', 0) / 100.0 * source_data.get('mentions', 0)
            bear_count += source_data.get('bearish_pct', 0) / 100.0 * source_data.get('mentions', 0)
    
    total_tagged = bull_count + bear_count
    bull_ratio = (bull_count / total_tagged) if total_tagged > 0 else 0.5
    
    # Confidence score (0-1): Based on number of sources and mention volume
    confidence = min(len(sources_used) / 2.0, 1.0) * min(total_mentions_all / 100.0, 1.0)
    
    result = {
        'ticker': ticker,
        'timestamp': datetime.utcnow().isoformat(),
        'sources': sources_used,
        'total_mentions': total_mentions_all,
        'sentiment_score': round(aggregated_sentiment, 3),
        'bull_ratio': round(bull_ratio, 3),
        'source_breakdown': source_breakdown,
        'confidence': round(confidence, 2),
        'data_quality': 'high' if len(sources_used) >= 2 and total_mentions_all >= 20 else 'medium' if total_mentions_all >= 10 else 'low'
    }
    
    logger.info(
        f"Social data for {ticker}: {len(sources_used)} sources, "
        f"{total_mentions_all} mentions, sentiment={aggregated_sentiment:.3f}"
    )
    
    return result

