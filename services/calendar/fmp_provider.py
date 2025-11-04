"""
Financial Modeling Prep (FMP) earnings calendar provider
Free tier: 250 calls/day
Premium: Various tiers available
Sign up: https://site.financialmodelingprep.com/developer/docs/
"""
import logging
import requests
import os
from datetime import datetime, timedelta
from typing import Optional

from services.calendar.base import EarningsCalendarAdapter, EarningsEvent

logger = logging.getLogger(__name__)

class FMPEarningsProvider(EarningsCalendarAdapter):
    """Financial Modeling Prep earnings calendar provider"""
    
    def __init__(self, api_key: str = None):
        self.api_key = api_key or os.getenv("FMP_API_KEY")
        if not self.api_key:
            raise ValueError(
                "FMP_API_KEY required. "
                "Get free key: https://site.financialmodelingprep.com/developer/docs/"
            )
        self.base_url = "https://financialmodelingprep.com/api/v3"
        self.name = "fmp"
    
    def _get(self, endpoint: str, params: dict = None) -> list:
        """Make API call to FMP"""
        url = f"{self.base_url}/{endpoint}"
        all_params = {
            "apikey": self.api_key,
            **(params or {})
        }
        
        try:
            response = requests.get(url, params=all_params, timeout=10)
            response.raise_for_status()
            data = response.json()
            
            # FMP returns errors as dict with "Error Message"
            if isinstance(data, dict) and "Error Message" in data:
                raise ValueError(f"FMP error: {data['Error Message']}")
            
            return data if isinstance(data, list) else []
        except requests.exceptions.RequestException as e:
            logger.error(f"FMP request error: {e}")
            raise ValueError(f"FMP API error: {e}")
    
    def get_next_earnings(self, ticker: str) -> Optional[EarningsEvent]:
        """Get next earnings date from FMP"""
        ticker = ticker.upper().strip()
        
        try:
            # FMP earnings calendar endpoint
            data = self._get(f"earnings_calendar", {
                "from": datetime.now().strftime("%Y-%m-%d"),
                "to": (datetime.now() + timedelta(days=90)).strftime("%Y-%m-%d")
            })
            
            # Find earnings for this ticker
            for item in data:
                if item.get("symbol", "").upper() == ticker:
                    date_str = item.get("date") or item.get("earningDate")
                    if date_str:
                        try:
                            earnings_date = datetime.strptime(date_str.split("T")[0], "%Y-%m-%d")
                            if earnings_date >= datetime.now():
                                return EarningsEvent(
                                    ticker=ticker,
                                    event_type="EARNINGS",
                                    event_time=earnings_date,
                                    source=self.name,
                                    confidence=0.95,  # FMP is reliable
                                    headline=item.get("name", f"{ticker} Earnings Report"),
                                    url=f"https://site.financialmodelingprep.com/stock/{ticker}"
                                )
                        except (ValueError, TypeError) as e:
                            logger.debug(f"Could not parse earnings date: {date_str}")
                            continue
            
        except Exception as e:
            logger.debug(f"FMP earnings fetch failed for {ticker}: {e}")
        
        return None
    
    def get_upcoming_earnings(self, tickers: list, days_ahead: int = 30) -> list:
        """Get upcoming earnings for multiple tickers"""
        events = []
        cutoff_date = datetime.now() + timedelta(days=days_ahead)
        
        try:
            # Fetch calendar for date range
            data = self._get("earnings_calendar", {
                "from": datetime.now().strftime("%Y-%m-%d"),
                "to": cutoff_date.strftime("%Y-%m-%d")
            })
            
            # Filter by requested tickers
            ticker_set = {t.upper() for t in tickers}
            for item in data:
                symbol = item.get("symbol", "").upper()
                if symbol in ticker_set:
                    date_str = item.get("date") or item.get("earningDate")
                    if date_str:
                        try:
                            earnings_date = datetime.strptime(date_str.split("T")[0], "%Y-%m-%d")
                            if datetime.now() <= earnings_date <= cutoff_date:
                                events.append(EarningsEvent(
                                    ticker=symbol,
                                    event_type="EARNINGS",
                                    event_time=earnings_date,
                                    source=self.name,
                                    confidence=0.95,
                                    headline=item.get("name", f"{symbol} Earnings Report"),
                                    url=f"https://site.financialmodelingprep.com/stock/{symbol}"
                                ))
                        except (ValueError, TypeError):
                            continue
            
        except Exception as e:
            logger.warning(f"FMP bulk fetch failed: {e}")
            # Fallback to individual fetches
            for ticker in tickers:
                event = self.get_next_earnings(ticker)
                if event:
                    days_to_event = (event.event_time - datetime.now()).days
                    if 0 <= days_to_event <= days_ahead:
                        events.append(event)
        
        return sorted(events, key=lambda e: e.event_time)

