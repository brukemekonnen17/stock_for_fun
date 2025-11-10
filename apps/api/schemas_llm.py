from pydantic import BaseModel, Field, ConfigDict, ValidationError
from typing import Literal, List, Dict, Optional, Union


class StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class TradeAnalysisV2(StrictModel):
    schema: Literal["TradeAnalysisV2"]
    verdict_intraday: Literal["BUY", "SELL", "SKIP", "REACTIVE"]
    verdict_swing_1to5d: Literal["BUY", "SELL", "SKIP"]
    confidence: float = Field(ge=0.5, le=1.0)
    room: Dict[str, Union[float, str]]
    pattern: Dict[str, object]
    participation: Dict[str, object]
    catalyst_alignment: Dict[str, object]
    meme_social: Dict[str, object]
    plan: Dict[str, object]
    risk: Dict[str, object]
    evidence: Optional[Dict[str, object]] = None
    evidence_fields: List[str]
    missing_fields: List[str]
    assumptions: Dict[str, object]
    statistical_analysis: Optional[Dict[str, object]] = None  # Enhanced statistical interpretation


def parse_llm_json(s: str) -> Optional["TradeAnalysisV2"]:
    """
    Parse LLM JSON response with detailed error capture.
    Returns TradeAnalysisV2 object or None if parsing fails.
    
    Allowed repairs:
    - Strip code fences (```json, ```)
    - Remove trailing commas (if valid JSON otherwise)
    
    All other modifications require schema updates.
    """
    if not s or not s.strip():
        return None
    
    try:
        # Allowed repair #1: Strip code fences if present (common LLM output)
        cleaned = s.strip()
        if cleaned.startswith("```json"):
            cleaned = cleaned[7:]
        elif cleaned.startswith("```"):
            cleaned = cleaned[3:]
        if cleaned.endswith("```"):
            cleaned = cleaned[:-3]
        cleaned = cleaned.strip()
        
        # Allowed repair #2: Try to remove trailing commas in arrays/objects
        # (This is a common JSON mistake that doesn't require schema change)
        import re
        # Remove trailing commas before closing brackets/braces
        cleaned = re.sub(r',(\s*[}\]])', r'\1', cleaned)
        
        return TradeAnalysisV2.model_validate_json(cleaned)
    except ValidationError as e:
        # Re-raise with context for artifact capture
        raise
    except Exception as e:
        # Wrap other exceptions for classification
        raise ValueError(f"JSON parse error: {str(e)}") from e

