import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from services.analysis.enhanced_features import compute_alignment
from apps.api.schemas_llm import TradeAnalysisV2
from services.llm.validator import enforce_policy_and_sanity


def test_alignment_mapping():
    assert compute_alignment("BREAKOUT", "HIGH", True) == "ALIGNED"
    assert compute_alignment("BREAKOUT", "MEDIUM", False) == "MIXED"
    assert compute_alignment("BREAKOUT", "LOW", False) == "MISALIGNED"
    assert compute_alignment(None, "LOW", False) == "UNKNOWN"


def test_breadth_downgrade_to_reactive():
    ta = TradeAnalysisV2.model_validate({
        "schema": "TradeAnalysisV2",
        "verdict_intraday": "BUY",
        "verdict_swing_1to5d": "BUY",
        "confidence": 0.7,
        "room": {
            "intraday_room_up_pct": 0.01,
            "intraday_room_down_pct": 0.005,
            "swing_room_up_pct": 0.02,
            "swing_room_down_pct": 0.01,
            "explain": "test"
        },
        "pattern": {"state": "BREAKOUT"},
        "participation": {"quality": "LOW"},
        "catalyst_alignment": {"alignment": "NEUTRAL"},
        "meme_social": {"diagnosis": "NOISE"},
        "plan": {
            "entry_type": "trigger",
            "entry_price": 100,
            "stop_price": 99.6,
            "targets": [100.8],
            "timeout_days": 1,
            "rationale": "test"
        },
        "risk": {"policy_pass": True},
        "evidence_fields": [],
        "missing_fields": [],
        "assumptions": {}
    })
    facts = {
        "price": 100.0,
        "spread": 0.01,
        "tick_size": 0.01,
        "policy_limits": {"spread_cents_max": 0.05, "spread_bps_max": 0.005},
        "evidence": {"event_study": {"significant": False}}
    }
    ta2 = enforce_policy_and_sanity(ta, facts)
    assert ta2.verdict_intraday in ("REACTIVE", "SKIP")

