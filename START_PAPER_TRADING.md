# 🎯 Start Paper Trading - Complete Guide

## ✅ Your System Status

**API:** ✅ Running on port 8000  
**Paper Trading:** ✅ Ready to start  
**Database:** ✅ Connected  
**Bandit:** ✅ Initialized  

---

## 🚀 Start Trading NOW

### In Your Terminal (the one you just used):

```bash
cd /Users/brukemekonnen/stock_investment
source .venv/bin/activate
python paper_trading.py --interval 30
```

---

## 📺 What You'll See

### First Cycle (happens immediately):

```
2025-11-03 17:15:00 - __main__ - INFO - Starting paper trading loop (interval: 30s)

==================================================
Starting trading cycle
==================================================

2025-11-03 17:15:00 - __main__ - INFO - Proposed trade - Arm: POST_EVENT_MOMO, Ticker: AAPL
2025-11-03 17:15:01 - __main__ - INFO - Trade validation: APPROVED - All checks passed
2025-11-03 17:15:01 - __main__ - INFO - Simulated fill: AAPL buy 100 @ 192.34 (slippage: 0.08%)
2025-11-03 17:15:01 - __main__ - INFO - Reward calc: entry=192.34, stop=189.50, exit=195.20, RU=2.84, R=1.01, reward=1.00
2025-11-03 17:15:01 - __main__ - INFO - Logged reward for arm POST_EVENT_MOMO: 1.0000
2025-11-03 17:15:01 - __main__ - INFO - Trading cycle completed

[⏱️ Sleeping for 30 seconds...]
```

### Second Cycle (30 seconds later):

```
==================================================
Starting trading cycle
==================================================

2025-11-03 17:15:31 - __main__ - INFO - Proposed trade - Arm: NEWS_SPIKE, Ticker: TSLA
2025-11-03 17:15:32 - __main__ - INFO - Trade validation: APPROVED - All checks passed
2025-11-03 17:15:32 - __main__ - INFO - Simulated fill: TSLA buy 50 @ 245.67
2025-11-03 17:15:32 - __main__ - INFO - Reward: 0.6500
2025-11-03 17:15:32 - __main__ - INFO - Trading cycle completed

[⏱️ Sleeping for 30 seconds...]
```

**It continues every 30 seconds!**

---

## 🎯 What's Happening

Every 30 seconds, your AI:

1. **Proposes Trade** 
   - Bandit selects best strategy arm (POST_EVENT_MOMO, NEWS_SPIKE, etc.)
   - Picks a ticker (AAPL, TSLA, NVDA, etc.)
   
2. **Validates**
   - Checks risk rules (max ticket, position limits, spreads, etc.)
   - Either APPROVED or REJECTED

3. **Simulates Fill**
   - Executes at simulated price
   - Includes realistic slippage

4. **Calculates Reward**
   - Uses R-multiple formula
   - Reward = (Exit - Entry) / (Entry - Stop)
   - Clipped to [-1.0, 1.0]

5. **Updates Bandit**
   - Learns which strategies work best
   - Adjusts probabilities for next selection

---

## 📊 Monitor Performance

### While paper trading is running, open a NEW terminal:

```bash
cd /Users/brukemekonnen/stock_investment
./monitor_trading.sh --watch
```

**You'll see:**

```
📊 Live Trading Monitor
================================
📈 Trading Statistics (Last update: 17:16:30)
================================
Total Decisions: 5

Performance by Strategy Arm:
Arm                Times Selected  Avg Reward  Worst    Best
-----------------  --------------  ----------  -------  -------
POST_EVENT_MOMO    2               0.8250      0.6500   1.0000
NEWS_SPIKE         2               0.5500      0.4500   0.6500
EARNINGS_PRE       1               0.7200      0.7200   0.7200

Recent Decisions:
Time      Arm              Reward
--------  ---------------  --------
17:16:21  POST_EVENT_MOMO  1.0000
17:15:51  NEWS_SPIKE       0.6500
17:15:21  EARNINGS_PRE     0.7200
17:14:51  POST_EVENT_MOMO  0.6500
17:14:21  NEWS_SPIKE       0.4500

================================
Updates every 10 seconds...
```

---

## 🔍 Check Database

```bash
cd /Users/brukemekonnen/stock_investment

# See all decisions
sqlite3 catalyst.db "SELECT * FROM bandit_logs ORDER BY ts DESC LIMIT 10;"

# Performance summary
sqlite3 catalyst.db "
SELECT 
  arm_name,
  COUNT(*) as times_selected,
  ROUND(AVG(reward), 4) as avg_reward,
  ROUND(MIN(reward), 4) as worst,
  ROUND(MAX(reward), 4) as best
FROM bandit_logs
GROUP BY arm_name
ORDER BY avg_reward DESC;
"
```

---

## 🛑 Stop Paper Trading

In the terminal where it's running:

**Press:** `Ctrl + C`

**You'll see:**
```
^C
2025-11-03 17:20:00 - __main__ - INFO - Paper trading stopped
2025-11-03 17:20:00 - apps.api.main - INFO - Saving all bandit states...
2025-11-03 17:20:00 - apps.api.main - INFO - All bandit states saved
```

---

## 🎓 Understanding the Output

### Strategy Arms (what the bandit selects):
- **POST_EVENT_MOMO** - Trade momentum after major events
- **NEWS_SPIKE** - React to sudden news catalysts
- **EARNINGS_PRE** - Position before earnings
- **REACTIVE** - Quick reaction to price moves
- **SKIP** - Wait for better opportunities

### Reward Scores:
- **+1.0** = Perfect trade (hit full target)
- **+0.5** = Good trade (50% of target)
- **0.0** = Breakeven
- **-0.5** = Small loss (50% of stop)
- **-1.0** = Full stop loss hit

### The Bandit Learning:
Over time, you'll see:
- **Some arms selected more often** (bandit finds winners)
- **Average rewards improving** (learning what works)
- **Worst arms phased out** (exploration → exploitation)

---

## 🎉 What Happens Next

1. **Let it run for 10-15 minutes** (20-30 cycles)
2. **Watch the monitor** to see which strategies win
3. **Check the database** to see all decisions
4. **The bandit learns** and gets smarter!

After enough data:
- The best arms will be selected more often
- Average reward will increase
- You'll see clear performance patterns

---

## 🔧 Optional: Adjust Settings

Edit `.env` to tune the system:

```bash
# Risk limits
MAX_TICKET=500              # Max $ per position
MAX_POSITIONS=3             # Max concurrent positions
MAX_PER_TRADE_LOSS=25       # Max $ loss per trade
DAILY_KILL_SWITCH=-75       # Stop if down this much

# Spread limits
SPREAD_CENTS_MAX=0.05       # Max 5¢ spread
SPREAD_BPS_MAX=50           # Max 0.5% spread

# Trading frequency
# (passed as --interval flag to paper_trading.py)
```

---

## 🎊 You're Trading!

Your AI trading system is now:
- ✅ Proposing trades
- ✅ Validating them
- ✅ Executing (simulated)
- ✅ Learning from results
- ✅ Getting smarter over time

**This is Thompson Sampling in action!**

---

## 📚 Next Steps

1. **Run it for an hour** - Get meaningful data
2. **Analyze which arms perform best**
3. **Adjust risk parameters if needed**
4. **Add E*TRADE OAuth** (run `./setup_etrade.sh`)
5. **Go live!** (when ready)

---

**Now run the commands and watch your AI trade! 🚀**

