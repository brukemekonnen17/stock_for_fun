"""
API integration tests using FastAPI TestClient
"""
import pytest
from fastapi.testclient import TestClient
from apps.api.main import app


@pytest.fixture
def client():
    """Create test client"""
    return TestClient(app)


class TestAPIEndpoints:
    """Test core API endpoints"""
    
    def test_health(self, client):
        """GET /health should return ok status"""
        response = client.get("/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "ok"
        assert "time" in data
    
    def test_scan(self, client):
        """GET /scan should return catalyst list"""
        response = client.get("/scan")
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        assert len(data) > 0
        
        # Check first item has expected keys
        first = data[0]
        assert "symbol" in first
        assert "catalyst" in first
        assert "confidence" in first
        assert "timestamp" in first
    
    def test_propose_with_context(self, client):
        """POST /propose should return selected_arm and plan"""
        payload = {
            "ticker": "AAPL",
            "price": 192.50,
            "event_type": "EARNINGS",
            "days_to_event": 7,
            "rank_components": {"immediacy": 0.6, "materiality": 0.6},
            "expected_move": 0.04,
            "backtest_kpis": {"hit_rate": 0.54},
            "liquidity": 5_000_000_000,
            "spread": 0.01,
            "news_summary": "Test",
            "context": [0.6, 0.6, 1.0, 0.4, 0.5, 0.04, 7]
        }
        
        response = client.post("/propose", json=payload)
        assert response.status_code == 200
        
        data = response.json()
        assert "selected_arm" in data
        assert "plan" in data
        assert "decision_id" in data
        
        # Selected arm should be one of the known arms
        valid_arms = {"EARNINGS_PRE", "POST_EVENT_MOMO", "NEWS_SPIKE", "REACTIVE", "SKIP"}
        assert data["selected_arm"] in valid_arms
        
        # Plan should have required keys
        plan = data["plan"]
        assert "ticker" in plan
        assert "entry_price" in plan
        assert "stop_price" in plan
    
    def test_validate_approved(self, client):
        """POST /validate should return verdict"""
        payload = {
            "plan": {
                "ticker": "AAPL",
                "entry_type": "limit",
                "entry_price": 192.0,
                "stop_rule": "ATR14 * 1.0 below entry",
                "stop_price": 189.0,
                "target_rule": "1.5 x stop",
                "target_price": 196.50,
                "timeout_days": 5,
                "confidence": 0.72,
                "reason": "Test trade"
            },
            "market": {
                "price": 192.30,
                "spread": 0.01,
                "avg_dollar_vol": 5_000_000_000
            },
            "context": {
                "open_positions": 1,
                "realized_pnl_today": -10.0
            }
        }
        
        response = client.post("/validate", json=payload)
        assert response.status_code == 200
        
        data = response.json()
        assert "verdict" in data
        assert "reason" in data
        assert "adjusted_size" in data
        
        # Should be APPROVED or REJECTED
        assert data["verdict"] in ["APPROVED", "REJECTED", "REVIEW"]
    
    def test_validate_rejected_kill_switch(self, client):
        """POST /validate should reject on kill-switch"""
        payload = {
            "plan": {
                "ticker": "AAPL",
                "entry_type": "limit",
                "entry_price": 192.0,
                "stop_rule": "ATR14 * 1.0 below entry",
                "stop_price": 189.0,
                "target_rule": "1.5 x stop",
                "target_price": 196.50,
                "timeout_days": 5,
                "confidence": 0.72,
                "reason": "Test trade"
            },
            "market": {
                "price": 192.30,
                "spread": 0.01,
                "avg_dollar_vol": 5_000_000_000
            },
            "context": {
                "open_positions": 1,
                "realized_pnl_today": -100.0  # Below kill-switch threshold
            }
        }
        
        response = client.post("/validate", json=payload)
        assert response.status_code == 200
        
        data = response.json()
        assert data["verdict"] == "REJECTED"
        assert "kill-switch" in data["reason"].lower()
    
    def test_bandit_reward(self, client):
        """POST /bandit/reward should return ok"""
        payload = {
            "arm_name": "POST_EVENT_MOMO",
            "context": [0.6, 0.6, 1.0, 0.4, 0.5, 0.04, 7],
            "reward": 0.35
        }
        
        response = client.post("/bandit/reward", json=payload)
        assert response.status_code == 200
        
        data = response.json()
        assert data["status"] == "ok"
    
    def test_bandit_reward_missing_context(self, client):
        """POST /bandit/reward should fail without context"""
        payload = {
            "arm_name": "POST_EVENT_MOMO",
            "context": [],  # Empty context
            "reward": 0.35
        }
        
        response = client.post("/bandit/reward", json=payload)
        assert response.status_code == 400


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

