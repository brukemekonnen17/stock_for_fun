"""
Response contracts for "why selected" explanations.
Facts are computed deterministically; LLM only explains, never invents.
"""
from pydantic import BaseModel, Field
from datetime import datetime
from typing import List, Optional, Literal

ArmName = Literal["EARNINGS_PRE", "POST_EVENT_MOMO", "NEWS_SPIKE", "REACTIVE", "SKIP"]

class NewsItem(BaseModel):
    headline: str
    url: str
    timestamp: datetime
    sentiment: float = Field(ge=-1, le=1, description="Sentiment score: -1 (very negative) to 1 (very positive)")

class PerfStats(BaseModel):
    horizon_days: int = 5
    samples: int
    hit_rate: float
    avg_win: float
    avg_loss: float
    median_r: float
    p90_r: float
    max_dd: float

class CatalystInfo(BaseModel):
    event_type: Literal["EARNINGS", "FDA_PDUFA", "TRIAL_READOUT", "GUIDANCE", "PARTNERSHIP", "DIVIDEND", "SPLIT"]
    event_time: datetime
    days_to_event: float
    materiality: float = Field(ge=0, le=1, description="Materiality score: 0 (low) to 1 (high impact)")
    expected_move: float  # fraction, e.g., 0.04 = 4%
    rank: float  # 0..100, CatalystRank

class MarketContext(BaseModel):
    price: float
    spread: float
    dollar_adv: float  # Average dollar volume
    rsi14: Optional[float] = Field(None, ge=0, le=100, description="RSI(14) indicator")
    atr14: Optional[float] = Field(None, ge=0, description="ATR(14) in dollars")

class StrategyRationale(BaseModel):
    selected_arm: ArmName
    reason: str  # one-liner why this arm
    gating_facts: List[str]  # bullet list of hard checks that passed

class WhySelected(BaseModel):
    ticker: str
    catalyst: CatalystInfo
    strategy: StrategyRationale
    news: List[NewsItem]
    history: PerfStats
    market: MarketContext
    llm_confidence: float = Field(ge=0.5, le=1.0, description="LLM confidence in the trade plan")

