"""
Tests for M1: LLM Summary Service
5 golden test pairs from notebook outputs
"""
import pytest
import json
from pathlib import Path
from services.llm.summarizer import (
    build_summarizer_prompt,
    load_contract_from_file,
    summarize_contract
)
from apps.api.schemas_summarizer import SummaryResponse

# Test data directory
TEST_DATA_DIR = Path(__file__).parent.parent / "artifacts"

@pytest.fixture
def sample_contract():
    """Sample analysis_contract.json from notebook"""
    return {
        "analysis_id": "test-123",
        "run_id": "test_run_123",
        "ticker": "NVDA",
        "window_days": 365,
        "timestamp": "2025-11-10T11:19:38.265299",
        "drivers": {
            "pattern": "GREEN",
            "sector_rs": "+",
            "iv_rv": "NEUTRAL",
            "meme": "MED"
        },
        "evidence": [
            {
                "test": "EMA_Crossover",
                "H": 5,
                "effect": 0.0025,  # 25 bps
                "ci": [0.001, 0.004],
                "p": 0.03,
                "q": 0.08
            }
        ],
        "economics": {
            "net_median": 0.0015,
            "net_p90": 0.003,
            "blocked": False
        },
        "plan": {
            "entry_price": 188.15,
            "stop_price": 173.15,
            "target_price": 210.65,
            "stop_pct": -8.0,
            "target_pct": 12.0,
            "risk_reward": 1.5,
            "policy_ok": True
        },
        "risks": [
            "Market volatility may impact entry execution"
        ],
        "why_now": "Strong technical pattern with positive sector momentum",
        "verdict": "BUY",
        "artifacts": {}
    }

@pytest.fixture
def blocked_contract():
    """Contract with blocked economics"""
    return {
        "analysis_id": "test-456",
        "run_id": "test_run_456",
        "ticker": "AAPL",
        "window_days": 365,
        "timestamp": "2025-11-10T12:00:00",
        "drivers": {
            "pattern": "YELLOW",
            "sector_rs": "NEUTRAL"
        },
        "evidence": [
            {
                "test": "EMA_Crossover",
                "H": 5,
                "effect": None,
                "ci": None,
                "p": None,
                "q": None
            }
        ],
        "economics": {
            "net_median": None,
            "net_p90": None,
            "blocked": True
        },
        "plan": {
            "entry_price": 150.0,
            "stop_price": 140.0,
            "target_price": 165.0,
            "stop_pct": -6.67,
            "target_pct": 10.0,
            "risk_reward": 1.5,
            "policy_ok": False
        },
        "risks": [
            "Net returns not positive after costs",
            "CAR does not support signal"
        ],
        "why_now": "Review conditions",
        "verdict": "SKIP",
        "artifacts": {}
    }

class TestSummarizer:
    """Test suite for summarizer service"""
    
    def test_build_prompt_required_fields(self, sample_contract):
        """Test prompt building with valid contract"""
        messages = build_summarizer_prompt(sample_contract)
        
        assert len(messages) == 2
        assert messages[0]["role"] == "system"
        assert messages[1]["role"] == "user"
        assert "NVDA" in messages[1]["content"]
        assert "BUY" in messages[1]["content"]
    
    def test_build_prompt_missing_fields(self):
        """Test prompt building fails with missing required fields"""
        incomplete = {"ticker": "NVDA"}
        
        with pytest.raises(ValueError, match="Missing required fields"):
            build_summarizer_prompt(incomplete)
    
    def test_load_contract_from_file(self, tmp_path):
        """Test loading contract from file"""
        contract_file = tmp_path / "test_contract.json"
        test_contract = {"ticker": "TEST", "verdict": "BUY", "evidence": [], "economics": {}, "plan": {}}
        
        with open(contract_file, 'w') as f:
            json.dump(test_contract, f)
        
        loaded = load_contract_from_file(str(contract_file))
        assert loaded["ticker"] == "TEST"
    
    def test_load_contract_file_not_found(self):
        """Test loading non-existent file raises FileNotFoundError"""
        with pytest.raises(FileNotFoundError):
            load_contract_from_file("nonexistent.json")
    
    @pytest.mark.asyncio
    async def test_summarize_contract_structure(self, sample_contract, monkeypatch):
        """Test summarize_contract returns valid structure (mocked LLM)"""
        # Mock LLM response
        mock_response = {
            "executive_summary": "NVDA shows a BUY signal with strong technical pattern (GREEN) and positive sector momentum. Statistical evidence at H=5 shows effect of +25 bps with CI [10, 40] bps (q=0.08 < 0.10, significant). Economics are unblocked with net_median of +15 bps. Plan shows entry at $188.15 with stop at $173.15 (-8.0%) and target at $210.65 (+12.0%), risk/reward 1.5, policy_ok=True.",
            "decision_rationale": [
                "Effect at H=5: +25 bps with CI [10, 40] bps (q=0.08 < 0.10, significant)",
                "Pattern: GREEN - validated crossover signal",
                "Economics: Unblocked - net_median +15 bps, net_p90 +30 bps"
            ],
            "risks_and_watch": [
                "Market volatility may impact entry execution",
                "Watch: Monitor sector momentum for continuation"
            ],
            "action_template": {
                "entry_price": 188.15,
                "stop_price": 173.15,
                "target_price": 210.65,
                "stop_pct": -8.0,
                "target_pct": 12.0,
                "risk_reward": 1.5,
                "policy_ok": True
            },
            "metadata": {
                "ticker": "NVDA",
                "run_id": "test_run_123",
                "timestamp": "2025-11-10T11:19:38.265299",
                "prompt_version": "1.0.0"
            }
        }
        
        async def mock_llm_call(messages):
            return json.dumps(mock_response)
        
        from services.llm import summarizer
        monkeypatch.setattr(summarizer, "propose_trade_v2", mock_llm_call)
        
        summary = await summarize_contract(sample_contract)
        
        # Validate structure
        assert "executive_summary" in summary
        assert "decision_rationale" in summary
        assert "risks_and_watch" in summary
        assert "action_template" in summary
        assert "metadata" in summary
        
        # Validate content
        assert len(summary["executive_summary"]) >= 150
        assert len(summary["decision_rationale"]) >= 1
        assert len(summary["risks_and_watch"]) >= 1
        assert summary["action_template"]["entry_price"] == 188.15
    
    @pytest.mark.asyncio
    async def test_summarize_blocked_contract(self, blocked_contract, monkeypatch):
        """Test summarize handles blocked economics correctly"""
        mock_response = {
            "executive_summary": "AAPL shows a SKIP verdict. Technical pattern is YELLOW with neutral sector RS. Statistical evidence is unavailable (effect null, CI null). Economics are blocked (net_median null, blocked=true), indicating capacity concerns. Plan shows entry at $150.00 but policy_ok is false, suggesting guardrail failures.",
            "decision_rationale": [
                "Effect at H=5: Statistical evidence unavailable",
                "Pattern: YELLOW - weak signal",
                "Economics: Blocked - net returns not positive after costs"
            ],
            "risks_and_watch": [
                "Net returns not positive after costs",
                "CAR does not support signal",
                "Watch: Insufficient statistical power"
            ],
            "action_template": {
                "entry_price": 150.0,
                "stop_price": 140.0,
                "target_price": 165.0,
                "stop_pct": -6.67,
                "target_pct": 10.0,
                "risk_reward": 1.5,
                "policy_ok": False
            },
            "metadata": {
                "ticker": "AAPL",
                "run_id": "test_run_456",
                "timestamp": "2025-11-10T12:00:00",
                "prompt_version": "1.0.0"
            }
        }
        
        async def mock_llm_call(messages):
            return json.dumps(mock_response)
        
        from services.llm import summarizer
        monkeypatch.setattr(summarizer, "propose_trade_v2", mock_llm_call)
        
        summary = await summarize_contract(blocked_contract)
        
        # Validate blocked status is mentioned
        assert "blocked" in summary["executive_summary"].lower() or "skip" in summary["executive_summary"].lower()
        assert summary["action_template"]["policy_ok"] is False
    
    @pytest.mark.asyncio
    async def test_summarize_invalid_json_response(self, sample_contract, monkeypatch):
        """Test summarize handles invalid JSON from LLM"""
        async def mock_llm_call(messages):
            return "This is not valid JSON"
        
        from services.llm import summarizer
        monkeypatch.setattr(summarizer, "propose_trade_v2", mock_llm_call)
        
        with pytest.raises(ValueError, match="LLM returned invalid JSON"):
            await summarize_contract(sample_contract)
    
    def test_summary_response_schema_validation(self):
        """Test SummaryResponse schema validation"""
        valid_summary = {
            "executive_summary": "Test summary " * 20,  # ~200 chars
            "decision_rationale": ["Point 1", "Point 2"],
            "risks_and_watch": ["Risk 1", "Risk 2"],
            "action_template": {
                "entry_price": 100.0,
                "stop_price": 95.0,
                "target_price": 110.0,
                "stop_pct": -5.0,
                "target_pct": 10.0,
                "risk_reward": 2.0,
                "policy_ok": True
            },
            "metadata": {
                "ticker": "TEST",
                "run_id": "test_123",
                "timestamp": "2025-01-01T00:00:00",
                "prompt_version": "1.0.0"
            }
        }
        
        # Should not raise
        response = SummaryResponse(**valid_summary)
        assert response.ticker == "TEST"
    
    def test_summary_response_schema_validation_fails(self):
        """Test SummaryResponse schema validation fails on invalid data"""
        invalid_summary = {
            "executive_summary": "Too short",  # < 150 chars
            "decision_rationale": [],
            "risks_and_watch": [],
            "action_template": {},
            "metadata": {}
        }
        
        with pytest.raises(Exception):  # Pydantic validation error
            SummaryResponse(**invalid_summary)

# Golden test pairs (to be run manually with real LLM)
GOLDEN_TEST_PAIRS = [
    {
        "name": "BUY with strong evidence",
        "contract_file": "artifacts/analysis_contract.json",  # Update with real path
        "expected_keywords": ["BUY", "significant", "effect", "unblocked"]
    },
    {
        "name": "SKIP with blocked economics",
        "contract_file": "artifacts/analysis_contract.json",  # Update with real path
        "expected_keywords": ["SKIP", "blocked", "insufficient"]
    }
]

if __name__ == "__main__":
    pytest.main([__file__, "-v"])

