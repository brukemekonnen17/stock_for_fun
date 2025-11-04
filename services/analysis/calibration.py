"""
Calibration diagnostics and recalibration for LLM confidence.
Tracks predicted confidence vs actual outcomes and applies isotonic/Platt recalibration.
"""
import numpy as np
from typing import List, Tuple, Optional, Dict
from dataclasses import dataclass
from datetime import datetime, timedelta
import logging
try:
    from sklearn.isotonic import IsotonicRegression
    from sklearn.linear_model import LogisticRegression
    SKLEARN_AVAILABLE = True
except ImportError:
    SKLEARN_AVAILABLE = False
    logger.warning("scikit-learn not available, calibration will use simple linear interpolation")
import json
import os

logger = logging.getLogger(__name__)

@dataclass
class CalibrationRecord:
    """Single record of predicted confidence and actual outcome."""
    decision_id: str
    ticker: str
    predicted_confidence: float
    actual_outcome: int  # 1 for success, 0 for failure
    timestamp: datetime
    arm_name: str
    reward: Optional[float] = None

class CalibrationService:
    """
    Service for tracking and recalibrating LLM confidence predictions.
    """
    
    def __init__(self, storage_path: Optional[str] = None):
        """
        Initialize calibration service.
        
        Args:
            storage_path: Path to JSON file for persistent storage. If None, uses in-memory only.
        """
        self.storage_path = storage_path or os.path.join(
            os.path.dirname(__file__), '..', '..', 'calibration_data.json'
        )
        self.records: List[CalibrationRecord] = []
        self.isotonic_model: Optional[IsotonicRegression] = None
        self.platt_model: Optional[LogisticRegression] = None
        self.calibration_method: str = "isotonic"  # or "platt"
        self._load_records()
    
    def _load_records(self):
        """Load calibration records from disk."""
        if os.path.exists(self.storage_path):
            try:
                with open(self.storage_path, 'r') as f:
                    data = json.load(f)
                    self.records = [
                        CalibrationRecord(
                            decision_id=r['decision_id'],
                            ticker=r['ticker'],
                            predicted_confidence=r['predicted_confidence'],
                            actual_outcome=r['actual_outcome'],
                            timestamp=datetime.fromisoformat(r['timestamp']),
                            arm_name=r.get('arm_name', ''),
                            reward=r.get('reward')
                        )
                        for r in data.get('records', [])
                    ]
                logger.info(f"Loaded {len(self.records)} calibration records")
            except Exception as e:
                logger.warning(f"Failed to load calibration records: {e}")
                self.records = []
    
    def _save_records(self):
        """Save calibration records to disk."""
        try:
            data = {
                'records': [
                    {
                        'decision_id': r.decision_id,
                        'ticker': r.ticker,
                        'predicted_confidence': r.predicted_confidence,
                        'actual_outcome': r.actual_outcome,
                        'timestamp': r.timestamp.isoformat(),
                        'arm_name': r.arm_name,
                        'reward': r.reward
                    }
                    for r in self.records
                ],
                'last_updated': datetime.utcnow().isoformat()
            }
            with open(self.storage_path, 'w') as f:
                json.dump(data, f, indent=2)
        except Exception as e:
            logger.error(f"Failed to save calibration records: {e}")
    
    def record_prediction(
        self,
        decision_id: str,
        ticker: str,
        predicted_confidence: float,
        arm_name: str = ""
    ):
        """
        Record a new prediction (before outcome is known).
        
        Args:
            decision_id: Unique decision identifier
            ticker: Stock ticker
            predicted_confidence: LLM's predicted confidence (0-1)
            arm_name: Selected bandit arm
        """
        record = CalibrationRecord(
            decision_id=decision_id,
            ticker=ticker,
            predicted_confidence=max(0.0, min(1.0, predicted_confidence)),
            actual_outcome=-1,  # Not yet determined
            timestamp=datetime.utcnow(),
            arm_name=arm_name
        )
        self.records.append(record)
        self._save_records()
    
    def record_outcome(
        self,
        decision_id: str,
        actual_outcome: int,
        reward: Optional[float] = None
    ):
        """
        Record the actual outcome for a prediction.
        
        Args:
            decision_id: Decision identifier
            actual_outcome: 1 for success, 0 for failure
            reward: Optional reward value
        """
        for record in self.records:
            if record.decision_id == decision_id:
                record.actual_outcome = actual_outcome
                if reward is not None:
                    record.reward = reward
                self._save_records()
                return
        
        logger.warning(f"Decision ID {decision_id} not found for outcome recording")
    
    def _get_training_data(self, min_samples: int = 20) -> Tuple[np.ndarray, np.ndarray]:
        """
        Get training data for calibration models.
        
        Returns:
            (predicted_confidences, actual_outcomes) arrays
        """
        completed = [
            (r.predicted_confidence, r.actual_outcome)
            for r in self.records
            if r.actual_outcome >= 0
        ]
        
        if len(completed) < min_samples:
            logger.warning(f"Only {len(completed)} completed records, need {min_samples} for calibration")
            return np.array([]), np.array([])
        
        predicted = np.array([c[0] for c in completed])
        actual = np.array([c[1] for c in completed])
        
        return predicted, actual
    
    def fit_calibration(self, method: str = "isotonic"):
        """
        Fit calibration model using completed predictions.
        
        Args:
            method: "isotonic" or "platt"
        """
        predicted, actual = self._get_training_data()
        
        if len(predicted) == 0:
            logger.warning("No training data available for calibration")
            return
        
        self.calibration_method = method
        
        if method == "isotonic":
            if SKLEARN_AVAILABLE:
                self.isotonic_model = IsotonicRegression(out_of_bounds='clip')
                self.isotonic_model.fit(predicted, actual)
                logger.info(f"Fitted isotonic calibration model on {len(predicted)} samples")
            else:
                # Simple linear interpolation fallback
                sorted_indices = np.argsort(predicted)
                sorted_pred = predicted[sorted_indices]
                sorted_actual = actual[sorted_indices]
                # Store as sorted arrays for interpolation
                self.isotonic_model = {
                    'sorted_pred': sorted_pred,
                    'sorted_actual': sorted_actual
                }
                logger.info(f"Fitted simple isotonic calibration (fallback) on {len(predicted)} samples")
        
        elif method == "platt":
            if SKLEARN_AVAILABLE:
                # Platt scaling: logistic regression on log-odds
                # Transform confidence to log-odds space
                predicted_log_odds = np.log(predicted / (1 - predicted + 1e-10) + 1e-10)
                predicted_log_odds = predicted_log_odds.reshape(-1, 1)
                
                self.platt_model = LogisticRegression()
                self.platt_model.fit(predicted_log_odds, actual)
                logger.info(f"Fitted Platt calibration model on {len(predicted)} samples")
            else:
                logger.warning("Platt scaling requires scikit-learn, falling back to isotonic")
                self.fit_calibration(method="isotonic")
        
        else:
            raise ValueError(f"Unknown calibration method: {method}")
    
    def calibrate_confidence(self, raw_confidence: float) -> float:
        """
        Apply calibration to raw confidence score.
        
        Args:
            raw_confidence: Raw confidence from LLM (0-1)
        
        Returns:
            Calibrated confidence (0-1)
        """
        if len(self._get_training_data()[0]) < 20:
            # Not enough data for calibration, return raw
            return max(0.0, min(1.0, raw_confidence))
        
        if self.calibration_method == "isotonic" and self.isotonic_model is not None:
            if SKLEARN_AVAILABLE and hasattr(self.isotonic_model, 'predict'):
                calibrated = self.isotonic_model.predict([raw_confidence])[0]
            else:
                # Fallback: linear interpolation
                model = self.isotonic_model
                if isinstance(model, dict) and 'sorted_pred' in model:
                    sorted_pred = model['sorted_pred']
                    sorted_actual = model['sorted_actual']
                    calibrated = np.interp(raw_confidence, sorted_pred, sorted_actual)
                else:
                    calibrated = raw_confidence
            return max(0.0, min(1.0, calibrated))
        
        elif self.calibration_method == "platt" and self.platt_model is not None:
            if SKLEARN_AVAILABLE:
                log_odds = np.log(raw_confidence / (1 - raw_confidence + 1e-10) + 1e-10)
                calibrated = self.platt_model.predict_proba([[log_odds]])[0][1]
            else:
                calibrated = raw_confidence
            return max(0.0, min(1.0, calibrated))
        
        # Fallback to raw confidence
        return max(0.0, min(1.0, raw_confidence))
    
    def compute_metrics(self) -> Dict[str, float]:
        """
        Compute calibration metrics (ECE, Brier score).
        
        Returns:
            Dict with 'ece', 'brier', 'n_samples'
        """
        predicted, actual = self._get_training_data()
        
        if len(predicted) == 0:
            return {
                "ece": 0.0,
                "brier": 0.0,
                "n_samples": 0
            }
        
        # Brier score
        brier = np.mean((predicted - actual) ** 2)
        
        # Expected Calibration Error (ECE)
        n_bins = min(10, len(predicted) // 5)
        if n_bins < 2:
            return {
                "ece": 0.0,
                "brier": float(brier),
                "n_samples": len(predicted)
            }
        
        bin_edges = np.linspace(0, 1, n_bins + 1)
        ece = 0.0
        total_weight = 0.0
        
        for i in range(n_bins):
            bin_mask = (predicted >= bin_edges[i]) & (predicted < bin_edges[i+1])
            if i == n_bins - 1:  # Include upper bound for last bin
                bin_mask = (predicted >= bin_edges[i]) & (predicted <= bin_edges[i+1])
            
            if np.sum(bin_mask) > 0:
                bin_probs = predicted[bin_mask]
                bin_outcomes = actual[bin_mask]
                bin_weight = len(bin_probs)
                bin_accuracy = np.mean(bin_outcomes)
                bin_confidence = np.mean(bin_probs)
                
                ece += bin_weight * abs(bin_accuracy - bin_confidence)
                total_weight += bin_weight
        
        ece = ece / total_weight if total_weight > 0 else 0.0
        
        return {
            "ece": float(ece),
            "brier": float(brier),
            "n_samples": len(predicted)
        }
    
    def get_reliability_plot_data(self, n_bins: int = 10) -> Dict:
        """
        Get data for reliability (calibration) plot.
        
        Returns:
            Dict with 'bin_centers', 'bin_accuracies', 'bin_confidences', 'bin_counts'
        """
        predicted, actual = self._get_training_data()
        
        if len(predicted) == 0:
            return {
                "bin_centers": [],
                "bin_accuracies": [],
                "bin_confidences": [],
                "bin_counts": []
            }
        
        bin_edges = np.linspace(0, 1, n_bins + 1)
        bin_centers = []
        bin_accuracies = []
        bin_confidences = []
        bin_counts = []
        
        for i in range(n_bins):
            bin_mask = (predicted >= bin_edges[i]) & (predicted < bin_edges[i+1])
            if i == n_bins - 1:
                bin_mask = (predicted >= bin_edges[i]) & (predicted <= bin_edges[i+1])
            
            if np.sum(bin_mask) > 0:
                bin_centers.append((bin_edges[i] + bin_edges[i+1]) / 2)
                bin_accuracies.append(float(np.mean(actual[bin_mask])))
                bin_confidences.append(float(np.mean(predicted[bin_mask])))
                bin_counts.append(int(np.sum(bin_mask)))
        
        return {
            "bin_centers": bin_centers,
            "bin_accuracies": bin_accuracies,
            "bin_confidences": bin_confidences,
            "bin_counts": bin_counts
        }
    
    def auto_recalibrate(self, min_samples: int = 20):
        """
        Automatically refit calibration models if enough new data is available.
        """
        predicted, actual = self._get_training_data(min_samples)
        
        if len(predicted) >= min_samples:
            self.fit_calibration(method=self.calibration_method)
            return True
        return False


# Global calibration service instance
_calibration_service: Optional[CalibrationService] = None

def get_calibration_service() -> CalibrationService:
    """Get or create global calibration service instance."""
    global _calibration_service
    if _calibration_service is None:
        _calibration_service = CalibrationService()
    return _calibration_service

def set_calibration_service(service: CalibrationService):
    """Set global calibration service instance."""
    global _calibration_service
    _calibration_service = service

