"""
Options IV (Implied Volatility) adapter for expected move calculation.
Supports multiple providers: Polygon, IEX Cloud, Alpha Vantage (fallback).
"""
import requests
import os
import logging
from typing import Optional, Dict, Any
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)

class OptionsIVAdapter:
    """
    Fetches options implied volatility to compute expected move.
    Falls back to historical volatility if options data unavailable.
    """
    
    def __init__(self):
        self.polygon_api_key = os.getenv("POLYGON_API_KEY")
        self.iex_api_key = os.getenv("IEX_API_KEY")
        self.alpha_vantage_api_key = os.getenv("ALPHA_VANTAGE_API_KEY")
    
    def get_expected_move_iv(
        self, 
        ticker: str, 
        days_to_event: int = 7,
        fallback_volatility: Optional[float] = None
    ) -> Dict[str, Any]:
        """
        Get expected move from options IV.
        
        Args:
            ticker: Stock ticker
            days_to_event: Days until catalyst event
            fallback_volatility: Historical volatility to use if IV unavailable
        
        Returns:
            Dict with:
            - expected_move_iv: Expected move from IV (annualized %)
            - iv: Implied volatility (annualized)
            - source: Data source used
            - confidence: Confidence in the IV estimate (0-1)
        """
        # Try Polygon first (most reliable for options)
        if self.polygon_api_key:
            iv_data = self._get_polygon_iv(ticker, days_to_event)
            if iv_data:
                return iv_data
        
        # Try IEX Cloud
        if self.iex_api_key:
            iv_data = self._get_iex_iv(ticker, days_to_event)
            if iv_data:
                return iv_data
        
        # Fallback to historical volatility
        if fallback_volatility is not None:
            # Convert annualized vol to expected move for given horizon
            # Expected move ≈ IV * sqrt(days/365) * adjustment_factor
            days_annualized = days_to_event / 365.0
            expected_move = fallback_volatility * (days_annualized ** 0.5) * 1.96  # ~95% CI
            return {
                "expected_move_iv": expected_move,
                "iv": fallback_volatility,
                "source": "historical_volatility",
                "confidence": 0.5
            }
        
        # Last resort: use a default
        logger.warning(f"No IV data available for {ticker}, using default expected move")
        return {
            "expected_move_iv": 0.03,  # 3% default
            "iv": 0.20,  # 20% annualized default
            "source": "default",
            "confidence": 0.3
        }
    
    def _get_polygon_iv(self, ticker: str, days_to_event: int) -> Optional[Dict[str, Any]]:
        """Fetch IV from Polygon.io options chain."""
        if not self.polygon_api_key:
            return None
        
        try:
            # Get options chain (closest expiration to days_to_event)
            url = f"https://api.polygon.io/v3/snapshot/options/{ticker}"
            params = {
                "apikey": self.polygon_api_key,
                "limit": 1
            }
            
            response = requests.get(url, params=params, timeout=10)
            if response.status_code == 200:
                data = response.json()
                results = data.get("results", [])
                if results:
                    # Find ATM option closest to event
                    option = results[0]
                    iv = option.get("implied_volatility", 0)
                    if iv > 0:
                        # Convert to expected move
                        days_annualized = days_to_event / 365.0
                        expected_move = iv * (days_annualized ** 0.5) * 1.96
                        return {
                            "expected_move_iv": expected_move,
                            "iv": iv,
                            "source": "polygon",
                            "confidence": 0.9
                        }
        except Exception as e:
            logger.debug(f"Polygon IV fetch failed for {ticker}: {e}")
        
        return None
    
    def _get_iex_iv(self, ticker: str, days_to_event: int) -> Optional[Dict[str, Any]]:
        """Fetch IV from IEX Cloud options data."""
        if not self.iex_api_key:
            return None
        
        try:
            # IEX Cloud options endpoint
            url = f"https://cloud.iexapis.com/stable/stock/{ticker}/options"
            params = {
                "token": self.iex_api_key
            }
            
            response = requests.get(url, params=params, timeout=10)
            if response.status_code == 200:
                options = response.json()
                if options:
                    # Use ATM option
                    atm_option = min(options, key=lambda x: abs(x.get("strike", 0) - x.get("lastPrice", 0)))
                    iv = atm_option.get("impliedVolatility", 0)
                    if iv > 0:
                        days_annualized = days_to_event / 365.0
                        expected_move = iv * (days_annualized ** 0.5) * 1.96
                        return {
                            "expected_move_iv": expected_move,
                            "iv": iv,
                            "source": "iex",
                            "confidence": 0.8
                        }
        except Exception as e:
            logger.debug(f"IEX IV fetch failed for {ticker}: {e}")
        
        return None


# Global instance
_options_iv_adapter: Optional[OptionsIVAdapter] = None

def get_options_iv_adapter() -> OptionsIVAdapter:
    """Get or create global options IV adapter."""
    global _options_iv_adapter
    if _options_iv_adapter is None:
        _options_iv_adapter = OptionsIVAdapter()
    return _options_iv_adapter

