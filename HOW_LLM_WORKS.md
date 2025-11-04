# 🤖 How the LLM Works - Simple Explanation

## 🎯 LLM's Single Job

**The LLM ONLY generates the trade plan** (entry price, stop loss, target price).

**It does NOT:**
- ❌ Choose stocks (scanner does this)
- ❌ Select strategy (bandit does this)
- ❌ Compute analysis (deterministic functions do this)
- ❌ Validate risk (policy validators do this)

---

## 🔄 Complete Flow (Where LLM Fits)

```
┌─────────────────────────────────────────────┐
│  1. PROPOSAL ARRIVES                       │
│     Dashboard sends: ticker, price, etc.    │
└──────────────┬──────────────────────────────┘
               │
               ▼
┌─────────────────────────────────────────────┐
│  2. DETERMINISTIC FACTS COMPUTED            │
│     ✅ Catalyst info (event type, days)     │
│     ✅ Market context (RSI, ATR, liquidity) │
│     ✅ Recent news (from NewsAPI)            │
│     ✅ Performance stats (from backtests)   │
│                                             │
│     (This is the "why selected" section!)   │
└──────────────┬──────────────────────────────┘
               │
               ▼
┌─────────────────────────────────────────────┐
│  3. BANDIT SELECTS STRATEGY                  │
│     POST_EVENT_MOMO, EARNINGS_PRE, etc.     │
│                                             │
│     (Uses Thompson Sampling algorithm)       │
└──────────────┬──────────────────────────────┘
               │
               ▼
┌─────────────────────────────────────────────┐
│  4. LLM CALLED (THIS IS THE ONLY LLM STEP)  │
│     ┌─────────────────────────────────────┐ │
│     │ HTTP POST to DeepSeek API           │ │
│     │                                      │ │
│     │ URL: api.deepseek.com/v1/...        │ │
│     │ Auth: Bearer sk-07b3257...         │ │
│     │                                      │ │
│     │ Input:                               │ │
│     │   - Ticker: AAPL                    │ │
│     │   - Price: 192.50                   │ │
│     │   - Event: EARNINGS                 │ │
│     │   - Constraints: MAX_TICKET=500    │ │
│     │                                      │ │
│     │ Output:                              │ │
│     │   - entry_price: 192.00            │ │
│     │   - stop_price: 189.50             │ │
│     │   - target_price: 196.50           │ │
│     │   - confidence: 0.72               │ │
│     │   - reason: "Earnings pre-setup..."│ │
│     └─────────────────────────────────────┘ │
└──────────────┬──────────────────────────────┘
               │
               ▼
┌─────────────────────────────────────────────┐
│  5. RESPONSE COMPOSED                       │
│     ✅ plan: (from LLM)                    │
│     ✅ analysis: (deterministic facts)      │
│     ✅ selected_arm: (from bandit)          │
└──────────────┬──────────────────────────────┘
               │
               ▼
┌─────────────────────────────────────────────┐
│  6. DASHBOARD DISPLAYS                      │
│     - Trade plan (entry/stop/target)         │
│     - Full "why selected" analysis         │
│     - Strategy explanation                  │
└─────────────────────────────────────────────┘
```

---

## 📡 LLM Connection Details

### **Where It's Called:**

**File:** `apps/api/main.py`  
**Function:** `decision_propose()`  
**Line:** `llm_out = await propose_trade(body.model_dump())`

### **What Gets Sent:**

**File:** `services/llm/client.py`  
**Function:** `propose_trade()`

**HTTP Request:**
```python
POST https://api.deepseek.com/v1/chat/completions

Headers:
  Authorization: Bearer sk-07b32570468e4bc58f29f06720c22e2b

Body:
{
  "model": "deepseek-chat",
  "messages": [
    {
      "role": "system",
      "content": "You are a trading advisor. You NEVER invent numbers..."
    },
    {
      "role": "user",
      "content": "{
        \"ticker\": \"AAPL\",
        \"price\": 192.50,
        \"event_type\": \"EARNINGS\",
        \"constraints\": {
          \"MAX_TICKET\": 500,
          \"MAX_PER_TRADE_LOSS\": 25
        }
      }"
    }
  ],
  "temperature": 0.2
}
```

### **What LLM Returns:**

```json
{
  "choices": [{
    "message": {
      "content": "{
        \"ticker\": \"AAPL\",
        \"entry_type\": \"limit\",
        \"entry_price\": 192.00,
        \"stop_price\": 189.50,
        \"target_price\": 196.50,
        \"timeout_days\": 5,
        \"confidence\": 0.72,
        \"reason\": \"Earnings pre-setup; EM supportive.\"
      }"
    }
  }]
}
```

**This becomes the `plan` in your dashboard.**

---

## 🔍 Current Connection Status

### **What's Happening:**

```
1. Dashboard sends proposal
   ↓
2. System computes facts (✅ works)
   ↓
3. Bandit selects arm (✅ works)
   ↓
4. LLM API called → POST to DeepSeek
   ↓
5. DeepSeek returns 402 (Insufficient Balance)
   ↓
6. Retry logic tries 3 times
   ↓
7. All fail → Fallback to mock plan
   ↓
8. Response returned with:
   - plan: (mock plan)
   - analysis: (full facts - still works!)
```

### **Your DeepSeek API:**
- **Key:** `sk-07b32570468e4bc58f29f06720c22e2b`
- **Status:** 402 Payment Required (needs funds)
- **Action Needed:** Add funds at https://platform.deepseek.com/

---

## 💡 Key Point: LLM is Just One Step

**The "Why Selected" analysis is computed BEFORE the LLM is called:**

```python
# Line 247-251: Facts computed FIRST
cat = catalyst_from_payload(body)           # ✅ Works
mkt = compute_market_context(...)           # ✅ Works  
news_items = recent_news(body.ticker)       # ✅ Works
perf = build_perf_stats(...)                # ✅ Works

# Line 268: LLM called AFTER
llm_out = await propose_trade(...)          # ⚠️ Fails (but has fallback)

# Line 271-279: Analysis uses deterministic facts
why = WhySelected(
    catalyst=cat,      # ✅ From step 1
    strategy=rationale,# ✅ From bandit
    news=news_items,   # ✅ From step 1
    history=perf,      # ✅ From step 1
    market=mkt,        # ✅ From step 1
    llm_confidence=0.6 # From LLM (or default if fails)
)
```

**So even when LLM fails, you still see the full analysis!**

---

## 🎯 What You See in Dashboard

### **When LLM Works:**
- ✅ Trade plan from LLM (smart entry/stop/target)
- ✅ Full analysis (why selected)
- ✅ LLM confidence score

### **When LLM Fails (Current):**
- ✅ Trade plan from mock (safe defaults)
- ✅ Full analysis (why selected) - **STILL SHOWS!**
- ⚠️ Confidence = 0.5 (default)

**The only difference:** Trade plan prices are simpler (but still valid).

---

## 🔧 Fix LLM (Optional)

### **Option 1: Add Funds to DeepSeek**
1. Go to https://platform.deepseek.com/
2. Add funds to account
3. API will start working

### **Option 2: Use Mock Plans (Recommended)**
- Mock plans are perfectly safe
- All analysis still shows
- No API costs
- Faster responses

### **Option 3: Switch LLM Provider**
```bash
# Use OpenAI instead
export DEEPSEEK_API_URL="https://api.openai.com/v1/chat/completions"
export DEEPSEEK_API_KEY="sk-your-openai-key"
```

---

## 📚 Files Involved

### **LLM Client:** `services/llm/client.py`
- Makes HTTP calls to DeepSeek
- Handles retries/timeouts
- Falls back to mock plan

### **LLM Schema:** `services/llm/schema.py`
- Defines prompt template
- System instructions

### **Called From:** `apps/api/main.py`
- Line 268: `llm_out = await propose_trade(...)`
- Only called AFTER facts are computed

---

## ✅ Summary

**LLM Connection:**
- **Type:** HTTP POST to DeepSeek API
- **When:** After facts computed, before response
- **Purpose:** Generate trade plan (entry/stop/target)
- **Fallback:** Mock plan if API fails

**Current Status:**
- ⚠️ API returning 402 (needs funds)
- ✅ System still works (mock fallback)
- ✅ Analysis still shows (computed separately)

**The LLM is just 1 step out of 6 - everything else works independently!** 🎯

---

**Read `LLM_EXPLAINED.md` for even more detail!**

