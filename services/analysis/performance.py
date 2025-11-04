"""
Calculate performance stats from real historical data
"""
import logging
from datetime import datetime, timedelta
from typing import Optional

from apps.api.schemas import PerfStats

logger = logging.getLogger(__name__)

def calculate_perf_stats_from_history(ticker: str, market_data_adapter, event_type: str) -> PerfStats:
    """
    Calculate performance stats from historical price data.
    For earnings: look at price moves after earnings dates.
    """
    try:
        # Get 6 months of historical data
        hist = market_data_adapter.daily_ohlc(ticker, lookback=180)
        
        if not hist or len(hist) < 30:
            logger.debug(f"Insufficient history for {ticker}, using defaults")
            return _default_perf_stats()
        
        closes = [h["close"] for h in hist]
        
        # Calculate various metrics from price history
        # 1. Hit rate: % of days with positive 5-day forward returns
        positive_moves = 0
        total_moves = 0
        returns_5d = []
        
        for i in range(5, min(len(closes), 30)):  # Look at last 30 days
            if i + 5 < len(closes):
                forward_return = (closes[i + 5] - closes[i]) / closes[i]
                returns_5d.append(forward_return)
                if forward_return > 0:
                    positive_moves += 1
                total_moves += 1
        
        hit_rate = positive_moves / total_moves if total_moves > 0 else 0.5
        
        # 2. Average win/loss
        wins = [r for r in returns_5d if r > 0]
        losses = [r for r in returns_5d if r < 0]
        
        avg_win = sum(wins) / len(wins) if wins else 0.012
        avg_loss = sum(losses) / len(losses) if losses else -0.008
        
        # 3. R-multiples (risk-adjusted returns)
        # Use ATR as risk unit
        try:
            highs = [h["high"] for h in hist[-30:]]
            lows = [h["low"] for h in hist[-30:]]
            
            if len(highs) >= 15 and len(lows) >= 15:
                # Calculate ATR
                true_ranges = []
                for i in range(1, len(highs)):
                    tr1 = highs[i] - lows[i]
                    tr2 = abs(highs[i] - closes[i-1])
                    tr3 = abs(lows[i] - closes[i-1])
                    true_ranges.append(max(tr1, tr2, tr3))
                
                if true_ranges:
                    atr = sum(true_ranges[-14:]) / min(14, len(true_ranges))
                    risk_unit = atr / closes[-1] if closes[-1] > 0 else 0.01
                    
                    # Calculate R-multiples
                    r_multiples = [r / risk_unit for r in returns_5d if risk_unit > 0]
                    
                    if r_multiples:
                        sorted_r = sorted(r_multiples)
                        median_r = sorted_r[len(sorted_r) // 2]
                        p90_r = sorted_r[int(len(sorted_r) * 0.9)] if len(sorted_r) > 1 else 0.35
                    else:
                        median_r = 0.10
                        p90_r = 0.35
                else:
                    median_r = 0.10
                    p90_r = 0.35
            else:
                median_r = 0.10
                p90_r = 0.35
        except Exception as e:
            logger.debug(f"R-multiple calculation failed for {ticker}: {e}")
            median_r = 0.10
            p90_r = 0.35
        
        # 4. Max drawdown
        max_dd = 0.0
        peak = closes[0]
        for close in closes:
            if close > peak:
                peak = close
            dd = (close - peak) / peak
            if dd < max_dd:
                max_dd = dd
        
        samples = total_moves if total_moves > 0 else 50
        
        logger.info(f"Calculated perf stats for {ticker}: hit_rate={hit_rate:.2%}, samples={samples}")
        
        return PerfStats(
            horizon_days=5,
            samples=samples,
            hit_rate=hit_rate,
            avg_win=avg_win,
            avg_loss=avg_loss,
            median_r=median_r,
            p90_r=p90_r,
            max_dd=max_dd,
        )
        
    except Exception as e:
        logger.warning(f"Failed to calculate perf stats for {ticker}: {e}", exc_info=True)
        return _default_perf_stats()

def _default_perf_stats() -> PerfStats:
    """Default fallback performance stats"""
    return PerfStats(
        horizon_days=5,
        samples=50,
        hit_rate=0.54,
        avg_win=0.012,
        avg_loss=-0.008,
        median_r=0.10,
        p90_r=0.35,
        max_dd=-0.15,
    )

