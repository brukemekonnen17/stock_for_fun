"""
Evidence-to-decision interpreter: single source of truth for actionable insights.
Maps statistical tests to consistent decision labels, colors, and rationales.
"""
from dataclasses import dataclass
from typing import Optional


@dataclass
class DecisionImplication:
    """Standardized decision implication from statistical test."""
    label: str        # "BUY" | "REACTIVE" | "SKIP" | "CONFIRM"
    color: str        # "green" | "yellow" | "red" | "blue"
    rationale: str
    severity: str = "medium"  # "high" | "medium" | "low"


def interpret_test(
    name: str,
    p: Optional[float],
    ci_low: Optional[float],
    ci_high: Optional[float],
    effect: Optional[float],
    test_specific_context: Optional[dict] = None
) -> DecisionImplication:
    """
    Interpret a statistical test result into a standardized decision implication.
    
    Args:
        name: Test name (e.g., "mann_whitney_u", "bootstrap_median_r")
        p: P-value (None if not applicable)
        ci_low: Lower bound of confidence interval
        ci_high: Upper bound of confidence interval
        effect: Effect size (if applicable)
        test_specific_context: Additional context (e.g., {"volume_surge_ratio": 1.5, "hit_rate": 0.0})
    
    Returns:
        DecisionImplication with label, color, rationale, severity
    """
    context = test_specific_context or {}
    
    # Edge case: Insufficient data
    if p is None and (ci_low is None or ci_high is None):
        return DecisionImplication(
            label="CONFIRM",
            color="blue",
            rationale="Insufficient evidence reported — require confirmation.",
            severity="low"
        )
    
    # Edge case: CI crosses zero (uncertain)
    if ci_low is not None and ci_high is not None:
        if ci_low <= 0 <= ci_high:
            return DecisionImplication(
                label="CONFIRM",
                color="yellow",
                rationale=f"{name}: CI crosses 0 [{ci_low:.3g}, {ci_high:.3g}] — evidence is weak, require pattern/volume confirmation.",
                severity="medium"
            )
    
    # Strong signal: Statistically significant AND non-overlapping CI away from 0
    if p is not None and p < 0.05:
        if ci_low is not None and ci_high is not None:
            # Check if CI is entirely positive or entirely negative
            if ci_low > 0 or ci_high < 0:
                # Strong directional signal
                effect_str = f", effect={effect:.3g}" if effect is not None else ""
                return DecisionImplication(
                    label="BUY" if (effect is None or effect > 0) else "SKIP",
                    color="green",
                    rationale=f"{name}: statistically significant (p={p:.3f}), effect={effect:.3g if effect is not None else 'N/A'}{effect_str}. Strong signal.",
                    severity="high"
                )
    
    # Weak signal: Not significant but directional effect
    if p is not None and p >= 0.05:
        if effect is not None and abs(effect) > 0.1:
            return DecisionImplication(
                label="REACTIVE",
                color="yellow",
                rationale=f"{name}: not significant (p={p:.3f}) but directional (effect={effect:.3g}) — react only on trigger/pattern confirmation.",
                severity="medium"
            )
    
    # No reliable edge
    return DecisionImplication(
        label="SKIP",
        color="red",
        rationale=f"{name}: no reliable edge (p={p:.3f if p is not None else 'N/A'}).",
        severity="high"
    )


def interpret_volume_test(
    p: Optional[float],
    ci_low: Optional[float],
    ci_high: Optional[float],
    volume_surge_ratio: float
) -> DecisionImplication:
    """Specialized interpretation for volume surge test."""
    if p is None:
        return DecisionImplication(
            label="CONFIRM",
            color="blue",
            rationale="Volume test incomplete. Cannot assess volume significance.",
            severity="low"
        )
    
    # Strong volume surge AND significant
    if p < 0.05:
        if volume_surge_ratio >= 2.0:
            return DecisionImplication(
                label="BUY",
                color="green",
                rationale=f"STRONG SIGNAL: Volume surge is statistically significant (p={p:.3f}), surge={volume_surge_ratio:.2f}x. High volume confirms price move. Consider BUY if pattern supports.",
                severity="high"
            )
        elif volume_surge_ratio >= 1.5:
            return DecisionImplication(
                label="BUY",
                color="green",
                rationale=f"MODERATE SIGNAL: Volume surge is significant (p={p:.3f}), surge={volume_surge_ratio:.2f}x. Moderate volume support. BUY if pattern aligns.",
                severity="medium"
            )
        else:
            return DecisionImplication(
                label="CONFIRM",
                color="yellow",
                rationale=f"WEAK SIGNAL: Volume surge is significant but magnitude is low (surge={volume_surge_ratio:.2f}x). Require pattern confirmation before trading.",
                severity="medium"
            )
    else:
        # Not statistically significant
        if volume_surge_ratio >= 2.0:
            return DecisionImplication(
                label="SKIP",
                color="red",
                rationale=f"DIVERGENT: High volume surge ({volume_surge_ratio:.2f}x) but NOT statistically significant (p≥{p:.3f}). This suggests noise or one-off event. SKIP unless pattern strongly confirms.",
                severity="high"
            )
        elif volume_surge_ratio >= 1.5:
            return DecisionImplication(
                label="CONFIRM",
                color="yellow",
                rationale=f"WEAK EVIDENCE: Moderate volume surge ({volume_surge_ratio:.2f}x) but NOT significant. Statistical evidence is weak. Require strong pattern confirmation.",
                severity="medium"
            )
        else:
            return DecisionImplication(
                label="SKIP",
                color="red",
                rationale=f"NO SIGNAL: Low volume surge ({volume_surge_ratio:.2f}x) and NOT statistically significant. No volume confirmation. SKIP this trade.",
                severity="high"
            )


def interpret_median_return(
    median_r: float,
    ci_low: float,
    ci_high: float
) -> DecisionImplication:
    """Specialized interpretation for median return bootstrap CI."""
    # CI includes zero (uncertain)
    if ci_low <= 0 <= ci_high:
        return DecisionImplication(
            label="CONFIRM",
            color="yellow",
            rationale=f"UNCERTAIN: Median return CI includes zero [{ci_low*100:.2f}%, {ci_high*100:.2f}%]. True median could be negative. Low confidence in positive returns.",
            severity="medium"
        )
    
    # Positive bias
    if median_r > 0.01:  # > 1%
        return DecisionImplication(
            label="BUY",
            color="green",
            rationale=f"POSITIVE BIAS: Median return is {median_r*100:.2f}% with 95% CI [{ci_low*100:.2f}%, {ci_high*100:.2f}%]. Historical bias is positive. Supports BUY.",
            severity="high"
        )
    elif median_r > 0:
        return DecisionImplication(
            label="REACTIVE",
            color="yellow",
            rationale=f"WEAK POSITIVE: Median return is small {median_r*100:.2f}% [{ci_low*100:.2f}%, {ci_high*100:.2f}%]. Marginal positive bias. Require pattern confirmation.",
            severity="medium"
        )
    else:
        return DecisionImplication(
            label="SKIP",
            color="red",
            rationale=f"NEGATIVE BIAS: Median return is {median_r*100:.2f}% [{ci_low*100:.2f}%, {ci_high*100:.2f}%]. Historical bias is negative. Consider SKIP or SELL.",
            severity="high"
        )


def interpret_hit_rate_test(
    p: Optional[float],
    wins: int,
    total: int
) -> DecisionImplication:
    """Specialized interpretation for hit rate (Wilson binomial) test."""
    hit_rate = wins / total if total > 0 else 0.0
    
    if p is None:
        return DecisionImplication(
            label="CONFIRM",
            color="blue",
            rationale="Hit rate test incomplete.",
            severity="low"
        )
    
    if total < 10:
        return DecisionImplication(
            label="CONFIRM",
            color="blue",
            rationale=f"INSUFFICIENT DATA: Only {total} samples. Need at least 10 trades for reliable hit rate. Cannot assess strategy performance.",
            severity="low"
        )
    
    if hit_rate == 0:
        return DecisionImplication(
            label="SKIP",
            color="red",
            rationale=f"CRITICAL: Hit rate is 0% ({wins}/{total}). Strategy has NEVER worked historically. SKIP this trade or drastically reduce position size.",
            severity="high"
        )
    
    if p < 0.05:
        # Statistically significant
        if hit_rate >= 0.6:
            return DecisionImplication(
                label="BUY",
                color="green",
                rationale=f"STRONG: Hit rate {hit_rate*100:.0f}% ({wins}/{total}) is significantly >50% (p={p:.3f}). Strategy has proven success. Supports BUY.",
                severity="high"
            )
        elif hit_rate >= 0.5:
            return DecisionImplication(
                label="BUY",
                color="green",
                rationale=f"POSITIVE: Hit rate {hit_rate*100:.0f}% ({wins}/{total}) is >50% and significant. Strategy works. Supports BUY.",
                severity="medium"
            )
        else:
            return DecisionImplication(
                label="SKIP",
                color="red",
                rationale=f"NEGATIVE: Hit rate {hit_rate*100:.0f}% ({wins}/{total}) is <50% but significant. Strategy underperforms. Consider SKIP.",
                severity="high"
            )
    else:
        # Not statistically significant
        if hit_rate >= 0.6:
            return DecisionImplication(
                label="CONFIRM",
                color="yellow",
                rationale=f"DIVERGENT: High hit rate {hit_rate*100:.0f}% but NOT statistically significant (p≥{p:.3f}). Sample may be too small. Require pattern confirmation.",
                severity="medium"
            )
        elif hit_rate >= 0.5:
            return DecisionImplication(
                label="CONFIRM",
                color="yellow",
                rationale=f"WEAK: Hit rate {hit_rate*100:.0f}% is >50% but NOT significant. Cannot conclude strategy works. Use pattern analysis.",
                severity="medium"
            )
        else:
            return DecisionImplication(
                label="SKIP",
                color="red",
                rationale=f"POOR: Hit rate {hit_rate*100:.0f}% ({wins}/{total}) is <50% and NOT significant. Strategy has no proven edge. SKIP.",
                severity="high"
            )


def format_fdr_badge(q_value: float) -> tuple[str, str]:
    """
    Format FDR q-value as a badge.
    
    Returns:
        (badge_text, color_class)
    """
    if q_value < 0.10:
        return ("q<0.10", "green")
    elif q_value < 0.20:
        return ("q<0.20", "yellow")
    else:
        return ("q≥0.20", "red")

