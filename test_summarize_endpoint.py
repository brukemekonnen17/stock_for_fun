"""
Quick test script for /summarize endpoint
Tests with mock LLM response to verify endpoint works
"""
import asyncio
import json
from services.llm.summarizer import summarize_contract, load_contract_from_file

async def test_with_mock():
    """Test summarizer with mocked LLM response"""
    # Load contract
    contract = load_contract_from_file("artifacts/analysis_contract.json")
    
    # Mock LLM response
    mock_response = {
        "executive_summary": "NVDA shows a YELLOW verdict with mixed signals. Technical pattern is GREEN with positive sector relative strength, but statistical evidence is insufficient (all CAR values null, n=2 events). Economics are blocked (net_median null, blocked=true), indicating capacity concerns. The plan shows entry at $188.15 with stop at $173.15 (-8.0%) and target at $210.65 (+12.0%), but policy_ok is false, suggesting guardrail failures.",
        "decision_rationale": [
            "Effect at H=5: Statistical evidence unavailable (effect null, CI null)",
            "Pattern: GREEN - validated crossover signal with positive sector RS",
            "Economics: Blocked - net returns not positive after costs (blocked=true)"
        ],
        "risks_and_watch": [
            "Net returns not positive after costs",
            "CAR does not support signal",
            "Regime not aligned",
            "Watch: Statistical power insufficient (n<10 events, all CAR values null)"
        ],
        "action_template": {
            "entry_price": 188.15,
            "stop_price": 173.15,
            "target_price": 210.65,
            "stop_pct": -8.0,
            "target_pct": 12.0,
            "risk_reward": 1.5,
            "policy_ok": False
        },
        "metadata": {
            "ticker": "NVDA",
            "run_id": "50b0f37965727112",
            "timestamp": "2025-11-10T11:19:38.265299",
            "prompt_version": "1.0.0"
        }
    }
    
    # Mock the LLM call
    import services.llm.summarizer as summarizer_module
    original_call = summarizer_module.propose_trade_v2
    
    async def mock_llm(messages):
        return json.dumps(mock_response)
    
    summarizer_module.propose_trade_v2 = mock_llm
    
    try:
        summary = await summarize_contract(contract)
        print("✅ Summarizer test passed!")
        print("\n" + "="*70)
        print("EXECUTIVE SUMMARY")
        print("="*70)
        print(summary["executive_summary"])
        print("\n" + "="*70)
        print("DECISION RATIONALE")
        print("="*70)
        for i, point in enumerate(summary["decision_rationale"], 1):
            print(f"{i}. {point}")
        print("\n" + "="*70)
        print("RISKS & WHAT TO WATCH")
        print("="*70)
        for i, risk in enumerate(summary["risks_and_watch"], 1):
            print(f"{i}. {risk}")
        print("\n" + "="*70)
        print("ACTION TEMPLATE")
        print("="*70)
        action = summary["action_template"]
        print(f"Entry: ${action['entry_price']:.2f}")
        print(f"Stop: ${action['stop_price']:.2f} ({action['stop_pct']:.1f}%)")
        print(f"Target: ${action['target_price']:.2f} ({action['target_pct']:.1f}%)")
        print(f"Risk/Reward: {action['risk_reward']:.2f}")
        print(f"Policy OK: {action['policy_ok']}")
        print("\n" + "="*70)
        print("METADATA")
        print("="*70)
        meta = summary["metadata"]
        print(f"Ticker: {meta['ticker']}")
        print(f"Run ID: {meta['run_id']}")
        print(f"Prompt Version: {meta['prompt_version']}")
        return True
    except Exception as e:
        print(f"❌ Test failed: {e}")
        import traceback
        traceback.print_exc()
        return False
    finally:
        summarizer_module.propose_trade_v2 = original_call

if __name__ == "__main__":
    success = asyncio.run(test_with_mock())
    exit(0 if success else 1)

