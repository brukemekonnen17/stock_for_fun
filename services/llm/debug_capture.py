"""
LLM Debug Capture & Artifact Management
Captures raw LLM inputs/outputs for analysis and debugging.
"""
import os
import json
import hashlib
import logging
from pathlib import Path
from datetime import datetime
from typing import Optional, Dict, Any
from services.config.flags import flag

logger = logging.getLogger(__name__)

# Artifact storage directory
ARTIFACT_DIR = Path(__file__).parent.parent.parent / "tests" / "golden" / "raw_llm"
ARTIFACT_DIR.mkdir(parents=True, exist_ok=True)

# Version tracking
SCHEMA_VERSION = "2.0.0"
PROMPT_VERSION = "1.1.0"  # Updated: Enhanced with repair instructions, stricter field requirements
VALIDATOR_VERSION = "1.1.0"  # Updated: Added breadth downgrade, improved error handling
MODEL_NAME = "claude-3-haiku-20240307"
MODEL_VERSION = "20240307"


def redact_secrets(text: str) -> str:
    """Redact API keys and sensitive data from text."""
    import re
    # Redact API keys (x-api-key, ANTHROPIC_API_KEY, etc.)
    text = re.sub(r'["\']?x-api-key["\']?\s*:\s*["\']([^"\']+)["\']', r'"x-api-key": "[REDACTED]"', text, flags=re.IGNORECASE)
    text = re.sub(r'ANTHROPIC_API_KEY["\']?\s*[:=]\s*["\']([^"\']+)["\']', r'ANTHROPIC_API_KEY="[REDACTED]"', text, flags=re.IGNORECASE)
    return text


def classify_error(raw_response: str, parse_error: Optional[Exception] = None) -> str:
    """
    Classify LLM error by taxonomy:
    - TRANSPORT: Network/timeout errors
    - RATE_LIMIT: API rate limiting
    - FORMAT: JSON parsing/malformed response
    - SCHEMA: Schema validation failures
    - POLICY_OVERRIDE: Policy enforcement changes
    - TIMEOUT: Request timeout
    """
    if parse_error:
        error_str = str(parse_error).lower()
        if "validationerror" in error_str or "schema" in error_str:
            return "SCHEMA"
        elif "json" in error_str or "parse" in error_str or "decode" in error_str:
            return "FORMAT"
    
    if not raw_response:
        return "TRANSPORT"
    
    if "rate limit" in raw_response.lower() or "429" in raw_response:
        return "RATE_LIMIT"
    
    if "timeout" in raw_response.lower():
        return "TIMEOUT"
    
    # Try to parse JSON to see if it's a format issue
    try:
        json.loads(raw_response)
        return "SCHEMA"  # Valid JSON but schema mismatch
    except:
        return "FORMAT"  # Invalid JSON


def capture_llm_artifact(
    decision_id: str,
    ticker: str,
    raw_request: Dict[str, Any],
    raw_response: str,
    parse_success: bool,
    error_bucket: Optional[str] = None,
    parse_error: Optional[Exception] = None,
    latency_ms: float = 0.0,
    metadata: Optional[Dict[str, Any]] = None
) -> Optional[str]:
    """
    Capture LLM artifact for analysis.
    Returns path to saved artifact if successful, None otherwise.
    """
    if not flag("ENABLE_LLM_DEBUG", False):
        return None
    
    try:
        # Redact sensitive data
        redacted_request = json.loads(redact_secrets(json.dumps(raw_request)))
        redacted_response = redact_secrets(raw_response)
        
        # Classify error if parse failed
        if not parse_success and not error_bucket:
            error_bucket = classify_error(raw_response, parse_error)
        
        # Create artifact payload
        artifact = {
            "timestamp": datetime.utcnow().isoformat(),
            "decision_id": decision_id,
            "ticker": ticker,
            "versions": {
                "model_name": MODEL_NAME,
                "model_version": MODEL_VERSION,
                "prompt_version": PROMPT_VERSION,
                "schema_version": SCHEMA_VERSION,
                "validator_version": VALIDATOR_VERSION
            },
            "metrics": {
                "latency_ms": latency_ms,
                "parse_success": parse_success,
                "error_bucket": error_bucket,
                "response_length": len(raw_response) if raw_response else 0
            },
            "request": redacted_request,
            "response": redacted_response,
            "metadata": metadata or {}
        }
        
        # Generate filename with checksum
        content_hash = hashlib.sha256(
            json.dumps(artifact, sort_keys=True).encode()
        ).hexdigest()[:12]
        
        status = "success" if parse_success else "failed"
        filename = f"{ticker}_{decision_id}_{status}_{content_hash}.json"
        filepath = ARTIFACT_DIR / filename
        
        # Save artifact
        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(artifact, f, indent=2, ensure_ascii=False)
        
        logger.debug(f"[{decision_id}] Captured LLM artifact: {filepath}")
        return str(filepath)
        
    except Exception as e:
        logger.warning(f"[{decision_id}] Failed to capture LLM artifact: {e}")
        return None


def get_version_info() -> Dict[str, str]:
    """Get current version information for stamping in responses."""
    return {
        "model_name": MODEL_NAME,
        "model_version": MODEL_VERSION,
        "prompt_version": PROMPT_VERSION,
        "schema_version": SCHEMA_VERSION,
        "validator_version": VALIDATOR_VERSION
    }

