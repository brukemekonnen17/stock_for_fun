# 🚀 Quick Start Guide

## Prerequisites

- Python 3.11+
- Node.js 18+
- npm or yarn

## 1. Setup Backend (2 minutes)

```bash
# Create and activate virtual environment
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate

# Install Python dependencies
pip install -r requirements.txt

# Create .env file (copy from .env.example if blocked)
cat > .env << 'EOF'
DB_URL=sqlite+pysqlite:///./catalyst.db
DEEPSEEK_API_URL=http://localhost:11434/v1/chat/completions
DEEPSEEK_API_KEY=changeme
MAX_TICKET=500
MAX_POSITIONS=3
MAX_PER_TRADE_LOSS=25
DAILY_KILL_SWITCH=-75
SPREAD_CENTS_MAX=0.05
SPREAD_BPS_MAX=50
SLIPPAGE_BPS=10
TRADING_TZ=America/New_York
EOF

# Start the API server
./start_api.sh
# OR: uvicorn apps.api.main:app --reload --port 8000
```

✅ API running at http://localhost:8000
- Docs: http://localhost:8000/docs
- Health: http://localhost:8000/health

## 2. Setup Frontend (1 minute)

In a **new terminal**:

```bash
# Install Node dependencies
npm install

# Start Next.js dev server
./start_frontend.sh
# OR: npm run dev
```

✅ Dashboard at http://localhost:3000

## 3. Test Paper Trading (30 seconds)

In a **new terminal** with venv activated:

```bash
# Quick single-cycle test
python run_paper_trading.py
```

You should see:
```
==================================================
PAPER TRADING CYCLE
==================================================
[1/4] Proposing trade...
   ✅ Selected arm: POST_EVENT_MOMO
   ✅ Plan received: 8 keys
[2/4] Validating trade...
   ✅ Trade approved: All checks passed
[3/4] Simulating fill...
   ✅ Fill: AAPL @ $150.12 (slippage: 0.08%)
[4/4] Logging reward...
   ✅ Reward logged: -0.0080
==================================================
CYCLE COMPLETED SUCCESSFULLY
==================================================
```

## 4. Run Continuous Paper Trading

```bash
# Runs every 60 seconds
python paper_trading.py --interval 60
```

Press `Ctrl+C` to stop.

## 🎯 What's Running

| Component | URL | Purpose |
|-----------|-----|---------|
| FastAPI Backend | http://localhost:8000 | Bandit + LLM + Validators |
| API Docs | http://localhost:8000/docs | Interactive API explorer |
| Catalyst Radar | http://localhost:3000 | Real-time dashboard |
| Paper Trading | Terminal | Automated trading loop |

## 🔍 Check It's Working

### Test the API:
```bash
curl http://localhost:8000/health
curl http://localhost:8000/scan
```

### Check the Dashboard:
Open http://localhost:3000 - you should see 3 catalyst cards (AAPL, TSLA, NVDA)

### Check Database:
```bash
sqlite3 catalyst.db "SELECT * FROM bandit_logs LIMIT 5;"
```

## ⚠️ Troubleshooting

### Port 8000 already in use:
```bash
lsof -ti:8000 | xargs kill -9
```

### Module import errors:
Make sure you're running from the project root and venv is activated.

### LLM errors (services.llm.client):
The system will mock LLM responses if the endpoint isn't available. Check your DEEPSEEK_API_URL in .env.

## 📚 Next Steps

1. View API docs: http://localhost:8000/docs
2. Read full README: [README.md](README.md)
3. Customize guardrails in `.env`
4. Wire real market data to `/scan`
5. Add actual broker integration

## 🎉 You're Ready!

The system is:
- ✅ Learning from each trade cycle
- ✅ Logging rewards to SQLite
- ✅ Validating trades against risk limits
- ✅ Showing catalysts on the dashboard

Happy trading! 🚀

