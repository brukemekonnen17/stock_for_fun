# 📡 API Reference - Quick Guide

## Base URL
```
http://127.0.0.1:8000
```

## Endpoints

### Health Check
```http
GET /health
Response: {"status": "ok", "time": "2024-01-15T10:00:00Z"}
```

---

### Analyze Stock (Main Endpoint)
```http
GET /analyze/{ticker}
Example: GET /analyze/NVDA
```

**Response**: Full trade proposal with analysis

**Features**:
- ✅ Fetches market data automatically
- ✅ Computes RSI/ATR indicators
- ✅ Fetches recent news
- ✅ Generates trade plan
- ✅ Returns "why selected" analysis

**Error Codes**:
- `200` - Success
- `404` - Ticker not found / no data
- `429` - Rate limit (wait 1-2 min)
- `500` - Server error

---

### Propose Trade (Full Context)
```http
POST /propose
Content-Type: application/json
```

**Body**:
```json
{
  "ticker": "AAPL",
  "price": 192.50,
  "event_type": "EARNINGS",
  "days_to_event": 7.0,
  "rank_components": {...},
  "expected_move": 0.04,
  "backtest_kpis": {...},
  "liquidity": 5000000000,
  "spread": 0.01,
  "context": [0.6, 0.6, 1.0, 0.4, 0.5, 0.04, 7]
}
```

**Response**: Same as `/analyze/{ticker}`

---

### Validate Trade
```http
POST /validate
Content-Type: application/json
```

**Body**:
```json
{
  "plan": {...},
  "market": {...},
  "context": {...},
  "decision_id": "..."
}
```

**Response**:
```json
{
  "verdict": "APPROVED",
  "reason": "All checks passed",
  "adjusted_size": 25
}
```

**Verdicts**: `APPROVED`, `REJECTED`, `REVIEW`

---

### Log Reward
```http
POST /bandit/reward
Content-Type: application/json
```

**Body**:
```json
{
  "arm_name": "POST_EVENT_MOMO",
  "context": [0.6, 0.6, 1.0, 0.4, 0.5, 0.04, 7],
  "reward": 0.35,
  "decision_id": "..."
}
```

**Response**: `{"status": "ok"}`

---

### Scan for Opportunities
```http
GET /scan?min_rank=70&limit=10
```

**Query Params**:
- `min_rank` (default: 70) - Minimum catalyst rank
- `limit` (default: 10) - Max results

**Response**: Array of scan items with catalysts

---

### Bandit Stats
```http
GET /bandit/stats
```

**Response**:
```json
{
  "total": 150,
  "arm_stats": [
    {
      "arm_name": "POST_EVENT_MOMO",
      "count": 45,
      "avg_reward": 0.23,
      "max_reward": 0.87,
      "min_reward": -0.45
    }
  ]
}
```

---

### Bandit Logs
```http
GET /bandit/logs?limit=50
```

**Response**: Array of reward logs

---

## Rate Limits & Errors

### Yahoo Finance Rate Limits
- **Symptom**: 429 errors
- **Solution**: Wait 1-2 minutes, retry
- **Auto-retry**: 3 attempts with 3s, 6s, 12s delays

### Common Errors

| Code | Meaning | Solution |
|------|---------|----------|
| 404 | Ticker not found | Check ticker symbol, try different ticker |
| 429 | Rate limit | Wait 1-2 minutes |
| 500 | Server error | Check API logs, retry |

---

## Testing with curl

```bash
# Health check
curl http://127.0.0.1:8000/health

# Analyze stock
curl http://127.0.0.1:8000/analyze/AAPL

# Propose trade
curl -X POST http://127.0.0.1:8000/propose \
  -H "Content-Type: application/json" \
  -d '{
    "ticker": "AAPL",
    "price": 192.50,
    "event_type": "EARNINGS",
    "days_to_event": 7,
    "context": [0.6, 0.6, 1.0, 0.4, 0.5, 0.04, 7]
  }'

# Get stats
curl http://127.0.0.1:8000/bandit/stats
```

---

## Response Schemas

See `apps/api/schemas.py` for full Pydantic models.

Key types:
- `ProposeResponse` - Trade proposal + analysis
- `WhySelected` - Complete analysis structure
- `PolicyVerdict` - Validation result
- `RewardPayload` - Reward logging

---

## ✅ Implementation Status

| Endpoint | Method | Status | Notes |
|----------|--------|--------|-------|
| `/health` | GET | ✅ | Working |
| `/analyze/{ticker}` | GET | ✅ | Full analysis with trade plan |
| `/quick/{ticker}` | GET | ✅ | Fast text-based analysis |
| `/propose` | POST | ✅ | Propose trade with context |
| `/validate` | POST | ✅ | Policy validation |
| `/bandit/reward` | POST | ✅ | Log reward (idempotent) |
| `/bandit/stats` | GET | ✅ | Performance statistics |
| `/bandit/logs` | GET | ✅ | Recent reward logs |
| `/scan` | GET | ✅ | Scan for opportunities |
| `/positions` | GET | ✅ | Broker positions (E*TRADE) |
| `/orders` | POST | ✅ | Place order (E*TRADE) |
| `/oauth/request_token` | POST | ✅ | OAuth step 1 |
| `/oauth/exchange` | POST | ✅ | OAuth step 2 |

**All documented endpoints are implemented!** ✅

