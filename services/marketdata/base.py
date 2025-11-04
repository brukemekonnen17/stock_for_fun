from typing import Protocol, List, Dict, Optional, Any
from datetime import datetime, timedelta

class MarketData(Protocol):
    """Original protocol for backward compatibility"""
    def last_quote(self, ticker: str) -> dict: ...
    def daily_ohlc(self, ticker: str, lookback: int = 60) -> List[dict]: ...
    def spread_proxy(self, ticker: str) -> float: ...

class MarketDataProvider(Protocol):
    """
    Enhanced protocol for market data providers with explicit real-time quote method.
    All providers must implement this interface for the fallback service.
    """
    def get_real_time_quote(self, ticker: str) -> Optional[Dict[str, Any]]:
        """
        Fetches the latest snapshot quote (price, bid/ask, volume).
        Returns a dictionary or None if the ticker is not found.
        """
        ...
    
    def get_historical_bars(self, ticker: str, interval: str, period: str) -> Optional[Any]:
        """
        Fetches historical data bars (OHLCV).
        For MVP, we may only need this for volatility and liquidity checks.
        """
        ...

