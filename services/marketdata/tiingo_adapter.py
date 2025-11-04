"""
Tiingo Market Data Adapter
Production-grade market data provider with reliable real-time quotes.

Free tier: 50 requests/day
Paid tiers available with higher limits

Sign up: https://api.tiingo.com/documentation/end-of-day
API Key: https://www.tiingo.com/account/api/token
"""
import requests
import os
import logging
from typing import Optional, Dict, Any
from datetime import datetime

logger = logging.getLogger(__name__)

class TiingoAdapter:
    """
    Tiingo implementation of the MarketDataProvider.
    Requires TIINGO_API_KEY in .env
    """
    
    BASE_URL = "https://api.tiingo.com/tiingo"
    
    def __init__(self):
        """Initialize Tiingo adapter with API key from environment"""
        self.api_key = os.getenv("TIINGO_API_KEY")
        if not self.api_key:
            logger.warning("TIINGO_API_KEY not found. Tiingo adapter is disabled.")
            self.api_key = None
    
    def get_real_time_quote(self, ticker: str) -> Optional[Dict[str, Any]]:
        """
        Get real-time quote from Tiingo.
        Returns standardized quote dict or None if unavailable.
        """
        if not self.api_key:
            return None
        
        ticker = ticker.upper().strip()
        headers = {
            'Content-Type': 'application/json',
            'Authorization': f'Token {self.api_key}'
        }
        url = f"{self.BASE_URL}/quotes/{ticker}"
        
        try:
            response = requests.get(url, headers=headers, timeout=10)
            response.raise_for_status()
            
            data = response.json()
            if not data or not isinstance(data, list) or len(data) == 0:
                logger.debug(f"No quote data from Tiingo for {ticker}")
                return None
            
            quote_data = data[0]
            
            # Map Tiingo's structure to standardized format
            price = quote_data.get('last')
            if price is None:
                logger.debug(f"No price in Tiingo response for {ticker}")
                return None
            
            return {
                'price': float(price),
                'bid': float(quote_data.get('bidPrice', price * 0.9999)),
                'ask': float(quote_data.get('askPrice', price * 1.0001)),
                'volume': int(quote_data.get('volume', 0)),
                'timestamp': quote_data.get('quoteTimestamp', datetime.utcnow().isoformat()),
                'source': 'Tiingo'
            }
            
        except requests.exceptions.HTTPError as e:
            if e.response.status_code == 404:
                logger.debug(f"Ticker {ticker} not found in Tiingo")
                return None
            elif e.response.status_code == 429:
                logger.warning(f"Tiingo rate limit exceeded for {ticker}")
                raise ValueError(f"RATE_LIMIT_429: Tiingo rate limit exceeded")
            else:
                logger.error(f"Tiingo HTTP error for {ticker}: {e}")
                return None
        except requests.exceptions.RequestException as e:
            logger.error(f"Tiingo API error for {ticker}: {e}")
            return None
        except Exception as e:
            logger.error(f"Unexpected error in Tiingo adapter for {ticker}: {e}")
            return None
    
    def get_historical_bars(self, ticker: str, interval: str = "1day", period: str = "1mo") -> Optional[list]:
        """
        Get historical bars from Tiingo.
        MVP: Return None for now, forcing fallback to yfinance for historical data.
        """
        # TODO: Implement Tiingo historical data endpoint
        # For MVP, we'll rely on yfinance for historical data
        return None
    
    # Compatibility methods to match existing MarketData protocol
    def last_quote(self, ticker: str) -> dict:
        """Compatibility method - calls get_real_time_quote"""
        quote = self.get_real_time_quote(ticker)
        if quote is None:
            raise ValueError(f"Could not fetch quote for {ticker} from Tiingo")
        return quote
    
    def daily_ohlc(self, ticker: str, lookback: int = 60) -> list:
        """Compatibility method - returns empty for MVP"""
        # MVP: Historical data falls back to yfinance
        return []
    
    def spread_proxy(self, ticker: str) -> float:
        """Calculate spread proxy from bid/ask"""
        quote = self.get_real_time_quote(ticker)
        if quote and 'bid' in quote and 'ask' in quote:
            return max(0.02, abs(quote['ask'] - quote['bid']))
        return 0.02  # Default spread

