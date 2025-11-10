"""
Ship-Blocker #4: Economics & Capacity Realism Tests

Tests to ensure that trading economics are realistic:
1. Spread proxy when quotes missing: clip(10000*(high-low)/close/π, 3, 50)
2. Enforce %ADV gate
3. Net median > 0 to allow BUY
"""

import pytest
import numpy as np
import pandas as pd
from typing import Dict
import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))


def calculate_spread_proxy_bps(high: float, low: float, close: float) -> float:
    """
    Calculate spread proxy in basis points when bid/ask quotes are missing.
    
    Formula: spread_bps = clip(10000 * (high - low) / close / π, 3, 50)
    
    Rationale:
    - (high - low) approximates intraday range
    - Divide by π ≈ 3.14159 to estimate typical spread from range
    - Multiply by 10000 to get basis points
    - Clip to [3, 50] bps for realistic bounds
    """
    if close <= 0 or high <= 0 or low <= 0:
        return 50.0  # Max penalty for invalid data
    
    spread_bps = 10000 * (high - low) / close / np.pi
    spread_bps = np.clip(spread_bps, 3.0, 50.0)
    
    return spread_bps


def calculate_adv_gate(adv_shares: float, avg_price: float, position_size_usd: float, max_pct_adv: float = 0.05) -> Dict:
    """
    Calculate %ADV gate.
    
    Args:
        adv_shares: Average daily volume (shares)
        avg_price: Average price
        position_size_usd: Desired position size in USD
        max_pct_adv: Maximum % of ADV (default 5%)
    
    Returns:
        Dict with gate status and details
    """
    if adv_shares <= 0 or avg_price <= 0:
        return {
            "adv_ok": False,
            "reason": "Invalid ADV or price",
            "adv_usd": 0,
            "max_position_usd": 0,
            "pct_adv": 0
        }
    
    adv_usd = adv_shares * avg_price
    max_position_usd = adv_usd * max_pct_adv
    
    if position_size_usd <= max_position_usd:
        adv_ok = True
        reason = f"Position {position_size_usd:,.0f} ≤ {max_pct_adv:.0%} ADV ({max_position_usd:,.0f})"
    else:
        adv_ok = False
        pct_used = position_size_usd / adv_usd
        reason = f"Position {position_size_usd:,.0f} exceeds {max_pct_adv:.0%} ADV (would use {pct_used:.1%})"
    
    return {
        "adv_ok": adv_ok,
        "reason": reason,
        "adv_usd": adv_usd,
        "max_position_usd": max_position_usd,
        "pct_adv": position_size_usd / adv_usd if adv_usd > 0 else 0
    }


def economics_gate(median_return: float, adv_gate_result: Dict) -> Dict:
    """
    Combined economics gate.
    
    BUY is only allowed if:
    1. Median net return > 0
    2. ADV gate passes
    """
    reasons = []
    
    # Check median return
    if median_return <= 0:
        reasons.append(f"Median return {median_return:.2%} ≤ 0 (not profitable)")
    
    # Check ADV gate
    if not adv_gate_result["adv_ok"]:
        reasons.append(adv_gate_result["reason"])
    
    gate_passed = (median_return > 0 and adv_gate_result["adv_ok"])
    
    return {
        "passed": gate_passed,
        "verdict": "PASS" if gate_passed else "FAIL",
        "reasons": reasons
    }


class TestEconomicsGates:
    """Test suite for economics and capacity gates."""
    
    def test_buy_blocked_when_net_median_leq_0(self):
        """
        Critical test: BUY should be blocked when median net return ≤ 0.
        
        Even with great signal, if costs eat returns, don't trade.
        """
        # Scenario: Signal looks good, but costs are too high
        median_return = -0.002  # -0.2% after costs
        
        # ADV gate passes
        adv_result = calculate_adv_gate(
            adv_shares=1_000_000,
            avg_price=100,
            position_size_usd=1_000_000,  # $1M position, 1% of ADV
            max_pct_adv=0.05
        )
        
        assert adv_result["adv_ok"], "ADV gate should pass"
        
        # Economics gate should fail
        gate = economics_gate(median_return, adv_result)
        
        assert not gate["passed"], "Economics gate should FAIL when median ≤ 0"
        assert gate["verdict"] == "FAIL"
        assert any("not profitable" in r.lower() for r in gate["reasons"])
        
        print(f"\n✅ BUY correctly blocked:")
        print(f"   Median return: {median_return:.2%}")
        print(f"   ADV gate: PASS")
        print(f"   Economics gate: {gate['verdict']}")
        print(f"   Reasons: {gate['reasons']}")
    
    def test_buy_blocked_when_adv_gate_fails(self):
        """
        Critical test: BUY should be blocked when position exceeds %ADV limit.
        
        Can't trade size that would move the market.
        """
        # Scenario: Good returns, but position too large
        median_return = 0.05  # 5% net return (good!)
        
        # ADV gate fails - trying to trade 10% of ADV
        adv_result = calculate_adv_gate(
            adv_shares=1_000_000,
            avg_price=100,
            position_size_usd=10_000_000,  # $10M position, 10% of ADV (too much!)
            max_pct_adv=0.05
        )
        
        assert not adv_result["adv_ok"], "ADV gate should FAIL"
        
        # Economics gate should fail
        gate = economics_gate(median_return, adv_result)
        
        assert not gate["passed"], "Economics gate should FAIL when ADV exceeded"
        assert gate["verdict"] == "FAIL"
        assert any("exceeds" in r.lower() for r in gate["reasons"])
        
        print(f"\n✅ BUY correctly blocked:")
        print(f"   Median return: {median_return:.2%}")
        print(f"   ADV gate: FAIL ({adv_result['pct_adv']:.1%} of ADV)")
        print(f"   Economics gate: {gate['verdict']}")
        print(f"   Reasons: {gate['reasons']}")
    
    def test_buy_allowed_when_both_gates_pass(self):
        """
        Test that BUY is allowed when both gates pass.
        """
        median_return = 0.03  # 3% net return
        
        # ADV gate passes
        adv_result = calculate_adv_gate(
            adv_shares=10_000_000,
            avg_price=100,
            position_size_usd=5_000_000,  # $5M position, 0.5% of ADV
            max_pct_adv=0.05
        )
        
        assert adv_result["adv_ok"], "ADV gate should pass"
        
        # Economics gate should pass
        gate = economics_gate(median_return, adv_result)
        
        assert gate["passed"], "Economics gate should PASS"
        assert gate["verdict"] == "PASS"
        assert len(gate["reasons"]) == 0, "Should have no blocking reasons"
        
        print(f"\n✅ BUY correctly allowed:")
        print(f"   Median return: {median_return:.2%}")
        print(f"   ADV gate: PASS ({adv_result['pct_adv']:.1%} of ADV)")
        print(f"   Economics gate: {gate['verdict']}")
    
    def test_spread_proxy_formula(self):
        """
        Test the spread proxy formula with various scenarios.
        """
        # Liquid large-cap (tight spread)
        spread_tight = calculate_spread_proxy_bps(high=100.5, low=99.5, close=100)
        assert 3 <= spread_tight <= 10, f"Tight spread should be 3-10 bps, got {spread_tight:.2f}"
        
        # Volatile stock (wider spread)
        spread_wide = calculate_spread_proxy_bps(high=105, low=95, close=100)
        assert 20 <= spread_wide <= 50, f"Wide spread should be 20-50 bps, got {spread_wide:.2f}"
        
        # Extreme case (clipped to max)
        spread_extreme = calculate_spread_proxy_bps(high=150, low=50, close=100)
        assert spread_extreme == 50.0, f"Extreme spread should clip to 50 bps, got {spread_extreme:.2f}"
        
        # Tight range (clipped to min)
        spread_min = calculate_spread_proxy_bps(high=100.01, low=99.99, close=100)
        assert spread_min == 3.0, f"Min spread should clip to 3 bps, got {spread_min:.2f}"
        
        print(f"\n✅ Spread proxy formula validated:")
        print(f"   Tight range (100.5-99.5): {spread_tight:.2f} bps")
        print(f"   Wide range (105-95): {spread_wide:.2f} bps")
        print(f"   Extreme range (150-50): {spread_extreme:.2f} bps (clipped)")
        print(f"   Min range (100.01-99.99): {spread_min:.2f} bps (clipped)")
    
    def test_spread_proxy_with_real_data(self):
        """
        Test spread proxy with realistic market data.
        """
        # NVDA-like (liquid tech stock)
        # Typical daily range ~2-3% with close around $150
        nvda_spread = calculate_spread_proxy_bps(high=153, low=149, close=151)
        
        # Should be reasonable (5-15 bps for a liquid stock)
        assert 3 <= nvda_spread <= 20, f"NVDA-like spread should be 3-20 bps, got {nvda_spread:.2f}"
        
        # Small-cap volatile stock
        # Typical daily range ~5-8% with close around $10
        smallcap_spread = calculate_spread_proxy_bps(high=10.5, low=9.8, close=10.1)
        
        # Should be wider (15-40 bps)
        assert 10 <= smallcap_spread <= 50, f"Small-cap spread should be 10-50 bps, got {smallcap_spread:.2f}"
        
        print(f"\n✅ Real-world spread proxies:")
        print(f"   NVDA-like (liquid): {nvda_spread:.2f} bps")
        print(f"   Small-cap (volatile): {smallcap_spread:.2f} bps")
    
    def test_adv_gate_with_various_sizes(self):
        """
        Test ADV gate with different position sizes.
        """
        adv_shares = 10_000_000
        avg_price = 100
        adv_usd = adv_shares * avg_price  # $1B ADV
        max_position = adv_usd * 0.05  # $50M max (5% of ADV)
        
        # Small position (1% of ADV) - should pass
        gate_1pct = calculate_adv_gate(adv_shares, avg_price, 10_000_000, max_pct_adv=0.05)
        assert gate_1pct["adv_ok"], "1% of ADV should pass"
        
        # Medium position (5% of ADV) - should pass (at limit)
        gate_5pct = calculate_adv_gate(adv_shares, avg_price, 50_000_000, max_pct_adv=0.05)
        assert gate_5pct["adv_ok"], "5% of ADV should pass (at limit)"
        
        # Large position (10% of ADV) - should fail
        gate_10pct = calculate_adv_gate(adv_shares, avg_price, 100_000_000, max_pct_adv=0.05)
        assert not gate_10pct["adv_ok"], "10% of ADV should fail"
        
        print(f"\n✅ ADV gate tested at various sizes:")
        print(f"   1% ADV: {gate_1pct['adv_ok']} (PASS)")
        print(f"   5% ADV: {gate_5pct['adv_ok']} (PASS)")
        print(f"   10% ADV: {gate_10pct['adv_ok']} (FAIL)")
    
    def test_economics_gate_integration(self):
        """
        Integration test: Combined economics gate with realistic scenarios.
        """
        # Scenario 1: Ideal trade
        adv_1 = calculate_adv_gate(10_000_000, 100, 5_000_000, 0.05)
        gate_1 = economics_gate(0.05, adv_1)
        assert gate_1["passed"], "Ideal trade should pass"
        
        # Scenario 2: Good signal, but unprofitable after costs
        adv_2 = calculate_adv_gate(10_000_000, 100, 5_000_000, 0.05)
        gate_2 = economics_gate(-0.01, adv_2)
        assert not gate_2["passed"], "Unprofitable trade should fail"
        
        # Scenario 3: Profitable, but too large
        adv_3 = calculate_adv_gate(10_000_000, 100, 100_000_000, 0.05)
        gate_3 = economics_gate(0.05, adv_3)
        assert not gate_3["passed"], "Oversized trade should fail"
        
        # Scenario 4: Both checks fail
        adv_4 = calculate_adv_gate(10_000_000, 100, 100_000_000, 0.05)
        gate_4 = economics_gate(-0.01, adv_4)
        assert not gate_4["passed"], "Trade failing both checks should fail"
        assert len(gate_4["reasons"]) == 2, "Should have 2 failure reasons"
        
        print(f"\n✅ Integration scenarios:")
        print(f"   Ideal: {gate_1['verdict']}")
        print(f"   Unprofitable: {gate_2['verdict']} - {gate_2['reasons']}")
        print(f"   Oversized: {gate_3['verdict']} - {gate_3['reasons']}")
        print(f"   Both fail: {gate_4['verdict']} - {gate_4['reasons']}")


def test_edge_cases():
    """
    Test edge cases for economics functions.
    """
    # Zero/negative prices
    spread_invalid = calculate_spread_proxy_bps(high=100, low=95, close=0)
    assert spread_invalid == 50.0, "Invalid price should return max spread"
    
    # Zero ADV
    adv_zero = calculate_adv_gate(adv_shares=0, avg_price=100, position_size_usd=1000, max_pct_adv=0.05)
    assert not adv_zero["adv_ok"], "Zero ADV should fail gate"
    
    # Exactly zero median return (should fail - need positive)
    adv_ok = calculate_adv_gate(1_000_000, 100, 1_000_000, 0.05)
    gate_zero = economics_gate(0.0, adv_ok)
    assert not gate_zero["passed"], "Zero median return should fail (need positive)"
    
    print(f"\n✅ Edge cases handled correctly:")
    print(f"   Invalid price → spread = {spread_invalid:.0f} bps")
    print(f"   Zero ADV → gate = FAIL")
    print(f"   Zero median return → gate = FAIL")


if __name__ == "__main__":
    # Run tests
    pytest.main([__file__, "-v", "-s"])

