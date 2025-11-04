"""
Market data adapter with automatic fallback handling
"""
import logging
from typing import Protocol, List, Dict

logger = logging.getLogger(__name__)

class MarketDataWithFallback:
    """
    Wrapper that automatically falls back to secondary adapter on rate limit errors
    """
    def __init__(self, primary, fallback):
        self.primary = primary
        self.fallback = fallback
        self._rate_limited = False
    
    def _is_rate_limit_error(self, error: Exception) -> bool:
        """Check if error is a rate limit error"""
        error_msg = str(error).lower()
        rate_limit_indicators = [
            "rate limit",
            "rate_limit",
            "429",
            "25 requests",
            "too many requests",
            "quota exceeded",
            "daily limit"
        ]
        return any(indicator in error_msg for indicator in rate_limit_indicators)
    
    def _try_with_fallback(self, method_name: str, *args, **kwargs):
        """Try primary adapter, fallback on rate limit"""
        # Try primary first (unless we know it's rate limited)
        if not self._rate_limited:
            try:
                method = getattr(self.primary, method_name)
                return method(*args, **kwargs)
            except Exception as e:
                if self._is_rate_limit_error(e):
                    logger.warning(f"Rate limit detected on {method_name}, switching to fallback adapter")
                    self._rate_limited = True
                    # Fall through to fallback
                else:
                    # Non-rate-limit error, re-raise
                    raise
        
        # Use fallback
        try:
            method = getattr(self.fallback, method_name)
            result = method(*args, **kwargs)
            logger.debug(f"Using fallback adapter for {method_name}")
            return result
        except Exception as e:
            # If fallback also fails, provide helpful error
            if self._is_rate_limit_error(e):
                logger.error(f"Both primary and fallback hit rate limits")
            raise ValueError(f"Both market data adapters failed. Primary error: rate limited. Fallback error: {e}")
    
    def last_quote(self, ticker: str) -> dict:
        """Get last quote with automatic fallback"""
        return self._try_with_fallback("last_quote", ticker)
    
    def daily_ohlc(self, ticker: str, lookback: int = 60) -> List[dict]:
        """Get daily OHLC with automatic fallback"""
        return self._try_with_fallback("daily_ohlc", ticker, lookback)
    
    def spread_proxy(self, ticker: str) -> float:
        """Get spread proxy with automatic fallback"""
        return self._try_with_fallback("spread_proxy", ticker)
    
    def reset_rate_limit(self):
        """Reset rate limit flag (e.g., after 24 hours)"""
        self._rate_limited = False
        logger.info("Rate limit flag reset - will try primary adapter again")

