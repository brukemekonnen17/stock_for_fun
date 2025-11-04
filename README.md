# Stock Investment - Catalyst Radar & Paper Trading

A complete system for catalyst scanning and paper trading with **Contextual Thompson Sampling** bandit learning.

## 🎯 Features

### Backend (FastAPI)
- **Contextual Bandit**: In-memory Thompson Sampling with 5 arms (EARNINGS_PRE, POST_EVENT_MOMO, NEWS_SPIKE, REACTIVE, SKIP)
- **Policy Validators**: Risk guardrails (position limits, spread checks, stop-loss validation)
- **LLM Integration**: DeepSeek advisor for trade plan generation
- **Persistent Logging**: SQLAlchemy-backed BanditLog table

### Paper Trading
- **Automated Loop**: Cron-style propose → validate → simulate → log reward cycle
- **Quick Test Script**: Single-cycle test for debugging

### Frontend (Next.js)
- **Catalyst Radar Dashboard**: Real-time catalyst scanning with auto-refresh
- **Modern UI**: Card-based display with confidence scores and expandable context

## 📁 Structure

```
stock_investment/
├── apps/api/
│   └── main.py              ← FastAPI routes (/propose, /validate, /scan, /bandit/reward)
├── db/
│   ├── models.py            ← SQLAlchemy models (BanditLog, Event, Trade)
│   └── session.py           ← Database session management
├── libs/analytics/
│   └── bandit.py            ← Contextual Thompson Sampling implementation
├── services/
│   ├── llm/
│   │   ├── client.py        ← LLM API client
│   │   └── schema.py        ← Prompt templates
│   └── policy/
│       └── validators.py    ← Risk/policy guardrails
├── app/                     ← Next.js pages
│   ├── page.tsx             ← Catalyst Radar dashboard
│   ├── layout.tsx
│   └── *.css
├── paper_trading.py         ← Full async trading loop
├── run_paper_trading.py     ← Quick single-cycle test
└── requirements.txt

```

## 🚀 Quick Start

### 1. Install Backend Dependencies

```bash
# Create virtual environment
python -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate

# Install packages
pip install -r requirements.txt
```

### 2. Configure Environment

Copy the example env file:
```bash
cp .env.example .env
```

Edit `.env` to configure:
- `DB_URL`: Database connection (defaults to SQLite in memory)
- `DEEPSEEK_API_URL`: LLM endpoint
- `DEEPSEEK_API_KEY`: API key
- Risk limits (MAX_TICKET, MAX_POSITIONS, etc.)

### 3. Start the API

```bash
# Option 1: Using the script
chmod +x start_api.sh
./start_api.sh

# Option 2: Direct command
uvicorn apps.api.main:app --reload --port 8000
```

API will be available at `http://localhost:8000`
- Docs: `http://localhost:8000/docs`
- Health: `http://localhost:8000/health`

### 4. Install Frontend Dependencies

```bash
npm install
```

### 5. Start the Frontend

```bash
# Option 1: Using the script
chmod +x start_frontend.sh
./start_frontend.sh

# Option 2: Direct command
npm run dev
```

Dashboard will be available at `http://localhost:3000`

## 🔄 Paper Trading

### Quick Test (Single Cycle)

```bash
python run_paper_trading.py --api-url http://localhost:8000
```

This runs one complete cycle and shows detailed output at each step.

### Continuous Loop

```bash
python paper_trading.py --api-url http://localhost:8000 --interval 60 --fill-delay 5
```

Options:
- `--api-url`: API base URL (default: http://localhost:8000)
- `--interval`: Seconds between cycles (default: 60)
- `--fill-delay`: Simulated fill delay in seconds (default: 5)

Press `Ctrl+C` to stop gracefully.

## 📡 API Endpoints

### Core Endpoints

- `GET /scan` - Get catalyst opportunities (for dashboard)
- `POST /propose` - Bandit selects arm + LLM generates trade plan
- `POST /validate` - Policy validation with size adjustment
- `POST /bandit/reward` - Log reward and update bandit online

### ProposePayload Schema

```json
{
  "ticker": "AAPL",
  "price": 150.0,
  "event_type": "EARNINGS",
  "days_to_event": 3.5,
  "rank_components": {"timing": 0.8, "catalyst_strength": 0.7},
  "expected_move": 0.04,
  "backtest_kpis": {"win_rate": 0.65, "sharpe": 1.2},
  "liquidity": 5000000000,
  "spread": 0.01,
  "news_summary": "Strong earnings expected",
  "context": [0.1, 0.2, ...]  // Feature vector for bandit
}
```

### Response: ProposeResponse

```json
{
  "selected_arm": "POST_EVENT_MOMO",
  "plan": {
    "ticker": "AAPL",
    "entry_type": "limit",
    "entry_price": 149.50,
    "stop_price": 145.00,
    "target_price": 158.00,
    "timeout_days": 5,
    "confidence": 0.78,
    "reason": "Post-earnings momentum play"
  }
}
```

## 🎛️ Bandit Arms

The system learns across 5 strategy arms:

- **EARNINGS_PRE**: Enter before earnings announcements
- **POST_EVENT_MOMO**: Ride momentum after catalyst
- **NEWS_SPIKE**: React to breaking news
- **REACTIVE**: Opportunistic entries on dips
- **SKIP**: Do nothing (avoid low-quality setups)

The bandit learns which arm performs best given the context vector.

## 🔧 Configuration

Risk guardrails (configured via environment variables):

- `MAX_TICKET`: Maximum $ per trade (default: $500)
- `MAX_POSITIONS`: Max concurrent positions (default: 3)
- `MAX_PER_TRADE_LOSS`: Max $ loss per trade (default: $25)
- `DAILY_KILL_SWITCH`: Daily loss limit (default: -$75)
- `SPREAD_CENTS_MAX`: Max spread in cents (default: 5¢)
- `SPREAD_BPS_MAX`: Max spread in bps (default: 50 bps)

## 📊 Database

The system creates tables automatically on startup:
- `bandit_logs`: Arm selections, context vectors, rewards
- `events`: Catalyst events (extensible)
- `signals`: Trading signals (extensible)
- `trades`: Trade history (extensible)

SQLite by default, easily switch to PostgreSQL via `DB_URL`.

## 🧪 Development

Run tests:
```bash
pytest  # Coming soon
```

Check types:
```bash
mypy apps/ services/ libs/
```

## 🎨 Catalyst Radar Dashboard

The Next.js dashboard (`http://localhost:3000`) shows:
- Live catalyst scan results
- Confidence scores (color-coded: green 80%+, yellow 60-80%, red <60%)
- Event timing and details
- Auto-refresh every 30 seconds (toggleable)
- Expandable context JSON

## 📝 Next Steps

1. Wire real market data to `/scan`
2. Integrate actual broker (Alpaca/IB) for fills
3. Implement reward calculation based on actual P&L
4. Add backtesting framework
5. Build performance analytics dashboard

