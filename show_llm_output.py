#!/usr/bin/env python3
"""Show example LLM output"""
import asyncio
import json
import os
from dotenv import load_dotenv
from services.llm.client import propose_trade, propose_trade_v2
from services.llm.prompt_builder import build_messages

load_dotenv()

async def test_v1_output():
    """Test legacy LLM (v1) output"""
    print("=" * 70)
    print("🧪 LLM v1 (Legacy) Output Example")
    print("=" * 70)
    
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
        "news_summary": "Apple reports strong Q4 earnings",
        "market_context": '{"rsi": 55, "atr": 2.5}',
        "social_sentiment": '{"sentiment_score": 0.65}',
        "context": []
    }
    
    print("\n📤 Input Payload:")
    print(json.dumps(payload, indent=2))
    
    print("\n⏳ Calling LLM API...")
    result = await propose_trade(payload)
    
    print("\n📥 LLM Response (v1):")
    print(json.dumps(result, indent=2))
    
    return result

async def test_v2_output():
    """Test Phase-1 LLM (v2) output"""
    print("\n" + "=" * 70)
    print("🧪 LLM v2 (Phase-1) Output Example")
    print("=" * 70)
    
    # Build payload similar to what the API sends
    payload_for_llm = {
        "price": 192.50,
        "spread": 0.01,
        "policy_limits": {
            "spread_cents_max": 0.05,
            "spread_bps_max": 0.005
        },
        "recent_high_10d": 195.0,
        "recent_low_10d": 188.0,
        "price_position_10d": 0.65,
        "volume_surge_ratio": 1.5,
        "expected_move_iv": 0.04,
        "rv_10d": 0.22,
        "iv_minus_rv": 0.02,
        "sector_relative_strength": 0.05,
        "pattern_detected": {
            "name": "Ascending Triangle",
            "confidence": 0.71,
            "side": "BULLISH"
        },
        "participation_quality": "HIGH",
        "evidence": {
            "event_study": {
                "significant": True
            }
        },
        "tick_size": 0.01
    }
    
    # Load system prompt
    from pathlib import Path
    project_dir = Path(__file__).parent
    prompt_path = project_dir / "PROMPTS" / "LLM_SYSTEM.md"
    
    system_prompt_text = ""
    if prompt_path.exists():
        with open(prompt_path, "r") as f:
            system_prompt_text = f.read()
    else:
        system_prompt_text = "You are a professional trading analyst."
    
    print("\n📤 Input Payload (simplified):")
    print(json.dumps({k: v for k, v in payload_for_llm.items() if k != "evidence"}, indent=2))
    
    print("\n⏳ Calling LLM API (v2)...")
    messages = build_messages(system_prompt_text, payload_for_llm)
    raw_response = await propose_trade_v2(messages)
    
    if raw_response:
        print("\n📥 Raw LLM Response (v2):")
        print(raw_response[:500] + "..." if len(raw_response) > 500 else raw_response)
        
        # Try to parse it
        from apps.api.schemas_llm import parse_llm_json
        try:
            parsed = parse_llm_json(raw_response)
            if parsed:
                print("\n✅ Parsed Response (v2):")
                print(json.dumps(parsed.model_dump(), indent=2, default=str))
        except Exception as e:
            print(f"\n❌ Parse Error: {e}")
    else:
        print("\n❌ Empty response from LLM")
    
    return raw_response

async def main():
    print("\n" + "=" * 70)
    print("LLM OUTPUT EXAMPLES")
    print("=" * 70)
    
    # Test v1
    v1_result = await test_v1_output()
    
    # Test v2 if enabled
    if os.getenv("ENABLE_LLM_PHASE1", "0") == "1":
        v2_result = await test_v2_output()
    else:
        print("\n" + "=" * 70)
        print("ℹ️  LLM v2 is disabled (ENABLE_LLM_PHASE1=0)")
        print("=" * 70)
    
    print("\n" + "=" * 70)
    print("✅ Examples Complete")
    print("=" * 70)

if __name__ == "__main__":
    asyncio.run(main())

