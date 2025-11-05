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


def parse_llm_json(s: str) -> Optional["TradeAnalysisV2"]:
    try:
        return TradeAnalysisV2.model_validate_json(s)
    except Exception:
        return None

