# 🚀 START HERE - See Your System Live

## Step-by-Step: Get Everything Running (5 Minutes)

### Terminal 1: Start the Backend

```bash
cd /Users/brukemekonnen/stock_investment

# Activate virtual environment
source .venv/bin/activate

# Install final dependencies
pip install requests==2.32.3 requests-oauthlib==2.0.0 yfinance==0.2.43

# Start API server
uvicorn apps.api.main:app --reload --port 8000
```

**What you'll see:**
```
INFO:     Uvicorn running on http://127.0.0.1:8000 (Press CTRL+C to quit)
INFO:     Started reloader process
INFO:     Started server process
INFO:     Waiting for application startup.
INFO:     Application startup complete.
```

**Leave this running!** ✅

---

### Terminal 2: Start the Frontend

```bash
cd /Users/brukemekonnen/stock_investment

# Start Next.js dashboard
npm run dev
```

**What you'll see:**
```
  ▲ Next.js 14.0.0
  - Local:        http://localhost:3000

 ✓ Ready in 2.3s
```

**Leave this running!** ✅

**Open browser:** http://localhost:3000

You should see the **Catalyst Radar** dashboard with REAL market data!

---

### Terminal 3: Test Connections

```bash
cd /Users/brukemekonnen/stock_investment

# Run comprehensive connection test
./test_live_integration.sh
```

**What you'll see:**
```
🧪 Testing Live Integration
================================

1. Testing real catalyst scanner...
✅ Scanner working - found 5 tickers
   First result: AAPL (confidence: 0.85)

2. Verifying real vs mock data...
✅ Real data detected (shows expected move)

3. Testing propose with scanner context...
✅ Proposal generated - Selected arm: POST_EVENT_MOMO

4. Testing E*TRADE endpoints...
ℹ️  E*TRADE not configured (expected - add credentials to test)

================================
✅ Live integration tests complete!
```

---

### Terminal 4: Start Paper Trading

```bash
cd /Users/brukemekonnen/stock_investment
source .venv/bin/activate

# Run paper trading loop (updates every 30 seconds)
python paper_trading.py --interval 30
```

**What you'll see in real-time:**
```
2024-11-03 15:23:45 - __main__ - INFO - Starting paper trading loop (interval: 30s)
==================================================
Starting trading cycle
==================================================
2024-11-03 15:23:45 - __main__ - INFO - Proposed trade - Arm: POST_EVENT_MOMO, Ticker: AAPL
2024-11-03 15:23:46 - __main__ - INFO - Trade validation: APPROVED - All checks passed
2024-11-03 15:23:51 - __main__ - INFO - Simulated fill: AAPL buy 100 @ 192.34 (slippage: 0.08%)
2024-11-03 15:23:51 - __main__ - INFO - Reward calc: entry=192.34, stop=189.50, exit=195.20, RU=2.84, R=1.01, reward=1.00
2024-11-03 15:23:51 - __main__ - INFO - Logged reward for arm POST_EVENT_MOMO: 1.0000
2024-11-03 15:23:51 - __main__ - INFO - Trading cycle completed

[Waits 30 seconds...]

==================================================
Starting trading cycle
==================================================
...
```

---

## What You're Seeing Live

### 1. Dashboard (http://localhost:3000)

**Real-time display:**
- **AAPL** - Q1 earnings event in 7 days. Expected move: 4.2%
  - Confidence: 85%
  - Liquidity: $5B
  - Spread: $0.01
  
- **TSLA** - Product launch event...
  - Confidence: 72%
  
- **NVDA** - AI chip news...
  - Confidence: 91%

**Auto-refreshes every 30 seconds** ✅

### 2. API Endpoints Working

Test them yourself:

```bash
# Health check
curl http://localhost:8000/health

# Get real catalyst scan
curl http://localhost:8000/scan | jq .

# Interactive API docs
# Open: http://localhost:8000/docs
```

### 3. Paper Trading Console

**Every 30 seconds you'll see:**

1. **Propose** - Bandit selects a strategy arm
   ```
   Selected arm: POST_EVENT_MOMO
   ```

2. **Validate** - Checks against risk rules
   ```
   Trade validation: APPROVED
   ```

3. **Fill** - Simulates execution
   ```
   Simulated fill: AAPL buy 100 @ 192.34
   ```

4. **Reward** - Calculates R-multiple
   ```
   Logged reward: 0.4500
   ```

### 4. Bandit Learning

After a few minutes, check what the bandit learned:

```bash
sqlite3 catalyst.db "
SELECT 
  arm_name,
  COUNT(*) as times_selected,
  AVG(reward) as avg_reward,
  MIN(reward) as worst,
  MAX(reward) as best
FROM bandit_logs
GROUP BY arm_name
ORDER BY avg_reward DESC;
"
```

**You'll see which strategies are working best!**

---

## Quick Visual Test Checklist

### ✅ Backend Running
- [ ] Terminal 1 shows: "Application startup complete"
- [ ] Can open: http://localhost:8000/docs
- [ ] Health check works: `curl http://localhost:8000/health`

### ✅ Frontend Running  
- [ ] Terminal 2 shows: "Ready in X.Xs"
- [ ] Browser shows: http://localhost:3000
- [ ] Dashboard displays real tickers (AAPL, TSLA, etc.)
- [ ] Auto-refresh happens (watch for 30s)

### ✅ Real Market Data Working
- [ ] `/scan` returns actual tickers (not just mock)
- [ ] Confidence scores vary (not all 0.85)
- [ ] Expected moves are calculated (e.g., "4.2%")

### ✅ Paper Trading Running
- [ ] Terminal 4 shows trading cycles
- [ ] New cycle every 30 seconds
- [ ] Arms are selected (POST_EVENT_MOMO, etc.)
- [ ] Rewards are logged

---

## Stop Everything

When done testing:

```bash
# In each terminal, press:
Ctrl + C

# Or close all terminals
```

---

## What's Happening Behind the Scenes

```
Every 30 seconds:

1. Paper Trading Loop queries /propose
   ↓
2. Backend's Bandit selects best arm based on context
   ↓
3. LLM (or fallback) generates trade plan
   ↓
4. /validate checks risk limits
   ↓
5. Fill is simulated with realistic slippage
   ↓
6. Reward is calculated in R-multiples
   ↓
7. /bandit/reward updates Thompson Sampling
   ↓
8. Saved to database (bandit_logs table)
   ↓
9. State persisted to disk (bandit_state/)
   
Loop repeats...
```

Meanwhile:
- Dashboard auto-refreshes /scan every 30s
- yfinance fetches real prices
- Bandit learns which arms perform best
- Everything logged to database

---

## View Results

### Check Database
```bash
# See recent decisions
sqlite3 catalyst.db "SELECT * FROM bandit_logs ORDER BY ts DESC LIMIT 5;"

# Performance by arm
sqlite3 catalyst.db "
SELECT 
  arm_name,
  COUNT(*) as selections,
  AVG(reward) as avg_reward
FROM bandit_logs
GROUP BY arm_name;
"
```

### Check Saved State
```bash
# View bandit learning state
ls -la bandit_state/
cat bandit_state/d7.json
```

### Check Logs
```
# API logs: In Terminal 1
# Trading logs: In Terminal 4
```

---

## Troubleshooting

### API won't start
```bash
# Check if port 8000 is in use
lsof -i :8000

# Kill it if needed
lsof -ti:8000 | xargs kill -9

# Try again
uvicorn apps.api.main:app --reload
```

### Frontend won't start
```bash
# Check if port 3000 is in use
lsof -i :3000

# Kill it if needed
lsof -ti:3000 | xargs kill -9

# Try again
npm run dev
```

### No data showing
```bash
# Check yfinance installed
pip show yfinance

# Test directly
python -c "import yfinance as yf; print(yf.Ticker('AAPL').fast_info.last_price)"
```

### Paper trading not starting
```bash
# Check dependencies
pip install httpx requests

# Check API is running
curl http://localhost:8000/health

# Try with more verbose logging
python paper_trading.py --interval 30
```

---

## 🎉 You're Live!

Once all 4 terminals are running, you have:

✅ **Real market data** streaming  
✅ **Bandit learning** from every trade  
✅ **Dashboard showing** live catalysts  
✅ **Paper trading** executing automatically  
✅ **Everything logged** to database  

Let it run for 10-15 minutes, then check the bandit performance to see what it learned!

---

## Next Steps

After testing paper trading:

1. **Analyze Results** - Check which arms performed best
2. **Tune Guardrails** - Adjust MAX_TICKET, spreads, etc. in `.env`
3. **Add E*TRADE** - Run `./setup_etrade.sh` for live trading
4. **Scale Up** - Increase frequency, add more tickers

**Questions?** Check the logs in Terminal 1 and 4 for errors.

