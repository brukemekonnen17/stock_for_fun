"""
Pydantic schemas for /summarize endpoint (M1)
"""
from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any
from datetime import datetime

class ActionTemplate(BaseModel):
    """Action template from plan object"""
    entry_price: Optional[float] = Field(None, description="Entry price from plan")
    stop_price: Optional[float] = Field(None, description="Stop loss price")
    target_price: Optional[float] = Field(None, description="Target price")
    stop_pct: Optional[float] = Field(None, description="Stop loss percentage")
    target_pct: Optional[float] = Field(None, description="Target gain percentage")
    risk_reward: Optional[float] = Field(None, description="Risk/reward ratio")
    policy_ok: Optional[bool] = Field(None, description="Whether plan passes policy checks")

class SummaryMetadata(BaseModel):
    """Metadata for the summary"""
    ticker: str = Field(..., description="Stock ticker")
    run_id: str = Field(..., description="Deterministic run ID")
    timestamp: str = Field(..., description="ISO timestamp")
    prompt_version: str = Field(..., description="Prompt version for determinism")

class SummaryResponse(BaseModel):
    """Response schema for /summarize endpoint"""
    executive_summary: str = Field(
        ...,
        min_length=150,
        max_length=500,
        description="150-250 word executive summary"
    )
    decision_rationale: List[str] = Field(
        ...,
        min_items=1,
        description="Bullet points mapping to evidence fields"
    )
    risks_and_watch: List[str] = Field(
        ...,
        min_items=1,
        description="Risks from contract + additional watch items"
    )
    action_template: ActionTemplate = Field(..., description="Entry/stop/target from plan")
    metadata: SummaryMetadata = Field(..., description="Summary metadata")
    
    class Config:
        json_schema_extra = {
            "example": {
                "executive_summary": "NVDA shows a YELLOW verdict with mixed signals. Technical pattern is GREEN with sector relative strength positive, but statistical evidence is insufficient (n=2 events, all CAR values null). Economics are blocked (net_median null, blocked=true), indicating capacity concerns. The plan shows entry at $188.15 with stop at $173.15 (-8.0%) and target at $210.65 (+12.0%), but policy_ok is false, suggesting guardrail failures.",
                "decision_rationale": [
                    "Effect at H=5: Not available (insufficient events)",
                    "Pattern: GREEN - validated crossover signal",
                    "Economics: Blocked - net returns not positive after costs"
                ],
                "risks_and_watch": [
                    "Net returns not positive after costs",
                    "CAR does not support signal",
                    "Regime not aligned",
                    "Watch: Statistical power insufficient (n<10 events)"
                ],
                "action_template": {
                    "entry_price": 188.15,
                    "stop_price": 173.15,
                    "target_price": 210.65,
                    "stop_pct": -8.0,
                    "target_pct": 12.0,
                    "risk_reward": 1.5,
                    "policy_ok": False
                },
                "metadata": {
                    "ticker": "NVDA",
                    "run_id": "50b0f37965727112",
                    "timestamp": "2025-11-10T11:19:38.265299",
                    "prompt_version": "1.0.0"
                }
            }
        }

class SummarizeRequest(BaseModel):
    """Request schema for /summarize endpoint"""
    contract: Optional[Dict[str, Any]] = Field(
        None,
        description="analysis_contract.json as dictionary (alternative to file_path)"
    )
    file_path: Optional[str] = Field(
        None,
        description="Path to analysis_contract.json file (alternative to contract)"
    )
    
    class Config:
        json_schema_extra = {
            "example": {
                "file_path": "artifacts/analysis_contract.json"
            }
        }

