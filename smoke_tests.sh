#!/bin/bash
# Smoke tests for Catalyst Scanner API
# Run with: ./smoke_tests.sh

set -e

API_URL="${API_URL:-http://localhost:8000}"
echo "Testing API at: $API_URL"
echo "================================"

# Colors
GREEN='\033[0;32m'
RED='\033[0;31m'
NC='\033[0m' # No Color

test_endpoint() {
    local name=$1
    local cmd=$2
    echo -e "\n🧪 Testing: $name"
    echo "---"
    if eval "$cmd"; then
        echo -e "${GREEN}✅ PASSED${NC}"
        return 0
    else
        echo -e "${RED}❌ FAILED${NC}"
        return 1
    fi
}

# Test 1: Health check
test_endpoint "GET /health" \
    "curl -sf $API_URL/health | jq -e '.status == \"ok\"' > /dev/null"

# Test 2: Scan endpoint
test_endpoint "GET /scan" \
    "curl -sf $API_URL/scan | jq -e 'length > 0' > /dev/null"

# Test 3: Propose (bandit + LLM)
echo -e "\n🧪 Testing: POST /propose (with full payload)"
echo "---"
PROPOSE_RESPONSE=$(curl -sf -X POST $API_URL/propose \
  -H "Content-Type: application/json" \
  -d '{
    "ticker":"AAPL",
    "price":192.50,
    "event_type":"EARNINGS",
    "days_to_event":7,
    "rank_components":{"immediacy":0.6,"materiality":0.6,"liq":1.0,"em":0.4,"news":0.5},
    "expected_move":0.04,
    "backtest_kpis":{"hit_rate":0.54,"avg_win":0.012,"avg_loss":-0.008,"max_dd":-0.06},
    "liquidity":5000000000,
    "spread":0.01,
    "news_summary":"Consensus slightly cautious; services strength noted.",
    "context":[0.6,0.6,1.0,0.4,0.5,0.04,7]
  }')

if echo "$PROPOSE_RESPONSE" | jq -e '.selected_arm and .plan' > /dev/null; then
    echo "$PROPOSE_RESPONSE" | jq .
    echo -e "${GREEN}✅ PASSED${NC}"
    SELECTED_ARM=$(echo "$PROPOSE_RESPONSE" | jq -r '.selected_arm')
    echo "Selected arm: $SELECTED_ARM"
else
    echo "$PROPOSE_RESPONSE"
    echo -e "${RED}❌ FAILED - Missing selected_arm or plan${NC}"
fi

# Test 4: Validate (with proper schema)
echo -e "\n🧪 Testing: POST /validate"
echo "---"
VALIDATE_RESPONSE=$(curl -sf -X POST $API_URL/validate \
  -H "Content-Type: application/json" \
  -d '{
    "plan":{
      "ticker":"AAPL",
      "entry_type":"limit",
      "entry_price":192.00,
      "stop_rule":"ATR14 * 1.0 below entry",
      "stop_price":189.00,
      "target_rule":"1.5 x stop",
      "target_price":196.50,
      "timeout_days":5,
      "confidence":0.72,
      "reason":"Earnings pre-setup; EM supportive."
    },
    "market":{"price":192.30,"spread":0.01,"avg_dollar_vol":5000000000},
    "context":{"open_positions":1,"realized_pnl_today":-10.0}
  }')

if echo "$VALIDATE_RESPONSE" | jq -e '.verdict' > /dev/null; then
    echo "$VALIDATE_RESPONSE" | jq .
    VERDICT=$(echo "$VALIDATE_RESPONSE" | jq -r '.verdict')
    if [ "$VERDICT" = "APPROVED" ]; then
        echo -e "${GREEN}✅ PASSED - Trade approved${NC}"
    else
        echo -e "${GREEN}✅ PASSED - Trade validation response received${NC}"
    fi
else
    echo "$VALIDATE_RESPONSE"
    echo -e "${RED}❌ FAILED - Missing verdict${NC}"
fi

# Test 5: Bandit reward
echo -e "\n🧪 Testing: POST /bandit/reward"
echo "---"
REWARD_RESPONSE=$(curl -sf -X POST $API_URL/bandit/reward \
  -H "Content-Type: application/json" \
  -d '{
    "arm_name":"POST_EVENT_MOMO",
    "context":[0.6,0.6,1.0,0.4,0.5,0.04,7],
    "reward":0.35
  }')

if echo "$REWARD_RESPONSE" | jq -e '.status == "ok"' > /dev/null; then
    echo "$REWARD_RESPONSE" | jq .
    echo -e "${GREEN}✅ PASSED${NC}"
else
    echo "$REWARD_RESPONSE"
    echo -e "${RED}❌ FAILED${NC}"
fi

# Test 6: Daily kill-switch
echo -e "\n🧪 Testing: Daily kill-switch (should reject)"
echo "---"
KILLSWITCH_RESPONSE=$(curl -sf -X POST $API_URL/validate \
  -H "Content-Type: application/json" \
  -d '{
    "plan":{
      "ticker":"AAPL",
      "entry_type":"limit",
      "entry_price":192.00,
      "stop_rule":"ATR14 * 1.0 below entry",
      "stop_price":189.00,
      "target_rule":"1.5 x stop",
      "target_price":196.50,
      "timeout_days":5,
      "confidence":0.72,
      "reason":"Testing kill switch"
    },
    "market":{"price":192.30,"spread":0.01,"avg_dollar_vol":5000000000},
    "context":{"open_positions":1,"realized_pnl_today":-100.0}
  }')

VERDICT=$(echo "$KILLSWITCH_RESPONSE" | jq -r '.verdict')
if [ "$VERDICT" = "REJECTED" ]; then
    REASON=$(echo "$KILLSWITCH_RESPONSE" | jq -r '.reason')
    echo "Verdict: $VERDICT"
    echo "Reason: $REASON"
    if echo "$REASON" | grep -qi "kill"; then
        echo -e "${GREEN}✅ PASSED - Kill-switch triggered correctly${NC}"
    else
        echo -e "${RED}❌ FAILED - Rejected but not for kill-switch${NC}"
    fi
else
    echo -e "${RED}❌ FAILED - Should have been rejected${NC}"
fi

# Test 7: Spread too wide
echo -e "\n🧪 Testing: Spread validation (should reject wide spread)"
echo "---"
SPREAD_RESPONSE=$(curl -sf -X POST $API_URL/validate \
  -H "Content-Type: application/json" \
  -d '{
    "plan":{
      "ticker":"AAPL",
      "entry_type":"limit",
      "entry_price":192.00,
      "stop_rule":"ATR14 * 1.0 below entry",
      "stop_price":189.00,
      "target_rule":"1.5 x stop",
      "target_price":196.50,
      "timeout_days":5,
      "confidence":0.72,
      "reason":"Testing spread check"
    },
    "market":{"price":192.30,"spread":0.10,"avg_dollar_vol":5000000000},
    "context":{"open_positions":1,"realized_pnl_today":0.0}
  }')

VERDICT=$(echo "$SPREAD_RESPONSE" | jq -r '.verdict')
if [ "$VERDICT" = "REJECTED" ]; then
    REASON=$(echo "$SPREAD_RESPONSE" | jq -r '.reason')
    echo "Verdict: $VERDICT"
    echo "Reason: $REASON"
    echo -e "${GREEN}✅ PASSED - Wide spread rejected${NC}"
else
    echo -e "${RED}❌ FAILED - Should have rejected wide spread${NC}"
fi

echo -e "\n================================"
echo -e "${GREEN}✅ Smoke tests complete!${NC}"

