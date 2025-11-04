"""
Alpha Vantage earnings calendar provider
Free tier: 5 calls/min, 500 calls/day
Premium: 30 calls/min, 1200 calls/day
"""
import logging
import requests
import os
from datetime import datetime
from typing import Optional
import time

from services.calendar.base import EarningsCalendarAdapter, EarningsEvent

logger = logging.getLogger(__name__)

class AlphaVantageEarningsProvider(EarningsCalendarAdapter):
    """Alpha Vantage earnings calendar provider"""
    
    def __init__(self, api_key: str = None):
        self.api_key = api_key or os.getenv("ALPHA_VANTAGE_API_KEY")
        if not self.api_key:
            raise ValueError(
                "ALPHA_VANTAGE_API_KEY required. "
                "Get free key: https://www.alphavantage.co/support/#api-key"
            )
        self.base_url = "https://www.alphavantage.co/query"
        self.name = "alphavantage"
        self._last_call_time = 0
        self._min_call_interval = 12  # Free tier: 5 calls/min = 12s between calls
    
    def _get(self, params: dict) -> dict:
        """Make API call with rate limiting"""
        elapsed = time.time() - self._last_call_time
        if elapsed < self._min_call_interval:
            wait_time = self._min_call_interval - elapsed
            logger.debug(f"Rate limiting: waiting {wait_time:.1f}s...")
            time.sleep(wait_time)
        
        all_params = {
            "apikey": self.api_key,
            **params
        }
        
        try:
            response = requests.get(self.base_url, params=all_params, timeout=10)
            response.raise_for_status()
            data = response.json()
            
            if "Error Message" in data:
                raise ValueError(f"Alpha Vantage error: {data['Error Message']}")
            if "Note" in data:
                raise ValueError(f"RATE_LIMIT_429: {data['Note']}")
            if "Information" in data:
                info = data["Information"]
                if "rate limit" in info.lower() or "25 requests" in info.lower():
                    raise ValueError(f"RATE_LIMIT_429: Alpha Vantage free tier limit: {info}")
            
            self._last_call_time = time.time()
            return data
        except requests.exceptions.RequestException as e:
            logger.error(f"Alpha Vantage request error: {e}")
            raise ValueError(f"Alpha Vantage API error: {e}")
    
    def get_next_earnings(self, ticker: str) -> Optional[EarningsEvent]:
        """Get next earnings date from Alpha Vantage"""
        ticker = ticker.upper().strip()
        
        try:
            # Alpha Vantage doesn't have a dedicated earnings calendar endpoint
            # But we can use the EARNINGS_CALENDAR function (if available)
            # Note: This may not be available in free tier
            data = self._get({
                "function": "EARNINGS_CALENDAR",
                "symbol": ticker,
                "horizon": "3month"
            })
            
            # Parse response (format varies by API version)
            if "earningsCalendar" in data:
                calendar = data["earningsCalendar"]
                if isinstance(calendar, list) and len(calendar) > 0:
                    # Get first future earnings date
                    for item in calendar:
                        if "reportDate" in item or "date" in item:
                            date_str = item.get("reportDate") or item.get("date")
                            try:
                                earnings_date = datetime.strptime(date_str, "%Y-%m-%d")
                                if earnings_date >= datetime.now():
                                    return EarningsEvent(
                                        ticker=ticker,
                                        event_type="EARNINGS",
                                        event_time=earnings_date,
                                        source=self.name,
                                        confidence=0.95,  # Alpha Vantage is reliable
                                        headline=f"{ticker} Earnings Report",
                                        url=f"https://www.alphavantage.co/query?function=EARNINGS_CALENDAR&symbol={ticker}"
                                    )
                            except (ValueError, TypeError) as e:
                                logger.debug(f"Could not parse earnings date: {date_str}")
                                continue
            
            # Fallback: Try to get from company overview (if available)
            # Note: This is a workaround - Alpha Vantage may not have earnings calendar in free tier
            logger.debug(f"Alpha Vantage earnings calendar not available for {ticker} (may require premium)")
            
        except ValueError as e:
            if "RATE_LIMIT" in str(e):
                raise  # Re-raise rate limit errors
            logger.debug(f"Alpha Vantage earnings fetch failed for {ticker}: {e}")
        except Exception as e:
            logger.debug(f"Alpha Vantage unexpected error for {ticker}: {e}")
        
        return None
    
    def get_upcoming_earnings(self, tickers: list, days_ahead: int = 30) -> list:
        """Get upcoming earnings for multiple tickers"""
        events = []
        for ticker in tickers:
            try:
                event = self.get_next_earnings(ticker)
                if event:
                    days_to_event = (event.event_time - datetime.now()).days
                    if 0 <= days_to_event <= days_ahead:
                        events.append(event)
            except ValueError as e:
                if "RATE_LIMIT" in str(e):
                    logger.warning(f"Rate limit reached, stopping earnings fetch")
                    break
                continue
        return sorted(events, key=lambda e: e.event_time)

