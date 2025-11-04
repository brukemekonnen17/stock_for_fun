"""
Bandit state persistence utilities
"""
import json
import pickle
import logging
from pathlib import Path
from typing import Optional
import numpy as np

logger = logging.getLogger(__name__)


class BanditStatePersistence:
    """Save and load bandit state (A/b matrices) to/from disk"""
    
    def __init__(self, state_dir: str = "./bandit_state"):
        self.state_dir = Path(state_dir)
        self.state_dir.mkdir(parents=True, exist_ok=True)
    
    def save(self, bandit, bandit_id: str = "default"):
        """
        Save bandit state to disk.
        
        Args:
            bandit: ContextualTS instance
            bandit_id: Identifier for this bandit (e.g., "d5" for 5-dim context)
        """
        try:
            state_file = self.state_dir / f"{bandit_id}.pkl"
            
            state = {
                "d": bandit.d,
                "alpha": bandit.alpha,
                "arm_names": [a.name for a in bandit.arms],
                "A": {k: v for k, v in bandit.A.items()},
                "b": {k: v for k, v in bandit.b.items()}
            }
            
            with open(state_file, 'wb') as f:
                pickle.dump(state, f)
            
            logger.info(f"Saved bandit state to {state_file}")
            
        except Exception as e:
            logger.error(f"Failed to save bandit state: {e}", exc_info=True)
    
    def load(self, bandit, bandit_id: str = "default") -> bool:
        """
        Load bandit state from disk.
        
        Args:
            bandit: ContextualTS instance to update
            bandit_id: Identifier for this bandit
            
        Returns:
            True if loaded successfully, False otherwise
        """
        try:
            state_file = self.state_dir / f"{bandit_id}.pkl"
            
            if not state_file.exists():
                logger.info(f"No saved state found at {state_file}")
                return False
            
            with open(state_file, 'rb') as f:
                state = pickle.load(f)
            
            # Validate dimensions
            if state["d"] != bandit.d:
                logger.warning(f"Dimension mismatch: saved={state['d']}, current={bandit.d}")
                return False
            
            # Restore state
            bandit.alpha = state["alpha"]
            bandit.A = state["A"]
            bandit.b = state["b"]
            
            logger.info(f"Loaded bandit state from {state_file}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to load bandit state: {e}", exc_info=True)
            return False
    
    def export_json(self, bandit, bandit_id: str = "default"):
        """
        Export bandit state to JSON (for inspection, not for loading).
        Converts numpy arrays to lists for JSON serialization.
        """
        try:
            json_file = self.state_dir / f"{bandit_id}.json"
            
            state = {
                "d": bandit.d,
                "alpha": bandit.alpha,
                "arm_names": [a.name for a in bandit.arms],
                "A": {k: v.tolist() for k, v in bandit.A.items()},
                "b": {k: v.tolist() for k, v in bandit.b.items()}
            }
            
            with open(json_file, 'w') as f:
                json.dump(state, f, indent=2)
            
            logger.info(f"Exported bandit state to {json_file}")
            
        except Exception as e:
            logger.error(f"Failed to export bandit state: {e}", exc_info=True)

