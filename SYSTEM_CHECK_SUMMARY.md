# LLM Reliability Health Program - System Check Summary

**Generated:** $(date -u +"%Y-%m-%dT%H:%M:%SZ")
**Version:** Health Check v1.0.0

## Executive Summary

This document provides a comprehensive health check of the Phase-1 LLM reliability layer, including SLO status, artifact capture, dual-path evaluation, and production readiness recommendations.

---

## Health Matrix

| Area | SLI | Target | Current | Status | Notes |
|------|-----|--------|---------|--------|-------|
| **Parse Rate (v2)** | % parsed | ≥ 99.0% | *TBD* | ⏳ | Requires 200+ calls for accurate measurement |
| **Schema Violations** | % violations | ≤ 0.5% | *TBD* | ⏳ | Tracked via error taxonomy |
| **Auto-Repair Usage** | % repaired | ≤ 10% | *TBD* | ⏳ | Allowed repairs: code fences, trailing commas |
| **P95 Latency** | seconds | ≤ 2.5s | *TBD* | ⏳ | API→LLM→parsed |
| **Timeout Rate** | % timeouts | ≤ 1% | *TBD* | ⏳ | 12s client timeout |
| **Fallback Rate (v2→v1)** | % fallbacks | ≤ 5% | *TBD* | ⏳ | Target: 0% before general rollout |
| **ECE (Calibration)** | Expected Calibration Error | ≤ 0.10 | *TBD* | ⏳ | Last 1,000 decisions |
| **Brier Score** | Trend | Non-increasing | *TBD* | ⏳ | Week-over-week |
| **UI Render Failures** | count/day | 0 | *TBD* | ⏳ | No N/A walls, no blank charts |
| **Actionability** | % actionable | 100% | *TBD* | ⏳ | Verdict + drivers + rationale |

**Legend:**
- ✅ = Passing SLO
- ⚠️ = Warning (within tolerance but not ideal)
- ❌ = Failing SLO
- ⏳ = Insufficient data (requires more samples)

---

## Version Tracking

### Current Versions (Stamped in Responses)

- **Model Name:** `claude-3-haiku-20240307`
- **Model Version:** `20240307`
- **Schema Version:** `2.0.0`
- **Prompt Version:** `1.0.0`
- **Validator Version:** `1.0.0`

### Versioning Policy

- **Schema:** Semantic versioning (MAJOR.MINOR.PATCH)
  - MAJOR: Breaking changes (requires UI updates)
  - MINOR: Backward-compatible additions
  - PATCH: Bug fixes, no schema changes
- **Prompt:** Increment when instructions change
- **Validator:** Increment when policy rules change
- **Changelogs:** See `CHANGELOG.md` (to be created)

---

## Error Taxonomy

Failures are classified into the following buckets:

| Error Type | Description | Example |
|------------|-------------|---------|
| **TRANSPORT** | Network/timeout errors | Empty response, connection refused |
| **RATE_LIMIT** | API rate limiting | HTTP 429, "rate limit" in response |
| **FORMAT** | JSON parsing/malformed response | Invalid JSON, missing quotes |
| **SCHEMA** | Schema validation failures | Missing required fields, wrong types |
| **POLICY_OVERRIDE** | Policy enforcement changes | Spread violation, pattern gating |
| **TIMEOUT** | Request timeout | Client timeout exceeded |

**Current Distribution:** *TBD* (requires artifact analysis)

---

## Artifact Capture

### Golden Corpus

Fixed tickers across regimes for reproducibility:

- **NVDA** (trending_up) - Large cap, high volatility
- **AAPL** (quiet) - Large cap, stable
- **TSLA** (trending_down) - Large cap, volatile
- **SPY** (quiet) - ETF baseline

### Artifact Storage

- **Location:** `tests/golden/raw_llm/`
- **Format:** JSON with metadata (versions, metrics, redacted request/response)
- **Retention:** 100% of failures, 5-10% sample of successes (daily rotation)
- **Redaction:** API keys, PII scrubbed

### Capture Status

- **Artifacts Captured:** *TBD* (run `scripts/capture_golden_corpus.py`)
- **Minimum Required:** ≥ 2 artifacts for analysis
- **Status:** ⏳ Pending capture

---

## Dual-Path Evaluation (LLM v1 vs v2)

### Current Architecture

- **LLM v2 (Phase-1):** Strict schema, policy enforcement, version stamping
- **LLM v1 (Legacy):** Template-based, less structured, fallback path

### Keep v1 If:

- ✅ Provider outages are non-trivial in your region
- ✅ Regulatory/compliance demands a non-LLM path
- ✅ You need a deterministic, auditable baseline for comparisons

### Retire v1 If (and only if):

- ✅ v2 parse-rate ≥ **99.5%**
- ✅ v2 fallback ≤ **1%**
- ✅ v2 matches/exceeds v1 on calibration and decision alignment for **4 consecutive weeks**
- ✅ Tested rollback to a conservative template-based "no-LLM" fallback exists

### Recommendation

**Status:** ⏳ **EVALUATION PENDING**

**Next Steps:**
1. Collect 200+ v2 calls for SLO measurement
2. Compare v1 vs v2 calibration and decision alignment
3. Document rollback procedure for template-based fallback
4. Make decision based on 4-week data window

**Interim Decision:** **KEEP v1** as fallback until v2 reliability is proven

---

## Rollout Strategy

### Canary Plan

1. **Phase 1: Shadow Mode (Optional)**
   - Run v2 in parallel, don't expose to UI
   - Compare deltas vs v1 until SLOs pass
   - **Duration:** 1-2 weeks

2. **Phase 2: Canary Ring (10% traffic)**
   - Enable v2 for 10% of requests OR fixed ticker set
   - Monitor SLOs closely
   - **Duration:** 1 week

3. **Phase 3: Gradual Rollout**
   - Increase to 50%, then 100% if SLOs hold
   - **Duration:** 2 weeks

### Auto-Degrade Rules

- **Critical:** Parse-rate < 98% (5-min window) → Auto-degrade to v1
- **Critical:** P95 latency > 3s → Auto-degrade to v1
- **Critical:** Timeouts > 2% → Auto-degrade to v1
- **Warning:** Repair-rate > 15% → Alert on-call
- **Warning:** Fallback-rate > 10% → Alert on-call

### Rollback Command

```bash
# Instant rollback via environment variable
export ENABLE_LLM_PHASE1=0

# Or via feature flag API (if implemented)
curl -X POST http://127.0.0.1:8000/features -d '{"ENABLE_LLM_PHASE1": false}'
```

### On-Call Owner

- **Primary:** *TBD*
- **Secondary:** *TBD*
- **Runbook:** `RUNBOOK_LLM_V2.md` (to be created)

---

## Compliance & Risk

### Secrets Management

- ✅ API keys redacted in logs
- ✅ No raw API keys in artifact files
- ⏳ Verify redaction in production logs

### PII Checks

- ✅ Payloads contain no user identifiers before archiving
- ⏳ Automated PII scanning (future enhancement)

### Rate Limiting

- ✅ Backoff policy: exponential (0.5s * 2^attempt)
- ✅ Max retries: 2 (configurable via `LLM_MAX_RETRIES`)
- ✅ Circuit breaker: Auto-degrade on SLO breaches

### Cost Guardrails

- ⏳ Daily token budget with alert at 80%, cutoff at 100%
- ⏳ Token usage tracking (future enhancement)

---

## Observability

### Telemetry Endpoints

- **`/metrics/llm_phase1`** - LLM quality metrics, SLO status, error taxonomy
- **`/stats/calibration`** - Calibration metrics (ECE, Brier, reliability plot)

### Alert Configuration

**Critical Alerts:**
- Parse-rate < 98% (5-min window)
- P95 latency > 3s
- Timeouts > 2%

**Warning Alerts:**
- Repair-rate > 15%
- Fallback-rate > 10%

**Alert Destination:** *TBD* (integrate with monitoring system)

---

## Testing & Validation

### Contract Tests

- ✅ Golden fixtures for success cases
- ⏳ Golden fixtures for each error bucket
- ⏳ UI smoke tests for fallback behavior

### Test Coverage

- ✅ Schema validation tests (`tests/test_llm_phase1.py`)
- ✅ Policy override tests (`tests/test_alignment_and_validator.py`)
- ⏳ Error taxonomy classification tests
- ⏳ UI render fallback tests

---

## Definition of Done

### Completed ✅

- [x] Instrumentation: Debug logging, artifact capture, version stamping
- [x] Error taxonomy: Classification system implemented
- [x] SLO definitions: Targets codified, telemetry endpoint returns status
- [x] Schema repairs: Documented allowed repairs (code fences, trailing commas)
- [x] Health check script: Expanded health check with SLO validation

### Pending ⏳

- [ ] Capture ≥2 real artifacts from golden corpus
- [ ] Compare captured outputs vs schema, update prompt/schema if needed
- [ ] Run expanded health checks and populate health matrix
- [ ] Document v1 keep/retire decision with evidence
- [ ] Configure alerts and integrate with monitoring
- [ ] Test canary rollout and auto-degrade
- [ ] Create runbook with rollback procedures

---

## Next Actions

### Immediate (This Week)

1. **Enable debug capture:** Set `ENABLE_LLM_DEBUG=1` in `.env`
2. **Run golden corpus capture:** `python scripts/capture_golden_corpus.py`
3. **Analyze artifacts:** Compare outputs vs schema, identify mismatches
4. **Update prompt/schema:** Fix any discrepancies found

### Short-term (Next 2 Weeks)

1. **Collect SLO data:** Run 200+ requests, measure parse-rate, latency, etc.
2. **Compare v1 vs v2:** Decision alignment, calibration metrics
3. **Test canary rollout:** 10% traffic, monitor SLOs
4. **Document rollback:** Create runbook with rollback procedures

### Long-term (Next Month)

1. **Evaluate v1 retirement:** Based on 4-week SLO data
2. **Production rollout:** Gradual increase to 100% if SLOs hold
3. **Cost optimization:** Token usage tracking and budget enforcement

---

## Appendix

### SLO Definitions

| SLI | Target | Measurement Window | Critical Threshold |
|-----|--------|-------------------|-------------------|
| Parse Rate | ≥ 99.0% | Last 200 calls | < 98% (5-min) |
| P95 Latency | ≤ 2.5s | Last 200 calls | > 3s |
| Timeout Rate | ≤ 1% | Last 200 calls | > 2% |
| Fallback Rate | ≤ 5% | Last 200 calls | > 10% (warning) |
| ECE | ≤ 0.10 | Last 1,000 decisions | > 0.15 (warning) |

### Version Changelog

**Schema v2.0.0** (Current)
- Initial strict schema with `extra="forbid"`
- Required fields: verdict_intraday, verdict_swing_1to5d, confidence, plan, risk, evidence_fields, missing_fields, assumptions

**Prompt v1.0.0** (Current)
- Initial prompt with 3 exemplars
- Rules for strict JSON, policy adherence, pattern inference

**Validator v1.0.0** (Current)
- Policy overrides: spread violation, pattern gating, feasibility checks
- Evidence consistency auto-downgrade
- Breadth downgrade guardrail

---

**Report Status:** ⏳ **IN PROGRESS** - Requires artifact capture and SLO data collection

**Last Updated:** $(date -u +"%Y-%m-%dT%H:%M:%SZ")
