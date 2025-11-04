"""
IEX Cloud Market Data Adapter

Free tier: 50,000 messages/month
Paid: $9/month for 1M messages/month

Sign up: https://iexcloud.io
Docs: https://iexcloud.io/docs/
"""
import requests
from datetime import datetime
from typing import List, Dict
import logging
import os

logger = logging.getLogger(__name__)

class IEXCloudAdapter:
    """IEX Cloud market data adapter - reliable, paid alternative to Yahoo Finance"""
    
    def __init__(self, api_key: str = None):
        self.api_key = api_key or os.getenv("IEX_CLOUD_API_KEY")
        if not self.api_key:
            # Allow initialization without key for graceful fallback
            logger.warning("IEX_CLOUD_API_KEY not set - adapter will fail on requests. Use YFMarketData instead.")
        self.base_url = "https://cloud.iexapis.com/stable" if self.api_key else "https://sandbox.iexapis.com/stable"
        self.timeout = 10
    
    def last_quote(self, ticker: str) -> dict:
        """Get real-time quote from IEX Cloud"""
        ticker = ticker.upper().strip()
        
        url = f"{self.base_url}/stock/{ticker}/quote"
        params = {"token": self.api_key}
        
        try:
            response = requests.get(url, params=params, timeout=self.timeout)
            response.raise_for_status()
            data = response.json()
            
            # IEX Cloud provides real bid/ask prices
            bid = data.get("iexBidPrice") or data.get("latestPrice", 0)
            ask = data.get("iexAskPrice") or data.get("latestPrice", 0)
            
            return {
                "price": float(data["latestPrice"]),
                "bid": float(bid),
                "ask": float(ask),
                "timestamp": datetime.utcnow().isoformat(),
            }
        except requests.exceptions.RequestException as e:
            logger.error(f"IEX Cloud API error for {ticker}: {e}")
            raise ValueError(f"Failed to fetch quote for {ticker} from IEX Cloud: {str(e)}")
    
    def daily_ohlc(self, ticker: str, lookback: int = 60) -> List[Dict]:
        """Get historical OHLC data"""
        ticker = ticker.upper().strip()
        
        # IEX Cloud supports up to 5 years of data
        # Format: 1d, 5d, 1m, 3m, 6m, 1y, 2y, 5y
        period_map = {
            5: "5d",
            30: "1m",
            60: "2m",
            90: "3m",
            180: "6m",
            365: "1y",
            730: "2y",
            1825: "5y"
        }
        
        # Find appropriate period
        period = "1m"  # Default
        for days, p in period_map.items():
            if lookback <= days:
                period = p
                break
        
        url = f"{self.base_url}/stock/{ticker}/chart/{period}"
        params = {"token": self.api_key}
        
        try:
            response = requests.get(url, params=params, timeout=self.timeout)
            response.raise_for_status()
            data = response.json()
            
            # Limit to requested lookback
            results = []
            for item in data[-lookback:]:
                results.append({
                    "date": item["date"],
                    "open": float(item["open"]),
                    "high": float(item["high"]),
                    "low": float(item["low"]),
                    "close": float(item["close"]),
                    "volume": int(item.get("volume", 0)),
                })
            
            return results
        except requests.exceptions.RequestException as e:
            logger.error(f"IEX Cloud historical data error for {ticker}: {e}")
            raise ValueError(f"Failed to fetch historical data for {ticker}: {str(e)}")
    
    def spread_proxy(self, ticker: str) -> float:
        """Get actual spread from IEX Cloud (real bid/ask)"""
        try:
            quote = self.last_quote(ticker)
            spread = quote["ask"] - quote["bid"]
            # Return actual spread, minimum 1 cent
            return max(0.01, spread)
        except Exception as e:
            logger.warning(f"Spread calculation failed for {ticker}, using default: {e}")
            # Fallback: estimate 0.1% spread
            try:
                quote = self.last_quote(ticker)
                return max(0.01, quote["price"] * 0.001)
            except:
                return 0.02  # Default 2 cents

