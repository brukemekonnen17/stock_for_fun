"""
Social Sentiment Scanner
Processes StockTwits messages into actionable sentiment metrics for momentum trading.

Uses simple counting of user-labeled sentiment (Bullish/Bearish) which research
confirms is the least error-prone approach for rapid-fire trading models.
"""
import logging
from typing import Dict, Any
from datetime import datetime
from .stocktwits_adapter import fetch_recent_messages

logger = logging.getLogger(__name__)

def get_real_time_sentiment(ticker: str, limit: int = 50) -> Dict[str, Any]:
    """
    Calculates the sentiment score and message volume based on recent StockTwits messages.
    
    This is the core metric for low-cap momentum trading - high mention volume
    combined with bullish sentiment indicates retail momentum.
    
    Args:
        ticker: Stock symbol (e.g., "AAPL")
        limit: Number of recent messages to analyze (default: 50)
    
    Returns:
        Dictionary with:
        - ticker: Stock symbol
        - mention_count_total: Total messages analyzed (key indicator for low-float mania)
        - sentiment_score: -1.0 to 1.0 (positive = bullish, negative = bearish)
        - bullish_pct: Percentage of bullish messages
        - bearish_pct: Percentage of bearish messages
        - source: "StockTwits"
        - timestamp: When the analysis was performed
    """
    ticker = ticker.upper().strip()
    
    messages = fetch_recent_messages(ticker, limit=limit)
    
    if not messages:
        logger.debug(f"No messages found for {ticker} on StockTwits")
        return {
            "ticker": ticker,
            "mention_count_total": 0,
            "sentiment_score": 0.0,
            "bullish_pct": 0.0,
            "bearish_pct": 0.0,
            "source": "StockTwits",
            "timestamp": datetime.utcnow().isoformat()
        }
    
    bullish_count = 0
    bearish_count = 0
    total_tagged = 0
    
    for msg in messages:
        # Check if a user explicitly tagged a sentiment
        # StockTwits structure: msg['sentiment']['basic'] = 'Bullish' | 'Bearish' | None
        sentiment_obj = msg.get('sentiment', {})
        if isinstance(sentiment_obj, dict):
            sentiment = sentiment_obj.get('basic')
        else:
            sentiment = sentiment_obj
        
        if sentiment == 'Bullish':
            bullish_count += 1
            total_tagged += 1
        elif sentiment == 'Bearish':
            bearish_count += 1
            total_tagged += 1
    
    # Calculate the Sentiment Score (Range: -1.0 to 1.0)
    # Formula: (bullish - bearish) / total_tagged
    # This gives us a normalized score where:
    #   +1.0 = 100% bullish
    #   -1.0 = 100% bearish
    #   0.0 = neutral or no tagged sentiment
    if total_tagged > 0:
        sentiment_score = (bullish_count - bearish_count) / total_tagged
    else:
        # Neutral baseline if no one tagged a sentiment in the last N messages
        sentiment_score = 0.0
    
    total_messages = len(messages)
    bullish_pct = (bullish_count / total_messages * 100) if total_messages > 0 else 0.0
    bearish_pct = (bearish_count / total_messages * 100) if total_messages > 0 else 0.0
    
    result = {
        "ticker": ticker,
        # The key indicator for low-float mania - high volume = momentum
        "mention_count_total": total_messages,
        # The agent's decision input - positive = bullish momentum
        "sentiment_score": round(sentiment_score, 3),
        "bullish_pct": round(bullish_pct, 1),
        "bearish_pct": round(bearish_pct, 1),
        "tagged_count": total_tagged,  # How many messages had explicit sentiment
        "source": "StockTwits",
        "timestamp": datetime.utcnow().isoformat()
    }
    
    logger.info(
        f"Sentiment for {ticker}: score={sentiment_score:.3f}, "
        f"mentions={total_messages}, bullish={bullish_count}, bearish={bearish_count}"
    )
    
    return result

