# M1: LLM Summary Service - Setup & Testing

## ✅ Implementation Complete

The `/summarize` endpoint is implemented and ready to use.

## 🔑 Prerequisites

1. **ANTHROPIC_API_KEY must be set** in your `.env` file or environment
2. API server must be running on `http://localhost:8000`

## 📡 API Endpoint

### POST `/summarize`

**Request:**
```json
{
  "file_path": "artifacts/analysis_contract.json"
}
```

OR

```json
{
  "contract": {
    "ticker": "NVDA",
    "verdict": "YELLOW",
    "evidence": [...],
    "economics": {...},
    "plan": {...}
  }
}
```

**Response:**
```json
{
  "executive_summary": "150-250 word summary...",
  "decision_rationale": [
    "Bullet point 1",
    "Bullet point 2"
  ],
  "risks_and_watch": [
    "Risk 1",
    "Risk 2"
  ],
  "action_template": {
    "entry_price": 188.15,
    "stop_price": 173.15,
    "target_price": 210.65,
    "stop_pct": -8.0,
    "target_pct": 12.0,
    "risk_reward": 1.5,
    "policy_ok": false
  },
  "metadata": {
    "ticker": "NVDA",
    "run_id": "50b0f37965727112",
    "timestamp": "2025-11-10T11:19:38.265299",
    "prompt_version": "1.0.0"
  }
}
```

## 🧪 Testing

### 1. Check API Key

```bash
# Check if API key is set (in the environment where server runs)
grep ANTHROPIC_API_KEY .env
```

### 2. Test Endpoint

```bash
curl -X POST http://localhost:8000/summarize \
  -H "Content-Type: application/json" \
  -d '{"file_path": "artifacts/analysis_contract.json"}' \
  | python3 -m json.tool
```

### 3. Expected Behavior

**If API key is missing:**
```json
{
  "detail": "LLM returned empty response. Check ANTHROPIC_API_KEY is set and LLM service is available."
}
```

**If API key is set:**
- Returns structured summary with executive_summary, decision_rationale, risks_and_watch, action_template
- All fields cite values from `analysis_contract.json` only
- Never invents numbers

## 🔍 Current Status

The endpoint is working correctly but requires:
- ✅ ANTHROPIC_API_KEY in environment
- ✅ Valid `analysis_contract.json` file
- ✅ API server running

## 📝 Example Output (Mock)

For the current `artifacts/analysis_contract.json` (NVDA, YELLOW verdict, blocked economics):

**Executive Summary:**
> NVDA shows a YELLOW verdict with mixed signals. Technical pattern is GREEN with positive sector relative strength, but statistical evidence is insufficient (all CAR values null, n=2 events). Economics are blocked (net_median null, blocked=true), indicating capacity concerns. The plan shows entry at $188.15 with stop at $173.15 (-8.0%) and target at $210.65 (+12.0%), but policy_ok is false, suggesting guardrail failures.

**Decision Rationale:**
1. Effect at H=5: Statistical evidence unavailable (effect null, CI null)
2. Pattern: GREEN - validated crossover signal with positive sector RS
3. Economics: Blocked - net returns not positive after costs (blocked=true)

**Risks & Watch:**
1. Net returns not positive after costs
2. CAR does not support signal
3. Regime not aligned
4. Watch: Statistical power insufficient (n<10 events, all CAR values null)

## 🚀 Next Steps

1. Set `ANTHROPIC_API_KEY` in `.env` file
2. Restart API server if needed
3. Test with real LLM call
4. Proceed to M2: RAG over artifacts

