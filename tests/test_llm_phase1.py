import json
import copy
import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from apps.api.schemas_llm import TradeAnalysisV2
from services.llm.validator import enforce_policy_and_sanity


def _load(path):
    full_path = project_root / path
    return json.load(open(full_path))


def test_strong_breakout_ok():
    out = _load("tests/golden/01_breakout_strong.out.json")
    ta = TradeAnalysisV2.model_validate(out)
    facts = {
        "policy_limits": {"spread_cents_max": 0.05, "spread_bps_max": 0.005},
        "price": 100.0,
        "spread": 0.002,
        "tick_size": 0.01,
        "pattern_detected": {"name": "Ascending Triangle"},
        "evidence": {"event_study": {"significant": True}}
    }
    ta2 = enforce_policy_and_sanity(ta, facts)
    assert ta2.verdict_intraday in ("BUY", "REACTIVE")


def test_weak_breakout_swing_skip():
    out = _load("tests/golden/02_breakout_weak.out.json")
    ta = TradeAnalysisV2.model_validate(out)
    facts = {
        "policy_limits": {"spread_cents_max": 0.05, "spread_bps_max": 0.005},
        "price": 50.0,
        "spread": 0.001,
        "tick_size": 0.01,
        "pattern_detected": {"name": "Flag"},
        "evidence": {"event_study": {"significant": False}}
    }
    ta2 = enforce_policy_and_sanity(ta, facts)
    assert ta2.verdict_swing_1to5d == "SKIP"


def test_spread_violation_forces_skip():
    out = _load("tests/golden/03_spread_violation.out.json")
    ta = TradeAnalysisV2.model_validate(out)
    facts = {
        "policy_limits": {"spread_cents_max": 0.05, "spread_bps_max": 0.005},
        "price": 20.0,
        "spread": 0.12,
        "tick_size": 0.01
    }
    ta2 = enforce_policy_and_sanity(ta, facts)
    assert ta2.verdict_intraday == "SKIP"
    assert ta2.verdict_swing_1to5d == "SKIP"

