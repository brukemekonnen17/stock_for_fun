#!/bin/bash
# E*TRADE OAuth Setup Helper
# This script guides you through getting access tokens

set -e

API_URL="${API_URL:-http://localhost:8000}"
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
NC='\033[0m'

echo -e "${BLUE}================================"
echo "E*TRADE OAuth Setup"
echo -e "================================${NC}"
echo ""

# Check if API is running
if ! curl -sf "$API_URL/health" > /dev/null 2>&1; then
    echo -e "${YELLOW}⚠️  API not running. Start it first:${NC}"
    echo "   uvicorn apps.api.main:app --reload"
    exit 1
fi

# Check if consumer keys are set
if ! grep -q "ETRADE_CONSUMER_KEY=9fab" .env 2>/dev/null; then
    echo -e "${YELLOW}⚠️  Consumer keys not found in .env${NC}"
    echo ""
    echo "Add to .env:"
    echo "ETRADE_CONSUMER_KEY=9fab270c43a476a2b0b61fbad0a60bb8"
    echo "ETRADE_CONSUMER_SECRET=3c201d071c6086057092715c5b6b35195011e6580abac84dae657d527f76ba32"
    echo "ETRADE_SANDBOX=true"
    echo ""
    exit 1
fi

echo -e "${GREEN}✓ Consumer keys found${NC}"
echo ""

# Step 1: Request token
echo -e "${BLUE}Step 1: Requesting OAuth token...${NC}"
RESPONSE=$(curl -sf -X POST "$API_URL/oauth/request_token" \
    -H "Content-Type: application/json" \
    -d '{"callback":"oob"}')

if [ $? -ne 0 ]; then
    echo -e "${YELLOW}❌ Failed to get request token. Check API logs.${NC}"
    exit 1
fi

OAUTH_TOKEN=$(echo "$RESPONSE" | jq -r '.oauth_token')
OAUTH_TOKEN_SECRET=$(echo "$RESPONSE" | jq -r '.oauth_token_secret')
AUTH_URL=$(echo "$RESPONSE" | jq -r '.authorize_url')

echo -e "${GREEN}✓ Request token obtained${NC}"
echo ""

# Step 2: User authorization
echo -e "${BLUE}Step 2: Authorization${NC}"
echo ""
echo -e "${YELLOW}🔐 Open this URL in your browser:${NC}"
echo ""
echo "    $AUTH_URL"
echo ""
echo "1. Sign in to E*TRADE Sandbox"
echo "2. Approve the application"
echo "3. Copy the verification code (5 digits)"
echo ""
read -p "Enter verification code: " VERIFIER

if [ -z "$VERIFIER" ]; then
    echo "No verifier entered. Exiting."
    exit 1
fi

echo ""

# Step 3: Exchange for access tokens
echo -e "${BLUE}Step 3: Exchanging for access tokens...${NC}"
EXCHANGE_RESPONSE=$(curl -sf -X POST "$API_URL/oauth/exchange" \
    -H "Content-Type: application/json" \
    -d "{
        \"oauth_token\":\"$OAUTH_TOKEN\",
        \"oauth_token_secret\":\"$OAUTH_TOKEN_SECRET\",
        \"verifier\":\"$VERIFIER\"
    }")

if [ $? -ne 0 ]; then
    echo -e "${YELLOW}❌ Failed to exchange tokens. Check the verifier code.${NC}"
    exit 1
fi

ACCESS_TOKEN=$(echo "$EXCHANGE_RESPONSE" | jq -r '.access_token')
ACCESS_TOKEN_SECRET=$(echo "$EXCHANGE_RESPONSE" | jq -r '.access_token_secret')

echo -e "${GREEN}✓ Access tokens obtained!${NC}"
echo ""

# Step 4: Update .env
echo -e "${BLUE}Step 4: Updating .env...${NC}"

# Remove old tokens if present
sed -i.bak '/^ETRADE_ACCESS_TOKEN=/d' .env 2>/dev/null || true
sed -i.bak '/^ETRADE_ACCESS_TOKEN_SECRET=/d' .env 2>/dev/null || true

# Add new tokens
echo "ETRADE_ACCESS_TOKEN=$ACCESS_TOKEN" >> .env
echo "ETRADE_ACCESS_TOKEN_SECRET=$ACCESS_TOKEN_SECRET" >> .env

echo -e "${GREEN}✓ .env updated${NC}"
echo ""

# Step 5: Get account ID
echo -e "${BLUE}Step 5: Getting account ID...${NC}"
echo "Please restart the API to load new credentials, then run:"
echo ""
echo "  curl -s http://localhost:8000/account | jq '.AccountListResponse.Accounts.Account[0].accountIdKey'"
echo ""
echo "Copy the accountIdKey and add to .env as:"
echo "  ETRADE_ACCOUNT_ID_KEY=<your_account_id>"
echo ""

echo -e "${GREEN}================================"
echo "✓ OAuth Setup Complete!"
echo -e "================================${NC}"
echo ""
echo "Next steps:"
echo "1. Restart API: uvicorn apps.api.main:app --reload"
echo "2. Get account ID and add to .env"
echo "3. Test: curl http://localhost:8000/positions"
echo ""

