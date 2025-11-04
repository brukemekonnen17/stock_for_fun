# 🤖 Quick Start Guide for AI Assistants

This guide helps AI assistants understand the codebase quickly and navigate it effectively.

## 🎯 System Purpose

**What it does**: Analyzes stocks, generates trade recommendations using ML/LLM, validates trades through policy rules, and learns from outcomes.

**Key Technologies**:
- FastAPI (Python backend)
- Contextual Thompson Sampling (bandit learning)
- DeepSeek LLM (trade plan generation)
- Yahoo Finance (market data)
- SQLAlchemy (database)

---

## 🔍 Where to Start Reading Code

### For Understanding the Flow:
1. **`apps/api/main.py`** - Start here! All endpoints, request/response handling
2. **`services/analysis/explain.py`** - "Why selected" analysis (deterministic)
3. **`services/llm/client.py`** - LLM integration
4. **`libs/analytics/bandit.py`** - Bandit algorithm

### For Adding Features:
1. **`apps/api/main.py`** - Add new endpoints here
2. **`services/marketdata/yf_adapter.py`** - Market data fetching
3. **`services/policy/validators.py`** - Risk rules
4. **`db/models.py`** - Database schema

### For Debugging:
1. Check `apps/api/main.py` logger output
2. Check `services/marketdata/yf_adapter.py` for Yahoo Finance errors
3. Check `services/llm/client.py` for LLM failures

---

## 🚨 Common Tasks & Solutions

### Task: Add a New API Endpoint

**Location**: `apps/api/main.py`

**Steps**:
```python
@app.get("/new-endpoint")
def new_endpoint(param: str):
    # Implementation
    return {"result": "..."}
```

**Example**: See `GET /analyze/{ticker}` around line 242

---

### Task: Add a New Market Data Source

**Location**: `services/marketdata/`

**Steps**:
1. Create new adapter implementing `MarketData` protocol
2. Update `apps/api/main.py` line 94: `market_data = NewAdapter()`

**Example**: `yf_adapter.py` implements `last_quote()`, `daily_ohlc()`, `spread_proxy()`

---

### Task: Add a New Bandit Arm (Strategy)

**Location**: `apps/api/main.py` line 62

**Steps**:
```python
_default_arms = [
    Arm("EARNINGS_PRE"),
    Arm("POST_EVENT_MOMO"),
    Arm("NEW_STRATEGY"),  # Add here
]
```

---

### Task: Fix Yahoo Finance Rate Limiting

**Location**: `services/marketdata/yf_adapter.py`

**Current Solution**: 
- Retry with exponential backoff (line 115-123)
- 5-minute caching (line 11-12, 98)
- Better error messages (line 123)

**If Still Failing**:
- Increase cache TTL (line 12: change `300` to `600`)
- Increase retry delays (line 117: change `3` to `5`)
- Add longer initial delay before retries

---

### Task: Improve Error Messages

**Locations**:
- `apps/api/main.py` line 262-275 (API errors)
- `services/marketdata/yf_adapter.py` line 123 (market data errors)

**Pattern**:
```python
raise HTTPException(
    status_code=429,
    detail="⚠️ Clear message with emoji. 💡 Tip: What to do."
)
```

---

### Task: Add New Analysis Component

**Location**: `services/analysis/explain.py`

**Steps**:
1. Add function (e.g., `def new_analysis(...)`)
2. Call in `apps/api/main.py` line 248-251
3. Add to `WhySelected` schema in `apps/api/schemas.py`

---

## 📊 Key Data Structures

### Context Vector (7-dim)
```python
[immediacy, materiality, liquidity_score, expected_move, news_score, expected_move_dup, days_to_event]
```
**Used by**: Bandit algorithm for arm selection

### ProposePayload
```python
{
  "ticker": str,
  "price": float,
  "event_type": str,
  "days_to_event": float,
  "rank_components": dict,
  "expected_move": float,
  "backtest_kpis": dict,
  "liquidity": float,
  "spread": float,
  "context": List[float],
  "decision_id": str
}
```

### WhySelected (Analysis)
```python
{
  "ticker": str,
  "catalyst": CatalystInfo,
  "strategy": StrategyRationale,
  "news": List[NewsItem],
  "history": PerfStats,
  "market": MarketContext,
  "llm_confidence": float
}
```

---

## 🔧 Configuration Points

### Change Policy Limits
**Location**: `services/policy/validators.py` line 4-10

**Env vars** (override defaults):
- `MAX_TICKET=500`
- `MAX_POSITIONS=3`
- `MAX_PER_TRADE_LOSS=25`

### Change LLM Provider
**Location**: `services/llm/client.py` line 10-11

**Env vars**:
- `DEEPSEEK_API_URL=...`
- `DEEPSEEK_API_KEY=...`

### Change Database
**Location**: `db/session.py` line 7

**Env var**: `DB_URL=sqlite+pysqlite:///./catalyst.db`

---

## 🐛 Debugging Checklist

1. **API not responding**
   - Check `uvicorn` is running
   - Check port 8000 not in use
   - Check logs in terminal

2. **Yahoo Finance errors**
   - Check internet connection
   - Wait 1-2 minutes (rate limit)
   - Try different ticker
   - Check `services/marketdata/yf_adapter.py` logs

3. **LLM errors**
   - Check `DEEPSEEK_API_KEY` set
   - Check API balance
   - Check `services/llm/client.py` logs
   - Fallback mock plan should still work

4. **Database errors**
   - Check `DB_URL` env var
   - Check SQLite file permissions
   - Run: `Base.metadata.create_all(bind=engine)`

5. **Dashboard not loading**
   - Check CORS in `apps/api/main.py` line 47-53
   - Check API base URL in `trading_dashboard.html`
   - Check browser console (F12)

---

## 🎓 Understanding the Code Flow

### Stock Analysis Request
```
User → GET /analyze/NVDA
  → apps/api/main.py:analyze_stock()
    → market_data.last_quote('NVDA')
      → services/marketdata/yf_adapter.py:last_quote()
        → yfinance.Ticker('NVDA')
    → market_data.daily_ohlc('NVDA')
    → decision_propose(payload)
      → bandit.select(context)
        → libs/analytics/bandit.py:select()
      → propose_trade(payload)
        → services/llm/client.py:propose_trade()
      → catalyst_from_payload(), compute_market_context(), etc.
        → services/analysis/explain.py
  → Return ProposeResponse with analysis
```

### Trade Validation
```
User → POST /validate
  → apps/api/main.py:decision_validate()
    → services/policy/validators.py:validate()
      → Check kill switch, positions, liquidity, spread
      → Calculate adjusted_size
  → Return PolicyVerdict
```

---

## 📝 Code Patterns

### Error Handling Pattern
```python
try:
    result = risky_operation()
except SpecificError as e:
    logger.warning(f"Failed: {e}")
    # Fallback
    result = fallback()
except Exception as e:
    logger.error(f"Unexpected: {e}", exc_info=True)
    raise HTTPException(status_code=500, detail=str(e))
```

### Retry Pattern (Market Data)
```python
max_retries = 3
for attempt in range(max_retries):
    try:
        return fetch_data()
    except RateLimitError:
        if attempt < max_retries - 1:
            time.sleep(backoff[attempt])
            continue
        raise
```

### Caching Pattern
```python
cache_key = f"quote_{ticker}"
if cache_key in _price_cache:
    data, cached_time = _price_cache[cache_key]
    if time.time() - cached_time < TTL:
        return data
# Fetch and cache
_data = fetch_data()
_price_cache[cache_key] = (_data, time.time())
return _data
```

---

## 🔗 Key Files Reference

| File | Purpose | Lines to Check |
|------|---------|----------------|
| `apps/api/main.py` | All API endpoints | 242 (analyze_stock), 322 (decision_propose) |
| `services/marketdata/yf_adapter.py` | Yahoo Finance adapter | 15 (last_quote), 115 (retry logic) |
| `services/llm/client.py` | LLM integration | 33 (propose_trade), 47 (retry) |
| `services/policy/validators.py` | Risk guardrails | 45 (validate function) |
| `libs/analytics/bandit.py` | Bandit algorithm | 24 (select), 35 (update) |
| `services/analysis/explain.py` | Deterministic analysis | All functions |
| `trading_dashboard.html` | Web UI | 441 (analyzeStock function) |

---

## ⚠️ Important Notes for AI Assistants

1. **Yahoo Finance Limitations**: Rate limits are common. Always add retry logic when adding new market data calls.

2. **LLM Fallback**: The system should work even if LLM fails. Always check for mock plans in `services/llm/client.py:propose_trade()`.

3. **Analysis is Deterministic**: The "why selected" analysis doesn't depend on LLM. It's in `services/analysis/explain.py`.

4. **Context Vector Size**: Must be 7 dimensions for bandit. Don't change without updating bandit initialization.

5. **Decision ID**: Used for idempotency. Always propagate through propose → validate → reward.

6. **Error Messages**: Should be user-friendly with emojis and actionable tips (see examples in code).

7. **Caching**: Prices cached 5 minutes. Historical data not cached (can be added).

8. **Database**: SQLite by default. Tables auto-created on startup if missing.

---

## 🚀 Quick Commands

```bash
# Start API
uvicorn apps.api.main:app --reload --host 0.0.0.0 --port 8000

# Run tests
pytest tests/

# Smoke tests
./smoke_tests.sh

# Check API health
curl http://127.0.0.1:8000/health
```

---

**Last Updated**: 2025-11-03
**For detailed docs**: See `TECHNICAL_DOCUMENTATION.md`

---

## ⚠️ Breaking Changes (v0.3.0)

- `decision_id` is now **required** (was optional)
- Extra fields in requests are **rejected** (strict validation)
- `/bandit/logs` returns **array** format (was wrapped)

