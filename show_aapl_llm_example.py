#!/usr/bin/env python3
"""Show example LLM v2 output for AAPL with enhanced statistical analysis"""
import asyncio
import json
from services.llm.client import propose_trade_v2
from services.llm.prompt_builder import build_messages
from pathlib import Path

async def show_aapl_example():
    """Show enhanced LLM output for AAPL"""
    print("=" * 80)
    print("📊 LLM v2 Enhanced Analysis Output for AAPL")
    print("=" * 80)
    
    # Load system prompt
    project_dir = Path(__file__).parent
    prompt_path = project_dir / "PROMPTS" / "LLM_SYSTEM.md"
    
    if prompt_path.exists():
        system_prompt_text = prompt_path.read_text(encoding="utf-8")
    else:
        system_prompt_text = "You are a professional trading analyst. Output STRICT JSON only."
    
    # Realistic AAPL payload with enhanced data
    payload_for_llm = {
        "ticker": "AAPL",
        "price": 192.50,
        "spread": 0.01,
        "policy_limits": {
            "spread_cents_max": 0.05,
            "spread_bps_max": 0.005
        },
        "recent_high_10d": 195.20,
        "recent_low_10d": 188.50,
        "price_position_10d": 0.75,
        "volume_surge_ratio": 1.65,
        "expected_move_iv": 0.045,
        "rv_10d": 0.22,
        "iv_minus_rv": 0.02,
        "sector_relative_strength": 0.08,
        "pattern_detected": {
            "name": "Ascending Triangle",
            "confidence": 0.75,
            "side": "BULLISH"
        },
        "participation_quality": "HIGH",
        # Technical indicators
        "adr20": 0.019,
        "atr14": 3.85,
        "ema20": 191.20,
        "ema50": 189.50,
        "rsi14": 62.5,
        "bb_upper": 195.80,
        "bb_lower": 189.20,
        # Evidence and statistical tests
        "evidence": {
            "event_study": {
                "significant": True,
                "car_summary": {
                    "car": [
                        {"day": -1, "mean": 0.005, "ci_low": -0.002, "ci_high": 0.012},
                        {"day": 0, "mean": 0.008, "ci_low": 0.001, "ci_high": 0.015},
                        {"day": 1, "mean": 0.015, "ci_low": 0.008, "ci_high": 0.022}
                    ]
                }
            },
            "statistical_tests": {
                "volume_test": {
                    "p_value": 0.02,
                    "effect_size": 0.45,
                    "ci_low": 1.2,
                    "ci_high": 2.1,
                    "significant": True
                },
                "return_test": {
                    "p_value": 0.03,
                    "median": 0.012,
                    "ci_low": 0.005,
                    "ci_high": 0.020,
                    "significant": True
                }
            },
            "fdr_correction": {
                "fdr_method": "BH_FDR",
                "q_values": [0.02, 0.03, 0.04]
            }
        },
        "event_type": "EARNINGS",
        "days_to_event": 7,
        "materiality": 0.65,
        "social_sentiment": {
            "score": 0.35,
            "mentions": 1250,
            "bull_ratio": 0.58
        },
        "tick_size": 0.01
    }
    
    print("\n📤 Input Data Summary:")
    print(f"   Price: ${payload_for_llm['price']}")
    print(f"   Volume Surge: {payload_for_llm['volume_surge_ratio']}x")
    print(f"   Pattern: {payload_for_llm['pattern_detected']['name']} ({payload_for_llm['pattern_detected']['confidence']*100:.0f}% confidence)")
    print(f"   RSI: {payload_for_llm['rsi14']}")
    print(f"   Event Study: {'Significant' if payload_for_llm['evidence']['event_study']['significant'] else 'Not significant'}")
    print(f"   Volume Test p-value: {payload_for_llm['evidence']['statistical_tests']['volume_test']['p_value']}")
    
    print("\n⏳ Calling LLM v2 API...")
    messages = build_messages(system_prompt_text, payload_for_llm)
    raw_response = await propose_trade_v2(messages)
    
    if raw_response:
        print("\n" + "=" * 80)
        print("📥 Raw LLM Response (Full JSON):")
        print("=" * 80)
        print(raw_response)
        
        # Try to parse it
        from apps.api.schemas_llm import parse_llm_json
        try:
            parsed = parse_llm_json(raw_response)
            if parsed:
                print("\n" + "=" * 80)
                print("✅ Parsed & Validated Response:")
                print("=" * 80)
                
                result = parsed.model_dump()
                
                print("\n🎯 VERDICTS:")
                print(f"   Intraday: {result['verdict_intraday']}")
                print(f"   Swing (1-5d): {result['verdict_swing_1to5d']}")
                print(f"   Confidence: {result['confidence']:.3f}")
                
                print("\n📊 ROOM ANALYSIS:")
                room = result.get("room", {})
                print(f"   Intraday Up: {room.get('intraday_room_up_pct', 0)*100:.2f}%")
                print(f"   Intraday Down: {room.get('intraday_room_down_pct', 0)*100:.2f}%")
                print(f"   Swing Up: {room.get('swing_room_up_pct', 0)*100:.2f}%")
                print(f"   Swing Down: {room.get('swing_room_down_pct', 0)*100:.2f}%")
                print(f"   Explanation: {room.get('explain', 'N/A')}")
                
                print("\n📈 PATTERN ANALYSIS:")
                pattern = result.get("pattern", {})
                print(f"   State: {pattern.get('state', 'N/A')}")
                key_levels = pattern.get("key_levels", {})
                if key_levels:
                    print(f"   Support: ${key_levels.get('support_1', 'N/A')}")
                    print(f"   Resistance: ${key_levels.get('resistance_1', 'N/A')}")
                
                print("\n💪 PARTICIPATION:")
                participation = result.get("participation", {})
                print(f"   Quality: {participation.get('quality', 'N/A')}")
                print(f"   Volume Surge: {participation.get('volume_surge_ratio', 'N/A')}")
                print(f"   Explanation: {participation.get('explain', 'N/A')}")
                
                print("\n📋 TRADE PLAN:")
                plan = result.get("plan", {})
                print(f"   Entry Type: {plan.get('entry_type', 'N/A')}")
                print(f"   Entry Price: ${plan.get('entry_price', 'N/A'):.2f}")
                print(f"   Stop Price: ${plan.get('stop_price', 'N/A'):.2f}")
                targets = plan.get("targets", [])
                if targets:
                    print(f"   Targets: {[f'${t:.2f}' for t in targets]}")
                print(f"   Timeout: {plan.get('timeout_days', 'N/A')} days")
                print(f"   Rationale: {plan.get('rationale', 'N/A')}")
                
                print("\n📊 STATISTICAL ANALYSIS:")
                stats = result.get("statistical_analysis", {})
                if stats:
                    effect_sizes = stats.get("effect_sizes", {})
                    if effect_sizes:
                        print(f"   Effect Sizes:")
                        print(f"     Volume Surge: {effect_sizes.get('volume_surge', 'N/A')}")
                        print(f"     Price Momentum: {effect_sizes.get('price_momentum', 'N/A')}")
                        print(f"     IV-RV Gap: {effect_sizes.get('iv_rv_gap', 'N/A')}")
                        print(f"     Sector Strength: {effect_sizes.get('sector_strength', 'N/A')}")
                    
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
                    print("   (Statistical analysis section not included in response)")
                
                print("\n" + "=" * 80)
                print("📄 Complete JSON Response:")
                print("=" * 80)
                print(json.dumps(result, indent=2, default=str))
        except Exception as e:
            print(f"\n❌ Parse Error: {e}")
            print("\nRaw response (first 1000 chars):")
            print(raw_response[:1000])
    else:
        print("\n❌ Empty response from LLM")

if __name__ == "__main__":
    asyncio.run(show_aapl_example())

