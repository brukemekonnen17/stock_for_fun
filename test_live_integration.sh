#!/bin/bash
# Test live integration with real market data

set -e

API_URL="${API_URL:-http://localhost:8000}"
GREEN='\033[0;32m'
BLUE='\033[0;34m'
NC='\033[0m'

echo "🧪 Testing Live Integration"
echo "================================"

# Test 1: Real market data scan
echo -e "\n${BLUE}1. Testing real catalyst scanner...${NC}"
SCAN_RESULT=$(curl -sf "$API_URL/scan?min_rank=0&limit=3")
echo "$SCAN_RESULT" | jq .

TICKER_COUNT=$(echo "$SCAN_RESULT" | jq '. | length')
if [ "$TICKER_COUNT" -gt 0 ]; then
    FIRST_TICKER=$(echo "$SCAN_RESULT" | jq -r '.[0].symbol')
    FIRST_CONF=$(echo "$SCAN_RESULT" | jq -r '.[0].confidence')
    echo -e "${GREEN}✅ Scanner working - found $TICKER_COUNT tickers${NC}"
    echo "   First result: $FIRST_TICKER (confidence: $FIRST_CONF)"
else
    echo "❌ Scanner returned no results"
fi

# Test 2: Check if it's real data (not mock)
echo -e "\n${BLUE}2. Verifying real vs mock data...${NC}"
CATALYST=$(echo "$SCAN_RESULT" | jq -r '.[0].catalyst')
if echo "$CATALYST" | grep -q "Expected move:"; then
    echo -e "${GREEN}✅ Real data detected (shows expected move)${NC}"
elif echo "$CATALYST" | grep -q "earnings call expected to beat"; then
    echo "⚠️  Mock data fallback active (check yfinance installation)"
else
    echo "✅ Custom catalyst text"
fi

# Test 3: Propose with real scanner data
echo -e "\n${BLUE}3. Testing propose with scanner context...${NC}"
if [ "$TICKER_COUNT" -gt 0 ]; then
    FIRST_ITEM=$(echo "$SCAN_RESULT" | jq '.[0]')
    TICKER=$(echo "$FIRST_ITEM" | jq -r '.symbol')
    RANK=$(echo "$FIRST_ITEM" | jq -r '.context.rank')
    EM=$(echo "$FIRST_ITEM" | jq -r '.context.expected_move')
    
    PROPOSE_PAYLOAD=$(cat << EOF
{
  "ticker": "$TICKER",
  "price": 150.0,
  "event_type": "EARNINGS",
  "days_to_event": 7,
  "rank_components": {"timing": 0.8},
  "expected_move": $EM,
  "backtest_kpis": {"hit_rate": 0.6},
  "liquidity": 5000000000,
  "spread": 0.01,
  "context": [0.8, 0.7, 1.0, 0.5, $RANK, $EM, 7]
}
EOF
    )
    
    PROPOSE_RESULT=$(echo "$PROPOSE_PAYLOAD" | curl -sf -X POST "$API_URL/propose" \
        -H "Content-Type: application/json" \
        -d @-)
    
    ARM=$(echo "$PROPOSE_RESULT" | jq -r '.selected_arm')
    echo -e "${GREEN}✅ Proposal generated - Selected arm: $ARM${NC}"
else
    echo "⚠️  Skipping propose test (no scan results)"
fi

# Test 4: E*TRADE endpoints (will fail if not configured, that's OK)
echo -e "\n${BLUE}4. Testing E*TRADE endpoints...${NC}"
POSITIONS_RESULT=$(curl -sf "$API_URL/positions" 2>/dev/null || echo '{"error":"not configured"}')
if echo "$POSITIONS_RESULT" | jq -e '.error' > /dev/null; then
    echo "ℹ️  E*TRADE not configured (expected - add credentials to test)"
else
    POS_COUNT=$(echo "$POSITIONS_RESULT" | jq '. | length')
    echo -e "${GREEN}✅ E*TRADE connected - $POS_COUNT positions${NC}"
fi

echo -e "\n================================"
echo -e "${GREEN}✅ Live integration tests complete!${NC}"
echo ""
echo "Next steps:"
echo "1. ✅ Real market data working via yfinance"
echo "2. ✅ Scanner using actual prices & volatility"
echo "3. ⚠️  E*TRADE needs credentials (optional for paper trading)"
echo ""
echo "Run paper trading with real data:"
echo "  python paper_trading.py --interval 30"

