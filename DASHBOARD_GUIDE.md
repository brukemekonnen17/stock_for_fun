# 📊 Dashboard Guide - What You'll See

## 🎉 System Started!

The `quick_start.sh` script just opened **4 Terminal windows** for you:

### Terminal 1: Backend API
```
INFO:     Uvicorn running on http://127.0.0.1:8000
INFO:     Application startup complete.
2024-11-03 15:23:45 - apps.api.main - INFO - Loaded bandit for d=7
2024-11-03 15:23:45 - apps.api.main - INFO - ✅ API ready
```
**✅ Leave this running!**

### Terminal 2: Next.js Frontend
```
  ▲ Next.js 14.0.0
  - Local:        http://localhost:3000
  - Network:      http://192.168.1.x:3000

 ✓ Ready in 2.3s
 ○ Compiling / ...
 ✓ Compiled / in 1.2s
```
**✅ Leave this running!**

### Terminal 3: Tests + Paper Trading
```
🧪 Testing Live Integration
================================
✅ All tests passed!

Press ENTER to start paper trading...
```
**👉 Press ENTER to start the trading loop!**

### Terminal 4: Opens automatically with monitoring
Terminals should be open - check your Terminal app!

---

## 🌐 Your Two Dashboards

### Dashboard 1: Catalyst Radar
**URL:** http://localhost:3000

```
┏━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┓
┃                                            ┃
┃        🎯 Catalyst Radar                   ┃
┃   Real-time catalyst scanning & insights  ┃
┃                                            ┃
┃   [📊 View Trading Dashboard]             ┃
┃                                            ┃
┃   [🔄 Scan Now]  ☑ Auto-refresh (30s)    ┃
┃                                            ┃
┣━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┫
┃                                            ┃
┃  ╔════════════════════════════════╗       ┃
┃  ║ AAPL                     85%   ║       ┃
┃  ║ EARNINGS event in 7 days.     ║       ┃
┃  ║ Expected move: 4.2%            ║       ┃
┃  ║                                ║       ┃
┃  ║ ▸ Context                      ║       ┃
┃  ║   Liquidity: $5.0B             ║       ┃
┃  ║   Spread: $0.01                ║       ┃
┃  ╚════════════════════════════════╝       ┃
┃                                            ┃
┃  ╔════════════════════════════════╗       ┃
┃  ║ TSLA                     72%   ║       ┃
┃  ║ EARNINGS event in 3 days.     ║       ┃
┃  ║ Expected move: 6.0%            ║       ┃
┃  ╚════════════════════════════════╝       ┃
┃                                            ┃
┃  ╔════════════════════════════════╗       ┃
┃  ║ NVDA                     91%   ║       ┃
┃  ║ EARNINGS event in 5 days.     ║       ┃
┃  ║ Expected move: 5.1%            ║       ┃
┃  ╚════════════════════════════════╝       ┃
┃                                            ┃
┗━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┛
```

**Features:**
- ✅ Real-time market data from yfinance
- ✅ Auto-refresh every 30 seconds
- ✅ Confidence scores for each catalyst
- ✅ Expected move percentages
- ✅ Liquidity and spread info

---

### Dashboard 2: Trading Dashboard (NEW!)
**URL:** http://localhost:3000/trading

```
┏━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┓
┃                                                      ┃
┃        📊 Trading Dashboard                          ┃
┃   Live bandit performance and trading activity      ┃
┃                                                      ┃
┃   [🔄 Refresh]  ☑ Auto-refresh (5s)  [🎯 Catalyst] ┃
┃   Last update: 15:23:45                             ┃
┃                                                      ┃
┣━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┫
┃                                                      ┃
┃  📈 Overview                                        ┃
┃  ┌─────────────┬─────────────┬───────────────────┐ ┃
┃  │ Total       │ Active      │ Best              │ ┃
┃  │ Decisions   │ Arms        │ Performer         │ ┃
┃  │             │             │                   │ ┃
┃  │    24       │     5       │ POST_EVENT_MOMO  │ ┃
┃  └─────────────┴─────────────┴───────────────────┘ ┃
┃                                                      ┃
┣━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┫
┃                                                      ┃
┃  🎯 Strategy Performance                            ┃
┃                                                      ┃
┃  ╔═══════════════════════════╗  ╔═══════════════╗  ┃
┃  ║ POST_EVENT_MOMO    0.650  ║  ║ NEWS_SPIKE    ║  ┃
┃  ║                           ║  ║         0.420 ║  ┃
┃  ║ Times Selected: 8         ║  ║ Selected: 6   ║  ┃
┃  ║ Best:  1.000              ║  ║ Best:  0.850  ║  ┃
┃  ║ Worst: -0.350             ║  ║ Worst: -0.100 ║  ┃
┃  ║ ████████████░░░░░         ║  ║ ████████░░░░  ║  ┃
┃  ╚═══════════════════════════╝  ╚═══════════════╝  ┃
┃                                                      ┃
┃  ╔═══════════════════════════╗  ╔═══════════════╗  ┃
┃  ║ EARNINGS_PRE       0.210  ║  ║ REACTIVE      ║  ┃
┃  ║                           ║  ║         0.150 ║  ┃
┃  ║ Times Selected: 5         ║  ║ Selected: 3   ║  ┃
┃  ║ Best:  0.920              ║  ║ Best:  0.450  ║  ┃
┃  ║ Worst: -0.500             ║  ║ Worst: -0.200 ║  ┃
┃  ║ ██████░░░░░░░░░░          ║  ║ █████░░░░░░░  ║  ┃
┃  ╚═══════════════════════════╝  ╚═══════════════╝  ┃
┃                                                      ┃
┣━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┫
┃                                                      ┃
┃  📝 Recent Decisions                                ┃
┃                                                      ┃
┃  ┌──────────┬────────────────┬─────────┬──────────┐┃
┃  │ Time     │ Strategy Arm   │ Reward  │ R-Multi  │┃
┃  ├──────────┼────────────────┼─────────┼──────────┤┃
┃  │ 15:25:21 │ POST_EVENT_MOMO│ +1.0000 │ 1.00R   │┃
┃  │ 15:24:51 │ NEWS_SPIKE     │ +0.6500 │ 0.65R   │┃
┃  │ 15:24:21 │ EARNINGS_PRE   │ +0.4200 │ 0.42R   │┃
┃  │ 15:23:51 │ POST_EVENT_MOMO│ +0.8500 │ 0.85R   │┃
┃  │ 15:23:21 │ REACTIVE       │ +0.1500 │ 0.15R   │┃
┃  │ 15:22:51 │ POST_EVENT_MOMO│ -0.3500 │ -0.35R  │┃
┃  │ 15:22:21 │ NEWS_SPIKE     │ +0.5200 │ 0.52R   │┃
┃  └──────────┴────────────────┴─────────┴──────────┘┃
┃                                                      ┃
┗━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┛
```

**Features:**
- ✅ Real-time bandit performance by strategy arm
- ✅ Auto-refresh every 5 seconds
- ✅ Color-coded rewards (green = positive, red = negative)
- ✅ Performance bars showing relative strength
- ✅ Live activity feed with recent decisions
- ✅ R-multiple calculations
- ✅ Summary statistics

---

## 🔄 What Happens Automatically

### Every 5 seconds (Trading Dashboard):
1. Fetches latest bandit logs from database
2. Updates arm performance statistics
3. Refreshes recent decisions table
4. Re-calculates best performer

### Every 30 seconds (Catalyst Radar):
1. Scans market for new catalysts
2. Fetches real prices from yfinance
3. Calculates confidence scores
4. Updates expected moves

### Every 30 seconds (Paper Trading):
1. **Propose** - Bandit selects strategy arm
2. **LLM** - Generates trade plan (or uses fallback)
3. **Validate** - Checks risk guardrails
4. **Fill** - Simulates execution with slippage
5. **Reward** - Calculates R-multiple
6. **Learn** - Updates bandit parameters
7. **Log** - Saves to database

---

## 🎯 What to Watch For

### On Catalyst Radar:
- **Multiple tickers** showing (AAPL, TSLA, NVDA, MSFT, AMZN)
- **Varying confidence scores** (not all the same)
- **Real expected moves** calculated from historical data
- **Auto-refresh indicator** at the top

### On Trading Dashboard:
- **Total Decisions** increasing every 30 seconds
- **Different arms being selected** (not always the same)
- **Rewards being logged** in the Recent Decisions table
- **Best performer changing** as the bandit learns
- **Performance bars updating** based on average rewards
- **Color-coded rewards**:
  - 🟢 Green = Positive reward (> 0.5)
  - 🟡 Yellow = Small positive (0 to 0.5)
  - 🔴 Red = Negative reward

### In Paper Trading Terminal:
```
==================================================
Starting trading cycle
==================================================
2024-11-03 15:23:45 - INFO - Proposed trade - Arm: POST_EVENT_MOMO
2024-11-03 15:23:46 - INFO - Trade validation: APPROVED
2024-11-03 15:23:51 - INFO - Simulated fill: AAPL buy 100 @ 192.34
2024-11-03 15:23:51 - INFO - Reward: 1.0000
2024-11-03 15:23:51 - INFO - Trading cycle completed

[⏱️ Waiting 30 seconds for next cycle...]
```

---

## 📊 Live Monitoring Commands

Open a **5th terminal** to watch stats in real-time:

```bash
cd /Users/brukemekonnen/stock_investment

# Live monitoring (updates every 10 seconds)
./monitor_trading.sh --watch
```

You'll see:
```
📊 Live Trading Monitor
================================
📈 Trading Statistics (Last update: 15:25:30)
================================
Total Decisions: 24

Performance by Strategy Arm:
Arm                Times Selected  Avg Reward  Worst    Best
-----------------  --------------  ----------  -------  -------
POST_EVENT_MOMO    8               0.6500      -0.3500  1.0000
NEWS_SPIKE         6               0.4200      -0.1000  0.8500
EARNINGS_PRE       5               0.2100      -0.5000  0.9200
REACTIVE           3               0.1500      -0.2000  0.4500
SKIP               2               0.0000      0.0000   0.0000

Recent Decisions:
Time      Arm              Reward
--------  ---------------  --------
15:25:21  POST_EVENT_MOMO  1.0000
15:24:51  NEWS_SPIKE       0.6500
15:24:21  EARNINGS_PRE     0.4200
15:23:51  POST_EVENT_MOMO  0.8500
15:23:21  REACTIVE         0.1500

================================
Updates every 10 seconds...
```

---

## 🎉 You're Live!

### URLs to Open:
- **Catalyst Radar:** http://localhost:3000
- **Trading Dashboard:** http://localhost:3000/trading
- **API Docs:** http://localhost:8000/docs
- **API Health:** http://localhost:8000/health

### Terminal Commands:
```bash
# Check connection
curl http://localhost:8000/health

# Get latest catalysts
curl http://localhost:8000/scan | jq .

# Get bandit stats
curl http://localhost:8000/bandit/stats | jq .

# Get recent logs
curl http://localhost:8000/bandit/logs | jq .

# Watch live monitoring
./monitor_trading.sh --watch

# Check database directly
sqlite3 catalyst.db "SELECT * FROM bandit_logs ORDER BY ts DESC LIMIT 5;"
```

---

## 🛑 Stop Everything

When done:
```bash
# Press Ctrl+C in each terminal window
# Or close all Terminal windows
```

---

## 🔧 Troubleshooting

### Dashboard shows "No data yet"
- ✅ Make sure paper trading is running (Terminal 3)
- ✅ Wait 30 seconds for first cycle to complete
- ✅ Check API is running: `curl http://localhost:8000/health`

### Auto-refresh not working
- ✅ Check that checkbox is enabled in dashboard
- ✅ Look for JavaScript errors in browser console (F12)
- ✅ Ensure API is accessible: `curl http://localhost:8000/bandit/stats`

### Paper trading not starting
- ✅ Make sure you pressed ENTER in Terminal 3
- ✅ Check API is running on port 8000
- ✅ Look for errors in Terminal 1 (API logs)

### No tickers showing on Catalyst Radar
- ✅ Check yfinance is installed: `pip show yfinance`
- ✅ Test API directly: `curl http://localhost:8000/scan`
- ✅ Check internet connection (yfinance needs to fetch data)

---

## 🎊 What's Working

✅ **Real-time market data** from yfinance  
✅ **Thompson Sampling bandit** learning continuously  
✅ **LLM integration** with fallback (DeepSeek)  
✅ **Policy guardrails** enforcing risk limits  
✅ **Two beautiful dashboards** with live updates  
✅ **Paper trading loop** executing automatically  
✅ **Database logging** of all decisions  
✅ **State persistence** across restarts  
✅ **E*TRADE OAuth ready** (run `./setup_etrade.sh`)  

---

## 🚀 Next Steps

1. **Watch the dashboards** for 10-15 minutes
2. **Observe which arms perform best**
3. **Check the monitoring** with `./monitor_trading.sh --watch`
4. **Tune guardrails** in `.env` if needed
5. **Add E*TRADE** for live trading (run `./setup_etrade.sh`)

---

**Enjoy watching your AI trading system learn in real-time!** 🎉

