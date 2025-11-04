# 🤖 LLM Integration - Complete Explanation

## 🎯 What the LLM Does

The LLM (DeepSeek) has **ONE job**: Generate a **trade plan** with entry, stop, and target prices.

**It does NOT:**
- ❌ Choose which stock (that's the scanner)
- ❌ Select strategy (that's the bandit)
- ❌ Compute analysis facts (those are deterministic)
- ❌ Validate risk (that's the policy validators)

**It DOES:**
- ✅ Generate trade plan (entry/stop/target/timeout)
- ✅ Provide thesis (text explanation)
- ✅ Assess confidence (0.5-1.0 score)
- ✅ Identify risks (list of concerns)

---

## 🔄 How It's Connected

### **Flow:**

```
1. Deterministic Facts Computed
   ↓
2. Bandit Selects Strategy Arm
   ↓
3. Facts + Strategy → LLM API Call
   ↓
4. LLM Returns Trade Plan JSON
   ↓
5. Plan + Analysis → Dashboard
```

### **Step-by-Step:**

#### **Step 1: Facts Computed (No LLM)**
```python
# In apps/api/main.py - decision_propose()
cat = catalyst_from_payload(body)        # Catalyst info
mkt = compute_market_context(...)        # Market data (RSI/ATR)
news_items = recent_news(body.ticker)    # News feed
perf = build_perf_stats(...)             # Performance stats
```

#### **Step 2: Bandit Selects Arm (No LLM)**
```python
bandit = get_bandit(len(body.context))
selected_arm = bandit.select(x=context_vector)
# Returns: "POST_EVENT_MOMO" or "EARNINGS_PRE", etc.
```

#### **Step 3: LLM Called (Only for Trade Plan)**
```python
# In services/llm/client.py - propose_trade()

# Build prompt with facts
user_prompt = """
{
  "ticker": "AAPL",
  "price": 192.50,
  "event_type": "EARNINGS",
  "expected_move": 0.04,
  "constraints": {
    "MAX_TICKET": 500,
    "MAX_PER_TRADE_LOSS": 25
  }
}
"""

# Call DeepSeek API
response = await httpx.post(
    "https://api.deepseek.com/v1/chat/completions",
    headers={"Authorization": "Bearer sk-..."},
    json={
        "model": "deepseek-chat",
        "messages": [
            {"role": "system", "content": "You are a trading advisor..."},
            {"role": "user", "content": user_prompt}
        ]
    }
)
```

#### **Step 4: LLM Returns Plan**
```json
{
  "entry_type": "limit",
  "entry_price": 192.00,
  "stop_price": 189.50,
  "target_price": 196.50,
  "timeout_days": 5,
  "confidence": 0.72,
  "reason": "Earnings pre-setup; EM supportive."
}
```

---

## 📡 Connection Details

### **API Endpoint:**
```
POST https://api.deepseek.com/v1/chat/completions
```

### **Authentication:**
```
Authorization: Bearer sk-07b32570468e4bc58f29f06720c22e2b
```

### **Request Format:**
```json
{
  "model": "deepseek-chat",
  "messages": [
    {
      "role": "system",
      "content": "You are a trading advisor. You NEVER invent numbers..."
    },
    {
      "role": "user",
      "content": "{...structured JSON with ticker, price, constraints...}"
    }
  ],
  "temperature": 0.2
}
```

### **Response Format:**
```json
{
  "choices": [{
    "message": {
      "content": "{...trade plan JSON...}"
    }
  }]
}
```

---

## 🔧 Code Location

### **LLM Client:** `services/llm/client.py`
- `propose_trade()` - Main function that calls API
- Retry logic (3 attempts with backoff)
- Timeout handling (30s)
- Fallback to mock plan on failure

### **LLM Schema:** `services/llm/schema.py`
- `LLM_SYSTEM` - System prompt (instructions to LLM)
- `LLM_USER_TEMPLATE` - JSON template for facts

### **Called From:** `apps/api/main.py`
- Line 268: `llm_out = await propose_trade(body.model_dump())`
- After deterministic facts computed
- Before "why selected" analysis composed

---

## 🎯 What LLM Receives (Input)

The LLM gets **structured facts only**:

```json
{
  "ticker": "AAPL",
  "price": 192.50,
  "event_type": "EARNINGS",
  "days_to_event": 7,
  "expected_move": 0.04,
  "liquidity": 5000000000,
  "spread": 0.01,
  "constraints": {
    "MAX_TICKET": 500,
    "MAX_PER_TRADE_LOSS": 25,
    "SPREAD_CENTS_MAX": 0.05,
    "SPREAD_BPS_MAX": 50
  },
  "backtest_kpis": {
    "hit_rate": 0.54,
    "avg_win": 0.012,
    "avg_loss": -0.008
  }
}
```

**Note:** LLM NEVER invents these numbers. They're computed deterministically first.

---

## 📤 What LLM Returns (Output)

The LLM returns a **trade plan**:

```json
{
  "ticker": "AAPL",
  "entry_type": "limit",
  "entry_price": 192.00,
  "stop_rule": "ATR14 * 1.0 below entry",
  "stop_price": 189.50,
  "target_rule": "1.5 x stop",
  "target_price": 196.50,
  "timeout_days": 5,
  "confidence": 0.72,
  "reason": "Earnings pre-setup; EM supportive."
}
```

**This becomes the `plan` in the response.**

---

## ⚠️ When LLM Fails

### **Current Issue: 402 Payment Required**

Your DeepSeek API key needs funds. When this happens:

1. **API returns 402** → Insufficient balance
2. **Retry logic** → Tries 3 times
3. **All retries fail** → Falls back to mock plan
4. **Mock plan generated** → Safe defaults
5. **Analysis still works** → Deterministic facts computed before LLM

### **Mock Plan Fallback:**

```python
def _mock_plan(ticker: str, price: float) -> dict:
    return {
        "entry_type": "limit",
        "entry_price": price * 0.995,  # 0.5% below current
        "stop_price": price * 0.98,      # 2% stop
        "target_price": price * 1.03,    # 3% target
        "timeout_days": 5,
        "confidence": 0.5,
        "reason": "LLM unavailable - generated mock plan"
    }
```

**This ensures the system always works, even if LLM is down.**

---

## 🔗 Connection Flow Diagram

```
┌─────────────────────────────────────────┐
│  1. Proposal Payload Arrives           │
│     (ticker, price, event_type, etc.)  │
└──────────────┬──────────────────────────┘
               │
               ▼
┌─────────────────────────────────────────┐
│  2. Deterministic Facts Computed        │
│     - Catalyst info                     │
│     - Market context (RSI/ATR)          │
│     - News feed                         │
│     - Performance stats                 │
└──────────────┬──────────────────────────┘
               │
               ▼
┌─────────────────────────────────────────┐
│  3. Bandit Selects Strategy             │
│     - POST_EVENT_MOMO, etc.            │
└──────────────┬──────────────────────────┘
               │
               ▼
┌─────────────────────────────────────────┐
│  4. LLM API Call                        │
│     POST https://api.deepseek.com/...  │
│     ┌──────────────────────────────┐  │
│     │ System: "You are advisor..."  │  │
│     │ User: {ticker, price, ...}   │  │
│     └──────────────────────────────┘  │
└──────────────┬──────────────────────────┘
               │
               ▼
        ┌──────────────┐
        │   Success?   │
        └──────┬───────┘
               │
        ┌──────┴───────┐
        │              │
    YES│              │NO
        │              │
        ▼              ▼
┌──────────────┐  ┌──────────────┐
│ LLM Plan     │  │ Mock Plan    │
│ (entry/stop) │  │ (safe def.)  │
└──────┬───────┘  └──────┬───────┘
       │                  │
       └────────┬─────────┘
                │
                ▼
┌─────────────────────────────────────────┐
│  5. Compose Response                    │
│     - plan: (from LLM or mock)         │
│     - analysis: (deterministic facts)    │
│     - selected_arm: (from bandit)       │
└─────────────────────────────────────────┘
```

---

## 💡 Key Insight

**The LLM is the LAST step, not the first.**

Everything else (catalyst analysis, news, RSI/ATR, strategy selection) happens **before** the LLM is called.

The LLM only:
1. **Reads** the facts we computed
2. **Generates** a trade plan within constraints
3. **Explains** the reasoning (text)

**It never invents numbers or chooses stocks.**

---

## 🔍 See It In Action

### **Check Logs:**

```bash
# Watch LLM API calls
tail -f api.log | grep -E "LLM|deepseek|402"
```

### **Test Directly:**

```bash
curl -X POST http://localhost:8000/propose \
  -H "Content-Type: application/json" \
  -d '{
    "ticker":"AAPL",
    "price":192.50,
    "event_type":"EARNINGS",
    "days_to_event":7,
    "context":[0.6,0.6,1.0,0.4,0.5,0.04,7],
    ...
  }' | jq .
```

You'll see:
- `plan` - From LLM (or mock if fails)
- `analysis` - Deterministic facts (always works)
- `selected_arm` - From bandit (always works)

---

## ✅ Summary

**LLM Connection:**
- ✅ **Endpoint:** DeepSeek API (https://api.deepseek.com/v1/chat/completions)
- ✅ **Auth:** Bearer token (your API key)
- ✅ **Input:** Structured JSON with facts
- ✅ **Output:** Trade plan JSON
- ✅ **Fallback:** Mock plan if API fails

**LLM Role:**
- ✅ **Generates:** Entry/stop/target prices
- ✅ **Provides:** Thesis and confidence
- ✅ **Never:** Chooses stocks or computes facts

**Current Status:**
- ⚠️ API returning 402 (needs funds)
- ✅ System still works (mock plan fallback)
- ✅ All analysis still shows (computed separately)

**The LLM is just one piece - the rest works independently!** 🎯

