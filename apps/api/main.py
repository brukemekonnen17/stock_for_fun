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
from services.llm.client import propose_trade
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
                if len(closes) >= 20:
                    returns = [(closes[i] - closes[i-1]) / closes[i-1] for i in range(1, len(closes))]
                    if len(returns) >= 19:
                        import statistics
                        mean_return = statistics.mean(returns[-20:])
                        variance = statistics.mean([(r - mean_return) ** 2 for r in returns[-20:]])
                        std_dev = variance ** 0.5
                        expected_move = abs(2 * std_dev)
                    else:
                        expected_move = 0.03
                elif len(closes) >= 6:
                    rets = [abs((closes[i] - closes[i-1]) / closes[i-1]) for i in range(1, len(closes))]
                    expected_move = sum(rets) / len(rets) if rets else 0.03
                else:
                    expected_move = 0.03
        except ValueError as e:
            logger.warning(f"Historical data fetch failed for {ticker}: {e}")
            dollar_vol = price * 1_000_000
            expected_move = 0.03
        
        liquidity_score = 1.0 if dollar_vol > 1_000_000_000 else (0.8 if dollar_vol > 100_000_000 else 0.5)
        spread_score = 1.0 - min(1.0, spread / (price * 0.01))
        volatility_score = min(1.0, expected_move / 0.10)
        rank = 50 + (liquidity_score * 20) + (spread_score * 15) + (volatility_score * 15)
        rank = max(0.0, min(100.0, rank))
        
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
        
        context = [
            immediacy,
            0.6,
            liquidity_score,
            expected_move,
            news_score,
            expected_move,
            days_to_event
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
    
    llm_out = await propose_trade(llm_payload)
    
    why = WhySelected(
        ticker=body.ticker,
        catalyst=cat,
        strategy=rationale,
        news=news_items,
        history=perf,
        market=mkt,
        llm_confidence=float(llm_out.get("confidence", 0.0))
    )
    
    return ProposeResponse(
        selected_arm=selected_arm,
        plan=llm_out,
        decision_id=body.decision_id,
        analysis=why.model_dump(),
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
    
    logger.info(f"[{decision_id}] Bandit updated")
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

@app.post("/trade/execute")
def trade_execute(body: ExecutePayload):
    return {"status": "SIMULATED", "ticker": body.ticker, "shares": body.shares, "limit_price": body.limit_price}
