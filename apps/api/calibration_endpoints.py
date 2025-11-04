"""
API endpoints for calibration diagnostics and management.
"""
from fastapi import APIRouter, HTTPException
from typing import Dict
import logging
from services.analysis.calibration import get_calibration_service

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/calibration", tags=["calibration"])

@router.get("/metrics")
def get_calibration_metrics() -> Dict:
    """
    Get current calibration metrics (ECE, Brier score, sample count).
    """
    service = get_calibration_service()
    metrics = service.compute_metrics()
    return metrics

@router.get("/reliability-plot")
def get_reliability_plot_data(n_bins: int = 10) -> Dict:
    """
    Get data for reliability (calibration) plot.
    Shows predicted confidence vs actual accuracy.
    """
    service = get_calibration_service()
    return service.get_reliability_plot_data(n_bins=n_bins)

@router.post("/recalibrate")
def trigger_recalibration(method: str = "isotonic") -> Dict:
    """
    Manually trigger recalibration.
    
    Args:
        method: "isotonic" or "platt"
    """
    if method not in ["isotonic", "platt"]:
        raise HTTPException(status_code=400, detail="Method must be 'isotonic' or 'platt'")
    
    service = get_calibration_service()
    service.fit_calibration(method=method)
    
    metrics = service.compute_metrics()
    return {
        "status": "recalibrated",
        "method": method,
        "metrics": metrics
    }

@router.get("/stats")
def get_calibration_stats() -> Dict:
    """
    Get calibration statistics summary.
    """
    service = get_calibration_service()
    metrics = service.compute_metrics()
    plot_data = service.get_reliability_plot_data()
    
    return {
        "metrics": metrics,
        "reliability_plot": plot_data,
        "method": service.calibration_method,
        "total_records": len(service.records),
        "completed_records": len([r for r in service.records if r.actual_outcome >= 0])
    }

