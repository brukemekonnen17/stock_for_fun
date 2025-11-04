"""
Unit tests for policy validators
"""
import pytest
from services.policy.validators import (
    TradePlan, MarketSnapshot, PolicyContext, PolicyVerdict, validate
)


class TestValidators:
    """Test policy validator rules"""
    
    def test_approve_valid_trade(self):
        """Should approve when all constraints are satisfied"""
        plan = TradePlan(
            ticker="AAPL",
            entry_type="limit",
            entry_price=150.0,
            stop_rule="2% below entry",
            stop_price=147.0,
            target_rule="1.5x risk",
            target_price=154.5,
            timeout_days=5,
            confidence=0.75,
            reason="Valid setup"
        )
        market = MarketSnapshot(
            price=150.0,
            spread=0.01,
            avg_dollar_vol=10_000_000
        )
        context = PolicyContext(
            open_positions=1,
            realized_pnl_today=0.0
        )
        
        verdict = validate(plan, market, context)
        
        assert verdict.verdict == "APPROVED"
        assert verdict.adjusted_size > 0
    
    def test_reject_on_kill_switch(self):
        """Should reject when daily kill-switch is triggered"""
        plan = TradePlan(
            ticker="AAPL",
            entry_type="limit",
            entry_price=150.0,
            stop_rule="2% below entry",
            stop_price=147.0,
            target_rule="1.5x risk",
            target_price=154.5,
            timeout_days=5,
            confidence=0.75,
            reason="Testing kill switch"
        )
        market = MarketSnapshot(
            price=150.0,
            spread=0.01,
            avg_dollar_vol=10_000_000
        )
        context = PolicyContext(
            open_positions=1,
            realized_pnl_today=-100.0  # Below -75 threshold
        )
        
        verdict = validate(plan, market, context)
        
        assert verdict.verdict == "REJECTED"
        assert "kill-switch" in verdict.reason.lower()
    
    def test_reject_on_max_positions(self):
        """Should reject when max concurrent positions reached"""
        plan = TradePlan(
            ticker="AAPL",
            entry_type="limit",
            entry_price=150.0,
            stop_rule="2% below entry",
            stop_price=147.0,
            target_rule="1.5x risk",
            target_price=154.5,
            timeout_days=5,
            confidence=0.75,
            reason="Testing max positions"
        )
        market = MarketSnapshot(
            price=150.0,
            spread=0.01,
            avg_dollar_vol=10_000_000
        )
        context = PolicyContext(
            open_positions=3,  # At MAX_POSITIONS limit
            realized_pnl_today=0.0
        )
        
        verdict = validate(plan, market, context)
        
        assert verdict.verdict == "REJECTED"
        assert "position" in verdict.reason.lower()
    
    def test_reject_on_low_liquidity(self):
        """Should reject when liquidity is insufficient"""
        plan = TradePlan(
            ticker="ILLQ",
            entry_type="limit",
            entry_price=150.0,
            stop_rule="2% below entry",
            stop_price=147.0,
            target_rule="1.5x risk",
            target_price=154.5,
            timeout_days=5,
            confidence=0.75,
            reason="Testing liquidity"
        )
        market = MarketSnapshot(
            price=150.0,
            spread=0.01,
            avg_dollar_vol=500_000  # Below 1M threshold
        )
        context = PolicyContext(
            open_positions=0,
            realized_pnl_today=0.0
        )
        
        verdict = validate(plan, market, context)
        
        assert verdict.verdict == "REJECTED"
        assert "liquidity" in verdict.reason.lower()
    
    def test_reject_on_wide_spread(self):
        """Should reject when spread is too wide"""
        plan = TradePlan(
            ticker="AAPL",
            entry_type="limit",
            entry_price=150.0,
            stop_rule="2% below entry",
            stop_price=147.0,
            target_rule="1.5x risk",
            target_price=154.5,
            timeout_days=5,
            confidence=0.75,
            reason="Testing spread"
        )
        market = MarketSnapshot(
            price=150.0,
            spread=0.10,  # 10 cents, above 5 cent threshold
            avg_dollar_vol=10_000_000
        )
        context = PolicyContext(
            open_positions=0,
            realized_pnl_today=0.0
        )
        
        verdict = validate(plan, market, context)
        
        assert verdict.verdict == "REJECTED"
        assert "spread" in verdict.reason.lower()
    
    def test_reject_invalid_stop(self):
        """Should reject when stop price is invalid (above entry for long)"""
        plan = TradePlan(
            ticker="AAPL",
            entry_type="limit",
            entry_price=150.0,
            stop_rule="Invalid stop",
            stop_price=152.0,  # Stop above entry - invalid for long
            target_rule="Target",
            target_price=155.0,
            timeout_days=5,
            confidence=0.75,
            reason="Testing invalid stop"
        )
        market = MarketSnapshot(
            price=150.0,
            spread=0.01,
            avg_dollar_vol=10_000_000
        )
        context = PolicyContext(
            open_positions=0,
            realized_pnl_today=0.0
        )
        
        verdict = validate(plan, market, context)
        
        assert verdict.verdict == "REJECTED"
        assert "stop" in verdict.reason.lower()


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

