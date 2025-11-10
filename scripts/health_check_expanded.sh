#!/usr/bin/env bash
set -euo pipefail

# Expanded Health Check Script
# Runs comprehensive health checks and generates a health matrix

API_BASE="${API_BASE:-http://127.0.0.1:8000}"
OUTPUT_FILE="${OUTPUT_FILE:-SYSTEM_CHECK_SUMMARY.md}"

echo "=== Expanded Health Check ==="
echo "Timestamp: $(date -u +"%Y-%m-%dT%H:%M:%SZ")"
echo "API Base: $API_BASE"
echo ""

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Initialize results
declare -A results
declare -A slo_status

# 1. Health endpoints
echo "1. Health Endpoints"
echo "-------------------"
for endpoint in "/healthz" "/readiness" "/features"; do
    if curl -sf "${API_BASE}${endpoint}" > /dev/null 2>&1; then
        echo -e "${GREEN}✅${NC} ${endpoint}"
        results["health_${endpoint}"]="pass"
    else
        echo -e "${RED}❌${NC} ${endpoint}"
        results["health_${endpoint}"]="fail"
    fi
done
echo ""

# 2. LLM Metrics
echo "2. LLM Phase-1 Metrics"
echo "----------------------"
METRICS=$(curl -sf "${API_BASE}/metrics/llm_phase1" 2>/dev/null || echo "{}")
if [ "$METRICS" != "{}" ]; then
    PARSE_RATE=$(echo "$METRICS" | jq -r '.parse_rate // 0')
    P95_LATENCY=$(echo "$METRICS" | jq -r '.p95_latency_ms // 0')
    FALLBACK_RATE=$(echo "$METRICS" | jq -r '.fallback_rate // 0')
    TIMEOUT_RATE=$(echo "$METRICS" | jq -r '.timeout_rate // 0')
    OVERRIDE_RATE=$(echo "$METRICS" | jq -r '.policy_override_rate // 0')
    
    # Check SLOs
    SLO_PARSE_RATE=0.99
    SLO_P95_LATENCY=2500.0
    SLO_FALLBACK=0.05
    SLO_TIMEOUT=0.01
    SLO_OVERRIDE=0.10
    
    if (( $(echo "$PARSE_RATE >= $SLO_PARSE_RATE" | bc -l) )); then
        slo_status["parse_rate"]="pass"
        echo -e "${GREEN}✅${NC} Parse Rate: ${PARSE_RATE} (target: ≥${SLO_PARSE_RATE})"
    else
        slo_status["parse_rate"]="fail"
        echo -e "${RED}❌${NC} Parse Rate: ${PARSE_RATE} (target: ≥${SLO_PARSE_RATE})"
    fi
    
    if (( $(echo "$P95_LATENCY <= $SLO_P95_LATENCY" | bc -l) )); then
        slo_status["p95_latency"]="pass"
        echo -e "${GREEN}✅${NC} P95 Latency: ${P95_LATENCY}ms (target: ≤${SLO_P95_LATENCY}ms)"
    else
        slo_status["p95_latency"]="fail"
        echo -e "${RED}❌${NC} P95 Latency: ${P95_LATENCY}ms (target: ≤${SLO_P95_LATENCY}ms)"
    fi
    
    if (( $(echo "$FALLBACK_RATE <= $SLO_FALLBACK" | bc -l) )); then
        slo_status["fallback_rate"]="pass"
        echo -e "${GREEN}✅${NC} Fallback Rate: ${FALLBACK_RATE} (target: ≤${SLO_FALLBACK})"
    else
        slo_status["fallback_rate"]="fail"
        echo -e "${RED}❌${NC} Fallback Rate: ${FALLBACK_RATE} (target: ≤${SLO_FALLBACK})"
    fi
    
    if (( $(echo "$TIMEOUT_RATE <= $SLO_TIMEOUT" | bc -l) )); then
        slo_status["timeout_rate"]="pass"
        echo -e "${GREEN}✅${NC} Timeout Rate: ${TIMEOUT_RATE} (target: ≤${SLO_TIMEOUT})"
    else
        slo_status["timeout_rate"]="fail"
        echo -e "${RED}❌${NC} Timeout Rate: ${TIMEOUT_RATE} (target: ≤${SLO_TIMEOUT})"
    fi
    
    if (( $(echo "$OVERRIDE_RATE <= $SLO_OVERRIDE" | bc -l) )); then
        slo_status["policy_override_rate"]="pass"
        echo -e "${GREEN}✅${NC} Policy Override Rate: ${OVERRIDE_RATE} (target: ≤${SLO_OVERRIDE})"
    else
        slo_status["policy_override_rate"]="fail"
        echo -e "${RED}❌${NC} Policy Override Rate: ${OVERRIDE_RATE} (target: ≤${SLO_OVERRIDE})"
    fi
else
    echo -e "${YELLOW}⚠️${NC}  Metrics endpoint unavailable"
    results["llm_metrics"]="unavailable"
fi
echo ""

# 3. Calibration Metrics
echo "3. Calibration Metrics"
echo "----------------------"
CAL_METRICS=$(curl -sf "${API_BASE}/stats/calibration" 2>/dev/null || echo "{}")
if [ "$CAL_METRICS" != "{}" ]; then
    ECE=$(echo "$CAL_METRICS" | jq -r '.ece // 0')
    BRIER=$(echo "$CAL_METRICS" | jq -r '.brier // 0')
    N_SAMPLES=$(echo "$CAL_METRICS" | jq -r '.n_samples // 0')
    
    SLO_ECE=0.10
    if (( $(echo "$ECE <= $SLO_ECE" | bc -l) )); then
        slo_status["ece"]="pass"
        echo -e "${GREEN}✅${NC} ECE: ${ECE} (target: ≤${SLO_ECE})"
    else
        slo_status["ece"]="fail"
        echo -e "${RED}❌${NC} ECE: ${ECE} (target: ≤${SLO_ECE})"
    fi
    
    echo "   Brier Score: ${BRIER}"
    echo "   Samples: ${N_SAMPLES}"
else
    echo -e "${YELLOW}⚠️${NC}  Calibration endpoint unavailable"
fi
echo ""

# 4. Test /propose endpoint
echo "4. Test /propose Endpoint (AAPL)"
echo "---------------------------------"
PROPOSE_RESPONSE=$(curl -sf -X POST "${API_BASE}/propose" \
    -H "Content-Type: application/json" \
    -d '{
        "ticker": "AAPL",
        "price": 190.0,
        "event_type": "EARNINGS",
        "days_to_event": 5.0,
        "expected_move": 0.04,
        "context": [0.6,0.6,1,0.4,0.5,0.04,5],
        "rank_components": {},
        "backtest_kpis": {},
        "liquidity": 10000000,
        "spread": 0.002,
        "decision_id": "health-check-aapl"
    }' 2>/dev/null || echo "{}")

if [ "$PROPOSE_RESPONSE" != "{}" ]; then
    HAS_LLM_V2=$(echo "$PROPOSE_RESPONSE" | jq -r '.analysis.llm_v2 != null')
    LLM_VERSION=$(echo "$PROPOSE_RESPONSE" | jq -r '.analysis.llm_version // "unknown"')
    HAS_DRIVERS=$(echo "$PROPOSE_RESPONSE" | jq -r '.analysis.drivers != null')
    HAS_SERIES=$(echo "$PROPOSE_RESPONSE" | jq -r '.analysis.series != null')
    
    if [ "$HAS_LLM_V2" = "true" ]; then
        echo -e "${GREEN}✅${NC} llm_v2 present"
        results["propose_llm_v2"]="pass"
    else
        echo -e "${RED}❌${NC} llm_v2 missing"
        results["propose_llm_v2"]="fail"
    fi
    
    echo "   LLM Version: ${LLM_VERSION}"
    
    if [ "$HAS_DRIVERS" = "true" ]; then
        echo -e "${GREEN}✅${NC} drivers present"
    else
        echo -e "${RED}❌${NC} drivers missing"
    fi
    
    if [ "$HAS_SERIES" = "true" ]; then
        echo -e "${GREEN}✅${NC} series data present"
    else
        echo -e "${YELLOW}⚠️${NC}  series data missing (non-critical)"
    fi
else
    echo -e "${RED}❌${NC} /propose endpoint failed"
    results["propose_endpoint"]="fail"
fi
echo ""

# 5. Check artifact capture
echo "5. Artifact Capture"
echo "-------------------"
ARTIFACT_DIR="tests/golden/raw_llm"
if [ -d "$ARTIFACT_DIR" ]; then
    ARTIFACT_COUNT=$(find "$ARTIFACT_DIR" -name "*.json" 2>/dev/null | wc -l | tr -d ' ')
    echo "   Artifacts captured: ${ARTIFACT_COUNT}"
    if [ "$ARTIFACT_COUNT" -ge 2 ]; then
        echo -e "${GREEN}✅${NC} Sufficient artifacts (≥2)"
        results["artifacts"]="pass"
    else
        echo -e "${YELLOW}⚠️${NC}  Insufficient artifacts (<2)"
        results["artifacts"]="partial"
    fi
else
    echo -e "${YELLOW}⚠️${NC}  Artifact directory not found"
    results["artifacts"]="missing"
fi
echo ""

# 6. Generate summary
echo "=== Health Check Summary ==="
echo ""
echo "Status:"
for key in "${!results[@]}"; do
    status="${results[$key]}"
    if [ "$status" = "pass" ]; then
        echo -e "${GREEN}✅${NC} ${key}"
    elif [ "$status" = "fail" ]; then
        echo -e "${RED}❌${NC} ${key}"
    else
        echo -e "${YELLOW}⚠️${NC}  ${key} (${status})"
    fi
done

echo ""
echo "SLO Status:"
for key in "${!slo_status[@]}"; do
    status="${slo_status[$key]}"
    if [ "$status" = "pass" ]; then
        echo -e "${GREEN}✅${NC} ${key}"
    else
        echo -e "${RED}❌${NC} ${key}"
    fi
done

echo ""
echo "Health check complete. See ${OUTPUT_FILE} for detailed report."

