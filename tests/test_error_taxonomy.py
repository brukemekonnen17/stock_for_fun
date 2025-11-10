"""
Test error taxonomy classification and schema repair logic.
"""
import pytest
import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from services.llm.debug_capture import classify_error
from apps.api.schemas_llm import parse_llm_json, TradeAnalysisV2


def test_classify_transport_error():
    """Empty response should be classified as TRANSPORT."""
    assert classify_error("", None) == "TRANSPORT"
    assert classify_error(None, None) == "TRANSPORT"


def test_classify_rate_limit_error():
    """Rate limit responses should be classified as RATE_LIMIT."""
    assert classify_error('{"error": "rate limit exceeded"}', None) == "RATE_LIMIT"
    assert classify_error('HTTP 429: Too Many Requests', None) == "RATE_LIMIT"


def test_classify_timeout_error():
    """Timeout responses should be classified as TIMEOUT."""
    assert classify_error('Request timeout after 12s', None) == "TIMEOUT"


def test_classify_schema_error():
    """Valid JSON but schema mismatch should be SCHEMA."""
    # Valid JSON but missing required fields
    valid_json = '{"verdict_intraday": "BUY"}'
    assert classify_error(valid_json, None) == "SCHEMA"


def test_classify_format_error():
    """Invalid JSON should be FORMAT."""
    invalid_json = '{"verdict_intraday": "BUY"'
    assert classify_error(invalid_json, None) == "FORMAT"


def test_classify_validation_error():
    """ValidationError should be classified as SCHEMA."""
    from pydantic import ValidationError
    try:
        TradeAnalysisV2.model_validate({"verdict_intraday": "BUY"})
    except ValidationError as e:
        assert classify_error('{}', e) == "SCHEMA"


def test_parse_repair_code_fences():
    """parse_llm_json should repair code fences."""
    # Valid response wrapped in code fences
    valid_response = '```json\n{"schema":"TradeAnalysisV2","verdict_intraday":"BUY","verdict_swing_1to5d":"SKIP","confidence":0.7,"room":{},"pattern":{},"participation":{},"catalyst_alignment":{},"meme_social":{},"plan":{},"risk":{},"evidence_fields":[],"missing_fields":[],"assumptions":{}}\n```'
    
    result = parse_llm_json(valid_response)
    assert result is not None
    assert result.schema == "TradeAnalysisV2"
    assert result.verdict_intraday == "BUY"


def test_parse_repair_trailing_comma():
    """parse_llm_json should repair trailing commas."""
    # Valid JSON with trailing comma
    valid_with_comma = '{"schema":"TradeAnalysisV2","verdict_intraday":"BUY","verdict_swing_1to5d":"SKIP","confidence":0.7,"room":{},"pattern":{},"participation":{},"catalyst_alignment":{},"meme_social":{},"plan":{},"risk":{},"evidence_fields":[],"missing_fields":[],"assumptions":{},}'
    
    result = parse_llm_json(valid_with_comma)
    assert result is not None
    assert result.schema == "TradeAnalysisV2"


def test_parse_reject_missing_fields():
    """parse_llm_json should reject responses missing required fields."""
    incomplete = '{"verdict_intraday":"BUY","confidence":0.7}'
    result = parse_llm_json(incomplete)
    assert result is None


def test_parse_reject_invalid_confidence():
    """parse_llm_json should reject confidence outside [0.5, 1.0]."""
    invalid_confidence = '{"schema":"TradeAnalysisV2","verdict_intraday":"BUY","verdict_swing_1to5d":"SKIP","confidence":0.3,"room":{},"pattern":{},"participation":{},"catalyst_alignment":{},"meme_social":{},"plan":{},"risk":{},"evidence_fields":[],"missing_fields":[],"assumptions":{}}'
    
    result = parse_llm_json(invalid_confidence)
    assert result is None


def test_parse_reject_extra_fields():
    """parse_llm_json should reject extra fields (extra='forbid')."""
    with_extra = '{"schema":"TradeAnalysisV2","verdict_intraday":"BUY","verdict_swing_1to5d":"SKIP","confidence":0.7,"room":{},"pattern":{},"participation":{},"catalyst_alignment":{},"meme_social":{},"plan":{},"risk":{},"evidence_fields":[],"missing_fields":[],"assumptions":{},"extra_field":"should_fail"}'
    
    result = parse_llm_json(with_extra)
    assert result is None


def test_parse_empty_string():
    """parse_llm_json should return None for empty string."""
    assert parse_llm_json("") is None
    assert parse_llm_json("   ") is None

