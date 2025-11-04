"""
Evidence-first statistical analysis module.
Provides rigorous statistical tests, uncertainty quantification, and causal inference.
"""
import numpy as np
from typing import List, Dict, Tuple, Optional, Any
from dataclasses import dataclass
from scipy import stats
import logging

logger = logging.getLogger(__name__)

@dataclass
class StatisticalTest:
    """Result of a statistical test with effect size and uncertainty."""
    name: str
    hypothesis: str
    effect_size: Optional[float] = None
    p_value: Optional[float] = None
    ci_low: Optional[float] = None
    ci_high: Optional[float] = None
    notes: str = ""


def bootstrap_ci(
    data: List[float],
    statistic_func: callable = np.median,
    n_bootstrap: int = 1000,
    confidence: float = 0.95,
    seed: Optional[int] = None
) -> Tuple[float, float, float]:
    """
    Bootstrap confidence interval for any statistic.
    
    Returns:
        (statistic, ci_low, ci_high)
    """
    if len(data) < 10:
        logger.warning(f"Bootstrap CI: insufficient data ({len(data)} samples)")
        stat = statistic_func(data)
        return stat, stat, stat
    
    np.random.seed(seed)
    n = len(data)
    bootstrap_stats = []
    
    for _ in range(n_bootstrap):
        sample = np.random.choice(data, size=n, replace=True)
        bootstrap_stats.append(statistic_func(sample))
    
    bootstrap_stats = np.array(bootstrap_stats)
    stat = statistic_func(data)
    alpha = 1 - confidence
    ci_low = np.percentile(bootstrap_stats, 100 * alpha / 2)
    ci_high = np.percentile(bootstrap_stats, 100 * (1 - alpha / 2))
    
    return stat, ci_low, ci_high


def mann_whitney_test(
    group1: List[float],
    group2: List[float],
    alternative: str = "two-sided"
) -> StatisticalTest:
    """
    Mann-Whitney U test (non-parametric comparison of two groups).
    
    Returns effect size (Cliff's delta approximation) and p-value.
    """
    if len(group1) < 3 or len(group2) < 3:
        return StatisticalTest(
            name="mann_whitney_u",
            hypothesis="Group1 median != Group2 median",
            notes="Insufficient sample size"
        )
    
    try:
        u_stat, p_value = stats.mannwhitneyu(group1, group2, alternative=alternative)
        
        # Cliff's delta approximation
        n1, n2 = len(group1), len(group2)
        rank1 = stats.rankdata(group1)
        rank2 = stats.rankdata(group2)
        u1 = u_stat
        u2 = n1 * n2 - u1
        delta = (u2 - u1) / (n1 * n2)  # Approximate Cliff's delta
        
        # Approximate CI using normal approximation
        se = np.sqrt((n1 + n2 + 1) / 12)
        z_crit = stats.norm.ppf(0.975)
        ci_low = delta - z_crit * se
        ci_high = delta + z_crit * se
        
        return StatisticalTest(
            name="mann_whitney_u",
            hypothesis=f"Group1 median != Group2 median (n1={n1}, n2={n2})",
            effect_size=delta,
            p_value=float(p_value),
            ci_low=float(ci_low),
            ci_high=float(ci_high),
            notes=f"U-statistic: {u_stat:.2f}"
        )
    except Exception as e:
        logger.error(f"Mann-Whitney test failed: {e}")
        return StatisticalTest(
            name="mann_whitney_u",
            hypothesis="Group1 median != Group2 median",
            notes=f"Test failed: {str(e)}"
        )


def wilson_binomial_test(
    successes: int,
    trials: int,
    baseline: float = 0.5,
    confidence: float = 0.95
) -> StatisticalTest:
    """
    Wilson score interval for binomial proportion (hit rate).
    Tests if hit rate > baseline.
    """
    if trials == 0:
        return StatisticalTest(
            name="wilson_binomial",
            hypothesis=f"Hit rate > {baseline}",
            notes="No trials"
        )
    
    p_hat = successes / trials if trials > 0 else 0
    z = stats.norm.ppf((1 + confidence) / 2)
    
    # Wilson score interval
    denominator = 1 + (z**2 / trials)
    center = (p_hat + z**2 / (2 * trials)) / denominator
    margin = z * np.sqrt((p_hat * (1 - p_hat) + z**2 / (4 * trials)) / trials) / denominator
    
    ci_low = max(0, center - margin)
    ci_high = min(1, center + margin)
    
    # Test against baseline
    z_test = (p_hat - baseline) / np.sqrt(baseline * (1 - baseline) / trials) if trials > 0 else 0
    p_value = 1 - stats.norm.cdf(z_test)  # One-sided: p_hat > baseline
    
    return StatisticalTest(
        name="wilson_binomial",
        hypothesis=f"Hit rate > {baseline}",
        effect_size=p_hat - baseline,
        p_value=float(p_value),
        ci_low=float(ci_low),
        ci_high=float(ci_high),
        notes=f"Observed: {successes}/{trials} = {p_hat:.3f}"
    )


def benjamini_hochberg_fdr(p_values: List[float], alpha: float = 0.05) -> List[Dict[str, Any]]:
    """
    Benjamini-Hochberg FDR correction for multiple testing.
    
    Returns list of {"test": str, "q": float} for each test.
    """
    if not p_values:
        return []
    
    m = len(p_values)
    sorted_p = sorted(enumerate(p_values), key=lambda x: x[1])
    q_values = []
    
    for rank, (idx, p_val) in enumerate(sorted_p, start=1):
        q = p_val * m / rank
        q_values.append((idx, q))
    
    # Adjust q-values to be monotonic
    q_values.sort(key=lambda x: x[0])
    for i in range(len(q_values) - 2, -1, -1):
        q_values[i] = (q_values[i][0], min(q_values[i][1], q_values[i+1][1]))
    
    return [
        {"test": f"test_{i}", "q": float(q)}
        for i, q in q_values
    ]


def event_study_car(
    returns: List[float],
    market_returns: List[float],
    event_window: Tuple[int, int] = (-5, 5),
    estimation_window: int = 60,
    confidence: float = 0.95
) -> StatisticalTest:
    """
    Event study: Cumulative Abnormal Returns (CAR) with market adjustment.
    
    Args:
        returns: Stock returns (aligned with market_returns)
        market_returns: Market/index returns
        event_window: (days_before, days_after) relative to event
        estimation_window: Days to estimate market model
        confidence: Confidence level for CI
    
    Returns:
        StatisticalTest with CAR, p-value, and CI
    """
    if len(returns) < estimation_window + max(abs(event_window[0]), abs(event_window[1])):
        return StatisticalTest(
            name="event_study",
            hypothesis="Cumulative Abnormal Return != 0",
            notes="Insufficient data for event study"
        )
    
    try:
        # Estimate market model (before event)
        est_returns = returns[:estimation_window]
        est_market = market_returns[:estimation_window]
        
        # Simple market model: r_stock = alpha + beta * r_market + epsilon
        if len(est_returns) < 10:
            return StatisticalTest(
                name="event_study",
                hypothesis="CAR != 0",
                notes="Insufficient estimation window"
            )
        
        beta, alpha, r_value, p_value_reg, std_err = stats.linregress(est_market, est_returns)
        expected_returns = [alpha + beta * r for r in est_market]
        residuals = [est_returns[i] - expected_returns[i] for i in range(len(est_returns))]
        sigma = np.std(residuals)
        
        # Calculate abnormal returns in event window
        event_start = estimation_window + event_window[0]
        event_end = estimation_window + event_window[1] + 1
        abnormal_returns = []
        
        for i in range(max(0, event_start), min(len(returns), event_end)):
            if i < len(market_returns):
                expected = alpha + beta * market_returns[i]
                abnormal = returns[i] - expected
                abnormal_returns.append(abnormal)
        
        if not abnormal_returns:
            return StatisticalTest(
                name="event_study",
                hypothesis="CAR != 0",
                notes="No abnormal returns in event window"
            )
        
        car = sum(abnormal_returns)
        car_variance = len(abnormal_returns) * (sigma ** 2)
        car_std = np.sqrt(car_variance)
        
        # Test if CAR != 0
        z_stat = car / car_std if car_std > 0 else 0
        p_value = 2 * (1 - stats.norm.cdf(abs(z_stat)))  # Two-sided
        
        # CI
        z_crit = stats.norm.ppf((1 + confidence) / 2)
        ci_low = car - z_crit * car_std
        ci_high = car + z_crit * car_std
        
        return StatisticalTest(
            name="event_study",
            hypothesis=f"CAR({event_window[0]}, {event_window[1]}) != 0",
            effect_size=car,
            p_value=float(p_value),
            ci_low=float(ci_low),
            ci_high=float(ci_high),
            notes=f"Market model: alpha={alpha:.4f}, beta={beta:.4f}, R²={r_value**2:.3f}"
        )
    except Exception as e:
        logger.error(f"Event study failed: {e}", exc_info=True)
        return StatisticalTest(
            name="event_study",
            hypothesis="CAR != 0",
            notes=f"Event study error: {str(e)}"
        )


def quantile_regression_room(
    returns: List[float],
    features: Optional[List[List[float]]] = None,
    quantiles: List[float] = [0.1, 0.5, 0.9]
) -> Dict[str, float]:
    """
    Quantile regression for room-to-run prediction.
    
    Returns:
        Dict mapping quantile -> expected_move
    """
    if len(returns) < 10:
        # Fallback: use empirical quantiles
        return {
            f"p{int(q*100)}": float(np.percentile(returns, q * 100))
            for q in quantiles
        }
    
    # Simple empirical quantiles (can be enhanced with linear quantile regression)
    result = {}
    for q in quantiles:
        result[f"p{int(q*100)}"] = float(np.percentile(returns, q * 100))
    
    return result


def calibration_metrics(
    predicted_probs: List[float],
    actual_outcomes: List[int]
) -> Dict[str, float]:
    """
    Calculate calibration metrics: ECE (Expected Calibration Error) and Brier score.
    
    Args:
        predicted_probs: Predicted probabilities (0-1)
        actual_outcomes: Binary outcomes (0 or 1)
    
    Returns:
        Dict with 'ece' and 'brier'
    """
    if len(predicted_probs) != len(actual_outcomes) or len(predicted_probs) == 0:
        return {"ece": 0.0, "brier": 0.0}
    
    # Brier score
    brier = np.mean([(p - a) ** 2 for p, a in zip(predicted_probs, actual_outcomes)])
    
    # ECE: bin probabilities and compare to observed frequency
    n_bins = min(10, len(predicted_probs) // 5)
    if n_bins < 2:
        return {"ece": 0.0, "brier": float(brier)}
    
    bin_edges = np.linspace(0, 1, n_bins + 1)
    ece = 0.0
    total_weight = 0.0
    
    for i in range(n_bins):
        bin_mask = (np.array(predicted_probs) >= bin_edges[i]) & (np.array(predicted_probs) < bin_edges[i+1])
        if i == n_bins - 1:  # Include upper bound for last bin
            bin_mask = (np.array(predicted_probs) >= bin_edges[i]) & (np.array(predicted_probs) <= bin_edges[i+1])
        
        if np.sum(bin_mask) > 0:
            bin_probs = np.array(predicted_probs)[bin_mask]
            bin_outcomes = np.array(actual_outcomes)[bin_mask]
            bin_weight = len(bin_probs)
            bin_accuracy = np.mean(bin_outcomes)
            bin_confidence = np.mean(bin_probs)
            
            ece += bin_weight * abs(bin_accuracy - bin_confidence)
            total_weight += bin_weight
    
    ece = ece / total_weight if total_weight > 0 else 0.0
    
    return {
        "ece": float(ece),
        "brier": float(brier)
    }


def conformal_prediction_band(
    historical_errors: List[float],
    coverage: float = 0.9
) -> Tuple[float, float]:
    """
    Conformal prediction: distribution-free prediction intervals.
    
    Returns:
        (lower_bound, upper_bound) for prediction error
    """
    if len(historical_errors) < 10:
        # Fallback: use empirical quantiles
        alpha = 1 - coverage
        lower = np.percentile(historical_errors, 100 * alpha / 2)
        upper = np.percentile(historical_errors, 100 * (1 - alpha / 2))
        return float(lower), float(upper)
    
    # Conformal: use (1-coverage) quantile of residuals
    alpha = 1 - coverage
    quantile = np.percentile(np.abs(historical_errors), 100 * (1 - alpha))
    
    return float(-quantile), float(quantile)


def compute_effect_size_grade(p_value: Optional[float], effect_size: Optional[float]) -> str:
    """
    Convert p-value and effect size to evidence grade (A/B/C).
    """
    if p_value is None or effect_size is None:
        return "C"
    
    if p_value < 0.01 and abs(effect_size) > 0.3:
        return "A"
    elif p_value < 0.05 and abs(effect_size) > 0.1:
        return "B"
    else:
        return "C"


def format_significance_badge(p_value: Optional[float]) -> str:
    """
    Format p-value as significance badge (*, **, ***).
    """
    if p_value is None:
        return ""
    if p_value < 0.001:
        return "***"
    elif p_value < 0.01:
        return "**"
    elif p_value < 0.05:
        return "*"
    else:
        return "ns"

