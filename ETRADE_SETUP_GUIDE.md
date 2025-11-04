# E*TRADE Setup Guide - Complete Flow

## Prerequisites

✅ E*TRADE developer account created
✅ Consumer Key and Secret obtained
✅ Added to `.env`:

```env
ETRADE_CONSUMER_KEY=9fab270c43a476a2b0b61fbad0a60bb8
ETRADE_CONSUMER_SECRET=3c201d071c6086057092715c5b6b35195011e6580abac84dae657d527f76ba32
ETRADE_SANDBOX=true
```

## Quick Setup (Automated Script)

```bash
# 1. Start API
uvicorn apps.api.main:app --reload

# 2. Run setup script (in new terminal)
./setup_etrade.sh
```

The script will:
1. Request OAuth token
2. Open authorization URL
3. Prompt for verification code
4. Exchange for access tokens
5. Update `.env` automatically

## Manual Setup (Step by Step)

### Step 1: Request Token

```bash
curl -X POST http://localhost:8000/oauth/request_token \
  -H "Content-Type: application/json" \
  -d '{"callback":"oob"}' | jq .
```

**Response:**
```json
{
  "oauth_token": "abc123...",
  "oauth_token_secret": "xyz789...",
  "authorize_url": "https://apisb.etrade.com/oauth/authorize?key=...&token=..."
}
```

**Save:**
- `oauth_token`
- `oauth_token_secret`

### Step 2: Authorize

1. Open `authorize_url` in browser
2. Sign in to **E*TRADE Sandbox**
3. Click "Accept" to authorize
4. **Copy the 5-digit verification code**

### Step 3: Exchange for Access Tokens

```bash
curl -X POST http://localhost:8000/oauth/exchange \
  -H "Content-Type: application/json" \
  -d '{
    "oauth_token":"<from step 1>",
    "oauth_token_secret":"<from step 1>",
    "verifier":"<5-digit code from step 2>"
  }' | jq .
```

**Response:**
```json
{
  "access_token": "def456...",
  "access_token_secret": "uvw999..."
}
```

### Step 4: Update .env

Add to `.env`:
```env
ETRADE_ACCESS_TOKEN=def456...
ETRADE_ACCESS_TOKEN_SECRET=uvw999...
```

**Restart the API** to load new credentials:
```bash
# Ctrl+C to stop, then:
uvicorn apps.api.main:app --reload
```

### Step 5: Get Account ID

```bash
curl -s http://localhost:8000/account | jq .
```

Look for `accountIdKey` in the response:
```json
{
  "AccountListResponse": {
    "Accounts": {
      "Account": [
        {
          "accountIdKey": "83405188",
          "accountDesc": "INDIVIDUAL",
          ...
        }
      ]
    }
  }
}
```

Add to `.env`:
```env
ETRADE_ACCOUNT_ID_KEY=83405188
```

**Restart API again** to load account ID.

## Verify Setup

### Test 1: Get Positions
```bash
curl -s http://localhost:8000/positions | jq .
```

**Expected:** List of positions (may be empty in sandbox)
```json
[
  {
    "symbol": "AAPL",
    "qty": 10,
    "price": 150.00,
    "market_value": 1500.00
  }
]
```

### Test 2: Get Account Info
```bash
curl -s http://localhost:8000/account | jq .
```

**Expected:** Account details

### Test 3: Place Order (Sandbox)
```bash
curl -X POST http://localhost:8000/orders \
  -H "Content-Type: application/json" \
  -d '{
    "ticker":"AAPL",
    "side":"BUY",
    "qty":1,
    "type":"limit",
    "limit_price":100.00,
    "tif":"DAY"
  }' | jq .
```

**Expected:**
```json
{
  "status": "ACCEPTED",
  "broker_order_id": "123456",
  "avg_px": null,
  "message": "..."
}
```

### Test 4: Cancel Order
```bash
curl -X POST http://localhost:8000/orders/cancel/123456 | jq .
```

**Expected:**
```json
{
  "status": "CANCELED",
  "broker_order_id": "123456",
  "message": "..."
}
```

## Complete .env Example

```env
# Database
DB_URL=sqlite+pysqlite:///./catalyst.db

# LLM
DEEPSEEK_API_URL=http://localhost:11434/v1/chat/completions
DEEPSEEK_API_KEY=changeme

# Guardrails
MAX_TICKET=500
MAX_POSITIONS=3
MAX_PER_TRADE_LOSS=25
DAILY_KILL_SWITCH=-75
SPREAD_CENTS_MAX=0.05
SPREAD_BPS_MAX=50
SLIPPAGE_BPS=10

# E*TRADE (Sandbox)
ETRADE_CONSUMER_KEY=9fab270c43a476a2b0b61fbad0a60bb8
ETRADE_CONSUMER_SECRET=3c201d071c6086057092715c5b6b35195011e6580abac84dae657d527f76ba32
ETRADE_ACCESS_TOKEN=your_access_token_here
ETRADE_ACCESS_TOKEN_SECRET=your_access_token_secret_here
ETRADE_ACCOUNT_ID_KEY=your_account_id_here
ETRADE_SANDBOX=true
```

## Troubleshooting

### Error: "Invalid consumer key"
- Check `ETRADE_CONSUMER_KEY` in `.env`
- Make sure no extra spaces
- Verify key is for sandbox (not production)

### Error: "Invalid verifier"
- Verifier code expires after 5 minutes
- Start over from Step 1
- Make sure you copied the full 5-digit code

### Error: "Invalid access token"
- Tokens may expire (check E*TRADE docs)
- Re-run OAuth flow to get new tokens
- Check `ETRADE_SANDBOX=true` matches your keys

### Error: "Account ID not found"
- Make sure you've set `ETRADE_ACCOUNT_ID_KEY` in `.env`
- Restart API after updating `.env`
- Verify accountIdKey from `/account` response

### Empty positions/orders
- Sandbox accounts start empty
- Place test order to populate
- Check E*TRADE sandbox portal for account status

## Security Notes

🔒 **NEVER commit `.env` to git**

Add to `.gitignore`:
```
.env
.env.*
!.env.example
```

🔒 **Rotate tokens regularly**
- Access tokens can be refreshed
- Consumer keys should be rotated quarterly
- Use separate sandbox/production credentials

🔒 **Log safely**
- Only log last 4 characters of tokens
- Redact full tokens in error messages
- Monitor API access logs

## Going Live (Production)

1. Get **production** consumer key/secret from E*TRADE
2. Change `.env`:
   ```env
   ETRADE_SANDBOX=false
   ```
3. Re-run OAuth flow for production tokens
4. **Start with very small position sizes**
5. Test with 1 share orders first
6. Monitor carefully for first week

## Token Refresh (Advanced)

E*TRADE tokens may expire. To automate refresh:

```python
# Add to services/broker/etrade_oauth.py
def refresh_token(consumer_key, consumer_secret, access_token, access_token_secret):
    # E*TRADE doesn't have explicit refresh
    # Need to re-authenticate if tokens expire
    # Store expiry time and trigger new OAuth flow
    pass
```

Consider storing tokens in encrypted database vs `.env` for production.

## Next Steps

After setup:
1. ✅ Test all 4 endpoints above
2. ✅ Run smoke tests: `./smoke_tests.sh`
3. ✅ Place/cancel test orders
4. ✅ Monitor for 24 hours in sandbox
5. 🚀 Deploy live trading loop

## Support

- E*TRADE API Docs: https://developer.etrade.com/
- OAuth 1.0a Spec: https://oauth.net/core/1.0a/
- Issues: Check API logs in terminal

---

**You're ready to trade! 🎉**

Test in sandbox extensively before going live.

