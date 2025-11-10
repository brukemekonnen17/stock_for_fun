# LLM Reliability Health Program - Quick Start

## Overview

This document provides a quick reference for the LLM Reliability Health Program implementation. For detailed documentation, see `SYSTEM_CHECK_SUMMARY.md`.

## Implementation Status

✅ **Completed:**
- Instrumentation: Debug logging, artifact capture, version stamping
- Error taxonomy: Classification system (TRANSPORT, RATE_LIMIT, FORMAT, SCHEMA, POLICY_OVERRIDE, TIMEOUT)
- SLO definitions: Targets codified, telemetry endpoint returns status
- Schema repairs: Documented allowed repairs (code fences, trailing commas)
- Health check scripts: Expanded health check with SLO validation
- Dual-path evaluation: Criteria documented for v1 keep/retire decision
- Tests: Error taxonomy tests, UI fallback tests, validator tests

⏳ **Pending (Requires Runtime Data):**
- Capture ≥2 real artifacts from golden corpus
- Run health checks and populate health matrix with actual metrics
- Compare v1 vs v2 calibration and decision alignment

## Quick Commands

### Enable Debug Capture

```bash
# Set in .env
export ENABLE_LLM_DEBUG=1
export ENABLE_LLM_PHASE1=1
```

### Capture Golden Corpus

```bash
python scripts/capture_golden_corpus.py
```

### Analyze Captured Artifacts

```bash
python scripts/analyze_artifacts.py
```

### Run Health Check

```bash
bash scripts/health_check_expanded.sh
```

### Check LLM Metrics

```bash
curl http://127.0.0.1:8000/metrics/llm_phase1 | jq
```

### Check Calibration Metrics

```bash
curl http://127.0.0.1:8000/stats/calibration | jq
```

## SLO Targets

| SLI | Target | Critical Threshold |
|-----|--------|-------------------|
| Parse Rate | ≥ 99.0% | < 98% (5-min) |
| P95 Latency | ≤ 2.5s | > 3s |
| Timeout Rate | ≤ 1% | > 2% |
| Fallback Rate | ≤ 5% | > 10% (warning) |
| ECE | ≤ 0.10 | > 0.15 (warning) |

## Version Tracking

All LLM responses include version information:
- Model: `claude-3-haiku-20240307`
- Schema: `2.0.0`
- Prompt: `1.1.0`
- Validator: `1.1.0`

## Error Taxonomy

Failures are classified into:
- **TRANSPORT**: Network/timeout errors
- **RATE_LIMIT**: API rate limiting
- **FORMAT**: JSON parsing errors
- **SCHEMA**: Schema validation failures
- **POLICY_OVERRIDE**: Policy enforcement changes
- **TIMEOUT**: Request timeout

## Rollout Strategy

1. **Shadow Mode** (optional): Run v2 in parallel, compare vs v1
2. **Canary** (10% traffic): Monitor SLOs closely
3. **Gradual Rollout**: Increase to 50%, then 100% if SLOs hold

## Auto-Degrade Rules

- Parse-rate < 98% → Auto-degrade to v1
- P95 latency > 3s → Auto-degrade to v1
- Timeouts > 2% → Auto-degrade to v1

## Rollback

```bash
# Instant rollback
export ENABLE_LLM_PHASE1=0
```

## Artifact Storage

- **Location:** `tests/golden/raw_llm/`
- **Format:** JSON with metadata (versions, metrics, redacted request/response)
- **Retention:** 100% of failures, 5-10% sample of successes

## Next Steps

1. Enable debug capture (`ENABLE_LLM_DEBUG=1`)
2. Run golden corpus capture
3. Analyze artifacts and update prompt/schema if needed
4. Collect 200+ requests for SLO measurement
5. Compare v1 vs v2 calibration and decision alignment
6. Make v1 keep/retire decision based on 4-week data

## Documentation

- **Detailed Health Report:** `SYSTEM_CHECK_SUMMARY.md`
- **Error Taxonomy Tests:** `tests/test_error_taxonomy.py`
- **UI Fallback Tests:** `tests/test_ui_fallback.py`
- **Validator Tests:** `tests/test_llm_phase1.py`

