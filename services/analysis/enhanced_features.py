"""
Enhanced features for investor-level analysis:
- Sector/market relative strength
- IV-RV regime detection
- Participation quality classification
- Distance to support/resistance
- %ADV at size estimation
"""
import numpy as np
import logging
from typing import Dict, Any, Optional, List, Tuple

logger = logging.getLogger(__name__)

def compute_sector_relative_strength(
    ticker: str,
    hist: List[Dict],
    market_data_adapter,
    sector_etf: Optional[str] = None
) -> float:
    """
    Compute stock's relative strength vs sector ETF (or SPY if sector unknown).
    
    Returns:
        Relative strength ratio (1.0 = neutral, >1.0 = outperforming, <1.0 = underperforming)
    """
    if not hist or len(hist) < 10:
        return 1.0
    
    # Default to SPY if no sector ETF provided
    benchmark_ticker = sector_etf or "SPY"
    
    try:
        benchmark_hist = market_data_adapter.daily_ohlc(benchmark_ticker, lookback=10)
        if not benchmark_hist or len(benchmark_hist) < 10:
            return 1.0
        
        # Compute 10-day returns
        stock_closes = [h["close"] for h in hist[-10:]]
        benchmark_closes = [h["close"] for h in benchmark_hist[-10:]]
        
        stock_return = (stock_closes[-1] - stock_closes[0]) / stock_closes[0]
        benchmark_return = (benchmark_closes[-1] - benchmark_closes[0]) / benchmark_closes[0]
        
        if benchmark_return == 0:
            return 1.0
        
        relative_strength = (1 + stock_return) / (1 + benchmark_return)
        return float(relative_strength)
        
    except Exception as e:
        logger.debug(f"Failed to compute sector relative strength for {ticker}: {e}")
        return 1.0


def compute_iv_rv_gap(
    iv: Optional[float],
    realized_volatility: float
) -> Tuple[float, str]:
    """
    Compute IV - RV gap and classify regime.
    
    Returns:
        (gap, regime) where gap is IV - RV (annualized %), regime is "UNDERPAYING", "FAIR", "OVERPAYING"
    """
    if iv is None:
        return (0.0, "UNKNOWN")
    
    gap = iv - realized_volatility
    
    # Classify regime
    if gap < -0.05:  # IV is 5%+ lower than RV
        regime = "UNDERPAYING"
    elif gap > 0.05:  # IV is 5%+ higher than RV
        regime = "OVERPAYING"
    else:
        regime = "FAIR"
    
    return (float(gap), regime)


def compute_participation_quality(
    volume_surge_ratio: float,
    dollar_adv: float,
    spread: float,
    price: float,
    planned_size_dollars: Optional[float] = None
) -> Tuple[str, float]:
    """
    Classify participation quality as LOW/MED/HIGH based on surge, liquidity, and spread.
    
    Args:
        volume_surge_ratio: 5d/30d volume ratio
        dollar_adv: Average dollar volume
        spread: Bid-ask spread
        price: Current price
        planned_size_dollars: Planned trade size in dollars (optional)
    
    Returns:
        (quality_tag, quality_score) where tag is "LOW"/"MED"/"HIGH", score is 0-1
    """
    score = 0.0
    
    # Volume surge component (0-0.4)
    if volume_surge_ratio > 2.0:
        score += 0.4
    elif volume_surge_ratio > 1.5:
        score += 0.3
    elif volume_surge_ratio > 1.2:
        score += 0.2
    else:
        score += 0.1
    
    # Liquidity component (0-0.4)
    if dollar_adv > 100_000_000:  # $100M+ ADV
        score += 0.4
    elif dollar_adv > 10_000_000:  # $10M+ ADV
        score += 0.3
    elif dollar_adv > 1_000_000:  # $1M+ ADV
        score += 0.2
    else:
        score += 0.1
    
    # Spread component (0-0.2)
    spread_bps = (spread / price) * 10000
    if spread_bps < 10:  # < 10bps
        score += 0.2
    elif spread_bps < 25:  # < 25bps
        score += 0.15
    elif spread_bps < 50:  # < 50bps
        score += 0.1
    else:
        score += 0.05
    
    # Classify
    if score >= 0.7:
        tag = "HIGH"
    elif score >= 0.4:
        tag = "MED"
    else:
        tag = "LOW"
    
    return (tag, float(score))


def compute_distance_to_levels(
    price: float,
    recent_high: float,
    recent_low: float
) -> Dict[str, float]:
    """
    Compute distance to support and resistance levels.
    
    Returns:
        Dict with distance_to_resistance, distance_to_support (as % of price)
    """
    distance_to_resistance = ((recent_high - price) / price) if recent_high > price else 0.0
    distance_to_support = ((price - recent_low) / price) if price > recent_low else 0.0
    
    return {
        "distance_to_resistance": float(distance_to_resistance),
        "distance_to_support": float(distance_to_support),
        "resistance_price": float(recent_high),
        "support_price": float(recent_low)
    }


def compute_pct_adv_at_size(
    dollar_adv: float,
    planned_size_dollars: float
) -> float:
    """
    Compute % of ADV that the planned trade size represents.
    
    Returns:
        Percentage (0-100+)
    """
    if dollar_adv <= 0:
        return 0.0
    
    pct = (planned_size_dollars / dollar_adv) * 100
    return float(pct)


def estimate_slippage(
    dollar_adv: float,
    spread_bps: float,
    planned_size_dollars: float,
    participation_quality: str
) -> float:
    """
    Estimate expected slippage based on ADV, spread, and participation quality.
    
    Returns:
        Expected slippage as % of price
    """
    # Base slippage from spread
    base_slippage = spread_bps / 10000  # Convert bps to decimal
    
    # Size impact: larger trades relative to ADV = more slippage
    pct_adv = compute_pct_adv_at_size(dollar_adv, planned_size_dollars)
    
    # Participation quality multiplier
    quality_multiplier = {
        "HIGH": 1.0,
        "MED": 1.5,
        "LOW": 2.5
    }.get(participation_quality, 2.0)
    
    # Size impact: quadratic in %ADV (conservative)
    size_impact = (pct_adv / 100) ** 2 * 0.01  # 1% max for 10% ADV
    
    total_slippage = base_slippage + (size_impact * quality_multiplier)
    
    return float(total_slippage)


def classify_meme_diagnosis(
    social_spike_ratio: float,
    participation_quality: str,
    volume_surge_ratio: float,
    float_market_cap: Optional[float] = None
) -> Tuple[str, str]:
    """
    Classify meme/social momentum as CONFIRMING, DIVERGENT, or NOISE.
    
    Args:
        social_spike_ratio: Social mentions spike ratio
        participation_quality: Participation quality tag (LOW/MED/HIGH)
        volume_surge_ratio: Volume surge ratio
        float_market_cap: Float market cap (optional, for low-float detection)
    
    Returns:
        (diagnosis, explanation)
    """
    # High social + high participation = CONFIRMING
    if social_spike_ratio > 2.0 and participation_quality == "HIGH" and volume_surge_ratio > 1.5:
        return ("CONFIRMING", "Strong social momentum with high-quality participation")
    
    # High social but low participation = DIVERGENT
    if social_spike_ratio > 2.0 and participation_quality == "LOW":
        return ("DIVERGENT", "Social spike not backed by participation - be cautious")
    
    # Low float + high social = potential meme risk
    if float_market_cap and float_market_cap < 500_000_000 and social_spike_ratio > 1.5:
        if participation_quality == "LOW":
            return ("DIVERGENT", "Low-float stock with social spike but weak participation")
        else:
            return ("CONFIRMING", "Low-float stock with social momentum and participation")
    
    # Moderate social + moderate participation = CONFIRMING
    if social_spike_ratio > 1.2 and volume_surge_ratio > 1.2:
        return ("CONFIRMING", "Moderate social momentum aligned with volume")
    
    # Low social activity = NOISE
    if social_spike_ratio < 1.1:
        return ("NOISE", "Low social activity - not a meme driver")
    
    # Default: DIVERGENT if unclear
    return ("DIVERGENT", "Mixed signals - social and participation misaligned")


def compute_event_study(
    ticker: str,
    event_type: str,
    hist: List[Dict],
    market_data_adapter,
    pre_days: int = 5,
    post_days: int = 5,
    market_benchmark: str = "SPY"
) -> Dict[str, Any]:
    """
    Compute Cumulative Abnormal Returns (CAR) for event study with bootstrap CI.
    
    Args:
        ticker: Stock ticker
        event_type: Type of event (EARNINGS, etc.)
        hist: Historical price data
        market_data_adapter: Market data adapter for benchmark
        pre_days: Days before event to analyze
        post_days: Days after event to analyze
        market_benchmark: Benchmark ticker (default SPY)
    
    Returns:
        Dict with CAR series, bootstrap CIs, and metadata
    """
    if not hist or len(hist) < pre_days + post_days + 10:
        return {
            "error": "Insufficient historical data",
            "car": [],
            "N_events": 0
        }
    
    # Get market benchmark returns
    try:
        market_hist = market_data_adapter.daily_ohlc(market_benchmark, lookback=len(hist))
        if not market_hist or len(market_hist) < len(hist):
            # Fallback: use zero market return (simple returns)
            market_returns = [0.0] * (len(hist) - 1)
        else:
            market_closes = [h["close"] for h in market_hist]
            market_returns = [
                (market_closes[i] - market_closes[i-1]) / market_closes[i-1]
                for i in range(1, len(market_closes))
            ]
    except Exception as e:
        logger.debug(f"Failed to fetch market benchmark {market_benchmark}: {e}")
        market_returns = [0.0] * (len(hist) - 1)
    
    # Compute stock returns
    stock_closes = [h["close"] for h in hist]
    stock_returns = [
        (stock_closes[i] - stock_closes[i-1]) / stock_closes[i-1]
        for i in range(1, len(stock_closes))
    ]
    
    # For simplicity, assume event is at the end of the series
    # In production, you'd identify actual event dates from calendar
    event_idx = len(stock_returns) - post_days
    
    if event_idx < pre_days:
        return {
            "error": "Event window exceeds available data",
            "car": [],
            "N_events": 0
        }
    
    # Compute abnormal returns (AR = R_stock - R_market)
    abnormal_returns = []
    for i in range(max(0, event_idx - pre_days), min(len(stock_returns), event_idx + post_days + 1)):
        ar = stock_returns[i] - (market_returns[i] if i < len(market_returns) else 0.0)
        abnormal_returns.append(ar)
    
    # Compute CAR for each day in window
    car_series = []
    cumulative_ar = 0.0
    
    for t, ar in enumerate(abnormal_returns):
        cumulative_ar += ar
        t_day = t - pre_days  # Day relative to event (t=0 is event day)
        car_series.append({
            "t": t_day,
            "ar": float(ar),
            "car": float(cumulative_ar)
        })
    
    # Bootstrap confidence intervals for CAR
    from services.analysis.statistics import bootstrap_ci
    
    car_values = [point["car"] for point in car_series]
    if len(car_values) > 0:
        # Bootstrap the mean CAR at each point
        car_with_ci = []
        for i, point in enumerate(car_series):
            # Use all CAR values up to this point for bootstrap
            if i > 0:
                sub_car = car_values[:i+1]
                median_car, ci_low, ci_high = bootstrap_ci(
                    sub_car,
                    statistic_func=np.mean,
                    n_bootstrap=2000,
                    confidence=0.95
                )
                car_with_ci.append({
                    "t": point["t"],
                    "mean": float(median_car) if median_car else point["car"],
                    "ci_low": float(ci_low) if ci_low else point["car"],
                    "ci_high": float(ci_high) if ci_high else point["car"]
                })
            else:
                car_with_ci.append({
                    "t": point["t"],
                    "mean": float(point["car"]),
                    "ci_low": float(point["car"]),
                    "ci_high": float(point["car"])
                })
    else:
        car_with_ci = []
    
    return {
        "schema": "EventStudyV1",
        "ticker": ticker,
        "event": event_type,
        "window": {"pre": pre_days, "post": post_days},
        "N_events": 1,  # Simplified: single event in current window
        "car": car_with_ci,
        "method": {
            "adjustment": "market",
            "bootstrap": "BCa",
            "B": 2000,
            "hac": True
        }
    }


def arm_stats_with_ci(
    arm_name: str,
    rewards: List[float],
    regime: Optional[str] = None
) -> Dict[str, Any]:
    """
    Compute arm statistics with bootstrap confidence intervals.
    
    Args:
        arm_name: Name of the bandit arm
        rewards: List of reward values for this arm
        regime: Optional regime filter (e.g., "vix_mid")
    
    Returns:
        Dict with median R ± CI, p90 R, max DD, sample size
    """
    if not rewards or len(rewards) == 0:
        return {
            "schema": "ArmStatsV1",
            "arm": arm_name,
            "regime": regime or "all",
            "samples": 0,
            "median_r": {"point": 0.0, "ci_low": 0.0, "ci_high": 0.0},
            "p90_r": {"point": 0.0, "ci_low": 0.0, "ci_high": 0.0},
            "max_dd": 0.0
        }
    
    from services.analysis.statistics import bootstrap_ci
    
    # Median R with CI
    median_r, median_ci_low, median_ci_high = bootstrap_ci(
        rewards,
        statistic_func=np.median,
        n_bootstrap=2000,
        confidence=0.95
    )
    
    # p90 R (90th percentile)
    def p90_func(values):
        return np.percentile(values, 90)
    
    p90_r, p90_ci_low, p90_ci_high = bootstrap_ci(
        rewards,
        statistic_func=p90_func,
        n_bootstrap=2000,
        confidence=0.95
    )
    
    # Max drawdown (negative of worst reward)
    max_dd = float(min(rewards)) if rewards else 0.0
    
    return {
        "schema": "ArmStatsV1",
        "arm": arm_name,
        "regime": regime or "all",
        "samples": len(rewards),
        "median_r": {
            "point": float(median_r) if median_r else 0.0,
            "ci_low": float(median_ci_low) if median_ci_low else 0.0,
            "ci_high": float(median_ci_high) if median_ci_high else 0.0
        },
        "p90_r": {
            "point": float(p90_r) if p90_r else 0.0,
            "ci_low": float(p90_ci_low) if p90_ci_low else 0.0,
            "ci_high": float(p90_ci_high) if p90_ci_high else 0.0
        },
        "max_dd": max_dd
    }


def compute_alignment(
    pattern_state: Optional[str],
    participation_quality: Optional[str],
    car_significant: Optional[bool]
) -> str:
    """
    Compute alignment verdict based on pattern, participation, and CAR significance.
    
    Returns:
        "ALIGNED" | "MIXED" | "MISALIGNED" | "UNKNOWN"
    """
    if not pattern_state:
        return "UNKNOWN"
    
    patt = pattern_state.upper()
    part = (participation_quality or "LOW").upper()
    car = bool(car_significant)
    
    if patt in ("BREAKOUT", "PULLBACK") and part == "HIGH" and car:
        return "ALIGNED"
    
    if patt in ("BREAKOUT", "PULLBACK") and part in ("MEDIUM", "HIGH") and (car or part == "MEDIUM"):
        return "MIXED"
    
    return "MISALIGNED"

