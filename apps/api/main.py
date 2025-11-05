"""
FastAPI Backend - Catalyst Scanner API
Complete trading system with bandit learning, policy validation, and E*TRADE integration
"""
from fastapi import FastAPI, Depends, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field
from datetime import datetime, timedelta
from typing import List, Optional
from sqlalchemy.orm import Session

from db.session import get_db, engine
from db.models import Base, BanditLog, RewardLog, Event
from services.policy.validators import (
    MarketSnapshot, TradePlan, PolicyContext, validate
)
from services.llm.client import propose_trade, propose_trade_v2
from apps.api.schemas_llm import parse_llm_json, TradeAnalysisV2
from services.llm.prompt_builder import build_messages
from services.llm.validator import enforce_policy_and_sanity
from pathlib import Path
from libs.analytics.bandit import ContextualTS, Arm
from libs.analytics.persistence import BanditStatePersistence
from services.scanner.catalyst_scanner import CatalystScanner
from services.broker.etrade_client import ETradeClient, ETradeConfig
from services.broker.base import OrderRequest
from services.broker.etrade_oauth import request_token as et_request_token, exchange_token as et_exchange_token
from apps.api.schemas import WhySelected, CatalystInfo, StrategyRationale, MarketContext, PerfStats, NewsItem
from apps.api.schemas_base import StrictModel
from services.analysis.explain import (
    catalyst_from_payload,
    compute_market_context,
    recent_news,
    build_perf_stats,
    brief_reason_for_arm,
    gating_facts,
    set_market_data_adapter
)
from services.analysis.events import get_event_details

import numpy as np
import logging
import atexit
import os
import json
from time import time
from dotenv import load_dotenv

# Load .env
project_dir = os.path.join(os.path.dirname(__file__), '..', '..')
dotenv_path = os.path.join(project_dir, '.env')
if os.path.exists(dotenv_path):
    load_dotenv(dotenv_path=dotenv_path)

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

app = FastAPI(title="Catalyst Scanner API", version="0.2.0")

# Include calibration router
from apps.api.calibration_endpoints import router as calibration_router
app.include_router(calibration_router)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize tables
Base.metadata.create_all(bind=engine)

# Bandit registry
_bandits: dict[int, ContextualTS] = {}
_default_arms = [
    Arm("EARNINGS_PRE"),
    Arm("POST_EVENT_MOMO"),
    Arm("NEWS_SPIKE"),
    Arm("REACTIVE"),
    Arm("SKIP"),
]
_persistence = BanditStatePersistence()

def get_bandit(d: int) -> ContextualTS:
    if d not in _bandits:
        _bandits[d] = ContextualTS(d=d, arms=_default_arms, alpha=1.0)
        _persistence.load(_bandits[d], bandit_id=f"d{d}")
    return _bandits[d]

def _save_all_bandits():
    logger.info("Saving all bandit states...")
    for d, bandit in _bandits.items():
        _persistence.save(bandit, bandit_id=f"d{d}")
    logger.info("All bandit states saved")

atexit.register(_save_all_bandits)

def _to_np(x: List[float]):
    return np.array(x, dtype=float)

# Market data
from services.marketdata.service import MarketDataProviderService
from services.marketdata.yf_adapter import YFMarketData
from services.marketdata.alphavantage_adapter import AlphaVantageAdapter
from services.marketdata.fallback_adapter import MarketDataWithFallback

market_data_service = MarketDataProviderService()

_primary_market_data = None
_fallback_market_data = None

try:
    if os.getenv("ALPHA_VANTAGE_API_KEY"):
        logger.info("Using Alpha Vantage for market data")
        _primary_market_data = AlphaVantageAdapter()
        _fallback_market_data = YFMarketData()
        logger.info("Yahoo Finance fallback ready")
    else:
        logger.info("Using Yahoo Finance for market data")
        _primary_market_data = YFMarketData()
        _fallback_market_data = YFMarketData()
except Exception as e:
    logger.warning(f"Failed to initialize Alpha Vantage, using Yahoo Finance: {e}")
    _primary_market_data = YFMarketData()
    _fallback_market_data = YFMarketData()

market_data = MarketDataWithFallback(_primary_market_data, _fallback_market_data)
scanner = CatalystScanner(md=market_data_service)
set_market_data_adapter(market_data)

# Calendar service
from services.calendar.service import EarningsCalendarService
from services.calendar.yfinance_provider import YFinanceEarningsProvider
from services.calendar.alphavantage_provider import AlphaVantageEarningsProvider
from services.calendar.fmp_provider import FMPEarningsProvider
from services.analysis.events import set_calendar_service

calendar_providers = []
try:
    if os.getenv("FMP_API_KEY"):
        calendar_providers.append(FMPEarningsProvider())
        logger.info("✅ FMP earnings calendar enabled")
except Exception as e:
    logger.debug(f"FMP provider not available: {e}")

try:
    if os.getenv("ALPHA_VANTAGE_API_KEY"):
        calendar_providers.append(AlphaVantageEarningsProvider())
        logger.info("✅ Alpha Vantage earnings calendar enabled")
except Exception as e:
    logger.debug(f"Alpha Vantage earnings provider not available: {e}")

try:
    calendar_providers.append(YFinanceEarningsProvider())
    logger.info("✅ yfinance earnings calendar enabled (fallback)")
except Exception as e:
    logger.warning(f"yfinance earnings provider failed: {e}")

if calendar_providers:
    calendar_service = EarningsCalendarService(calendar_providers)
    set_calendar_service(calendar_service)
    logger.info(f"✅ Earnings calendar service initialized with {len(calendar_providers)} provider(s)")
else:
    logger.warning("⚠️ No earnings calendar providers available")
    calendar_service = None

UNIVERSE = ["AAPL", "TSLA", "NVDA", "MSFT", "AMZN", "GOOGL", "META", "AMD", "NFLX", "DIS"]

def _etrade_from_env() -> ETradeClient:
    cfg = ETradeConfig(
        consumer_key=os.getenv("ETRADE_CONSUMER_KEY", ""),
        consumer_secret=os.getenv("ETRADE_CONSUMER_SECRET", ""),
        access_token=os.getenv("ETRADE_ACCESS_TOKEN", ""),
        access_token_secret=os.getenv("ETRADE_ACCESS_TOKEN_SECRET", ""),
        account_id_key=os.getenv("ETRADE_ACCOUNT_ID_KEY", ""),
        sandbox=os.getenv("ETRADE_SANDBOX", "true").lower() == "true",
    )
    return ETradeClient(cfg)

# Pydantic Models
class ProposePayload(StrictModel):
    ticker: str
    price: float
    event_type: str
    days_to_event: float
    rank_components: dict
    expected_move: float
    backtest_kpis: dict
    liquidity: float
    spread: float
    news_summary: str = ""
    volume_surge_ratio: float = 1.0
    recent_high: float = 0.0
    recent_low: float = 0.0
    price_position: float = 0.5
    rolling_volatility_10d: float = 0.0
    breakout_flag: bool = False
    adv_change: float = 0.0
    context: List[float] = Field(default_factory=list)
    decision_id: str

class ProposeResponse(StrictModel):
    selected_arm: str
    plan: dict
    decision_id: str
    analysis: dict | None = None
    schema_version: str = Field(default="ProposeResponseV1", alias="schema")
    model_config = {"populate_by_name": True}

class ValidatePayload(StrictModel):
    plan: TradePlan
    market: MarketSnapshot
    context: PolicyContext
    decision_id: str

class RewardPayload(StrictModel):
    arm_name: str
    context: List[float]
    reward: float
    decision_id: str
    meta: dict = Field(default_factory=dict)

class ExecutePayload(StrictModel):
    ticker: str
    shares: int
    limit_price: float

# Dashboard
@app.get("/", response_class=FileResponse)
def root():
    return FileResponse("/Users/brukemekonnen/stock_investment/trading_dashboard.html")

@app.get("/dashboard", response_class=FileResponse)
def dashboard():
    return FileResponse("/Users/brukemekonnen/stock_investment/trading_dashboard.html")

# Health
@app.get("/health")
def health():
    return {"status": "ok", "time": datetime.utcnow().isoformat()}

@app.get("/events/upcoming")
def upcoming(days: int = 14, db: Session = Depends(get_db)):
    if calendar_service:
        try:
            events = calendar_service.get_upcoming_earnings(UNIVERSE, days_ahead=days, db=db)
            return [
                {
                    "ticker": e.ticker,
                    "event_type": e.event_type,
                    "event_time": e.event_time.isoformat(),
                    "headline": e.headline or f"{e.ticker} {e.event_type}",
                    "source": e.source,
                    "confidence": e.confidence,
                    "url": e.url
                }
                for e in events
            ]
        except Exception as e:
            logger.error(f"Failed to get upcoming events: {e}")
    
    try:
        now = datetime.utcnow()
        cutoff = now + timedelta(days=days)
        db_events = db.query(Event).filter(
            Event.event_time >= now,
            Event.event_time <= cutoff
        ).order_by(Event.event_time.asc()).limit(50).all()
        
        if db_events:
            return [
                {
                    "ticker": e.ticker,
                    "event_type": e.event_type,
                    "event_time": e.event_time.isoformat(),
                    "headline": e.headline or f"{e.ticker} {e.event_type}",
                    "source": e.source,
                    "confidence": e.confidence,
                    "url": e.url
                }
                for e in db_events
            ]
    except Exception as e:
        logger.error(f"Database query failed: {e}")
    
    logger.warning("No earnings events available")
    return []

@app.get("/scan")
def scan(min_rank: int = 70, limit: int = 10):
    try:
        items = scanner.scan(UNIVERSE)
        items = [i for i in items if i.rank >= min_rank][:limit]
        
        now = datetime.utcnow()
        return [
            {
                "symbol": i.ticker,
                "catalyst": f"{i.event_type} event in {(i.event_time - now).days} days. Expected move: {i.expected_move*100:.1f}%",
                "confidence": min(0.99, i.rank / 100.0),
                "timestamp": i.event_time.isoformat(),
                "context": {
                    "event_type": i.event_type,
                    "rank": i.rank,
                    "expected_move": i.expected_move,
                    "liquidity": i.liquidity,
                    "spread": i.spread
                }
            }
            for i in items
        ]
    except Exception as e:
        logger.error(f"Scanner failed: {e}")
        now = datetime.utcnow()
        return [
            {
                "symbol": "AAPL",
                "catalyst": "Q1 earnings expected",
                "confidence": 0.85,
                "timestamp": (now + timedelta(days=7)).isoformat(),
                "context": {
                    "event_type": "EARNINGS",
                    "rank": 82.3,
                    "expected_move": 0.04,
                    "liquidity": 5_000_000_000,
                    "spread": 0.01
                }
            }
        ]

@app.get("/quick/{ticker}")
async def quick_analysis(ticker: str):
    ticker = ticker.upper().strip()
    
    try:
        quote = market_data.last_quote(ticker)
        price = quote["price"]
        
        text = f"""
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
📊 QUICK ANALYSIS: {ticker}
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

💰 Current Price: ${price:.2f}

📈 Quick Stats:
• Price: ${price:.2f}
• Last Updated: {quote.get('timestamp', 'N/A')}

💡 Recommendation: 
Quick analysis complete. For full analysis, 
use /analyze/{ticker}

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
"""
        return {"ticker": ticker, "price": price, "analysis": text.strip()}
    except Exception as e:
        return {
            "ticker": ticker, 
            "error": str(e),
            "analysis": f"❌ Could not fetch data for {ticker}: {str(e)}"
        }

@app.get("/history/{ticker}")
def get_price_history(ticker: str, days: int = 30):
    """
    Get historical price data for time series visualization.
    Returns OHLC data with technical indicators.
    """
    ticker = ticker.upper().strip()
    try:
        hist = market_data.daily_ohlc(ticker, lookback=days)
        if not hist:
            return {"error": f"No historical data for {ticker}"}
        
        closes = [h["close"] for h in hist]
        highs = [h["high"] for h in hist]
        lows = [h["low"] for h in hist]
        volumes = [h["volume"] for h in hist]
        dates = [h["date"] for h in hist]
        
        # Calculate technical indicators
        # Simple Moving Averages
        sma_20 = []
        sma_50 = []
        for i in range(len(closes)):
            if i >= 19:
                sma_20.append(sum(closes[i-19:i+1]) / 20)
            else:
                sma_20.append(None)
            if i >= 49:
                sma_50.append(sum(closes[i-49:i+1]) / 50)
            else:
                sma_50.append(None)
        
        # RSI calculation
        rsi_values = []
        for i in range(len(closes)):
            if i < 14:
                rsi_values.append(None)
            else:
                gains = [max(0, closes[j] - closes[j-1]) for j in range(i-13, i+1)]
                losses = [max(0, closes[j-1] - closes[j]) for j in range(i-13, i+1)]
                avg_gain = sum(gains) / 14
                avg_loss = sum(losses) / 14
                if avg_loss == 0:
                    rsi = 100
                else:
                    rs = avg_gain / avg_loss
                    rsi = 100 - (100 / (1 + rs))
                rsi_values.append(rsi)
        
        # ATR calculation
        atr_values = []
        for i in range(len(hist)):
            if i == 0:
                atr_values.append(None)
            else:
                tr = max(highs[i] - lows[i], abs(highs[i] - closes[i-1]), abs(lows[i] - closes[i-1]))
                if i < 14:
                    atr_values.append(None)
                else:
                    recent_trs = []
                    for j in range(max(0, i-14), i+1):
                        if j > 0:
                            tr = max(highs[j] - lows[j], abs(highs[j] - closes[j-1]), abs(lows[j] - closes[j-1]))
                            recent_trs.append(tr)
                    atr_values.append(sum(recent_trs) / len(recent_trs))
        
        # Support/Resistance levels
        recent_high = max(highs[-10:])
        recent_low = min(lows[-10:])
        
        # Ensure dates are strings (not date objects) for Plotly
        date_strings = []
        for date_val in dates:
            if isinstance(date_val, str):
                date_strings.append(date_val)
            else:
                # Convert date object to string
                from datetime import date
                if isinstance(date_val, date):
                    date_strings.append(date_val.isoformat())
                else:
                    date_strings.append(str(date_val))
        
        return {
            "ticker": ticker,
            "data": [
                {
                    "date": date_strings[i],
                    "open": float(hist[i]["open"]),
                    "high": float(highs[i]),
                    "low": float(lows[i]),
                    "close": float(closes[i]),
                    "volume": int(volumes[i]),
                    "sma_20": float(sma_20[i]) if sma_20[i] is not None else None,
                    "sma_50": float(sma_50[i]) if sma_50[i] is not None else None,
                    "rsi": float(rsi_values[i]) if rsi_values[i] is not None else None,
                    "atr": float(atr_values[i]) if atr_values[i] is not None else None,
                }
                for i in range(len(hist))
            ],
            "indicators": {
                "current_rsi": float(rsi_values[-1]) if rsi_values[-1] else None,
                "current_atr": float(atr_values[-1]) if atr_values[-1] else None,
                "support": float(recent_low),
                "resistance": float(recent_high),
            }
        }
    except Exception as e:
        logger.error(f"Error fetching history for {ticker}: {e}", exc_info=True)
        return {"error": str(e)}

@app.get("/surge/{ticker}")
def analyze_surge_potential(ticker: str):
    """
    Analyze if a stock has room for price increase or intraday play potential.
    Returns surge analysis with room-to-run metrics.
    """
    ticker = ticker.upper().strip()
    logger.info(f"Analyzing surge potential for {ticker}")
    
    try:
        quote = market_data.last_quote(ticker)
        price = quote["price"]
        hist = market_data.daily_ohlc(ticker, lookback=30)
        
        if not hist:
            return {"error": f"No data available for {ticker}"}
        
        closes = [h["close"] for h in hist]
        highs = [h["high"] for h in hist]
        lows = [h["low"] for h in hist]
        volumes = [h["volume"] for h in hist]
        
        # Calculate key metrics
        recent_high = max(highs[-10:])
        recent_low = min(lows[-10:])
        price_position = (price - recent_low) / (recent_high - recent_low) if (recent_high - recent_low) > 0 else 0.5
        
        # Volume surge
        avg_vol_5d = sum(volumes[-5:]) / 5
        avg_vol_30d = sum(volumes[-30:]) / 30
        volume_surge = avg_vol_5d / avg_vol_30d if avg_vol_30d > 0 else 1.0
        
        # Calculate volatility
        returns = [(closes[i] - closes[i-1]) / closes[i-1] for i in range(1, len(closes))]
        volatility = np.std(returns) * np.sqrt(252) if returns else 0.03  # Annualized
        
        # Calculate upside potential
        resistance_distance = (recent_high - price) / price if recent_high > price else 0
        support_distance = (price - recent_low) / price if price > recent_low else 0
        
        # Intraday range potential (based on ATR)
        atr_sum = 0
        for i in range(1, min(15, len(hist))):
            tr = max(highs[i] - lows[i], abs(highs[i] - closes[i-1]), abs(lows[i] - closes[i-1]))
            atr_sum += tr
        avg_atr = atr_sum / min(14, len(hist) - 1) if len(hist) > 1 else price * 0.02
        intraday_potential = (avg_atr / price) * 100
        
        # Surge score (0-100)
        surge_score = 0
        if volume_surge > 2.0:
            surge_score += 30
        elif volume_surge > 1.5:
            surge_score += 20
        
        if price_position < 0.3:  # Near support
            surge_score += 30
        elif price_position > 0.7:  # Near resistance
            surge_score += 10
        
        if resistance_distance > 0.05:  # 5%+ room to resistance
            surge_score += 20
        
        if intraday_potential > 3:  # High intraday volatility
            surge_score += 20
        
        # Get social sentiment
        from services.social.sentiment_scanner import get_real_time_sentiment
        try:
            social = get_real_time_sentiment(ticker)
            if social.get('mention_count_total', 0) > 50 and social.get('sentiment_score', 0) > 0.5:
                surge_score += 20  # Meme/social momentum
                meme_signal = True
            else:
                meme_signal = False
        except:
            social = {}
            meme_signal = False
        
        return {
            "ticker": ticker,
            "current_price": price,
            "surge_score": min(100, surge_score),
            "room_to_run": {
                "upside_to_resistance": resistance_distance * 100,
                "downside_to_support": support_distance * 100,
                "intraday_potential_pct": intraday_potential,
                "price_position": price_position * 100,
            },
            "momentum": {
                "volume_surge": volume_surge,
                "volatility_annualized": volatility * 100,
                "atr_dollars": avg_atr,
            },
            "levels": {
                "support": recent_low,
                "resistance": recent_high,
                "recent_high": recent_high,
                "recent_low": recent_low,
            },
            "social": {
                "mention_count": social.get('mention_count_total', 0),
                "sentiment_score": social.get('sentiment_score', 0),
                "meme_signal": meme_signal,
            },
            "recommendation": "HIGH_POTENTIAL" if surge_score >= 70 else "MODERATE" if surge_score >= 50 else "LOW_POTENTIAL",
        }
    except Exception as e:
        logger.error(f"Error analyzing surge for {ticker}: {e}", exc_info=True)
        return {"error": str(e)}

@app.get("/analyze/{ticker}")
async def analyze_stock(ticker: str):
    ticker = ticker.upper().strip()
    logger.info(f"Analyzing stock: {ticker}")
    
    decision_id = f"analyze-{ticker}-{int(datetime.utcnow().timestamp())}"
    
    try:
        try:
            quote = market_data.last_quote(ticker)
            price = quote["price"]
        except ValueError as e:
            error_msg = str(e)
            logger.warning(f"Market data error for {ticker}: {error_msg}")
            
            if "429" in error_msg or "Too Many Requests" in error_msg or "rate limit" in error_msg.lower():
                detail_msg = f"⚠️ Rate limit exceeded for {ticker}. Wait 24 hours or upgrade to premium."
                raise HTTPException(status_code=429, detail=detail_msg)
            elif "Could not fetch" in error_msg or "delisted" in error_msg.lower():
                detail_msg = f"⚠️ Could not fetch market data for {ticker}. Ticker may be invalid or temporarily unavailable."
                raise HTTPException(status_code=404, detail=detail_msg)
            else:
                raise HTTPException(status_code=500, detail=f"Failed to fetch market data: {error_msg[:200]}")
        
        try:
            spread = market_data.spread_proxy(ticker)
        except Exception as e:
            logger.warning(f"Spread calc failed for {ticker}: {e}")
            spread = max(0.02, price * 0.0005)
        
        try:
            hist = market_data.daily_ohlc(ticker, lookback=30)
            if not hist:
                dollar_vol = price * 1_000_000
                expected_move = 0.03
                volume_surge_ratio, recent_high, recent_low = 1.0, price, price
                price_position, rolling_volatility_10d = 0.5, 0.03
            else:
                avg_vol_30d = sum([h["volume"] for h in hist[-30:]]) / max(1, len(hist[-30:]))
                dollar_adv_30d = avg_vol_30d * price
                
                avg_vol_5d = sum([h["volume"] for h in hist[-5:]]) / max(1, len(hist[-5:]))
                dollar_adv_5d = avg_vol_5d * price

                dollar_vol = dollar_adv_30d
                
                volume_surge_ratio = (avg_vol_5d / avg_vol_30d) if avg_vol_30d > 0 else 1.0
                adv_change = (dollar_adv_5d - dollar_adv_30d) / dollar_adv_30d if dollar_adv_30d > 0 else 0.0
                
                recent_high = max([h["high"] for h in hist[-10:]]) if len(hist) >= 10 else price
                recent_low = min([h["low"] for h in hist[-10:]]) if len(hist) >= 10 else price
                breakout_flag = price > recent_high

                price_position = (price - recent_low) / max(1e-6, (recent_high - recent_low))
                
                hist_prices_10d = [h["close"] for h in hist[-10:]]
                if len(hist_prices_10d) > 1:
                    rolling_volatility_10d = np.std(np.diff(np.log(hist_prices_10d)))
                else:
                    rolling_volatility_10d = 0.03

                closes = [h["close"] for h in hist]
                # Compute realized volatility for IV-RV gap and fallback
                if len(closes) >= 20:
                    returns = [(closes[i] - closes[i-1]) / closes[i-1] for i in range(1, len(closes))]
                    if len(returns) >= 19:
                        import statistics
                        mean_return = statistics.mean(returns[-20:])
                        variance = statistics.mean([(r - mean_return) ** 2 for r in returns[-20:]])
                        std_dev = variance ** 0.5
                        realized_volatility = abs(std_dev) * np.sqrt(252)  # Annualized
                        expected_move_heuristic = abs(2 * std_dev)
                    else:
                        realized_volatility = 0.20  # 20% default annualized
                        expected_move_heuristic = 0.03
                elif len(closes) >= 6:
                    rets = [abs((closes[i] - closes[i-1]) / closes[i-1]) for i in range(1, len(closes))]
                    expected_move_heuristic = sum(rets) / len(rets) if rets else 0.03
                    realized_volatility = expected_move_heuristic * np.sqrt(252)  # Rough annualized
                else:
                    expected_move_heuristic = 0.03
                    realized_volatility = 0.20
            
            # Try to get IV-based expected move
            from services.marketdata.options_iv_adapter import get_options_iv_adapter
            iv_adapter = get_options_iv_adapter()
            event_type, days_to_event = get_event_details(ticker, market_data, db=None)
            iv_data = iv_adapter.get_expected_move_iv(
                ticker=ticker,
                days_to_event=days_to_event,
                fallback_volatility=realized_volatility
            )
            
            # Use IV-based if available and confident, otherwise fallback
            if iv_data["confidence"] > 0.6:
                expected_move = iv_data["expected_move_iv"]
                iv = iv_data["iv"]
                expected_move_source = iv_data["source"]
            else:
                expected_move = expected_move_heuristic
                iv = realized_volatility
                expected_move_source = "historical_volatility"
            
            # Compute IV-RV gap
            from services.analysis.enhanced_features import compute_iv_rv_gap
            iv_rv_gap, iv_regime = compute_iv_rv_gap(iv, realized_volatility)
        except ValueError as e:
            logger.warning(f"Historical data fetch failed for {ticker}: {e}")
            dollar_vol = price * 1_000_000
            expected_move = 0.03
            expected_move_source = "default"
            iv = 0.20
            realized_volatility = 0.20
            iv_rv_gap = 0.0
            iv_regime = "UNKNOWN"
            volume_surge_ratio, recent_high, recent_low = 1.0, price, price
            price_position, rolling_volatility_10d = 0.5, 0.03
            adv_change = 0.0
            breakout_flag = False
            hist = []
        
        liquidity_score = 1.0 if dollar_vol > 1_000_000_000 else (0.8 if dollar_vol > 100_000_000 else 0.5)
        spread_score = 1.0 - min(1.0, spread / (price * 0.01))
        volatility_score = min(1.0, expected_move / 0.10)
        rank = 50 + (liquidity_score * 20) + (spread_score * 15) + (volatility_score * 15)
        rank = max(0.0, min(100.0, rank))
        
        # Compute enhanced features
        from services.analysis.enhanced_features import (
            compute_sector_relative_strength,
            compute_participation_quality,
            compute_distance_to_levels,
            classify_meme_diagnosis
        )
        
        # Sector relative strength
        sector_rel_strength = compute_sector_relative_strength(ticker, hist, market_data) if hist else 1.0
        
        # Participation quality
        participation_quality, participation_score = compute_participation_quality(
            volume_surge_ratio=volume_surge_ratio,
            dollar_adv=dollar_vol,
            spread=spread,
            price=price
        )
        
        # Distance to levels
        distance_levels = compute_distance_to_levels(price, recent_high, recent_low)
        
        # IV-RV gap (already computed above)
        iv_rv_gap_normalized = max(-1.0, min(1.0, iv_rv_gap / 0.20))  # Normalize to -1 to 1
        
        try:
            hist_recent = market_data.daily_ohlc(ticker, lookback=5)
            if hist_recent and len(hist_recent) >= 3:
                recent_changes = [abs((hist_recent[i]["close"] - hist_recent[i-1]["close"]) / hist_recent[i-1]["close"]) 
                                 for i in range(1, len(hist_recent))]
                avg_recent_vol = sum(recent_changes) / len(recent_changes) if recent_changes else 0.02
                immediacy = min(1.0, avg_recent_vol * 50)
            else:
                immediacy = 0.6
        except:
            immediacy = 0.6
        
        try:
            from services.analysis.explain import recent_news
            news_items = recent_news(ticker, limit=3)
            if news_items and len(news_items) > 0:
                sentiments = [item.sentiment for item in news_items if hasattr(item, 'sentiment')]
                news_score = (sum(sentiments) / len(sentiments) + 1) / 2 if sentiments else 0.5
            else:
                news_score = 0.5
        except:
            news_score = 0.5
        
        event_type, days_to_event = get_event_details(ticker, market_data, db=None)
        
        # Enhanced context vector (removed duplicate expected_move, added richer features)
        context = [
            immediacy,                      # 0: Recent volatility/immediacy
            0.6,                           # 1: Materiality (static for now)
            liquidity_score,               # 2: Liquidity score
            expected_move,                  # 3: Expected move (IV-based if available)
            news_score,                     # 4: News sentiment
            days_to_event,                  # 5: Days to event
            sector_rel_strength,            # 6: Sector relative strength (NEW)
            price_position,                 # 7: Price position 10d (NEW)
            volume_surge_ratio,             # 8: Volume surge ratio (NEW)
            participation_score,           # 9: Participation quality score (NEW)
            iv_rv_gap_normalized,           # 10: IV-RV gap normalized (NEW)
            distance_levels["distance_to_resistance"],  # 11: Distance to resistance (NEW)
        ]
        
        payload = ProposePayload(
            ticker=ticker,
            price=price,
            event_type=event_type,
            days_to_event=days_to_event,
            rank_components={
                "immediacy": immediacy,
                "materiality": 0.6,
                "liquidity": liquidity_score,
                "expected_move": expected_move,
                "news": news_score,
                "rank": rank
            },
            expected_move=expected_move,
            backtest_kpis={},
            liquidity=dollar_vol,
            spread=spread,
            news_summary="",
            volume_surge_ratio=round(volume_surge_ratio, 2),
            recent_high=round(recent_high, 2),
            recent_low=round(recent_low, 2),
            price_position=round(price_position, 2),
            rolling_volatility_10d=round(rolling_volatility_10d, 4),
            breakout_flag=breakout_flag,
            adv_change=round(adv_change, 2),
            context=context,
            decision_id=decision_id
        )
        
        response = await decision_propose(payload)
        return response
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error analyzing {ticker}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to analyze {ticker}")

@app.post("/decision/propose", response_model=ProposeResponse)
async def decision_propose(body: ProposePayload) -> ProposeResponse:
    logger.info(f"[{body.decision_id}] Propose: ticker={body.ticker}, event={body.event_type}")
    
    cat = catalyst_from_payload(body, market_data_adapter=market_data)
    mkt = compute_market_context(body.ticker, body.price, body.spread, body.liquidity)
    news_items = recent_news(body.ticker, limit=5)
    perf = build_perf_stats(body.ticker, body.event_type, body.backtest_kpis, market_data_adapter=market_data)
    
    from services.social.sentiment_scanner import get_real_time_sentiment
    try:
        social_data = get_real_time_sentiment(body.ticker)
        logger.info(f"[{body.decision_id}] Social sentiment: score={social_data.get('sentiment_score', 0):.3f}, mentions={social_data.get('mention_count_total', 0)}")
    except Exception as e:
        logger.warning(f"[{body.decision_id}] Failed to fetch social sentiment: {e}")
        social_data = {
            "ticker": body.ticker,
            "sentiment_score": 0.0,
            "mention_count_total": 0,
            "bullish_pct": 0.0,
            "source": "StockTwits",
            "timestamp": datetime.utcnow().isoformat()
        }
    
    selected_arm = "SKIP"
    if body.context:
        bandit = get_bandit(len(body.context))
        selected_arm = bandit.select(x=_to_np(body.context))
        logger.info(f"[{body.decision_id}] Bandit selected arm: {selected_arm}")
    
    rationale = StrategyRationale(
        selected_arm=selected_arm,
        reason=brief_reason_for_arm(selected_arm, cat, mkt),
        gating_facts=gating_facts(cat, mkt)
    )
    
    # Compute evidence and pattern detection FIRST (needed for Phase-1 LLM)
    from apps.api.evidence_analysis import compute_evidence_analysis, compute_technical_indicators
    from services.analysis.pattern_detection import detect_patterns
    
    evidence = {}
    pattern_info = None
    hist = None
    try:
        hist = market_data.daily_ohlc(body.ticker, lookback=30)
        if hist:
            # Detect technical patterns
            pattern_info = detect_patterns(hist, body.price)
            
            evidence = compute_evidence_analysis(
                ticker=body.ticker,
                hist=hist,
                price=body.price,
                volume_surge_ratio=body.volume_surge_ratio,
                event_type=cat.event_type,
                days_to_event=cat.days_to_event,
                backtest_data=perf.model_dump() if hasattr(perf, 'model_dump') else {}
            )
            
            # Add pattern info to evidence
            if pattern_info:
                evidence["patterns"] = pattern_info
    except Exception as e:
        logger.warning(f"[{body.decision_id}] Evidence analysis failed: {e}")
    
    # Get event-study CAR (for evidence)
    event_study_summary = {}
    event_study_car_sig = False
    try:
        from services.analysis.enhanced_features import compute_event_study
        event_study = compute_event_study(
            ticker=body.ticker,
            event_type=cat.event_type,
            hist=hist if hist else [],
            market_data_adapter=market_data,
            pre_days=5,
            post_days=5
        )
        if "car" in event_study and len(event_study["car"]) > 0:
            # Keep full CAR series for Plotly panel
            event_study_summary = {
                "car": event_study["car"],
                "supports": any(c.get("mean", 0) > 0.005 for c in event_study["car"]),
                "ticker": event_study.get("ticker", body.ticker),
                "event": event_study.get("event", cat.event_type),
                "window": event_study.get("window", {"pre": 5, "post": 5})
            }
            # Check if CAR is significant (any positive mean > 0.5%)
            event_study_car_sig = any(c.get("mean", 0) > 0.005 for c in event_study["car"])
    except Exception as e:
        logger.debug(f"[{body.decision_id}] Event study computation failed: {e}")
    
    # Build deterministic facts for Phase-1 LLM
    from services.analysis.enhanced_features import compute_participation_quality, compute_iv_rv_gap
    from services.policy.validators import SPREAD_CENTS_MAX, SPREAD_BPS_MAX
    
    participation_quality, participation_score = compute_participation_quality(
        volume_surge_ratio=body.volume_surge_ratio,
        dollar_adv=body.liquidity,
        spread=body.spread,
        price=body.price
    )
    
    # Compute IV-RV gap if available
    try:
        iv_rv_gap, iv_rv_regime = compute_iv_rv_gap(
            iv=body.expected_move / 100.0 if body.expected_move else None,
            realized_volatility=body.rolling_volatility_10d
        )
    except Exception:
        iv_rv_gap = 0.0
        iv_rv_regime = "UNKNOWN"
    
    # Compute sector relative strength
    try:
        from services.analysis.enhanced_features import compute_sector_relative_strength
        sector_rel_strength = compute_sector_relative_strength(
            ticker=body.ticker,
            hist=hist if hist else [],
            market_data_adapter=market_data
        )
    except Exception:
        sector_rel_strength = 1.0
    
    # Pattern detected (or null)
    pattern_detected_dict = None
    if pattern_info and pattern_info.get("primary_pattern"):
        primary = pattern_info["primary_pattern"]
        pattern_detected_dict = {
            "name": primary.get("name", ""),
            "confidence": primary.get("confidence", 0.0),
            "side": primary.get("type", "NEUTRAL").upper() if primary.get("type") in ("BULLISH", "BEARISH") else "NEUTRAL"
        }
    
    # Build deterministic payload for Phase-1 LLM
    payload_for_llm = {
        "price": float(body.price),
        "spread": float(body.spread),
        "policy_limits": {
            "spread_cents_max": SPREAD_CENTS_MAX,
            "spread_bps_max": SPREAD_BPS_MAX
        },
        "recent_high_10d": float(body.recent_high),
        "recent_low_10d": float(body.recent_low),
        "price_position_10d": float(body.price_position),
        "volume_surge_ratio": float(body.volume_surge_ratio),
        "expected_move_iv": float(body.expected_move / 100.0) if body.expected_move else 0.0,
        "rv_10d": float(body.rolling_volatility_10d),
        "iv_minus_rv": float(iv_rv_gap),
        "sector_relative_strength": float(sector_rel_strength),
        "pattern_detected": pattern_detected_dict,
        "participation_quality": participation_quality,
        "evidence": {
            "event_study": {
                "significant": event_study_car_sig
            }
        },
        "tick_size": 0.01  # Default tick size
    }
    
    # Load SYSTEM prompt
    try:
        prompt_path = Path(project_dir) / "PROMPTS" / "LLM_SYSTEM.md"
        if prompt_path.exists():
            system_prompt_text = prompt_path.read_text(encoding="utf-8").split("# Exemplar")[0].strip()
        else:
            logger.warning(f"[{body.decision_id}] LLM_SYSTEM.md not found, using fallback")
            system_prompt_text = "You are a professional trading analyst. Output STRICT JSON only."
    except Exception as e:
        logger.warning(f"[{body.decision_id}] Failed to load SYSTEM prompt: {e}")
        system_prompt_text = "You are a professional trading analyst. Output STRICT JSON only."
    
    # Call Phase-1 LLM
    llm_analysis_v2 = None
    llm_start_time = time()
    policy_override_applied = False
    try:
        messages = build_messages(system_prompt_text, payload_for_llm)
        raw_response = await propose_trade_v2(messages)
        
        latency_ms = (time() - llm_start_time) * 1000
        
        if raw_response:
            ta = parse_llm_json(raw_response)
            if ta:
                # Enforce policy and sanity checks
                ta_before = ta.model_dump().copy()
                ta = enforce_policy_and_sanity(ta, facts=payload_for_llm)
                ta_after = ta.model_dump()
                
                # Check if policy override changed verdicts
                if (ta_before.get("verdict_intraday") != ta_after.get("verdict_intraday") or
                    ta_before.get("verdict_swing_1to5d") != ta_after.get("verdict_swing_1to5d")):
                    policy_override_applied = True
                
                llm_analysis_v2 = ta_after
                confidence_raw = ta_after.get("confidence", 0.5)
                
                # Record telemetry
                record_llm_metric(
                    parse_ok=True,
                    latency_ms=latency_ms,
                    policy_override=policy_override_applied,
                    confidence_raw=confidence_raw
                )
                
                logger.info(f"[{body.decision_id}] Phase-1 LLM analysis parsed successfully (latency: {latency_ms:.1f}ms)")
            else:
                # Record parse failure
                record_llm_metric(
                    parse_ok=False,
                    latency_ms=latency_ms,
                    policy_override=False
                )
                logger.warning(f"[{body.decision_id}] Phase-1 LLM parse failed, using fallback")
        else:
            # Record failure
            record_llm_metric(
                parse_ok=False,
                latency_ms=latency_ms,
                policy_override=False
            )
            logger.warning(f"[{body.decision_id}] Phase-1 LLM returned empty, using fallback")
    except Exception as e:
        latency_ms = (time() - llm_start_time) * 1000
        record_llm_metric(
            parse_ok=False,
            latency_ms=latency_ms,
            policy_override=False
        )
        logger.warning(f"[{body.decision_id}] Phase-1 LLM error: {e}, using fallback")
    
    # Fallback to conservative SKIP if Phase-1 LLM failed
    if llm_analysis_v2 is None:
        llm_analysis_v2 = TradeAnalysisV2.model_validate({
            "schema": "TradeAnalysisV2",
            "verdict_intraday": "SKIP",
            "verdict_swing_1to5d": "SKIP",
            "confidence": 0.5,
            "room": {
                "intraday_room_up_pct": 0.0,
                "intraday_room_down_pct": 0.0,
                "swing_room_up_pct": 0.0,
                "swing_room_down_pct": 0.0,
                "explain": "LLM parse fail"
            },
            "pattern": {"state": "RANGE"},
            "participation": {"quality": "LOW"},
            "catalyst_alignment": {"alignment": "NEUTRAL"},
            "meme_social": {"diagnosis": "NOISE"},
            "plan": {
                "entry_type": "limit",
                "entry_price": payload_for_llm.get("price", 0),
                "stop_price": payload_for_llm.get("price", 0) * 0.99,
                "targets": [],
                "timeout_days": 1,
                "rationale": "N/A"
            },
            "risk": {"policy_pass": False, "warnings": ["LLM parse failed"]},
            "evidence": {},
            "evidence_fields": [],
            "missing_fields": ["llm_output"],
            "assumptions": {"llm_fallback": True}
        }).model_dump()
    
    llm_payload = body.model_dump().copy()
    llm_payload["market_context"] = json.dumps({
        "ticker": body.ticker,
        "price": mkt.price,
        "spread": mkt.spread,
        "dollar_adv": mkt.dollar_adv,
        "rsi14": mkt.rsi14,
        "atr14": mkt.atr14,
        "volatility": body.expected_move,
        "liquidity_score": body.rank_components.get("liquidity", 0.5),
        "immediacy": body.rank_components.get("immediacy", 0.6),
        "news_sentiment": body.rank_components.get("news", 0.5),
        "volume_surge_ratio": body.volume_surge_ratio,
        "recent_high_10d": body.recent_high,
        "recent_low_10d": body.recent_low,
        "price_position": body.price_position,
        "rolling_volatility_10d": body.rolling_volatility_10d,
    })
    llm_payload["social_sentiment"] = json.dumps(social_data)
    
    # Use Phase-1 LLM analysis if available, otherwise fall back to old LLM
    if llm_analysis_v2 and llm_analysis_v2.get("schema") == "TradeAnalysisV2":
        # Convert Phase-1 LLM output to legacy format for compatibility
        plan = llm_analysis_v2.get("plan", {})
        llm_out = {
            "ticker": body.ticker,
            "action": llm_analysis_v2.get("verdict_intraday", "SKIP"),
            "entry_type": plan.get("entry_type", "limit"),
            "entry_price": plan.get("entry_price", body.price),
            "stop_price": plan.get("stop_price", body.price * 0.98),
            "target_price": plan.get("targets", [body.price * 1.05])[0] if plan.get("targets") else body.price * 1.05,
            "timeout_days": plan.get("timeout_days", 1),
            "confidence": llm_analysis_v2.get("confidence", 0.5),
            "reason": plan.get("rationale", "Phase-1 LLM analysis")
        }
        raw_confidence = float(llm_analysis_v2.get("confidence", 0.5))
    else:
        # Fallback to old LLM
        llm_out = await propose_trade(llm_payload)
        raw_confidence = float(llm_out.get("confidence", 0.5))
    
    # Apply calibration if available
    from services.analysis.calibration import get_calibration_service
    calibration_service = get_calibration_service()
    
    # Record prediction for calibration tracking
    calibration_service.record_prediction(
        decision_id=body.decision_id,
        ticker=body.ticker,
        predicted_confidence=raw_confidence,
        arm_name=selected_arm
    )
    
    # Get calibrated confidence
    calibrated_confidence = calibration_service.calibrate_confidence(raw_confidence)
    
    # Update telemetry with calibrated confidence
    if llm_analysis_v2:
        record_llm_metric(
            parse_ok=True,
            latency_ms=0.0,  # Already recorded above
            policy_override=policy_override_applied,
            confidence_raw=raw_confidence,
            confidence_calibrated=calibrated_confidence
        )
    
    # Update LLM output with calibrated confidence
    llm_out["confidence"] = calibrated_confidence
    llm_out["raw_confidence"] = raw_confidence  # Keep original for reference
    
    # Event study summary already computed above
    
    # Get arm statistics with CI
    arm_stats_summary = {}
    try:
        from services.analysis.enhanced_features import arm_stats_with_ci
        from db.models import BanditLog
        from db.session import SessionLocal
        
        db_session = SessionLocal()
        try:
            arm_logs = db_session.query(BanditLog).filter(
                BanditLog.arm_name == selected_arm
            ).all()
            
            if arm_logs:
                rewards = [log.reward for log in arm_logs]
                arm_stats = arm_stats_with_ci(selected_arm, rewards)
                arm_stats_summary = {
                    "arm": arm_stats["arm"],
                    "samples": arm_stats["samples"],
                    "median_r_ci": [
                        arm_stats["median_r"]["ci_low"],
                        arm_stats["median_r"]["ci_high"]
                    ],
                    "median_r_point": arm_stats["median_r"]["point"],
                    "p90_r": arm_stats["p90_r"]["point"],
                    "max_dd": arm_stats["max_dd"]
                }
        finally:
            db_session.close()
    except Exception as e:
        logger.debug(f"[{body.decision_id}] Arm stats computation failed: {e}")
    
    # Get calibration metrics
    cal_metrics = calibration_service.compute_metrics()
    if "calibration" not in evidence:
        evidence["calibration"] = {}
    evidence["calibration"].update({
        "ece": cal_metrics["ece"],
        "brier": cal_metrics["brier"],
        "n_samples": cal_metrics["n_samples"],
        "raw_confidence": raw_confidence,
        "calibrated_confidence": calibrated_confidence
    })
    
    # Add event study and arm stats to evidence
    if event_study_summary:
        evidence["event_study"] = event_study_summary
    if arm_stats_summary:
        evidence["arm_stats"] = arm_stats_summary
    
    # Compute alignment verdict (single source of truth) BEFORE creating analysis_dict
    from services.analysis.enhanced_features import compute_alignment
    pattern_state = (llm_analysis_v2.get("pattern") if llm_analysis_v2 else {}).get("state") if llm_analysis_v2 else None
    if not pattern_state and pattern_info:
        # Fallback: derive from pattern_info if LLM didn't provide state
        primary_pattern = pattern_info.get("primary_pattern")
        if primary_pattern:
            pattern_type = primary_pattern.get("type", "NEUTRAL")
            if pattern_type == "BULLISH":
                pattern_state = "BREAKOUT"
            elif pattern_type == "BEARISH":
                pattern_state = "PULLBACK"
            else:
                pattern_state = "RANGE"
    participation_quality_for_alignment = (llm_analysis_v2.get("participation") if llm_analysis_v2 else {}).get("quality") if llm_analysis_v2 else participation_quality
    car_significant = event_study_summary.get("supports", False) if event_study_summary else False
    alignment = compute_alignment(pattern_state, participation_quality_for_alignment, car_significant)
    
    why = WhySelected(
        ticker=body.ticker,
        catalyst=cat,
        strategy=rationale,
        news=news_items,
        history=perf,
        market=mkt,
        llm_confidence=calibrated_confidence  # Use calibrated confidence
    )
    
    analysis_dict = why.model_dump()
    if evidence:
        analysis_dict["evidence"] = evidence
    
    # Add Phase-1 LLM analysis to evidence (for audit trail) - AFTER analysis_dict is created
    if llm_analysis_v2:
        analysis_dict["llm_v2"] = llm_analysis_v2
    
    # Add alignment verdict - AFTER analysis_dict is created
    analysis_dict["alignment"] = alignment
    
    # Add series arrays for Plotly panels (compute once server-side for performance)
    series_data = {}
    try:
        if hist and len(hist) >= 20:
            from apps.api.evidence_analysis import compute_technical_indicators
            indicators = compute_technical_indicators(hist, body.price)
            
            closes = [h["close"] for h in hist]
            opens = [h["open"] for h in hist]
            highs = [h["high"] for h in hist]
            lows = [h["low"] for h in hist]
            dates = [h.get("date", "") for h in hist] if all("date" in h for h in hist) else list(range(len(hist)))
            
            # Calculate EMAs if not already computed
            ema20_vals = []
            ema50_vals = []
            if len(closes) >= 20:
                alpha_20 = 2 / (20 + 1)
                ema20 = closes[0]
                for c in closes:
                    ema20 = alpha_20 * c + (1 - alpha_20) * ema20
                    ema20_vals.append(ema20)
            else:
                ema20_vals = [indicators.get("ema20", body.price)] * len(closes)
            
            if len(closes) >= 50:
                alpha_50 = 2 / (50 + 1)
                ema50 = closes[0]
                for c in closes:
                    ema50 = alpha_50 * c + (1 - alpha_50) * ema50
                    ema50_vals.append(ema50)
            else:
                ema50_vals = [indicators.get("ema50", body.price)] * len(closes)
            
            series_data = {
                "dates": dates[-30:] if len(dates) > 30 else dates,
                "open": opens[-30:] if len(opens) > 30 else opens,
                "high": highs[-30:] if len(highs) > 30 else highs,
                "low": lows[-30:] if len(lows) > 30 else lows,
                "close": closes[-30:] if len(closes) > 30 else closes,
                "ema20": ema20_vals[-30:] if len(ema20_vals) > 30 else ema20_vals,
                "ema50": ema50_vals[-30:] if len(ema50_vals) > 30 else ema50_vals,
                "bb_upper": [indicators.get("bb_upper", body.price * 1.02)] * (len(closes[-30:]) if len(closes) > 30 else len(closes)),
                "bb_lower": [indicators.get("bb_lower", body.price * 0.98)] * (len(closes[-30:]) if len(closes) > 30 else len(closes)),
                "recent_high_10d": body.recent_high,
                "recent_low_10d": body.recent_low
            }
    except Exception as e:
        logger.debug(f"[{body.decision_id}] Series data computation failed: {e}")
    
    # Add drivers summary (deterministic, beyond catalysts)
    drivers = {}
    try:
        from services.analysis.enhanced_features import (
            compute_participation_quality,
            compute_iv_rv_gap,
            classify_meme_diagnosis
        )
        
        participation_quality, participation_score = compute_participation_quality(
            volume_surge_ratio=body.volume_surge_ratio,
            dollar_adv=body.liquidity,
            spread=body.spread,
            price=body.price
        )
        
        # IV-RV gap (already computed above)
        iv_rv_gap_normalized = max(-1.0, min(1.0, iv_rv_gap / 0.20))
        
        # Pattern state
        pattern_state = "BREAKOUT" if body.breakout_flag else ("RANGE" if 0.2 < body.price_position < 0.8 else "PULLBACK")
        pattern_strength = "strong" if body.volume_surge_ratio >= 1.5 else ("weak" if body.volume_surge_ratio >= 1.2 else "none")
        
        # Meme risk
        social_mentions = social_data.get("mention_count_total", 0)
        social_spike_ratio = social_mentions / max(1, 50)  # Normalize to 50 mentions baseline
        meme_risk, meme_explanation = classify_meme_diagnosis(
            social_spike_ratio=social_spike_ratio,
            participation_quality=participation_quality,
            volume_surge_ratio=body.volume_surge_ratio,
            float_market_cap=None  # Could compute from dollar_adv if needed
        )
        
        drivers = {
            "pattern": f"{pattern_state.upper()} ({pattern_strength})",
            "participation": participation_quality,
            "sector_relative_strength": sector_rel_strength,
            "iv_minus_rv": iv_rv_gap_normalized,
            "meme_risk": meme_risk
        }
    except Exception as e:
        logger.debug(f"[{body.decision_id}] Drivers computation failed: {e}")
    
    # Compute NBA (Next-Best-Action) score for prioritization
    nba_score = 0.0
    try:
        # Signal buy strength (from evidence tests)
        sig_buy = 1.0 if any(t.get("decision_label") == "BUY" and t.get("p_value", 1.0) < 0.05 for t in evidence.get("tests", [])) else 0.0
        
        # Weights
        w1, w2, w3, w4, w5 = 0.3, 0.25, 0.2, 0.15, 0.1
        
        participation_score_val = participation_score if 'participation_score' in locals() else 0.5
        spread_penalty = min(1.0, body.spread / (body.price * 0.01))  # Penalty if spread > 1% of price
        meme_noise_penalty = 0.3 if meme_risk == "NOISE" else 0.0
        
        nba_score = (
            w1 * sig_buy +
            w2 * calibrated_confidence +
            w3 * participation_score_val -
            w4 * spread_penalty -
            w5 * meme_noise_penalty
        )
        nba_score = max(0.0, min(1.0, nba_score))  # Clamp to [0, 1]
    except Exception as e:
        logger.debug(f"[{body.decision_id}] NBA score computation failed: {e}")
    
    # Add series, drivers, and NBA to analysis
    if series_data:
        analysis_dict["series"] = series_data
    if drivers:
        analysis_dict["drivers"] = drivers
    analysis_dict["nba_score"] = nba_score
    analysis_dict["timestamp"] = datetime.utcnow().isoformat()
    
    return ProposeResponse(
        selected_arm=selected_arm,
        plan=llm_out,
        decision_id=body.decision_id,
        analysis=analysis_dict,
        schema_version="ProposeResponseV1"
    )

@app.post("/propose")
async def propose_alias(body: ProposePayload):
    return await decision_propose(body)

@app.post("/decision/validate")
def decision_validate(body: ValidatePayload):
    decision_id = body.decision_id
    logger.info(f"[{decision_id}] Validate: ticker={body.plan.ticker}")
    
    verdict = validate(body.plan, body.market, body.context)
    result = verdict.model_dump()
    result["decision_id"] = decision_id
    
    logger.info(f"[{decision_id}] Verdict: {verdict.verdict} - {verdict.reason}")
    
    return result

@app.post("/validate")
def validate_alias(body: ValidatePayload):
    return decision_validate(body)

@app.post("/bandit/reward")
def bandit_reward(body: RewardPayload, db: Session = Depends(get_db)):
    if not body.context:
        raise HTTPException(status_code=400, detail="context is required")

    decision_id = body.decision_id
    logger.info(f"[{decision_id}] Reward: arm={body.arm_name}, reward={body.reward:.4f}")
    
    existing = db.query(RewardLog).filter_by(decision_id=decision_id).first()
    if existing:
        logger.warning(f"[{decision_id}] Duplicate reward detected - ignoring")
        return {"status": "duplicate_ignored", "decision_id": decision_id}
    
    bandit = get_bandit(len(body.context))
    bandit.update(arm_name=body.arm_name, x=_to_np(body.context), r=body.reward)

    reward_log = RewardLog(decision_id=decision_id, arm_name=body.arm_name, reward=body.reward)
    bandit_log = BanditLog(ts=datetime.utcnow(), arm_name=body.arm_name, x_json=body.context, reward=body.reward)
    db.add(reward_log)
    db.add(bandit_log)
    db.commit()
    
    # Update calibration service with outcome
    from services.analysis.calibration import get_calibration_service
    calibration_service = get_calibration_service()
    # Determine outcome: 1 if reward > 0, 0 otherwise (or use threshold)
    outcome = 1 if body.reward > 0 else 0
    calibration_service.record_outcome(
        decision_id=decision_id,
        actual_outcome=outcome,
        reward=body.reward
    )
    
    # Auto-recalibrate if enough new data
    calibration_service.auto_recalibrate(min_samples=20)
    
    logger.info(f"[{decision_id}] Bandit updated, calibration recorded")
    return {"status": "ok", "decision_id": decision_id}

class OAuthReqBody(StrictModel):
    callback: str = "oob"

@app.post("/oauth/request_token")
def oauth_request_token(body: OAuthReqBody):
    ck = os.getenv("ETRADE_CONSUMER_KEY", "")
    cs = os.getenv("ETRADE_CONSUMER_SECRET", "")
    if not ck or not cs:
        raise HTTPException(status_code=400, detail="Set ETRADE keys in .env")
    
    logger.info("Requesting OAuth token")
    rt = et_request_token(ck, cs, callback=body.callback)
    return rt

class OAuthExBody(StrictModel):
    oauth_token: str
    oauth_token_secret: str
    verifier: str

@app.post("/oauth/exchange")
def oauth_exchange(body: OAuthExBody):
    ck = os.getenv("ETRADE_CONSUMER_KEY", "")
    cs = os.getenv("ETRADE_CONSUMER_SECRET", "")
    if not ck or not cs:
        raise HTTPException(status_code=400, detail="Set ETRADE keys in .env")
    
    logger.info("Exchanging verifier")
    out = et_exchange_token(ck, cs, body.oauth_token, body.oauth_token_secret, body.verifier)
    logger.info("✅ Access tokens obtained")
    return out

@app.get("/positions")
def get_positions():
    try:
        brk = _etrade_from_env()
        return brk.positions()
    except Exception as e:
        logger.error(f"Failed to get positions: {e}")
        return {"error": str(e), "positions": []}

@app.post("/orders")
def place_order(req: OrderRequest):
    try:
        brk = _etrade_from_env()
        return brk.place(req).model_dump()
    except Exception as e:
        logger.error(f"Failed to place order: {e}")
        return {"status": "REJECTED", "message": str(e)}

@app.post("/orders/cancel/{broker_order_id}")
def cancel_order(broker_order_id: str):
    try:
        brk = _etrade_from_env()
        return brk.cancel(broker_order_id).model_dump()
    except Exception as e:
        logger.error(f"Failed to cancel order: {e}")
        return {"status": "ERROR", "message": str(e)}

@app.get("/account")
def get_account():
    try:
        brk = _etrade_from_env()
        return brk.account()
    except Exception as e:
        logger.error(f"Failed to get account: {e}")
        return {"error": str(e)}

@app.get("/bandit/logs")
def get_bandit_logs(limit: int = 50, db: Session = Depends(get_db)):
    from sqlalchemy import func
    
    limit = max(1, min(500, limit))
    
    logs = db.query(BanditLog).order_by(BanditLog.ts.desc()).limit(limit).all()
    return [
        {
            "ts": log.ts.isoformat(),
            "arm_name": log.arm_name,
            "context": log.x_json,
            "reward": log.reward
        }
        for log in logs
    ]

@app.get("/bandit/stats")
def get_bandit_stats(db: Session = Depends(get_db)):
    from sqlalchemy import func
    
    stats = db.query(
        BanditLog.arm_name,
        func.count(BanditLog.id).label('count'),
        func.avg(BanditLog.reward).label('avg_reward'),
        func.min(BanditLog.reward).label('min_reward'),
        func.max(BanditLog.reward).label('max_reward')
    ).group_by(BanditLog.arm_name).all()
    
    total = db.query(func.count(BanditLog.id)).scalar()
    
    arm_stats = [
        {
            "arm_name": s.arm_name,
            "count": s.count,
            "avg_reward": float(s.avg_reward) if s.avg_reward else 0.0,
            "min_reward": float(s.min_reward) if s.min_reward else 0.0,
            "max_reward": float(s.max_reward) if s.max_reward else 0.0
        }
        for s in stats
    ]
    
    arm_stats.sort(key=lambda x: x['avg_reward'], reverse=True)
    
    return {
        "total": total or 0,
        "arm_stats": arm_stats
    }

@app.get("/evidence/event-study")
def get_event_study(
    ticker: str,
    event: str = "EARNINGS",
    pre: int = 5,
    post: int = 5,
    benchmark: str = "SPY"
):
    """
    Compute Cumulative Abnormal Returns (CAR) for event study with bootstrap CI.
    
    Args:
        ticker: Stock ticker
        event: Event type (EARNINGS, FDA_PDUFA, etc.)
        pre: Days before event
        post: Days after event
        benchmark: Market benchmark (default SPY)
    
    Returns:
        EventStudyV1 schema with CAR series and confidence intervals
    """
    ticker = ticker.upper().strip()
    try:
        hist = market_data.daily_ohlc(ticker, lookback=max(30, pre + post + 10))
        if not hist:
            raise HTTPException(status_code=404, detail=f"No historical data for {ticker}")
        
        from services.analysis.enhanced_features import compute_event_study
        result = compute_event_study(
            ticker=ticker,
            event_type=event,
            hist=hist,
            market_data_adapter=market_data,
            pre_days=pre,
            post_days=post,
            market_benchmark=benchmark
        )
        
        if "error" in result:
            raise HTTPException(status_code=400, detail=result["error"])
        
        return result
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error computing event study for {ticker}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to compute event study: {str(e)}")

@app.get("/stats/arms/ci")
def get_arm_stats_ci(
    arm: Optional[str] = None,
    regime: Optional[str] = None,
    db: Session = Depends(get_db)
):
    """
    Get arm performance statistics with bootstrap confidence intervals.
    
    Args:
        arm: Arm name (optional, returns all arms if not specified)
        regime: Regime filter (optional, e.g., "vix_mid")
    
    Returns:
        ArmStatsV1 schema with median R ± CI, p90 R, max DD
    """
    try:
        query = db.query(BanditLog)
        
        if arm:
            query = query.filter(BanditLog.arm_name == arm)
        
        # Note: regime filtering would require storing regime in BanditLog
        # For now, we use all data
        logs = query.all()
        
        if not logs:
            raise HTTPException(status_code=404, detail=f"No data found for arm={arm}")
        
        # Group by arm if arm not specified
        if not arm:
            arms = {}
            for log in logs:
                if log.arm_name not in arms:
                    arms[log.arm_name] = []
                arms[log.arm_name].append(log.reward)
            
            from services.analysis.enhanced_features import arm_stats_with_ci
            results = []
            for arm_name, rewards in arms.items():
                stats = arm_stats_with_ci(arm_name, rewards, regime)
                results.append(stats)
            
            return {
                "schema": "ArmStatsV1",
                "arms": results
            }
        else:
            # Single arm
            rewards = [log.reward for log in logs]
            from services.analysis.enhanced_features import arm_stats_with_ci
            return arm_stats_with_ci(arm, rewards, regime)
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error computing arm stats: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to compute arm stats: {str(e)}")

@app.get("/stats/calibration")
def get_calibration_stats():
    """
    Get LLM confidence calibration metrics.
    
    Returns:
        CalibrationV1 schema with ECE, Brier score, reliability plot data
    """
    from services.analysis.calibration import get_calibration_service
    service = get_calibration_service()
    
    metrics = service.compute_metrics()
    plot_data = service.get_reliability_plot_data(n_bins=10)
    
    return {
        "schema": "CalibrationV1",
        "ece": metrics["ece"],
        "brier": metrics["brier"],
        "n_samples": metrics["n_samples"],
        "bins": [
            {
                "bin": plot_data["bin_centers"][i],
                "pred": plot_data["bin_confidences"][i],
                "real": plot_data["bin_accuracies"][i],
                "count": plot_data["bin_counts"][i]
            }
            for i in range(len(plot_data["bin_centers"]))
        ]
    }

@app.post("/trade/execute")
def trade_execute(body: ExecutePayload):
    return {"status": "SIMULATED", "ticker": body.ticker, "shares": body.shares, "limit_price": body.limit_price}

# ========================================
# Action Slab Endpoints (Task C)
# ========================================

class AlertCreatePayload(StrictModel):
    ticker: str
    rule: dict
    decision_id: Optional[str] = None
    plan: Optional[dict] = None
    alignment: Optional[str] = None
    llm_v2: Optional[dict] = None
    drivers: Optional[dict] = None
    nba_score: Optional[float] = None
    timestamp_ms: Optional[int] = None

@app.post("/alerts/create")
async def create_alert(body: AlertCreatePayload):
    """
    Create a price/condition alert.
    Stub endpoint - logs and returns success.
    """
    logger.info(f"Alert created: ticker={body.ticker}, rule={body.rule}")
    # TODO: Store alert in database, wire to notification service
    return {
        "status": "created",
        "ticker": body.ticker,
        "rule": body.rule,
        "alert_id": f"alert_{body.ticker}_{datetime.utcnow().timestamp()}"
    }

class BriefSendPayload(StrictModel):
    ticker: str
    verdict: Optional[str] = None
    summary: str
    links: Optional[dict] = None
    decision_id: Optional[str] = None
    plan: Optional[dict] = None
    alignment: Optional[str] = None
    llm_v2: Optional[dict] = None
    drivers: Optional[dict] = None
    nba_score: Optional[float] = None
    timestamp_ms: Optional[int] = None

@app.post("/briefs/send")
async def send_brief(body: BriefSendPayload):
    """
    Send a brief memo to stakeholders.
    Stub endpoint - logs and returns success.
    """
    logger.info(f"Brief sent: ticker={body.ticker}, verdict={body.verdict}")
    # TODO: Send email/Slack notification, store in CRM
    return {
        "status": "sent",
        "ticker": body.ticker,
        "brief_id": f"brief_{body.ticker}_{datetime.utcnow().timestamp()}"
    }

class DecisionCommitPayload(StrictModel):
    ticker: str
    decision_id: Optional[str] = None
    plan: dict
    owner: str = "me"
    due: Optional[str] = None
    alignment: Optional[str] = None
    llm_v2: Optional[dict] = None
    drivers: Optional[dict] = None
    nba_score: Optional[float] = None
    timestamp_ms: Optional[int] = None

@app.post("/decisions/commit")
async def commit_decision(body: DecisionCommitPayload):
    """
    Commit a decision plan with owner and due date.
    Stub endpoint - logs and returns success.
    """
    logger.info(f"Decision committed: ticker={body.ticker}, owner={body.owner}, due={body.due}, alignment={body.alignment}")
    # TODO: Store in database, create task in project management system
    return {
        "status": "committed",
        "ticker": body.ticker,
        "owner": body.owner,
        "due": body.due,
        "decision_id": body.decision_id or f"decision_{body.ticker}_{datetime.utcnow().timestamp()}"
    }

# ========================================
# LLM Quality Telemetry (Task 4)
# ========================================

from collections import deque
import threading

_llm_metrics = {
    "parse_ok": deque(maxlen=1000),
    "parse_fail": deque(maxlen=1000),
    "latency_ms": deque(maxlen=1000),
    "policy_override": deque(maxlen=1000),
    "confidence_raw": deque(maxlen=1000),
    "confidence_calibrated": deque(maxlen=1000)
}
_metrics_lock = threading.Lock()

def record_llm_metric(
    parse_ok: bool,
    latency_ms: float,
    policy_override: bool = False,
    confidence_raw: Optional[float] = None,
    confidence_calibrated: Optional[float] = None
):
    """Record LLM quality metrics for telemetry."""
    with _metrics_lock:
        if parse_ok:
            _llm_metrics["parse_ok"].append(time())
        else:
            _llm_metrics["parse_fail"].append(time())
        
        _llm_metrics["latency_ms"].append(latency_ms)
        _llm_metrics["policy_override"].append(1 if policy_override else 0)
        
        if confidence_raw is not None:
            _llm_metrics["confidence_raw"].append(confidence_raw)
        if confidence_calibrated is not None:
            _llm_metrics["confidence_calibrated"].append(confidence_calibrated)

@app.get("/metrics/llm_phase1")
def get_llm_metrics():
    """
    Get LLM Phase-1 quality telemetry.
    Returns rolling counts and p95 latency.
    """
    with _metrics_lock:
        parse_ok_count = len(_llm_metrics["parse_ok"])
        parse_fail_count = len(_llm_metrics["parse_fail"])
        total = parse_ok_count + parse_fail_count
        parse_rate = parse_ok_count / total if total > 0 else 1.0
        
        latencies = list(_llm_metrics["latency_ms"])
        p95_latency = sorted(latencies)[int(len(latencies) * 0.95)] if latencies else 0.0
        median_latency = sorted(latencies)[len(latencies) // 2] if latencies else 0.0
        
        policy_overrides = list(_llm_metrics["policy_override"])
        override_rate = sum(policy_overrides) / len(policy_overrides) if policy_overrides else 0.0
        
        conf_raw = list(_llm_metrics["confidence_raw"])
        conf_cal = list(_llm_metrics["confidence_calibrated"])
        
        return {
            "schema": "LLMMetricsV1",
            "parse_rate": parse_rate,
            "parse_ok_count": parse_ok_count,
            "parse_fail_count": parse_fail_count,
            "total_requests": total,
            "p95_latency_ms": p95_latency,
            "median_latency_ms": median_latency,
            "policy_override_rate": override_rate,
            "avg_confidence_raw": sum(conf_raw) / len(conf_raw) if conf_raw else 0.0,
            "avg_confidence_calibrated": sum(conf_cal) / len(conf_cal) if conf_cal else 0.0,
            "window_size": 1000
        }
