from pydantic import BaseModel, Field
import os

# Import StrictModel after apps.api is initialized to avoid circular import
# For now, use BaseModel with model_config in validators module
try:
    from apps.api.schemas_base import StrictModel
except ImportError:
    # Fallback if schemas_base not available yet
    class StrictModel(BaseModel):
        model_config = {"extra": "forbid"}

# Guardrails (from env with defaults)
MAX_TICKET = float(os.getenv("MAX_TICKET", 500))
MAX_POSITIONS = int(os.getenv("MAX_POSITIONS", 3))
MAX_PER_TRADE_LOSS = float(os.getenv("MAX_PER_TRADE_LOSS", 25))
DAILY_KILL_SWITCH = float(os.getenv("DAILY_KILL_SWITCH", -75))
SPREAD_CENTS_MAX = float(os.getenv("SPREAD_CENTS_MAX", 0.05))  # 5¢
SPREAD_BPS_MAX = float(os.getenv("SPREAD_BPS_MAX", 50))        # 0.5%
SLIPPAGE_BPS = float(os.getenv("SLIPPAGE_BPS", 10))            # 0.10%

class MarketSnapshot(StrictModel):
    price: float
    spread: float            # dollars
    avg_dollar_vol: float

class TradePlan(StrictModel):
    ticker: str
    entry_type: str = Field(pattern=r"^(limit|market|trigger)$")
    entry_price: float
    stop_rule: str           # textual rule (resolved upstream)
    stop_price: float
    target_rule: str
    target_price: float
    timeout_days: int = Field(ge=1, le=10)
    confidence: float = Field(ge=0.5, le=1.0)
    reason: str

class PolicyContext(StrictModel):
    open_positions: int
    realized_pnl_today: float

class PolicyVerdict(StrictModel):
    verdict: str  # APPROVED | REJECTED | REVIEW
    reason: str
    adjusted_size: int

def _spread_ok(spread: float, price: float) -> bool:
    bps_ok = (spread / price) * 10000 <= SPREAD_BPS_MAX if price > 0 else False
    cents_ok = spread <= SPREAD_CENTS_MAX
    return bps_ok and cents_ok

def validate(plan: TradePlan, mkt: MarketSnapshot, ctx: PolicyContext) -> PolicyVerdict:
    if ctx.realized_pnl_today <= DAILY_KILL_SWITCH:
        return PolicyVerdict(verdict="REJECTED", reason="Daily kill-switch triggered", adjusted_size=0)

    if ctx.open_positions >= MAX_POSITIONS:
        return PolicyVerdict(verdict="REJECTED", reason="Max concurrent positions reached", adjusted_size=0)

    if mkt.avg_dollar_vol < 1_000_000:
        return PolicyVerdict(verdict="REJECTED", reason="Insufficient liquidity", adjusted_size=0)

    if not _spread_ok(mkt.spread, mkt.price):
        return PolicyVerdict(verdict="REJECTED", reason="Spread too wide", adjusted_size=0)

    # Worst-case entry: half-spread adverse + slippage bps
    worst_entry = plan.entry_price + (mkt.spread / 2.0) + (plan.entry_price * (SLIPPAGE_BPS / 10_000))
    loss_per_share = max(worst_entry - plan.stop_price, 0.0)
    if loss_per_share <= 0:
        return PolicyVerdict(verdict="REJECTED", reason="Invalid stop (non-positive distance)", adjusted_size=0)

    max_shares_ticket = int(MAX_TICKET // max(worst_entry, 1e-6))
    if max_shares_ticket <= 0:
        return PolicyVerdict(verdict="REJECTED", reason="Ticket too small for price", adjusted_size=0)

    allowed_by_loss = int(MAX_PER_TRADE_LOSS // loss_per_share)
    final_shares = max(0, min(max_shares_ticket, allowed_by_loss))

    if final_shares == 0:
        return PolicyVerdict(verdict="REJECTED", reason="Per-trade loss would exceed cap", adjusted_size=0)

    return PolicyVerdict(verdict="APPROVED", reason="All checks passed", adjusted_size=final_shares)

