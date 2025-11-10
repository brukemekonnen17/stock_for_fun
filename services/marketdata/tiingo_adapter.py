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
from typing import Optional, Dict, Any, List
from datetime import datetime, timedelta

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
        Get historical bars - compatibility method that delegates to daily_ohlc.
        """
        # Map period to lookback days
        period_map = {"1d": 1, "5d": 5, "1mo": 30, "3mo": 90, "1y": 365}
        lookback = period_map.get(period, 60)
        return self.daily_ohlc(ticker, lookback=lookback)
    
    # Compatibility methods to match existing MarketData protocol
    def last_quote(self, ticker: str) -> dict:
        """Compatibility method - calls get_real_time_quote"""
        quote = self.get_real_time_quote(ticker)
        if quote is None:
            raise ValueError(f"Could not fetch quote for {ticker} from Tiingo")
        return quote
    
    def daily_ohlc(self, ticker: str, lookback: int = 60) -> List[dict]:
        """
        Get daily OHLC data from Tiingo EOD API with split-adjusted prices.
        
        Args:
            ticker: Stock symbol
            lookback: Number of calendar days to look back (Tiingo will return trading days)
        
        Returns:
            List of dicts with date, open, high, low, close, adj_close, volume
        """
        if not self.api_key:
            logger.debug("Tiingo API key not configured, skipping")
            return []
        
        ticker = ticker.upper().strip()
        
        # Calculate date range (lookback days from today)
        end_date = datetime.now()
        start_date = end_date - timedelta(days=lookback)
        
        headers = {
            'Content-Type': 'application/json',
            'Authorization': f'Token {self.api_key}'
        }
        
        # Tiingo EOD API endpoint
        url = f"{self.BASE_URL}/daily/{ticker}/prices"
        params = {
            'startDate': start_date.strftime('%Y-%m-%d'),
            'endDate': end_date.strftime('%Y-%m-%d')
        }
        
        try:
            logger.debug(f"Fetching Tiingo EOD data for {ticker} from {start_date.date()} to {end_date.date()}")
            response = requests.get(url, headers=headers, params=params, timeout=15)
            response.raise_for_status()
            
            data = response.json()
            
            if not data or not isinstance(data, list):
                logger.warning(f"No historical data from Tiingo for {ticker}")
                return []
            
            # Transform Tiingo format to our standard format
            out = []
            for bar in data:
                # Extract date (Tiingo returns ISO format like "2024-11-10T00:00:00.000Z")
                date_str = bar.get('date', '')
                if date_str:
                    # Convert to simple date format (YYYY-MM-DD)
                    date_obj = datetime.fromisoformat(date_str.replace('Z', '+00:00'))
                    date_simple = date_obj.strftime('%Y-%m-%d')
                else:
                    logger.warning(f"Missing date in Tiingo response for {ticker}")
                    continue
                
                # Tiingo provides split-adjusted data in adjClose, adjOpen, adjHigh, adjLow
                # We use adjClose for consistency with other providers
                out.append({
                    'date': date_simple,
                    'open': float(bar.get('open', 0)),
                    'high': float(bar.get('high', 0)),
                    'low': float(bar.get('low', 0)),
                    'close': float(bar.get('close', 0)),
                    'adj_close': float(bar.get('adjClose', bar.get('close', 0))),  # Split-adjusted
                    'volume': int(bar.get('volume', 0))
                })
            
            logger.info(f"✅ Tiingo returned {len(out)} bars for {ticker}")
            return out
            
        except requests.exceptions.HTTPError as e:
            if e.response.status_code == 404:
                logger.warning(f"Ticker {ticker} not found in Tiingo EOD data")
                return []
            elif e.response.status_code == 429:
                logger.warning(f"Tiingo rate limit exceeded for {ticker}")
                raise ValueError(f"RATE_LIMIT_429: Tiingo rate limit exceeded (50/day on free tier)")
            else:
                logger.error(f"Tiingo HTTP error for {ticker}: {e}")
                return []
        except requests.exceptions.RequestException as e:
            logger.error(f"Tiingo API request error for {ticker}: {e}")
            return []
        except Exception as e:
            logger.error(f"Unexpected error fetching Tiingo data for {ticker}: {e}")
            return []
    
    def spread_proxy(self, ticker: str) -> float:
        """Calculate spread proxy from bid/ask"""
        quote = self.get_real_time_quote(ticker)
        if quote and 'bid' in quote and 'ask' in quote:
            return max(0.02, abs(quote['ask'] - quote['bid']))
        return 0.02  # Default spread

