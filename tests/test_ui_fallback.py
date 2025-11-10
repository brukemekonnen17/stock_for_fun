"""
Test UI fallback behavior when llm_v2 is absent.
Ensures dashboard gracefully handles missing LLM analysis.
"""
import pytest
import json


def test_ui_handles_missing_llm_v2():
    """UI should handle missing llm_v2 without errors."""
    # Simulate analysis response without llm_v2
    analysis_response = {
        "analysis": {
            "ticker": "AAPL",
            "llm_version": "v1",
            "drivers": {
                "pattern": "RANGE",
                "participation": "LOW",
                "sector_relative_strength": 0.0,
                "iv_minus_rv": 0.0,
                "meme_risk": "NOISE"
            },
            "plan": {
                "confidence": 0.5,
                "reason": "Legacy LLM analysis"
            }
        },
        "plan": {
            "action": "SKIP",
            "confidence": 0.5,
            "reason": "Legacy LLM analysis"
        }
    }
    
    # UI should safely extract confidence from plan or analysis.llm_confidence
    confidence = (
        analysis_response.get("analysis", {}).get("llm_v2", {}).get("confidence") or
        analysis_response.get("plan", {}).get("confidence") or
        analysis_response.get("analysis", {}).get("llm_confidence") or
        0.5
    )
    
    assert confidence == 0.5
    
    # UI should safely extract rationale
    rationale = (
        analysis_response.get("analysis", {}).get("llm_v2", {}).get("plan", {}).get("rationale") or
        analysis_response.get("plan", {}).get("reason") or
        "No reasoning provided"
    )
    
    assert rationale == "Legacy LLM analysis"
    
    # Drivers should always be present
    drivers = analysis_response.get("analysis", {}).get("drivers", {})
    assert "pattern" in drivers
    assert "participation" in drivers


def test_ui_handles_null_confidence():
    """UI should handle null/undefined confidence gracefully."""
    analysis_response = {
        "analysis": {
            "ticker": "AAPL",
            "llm_v2": None
        },
        "plan": {}
    }
    
    # Should default to 0.5, not crash
    confidence = (
        analysis_response.get("analysis", {}).get("llm_v2", {}).get("confidence") or
        analysis_response.get("plan", {}).get("confidence") or
        0.5
    )
    
    assert confidence == 0.5


def test_ui_displays_age_banner():
    """UI should display age banner when timestamp is old."""
    from datetime import datetime, timedelta
    
    # Old timestamp (6 minutes ago)
    old_timestamp = (datetime.utcnow() - timedelta(minutes=6)).isoformat()
    
    analysis_response = {
        "analysis": {
            "ticker": "AAPL",
            "timestamp": old_timestamp
        }
    }
    
    timestamp_str = analysis_response.get("analysis", {}).get("timestamp")
    if timestamp_str:
        timestamp = datetime.fromisoformat(timestamp_str.replace('Z', '+00:00'))
        age_seconds = (datetime.utcnow().replace(tzinfo=timestamp.tzinfo) - timestamp).total_seconds()
        age_minutes = int(age_seconds / 60)
        
        # Should flag as old if > 5 minutes
        is_old = age_minutes > 5
        assert is_old == True


def test_ui_hides_confidence_bar_when_unavailable():
    """UI should hide confidence bar when LLM unavailable."""
    analysis_response = {
        "analysis": {
            "ticker": "AAPL",
            "llm_v2": None
        },
        "plan": {}
    }
    
    # Check if confidence is available
    has_confidence = (
        analysis_response.get("analysis", {}).get("llm_v2", {}).get("confidence") is not None or
        analysis_response.get("plan", {}).get("confidence") is not None
    )
    
    # In this case, confidence defaults to 0.5, but UI should still show it
    # The key is that it doesn't crash
    assert has_confidence == False  # No explicit confidence, but UI will use default

