"""
Earnings calendar service with database caching and provider fallback
"""
import logging
from datetime import datetime, timedelta
from typing import Optional, List
from sqlalchemy.orm import Session
from sqlalchemy import and_

from db.models import Event
from services.calendar.base import EarningsCalendarAdapter, EarningsEvent

logger = logging.getLogger(__name__)

class EarningsCalendarService:
    """
    Earnings calendar service with:
    1. Database caching (Event model)
    2. Multiple provider fallback
    3. Cache expiration (refresh stale data)
    """
    
    def __init__(self, providers: List[EarningsCalendarAdapter], db: Session = None):
        """
        Initialize with ordered list of providers (tried in order).
        First provider is primary, others are fallbacks.
        """
        self.providers = providers
        self.db = db
        self.cache_ttl_hours = 24  # Cache events for 24 hours
    
    def get_next_earnings(self, ticker: str, db: Session = None) -> Optional[EarningsEvent]:
        """
        Get next earnings date for a ticker.
        Checks cache first, then tries providers.
        """
        db = db or self.db
        ticker = ticker.upper().strip()
        now = datetime.utcnow()
        
        # 1. Check database cache first
        if db:
            cached = db.query(Event).filter(
                and_(
                    Event.ticker == ticker,
                    Event.event_type == "EARNINGS",
                    Event.event_time >= now  # Only future events
                )
            ).order_by(Event.event_time.asc()).first()
            
            if cached:
                # Check if cache is still fresh
                cache_age = now - cached.created_at
                if cache_age < timedelta(hours=self.cache_ttl_hours):
                    logger.debug(f"Using cached earnings for {ticker}: {cached.event_time}")
                    return EarningsEvent(
                        ticker=cached.ticker,
                        event_type=cached.event_type,
                        event_time=cached.event_time,
                        source=cached.source,
                        confidence=cached.confidence,
                        headline=cached.headline,
                        url=cached.url
                    )
                else:
                    logger.debug(f"Cache expired for {ticker}, refreshing...")
        
        # 2. Try providers in order
        for provider in self.providers:
            try:
                event = provider.get_next_earnings(ticker)
                if event:
                    # Save to database
                    if db:
                        self._save_event(event, db)
                    return event
            except Exception as e:
                logger.warning(f"Provider {provider.__class__.__name__} failed for {ticker}: {e}")
                continue
        
        logger.warning(f"No earnings date found for {ticker} from any provider")
        return None
    
    def get_upcoming_earnings(self, tickers: List[str], days_ahead: int = 30, db: Session = None) -> List[EarningsEvent]:
        """
        Get upcoming earnings for multiple tickers.
        Uses cache when available, fetches from providers when needed.
        """
        events = []
        for ticker in tickers:
            event = self.get_next_earnings(ticker, db)
            if event:
                days_to_event = (event.event_time - datetime.utcnow()).days
                if 0 <= days_to_event <= days_ahead:
                    events.append(event)
        
        # Sort by event_time
        events.sort(key=lambda e: e.event_time)
        return events
    
    def _save_event(self, event: EarningsEvent, db: Session):
        """Save or update event in database"""
        try:
            # Check if event already exists
            existing = db.query(Event).filter(
                and_(
                    Event.ticker == event.ticker,
                    Event.event_type == event.event_type,
                    Event.event_time == event.event_time
                )
            ).first()
            
            if existing:
                # Update existing
                existing.source = event.source
                existing.confidence = event.confidence
                existing.headline = event.headline
                existing.url = event.url
                existing.created_at = datetime.utcnow()
            else:
                # Create new
                new_event = Event(
                    ticker=event.ticker,
                    event_type=event.event_type,
                    event_time=event.event_time,
                    source=event.source,
                    confidence=event.confidence,
                    headline=event.headline,
                    url=event.url
                )
                db.add(new_event)
            
            db.commit()
            logger.debug(f"Saved earnings event to DB: {event.ticker} @ {event.event_time}")
        except Exception as e:
            logger.error(f"Failed to save event to DB: {e}")
            db.rollback()

