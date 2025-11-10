#!/usr/bin/env python3
"""
Smoke Matrix Test - 5 critical test cases
"""

import json
import subprocess
import sys
from pathlib import Path
from typing import Dict, List, Tuple


def run_notebook_for_ticker(ticker: str, expected_outcome: str) -> Tuple[bool, str]:
    """
    Run notebook for a ticker and check expected outcome.
    
    This is a placeholder - actual implementation would:
    1. Modify notebook to use the test ticker
    2. Execute notebook
    3. Parse artifacts
    4. Check expected outcome
    """
    print(f"\n--- Testing {ticker} (expected: {expected_outcome}) ---")
    
    # For now, just check if we can load artifacts
    artifacts_dir = Path("artifacts")
    investor_card_path = artifacts_dir / "investor_card.json"
    
    if not investor_card_path.exists():
        return False, f"Artifacts not found for {ticker}"
    
    try:
        with open(investor_card_path, 'r') as f:
            card = json.load(f)
        
        verdict = card.get('verdict', 'UNKNOWN')
        ticker_actual = card.get('ticker', 'UNKNOWN')
        
        if ticker_actual != ticker:
            return False, f"Ticker mismatch: expected {ticker}, got {ticker_actual}"
        
        print(f"  Verdict: {verdict}")
        print(f"  Ticker: {ticker_actual}")
        
        return True, f"Verdict: {verdict}"
        
    except Exception as e:
        return False, f"Error: {e}"


def test_mega_cap_liquid() -> Tuple[bool, str]:
    """Test mega-cap/liquid: AAPL/NVDA → expect BUY or REVIEW, no economics veto."""
    print("\n" + "="*70)
    print("SMOKE TEST #1: Mega-Cap/Liquid (AAPL/NVDA)")
    print("="*70)
    
    # This would run the notebook for AAPL or NVDA
    # Expected: BUY or REVIEW, no economics veto
    return run_notebook_for_ticker("NVDA", "BUY or REVIEW")


def test_mid_cap() -> Tuple[bool, str]:
    """Test mid-cap: AMD/SHOP → one should fail impact veto or effect floor."""
    print("\n" + "="*70)
    print("SMOKE TEST #2: Mid-Cap (AMD/SHOP)")
    print("="*70)
    
    # Expected: Impact veto or effect floor failure
    return run_notebook_for_ticker("AMD", "Impact veto or effect floor")


def test_low_liquidity() -> Tuple[bool, str]:
    """Test low-liquidity: small ticker → ADV gate must fail."""
    print("\n" + "="*70)
    print("SMOKE TEST #3: Low-Liquidity (Small Ticker)")
    print("="*70)
    
    # Expected: ADV gate failure
    return run_notebook_for_ticker("PCSA", "ADV gate failure")


def test_event_sparse() -> Tuple[bool, str]:
    """Test event-sparse: BRK.B → small-N yellow chip likely."""
    print("\n" + "="*70)
    print("SMOKE TEST #4: Event-Sparse (BRK.B)")
    print("="*70)
    
    # Expected: Small-N yellow chip
    return run_notebook_for_ticker("BRK.B", "Small-N yellow chip")


def test_holiday_window() -> Tuple[bool, str]:
    """Test holiday window: any name spanning market holiday → 0 invalid bars."""
    print("\n" + "="*70)
    print("SMOKE TEST #5: Holiday Window")
    print("="*70)
    
    # Expected: 0 invalid bars
    return run_notebook_for_ticker("AAPL", "0 invalid bars")


def main():
    """Run smoke matrix tests."""
    print("\n" + "="*70)
    print("SMOKE MATRIX TEST SUITE")
    print("="*70)
    print("\n⚠️  NOTE: This is a placeholder implementation.")
    print("   Actual execution requires notebook modification and execution.")
    print("   Run manually for each ticker and verify expected outcomes.")
    
    results = []
    
    # Run all smoke tests
    results.append(("Mega-Cap/Liquid", test_mega_cap_liquid()))
    results.append(("Mid-Cap", test_mid_cap()))
    results.append(("Low-Liquidity", test_low_liquidity()))
    results.append(("Event-Sparse", test_event_sparse()))
    results.append(("Holiday Window", test_holiday_window()))
    
    # Summary
    print("\n" + "="*70)
    print("SMOKE TEST SUMMARY")
    print("="*70)
    
    for name, (status, msg) in results:
        status_icon = "✅" if status else "⚠️"
        print(f"{status_icon} {name}: {msg}")
    
    print("\n" + "="*70)
    print("⚠️  Manual verification required for full smoke test")
    print("="*70)
    
    # Exit with non-zero if any test failed (for CI)
    failed_count = sum(1 for _, (status, _) in results if not status)
    exit_code = 0 if failed_count == 0 else 1
    sys.exit(exit_code)


if __name__ == "__main__":
    sys.exit(main())

