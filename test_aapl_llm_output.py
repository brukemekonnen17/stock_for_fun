#!/usr/bin/env python3
"""Test LLM v2 output with AAPL stock"""
import asyncio
import json
import os
from datetime import datetime
from dotenv import load_dotenv

load_dotenv()

async def test_aapl_llm():
    """Test LLM v2 with real AAPL data"""
    print("=" * 80)
    print("🧪 LLM v2 Analysis Output for AAPL")
    print("=" * 80)
    
    # Create a realistic payload
    payload_data = {
        "decision_id": f"test_aapl_{int(datetime.now().timestamp())}",
        "ticker": "AAPL",
        "price": 192.50,
        "spread": 0.01,
        "liquidity": 5000000000,  # $5B daily volume
        "event_type": "EARNINGS",
        "days_to_event": 7,
        "expected_move": 4.5,  # 4.5% expected move
        "volume_surge_ratio": 1.65,
        "recent_high": 195.20,
        "recent_low": 188.50,
        "price_position": 0.75,  # 75% of 10-day range
        "rolling_volatility_10d": 0.22,
        "context": [0.6, 0.7, 0.5, 0.8],  # Feature vector
        "rank_components": {
            "immediacy": 0.75,
            "materiality": 0.65,
            "liquidity": 0.80,
            "news": 0.60
        },
        "backtest_kpis": {
            "hit_rate": 0.58,
            "avg_win": 0.025,
            "avg_loss": -0.015
        }
    }
    
    try:
        # Import from main.py where ProposePayload is defined
        from apps.api.main import ProposePayload, decision_propose
        
        body = ProposePayload(**payload_data)
        print("\n📤 Input Payload:")
        print(json.dumps(body.model_dump(), indent=2))
        
        print("\n⏳ Calling LLM API...")
        print("   (This may take a few seconds)")
        
        response = await decision_propose(body)
        
        print("\n" + "=" * 80)
        print("📥 LLM Analysis Output")
        print("=" * 80)
        
        # Extract LLM v2 analysis if available
        if response.analysis and response.analysis.get("llm_v2"):
            llm_v2 = response.analysis.get("llm_v2")
            
            print("\n🎯 Verdicts:")
            print(f"   Intraday: {llm_v2.get('verdict_intraday', 'N/A')}")
            print(f"   Swing (1-5d): {llm_v2.get('verdict_swing_1to5d', 'N/A')}")
            print(f"   Confidence: {llm_v2.get('confidence', 0.5):.3f}")
            
            print("\n📊 Room Analysis:")
            room = llm_v2.get("room", {})
            print(f"   Intraday Up: {room.get('intraday_room_up_pct', 0)*100:.2f}%")
            print(f"   Intraday Down: {room.get('intraday_room_down_pct', 0)*100:.2f}%")
            print(f"   Swing Up: {room.get('swing_room_up_pct', 0)*100:.2f}%")
            print(f"   Swing Down: {room.get('swing_room_down_pct', 0)*100:.2f}%")
            print(f"   Explanation: {room.get('explain', 'N/A')}")
            
            print("\n📈 Pattern Analysis:")
            pattern = llm_v2.get("pattern", {})
            print(f"   State: {pattern.get('state', 'N/A')}")
            key_levels = pattern.get("key_levels", {})
            if key_levels:
                print(f"   Support: ${key_levels.get('support_1', 'N/A')}")
                print(f"   Resistance: ${key_levels.get('resistance_1', 'N/A')}")
            
            print("\n💪 Participation:")
            participation = llm_v2.get("participation", {})
            print(f"   Quality: {participation.get('quality', 'N/A')}")
            print(f"   Volume Surge: {participation.get('volume_surge_ratio', 'N/A')}")
            print(f"   Explanation: {participation.get('explain', 'N/A')}")
            
            print("\n🎯 Catalyst Alignment:")
            catalyst = llm_v2.get("catalyst_alignment", {})
            print(f"   Alignment: {catalyst.get('alignment', 'N/A')}")
            print(f"   Explanation: {catalyst.get('explain', 'N/A')}")
            
            print("\n📱 Social/Meme Analysis:")
            meme = llm_v2.get("meme_social", {})
            print(f"   Diagnosis: {meme.get('diagnosis', 'N/A')}")
            print(f"   Explanation: {meme.get('explain', 'N/A')}")
            
            print("\n📋 Trade Plan:")
            plan = llm_v2.get("plan", {})
            print(f"   Entry Type: {plan.get('entry_type', 'N/A')}")
            print(f"   Entry Price: ${plan.get('entry_price', 'N/A')}")
            print(f"   Stop Price: ${plan.get('stop_price', 'N/A')}")
            targets = plan.get("targets", [])
            if targets:
                print(f"   Targets: {[f'${t:.2f}' for t in targets]}")
            print(f"   Timeout: {plan.get('timeout_days', 'N/A')} days")
            print(f"   Rationale: {plan.get('rationale', 'N/A')}")
            
            print("\n⚠️  Risk Assessment:")
            risk = llm_v2.get("risk", {})
            print(f"   Policy Pass: {risk.get('policy_pass', 'N/A')}")
            reasons = risk.get("reasons", [])
            if reasons:
                print(f"   Reasons: {', '.join(reasons)}")
            warnings = risk.get("warnings", [])
            if warnings:
                print(f"   Warnings: {', '.join(warnings)}")
            
            print("\n📊 Statistical Analysis:")
            stats = llm_v2.get("statistical_analysis", {})
            if stats:
                effect_sizes = stats.get("effect_sizes", {})
                if effect_sizes:
                    print(f"   Volume Surge: {effect_sizes.get('volume_surge', 'N/A')}")
                    print(f"   Price Momentum: {effect_sizes.get('price_momentum', 'N/A')}")
                    print(f"   IV-RV Gap: {effect_sizes.get('iv_rv_gap', 'N/A')}")
                    print(f"   Sector Strength: {effect_sizes.get('sector_strength', 'N/A')}")
                
                significance = stats.get("significance", {})
                if significance:
                    print(f"\n   Statistical Significance:")
                    print(f"     Event Study p-value: {significance.get('event_study_p', 'N/A')}")
                    print(f"     Significant: {significance.get('event_study_significant', 'N/A')}")
                    print(f"     FDR q-value: {significance.get('fdr_q', 'N/A')}")
                    print(f"     Interpretation: {significance.get('interpretation', 'N/A')}")
                
                time_horizon = stats.get("time_horizon_analysis", {})
                if time_horizon:
                    print(f"\n   Time Horizon Analysis:")
                    print(f"     Intraday: {time_horizon.get('intraday_setup', 'N/A')}")
                    print(f"     Swing: {time_horizon.get('swing_setup', 'N/A')}")
                    print(f"     Long-term: {time_horizon.get('long_term_context', 'N/A')}")
                
                risk_reward = stats.get("risk_reward", {})
                if risk_reward:
                    print(f"\n   Risk/Reward:")
                    print(f"     Intraday R:R: {risk_reward.get('intraday_rr', 'N/A')}")
                    print(f"     Swing R:R: {risk_reward.get('swing_rr', 'N/A')}")
                    print(f"     Explanation: {risk_reward.get('explain', 'N/A')}")
            else:
                print("   (Statistical analysis not yet available in response)")
            
            print("\n🔍 Evidence Fields Used:")
            evidence_fields = llm_v2.get("evidence_fields", [])
            if evidence_fields:
                for field in evidence_fields[:10]:  # Show first 10
                    print(f"   - {field}")
                if len(evidence_fields) > 10:
                    print(f"   ... and {len(evidence_fields) - 10} more")
            
            print("\n📝 Full JSON Output:")
            print(json.dumps(llm_v2, indent=2, default=str))
        else:
            print("\n⚠️  LLM v2 analysis not found in response")
            print("Full response structure:")
            print(json.dumps(response.model_dump(), indent=2, default=str))
            
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(test_aapl_llm())

