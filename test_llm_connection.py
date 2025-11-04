#!/usr/bin/env python3
"""Quick test to show LLM connection"""
import asyncio
import os
from services.llm.client import propose_trade

async def test():
    print("🧪 Testing LLM Connection...")
    print("=" * 50)
    
    payload = {
        "ticker": "AAPL",
        "price": 192.50,
        "event_type": "EARNINGS",
        "days_to_event": 7,
        "rank_components": {"immediacy": 0.6, "materiality": 0.6},
        "expected_move": 0.04,
        "backtest_kpis": {"hit_rate": 0.54},
        "liquidity": 5000000000,
        "spread": 0.01,
        "news_summary": "Test",
        "context": []
    }
    
    print(f"\n📤 Sending to LLM:")
    print(f"   API URL: {os.getenv('DEEPSEEK_API_URL', 'default')}")
    print(f"   API Key: {os.getenv('DEEPSEEK_API_KEY', 'not set')[:10]}...")
    print(f"   Payload: ticker={payload['ticker']}, price={payload['price']}")
    
    print(f"\n⏳ Calling LLM API...")
    result = await propose_trade(payload)
    
    print(f"\n📥 Response:")
    print(f"   Entry: ${result.get('entry_price', 'N/A')}")
    print(f"   Stop: ${result.get('stop_price', 'N/A')}")
    print(f"   Target: ${result.get('target_price', 'N/A')}")
    print(f"   Confidence: {result.get('confidence', 'N/A')}")
    print(f"   Reason: {result.get('reason', 'N/A')[:60]}...")
    
    if "mock" in result.get('reason', '').lower():
        print(f"\n⚠️  Using mock plan (LLM API unavailable)")
    else:
        print(f"\n✅ LLM plan received successfully")

if __name__ == "__main__":
    asyncio.run(test())
