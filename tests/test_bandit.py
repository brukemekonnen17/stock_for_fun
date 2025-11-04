"""
Unit tests for contextual bandit
"""
import pytest
import numpy as np
from libs.analytics.bandit import Arm, ContextualTS


class TestBandit:
    """Test Contextual Thompson Sampling bandit"""
    
    def test_initialization(self):
        """Should initialize with correct dimensions and arms"""
        d = 5
        arms = [Arm("ARM_A"), Arm("ARM_B"), Arm("SKIP")]
        
        bandit = ContextualTS(d=d, arms=arms, alpha=1.0)
        
        assert bandit.d == d
        assert len(bandit.arms) == 3
        assert "ARM_A" in bandit.A
        assert "ARM_B" in bandit.A
        
        # Check A matrices are identity
        np.testing.assert_array_equal(bandit.A["ARM_A"], np.eye(d))
        
        # Check b vectors are zero
        np.testing.assert_array_equal(bandit.b["ARM_A"], np.zeros((d, 1)))
    
    def test_select_returns_valid_arm(self):
        """Should return one of the known arms"""
        d = 5
        arms = [Arm("ARM_A"), Arm("ARM_B"), Arm("SKIP")]
        bandit = ContextualTS(d=d, arms=arms, alpha=1.0)
        
        x = np.random.randn(d)
        selected = bandit.select(x)
        
        arm_names = [a.name for a in arms]
        assert selected in arm_names
    
    def test_select_with_seed_is_deterministic(self):
        """Should be deterministic with same seed"""
        d = 5
        arms = [Arm("ARM_A"), Arm("ARM_B")]
        
        x = np.random.randn(d)
        
        # First run
        np.random.seed(42)
        bandit1 = ContextualTS(d=d, arms=arms, alpha=1.0)
        selected1 = bandit1.select(x)
        
        # Second run with same seed
        np.random.seed(42)
        bandit2 = ContextualTS(d=d, arms=arms, alpha=1.0)
        selected2 = bandit2.select(x)
        
        assert selected1 == selected2
    
    def test_update_modifies_parameters(self):
        """Should update A and b matrices after update"""
        d = 3
        arms = [Arm("ARM_A")]
        bandit = ContextualTS(d=d, arms=arms, alpha=1.0)
        
        x = np.array([1.0, 0.5, -0.3])
        reward = 0.5
        
        # Store original
        A_before = bandit.A["ARM_A"].copy()
        b_before = bandit.b["ARM_A"].copy()
        
        # Update
        bandit.update(arm_name="ARM_A", x=x, r=reward)
        
        # Check that A and b have changed
        assert not np.allclose(bandit.A["ARM_A"], A_before)
        assert not np.allclose(bandit.b["ARM_A"], b_before)
        
        # Check that Frobenius norm of A increased (more certain)
        assert np.linalg.norm(bandit.A["ARM_A"], 'fro') > np.linalg.norm(A_before, 'fro')
    
    def test_update_accumulates_evidence(self):
        """Should accumulate evidence over multiple updates"""
        d = 3
        arms = [Arm("ARM_A")]
        bandit = ContextualTS(d=d, arms=arms, alpha=1.0)
        
        # Multiple positive rewards should increase b
        x = np.array([1.0, 0.0, 0.0])
        for _ in range(10):
            bandit.update(arm_name="ARM_A", x=x, r=1.0)
        
        # b should be significantly positive for first component
        assert bandit.b["ARM_A"][0, 0] > 5.0
    
    def test_multi_arm_independence(self):
        """Updates to one arm should not affect others"""
        d = 3
        arms = [Arm("ARM_A"), Arm("ARM_B")]
        bandit = ContextualTS(d=d, arms=arms, alpha=1.0)
        
        x = np.array([1.0, 0.5, -0.3])
        
        # Store ARM_B state
        A_b_before = bandit.A["ARM_B"].copy()
        b_b_before = bandit.b["ARM_B"].copy()
        
        # Update only ARM_A
        bandit.update(arm_name="ARM_A", x=x, r=0.5)
        
        # ARM_B should be unchanged
        np.testing.assert_array_equal(bandit.A["ARM_B"], A_b_before)
        np.testing.assert_array_equal(bandit.b["ARM_B"], b_b_before)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

