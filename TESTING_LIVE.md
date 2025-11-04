# Live Testing Guide

## Current State: Paper Trading Ready ✅

You have a **complete paper trading system** that works end-to-end without E*TRADE. Here's how to test it:

## Option 1: Paper Trading (No Broker Needed) - READY NOW

### What Works
- ✅ Backend generates trade proposals (bandit + LLM)
- ✅ Validates against risk rules
- ✅ Simulates fills with slippage
- ✅ Logs rewards and updates bandit
- ✅ Dashboard shows mock catalysts
- ✅ All learning happens (bandit improves over time)

### How to Test

#### Terminal 1: Start API
```bash
cd /Users/brukemekonnen/stock_investment
source .venv/bin/activate
uvicorn apps.api.main:app --reload --port 8000
```

#### Terminal 2: Start Frontend
```bash
cd /Users/brukemekonnen/stock_investment
npm run dev
```

#### Terminal 3: Run Paper Trading
```bash
cd /Users/brukemekonnen/stock_investment
source .venv/bin/activate

# Single cycle test
python run_paper_trading.py

# Continuous loop (every 60 seconds)
python paper_trading.py --interval 60

# Fast loop for testing (every 10 seconds)
python paper_trading.py --interval 10
```

#### What You'll See
```
==================================================
Starting trading cycle
==================================================
Proposed trade - Arm: POST_EVENT_MOMO, Ticker: AAPL
Trade validation: APPROVED - All checks passed
Simulated fill: AAPL buy 100 @ 192.34 (slippage: 0.08%)
Logged reward for arm POST_EVENT_MOMO: 0.4500
Trading cycle completed
```

#### Check Results
```bash
# View bandit logs
sqlite3 catalyst.db "SELECT ts, arm_name, reward FROM bandit_logs ORDER BY ts DESC LIMIT 10;"

# View saved bandit state
ls -la bandit_state/
cat bandit_state/d7.json

# Check API logs
# Look for [decision_id] entries with arm selections
```

#### Dashboard
Open http://localhost:3000
- See mock catalysts (AAPL, TSLA, NVDA)
- Confidence scores
- Auto-refresh every 30s

### What's Being Tested
✅ Bandit arm selection (learns over time)
✅ LLM trade plan generation (or fallback)
✅ Policy validation (spreads, limits, kill-switch)
✅ Reward calculation (R-multiples)
✅ State persistence (survives restarts)
✅ End-to-end flow

### Limitations (Paper Trading)
- ❌ Not using real market prices
- ❌ Not placing real orders
- ❌ Fills are simulated (not actual execution)
- ❌ Catalysts are mock data

**BUT: The bandit IS learning** - it's tracking which arms work best given context.

---

## Option 2: E*TRADE Integration - WHAT'S NEEDED

To connect to E*TRADE and trade live, you need:

### 1. E*TRADE API Setup
```bash
# Register for E*TRADE developer account
# https://developer.etrade.com/

# Get OAuth credentials:
# - Consumer Key
# - Consumer Secret
```

### 2. Install E*TRADE SDK
```bash
pip install requests-oauthlib
```

### 3. Create Broker Client
I'll create `services/broker/etrade_client.py` for you (see below)

### 4. Wire Real Market Data
Need to replace mock `/scan` with real catalyst feed:
- News APIs (Benzinga, Alpha Vantage)
- Earnings calendar (Polygon.io, FMP)
- Options flow data

### 5. Update Paper Trading Loop
Point to real broker instead of simulated fills

---

## Option 3: Hybrid (Real Data, Simulated Fills) - RECOMMENDED NEXT STEP

**Best way to test before going live:**

1. ✅ Keep current paper trading loop
2. ✅ Add real market data feed
3. ✅ Add real catalyst scanner
4. ✅ Simulate fills using real bid/ask spreads
5. ❌ Don't submit actual orders yet

This lets you validate:
- Catalyst quality
- Bandit performance
- Validator effectiveness
- Real-world timing

**Then** add E*TRADE for live execution.

---

## What You Can Do RIGHT NOW

### 1. Test Paper Trading System
```bash
# This works completely without any external APIs
python paper_trading.py --interval 30
```

Let it run for an hour. Watch the bandit learn.

### 2. Verify Bandit Learning
```bash
# After running for a while
sqlite3 catalyst.db "
SELECT 
  arm_name,
  COUNT(*) as selections,
  AVG(reward) as avg_reward,
  MIN(reward) as min_reward,
  MAX(reward) as max_reward
FROM bandit_logs
GROUP BY arm_name
ORDER BY avg_reward DESC;
"
```

You should see arms with higher rewards get selected more often over time.

### 3. Test Different Contexts
Modify `paper_trading.py` to test different market conditions:

```python
# In run_cycle(), try different contexts:
context = [0.8, 0.9, 1.0, 0.7, 0.8, 0.06, 3]  # High-confidence, near-term
context = [0.3, 0.4, 0.6, 0.2, 0.3, 0.02, 14] # Low-confidence, far-term
```

See which arms the bandit prefers for each context.

### 4. Test Validators
```bash
# Run smoke tests to verify all rules work
./smoke_tests.sh
```

### 5. Stress Test
```bash
# Run fast loop to generate lots of decisions
python paper_trading.py --interval 5
```

Let it run overnight. Check bandit performance in the morning.

---

## Summary: Testing Paths

| Path | Status | What Works | What's Missing |
|------|--------|------------|----------------|
| **Paper Trading** | ✅ READY NOW | Everything except real orders | Real market data, real fills |
| **Real Data + Simulated** | 🟡 NEEDS DATA API | Real prices, real catalysts | Real fills |
| **Live E*TRADE** | 🔴 NEEDS INTEGRATION | Everything | Broker client |

---

## Recommended Testing Sequence

### Week 1: Paper Trading (NOW)
- ✅ Run paper_trading.py continuously
- ✅ Collect 100+ decisions
- ✅ Analyze bandit performance
- ✅ Tune guardrails if needed

### Week 2: Real Market Data
- Add market data API (Alpha Vantage, Polygon.io)
- Replace mock /scan with real catalysts
- Keep simulated fills
- Validate catalyst quality

### Week 3: E*TRADE Integration
- Set up E*TRADE OAuth
- Create broker client
- Paper trade with real market data
- Track slippage vs simulation

### Week 4: Live Trading (Small Size)
- Start with 1 share per trade
- Run for 1 week
- Validate actual P&L vs expected
- Scale up slowly

---

## Your System is READY for Testing

**You have everything needed for paper trading:**
- ✅ Agent (bandit + LLM)
- ✅ Backend (API)
- ✅ Frontend (dashboard)
- ✅ Loop (paper_trading.py)
- ✅ Persistence (survives restarts)
- ✅ Logging (decision tracking)
- ✅ Testing (smoke + unit tests)

**Start testing NOW with:**
```bash
python paper_trading.py --interval 30
```

Then decide if you want to:
1. Add real market data next, OR
2. Jump straight to E*TRADE integration

Want me to create the E*TRADE integration next?

