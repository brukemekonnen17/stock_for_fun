# 📚 Technical Documentation - Stock Investment Trading System

## 🎯 System Overview

A production-ready algorithmic trading system that:
1. Scans stocks for catalyst events (earnings, news, etc.)
2. Uses contextual bandits to select trading strategies
3. Generates trade plans via LLM (DeepSeek)
4. Validates trades through policy guardrails
5. Provides human-in-the-loop approval via dashboard
6. Tracks performance and learns from outcomes

**Current Status**: Functional with Yahoo Finance integration. Paper trading ready. Live broker integration (E*TRADE) available but requires OAuth setup.

---

## 🏗️ Architecture

```
┌─────────────────┐
│  Dashboard      │  (HTML/JS frontend)
│  trading_dash   │
└────────┬────────┘
         │ HTTP/REST
┌────────▼────────┐
│  FastAPI        │  (apps/api/main.py)
│  Backend        │
└────────┬────────┘
         │
    ┌────┴────┬──────────┬─────────────┐
    │         │          │             │
┌───▼───┐ ┌──▼──┐ ┌─────▼──────┐ ┌────▼─────┐
│Bandit │ │ LLM │ │Market Data │ │Broker   │
│       │ │Client│ │Adapter     │ │(ETrade) │
└───────┘ └──────┘ └────────────┘ └─────────┘
```

### Core Components

1. **API Layer** (`apps/api/main.py`)
   - FastAPI REST endpoints
   - Request/response validation
   - CORS enabled for dashboard

2. **Decision Engine** (`services/`)
   - `policy/validators.py` - Risk guardrails
   - `llm/client.py` - Trade plan generation
   - `analysis/explain.py` - Deterministic "why selected" analysis

3. **Learning System** (`libs/analytics/`)
   - `bandit.py` - Contextual Thompson Sampling
   - `persistence.py` - State saving/loading

4. **Data Sources**
   - `services/marketdata/yf_adapter.py` - Yahoo Finance (free tier)
   - `services/news/newsapi_adapter.py` - NewsAPI (requires key)
   - `services/scanner/catalyst_scanner.py` - Opportunity scanning

5. **Broker Integration** (`services/broker/`)
   - `base.py` - Broker abstraction interface
   - `etrade_client.py` - E*TRADE OAuth1 implementation

6. **Database** (`db/`)
   - SQLAlchemy ORM
   - Models: `Trade`, `BanditLog`, `Event`, `Signal`
   - SQLite (default) or PostgreSQL compatible

---

## 📡 API Endpoints

### Core Trading Endpoints

#### `GET /analyze/{ticker}`
**Purpose**: Analyze any stock ticker and get full trade recommendation

**Request**:
```http
GET /analyze/NVDA
```

**Response**:
```json
{
  "selected_arm": "POST_EVENT_MOMO",
  "plan": {
    "ticker": "NVDA",
    "entry_type": "limit",
    "entry_price": 485.50,
    "stop_price": 475.00,
    "target_price": 510.00,
    "timeout_days": 5,
    "confidence": 0.72,
    "reason": "..."
  },
  "decision_id": "1234567890.123",
  "analysis": {
    "ticker": "NVDA",
    "catalyst": {
      "event_type": "EARNINGS",
      "days_to_event": 7.0,
      "expected_move": 0.045,
      "materiality": 0.6,
      "rank": 82.3
    },
    "strategy": {
      "selected_arm": "POST_EVENT_MOMO",
      "reason": "Post-event momentum strategy selected...",
      "gating_facts": [
        "Expected move 4.5% ≥ 3%",
        "Rank ≥ 70",
        "Liquidity sufficient"
      ]
    },
    "news": [...],
    "history": {...},
    "market": {
      "price": 485.50,
      "spread": 0.02,
      "dollar_adv": 5000000000,
      "rsi14": 58.3,
      "atr14": 12.45
    },
    "llm_confidence": 0.72
  }
}
```

**Limitations**:
- Depends on Yahoo Finance API (rate limits)
- Retries 3x with exponential backoff (3s, 6s, 12s)
- 5-minute cache for prices
- May fail if Yahoo Finance is down

---

#### `POST /propose`
**Purpose**: Propose a trade with full context (used by paper trading loop)

**Request**:
```json
{
  "ticker": "AAPL",
  "price": 192.50,
  "event_type": "EARNINGS",
  "days_to_event": 7.0,
  "rank_components": {
    "immediacy": 0.6,
    "materiality": 0.6,
    "liquidity": 1.0,
    "expected_move": 0.04,
    "news": 0.5
  },
  "expected_move": 0.04,
  "backtest_kpis": {
    "hit_rate": 0.54,
    "avg_win": 0.012,
    "avg_loss": -0.008,
    "max_dd": -0.06
  },
  "liquidity": 5000000000,
  "spread": 0.01,
  "news_summary": "Q1 earnings expected...",
  "context": [0.6, 0.6, 1.0, 0.4, 0.5, 0.04, 7],
  "decision_id": "1234567890.123"
}
```

**Response**: Same as `/analyze/{ticker}`

---

#### `POST /validate`
**Purpose**: Validate trade plan against policy guardrails

**Request**:
```json
{
  "plan": {
    "ticker": "AAPL",
    "entry_type": "limit",
    "entry_price": 192.00,
    "stop_price": 189.50,
    "target_price": 196.50,
    "timeout_days": 5,
    "confidence": 0.72,
    "reason": "..."
  },
  "market": {
    "price": 192.50,
    "spread": 0.01,
    "avg_dollar_vol": 5000000000
  },
  "context": {
    "open_positions": 0,
    "realized_pnl_today": 0.0
  },
  "decision_id": "1234567890.123"
}
```

**Response**:
```json
{
  "verdict": "APPROVED" | "REJECTED" | "REVIEW",
  "reason": "All checks passed",
  "adjusted_size": 25
}
```

**Policy Rules** (configurable via env vars):
- `MAX_TICKET` = $500 (default)
- `MAX_POSITIONS` = 3 (default)
- `MAX_PER_TRADE_LOSS` = $25 (default)
- `DAILY_KILL_SWITCH` = -$75 (default)
- `SPREAD_CENTS_MAX` = $0.05 (default)
- `SPREAD_BPS_MAX` = 50 bps (default)
- `SLIPPAGE_BPS` = 10 bps (default)

---

#### `POST /bandit/reward`
**Purpose**: Log trade outcome and update bandit learning

**Request**:
```json
{
  "arm_name": "POST_EVENT_MOMO",
  "context": [0.6, 0.6, 1.0, 0.4, 0.5, 0.04, 7],
  "reward": 0.35,
  "decision_id": "1234567890.123",
  "meta": {
    "ticker": "AAPL",
    "entry_px": 192.00,
    "exit_px": 196.50,
    "r_multiple": 0.35
  }
}
```

**Response**:
```json
{
  "status": "ok"
}
```

**Note**: Reward is R-multiple (risk-adjusted P&L), typically clipped to [-1.0, 1.0]

---

### Scanning & Discovery

#### `GET /scan?min_rank=70&limit=10`
**Purpose**: Scan universe for catalyst opportunities

**Response**:
```json
[
  {
    "symbol": "AAPL",
    "catalyst": "EARNINGS event in 7 days. Expected move: 4.0%",
    "confidence": 0.85,
    "timestamp": "2024-01-15T10:00:00Z",
    "context": {
      "event_type": "EARNINGS",
      "rank": 82.3,
      "expected_move": 0.04,
      "liquidity": 5000000000,
      "spread": 0.01
    }
  }
]
```

**Universe**: `["AAPL", "TSLA", "NVDA", "MSFT", "AMZN", "GOOGL", "META", "AMD", "NFLX", "DIS"]`

---

### Broker Endpoints (E*TRADE)

#### `GET /positions`
**Purpose**: Get current positions from broker

**Auth**: Requires E*TRADE OAuth tokens

#### `POST /orders`
**Purpose**: Place order via broker

**Auth**: Requires E*TRADE OAuth tokens

#### `POST /orders/cancel/{broker_order_id}`
**Purpose**: Cancel pending order

**Auth**: Requires E*TRADE OAuth tokens

#### `POST /oauth/request_token`
**Purpose**: Step 1 of E*TRADE OAuth flow

#### `POST /oauth/exchange`
**Purpose**: Step 2 of E*TRADE OAuth flow (exchange PIN for tokens)

---

### Monitoring & Stats

#### `GET /bandit/stats`
**Purpose**: Get bandit performance statistics

**Response**:
```json
{
  "total": 150,
  "arm_stats": [
    {
      "arm_name": "POST_EVENT_MOMO",
      "count": 45,
      "avg_reward": 0.23,
      "max_reward": 0.87,
      "min_reward": -0.45
    }
  ]
}
```

#### `GET /bandit/logs?limit=50`
**Purpose**: Get recent bandit reward logs

---

## 🔧 Implementation Details

### Bandit Algorithm

**Location**: `libs/analytics/bandit.py`

**Algorithm**: Contextual Thompson Sampling (linear model)

**Arms** (strategies):
- `EARNINGS_PRE` - Pre-earnings plays
- `POST_EVENT_MOMO` - Post-event momentum
- `NEWS_SPIKE` - News-driven trades
- `REACTIVE` - Reactive to market moves
- `SKIP` - No trade

**Context Vector** (7-dim):
```python
[
  immediacy,      # How soon is the catalyst?
  materiality,    # How material is the event?
  liquidity,      # Liquidity score (0-1)
  expected_move,  # Expected price move (0-1)
  news_score,     # News sentiment/volume (0-1)
  expected_move,  # Duplicate for feature engineering
  days_to_event   # Days until catalyst
]
```

**Persistence**: Saves `A` (precision) and `b` (covariance) matrices to `bandit_state/` on shutdown, loads on startup.

---

### LLM Integration

**Location**: `services/llm/client.py`

**Provider**: DeepSeek API (configurable)

**Environment Variables**:
```bash
DEEPSEEK_API_URL=https://api.deepseek.com/v1/chat/completions
DEEPSEEK_API_KEY=sk-...
LLM_MAX_RETRIES=2
```

**Features**:
- Retry with exponential backoff
- JSON schema validation
- Fallback to mock plan on failure
- Timeout handling (30s total, 5s connect)

**Fallback Behavior**: If LLM fails, generates safe "SKIP" plan with:
- Entry: 99.5% of current price
- Stop: 2% below entry
- Target: 3% above entry
- Confidence: 0.5

**Important**: Analysis (news, market context, catalyst) is **deterministic** and still appears even if LLM fails.

---

### Market Data Adapter

**Location**: `services/marketdata/yf_adapter.py`

**Provider**: Yahoo Finance (via `yfinance` library)

**Methods**:
- `last_quote(ticker)` - Get current price, bid, ask
- `daily_ohlc(ticker, lookback=60)` - Get OHLC history
- `spread_proxy(ticker)` - Estimate bid-ask spread
- `compute_rsi(ticker, length=14)` - RSI indicator
- `compute_atr(ticker, length=14)` - ATR indicator

**Retry Logic**:
- 3 attempts with exponential backoff (3s, 6s, 12s)
- Detects rate limit (429) errors
- Falls back through: `fast_info` → `history()` → `info` dict

**Caching**: 5-minute TTL for prices

**Limitations**:
- ✅ Free tier (no API key needed)
- ❌ Rate limits (429 errors common)
- ❌ No real-time Level 2 data
- ❌ Spread is estimated, not actual
- ❌ May fail during market hours due to traffic

**Error Handling**:
- Returns clear error messages
- Suggests waiting 1-2 minutes
- Recommends trying different tickers

---

### News Integration

**Location**: `services/news/newsapi_adapter.py`

**Provider**: NewsAPI (optional, requires key)

**Environment Variable**:
```bash
NEWSAPI_KEY=your_key_here
```

**Fallback**: Stub implementation if key not set or on error

**Features**:
- Fetches last 24h news for ticker
- Simple sentiment estimation (-1 to +1)
- Limits to 5 items

---

### Deterministic Analysis

**Location**: `services/analysis/explain.py`

**Purpose**: Generate "why selected" explanation from facts (not LLM)

**Functions**:
- `catalyst_from_payload(payload)` - Extract catalyst info
- `compute_market_context(ticker, price, spread, liquidity)` - Market metrics (RSI, ATR)
- `recent_news(ticker, limit=5)` - Fetch news items
- `build_perf_stats(ticker, event_type, backtest_kpis)` - Historical performance
- `brief_reason_for_arm(arm, catalyst, market)` - Strategy rationale
- `gating_facts(catalyst, market)` - Policy checks passed

**Key Point**: This analysis is always generated, even if LLM fails. It provides transparency into why a stock was selected.

---

## 🔐 Configuration

### Environment Variables

```bash
# Database
DB_URL=sqlite+pysqlite:///./catalyst.db

# LLM (DeepSeek)
DEEPSEEK_API_URL=https://api.deepseek.com/v1/chat/completions
DEEPSEEK_API_KEY=sk-...
LLM_MAX_RETRIES=2

# News (optional)
NEWSAPI_KEY=your_key_here

# E*TRADE (for live trading)
ETRADE_CONSUMER_KEY=...
ETRADE_CONSUMER_SECRET=...
ETRADE_ACCESS_TOKEN=...
ETRADE_ACCESS_TOKEN_SECRET=...
ETRADE_ACCOUNT_ID_KEY=...
ETRADE_SANDBOX=true  # or false for live

# Policy Limits (optional, defaults shown)
MAX_TICKET=500
MAX_POSITIONS=3
MAX_PER_TRADE_LOSS=25
DAILY_KILL_SWITCH=-75
SPREAD_CENTS_MAX=0.05
SPREAD_BPS_MAX=50
SLIPPAGE_BPS=10
```

---

## 🗄️ Database Schema

**Location**: `db/models.py`

### Tables

**`trades`**:
- `trade_id` (PK)
- `ticker`, `entry_time`, `entry_px`
- `exit_time`, `exit_px` (nullable)
- `shares`, `reason_in`, `reason_out`
- `pnl`, `pnl_pct`, `max_dd_pct`

**`bandit_logs`**:
- `id` (PK)
- `ts`, `arm_name`
- `x_json` (context vector)
- `reward`

**`events`**:
- `event_id` (PK)
- `ticker`, `event_type`, `event_time`
- `headline`, `url`, `confidence`

**`signals`**:
- `signal_id` (PK)
- `ticker`, `asof_time`, `signal_name`
- `score`, `meta_json`

---

## 📊 Data Flow

### Stock Analysis Flow

```
1. User enters ticker (e.g., "NVDA")
   ↓
2. GET /analyze/NVDA
   ↓
3. Fetch market data (Yahoo Finance)
   ├─> last_quote() → price, spread
   ├─> daily_ohlc() → history for liquidity/volatility
   └─> Retry if rate limited
   ↓
4. Compute market context
   ├─> RSI(14) via pandas_ta
   ├─> ATR(14) via pandas_ta
   └─> Dollar ADV calculation
   ↓
5. Fetch news (NewsAPI or stub)
   ↓
6. Build context vector [7-dim]
   ↓
7. Bandit selects arm (strategy)
   ↓
8. Generate "why selected" analysis (deterministic)
   ├─> Catalyst info
   ├─> Strategy rationale
   ├─> News items
   ├─> Market context
   └─> Performance stats
   ↓
9. LLM generates trade plan (or fallback)
   ├─> Entry type, price, stop, target
   ├─> Timeout, confidence
   └─> Reasoning
   ↓
10. Return ProposeResponse with analysis
```

### Paper Trading Loop Flow

```
1. Scanner finds opportunity (or manual selection)
   ↓
2. POST /propose with full context
   ↓
3. Bandit + LLM generate plan
   ↓
4. Human approves/rejects (dashboard)
   ↓
5. POST /validate → Policy checks
   ↓
6. If approved: Simulate fill (paper trading)
   ↓
7. Calculate R-multiple reward
   ↓
8. POST /bandit/reward → Update learning
   ↓
9. Repeat
```

---

## 🚨 Known Limitations

### Yahoo Finance API

**Issues**:
1. Rate limiting (429 errors)
   - Common during market hours
   - No documented rate limits
   - Solution: Retry with backoff, cache results

2. Missing fields
   - `fast_info` doesn't always have `currentTradingPeriod`
   - Solution: Multiple fallbacks (`last_price` → `regular_market_price` → `history()` → `info` dict)

3. Delayed data
   - Free tier: 15-20 min delay
   - Solution: Acceptable for paper trading

4. No Level 2 data
   - Spread is estimated
   - Solution: Uses 5bps proxy or intraday range

**Workarounds**:
- ✅ Retry logic with exponential backoff
- ✅ 5-minute caching
- ✅ Clear error messages
- ✅ Graceful degradation

**Recommendation for Production**: Use paid market data API (Alpha Vantage, IEX Cloud, Polygon.io)

---

### LLM Integration

**Limitations**:
1. API costs (DeepSeek charges per token)
2. Rate limits (may vary by provider)
3. Response time (typically 2-5 seconds)
4. JSON parsing errors (rare, handled with fallback)

**Fallback**: Mock plan with safe defaults

**Improvement Ideas**:
- Cache LLM responses for similar contexts
- Batch requests
- Use cheaper LLM for simple cases

---

### News API

**Limitations**:
1. Requires API key (free tier: 100 requests/day)
2. Limited historical data
3. Sentiment analysis is simple (keyword-based)

**Fallback**: Stub returns empty list

---

### Broker Integration

**Current Status**: E*TRADE OAuth implemented, but requires:
1. Consumer key/secret from E*TRADE developer account
2. OAuth PIN flow (out-of-band)
3. Access tokens (expire, need refresh)

**Limitations**:
1. OAuth flow requires manual steps
2. Sandbox vs. live environments
3. Order status polling not implemented
4. Error handling could be improved

**Production Considerations**:
- Add token refresh logic
- Implement order status polling
- Add position reconciliation
- Handle partial fills

---

## 📁 File Structure

```
stock_investment/
├── apps/
│   └── api/
│       ├── main.py              # FastAPI application, all endpoints
│       └── schemas.py           # Pydantic models for API
├── db/
│   ├── models.py                # SQLAlchemy ORM models
│   └── session.py              # Database session management
├── libs/
│   └── analytics/
│       ├── bandit.py            # Contextual Thompson Sampling
│       └── persistence.py       # Bandit state save/load
├── services/
│   ├── analysis/
│   │   └── explain.py          # Deterministic analysis
│   ├── broker/
│   │   ├── base.py             # Broker interface
│   │   ├── etrade_client.py    # E*TRADE implementation
│   │   └── etrade_oauth.py    # OAuth helpers
│   ├── llm/
│   │   ├── client.py           # DeepSeek API client
│   │   └── schema.py           # LLM prompt templates
│   ├── marketdata/
│   │   ├── base.py             # MarketData protocol
│   │   └── yf_adapter.py      # Yahoo Finance adapter
│   ├── news/
│   │   ├── newsapi_adapter.py  # NewsAPI integration
│   │   └── simple_news.py      # Stub fallback
│   ├── policy/
│   │   └── validators.py       # Risk guardrails
│   └── scanner/
│       └── catalyst_scanner.py # Opportunity scanning
├── tests/
│   ├── test_api.py
│   ├── test_bandit.py
│   └── test_validators.py
├── paper_trading.py            # Paper trading loop
├── trading_dashboard.html      # Web dashboard
├── requirements.txt
└── README.md
```

---

## 🔄 Next Steps / Improvement Areas

### High Priority

1. **Market Data Provider**
   - [ ] Integrate paid provider (Alpha Vantage, IEX Cloud)
   - [ ] Real-time Level 2 data for accurate spreads
   - [ ] WebSocket streaming for live prices

2. **Event Calendar**
   - [ ] Integrate earnings calendar API
   - [ ] Real catalyst event detection
   - [ ] Historical event tracking

3. **Catalyst Ranking**
   - [ ] Replace stub rank calculation
   - [ ] ML-based ranking model
   - [ ] Feature engineering for catalysts

4. **Order Management**
   - [ ] Order status polling
   - [ ] Position reconciliation
   - [ ] Partial fill handling

### Medium Priority

5. **Performance Tracking**
   - [ ] Better backtest KPIs from historical data
   - [ ] Sharpe ratio, Sortino ratio
   - [ ] Drawdown analysis

6. **News Enhancement**
   - [ ] Better sentiment analysis (NLP model)
   - [ ] Event extraction (who, what, when)
   - [ ] News aggregation from multiple sources

7. **Dashboard Improvements**
   - [ ] Real-time updates (WebSocket)
   - [ ] Historical performance charts
   - [ ] Portfolio view

8. **Testing**
   - [ ] Integration tests with mock APIs
   - [ ] Paper trading loop tests
   - [ ] Load testing

### Low Priority

9. **Multi-Broker Support**
   - [ ] Alpaca integration
   - [ ] Interactive Brokers
   - [ ] Abstract broker interface usage

10. **Advanced Features**
    - [ ] Options trading support
    - [ ] Multi-leg strategies
    - [ ] Portfolio optimization

---

## 🧪 Testing

### Unit Tests

```bash
pytest tests/
```

**Coverage**:
- `test_validators.py` - Policy validation
- `test_bandit.py` - Bandit selection/update
- `test_api.py` - API endpoints

### Smoke Tests

```bash
./smoke_tests.sh
```

**Tests**:
- `/health`
- `/scan`
- `/propose`
- `/validate`
- `/bandit/reward`

### Manual Testing

1. Start API: `uvicorn apps.api.main:app --reload`
2. Open dashboard: `open trading_dashboard.html`
3. Analyze stock: Enter ticker, click "Analyze"
4. Approve/reject trade
5. Check stats: `/bandit/stats`

---

## 📝 Code Examples

### Adding a New Market Data Provider

```python
# services/marketdata/new_provider.py
from services.marketdata.base import MarketData

class NewProviderAdapter:
    def last_quote(self, ticker: str) -> dict:
        # Implement provider-specific logic
        return {"price": ..., "bid": ..., "ask": ..., "timestamp": ...}
    
    def daily_ohlc(self, ticker: str, lookback: int = 60):
        # Implement
        return [...]
```

Update `apps/api/main.py`:
```python
from services.marketdata.new_provider import NewProviderAdapter
market_data = NewProviderAdapter()
```

### Adding a New Bandit Arm

```python
# In apps/api/main.py
_default_arms = [
    Arm("EARNINGS_PRE"),
    Arm("POST_EVENT_MOMO"),
    Arm("NEWS_SPIKE"),
    Arm("REACTIVE"),
    Arm("SKIP"),
    Arm("NEW_STRATEGY"),  # Add here
]
```

### Adding a New API Endpoint

```python
# In apps/api/main.py
@app.get("/new-endpoint")
def new_endpoint(param: str):
    # Implementation
    return {"result": "..."}
```

---

## 🔍 Debugging

### API Logs

```python
# Logging is configured in apps/api/main.py
# Level: INFO
# Format: timestamp - name - level - message
```

### Common Issues

1. **"Could not fetch price"**
   - Check Yahoo Finance status
   - Wait 1-2 minutes and retry
   - Try different ticker

2. **"LLM unavailable"**
   - Check `DEEPSEEK_API_KEY`
   - Check API balance
   - Fallback mock plan should still work

3. **"No historical data"**
   - Ticker might be delisted
   - Try different ticker
   - Check `daily_ohlc()` implementation

4. **CORS errors**
   - Check `CORSMiddleware` configuration
   - Ensure dashboard uses correct API URL

---

## 📚 Key Concepts

### R-Multiple (Reward Calculation)

```
R = (Exit Price - Entry Price) / (Entry Price - Stop Price)

Reward = clip(R, -1.0, 1.0)
```

**Example**:
- Entry: $100
- Stop: $98
- Exit: $104
- R = (104 - 100) / (100 - 98) = 4 / 2 = 2.0R
- Clipped to 1.0 (max reward)

### Bandit Context Vector

7-dimensional feature vector:
```
[immediacy, materiality, liquidity_score, expected_move, news_score, expected_move_dup, days_to_event]
```

### Policy Validation Flow

1. Check daily kill switch
2. Check max positions
3. Check liquidity
4. Check spread (cents + bps)
5. Calculate worst-case entry (spread + slippage)
6. Calculate max shares by ticket size
7. Calculate max shares by loss cap
8. Take minimum → `adjusted_size`

---

## 🎓 Learning Resources

### Bandit Algorithms
- Contextual Bandits: https://en.wikipedia.org/wiki/Multi-armed_bandit#Contextual_bandits
- Thompson Sampling: https://en.wikipedia.org/wiki/Thompson_sampling

### Trading Concepts
- R-Multiple: Van Tharp's risk management
- Position sizing: Kelly Criterion, Fixed Fractional

### API Documentation
- Yahoo Finance: https://github.com/ranaroussi/yfinance
- FastAPI: https://fastapi.tiangolo.com/
- SQLAlchemy: https://docs.sqlalchemy.org/

---

## 📞 Support

For issues:
1. Check this documentation
2. Review error messages (they're designed to be helpful)
3. Check API logs
4. Review known limitations above

**Remember**: This is a complex system with external dependencies. Many issues are due to API rate limits or external service outages, not bugs in the code.

---

**Last Updated**: 2025-11-03
**Version**: 0.3.0
**Status**: Functional, production-ready with known limitations

