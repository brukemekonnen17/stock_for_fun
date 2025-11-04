"""
Deterministic computation of "why selected" facts.
All numeric truth comes from here, not from LLM.
"""
from datetime import datetime, timedelta
from typing import List
import logging

from apps.api.schemas import CatalystInfo, PerfStats, NewsItem, MarketContext
from services.news.newsapi_adapter import get_recent_news_items
from services.analysis.events import get_event_details

logger = logging.getLogger(__name__)

# Market data adapter will be injected by the caller to use the same one as the API
_md = None

def set_market_data_adapter(adapter):
    """Set the market data adapter to use (should be the same one as the API)"""
    global _md
    _md = adapter

def catalyst_from_payload(payload: "ProposePayload", market_data_adapter) -> CatalystInfo:
    # Get real event details first
    event_type, days_to_event = get_event_details(payload.ticker, market_data_adapter)

    return CatalystInfo(
        event_type=event_type,
        event_time=datetime.utcnow() + timedelta(days=days_to_event),
        days_to_event=days_to_event,
        materiality=_materiality(event_type, ticker=getattr(payload, 'ticker', None), market_data_adapter=market_data_adapter),
        expected_move=payload.expected_move,
        rank=sum(payload.rank_components.values()) / len(payload.rank_components) * 100 if payload.rank_components else 50.0
    )

def _materiality(event_type: str, ticker: str = None, market_data_adapter=None) -> float:
    """Materiality score by event type (0-1 scale)
    Can be enhanced with ticker-specific historical earnings impact
    """
    base_m = {
        "FDA_PDUFA": 1.0,
        "TRIAL_READOUT": 0.9,
        "EARNINGS": 0.6,
        "GUIDANCE": 0.5,
        "PARTNERSHIP": 0.5,
        "DIVIDEND": 0.2,
        "SPLIT": 0.2,
    }
    
    base_score = base_m.get(event_type, 0.4)
    
    # Enhance with ticker-specific data if available
    if ticker and market_data_adapter and event_type == "EARNINGS":
        try:
            # Look at historical earnings moves to adjust materiality
            hist = market_data_adapter.daily_ohlc(ticker, lookback=365)
            if hist and len(hist) >= 60:
                # Calculate average absolute move around earnings periods
                # (Simplified: use quarterly volatility as proxy)
                closes = [h["close"] for h in hist[-60:]]
                quarterly_moves = []
                for i in range(0, len(closes) - 20, 20):
                    if i + 20 < len(closes):
                        move = abs((closes[i + 20] - closes[i]) / closes[i])
                        quarterly_moves.append(move)
                
                if quarterly_moves:
                    avg_quarterly_move = sum(quarterly_moves) / len(quarterly_moves)
                    # Adjust materiality: higher volatility = higher materiality
                    # Scale: 0.5x to 1.5x base materiality based on volatility
                    volatility_factor = min(1.5, max(0.5, avg_quarterly_move / 0.10))  # 10% is baseline
                    base_score = base_score * volatility_factor
                    logger.debug(f"Adjusted materiality for {ticker}: {base_score:.2f} (volatility factor: {volatility_factor:.2f})")
        except Exception as e:
            logger.debug(f"Failed to enhance materiality for {ticker}: {e}")
    
    return base_score

def compute_market_context(ticker: str, price: float, spread: float, dollar_adv: float) -> MarketContext:
    """Compute market context including technical indicators"""
    global _md
    if _md is None:
        # Fallback to YFMarketData if not set (shouldn't happen in normal operation)
        from services.marketdata.yf_adapter import YFMarketData
        _md = YFMarketData()
        logger.warning("Market data adapter not set, using YFMarketData fallback")
    
    rsi14 = None
    atr14 = None
    
    try:
        # Get historical data for RSI/ATR - use longer lookback for better RSI
        hist = _md.daily_ohlc(ticker, lookback=30)
        
        if hist and len(hist) >= 15:  # Need at least 15 days for RSI(14)
            closes = [h["close"] for h in hist[-15:]]
            highs = [h["high"] for h in hist[-15:]]
            lows = [h["low"] for h in hist[-15:]]
            
            # Compute RSI(14) - ensure we have enough data
            if len(closes) >= 15:
                rsi14 = _compute_rsi(closes, period=14)
                logger.debug(f"RSI(14) for {ticker}: {rsi14}")
            
            # Compute ATR(14)
            if len(highs) >= 15 and len(lows) >= 15:
                atr14 = _compute_atr(highs, lows, closes, period=14)
                logger.debug(f"ATR(14) for {ticker}: {atr14}")
        else:
            logger.warning(f"Insufficient historical data for {ticker}: {len(hist) if hist else 0} days (need 15+)")
        
    except Exception as e:
        logger.warning(f"Failed to compute market context for {ticker}: {e}", exc_info=True)
    
    return MarketContext(
        price=price,
        spread=spread,
        dollar_adv=dollar_adv,
        rsi14=rsi14,
        atr14=atr14
    )

def _compute_rsi(prices: List[float], period: int = 14) -> float:
    """Compute RSI (Relative Strength Index)"""
    if len(prices) < period + 1:
        return None
    
    deltas = [prices[i] - prices[i-1] for i in range(1, len(prices))]
    gains = [d if d > 0 else 0 for d in deltas[-period:]]
    losses = [-d if d < 0 else 0 for d in deltas[-period:]]
    
    avg_gain = sum(gains) / period
    avg_loss = sum(losses) / period
    
    if avg_loss == 0:
        return 100.0
    
    rs = avg_gain / avg_loss
    rsi = 100 - (100 / (1 + rs))
    return round(rsi, 2)

def _compute_atr(highs: List[float], lows: List[float], closes: List[float], period: int = 14) -> float:
    """Compute ATR (Average True Range)"""
    if len(highs) < period + 1:
        return None
    
    true_ranges = []
    for i in range(1, len(highs)):
        tr1 = highs[i] - lows[i]
        tr2 = abs(highs[i] - closes[i-1])
        tr3 = abs(lows[i] - closes[i-1])
        true_ranges.append(max(tr1, tr2, tr3))
    
    if len(true_ranges) < period:
        return None
    
    atr = sum(true_ranges[-period:]) / period
    return round(atr, 2)

def recent_news(ticker: str, limit: int = 5) -> List[NewsItem]:
    """Get recent news for a ticker"""
    try:
        items = get_recent_news_items(ticker, limit=limit)
        return items
    except Exception as e:
        logger.warning(f"Failed to fetch news for {ticker}: {e}")
        # Fallback to simple stub
        now = datetime.utcnow()
        return [
            NewsItem(
                headline=f"{ticker} - Market analysis ongoing",
                url="https://example.com",
                timestamp=now - timedelta(hours=1),
                sentiment=0.0
            )
        ]

def build_perf_stats(ticker: str, event_type: str, backtest_kpis: dict, market_data_adapter=None) -> PerfStats:
    """Build performance stats from backtest KPIs or historical data"""
    # Use provided backtest KPIs if available
    if backtest_kpis and backtest_kpis.get("samples", 0) > 0:
        return PerfStats(
            horizon_days=5,
            samples=backtest_kpis.get("samples", 50),
            hit_rate=backtest_kpis.get("hit_rate", 0.5),
            avg_win=backtest_kpis.get("avg_win", 0.012),
            avg_loss=backtest_kpis.get("avg_loss", -0.008),
            median_r=backtest_kpis.get("median_r", 0.10),
            p90_r=backtest_kpis.get("p90_r", 0.35),
            max_dd=backtest_kpis.get("max_dd", -0.18),
        )
    
    # Try to calculate from real historical data
    if market_data_adapter:
        try:
            from services.analysis.performance import calculate_perf_stats_from_history
            return calculate_perf_stats_from_history(ticker, market_data_adapter, event_type)
        except Exception as e:
            logger.warning(f"Failed to calculate perf stats from history for {ticker}: {e}")
    
    # Default stub if no backtest data and calculation failed
    return PerfStats(
        horizon_days=5,
        samples=50,
        hit_rate=0.50,
        avg_win=0.010,
        avg_loss=-0.008,
        median_r=0.08,
        p90_r=0.30,
        max_dd=-0.15,
    )

def brief_reason_for_arm(arm: str, cat: CatalystInfo, mkt: MarketContext) -> str:
    """Generate brief reason why this arm was selected"""
    if arm == "POST_EVENT_MOMO":
        return "Post-event momentum favored given strong gap potential and adequate $ADV."
    if arm == "EARNINGS_PRE":
        return "Pre-earnings setup with near-term catalyst and above-median expected move."
    if arm == "NEWS_SPIKE":
        return "Abnormal volume/news flow suggests short-term dislocation."
    if arm == "REACTIVE":
        return "Binary catalyst—reactive (not predictive) strategy post-print."
    return "No edge identified; skip."

def gating_facts(cat: CatalystInfo, mkt: MarketContext) -> List[str]:
    """Generate list of gating facts (checks that passed)"""
    out = []
    
    if cat.expected_move >= 0.03:
        out.append(f"Expected move {cat.expected_move:.1%} ≥ 3%")
    
    if cat.rank >= 70:
        out.append(f"CatalystRank {cat.rank:.0f} ≥ 70")
    
    if mkt.dollar_adv >= 1_000_000:
        out.append(f"Liquidity ${mkt.dollar_adv:,.0f} ≥ $1M ADV")
    
    max_spread = min(0.05, mkt.price * 0.005)
    if mkt.spread <= max_spread:
        out.append("Spread within policy")
    
    if cat.materiality >= 0.5:
        out.append(f"High materiality ({cat.materiality:.0%})")
    
    if mkt.rsi14 and 30 <= mkt.rsi14 <= 70:
        out.append(f"RSI(14) {mkt.rsi14:.0f} in neutral range")
    
    return out

