import yfinance as yf
from datetime import datetime, timedelta
import logging
import pandas as pd
import time
from functools import lru_cache

logger = logging.getLogger(__name__)

# Simple cache with TTL (5 minutes)
_price_cache = {}
_cache_ttl = 300  # 5 minutes

class YFMarketData:
    """
    Yahoo Finance market data adapter.
    Implements MarketDataProvider protocol for fallback service compatibility.
    """
    
    def get_real_time_quote(self, ticker: str):
        """Get real-time quote - compatibility method for MarketDataProvider protocol"""
        return self.last_quote(ticker)
    
    def get_historical_bars(self, ticker: str, interval: str = "1day", period: str = "1mo"):
        """Get historical bars - compatibility method"""
        # Map period to lookback days
        period_map = {"1d": 1, "5d": 5, "1mo": 30, "3mo": 90, "1y": 365}
        lookback = period_map.get(period, 60)
        return self.daily_ohlc(ticker, lookback=lookback)
    def last_quote(self, ticker: str) -> dict:
        """Get last quote with robust error handling, retries, and caching."""
        ticker = ticker.upper().strip()
        
        # Check cache first
        cache_key = f"quote_{ticker}"
        if cache_key in _price_cache:
            cached_data, cached_time = _price_cache[cache_key]
            if time.time() - cached_time < _cache_ttl:
                logger.info(f"Using cached price for {ticker}")
                return cached_data
        
        # Retry logic with exponential backoff
        max_retries = 3
        for attempt in range(max_retries):
            try:
                t = yf.Ticker(ticker)
                
                # Try fast_info first (fastest)
                price = None
                try:
                    info = t.fast_info
                    price = getattr(info, 'last_price', None)
                    if price is None:
                        # Try regular_price or previous_close as fallback
                        price = getattr(info, 'regular_market_price', None) or \
                                getattr(info, 'previous_close', None)
                except (AttributeError, KeyError) as e:
                    logger.warning(f"fast_info failed for {ticker} (attempt {attempt+1}): {e}")
                    price = None
                
                # Fallback to history if fast_info doesn't work
                if price is None:
                    try:
                        # Try multiple periods
                        for period in ["5d", "1mo", "3mo"]:
                            try:
                                hist = t.history(period=period, interval="1d")
                                if not hist.empty:
                                    price = float(hist['Close'].iloc[-1])
                                    logger.info(f"Got price for {ticker} from {period} history")
                                    break
                            except:
                                continue
                    except Exception as e:
                        logger.warning(f"history fallback failed for {ticker}: {e}")
                
                # Last resort: use info dict
                if price is None:
                    try:
                        info_dict = t.info
                        price = info_dict.get('currentPrice') or \
                                info_dict.get('regularMarketPrice') or \
                                info_dict.get('previousClose')
                    except Exception as e:
                        logger.warning(f"info dict fallback failed for {ticker}: {e}")
                
                # Absolute last resort: try to get ANY historical close (even if old)
                if price is None:
                    try:
                        # Try longer historical periods
                        for period in ["1y", "2y", "5y"]:
                            try:
                                hist = t.history(period=period, interval="1d")
                                if not hist.empty:
                                    # Use most recent close, even if it's days/weeks old
                                    price = float(hist['Close'].iloc[-1])
                                    logger.warning(f"Using stale historical price for {ticker} from {period} (last close: {hist.index[-1]})")
                                    break
                            except:
                                continue
                    except Exception as e:
                        logger.warning(f"Historical fallback failed for {ticker}: {e}")
                
                if price is None:
                    raise ValueError(f"Could not fetch price for {ticker} after all attempts. Yahoo Finance may be blocking requests or the ticker may be invalid.")
                
                price = float(price)
                
                # Get bid/ask (approximate)
                bid = price * 0.9999  # Default: slightly below price
                ask = price * 1.0001  # Default: slightly above price
                
                try:
                    info = t.fast_info
                    last_daily = getattr(info, 'last_daily', None)
                    if last_daily:
                        bid = price - abs(float(price - float(last_daily)) * 0.5)
                        ask = price + abs(float(price - float(last_daily)) * 0.5)
                except:
                    pass
                
                result = {
                    "price": price,
                    "bid": bid,
                    "ask": ask,
                    "timestamp": datetime.utcnow().isoformat(),
                }
                
                # Cache the result
                _price_cache[cache_key] = (result, time.time())
                
                return result
                
            except Exception as e:
                error_msg = str(e)
                logger.warning(f"Attempt {attempt+1}/{max_retries} failed for {ticker}: {error_msg[:200]}")
                
                # Check if it's a rate limit error (check error message or response)
                is_rate_limit = (
                    "429" in error_msg or 
                    "Too Many Requests" in error_msg or 
                    "Rate limit" in error_msg.lower() or
                    "rate limit" in error_msg.lower() or
                    "Client Error: Too Many Requests" in error_msg
                )
                
                if is_rate_limit:
                    if attempt < max_retries - 1:
                        wait_time = (2 ** attempt) * 3  # Longer backoff: 3s, 6s, 12s
                        logger.info(f"Rate limited for {ticker}. Waiting {wait_time}s before retry {attempt+2}/{max_retries}...")
                        time.sleep(wait_time)
                        continue
                    else:
                        # Last attempt failed due to rate limit - make it very clear
                        raise ValueError(f"RATE_LIMIT_429: Rate limit exceeded for {ticker} after {max_retries} attempts. Yahoo Finance is temporarily blocking requests. Please wait 5-10 minutes and try again, or use IEX Cloud (IEX_CLOUD_API_KEY) for more reliable data.")
                
                # For other errors, if it's the last attempt, raise the error
                if attempt == max_retries - 1:
                    # Include rate limit info if present - check more thoroughly
                    if "429" in error_msg or "Too Many Requests" in error_msg or "rate limit" in error_msg.lower():
                        raise ValueError(f"RATE_LIMIT_429: Could not fetch price for {ticker}. Yahoo Finance rate limit exceeded. Please wait 5-10 minutes and try again, or use IEX Cloud (IEX_CLOUD_API_KEY) for more reliable data.")
                    # Check if it's a general connection/data issue (blocking)
                    if "Expecting value" in error_msg or "JSON" in error_msg or "possibly delisted" in error_msg.lower():
                        # If we've seen 429 errors in the logs, it's likely rate limiting
                        raise ValueError(f"RATE_LIMIT_429: Could not fetch price for {ticker}. Yahoo Finance may be blocking requests (likely rate limiting). Try waiting 5-10 minutes or use IEX Cloud (IEX_CLOUD_API_KEY).")
                    raise ValueError(f"Could not fetch price for {ticker} after {max_retries} attempts. Error: {error_msg[:200]}")
        
        # Should never reach here, but just in case
        raise ValueError(f"Could not fetch price for {ticker}. Ticker may be invalid or delisted.")

    def daily_ohlc(self, ticker: str, lookback: int = 60):
        """Get daily OHLC data with error handling."""
        try:
            t = yf.Ticker(ticker)
            df = t.history(period=f"{lookback}d", interval="1d")
            
            if df.empty:
                logger.warning(f"No historical data for {ticker}")
                return []
            
            out = []
            for idx, row in df.iterrows():
                out.append({
                    "date": idx.to_pydatetime().date().isoformat(),
                    "open": float(row["Open"]),
                    "high": float(row["High"]),
                    "low": float(row["Low"]),
                    "close": float(row["Close"]),
                    "adj_close": float(row.get("Adj Close", row["Close"])),  # Split-adjusted close
                    "volume": int(row["Volume"]) if not pd.isna(row["Volume"]) else 0,
                })
            return out
        except Exception as e:
            logger.error(f"Error fetching daily OHLC for {ticker}: {e}")
            raise ValueError(f"Failed to fetch historical data for {ticker}: {str(e)}")

    def spread_proxy(self, ticker: str) -> float:
        """Calculate spread proxy with error handling."""
        try:
            # Try intraday data first
            df = yf.download(ticker, period="1d", interval="1m", progress=False)
            if not df.empty:
                last = df.iloc[-1]
                price = float(last["Close"])
                return max(0.02, price * 0.0005)
        except Exception as e:
            logger.warning(f"Intraday spread calc failed for {ticker}: {e}")
        
        # Fallback: use daily data
        try:
            t = yf.Ticker(ticker)
            hist = t.history(period="5d", interval="1d")
            if not hist.empty:
                price = float(hist["Close"].iloc[-1])
                return max(0.02, price * 0.0005)
        except Exception as e:
            logger.warning(f"Daily spread calc failed for {ticker}: {e}")
        
        # Last resort: default spread
        return 0.02

