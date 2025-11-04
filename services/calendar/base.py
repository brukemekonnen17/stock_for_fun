"""
Base interface for earnings calendar providers
"""
from typing import Protocol, Optional, List
from datetime import datetime
from dataclasses import dataclass

@dataclass
class EarningsEvent:
    """Earnings event data structure"""
    ticker: str
    event_type: str  # "EARNINGS", "DIVIDEND", etc.
    event_time: datetime
    source: str  # Provider name
    confidence: float = 1.0  # 0.0-1.0, how confident we are in this date
    headline: str = ""
    url: str = ""

class EarningsCalendarAdapter(Protocol):
    """Protocol for earnings calendar data providers"""
    
    def get_next_earnings(self, ticker: str) -> Optional[EarningsEvent]:
        """
        Get the next earnings date for a ticker.
        Returns None if not found or unavailable.
        """
        ...
    
    def get_upcoming_earnings(self, tickers: List[str], days_ahead: int = 30) -> List[EarningsEvent]:
        """
        Get upcoming earnings for multiple tickers within days_ahead.
        Returns list of events sorted by event_time.
        """
        ...

