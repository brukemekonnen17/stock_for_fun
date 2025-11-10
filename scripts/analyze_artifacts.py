#!/usr/bin/env python3
"""
Analyze captured LLM artifacts to identify schema mismatches.
Compares actual outputs vs expected schema and generates a diff report.
"""
import sys
import json
from pathlib import Path
from collections import defaultdict

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from apps.api.schemas_llm import TradeAnalysisV2, parse_llm_json
import re


def detect_repairs(raw_response: str) -> dict:
    """
    Detect if repairs were needed (code fences, trailing commas).
    Returns dict with repair flags and original state.
    """
    repairs = {
        "code_fence_stripped": False,
        "trailing_comma_removed": False,
        "original_has_code_fence": False,
        "original_has_trailing_comma": False
    }
    
    if not raw_response:
        return repairs
    
    # Check for code fences
    cleaned = raw_response.strip()
    if cleaned.startswith("```json") or cleaned.startswith("```"):
        repairs["original_has_code_fence"] = True
        repairs["code_fence_stripped"] = True
    
    # Check for trailing commas (before closing brackets/braces)
    if re.search(r',(\s*[}\]])', cleaned):
        repairs["original_has_trailing_comma"] = True
        repairs["trailing_comma_removed"] = True
    
    return repairs


def analyze_artifact(artifact_path: Path):
    """Analyze a single artifact file."""
    with open(artifact_path, 'r') as f:
        artifact = json.load(f)
    
    raw_response = artifact.get("response", "")
    parse_success = artifact.get("metrics", {}).get("parse_success", False)
    error_bucket = artifact.get("metrics", {}).get("error_bucket")
    
    result = {
        "file": artifact_path.name,
        "ticker": artifact.get("ticker"),
        "decision_id": artifact.get("decision_id"),
        "parse_success": parse_success,
        "error_bucket": error_bucket,
        "response_length": len(raw_response),
        "issues": []
    }
    
    if not parse_success:
        # Try to parse and capture the error
        try:
            parsed = parse_llm_json(raw_response)
            if parsed is None:
                result["issues"].append("parse_llm_json returned None (no detailed error)")
        except Exception as e:
            result["issues"].append(f"Parse exception: {type(e).__name__}: {str(e)}")
            
            # Try to validate against schema to get field-level errors
            try:
                # Try to parse as JSON first
                json_data = json.loads(raw_response)
                
                # Try to validate against schema
                try:
                    TradeAnalysisV2.model_validate(json_data)
                except Exception as schema_error:
                    if hasattr(schema_error, 'errors'):
                        for error in schema_error.errors():
                            field = ".".join(str(x) for x in error.get("loc", []))
                            error_type = error.get("type")
                            error_msg = error.get("msg")
                            result["issues"].append(f"Schema field error: {field} - {error_type}: {error_msg}")
                    else:
                        result["issues"].append(f"Schema validation error: {str(schema_error)}")
            except json.JSONDecodeError:
                result["issues"].append("Invalid JSON format")
            except Exception as e2:
                result["issues"].append(f"Unexpected error during validation: {str(e2)}")
    else:
        # Parse succeeded - check for any warnings or inconsistencies
        try:
            parsed = parse_llm_json(raw_response)
            if parsed:
                # Check for missing critical fields
                if not parsed.plan:
                    result["issues"].append("Warning: plan field is empty")
                if not parsed.evidence_fields:
                    result["issues"].append("Warning: evidence_fields is empty")
                if parsed.confidence < 0.5 or parsed.confidence > 1.0:
                    result["issues"].append(f"Warning: confidence out of bounds: {parsed.confidence}")
        except Exception as e:
            result["issues"].append(f"Unexpected error re-parsing: {str(e)}")
    
    return result


def main():
    """Analyze all artifacts and generate report."""
    artifact_dir = project_root / "tests" / "golden" / "raw_llm"
    
    if not artifact_dir.exists():
        print(f"❌ Artifact directory not found: {artifact_dir}")
        print("   Run: python scripts/capture_golden_corpus.py")
        return
    
    artifacts = list(artifact_dir.glob("*.json"))
    
    if not artifacts:
        print(f"⚠️  No artifacts found in {artifact_dir}")
        print("   Run: python scripts/capture_golden_corpus.py")
        return
    
    print("=" * 60)
    print("LLM Artifact Analysis")
    print("=" * 60)
    print(f"Found {len(artifacts)} artifacts")
    print()
    
    results = []
    error_summary = defaultdict(int)
    
    for artifact_path in artifacts:
        result = analyze_artifact(artifact_path)
        results.append(result)
        
        if result["parse_success"]:
            print(f"✅ {result['ticker']} ({result['file']}): Parse succeeded")
        else:
            print(f"❌ {result['ticker']} ({result['file']}): Parse failed ({result['error_bucket']})")
            error_summary[result["error_bucket"]] += 1
            if result["issues"]:
                for issue in result["issues"]:
                    print(f"   - {issue}")
    
    print()
    print("=" * 60)
    print("Error Summary")
    print("=" * 60)
    for error_type, count in sorted(error_summary.items()):
        print(f"  {error_type}: {count}")
    
    print()
    print("=" * 60)
    print("Recommendations")
    print("=" * 60)
    
    if error_summary.get("SCHEMA", 0) > 0:
        print("⚠️  Schema errors detected:")
        print("   1. Review captured artifacts for missing fields")
        print("   2. Update PROMPTS/LLM_SYSTEM.md to enforce required fields")
        print("   3. Consider schema relaxation if fields are truly optional")
    
    if error_summary.get("FORMAT", 0) > 0:
        print("⚠️  Format errors detected:")
        print("   1. Check if LLM is returning valid JSON")
        print("   2. Verify code fence stripping is working")
        print("   3. Consider adding more repair logic (if needed)")
    
    if error_summary.get("TRANSPORT", 0) > 0:
        print("⚠️  Transport errors detected:")
        print("   1. Check API connectivity")
        print("   2. Verify ANTHROPIC_API_KEY is set")
        print("   3. Check rate limits and timeouts")
    
    # Save detailed report
    report_path = project_root / "tests" / "golden" / "raw_llm" / "analysis_report.json"
    with open(report_path, 'w') as f:
        json.dump({
            "timestamp": __import__('datetime').datetime.utcnow().isoformat(),
            "total_artifacts": len(results),
            "parse_success_count": sum(1 for r in results if r["parse_success"]),
            "parse_fail_count": sum(1 for r in results if not r["parse_success"]),
            "error_summary": dict(error_summary),
            "detailed_results": results
        }, f, indent=2)
    
    print()
    print(f"✅ Detailed report saved to: {report_path}")


if __name__ == "__main__":
    main()

