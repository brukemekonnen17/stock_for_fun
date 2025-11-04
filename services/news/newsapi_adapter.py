"""
NewsAPI adapter for real news feeds.
Free tier: 100 requests/day, 1000 requests/month
Get key: https://newsapi.org/
"""
import os
import logging
from datetime import datetime, timedelta
from typing import List

from apps.api.schemas import NewsItem

logger = logging.getLogger(__name__)

NEWSAPI_KEY = os.getenv("NEWSAPI_KEY", "")
NEWSAPI_URL = "https://newsapi.org/v2/everything"

def get_recent_news_items(ticker: str, limit: int = 5, days_back: int = 7) -> List[NewsItem]:
    """
    Fetch recent news for a ticker using NewsAPI.
    Falls back to multiple sources if NewsAPI fails.
    """
    # Always try Yahoo Finance first (it's free and reliable)
    yahoo_news = _try_yahoo_news(ticker, limit)
    if yahoo_news and len(yahoo_news) > 0:
        logger.info(f"Using Yahoo Finance news for {ticker}: {len(yahoo_news)} items")
        return yahoo_news
    
    # Try NewsAPI if key is configured
    if NEWSAPI_KEY and NEWSAPI_KEY != "":
        try:
            # Search for news about the company
            from_date = (datetime.utcnow() - timedelta(days=days_back)).strftime("%Y-%m-%d")
            params = {
                "q": ticker,
                "apiKey": NEWSAPI_KEY,
                "sortBy": "publishedAt",
                "language": "en",
                "pageSize": limit,
                "from": from_date,
            }
            
            # Use sync requests
            import requests
            response = requests.get(NEWSAPI_URL, params=params, timeout=10)
            response.raise_for_status()
            data = response.json()
            
            articles = data.get("articles", [])
            
            items = []
            for article in articles[:limit]:
                try:
                    # Simple sentiment estimation (can be enhanced with NLP)
                    sentiment = _estimate_sentiment(article.get("title", "") + " " + article.get("description", ""))
                    
                    items.append(NewsItem(
                        headline=article.get("title", "No title")[:200],
                        url=article.get("url", "https://example.com"),
                        timestamp=datetime.fromisoformat(article.get("publishedAt", datetime.utcnow().isoformat()).replace("Z", "+00:00")),
                        sentiment=sentiment
                    ))
                except Exception as e:
                    logger.warning(f"Failed to parse article: {e}")
                    continue
            
            if items:
                logger.info(f"Using NewsAPI news for {ticker}: {len(items)} items")
                return items
        except Exception as e:
            logger.warning(f"NewsAPI fetch failed for {ticker}: {e}")
    
    # Fallback: stub news (should rarely happen)
    logger.warning(f"All news sources failed for {ticker}, using stub news")
    return _stub_news(ticker, limit)

def _try_yahoo_news(ticker: str, limit: int) -> List[NewsItem]:
    """Try to get news from Yahoo Finance as fallback"""
    try:
        import yfinance as yf
        stock = yf.Ticker(ticker)
        
        # Fetch news with timeout
        import signal
        
        # Get news (may take a moment)
        news = stock.news
        
        if news and len(news) > 0:
            items = []
            for article in news[:limit]:
                try:
                    # Extract sentiment from title and description
                    title = article.get("title", "")
                    # Try to get description if available
                    description = article.get("summary", "") or article.get("description", "")
                    full_text = f"{title} {description}"
                    sentiment = _estimate_sentiment(full_text)
                    
                    # Parse timestamp
                    pub_time = article.get("providerPublishTime", 0)
                    if pub_time and isinstance(pub_time, (int, float)) and pub_time > 0:
                        timestamp = datetime.fromtimestamp(pub_time)
                    elif isinstance(pub_time, str):
                        # Try to parse string timestamp
                        try:
                            timestamp = datetime.fromisoformat(pub_time.replace("Z", "+00:00"))
                        except:
                            timestamp = datetime.utcnow()
                    else:
                        timestamp = datetime.utcnow()
                    
                    # Get URL
                    url = article.get("link") or article.get("url") or f"https://finance.yahoo.com/quote/{ticker}"
                    
                    items.append(NewsItem(
                        headline=title[:200] if title else f"{ticker} news",
                        url=url,
                        timestamp=timestamp,
                        sentiment=sentiment
                    ))
                except Exception as e:
                    logger.warning(f"Failed to parse Yahoo news article: {e}")
                    continue
            
            if items:
                logger.info(f"Found {len(items)} news items from Yahoo Finance for {ticker}")
                return items
            else:
                logger.warning(f"Yahoo Finance returned {len(news)} articles but none were parseable for {ticker}")
        else:
            logger.debug(f"No news found for {ticker} on Yahoo Finance")
    except ImportError:
        logger.warning("yfinance not installed - cannot fetch Yahoo Finance news")
    except Exception as e:
        logger.warning(f"Yahoo Finance news fetch failed for {ticker}: {e}", exc_info=True)
    
    return []

def _estimate_sentiment(text: str) -> float:
    """
    Simple sentiment estimation based on keywords.
    Returns -1 (very negative) to 1 (very positive).
    
    For production, use a proper sentiment analysis library (vaderSentiment, TextBlob, etc.)
    """
    text_lower = text.lower()
    
    positive_words = ["beat", "surge", "gain", "rise", "up", "strong", "profit", "growth", "positive", "bullish", "exceeds"]
    negative_words = ["miss", "fall", "drop", "down", "loss", "weak", "decline", "negative", "bearish", "concern"]
    
    pos_count = sum(1 for word in positive_words if word in text_lower)
    neg_count = sum(1 for word in negative_words if word in text_lower)
    
    if pos_count == 0 and neg_count == 0:
        return 0.0
    
    # Normalize to [-1, 1]
    sentiment = (pos_count - neg_count) / max(pos_count + neg_count, 1)
    return max(-1.0, min(1.0, sentiment))

def _stub_news(ticker: str, limit: int) -> List[NewsItem]:
    """Fallback stub news"""
    now = datetime.utcnow()
    return [
        NewsItem(
            headline=f"{ticker} - Market analysis and trading activity",
            url=f"https://finance.yahoo.com/quote/{ticker}",
            timestamp=now - timedelta(hours=i),
            sentiment=0.0
        )
        for i in range(limit)
    ]

