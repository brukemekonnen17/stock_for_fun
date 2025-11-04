"""
Evidence-first analysis endpoint with statistical tests and uncertainty quantification.
"""
import logging
from datetime import datetime
from typing import Dict, List, Optional, Any
import numpy as np
from services.analysis.statistics import (
    bootstrap_ci,
    mann_whitney_test,
    wilson_binomial_test,
    benjamini_hochberg_fdr,
    event_study_car,
    quantile_regression_room,
    calibration_metrics,
    conformal_prediction_band,
    compute_effect_size_grade,
    format_significance_badge,
    StatisticalTest
)
from services.analysis.evidence_rules import (
    interpret_test,
    interpret_volume_test,
    interpret_median_return,
    interpret_hit_rate_test,
    format_fdr_badge
)

logger = logging.getLogger(__name__)


def compute_technical_indicators(
    hist: List[Dict],
    price: float
) -> Dict[str, Any]:
    """
    Compute comprehensive technical indicators from historical data.
    Returns: EMA20, EMA50, RSI14, Bollinger Bands, ATR14, ADR20
    """
    if not hist or len(hist) < 20:
        return {
            "ema20": price,
            "ema50": price,
            "rsi14": 50.0,
            "bb_upper": price * 1.02,
            "bb_lower": price * 0.98,
            "atr14": price * 0.02,
            "adr20": 0.02
        }
    
    closes = [h["close"] for h in hist]
    highs = [h["high"] for h in hist]
    lows = [h["low"] for h in hist]
    
    # EMA calculations
    ema20 = closes[-1]
    alpha_20 = 2 / (20 + 1)
    for i in range(max(0, len(closes) - 20), len(closes)):
        if i > 0:
            ema20 = alpha_20 * closes[i] + (1 - alpha_20) * ema20
        else:
            ema20 = closes[i]
    
    ema50 = closes[-1]
    alpha_50 = 2 / (50 + 1)
    for i in range(max(0, len(closes) - 50), len(closes)):
        if i > 0:
            ema50 = alpha_50 * closes[i] + (1 - alpha_50) * ema50
        else:
            ema50 = closes[i]
    
    # RSI14
    rsi14 = 50.0
    if len(closes) >= 15:
        gains = [max(0, closes[i] - closes[i-1]) for i in range(len(closes)-14, len(closes))]
        losses = [max(0, closes[i-1] - closes[i]) for i in range(len(closes)-14, len(closes))]
        avg_gain = sum(gains) / 14
        avg_loss = sum(losses) / 14
        if avg_loss > 0:
            rs = avg_gain / avg_loss
            rsi14 = 100 - (100 / (1 + rs))
    
    # Bollinger Bands (20-period, 2 std dev)
    if len(closes) >= 20:
        sma20 = sum(closes[-20:]) / 20
        std20 = np.std(closes[-20:])
        bb_upper = sma20 + 2 * std20
        bb_lower = sma20 - 2 * std20
    else:
        sma20 = price
        std20 = price * 0.02
        bb_upper = price * 1.02
        bb_lower = price * 0.98
    
    # ATR14
    atr14 = price * 0.02
    if len(hist) >= 15:
        trs = []
        for i in range(max(1, len(hist) - 14), len(hist)):
            tr = max(
                highs[i] - lows[i],
                abs(highs[i] - closes[i-1]),
                abs(lows[i] - closes[i-1])
            )
            trs.append(tr)
        if trs:
            atr14 = sum(trs) / len(trs)
    
    # ADR20 (Average Daily Range)
    if len(hist) >= 20:
        ranges = [(highs[i] - lows[i]) / closes[i] for i in range(len(hist) - 20, len(hist))]
        adr20 = sum(ranges) / len(ranges)
    else:
        adr20 = 0.02
    
    return {
        "ema20": float(ema20),
        "ema50": float(ema50),
        "rsi14": float(rsi14),
        "bb_upper": float(bb_upper),
        "bb_lower": float(bb_lower),
        "atr14": float(atr14),
        "adr20": float(adr20)
    }


def compute_evidence_analysis(
    ticker: str,
    hist: List[Dict],
    price: float,
    volume_surge_ratio: float,
    event_type: str,
    days_to_event: int,
    backtest_data: Optional[Dict] = None
) -> Dict[str, Any]:
    """
    Compute evidence-first statistical tests and analysis.
    """
    evidence = {
        "tests": [],
        "multiple_testing": {"method": "BH_FDR", "q_values": []},
        "calibration": {"ece": 0.0, "brier": 0.0},
        "assumptions": {
            "stationarity_checked": False,
            "normality_checked": False,
            "hac_correction": True,
            "missing": []
        }
    }
    
    if not hist or len(hist) < 10:
        evidence["assumptions"]["missing"].append("insufficient_historical_data")
        return evidence
    
    closes = [h["close"] for h in hist]
    returns = [(closes[i] - closes[i-1]) / closes[i-1] for i in range(1, len(closes))]
    
    # Test 1: Volume surge significance (Mann-Whitney: recent vs historical)
    if len(hist) >= 30:
        recent_volumes = [h["volume"] for h in hist[-5:]]
        historical_volumes = [h["volume"] for h in hist[-30:-5]]
        
        if recent_volumes and historical_volumes:
            vol_test = mann_whitney_test(recent_volumes, historical_volumes)
            vol_test.hypothesis = f"Recent 5d volume > historical 25d volume (surge={volume_surge_ratio:.2f}x)"
            
            # Generate actionable interpretation using unified rules
            vol_decision = interpret_volume_test(
                p=vol_test.p_value,
                ci_low=vol_test.ci_low,
                ci_high=vol_test.ci_high,
                volume_surge_ratio=volume_surge_ratio
            )
            
            evidence["tests"].append({
                "name": vol_test.name,
                "hypothesis": vol_test.hypothesis,
                "effect_size": vol_test.effect_size,
                "p_value": vol_test.p_value,
                "ci_low": vol_test.ci_low,
                "ci_high": vol_test.ci_high,
                "notes": vol_test.notes,
                "decision_implication": vol_decision.rationale,
                "decision_label": vol_decision.label,
                "decision_color": vol_decision.color,
                "decision_severity": vol_decision.severity
            })
    
    # Test 2: Bootstrap CI for median return
    if len(returns) >= 20:
        median_r, ci_low, ci_high = bootstrap_ci(returns, np.median, n_bootstrap=1000)
        # Generate actionable interpretation using unified rules
        median_decision = interpret_median_return(median_r, ci_low, ci_high)
        
        evidence["tests"].append({
            "name": "bootstrap_median_r",
            "hypothesis": "Median return (95% CI)",
            "effect_size": median_r,
            "p_value": None,
            "ci_low": ci_low,
            "ci_high": ci_high,
            "notes": f"Median R: {median_r:.4f} [{ci_low:.4f}, {ci_high:.4f}]",
            "decision_implication": median_decision.rationale,
            "decision_label": median_decision.label,
            "decision_color": median_decision.color,
            "decision_severity": median_decision.severity
        })
    
    # Test 3: Hit rate test (if backtest data available)
    if backtest_data:
        wins = backtest_data.get("wins", 0)
        total = backtest_data.get("samples", 0)
        if total > 0:
            hit_rate_test = wilson_binomial_test(wins, total, baseline=0.5)
            hit_rate_test.hypothesis = f"Hit rate > 50% (observed: {wins}/{total})"
            
            # Generate actionable interpretation using unified rules
            hit_rate_decision = interpret_hit_rate_test(
                p=hit_rate_test.p_value,
                wins=wins,
                total=total
            )
            
            evidence["tests"].append({
                "name": hit_rate_test.name,
                "hypothesis": hit_rate_test.hypothesis,
                "effect_size": hit_rate_test.effect_size,
                "p_value": hit_rate_test.p_value,
                "ci_low": hit_rate_test.ci_low,
                "ci_high": hit_rate_test.ci_high,
                "notes": hit_rate_test.notes,
                "decision_implication": hit_rate_decision.rationale,
                "decision_label": hit_rate_decision.label,
                "decision_color": hit_rate_decision.color,
                "decision_severity": hit_rate_decision.severity
            })
    
    # FDR correction for multiple tests
    p_values = [t.get("p_value") for t in evidence["tests"] if t.get("p_value") is not None]
    if p_values:
        q_values = benjamini_hochberg_fdr(p_values, alpha=0.05)
        evidence["multiple_testing"]["q_values"] = [
            {
                "test": evidence["tests"][i].get("name", f"test_{i}"),
                "q": q,
                "badge": format_fdr_badge(q)[0],
                "badge_color": format_fdr_badge(q)[1]
            }
            for i, q in enumerate(q_values) if evidence["tests"][i].get("p_value") is not None
        ]
    
    # Calibration metrics (if we have predicted vs actual)
    # This would require historical LLM confidence vs outcomes - placeholder for now
    evidence["calibration"]["ece"] = 0.0
    evidence["calibration"]["brier"] = 0.0
    
    return evidence


def compute_room_to_run(
    hist: List[Dict],
    price: float,
    recent_high: float,
    recent_low: float,
    atr14: float,
    adr20: float,
    expected_move_iv: float
) -> Dict[str, Any]:
    """
    Compute room-to-run metrics with quantile regression and conformal prediction.
    """
    if not hist or len(hist) < 10:
        return {
            "intraday_room_up_pct": 0.0,
            "intraday_room_down_pct": 0.0,
            "swing_room_up_pct": 0.0,
            "swing_room_down_pct": 0.0,
            "explain": "Insufficient data"
        }
    
    distance_to_resistance = (recent_high - price) / price if recent_high > price else 0
    distance_to_support = (price - recent_low) / price if price > recent_low else 0
    
    # Intraday room (using ADR and ATR)
    intraday_room_up = max(distance_to_resistance, adr20 - abs(distance_to_resistance))
    intraday_room_down = distance_to_support
    
    # Swing room (1-5 day)
    swing_room_up = max(expected_move_iv, distance_to_resistance) if distance_to_resistance > 0 else expected_move_iv
    swing_room_down = max(expected_move_iv * 0.6, distance_to_support)
    
    # Quantile regression for prediction intervals
    closes = [h["close"] for h in hist]
    returns = [(closes[i] - closes[i-1]) / closes[i-1] for i in range(1, len(closes))]
    
    if len(returns) >= 10:
        quantiles = quantile_regression_room(returns, quantiles=[0.1, 0.5, 0.9])
        # Conformal prediction bands
        historical_errors = [r - np.median(returns) for r in returns[-30:]]
        if len(historical_errors) >= 10:
            conf_lower, conf_upper = conformal_prediction_band(historical_errors, coverage=0.9)
            explain = f"Room estimates: Intraday ±{adr20*100:.1f}%, Swing ±{expected_move_iv*100:.1f}%. Conformal bands: [{conf_lower*100:.1f}%, {conf_upper*100:.1f}%]"
        else:
            explain = f"Room estimates: Intraday ±{adr20*100:.1f}%, Swing ±{expected_move_iv*100:.1f}%"
    else:
        explain = f"Basic estimates: Intraday ±{adr20*100:.1f}%, Swing ±{expected_move_iv*100:.1f}%"
    
    return {
        "intraday_room_up_pct": float(intraday_room_up * 100),
        "intraday_room_down_pct": float(intraday_room_down * 100),
        "swing_room_up_pct": float(swing_room_up * 100),
        "swing_room_down_pct": float(swing_room_down * 100),
        "explain": explain
    }



