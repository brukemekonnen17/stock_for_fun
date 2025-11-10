from fastapi.testclient import TestClient
from apps.api.main import app

client = TestClient(app)


def test_propose_includes_drivers():
    body = {
        "ticker": "AAPL",
        "price": 190.0,
        "event_type": "EARNINGS",
        "days_to_event": 5,
        "context": [0.6, 0.6, 1, 0.4, 0.5, 0.04, 5],
        "rank_components": {},
        "backtest_kpis": {},
        "liquidity": 10_000_000,
        "spread": 0.002,
        "decision_id": "drivers-test"
    }
    r = client.post("/propose", json=body)
    assert r.status_code == 200, r.text
    analysis = r.json().get("analysis") or {}
    drivers = analysis.get("drivers") or {}
    for k in ("pattern", "participation", "sector_relative_strength", "iv_minus_rv", "meme_risk"):
        assert k in drivers, f"missing driver key: {k}"


def test_features_endpoint():
    r = client.get("/features")
    assert r.status_code == 200
    data = r.json()
    assert "safeMode" in data
    assert "useLlmV2" in data
    assert "driversLegend" in data

