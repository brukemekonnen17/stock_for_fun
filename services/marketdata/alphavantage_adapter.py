"""
Alpha Vantage Market Data Adapter

IEX Cloud shut down on August 31, 2024. Alpha Vantage is an active alternative.
Free tier: 5 calls/min, 500 calls/day
Premium: $29.99/month - 30 calls/min, 1200 calls/day

Sign up: https://www.alphavantage.co/support/#api-key
Docs: https://www.alphavantage.co/documentation/
"""
import requests
from datetime import datetime, timedelta
from typing import List, Dict, Optional
import logging
import os
import time

logger = logging.getLogger(__name__)

class AlphaVantageAdapter:
    """Alpha Vantage market data adapter - active alternative to IEX Cloud"""
    
    def __init__(self, api_key: str = None):
        self.api_key = api_key or os.getenv("ALPHA_VANTAGE_API_KEY")
        if not self.api_key:
            raise ValueError(
                "ALPHA_VANTAGE_API_KEY environment variable required. "
                "Get your free key at https://www.alphavantage.co/support/#api-key"
            )
        self.base_url = "https://www.alphavantage.co/query"
        self.timeout = 10
        # Rate limiting: Detect premium vs free tier
        # Free tier: 5 calls/min (12s between calls)
        # Premium tier: 30 calls/min (2s between calls)
        # We'll detect based on API response and adjust
        self._last_call_time = 0
        self._min_call_interval = 2  # Start with premium tier (2s), adjust if we get rate limit errors
        self._is_premium = None  # Will be detected from API responses
    
    def _get(self, params: Dict) -> Dict:
        """Make API call with rate limiting"""
        # Rate limiting for free tier (5 calls/min)
        elapsed = time.time() - self._last_call_time
        if elapsed < self._min_call_interval:
            wait_time = self._min_call_interval - elapsed
            logger.info(f"Rate limiting: waiting {wait_time:.1f}s...")
            time.sleep(wait_time)
        
        all_params = {
            "apikey": self.api_key,
            **params
        }
        
        try:
            response = requests.get(self.base_url, params=all_params, timeout=self.timeout)
            response.raise_for_status()
            data = response.json()
            
            # Check for API errors
            if "Error Message" in data:
                raise ValueError(f"Alpha Vantage API error: {data['Error Message']}")
            if "Note" in data:
                raise ValueError(f"RATE_LIMIT_429: Alpha Vantage rate limit: {data['Note']}")
            if "Information" in data:
                # This usually means rate limit or subscription required
                info = data["Information"]
                if "rate limit" in info.lower() or "25 requests" in info.lower():
                    # Free tier limit - adjust rate limiting
                    self._min_call_interval = 12
                    self._is_premium = False
                    raise ValueError(f"RATE_LIMIT_429: Alpha Vantage free tier limit: 25 requests/day. {info}")
                elif "1200" in info.lower() or "premium" in info.lower():
                    # Premium tier limit
                    self._is_premium = True
                    raise ValueError(f"RATE_LIMIT_429: Alpha Vantage premium tier limit: 1200 requests/day. {info}")
                raise ValueError(f"Alpha Vantage info: {info}")
            
            # Success - if we got here with premium interval, assume premium
            if self._is_premium is None and self._min_call_interval == 2:
                self._is_premium = True
                logger.debug("Alpha Vantage premium tier detected")
            
            self._last_call_time = time.time()
            return data
        except requests.exceptions.RequestException as e:
            logger.error(f"Alpha Vantage request error: {e}")
            raise ValueError(f"Alpha Vantage API error: {e}")
    
    def last_quote(self, ticker: str) -> dict:
        """Get real-time quote for a ticker"""
        ticker = ticker.upper().strip()
        
        # Use GLOBAL_QUOTE function for latest price
        data = self._get({
            "function": "GLOBAL_QUOTE",
            "symbol": ticker
        })
        
        if "Global Quote" not in data or not data["Global Quote"]:
            # Check for error messages
            if "Error Message" in data:
                raise ValueError(f"Alpha Vantage error for {ticker}: {data['Error Message']}")
            if "Note" in data:
                raise ValueError(f"Alpha Vantage rate limit for {ticker}: {data['Note']}")
            raise ValueError(f"No quote data available for {ticker}. Ticker may be invalid or delisted.")
        
        quote = data["Global Quote"]
        price = float(quote.get("05. price", 0))
        if price == 0:
            raise ValueError(f"Invalid price data for {ticker}. Price is zero or missing.")
        
        # Calculate bid/ask from price (AV doesn't provide bid/ask in free tier)
        bid = price * 0.9999
        ask = price * 1.0001
        
        return {
            "price": price,
            "bid": bid,
            "ask": ask,
            "timestamp": datetime.utcnow().isoformat(),
        }
    
    def daily_ohlc(self, ticker: str, lookback: int = 60) -> List[dict]:
        """Get daily OHLC data"""
        ticker = ticker.upper().strip()
        
        # Use TIME_SERIES_DAILY function
        data = self._get({
            "function": "TIME_SERIES_DAILY",
            "symbol": ticker,
            "outputsize": "compact" if lookback <= 100 else "full"
        })
        
        if "Time Series (Daily)" not in data:
            raise ValueError(f"No historical data available for {ticker}")
        
        series = data["Time Series (Daily)"]
        out = []
        
        # Sort by date (most recent first)
        sorted_dates = sorted(series.keys(), reverse=True)[:lookback]
        
        for date_str in sorted_dates:
            day_data = series[date_str]
            out.append({
                "date": date_str,
                "open": float(day_data["1. open"]),
                "high": float(day_data["2. high"]),
                "low": float(day_data["3. low"]),
                "close": float(day_data["4. close"]),
                "volume": int(float(day_data["5. volume"])),
            })
        
        return out
    
    def spread_proxy(self, ticker: str) -> float:
        """Get spread proxy (estimate based on price)"""
        try:
            quote = self.last_quote(ticker)
            price = quote["price"]
            # Estimate spread as 0.05% of price
            return max(0.02, price * 0.0005)
        except Exception as e:
            logger.warning(f"Could not get spread for {ticker}, using default: {e}")
            return 0.02

