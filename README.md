# 🎯 Catalyst Radar - Enterprise Trading Analytics System

A sophisticated AI-powered trading system featuring real-time market analysis, contextual bandit learning, and enterprise-level analytics dashboard.

## 🚀 Features

### Core Capabilities
- **AI-Powered Trade Analysis**: Claude 3 Haiku integration for intelligent trade recommendations
- **Contextual Bandit Learning**: Thompson Sampling algorithm for strategy optimization
- **Real-Time Market Data**: Multi-provider integration (Tiingo, Alpha Vantage, yfinance)
- **Earnings Calendar**: Multi-source earnings event tracking with fallback chain
- **Social Sentiment**: StockTwits integration for momentum trading signals
- **Policy Validation**: 7-point risk guardrail system for trade safety
- **Enterprise Dashboard**: FT-style analytical interface with advanced visualizations

### Technical Stack
- **Backend**: FastAPI (Python 3.10+)
- **Frontend**: Enterprise HTML5 dashboard with Chart.js
- **Database**: SQLite (production-ready for PostgreSQL)
- **LLM**: Anthropic Claude 3 Haiku
- **Market Data**: Tiingo → Alpha Vantage → yfinance fallback chain
- **Broker Integration**: E*TRADE OAuth1 API

## 📋 Quick Start

### Prerequisites
```bash
python 3.10+
pip install -r requirements.txt
```

### Environment Setup
1. Copy `.env.etrade.example` to `.env`
2. Add your API keys:
   ```env
   ANTHROPIC_API_KEY=your_claude_key
   TIINGO_API_KEY=your_tiingo_key (optional)
   ALPHA_VANTAGE_API_KEY=your_av_key (optional)
   FMP_API_KEY=your_fmp_key (optional)
   ```

### Start the System
```bash
# Start API server
uvicorn apps.api.main:app --host 0.0.0.0 --port 8000

# Access dashboard
open http://localhost:8000
```

## 📊 Dashboard Features

### Enterprise Analytics Panels
- **Decision Bar**: Verdict, confidence meter, current price
- **Trade Execution Plan**: Entry/Stop/Target prices with risk parameters
- **Technical Pattern Analysis**: 10-day price position, breakout detection
- **Volume & Participation**: Surge ratio analysis, liquidity metrics
- **Catalyst Timeline**: Event countdown, expected move, materiality
- **Market Context**: RSI(14), ATR(14), spread, volatility indicators
- **Social Sentiment**: StockTwits mentions and sentiment scoring
- **Performance History**: Backtest statistics (hit rate, win/loss)
- **AI Reasoning**: LLM-generated trade thesis
- **News Feed**: Recent headlines with sentiment analysis

## 🏗️ Architecture

```
┌─────────────────────────────────────────────────┐
│  Enterprise Dashboard (FT-Style)                 │
│  - Real-time analytics                          │
│  - Advanced visualizations                      │
└──────────────┬──────────────────────────────────┘
               │
┌──────────────▼──────────────────────────────────┐
│  FastAPI Backend                                │
│  ├─ Market Data Service (Tiingo/AV/yfinance)    │
│  ├─ Earnings Calendar (FMP/AV/yfinance)         │
│  ├─ Social Sentiment (StockTwits)               │
│  ├─ LLM Integration (Claude 3 Haiku)             │
│  ├─ Contextual Bandit (Thompson Sampling)       │
│  └─ Policy Validators (Risk Guardrails)         │
└──────────────┬──────────────────────────────────┘
               │
┌──────────────▼──────────────────────────────────┐
│  Data Sources                                   │
│  - Market Data APIs                             │
│  - Earnings Calendars                           │
│  - Social Media APIs                            │
│  - News APIs                                    │
└─────────────────────────────────────────────────┘
```

## 📡 API Endpoints

### Core Endpoints
- `GET /health` - Health check
- `GET /analyze/{ticker}` - Full stock analysis with trade plan
- `GET /scan` - Scan for catalyst opportunities
- `POST /decision/propose` - Propose trade with context
- `POST /decision/validate` - Validate trade against policy
- `POST /bandit/reward` - Log reward for learning

See [API_REFERENCE.md](API_REFERENCE.md) for complete documentation.

## 🔐 Security

- All API keys stored in `.env` (not committed)
- Policy guardrails prevent reckless trades
- Idempotent reward logging
- Rate limiting on external APIs

## 📈 Performance

- **Market Data**: Fallback chain ensures 99%+ uptime
- **LLM Response**: <2s average with Claude 3 Haiku
- **Dashboard Load**: <500ms for full analysis
- **Bandit Learning**: Real-time strategy optimization

## 🧪 Testing

```bash
# Run system verification
python verify_system.py

# Run API tests
pytest tests/test_api.py

# Run bandit tests
pytest tests/test_bandit.py
```

## 📚 Documentation

- [API Reference](API_REFERENCE.md)
- [System Overview](SYSTEM_OVERVIEW.md)
- [Technical Documentation](TECHNICAL_DOCUMENTATION.md)
- [E*TRADE Integration](ETRADE_INTEGRATION.md)
- [Quick Start Guide](QUICKSTART.md)

## 🛠️ Development

### Project Structure
```
stock_investment/
├── apps/api/          # FastAPI backend
├── services/          # Core services
│   ├── marketdata/    # Market data providers
│   ├── calendar/      # Earnings calendar
│   ├── social/        # Social sentiment
│   ├── llm/           # LLM integration
│   └── policy/        # Risk validators
├── libs/analytics/    # Bandit learning
├── db/                # Database models
├── tests/             # Test suite
└── trading_dashboard.html  # Enterprise dashboard
```

## 📝 License

This project is proprietary software. All rights reserved.

## 🤝 Contributing

This is a private enterprise system. For questions or support, contact the development team.

## 📧 Support

For issues or questions:
1. Check the documentation in `/docs`
2. Review [SYSTEM_STATUS.md](COMPLETE_SYSTEM_STATUS.md)
3. Run `python verify_system.py` for diagnostics

---

**Built with ❤️ for enterprise trading analytics**
