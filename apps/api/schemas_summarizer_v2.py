"""
Pydantic schemas for /summarize endpoint (v2 - Hardline)
Strict, rule-driven schema with contract path citations
"""
from pydantic import BaseModel, Field
from typing import List, Optional, Literal

class CIData(BaseModel):
    """95% Confidence Interval"""
    lower: Optional[float] = Field(None, description="Lower bound")
    upper: Optional[float] = Field(None, description="Upper bound")
    source: Optional[Literal["contract", "conservative", None]] = Field(None, description="CI source")

class DecisionData(BaseModel):
    """Decision evidence and gates"""
    best_horizon: Optional[int] = Field(None, description="Best horizon (lowest q with effect≥30bps)")
    q_value: Optional[float] = Field(None, description="FDR-corrected q-value")
    effect_bps: Optional[float] = Field(None, description="Effect size in basis points")
    ci_95: CIData = Field(..., description="95% confidence interval")
    economics_ok: bool = Field(..., description="Net median > 0 and not blocked")
    adv_ok: Optional[bool] = Field(None, description="ADV check passed")
    veto: Optional[Literal["YES", "NO", None]] = Field(None, description="Economics veto status")

class ActionData(BaseModel):
    """Action template (entry/stop/target)"""
    entry: Optional[float] = Field(None, description="Entry price")
    stop: Optional[float] = Field(None, description="Stop loss price")
    target: Optional[float] = Field(None, description="Target price")
    rr: Optional[float] = Field(None, description="Risk/reward ratio")

class RationalePoint(BaseModel):
    """Single rationale point with contract path citations"""
    point: str = Field(..., description="Rationale point")
    paths: List[str] = Field(..., description="Contract JSON paths cited")

class RiskItem(BaseModel):
    """Risk item with contract path citations"""
    risk: str = Field(..., description="Risk description")
    paths: List[str] = Field(..., description="Contract JSON paths cited")

class TraderLens(BaseModel):
    """Intraday trader perspective - decisive, actionable"""
    tone: str = Field(..., description="Tone: decisive, cautious, aggressive")
    playbook: dict = Field(..., description="Concrete playbook with triggers, size, stops, targets")
    what_to_watch: List[str] = Field(..., description="Key levels and signals to monitor")
    short_term_verdict: Literal["YES", "NO"] = Field(..., description="Does this work for 1-2 day trade or intraday scalp?")
    short_term_reason: str = Field(..., description="Why YES or NO for short-term opportunity")

class AnalystLens(BaseModel):
    """Professional analyst perspective - measured, risk-adjusted"""
    tone: str = Field(..., description="Tone: measured, cautious, confident")
    thesis: str = Field(..., description="Why the setup is (not) investable based on q/effect/capacity")
    risks: List[str] = Field(..., description="Key risks to watch")
    conditions_to_upgrade: List[str] = Field(..., description="What would need to change to upgrade verdict")

class EmotionLayer(BaseModel):
    """Emotion/social sentiment layer - acknowledged but clipped"""
    social_z: Optional[float] = Field(None, description="Social sentiment z-score")
    applied_weight: float = Field(..., description="Applied weight (clipped to ≤0.15)")
    narrative_bias: str = Field(..., description="One-line narrative bias from social sentiment")
    discipline: str = Field(default="Emotion can tilt REACTIVE sizing but cannot override econ gates", description="Discipline statement")

class SummaryResponseV2(BaseModel):
    """Response schema for /summarize endpoint (v2 - Hardline)"""
    ticker: str = Field(..., description="Stock ticker")
    run_id: str = Field(..., description="Deterministic run ID")
    verdict: Literal["BUY", "REVIEW", "SKIP", "REACTIVE"] = Field(..., description="Final verdict")
    reason_code: str = Field(..., description="Reason code (e.g., STATS_WEAK, ECON_VETO)")
    executive_summary: str = Field(
        ...,
        min_length=150,  # Minimum 150 words for SKIP (≈750 chars), 200+ for BUY/REVIEW
        max_length=3000,  # Allow longer executive summaries (200-300 words ≈ 1000-1500 chars)
        description="200+ word executive summary for BUY/REVIEW, 150+ for SKIP. Must explain pattern, statistical reliability, economics, decision rationale, and action guidance in plain language."
    )
    decision: DecisionData = Field(..., description="Decision evidence and gates")
    action: ActionData = Field(..., description="Action template")
    rationale: List[RationalePoint] = Field(..., min_items=1, description="Decision rationale with citations")
    risks: List[RiskItem] = Field(..., min_items=1, description="Risks with citations")
    citations: List[str] = Field(..., description="All contract paths cited")
    omissions: List[str] = Field(default_factory=list, description="Missing fields noted")
    trader_lens: Optional[TraderLens] = Field(None, description="Intraday trader perspective")
    analyst_lens: Optional[AnalystLens] = Field(None, description="Professional analyst perspective")
    emotion_layer: Optional[EmotionLayer] = Field(None, description="Emotion/social sentiment layer")
    
    class Config:
        json_schema_extra = {
            "example": {
                "ticker": "PCSA",
                "run_id": "a606661f297db1f0",
                "verdict": "SKIP",
                "reason_code": "STATS_WEAK",
                "executive_summary": "SKIP because no horizon meets q<0.10 and effect≥30 bps. Evidence shows all null values for effect, CI, p, and q across horizons H=1,3,5,10,20 (paths: evidence[*].q, evidence[*].effect). Economics are blocked (net_median=null, blocked=true, paths: economics.net_median, economics.blocked). Drivers show pattern=GREEN but insufficient statistical support. Do not commit capital.",
                "decision": {
                    "best_horizon": None,
                    "q_value": None,
                    "effect_bps": None,
                    "ci_95": {"lower": None, "upper": None, "source": None},
                    "economics_ok": False,
                    "adv_ok": None,
                    "veto": "YES"
                },
                "action": {
                    "entry": 0.31,
                    "stop": 0.22,
                    "target": 0.44,
                    "rr": 1.5
                },
                "rationale": [
                    {"point": "No horizon meets q<0.10 with ≥30 bps effect.", "paths": ["evidence[*].q", "evidence[*].effect"]},
                    {"point": "Economics blocked (net_median=null, blocked=true).", "paths": ["economics.net_median", "economics.blocked"]}
                ],
                "risks": [
                    {"risk": "Net returns not positive after costs.", "paths": ["economics.net_median"]},
                    {"risk": "CAR does not support signal.", "paths": ["evidence[*].q", "evidence[*].ci"]}
                ],
                "citations": ["evidence[*].q", "evidence[*].effect", "economics.net_median", "economics.blocked"],
                "omissions": ["No statistical evidence available; all horizons have null q/effect/ci"]
            }
        }

