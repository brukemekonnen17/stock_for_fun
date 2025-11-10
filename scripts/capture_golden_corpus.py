#!/usr/bin/env python3
"""
Capture golden corpus artifacts for reproducibility.
Runs a fixed set of tickers/regimes and archives raw LLM outputs.
"""
import sys
import os
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

import asyncio
import json
from datetime import datetime
from apps.api.main import app
from fastapi.testclient import TestClient

# Golden corpus: fixed tickers across different regimes
GOLDEN_CORPUS = [
    {"ticker": "NVDA", "price": 500.0, "regime": "trending_up", "event_type": "EARNINGS"},
    {"ticker": "AAPL", "price": 190.0, "regime": "quiet", "event_type": "EARNINGS"},
    {"ticker": "TSLA", "price": 250.0, "regime": "trending_down", "event_type": "EARNINGS"},
    {"ticker": "SPY", "price": 450.0, "regime": "quiet", "event_type": "EARNINGS"},
]

# Enable debug capture
os.environ["ENABLE_LLM_DEBUG"] = "1"
os.environ["ENABLE_LLM_PHASE1"] = "1"


async def capture_ticker(ticker_info: dict):
    """Capture one ticker's LLM output."""
    client = TestClient(app)
    
    payload = {
        "ticker": ticker_info["ticker"],
        "price": ticker_info["price"],
        "event_type": ticker_info["event_type"],
        "days_to_event": 5.0,
        "expected_move": 0.05,
        "context": [0.6, 0.6, 1.0, 0.4, 0.5, 0.04, 5.0],
        "rank_components": {},
        "backtest_kpis": {},
        "liquidity": 10_000_000,
        "spread": 0.002,
        "decision_id": f"golden-{ticker_info['ticker']}-{datetime.utcnow().timestamp()}"
    }
    
    print(f"Capturing {ticker_info['ticker']} ({ticker_info['regime']})...")
    
    try:
        response = client.post("/propose", json=payload)
        if response.status_code == 200:
            data = response.json()
            analysis = data.get("analysis", {})
            llm_v2 = analysis.get("llm_v2")
            
            if llm_v2:
                print(f"  ✅ Captured {ticker_info['ticker']}: confidence={llm_v2.get('confidence', 'N/A')}")
            else:
                print(f"  ⚠️  {ticker_info['ticker']}: No llm_v2 in response")
        else:
            print(f"  ❌ {ticker_info['ticker']}: HTTP {response.status_code}")
    except Exception as e:
        print(f"  ❌ {ticker_info['ticker']}: Error - {e}")


def main():
    """Capture all golden corpus tickers."""
    print("=" * 60)
    print("Golden Corpus Capture")
    print("=" * 60)
    print(f"Timestamp: {datetime.utcnow().isoformat()}")
    print(f"Corpus size: {len(GOLDEN_CORPUS)} tickers")
    print()
    
    # Run captures sequentially to avoid rate limits
    for ticker_info in GOLDEN_CORPUS:
        capture_ticker(ticker_info)
        # Small delay between requests
        import time
        time.sleep(2)
    
    print()
    print("=" * 60)
    print("Capture complete. Check tests/golden/raw_llm/ for artifacts.")
    print("=" * 60)


if __name__ == "__main__":
    main()
