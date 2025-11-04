"""
Technical pattern detection for trading analysis.
Identifies common chart patterns: ABCD, Head & Shoulders, Triangles, Flags, etc.
"""
import numpy as np
from typing import Dict, List, Optional, Tuple, Any
import logging

logger = logging.getLogger(__name__)


def detect_patterns(hist: List[Dict], price: float) -> Dict[str, Any]:
    """
    Detect common technical chart patterns from historical price data.
    
    Returns:
        Dict with detected patterns, their characteristics, and trading implications.
    """
    if not hist or len(hist) < 20:
        return {
            "patterns": [],
            "primary_pattern": None,
            "pattern_confidence": 0.0,
            "trading_implications": []
        }
    
    closes = [h["close"] for h in hist]
    highs = [h["high"] for h in hist]
    lows = [h["low"] for h in hist]
    volumes = [h.get("volume", 0) for h in hist]
    
    patterns = []
    
    # Detect ABCD Pattern
    abcd = _detect_abcd_pattern(closes, highs, lows)
    if abcd:
        patterns.append(abcd)
    
    # Detect Head & Shoulders
    hns = _detect_head_shoulders(closes, highs)
    if hns:
        patterns.append(hns)
    
    # Detect Inverse Head & Shoulders
    ihns = _detect_inverse_head_shoulders(closes, lows)
    if ihns:
        patterns.append(ihns)
    
    # Detect Triangles (Ascending, Descending, Symmetrical)
    triangles = _detect_triangles(closes, highs, lows)
    patterns.extend(triangles)
    
    # Detect Flags & Pennants
    flags = _detect_flags_pennants(closes, highs, lows, volumes)
    patterns.extend(flags)
    
    # Detect Double Tops/Bottoms
    double_tops = _detect_double_tops(closes, highs)
    patterns.extend(double_tops)
    
    double_bottoms = _detect_double_bottoms(closes, lows)
    patterns.extend(double_bottoms)
    
    # Detect Wedges (Rising, Falling)
    wedges = _detect_wedges(closes, highs, lows)
    patterns.extend(wedges)
    
    # Select primary pattern (highest confidence)
    primary_pattern = None
    if patterns:
        primary_pattern = max(patterns, key=lambda p: p.get("confidence", 0.0))
    
    # Generate trading implications
    trading_implications = _generate_trading_implications(patterns, price, closes[-1])
    
    return {
        "patterns": patterns,
        "primary_pattern": primary_pattern,
        "pattern_confidence": primary_pattern["confidence"] if primary_pattern else 0.0,
        "trading_implications": trading_implications
    }


def _detect_abcd_pattern(closes: List[float], highs: List[float], lows: List[float]) -> Optional[Dict]:
    """
    Detect ABCD (Harmonic) pattern.
    AB = CD, with Fibonacci retracements.
    """
    if len(closes) < 20:
        return None
    
    # Look for swing points
    swing_highs = []
    swing_lows = []
    
    for i in range(2, len(highs) - 2):
        if highs[i] > highs[i-1] and highs[i] > highs[i+1] and highs[i] > highs[i-2] and highs[i] > highs[i+2]:
            swing_highs.append((i, highs[i]))
        if lows[i] < lows[i-1] and lows[i] < lows[i+1] and lows[i] < lows[i-2] and lows[i] < lows[i+2]:
            swing_lows.append((i, lows[i]))
    
    if len(swing_highs) < 2 or len(swing_lows) < 2:
        return None
    
    # Look for ABCD structure: A (high) -> B (low) -> C (high) -> D (low)
    # Or: A (low) -> B (high) -> C (low) -> D (high) for bullish
    for i in range(len(swing_highs) - 1):
        for j in range(len(swing_lows) - 1):
            # Check if we have A->B->C->D sequence
            if swing_highs[i][0] < swing_lows[j][0] < swing_highs[i+1][0] < swing_lows[j+1][0]:
                A = swing_highs[i][1]
                B = swing_lows[j][1]
                C = swing_highs[i+1][1]
                D = swing_lows[j+1][1]
                
                # Check AB = CD ratio (0.618 to 1.618 is harmonic)
                AB = abs(A - B)
                BC = abs(C - B)
                CD = abs(C - D)
                
                if AB > 0 and CD > 0:
                    ratio = CD / AB
                    if 0.618 <= ratio <= 1.618:
                        # Check if D is near 0.618 or 0.786 retracement of BC
                        bc_retrace = abs(D - B) / BC if BC > 0 else 0
                        if 0.618 <= bc_retrace <= 0.786:
                            return {
                                "name": "ABCD_Bullish",
                                "type": "BULLISH",
                                "confidence": min(0.85, 0.5 + (abs(ratio - 1.0) < 0.1) * 0.35),
                                "points": {"A": A, "B": B, "C": C, "D": D},
                                "target": C + (C - B),
                                "stop": D * 0.98,
                                "description": "Bullish ABCD pattern detected. D point suggests potential reversal to upside."
                            }
    
    return None


def _detect_head_shoulders(closes: List[float], highs: List[float]) -> Optional[Dict]:
    """Detect Head & Shoulders pattern (bearish reversal)."""
    if len(highs) < 15:
        return None
    
    # Find three peaks: left shoulder, head, right shoulder
    peaks = []
    for i in range(2, len(highs) - 2):
        if highs[i] > highs[i-1] and highs[i] > highs[i+1]:
            peaks.append((i, highs[i]))
    
    if len(peaks) < 3:
        return None
    
    # Look for H&S: left shoulder, head (highest), right shoulder (lower)
    for i in range(len(peaks) - 2):
        ls_idx, ls_high = peaks[i]
        head_idx, head_high = peaks[i+1]
        rs_idx, rs_high = peaks[i+2]
        
        # Head should be highest
        if head_high > ls_high and head_high > rs_high:
            # Shoulders should be roughly equal
            shoulder_diff = abs(ls_high - rs_high) / max(ls_high, rs_high)
            if shoulder_diff < 0.05:  # Within 5%
                # Neckline (trough between shoulders and head)
                neckline = min(closes[ls_idx:head_idx] + closes[head_idx:rs_idx])
                if neckline < head_high * 0.95:
                    target = neckline - (head_high - neckline)
                    return {
                        "name": "Head_Shoulders",
                        "type": "BEARISH",
                        "confidence": 0.75,
                        "points": {
                            "left_shoulder": ls_high,
                            "head": head_high,
                            "right_shoulder": rs_high,
                            "neckline": neckline
                        },
                        "target": target,
                        "stop": head_high * 1.02,
                        "description": "Head & Shoulders pattern detected. Bearish reversal signal."
                    }
    
    return None


def _detect_inverse_head_shoulders(closes: List[float], lows: List[float]) -> Optional[Dict]:
    """Detect Inverse Head & Shoulders pattern (bullish reversal)."""
    if len(lows) < 15:
        return None
    
    # Find three troughs: left shoulder, head, right shoulder
    troughs = []
    for i in range(2, len(lows) - 2):
        if lows[i] < lows[i-1] and lows[i] < lows[i+1]:
            troughs.append((i, lows[i]))
    
    if len(troughs) < 3:
        return None
    
    # Look for inverse H&S: left shoulder, head (lowest), right shoulder (higher)
    for i in range(len(troughs) - 2):
        ls_idx, ls_low = troughs[i]
        head_idx, head_low = troughs[i+1]
        rs_idx, rs_low = troughs[i+2]
        
        # Head should be lowest
        if head_low < ls_low and head_low < rs_low:
            # Shoulders should be roughly equal
            shoulder_diff = abs(ls_low - rs_low) / max(ls_low, rs_low) if max(ls_low, rs_low) > 0 else 1.0
            if shoulder_diff < 0.05:
                # Neckline (peak between shoulders and head)
                neckline = max(closes[ls_idx:head_idx] + closes[head_idx:rs_idx])
                if neckline > head_low * 1.05:
                    target = neckline + (neckline - head_low)
                    return {
                        "name": "Inverse_Head_Shoulders",
                        "type": "BULLISH",
                        "confidence": 0.75,
                        "points": {
                            "left_shoulder": ls_low,
                            "head": head_low,
                            "right_shoulder": rs_low,
                            "neckline": neckline
                        },
                        "target": target,
                        "stop": head_low * 0.98,
                        "description": "Inverse Head & Shoulders pattern detected. Bullish reversal signal."
                    }
    
    return None


def _detect_triangles(closes: List[float], highs: List[float], lows: List[float]) -> List[Dict]:
    """Detect triangle patterns (ascending, descending, symmetrical)."""
    patterns = []
    if len(closes) < 20:
        return patterns
    
    # Look for converging trendlines
    recent_highs = highs[-20:]
    recent_lows = lows[-20:]
    
    # Calculate trendline slopes
    high_trend = np.polyfit(range(len(recent_highs)), recent_highs, 1)[0]
    low_trend = np.polyfit(range(len(recent_lows)), recent_lows, 1)[0]
    
    # Ascending triangle: horizontal resistance, rising support
    if abs(high_trend) < 0.001 and low_trend > 0.001:
        patterns.append({
            "name": "Ascending_Triangle",
            "type": "BULLISH",
            "confidence": 0.70,
            "resistance": max(recent_highs),
            "support_trend": "rising",
            "target": max(recent_highs) * 1.05,
            "stop": min(recent_lows) * 0.98,
            "description": "Ascending triangle: horizontal resistance with rising support. Bullish breakout expected."
        })
    
    # Descending triangle: falling resistance, horizontal support
    elif high_trend < -0.001 and abs(low_trend) < 0.001:
        patterns.append({
            "name": "Descending_Triangle",
            "type": "BEARISH",
            "confidence": 0.70,
            "resistance_trend": "falling",
            "support": min(recent_lows),
            "target": min(recent_lows) * 0.95,
            "stop": max(recent_highs) * 1.02,
            "description": "Descending triangle: falling resistance with horizontal support. Bearish breakdown expected."
        })
    
    # Symmetrical triangle: converging trendlines
    elif abs(high_trend) > 0.001 and abs(low_trend) > 0.001 and np.sign(high_trend) != np.sign(low_trend):
        patterns.append({
            "name": "Symmetrical_Triangle",
            "type": "NEUTRAL",
            "confidence": 0.65,
            "convergence": "both",
            "target": closes[-1] * (1 + abs(high_trend - low_trend) * 10),
            "stop": closes[-1] * (1 - abs(high_trend - low_trend) * 10),
            "description": "Symmetrical triangle: converging trendlines. Wait for breakout direction."
        })
    
    return patterns


def _detect_flags_pennants(closes: List[float], highs: List[float], lows: List[float], volumes: List[float]) -> List[Dict]:
    """Detect flag and pennant patterns (continuation patterns)."""
    patterns = []
    if len(closes) < 15:
        return patterns
    
    # Look for strong move followed by consolidation
    recent_closes = closes[-15:]
    recent_volumes = volumes[-15:] if len(volumes) >= 15 else []
    
    # Check for initial surge (pole)
    if len(recent_closes) >= 10:
        pole_move = (recent_closes[0] - recent_closes[5]) / recent_closes[5] if recent_closes[5] > 0 else 0
        consolidation_range = (max(recent_closes[-5:]) - min(recent_closes[-5:])) / recent_closes[-5] if recent_closes[-5] > 0 else 0
        
        # Flag: consolidation after strong move
        if abs(pole_move) > 0.05 and consolidation_range < 0.03:
            is_bullish = pole_move > 0
            patterns.append({
                "name": "Bull_Flag" if is_bullish else "Bear_Flag",
                "type": "BULLISH" if is_bullish else "BEARISH",
                "confidence": 0.68,
                "pole_move_pct": pole_move * 100,
                "target": recent_closes[-1] * (1 + pole_move * 0.618),  # 61.8% retracement target
                "stop": min(recent_closes[-5:]) * 0.98 if is_bullish else max(recent_closes[-5:]) * 1.02,
                "description": f"{'Bull' if is_bullish else 'Bear'} flag: continuation pattern. Expect move to continue in pole direction."
            })
    
    return patterns


def _detect_double_tops(closes: List[float], highs: List[float]) -> List[Dict]:
    """Detect double top pattern (bearish reversal)."""
    patterns = []
    if len(highs) < 10:
        return patterns
    
    # Find two similar peaks
    peaks = []
    for i in range(2, len(highs) - 2):
        if highs[i] > highs[i-1] and highs[i] > highs[i+1]:
            peaks.append((i, highs[i]))
    
    if len(peaks) < 2:
        return patterns
    
    # Look for double top
    for i in range(len(peaks) - 1):
        p1_idx, p1_high = peaks[i]
        p2_idx, p2_high = peaks[i+1]
        
        # Peaks should be similar (within 2%)
        if abs(p1_high - p2_high) / max(p1_high, p2_high) < 0.02:
            # Trough between peaks
            trough = min(closes[p1_idx:p2_idx])
            if trough < p1_high * 0.95:
                target = trough - (p1_high - trough)
                patterns.append({
                    "name": "Double_Top",
                    "type": "BEARISH",
                    "confidence": 0.72,
                    "resistance": p1_high,
                    "trough": trough,
                    "target": target,
                    "stop": p1_high * 1.02,
                    "description": "Double top pattern: bearish reversal signal. Two failed attempts to break resistance."
                })
    
    return patterns


def _detect_double_bottoms(closes: List[float], lows: List[float]) -> List[Dict]:
    """Detect double bottom pattern (bullish reversal)."""
    patterns = []
    if len(lows) < 10:
        return patterns
    
    # Find two similar troughs
    troughs = []
    for i in range(2, len(lows) - 2):
        if lows[i] < lows[i-1] and lows[i] < lows[i+1]:
            troughs.append((i, lows[i]))
    
    if len(troughs) < 2:
        return patterns
    
    # Look for double bottom
    for i in range(len(troughs) - 1):
        t1_idx, t1_low = troughs[i]
        t2_idx, t2_low = troughs[i+1]
        
        # Troughs should be similar (within 2%)
        if abs(t1_low - t2_low) / max(t1_low, t2_low) < 0.02:
            # Peak between troughs
            peak = max(closes[t1_idx:t2_idx])
            if peak > t1_low * 1.05:
                target = peak + (peak - t1_low)
                patterns.append({
                    "name": "Double_Bottom",
                    "type": "BULLISH",
                    "confidence": 0.72,
                    "support": t1_low,
                    "peak": peak,
                    "target": target,
                    "stop": t1_low * 0.98,
                    "description": "Double bottom pattern: bullish reversal signal. Two successful bounces off support."
                })
    
    return patterns


def _detect_wedges(closes: List[float], highs: List[float], lows: List[float]) -> List[Dict]:
    """Detect rising/falling wedge patterns."""
    patterns = []
    if len(closes) < 20:
        return patterns
    
    recent_highs = highs[-20:]
    recent_lows = lows[-20:]
    
    high_trend = np.polyfit(range(len(recent_highs)), recent_highs, 1)[0]
    low_trend = np.polyfit(range(len(recent_lows)), recent_lows, 1)[0]
    
    # Rising wedge: both trendlines rising, but converging
    if high_trend > 0 and low_trend > 0 and high_trend < low_trend:
        patterns.append({
            "name": "Rising_Wedge",
            "type": "BEARISH",
            "confidence": 0.68,
            "target": min(recent_lows) * 0.95,
            "stop": max(recent_highs) * 1.02,
            "description": "Rising wedge: bearish reversal pattern. Price making higher highs and higher lows, but momentum weakening."
        })
    
    # Falling wedge: both trendlines falling, but converging
    elif high_trend < 0 and low_trend < 0 and abs(high_trend) < abs(low_trend):
        patterns.append({
            "name": "Falling_Wedge",
            "type": "BULLISH",
            "confidence": 0.68,
            "target": max(recent_highs) * 1.05,
            "stop": min(recent_lows) * 0.98,
            "description": "Falling wedge: bullish reversal pattern. Price making lower highs and lower lows, but selling pressure weakening."
        })
    
    return patterns


def _generate_trading_implications(patterns: List[Dict], current_price: float, last_close: float) -> List[str]:
    """Generate actionable trading implications from detected patterns."""
    implications = []
    
    if not patterns:
        implications.append("No clear chart patterns detected. Rely on other signals (volume, catalysts, sentiment).")
        return implications
    
    primary = max(patterns, key=lambda p: p.get("confidence", 0.0)) if patterns else None
    
    if primary:
        ptype = primary.get("type", "NEUTRAL")
        name = primary.get("name", "")
        confidence = primary.get("confidence", 0.0)
        
        if ptype == "BULLISH" and confidence > 0.65:
            target = primary.get("target", current_price * 1.05)
            stop = primary.get("stop", current_price * 0.95)
            implications.append(f"🔵 {name}: Bullish pattern detected ({confidence*100:.0f}% confidence). Target: ${target:.2f}, Stop: ${stop:.2f}")
            implications.append(f"   → Entry: Consider BUY on confirmation (breakout above {primary.get('points', {}).get('neckline', current_price * 1.02):.2f})")
        
        elif ptype == "BEARISH" and confidence > 0.65:
            target = primary.get("target", current_price * 0.95)
            stop = primary.get("stop", current_price * 1.05)
            implications.append(f"🔴 {name}: Bearish pattern detected ({confidence*100:.0f}% confidence). Target: ${target:.2f}, Stop: ${stop:.2f}")
            implications.append(f"   → Entry: Consider SELL/SHORT on confirmation (breakdown below {primary.get('points', {}).get('neckline', current_price * 0.98):.2f})")
        
        elif ptype == "NEUTRAL":
            implications.append(f"⚠️ {name}: Neutral pattern. Wait for breakout direction before taking action.")
    
    # Multiple patterns
    if len(patterns) > 1:
        bullish_count = sum(1 for p in patterns if p.get("type") == "BULLISH")
        bearish_count = sum(1 for p in patterns if p.get("type") == "BEARISH")
        
        if bullish_count > bearish_count:
            implications.append(f"📊 Multiple patterns ({bullish_count} bullish, {bearish_count} bearish): Overall bias is BULLISH")
        elif bearish_count > bullish_count:
            implications.append(f"📊 Multiple patterns ({bullish_count} bullish, {bearish_count} bearish): Overall bias is BEARISH")
        else:
            implications.append(f"📊 Mixed signals: {len(patterns)} patterns detected with conflicting signals. Wait for confirmation.")
    
    return implications

