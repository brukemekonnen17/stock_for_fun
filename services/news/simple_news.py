"""
Simple news aggregator - can be enhanced with real APIs later
For now, provides contextual news summaries for stocks
"""
import logging
from typing import Dict
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)

# Mock news data - in production, replace with real news API (NewsAPI, Alpha Vantage, etc.)
NEWS_DATABASE = {
    "AAPL": [
        {"headline": "Q1 Earnings Beat Expectations", "date": datetime.utcnow() - timedelta(days=2), "sentiment": "positive"},
        {"headline": "Strong iPhone Sales in China", "date": datetime.utcnow() - timedelta(days=1), "sentiment": "positive"},
        {"headline": "Services Revenue Up 15% YoY", "date": datetime.utcnow() - timedelta(days=3), "sentiment": "positive"},
    ],
    "TSLA": [
        {"headline": "Elon Announces New Model", "date": datetime.utcnow() - timedelta(days=1), "sentiment": "positive"},
        {"headline": "Production Delays Reported", "date": datetime.utcnow() - timedelta(days=4), "sentiment": "negative"},
    ],
    "NVDA": [
        {"headline": "AI Chip Demand Surges", "date": datetime.utcnow() - timedelta(days=1), "sentiment": "positive"},
        {"headline": "Data Center Revenue Up 200%", "date": datetime.utcnow() - timedelta(days=2), "sentiment": "positive"},
    ],
}

def get_recent_news(ticker: str, days: int = 7) -> list:
    """Get recent news for a ticker"""
    news = NEWS_DATABASE.get(ticker, [])
    cutoff = datetime.utcnow() - timedelta(days=days)
    return [n for n in news if n["date"] >= cutoff]

def get_news_summary(ticker: str) -> str:
    """Get a summary of recent news"""
    news = get_recent_news(ticker, days=7)
    if not news:
        return f"Limited recent news for {ticker}. Market conditions appear stable."
    
    positive = sum(1 for n in news if n["sentiment"] == "positive")
    negative = sum(1 for n in news if n["sentiment"] == "negative")
    
    if positive > negative:
        summary = f"Positive sentiment: {positive} positive news items in past week. "
    elif negative > positive:
        summary = f"Mixed sentiment: {negative} concerns noted. "
    else:
        summary = "Neutral news flow. "
    
    summary += "Recent headlines: " + "; ".join([n["headline"] for n in news[:3]])
    return summary

