"""
Market Data Provider Service with intelligent fallback chain
Orchestrates multiple providers (Tiingo -> yfinance) for reliable data access
"""
import logging
from typing import Optional, Dict, Any, List
from datetime import datetime

logger = logging.getLogger(__name__)

class MarketDataProviderService:
    """
    Primary service for market data, implementing a reliable provider fallback chain.
    
    Strategy:
    1. Try Tiingo (production-grade, reliable)
    2. Fallback to yfinance (free but unreliable)
    3. Log source for monitoring and debugging
    """
    
    def __init__(self):
        """Initialize service with provider chain"""
        from .tiingo_adapter import TiingoAdapter
        from .yf_adapter import YFMarketData
        
        # Order matters: Tiingo (primary) -> YFinance (fallback)
        self.providers = []
        
        # Add Tiingo if configured
        try:
            tiingo = TiingoAdapter()
            if tiingo.api_key:
                self.providers.append(tiingo)
                logger.info("✅ Tiingo market data provider enabled")
            else:
                logger.info("⚠️ Tiingo provider disabled (no API key)")
        except Exception as e:
            logger.warning(f"Failed to initialize Tiingo adapter: {e}")
        
        # Always add yfinance as fallback
        try:
            yf = YFMarketData()
            self.providers.append(yf)
            logger.info("✅ yfinance market data provider enabled (fallback)")
        except Exception as e:
            logger.error(f"Failed to initialize yfinance adapter: {e}")
            # This is critical - if yfinance fails, we have no fallback
        
        if not self.providers:
            logger.error("CRITICAL: No market data providers available!")
    
    def get_real_time_quote(self, ticker: str) -> Optional[Dict[str, Any]]:
        """
        Get real-time quote by trying providers in order.
        Returns the first successful quote with source information.
        """
        ticker = ticker.upper().strip()
        
        for provider in self.providers:
            # Skip providers that aren't configured
            if hasattr(provider, 'api_key') and getattr(provider, 'api_key') is None:
                logger.debug(f"Skipping {provider.__class__.__name__} (not configured)")
                continue
            
            try:
                # Try to get quote using protocol method
                if hasattr(provider, 'get_real_time_quote'):
                    quote = provider.get_real_time_quote(ticker)
                elif hasattr(provider, 'last_quote'):
                    # Fallback to compatibility method
                    quote = provider.last_quote(ticker)
                    # Ensure source is set
                    if isinstance(quote, dict) and 'source' not in quote:
                        quote['source'] = provider.__class__.__name__
                else:
                    logger.warning(f"Provider {provider.__class__.__name__} doesn't implement required methods")
                    continue
                
                if quote and quote.get('price') is not None:
                    source = quote.get('source', provider.__class__.__name__)
                    logger.info(f"Quote for {ticker} successfully fetched from {source}")
                    return quote
                else:
                    logger.debug(f"{provider.__class__.__name__} returned no data for {ticker}")
                    
            except ValueError as e:
                error_msg = str(e)
                # Check if it's a rate limit error
                if "RATE_LIMIT" in error_msg or "429" in error_msg:
                    logger.warning(f"Rate limit on {provider.__class__.__name__} for {ticker}, trying next provider")
                    continue
                # Re-raise non-rate-limit errors after all providers exhausted
                if provider == self.providers[-1]:
                    raise
                logger.debug(f"{provider.__class__.__name__} failed for {ticker}: {e}")
                continue
            except Exception as e:
                logger.warning(f"{provider.__class__.__name__} error for {ticker}: {e}")
                # Continue to next provider
                if provider == self.providers[-1]:
                    # Last provider failed
                    logger.error(f"CRITICAL: Failed to get real-time quote for {ticker} from all providers")
                    raise ValueError(f"All market data providers failed for {ticker}. Last error: {e}")
                continue
        
        # Should never reach here, but just in case
        logger.error(f"CRITICAL: Failed to get real-time quote for {ticker} from all providers (no exceptions raised)")
        return None
    
    # Compatibility methods for existing code
    def last_quote(self, ticker: str) -> dict:
        """Compatibility method - calls get_real_time_quote"""
        quote = self.get_real_time_quote(ticker)
        if quote is None:
            raise ValueError(f"Could not fetch quote for {ticker} from any provider")
        return quote
    
    def daily_ohlc(self, ticker: str, lookback: int = 60) -> List[dict]:
        """Get daily OHLC - delegates to yfinance (fallback) for historical data"""
        # For MVP, use yfinance for historical data (Tiingo historical not implemented yet)
        for provider in self.providers:
            if hasattr(provider, 'daily_ohlc'):
                try:
                    result = provider.daily_ohlc(ticker, lookback)
                    if result:
                        return result
                except Exception as e:
                    logger.debug(f"{provider.__class__.__name__} daily_ohlc failed: {e}")
                    continue
        
        logger.warning(f"No historical data available for {ticker}")
        return []
    
    def spread_proxy(self, ticker: str) -> float:
        """Get spread proxy - tries providers in order"""
        for provider in self.providers:
            if hasattr(provider, 'spread_proxy'):
                try:
                    spread = provider.spread_proxy(ticker)
                    if spread and spread > 0:
                        return spread
                except Exception as e:
                    logger.debug(f"{provider.__class__.__name__} spread_proxy failed: {e}")
                    continue
        
        # Default spread
        return 0.02

