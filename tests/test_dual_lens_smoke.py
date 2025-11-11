"""
Smoke tests for Dual-Lens Decisioning with Guardrails
Tests hard-gate correctness, REACTIVE logic, emotion clipping, and schema rigidity.
"""
import pytest
import json
from pathlib import Path
from services.llm.summarizer import summarize_contract
import asyncio

# Test fixtures - minimal contract payloads for each case
TEST_FIXTURES = {
    "buy_eligible": {
        "ticker": "TEST",
        "run_id": "test_buy",
        "drivers": {"pattern": "GREEN"},
        "evidence": [{
            "H": 5,
            "q": 0.07,
            "p": 0.05,
            "effect": 0.0045,  # 45 bps
            "ci": [0.002, 0.007]
        }],
        "economics": {
            "net_median": 0.003,
            "blocked": False,
            "spread_bps": 6,
            "impact_bps": 10
        },
        "adv_ok": True,
        "hybrid_decision": {
            "evidence_score": 0.75,
            "components": {"S": 0.8, "F": 0.6, "R": 0.7, "C": 0.5, "M": 0.4}
        }
    },
    "stats_weak_flow_ok": {
        "ticker": "TEST",
        "run_id": "test_reactive_flow",
        "drivers": {"pattern": "GREEN"},
        "evidence": [{
            "H": 5,
            "q": 0.32,
            "p": 0.15,
            "effect": 0.0008,  # 8 bps
            "ci": [-0.001, 0.003]
        }],
        "economics": {
            "net_median": 0.001,
            "blocked": False,
            "spread_bps": 8,
            "impact_bps": 12
        },
        "adv_ok": True,
        "hybrid_decision": {
            "evidence_score": 0.55,
            "components": {"S": 0.2, "F": 0.72, "R": 0.6, "C": 0.5, "M": 0.4},
            "flow_score": 0.72
        },
        "social_signals": {
            "meme": {"z_score": 1.6, "mention_count": 50}
        }
    },
    "econ_veto": {
        "ticker": "TEST",
        "run_id": "test_veto",
        "drivers": {"pattern": "GREEN"},
        "evidence": [{
            "H": 5,
            "q": 0.07,
            "p": 0.05,
            "effect": 0.0045,
            "ci": [0.002, 0.007]
        }],
        "economics": {
            "net_median": 0.003,
            "blocked": True,  # VETO
            "spread_bps": 6,
            "impact_bps": 10
        },
        "adv_ok": True,
        "hybrid_decision": {
            "evidence_score": 0.75,
            "components": {"S": 0.8, "F": 0.6, "R": 0.7, "C": 0.5, "M": 0.4}
        }
    },
    "spread_too_wide": {
        "ticker": "TEST",
        "run_id": "test_spread",
        "drivers": {"pattern": "GREEN"},
        "evidence": [{
            "H": 5,
            "q": 0.07,
            "p": 0.05,
            "effect": 0.0045,
            "ci": [0.002, 0.007]
        }],
        "economics": {
            "net_median": 0.003,
            "blocked": False,
            "spread_bps": 64,  # > 50
            "impact_bps": 10
        },
        "adv_ok": True
    },
    "social_clipping": {
        "ticker": "TEST",
        "run_id": "test_clip",
        "drivers": {"pattern": "GREEN"},
        "evidence": [{
            "H": 5,
            "q": 0.32,
            "p": 0.15,
            "effect": 0.0008,
            "ci": [-0.001, 0.003]
        }],
        "economics": {
            "net_median": 0.001,
            "blocked": False,
            "spread_bps": 8,
            "impact_bps": 12
        },
        "adv_ok": True,
        "hybrid_decision": {
            "evidence_score": 0.55,
            "components": {"S": 0.2, "F": 0.6, "R": 0.6, "C": 0.5, "M": 0.4},
            "weights": {"social": 0.35}  # Should be clipped to 0.15
        },
        "social_signals": {
            "meme": {"z_score": 2.3, "mention_count": 100}
        }
    }
}

@pytest.mark.asyncio
async def test_buy_eligible():
    """BUY-eligible: q=0.07, effect_bps=45, all gates pass → expect BUY, confidence ~0.70–0.80"""
    contract = TEST_FIXTURES["buy_eligible"]
    summary = await summarize_contract(contract)
    
    assert summary["verdict"] == "BUY", f"Expected BUY, got {summary['verdict']}"
    assert summary["reason_code"] == "BUY_APPROVED"
    
    confidence = summary.get("confidence", 0.0)
    assert 0.65 <= confidence <= 0.85, f"Confidence {confidence} not in BUY band (0.65-0.85)"
    
    # Check telemetry
    assert "telemetry" in summary
    assert summary["telemetry"]["class_band"] == "BUY"
    assert len(summary["telemetry"]["gate_hits"]) == 0  # No gates tripped

@pytest.mark.asyncio
async def test_reactive_stats_weak_flow_ok():
    """Stats weak but flow strong → expect REACTIVE"""
    contract = TEST_FIXTURES["stats_weak_flow_ok"]
    summary = await summarize_contract(contract)
    
    assert summary["verdict"] == "REACTIVE", f"Expected REACTIVE, got {summary['verdict']}"
    assert summary["reason_code"] in ["REACTIVE_STATS_WEAK_FLOW_OK", "REACTIVE_STATS_WEAK_SOCIAL_OK"]
    
    confidence = summary.get("confidence", 0.0)
    assert 0.45 <= confidence <= 0.65, f"Confidence {confidence} not in REACTIVE band (0.45-0.65)"
    
    # Check short-term verdict exists
    if "trader_lens" in summary and summary["trader_lens"]:
        assert summary["trader_lens"]["short_term_verdict"] in ["YES", "NO"]

@pytest.mark.asyncio
async def test_econ_veto_overrides():
    """Economics veto → must be SKIP even if stats good"""
    contract = TEST_FIXTURES["econ_veto"]
    summary = await summarize_contract(contract)
    
    assert summary["verdict"] == "SKIP", f"Expected SKIP (veto), got {summary['verdict']}"
    assert summary["reason_code"] == "ECON_VETO"
    
    confidence = summary.get("confidence", 0.0)
    assert 0.15 <= confidence <= 0.35, f"Confidence {confidence} not in SKIP band (0.15-0.35)"
    
    # Check gate hit
    assert "ECON_VETO" in summary["telemetry"]["gate_hits"]

@pytest.mark.asyncio
async def test_spread_too_wide():
    """Spread > 50 → must be SKIP even if stats good"""
    contract = TEST_FIXTURES["spread_too_wide"]
    summary = await summarize_contract(contract)
    
    assert summary["verdict"] == "SKIP", f"Expected SKIP (spread), got {summary['verdict']}"
    assert summary["reason_code"] == "SKIP_SPREAD_TOO_WIDE"
    
    # Check gate hit
    assert "SKIP_SPREAD_TOO_WIDE" in summary["telemetry"]["gate_hits"]

@pytest.mark.asyncio
async def test_social_weight_clipping():
    """Social weight > 0.15 → must be clipped to ≤0.15"""
    contract = TEST_FIXTURES["social_clipping"]
    summary = await summarize_contract(contract)
    
    if "emotion_layer" in summary and summary["emotion_layer"]:
        applied_weight = summary["emotion_layer"]["applied_weight"]
        assert applied_weight <= 0.15, f"Social weight {applied_weight} not clipped to ≤0.15"
        
        # Check telemetry
        assert summary["telemetry"]["applied_weight_social"] <= 0.15

@pytest.mark.asyncio
async def test_short_term_verdict_decisive():
    """Short-term verdict must be YES/NO, never null or wordy"""
    contract = TEST_FIXTURES["stats_weak_flow_ok"]
    summary = await summarize_contract(contract)
    
    if "trader_lens" in summary and summary["trader_lens"]:
        verdict = summary["trader_lens"]["short_term_verdict"]
        assert verdict in ["YES", "NO"], f"Short-term verdict must be YES/NO, got: {verdict}"
        
        reason = summary["trader_lens"]["short_term_reason"]
        assert reason is not None and len(reason) > 0, "Short-term reason must be provided"

@pytest.mark.asyncio
async def test_playbook_populated():
    """Playbook fields must all be populated, no placeholders"""
    contract = TEST_FIXTURES["buy_eligible"]
    summary = await summarize_contract(contract)
    
    if "trader_lens" in summary and summary["trader_lens"]:
        playbook = summary["trader_lens"]["playbook"]
        required_fields = ["trigger", "size_rule", "stop", "target", "time_stop", "invalidation"]
        
        for field in required_fields:
            assert field in playbook, f"Playbook missing field: {field}"
            assert playbook[field] is not None, f"Playbook field {field} is None"
            assert len(str(playbook[field])) > 0, f"Playbook field {field} is empty"
            # Check no placeholders
            assert "placeholder" not in str(playbook[field]).lower(), f"Playbook field {field} contains placeholder"

@pytest.mark.asyncio
async def test_conditions_to_upgrade_concrete():
    """Analyst lens conditions_to_upgrade must include concrete thresholds"""
    contract = TEST_FIXTURES["stats_weak_flow_ok"]
    summary = await summarize_contract(contract)
    
    if "analyst_lens" in summary and summary["analyst_lens"]:
        conditions = summary["analyst_lens"]["conditions_to_upgrade"]
        assert len(conditions) > 0, "Must have at least one condition to upgrade"
        
        # Check for concrete thresholds
        conditions_str = " ".join(conditions).lower()
        assert any(x in conditions_str for x in ["q<0.10", "effect", "bps", "net_median"]), \
            "Conditions must include concrete thresholds like q<0.10, effect_bps≥30"

@pytest.mark.asyncio
async def test_discipline_statement_verbatim():
    """Emotion layer discipline must include verbatim statement"""
    contract = TEST_FIXTURES["social_clipping"]
    summary = await summarize_contract(contract)
    
    if "emotion_layer" in summary and summary["emotion_layer"]:
        discipline = summary["emotion_layer"]["discipline"]
        assert "emotion can tilt" in discipline.lower(), \
            "Discipline must include 'emotion can tilt'"
        assert "cannot override econ gates" in discipline.lower(), \
            "Discipline must include 'cannot override econ gates'"

if __name__ == "__main__":
    # Run tests
    pytest.main([__file__, "-v"])

