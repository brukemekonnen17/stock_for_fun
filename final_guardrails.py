#!/usr/bin/env python3
"""
Final Guardrails - Production Safety Hardening
Implements the remaining guardrails for production safety.
"""

import json
import time
from pathlib import Path
from typing import Dict, Any


def add_evidence_decision_coherence_asserts(investor_card: Dict[str, Any]) -> None:
    """
    FINAL GUARDRAIL #3: Evidence/Decision Coherence Assert
    
    Before saving the investor card:
    - If veto=YES ⇒ verdict ∈ {SKIP, REVIEW}
    - If q < 0.10 but effect < 0.003 (30 bps) ⇒ significance = False
    """
    economics = investor_card.get('economics', {})
    evidence = investor_card.get('evidence', {})
    verdict = investor_card.get('verdict', 'UNKNOWN')
    
    # Assert 1: veto=YES ⇒ verdict ∈ {SKIP, REVIEW}
    impact_veto = economics.get('impact_veto', False)
    if impact_veto and verdict not in {'SKIP', 'REVIEW'}:
        raise ValueError(
            f"Coherence violation: impact_veto=YES but verdict={verdict} "
            f"(must be SKIP or REVIEW)"
        )
    
    # Assert 2: q < 0.10 but effect < 30 bps ⇒ significance = False
    q_val = evidence.get('q_value')
    effect_bps = evidence.get('effect_bps', 0.0)
    is_significant = evidence.get('significant', False)
    
    if q_val is not None and q_val < 0.10:
        if effect_bps < 30.0:  # 30 basis points
            if is_significant:
                raise ValueError(
                    f"Coherence violation: q={q_val:.4f} < 0.10 but effect={effect_bps:.1f}bps < 30bps, "
                    f"yet significant=True (should be False)"
                )
    
    print("✅ Evidence/decision coherence asserts passed")


def check_min_events_per_horizon(xover_stats, min_events: int = 10) -> Dict[str, bool]:
    """
    FINAL GUARDRAIL #2: Min events per horizon (n ≥ 10)
    
    Require n ≥ 10 for any horizon to be eligible for significance;
    otherwise mark as insufficient power and exclude from verdict scoring.
    """
    if xover_stats is None or xover_stats.empty:
        return {}
    
    horizon_eligibility = {}
    for _, row in xover_stats.iterrows():
        H = row.get('H', 0)
        n_ev = row.get('n_ev', row.get('n', 0))
        eligible = n_ev >= min_events
        horizon_eligibility[f'H{H}'] = eligible
        
        if not eligible:
            print(f"⚠️  H={H}: Insufficient power (n={n_ev} < {min_events}) - excluded from verdict")
    
    return horizon_eligibility


def check_runtime_cap(start_time: float, max_seconds: int = 30 * 60) -> None:
    """
    FINAL GUARDRAIL #2: Max runtime cap
    
    Fail if runtime > max_seconds (prevents CI hangs).
    """
    elapsed = time.time() - start_time
    if elapsed > max_seconds:
        raise RuntimeError(
            f"Max runtime exceeded: {elapsed:.1f}s > {max_seconds}s "
            f"(limit: {max_seconds/60:.1f} minutes)"
        )


def save_provider_to_run_meta(provider_name: str, run_meta_path: Path) -> None:
    """
    FINAL GUARDRAIL #1: Log provider used into run_meta.json
    """
    if not run_meta_path.exists():
        return
    
    try:
        with open(run_meta_path, 'r') as f:
            run_meta = json.load(f)
        
        run_meta['provider_name'] = provider_name
        run_meta['provider_logged_at'] = time.strftime('%Y-%m-%d %H:%M:%S UTC', time.gmtime())
        
        with open(run_meta_path, 'w') as f:
            json.dump(run_meta, f, indent=2)
        
        print(f"✅ Provider logged to run_meta.json: {provider_name}")
    except Exception as e:
        print(f"⚠️  Could not log provider to run_meta: {e}")


if __name__ == "__main__":
    print("Final Guardrails Module")
    print("Import this module to use guardrail functions")

