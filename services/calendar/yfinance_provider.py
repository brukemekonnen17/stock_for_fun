"""
Yahoo Finance earnings calendar provider
Uses yfinance library (free, but rate-limited and unofficial)
"""
import logging
from datetime import datetime
from typing import Optional
import yfinance as yf

from services.calendar.base import EarningsCalendarAdapter, EarningsEvent

logger = logging.getLogger(__name__)

class YFinanceEarningsProvider(EarningsCalendarAdapter):
    """Yahoo Finance earnings provider (free, but unreliable)"""
    
    def __init__(self):
        self.name = "yfinance"
    
    def get_next_earnings(self, ticker: str) -> Optional[EarningsEvent]:
        """Get next earnings date from yfinance"""
        ticker = ticker.upper().strip()
        
        try:
            stock = yf.Ticker(ticker)
            
            # Try calendar first
            try:
                calendar = stock.calendar
                if calendar is not None and len(calendar) > 0:
                    if hasattr(calendar, 'Earnings Date'):
                        earnings_date = calendar['Earnings Date'].iloc[0] if len(calendar) > 0 else None
                    elif hasattr(calendar, 'iloc'):
                        earnings_date = calendar.iloc[0].get('Earnings Date') if len(calendar) > 0 else None
                    else:
                        earnings_date = None
                    
                    if earnings_date:
                        # Parse date
                        if isinstance(earnings_date, str):
                            try:
                                from dateutil import parser as date_parser
                                earnings_date = date_parser.parse(earnings_date)
                            except ImportError:
                                # Basic parsing
                                try:
                                    earnings_date = datetime.strptime(earnings_date, "%Y-%m-%d")
                                except:
                                    try:
                                        earnings_date = datetime.strptime(earnings_date, "%Y-%m-%d %H:%M:%S")
                                    except:
                                        logger.warning(f"Could not parse earnings date: {earnings_date}")
                                        earnings_date = None
                        elif hasattr(earnings_date, 'to_pydatetime'):
                            earnings_date = earnings_date.to_pydatetime()
                        
                        if earnings_date and earnings_date >= datetime.now():
                            return EarningsEvent(
                                ticker=ticker,
                                event_type="EARNINGS",
                                event_time=earnings_date,
                                source=self.name,
                                confidence=0.8,  # yfinance is somewhat reliable
                                headline=f"{ticker} Earnings Report",
                                url=f"https://finance.yahoo.com/quote/{ticker}"
                            )
            except Exception as e:
                logger.debug(f"yfinance calendar failed for {ticker}: {e}")
            
            # Try info dict
            try:
                info = stock.info
                if 'earningsDate' in info and info['earningsDate']:
                    earnings_dates = info['earningsDate']
                    if isinstance(earnings_dates, list) and len(earnings_dates) > 0:
                        for ed in earnings_dates:
                            if isinstance(ed, (int, float)):
                                earnings_date = datetime.fromtimestamp(ed)
                            elif isinstance(ed, str):
                                try:
                                    from dateutil import parser as date_parser
                                    earnings_date = date_parser.parse(ed)
                                except ImportError:
                                    try:
                                        earnings_date = datetime.strptime(ed, "%Y-%m-%d")
                                    except:
                                        continue
                            else:
                                continue
                            
                            if earnings_date and earnings_date >= datetime.now():
                                return EarningsEvent(
                                    ticker=ticker,
                                    event_type="EARNINGS",
                                    event_time=earnings_date,
                                    source=self.name,
                                    confidence=0.8,
                                    headline=f"{ticker} Earnings Report",
                                    url=f"https://finance.yahoo.com/quote/{ticker}"
                                )
            except Exception as e:
                logger.debug(f"yfinance info earningsDate failed for {ticker}: {e}")
                
        except Exception as e:
            logger.debug(f"yfinance earnings fetch failed for {ticker}: {e}")
        
        return None
    
    def get_upcoming_earnings(self, tickers: list, days_ahead: int = 30) -> list:
        """Get upcoming earnings for multiple tickers"""
        events = []
        for ticker in tickers:
            event = self.get_next_earnings(ticker)
            if event:
                days_to_event = (event.event_time - datetime.now()).days
                if 0 <= days_to_event <= days_ahead:
                    events.append(event)
        return sorted(events, key=lambda e: e.event_time)

