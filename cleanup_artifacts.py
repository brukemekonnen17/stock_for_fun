#!/usr/bin/env python3
"""
Artifact Cleanup Script - 30-day TTL
FINAL GUARDRAIL #4: Artifact retention

Keeps only payload artifacts (JSON, CSV) for determinism hashing;
purges HTML/PNGs older than 30 days.
"""

import os
import time
from pathlib import Path
from datetime import datetime, timedelta


def cleanup_artifacts(artifacts_dir: Path = Path("artifacts"), ttl_days: int = 30) -> None:
    """
    Clean up artifacts older than TTL days.
    
    Keeps:
    - investor_card.json
    - run_meta.json
    - analysis_contract.json
    - xover_stats.csv (if exists)
    
    Removes:
    - HTML files older than TTL
    - PNG files older than TTL
    - Other temporary files
    """
    if not artifacts_dir.exists():
        print(f"Artifacts directory not found: {artifacts_dir}")
        return
    
    ttl_seconds = ttl_days * 24 * 60 * 60
    cutoff_time = time.time() - ttl_seconds
    
    # Files to always keep (payload artifacts)
    keep_files = {
        "investor_card.json",
        "run_meta.json",
        "analysis_contract.json",
        "xover_stats.csv"
    }
    
    removed_count = 0
    kept_count = 0
    
    for artifact_file in artifacts_dir.glob("*"):
        if not artifact_file.is_file():
            continue
        
        # Always keep payload artifacts
        if artifact_file.name in keep_files:
            kept_count += 1
            continue
        
        # Remove HTML/PNG files older than TTL
        if artifact_file.suffix in {'.html', '.png'}:
            file_mtime = artifact_file.stat().st_mtime
            if file_mtime < cutoff_time:
                try:
                    artifact_file.unlink()
                    removed_count += 1
                    print(f"🗑️  Removed: {artifact_file.name} (age: {(time.time() - file_mtime) / (24*60*60):.1f} days)")
                except Exception as e:
                    print(f"⚠️  Could not remove {artifact_file.name}: {e}")
            else:
                kept_count += 1
    
    print(f"\n✅ Cleanup complete: {removed_count} removed, {kept_count} kept")
    print(f"   TTL: {ttl_days} days")


if __name__ == "__main__":
    import sys
    
    ttl = int(sys.argv[1]) if len(sys.argv) > 1 else 30
    cleanup_artifacts(ttl_days=ttl)

