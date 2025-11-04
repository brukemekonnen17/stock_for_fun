"""
StockTwits API Adapter
Fetches real-time social sentiment data for momentum trading signals.

StockTwits Public API: https://stocktwits.com/developers/docs
No API key required for basic public endpoints (rate limits apply)
"""
import requests
import logging
from typing import List, Dict, Any

logger = logging.getLogger(__name__)

# StockTwits API base URL (Public stream endpoint for a symbol)
BASE_URL = "https://api.stocktwits.com/api/2/streams/symbol/{ticker}.json"

def fetch_recent_messages(ticker: str, limit: int = 50) -> List[Dict[str, Any]]:
    """
    Fetches the latest messages for a given ticker from StockTwits.
    
    Args:
        ticker: Stock symbol (e.g., "AAPL")
        limit: Maximum number of messages to fetch (default: 50)
    
    Returns:
        List of message dictionaries, or empty list on error
    """
    ticker = ticker.upper().strip()
    url = BASE_URL.format(ticker=ticker)
    
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
    }
    
    try:
        # Added headers to mimic a browser request
        response = requests.get(url, headers=headers, params={'limit': limit}, timeout=10)
        response.raise_for_status()  # Catches 4xx/5xx errors
        
        data = response.json()
        
        # Return only the 'messages' list
        messages = data.get('messages', [])
        logger.debug(f"Fetched {len(messages)} messages from StockTwits for {ticker}")
        return messages
    
    except requests.exceptions.HTTPError as e:
        if e.response.status_code == 404:
            logger.debug(f"Ticker {ticker} not found in StockTwits")
            return []
        elif e.response.status_code == 429:
            logger.warning(f"StockTwits rate limit exceeded for {ticker}")
            return []
        else:
            logger.error(f"StockTwits HTTP error for {ticker}: {e}")
            return []
    except requests.exceptions.RequestException as e:
        logger.error(f"StockTwits API error for {ticker}: {e}")
        return []
    except Exception as e:
        logger.error(f"Unexpected error fetching StockTwits data for {ticker}: {e}")
        return []

