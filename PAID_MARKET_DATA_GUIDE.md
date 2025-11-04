# 💰 Paid Market Data Providers - Guide & Pricing

## 🎯 Why Consider Paid Providers?

**Current Situation**: Yahoo Finance (via `yfinance`) is free but has:
- ❌ Strict rate limits (429 errors)
- ❌ No official API support
- ❌ 15-20 minute data delays
- ❌ No Level 2 (order book) data
- ❌ Unreliable during high traffic

**Paid Providers Offer**:
- ✅ Official API support
- ✅ Higher rate limits (or unlimited)
- ✅ Real-time or near-real-time data
- ✅ Level 2 data (some providers)
- ✅ Better reliability
- ✅ Support & documentation

---

## 📊 Provider Comparison & Pricing

### 1. **IEX Cloud** ⭐ Recommended for Starters
**Best for**: Getting started, reasonable pricing

**Pricing**:
- **Free Tier**: 50,000 messages/month
- **Launch**: $9/month - 1M messages/month
- **Grow**: $29/month - 5M messages/month
- **Scale**: $99/month - 20M messages/month
- **Enterprise**: Custom pricing

**Features**:
- Real-time quotes
- Historical data
- Fundamentals
- News
- Options data

**API**: RESTful, well-documented
**Data Delay**: Real-time (paid), 15-min (free)

**Website**: https://iexcloud.io

---

### 2. **Alpha Vantage** 💰 Budget-Friendly
**Best for**: Cost-conscious users, simple needs

**Pricing**:
- **Free Tier**: 5 API calls/min, 500 calls/day
- **Premium**: $29.99/month - 30 calls/min, 1200 calls/day
- **Alpha Intelligence**: $49.99/month - AI-powered insights

**Features**:
- Real-time & historical quotes
- Technical indicators
- Fundamental data
- Forex, crypto support

**API**: RESTful, simple
**Data Delay**: Real-time (premium), 15-min (free)

**Website**: https://www.alphavantage.co

---

### 3. **Polygon.io** 🚀 Professional Grade
**Best for**: Serious traders, real-time needs

**Pricing**:
- **Starter**: $49/month - Real-time stocks, options, forex
- **Developer**: $99/month - + Level 2 data, websockets
- **Advanced**: $199/month - + Market data, advanced features
- **Enterprise**: Custom pricing

**Features**:
- Real-time quotes (WebSocket)
- Level 2 order book
- Historical data
- Options chains
- News & sentiment

**API**: REST + WebSocket
**Data Delay**: Real-time

**Website**: https://polygon.io

---

### 4. **Tiingo** 📈 Good Balance
**Best for**: Balanced features and pricing

**Pricing**:
- **Free Tier**: 500 calls/day
- **Starter**: $10/month - 2,000 calls/day
- **Professional**: $30/month - 10,000 calls/day
- **Enterprise**: Custom pricing

**Features**:
- Real-time quotes
- Historical data
- Fundamentals
- News
- IEX exchange data

**API**: RESTful
**Data Delay**: Real-time (paid), 15-min (free)

**Website**: https://api.tiingo.com

---

### 5. **Quandl/Nasdaq Data Link** 📊 Enterprise
**Best for**: Large-scale needs, diverse datasets

**Pricing**:
- **Free Tier**: Limited datasets
- **Basic**: $50/month - Basic market data
- **Premium**: Custom pricing - Premium datasets
- **Enterprise**: Custom pricing - Full access

**Features**:
- Extensive historical data
- Alternative data
- Economic indicators
- Multiple exchanges

**API**: RESTful
**Data Delay**: Varies by dataset

**Website**: https://data.nasdaq.com

---

## 💡 Recommendation Matrix

| Use Case | Best Provider | Cost/Month |
|----------|---------------|------------|
| **Getting Started** | IEX Cloud Launch | $9 |
| **Budget-Conscious** | Alpha Vantage Premium | $29.99 |
| **Real-Time Trading** | Polygon.io Starter | $49 |
| **Balanced** | Tiingo Professional | $30 |
| **Enterprise** | Polygon.io Advanced | $199+ |

---

## 🔧 Implementation Guide

### Quick Integration Pattern

All providers follow the same pattern since we use the `MarketData` protocol:

```python
# services/marketdata/base.py defines the interface:
class MarketData(Protocol):
    def last_quote(self, ticker: str) -> dict: ...
    def daily_ohlc(self, ticker: str, lookback: int = 60): ...
    def spread_proxy(self, ticker: str) -> float: ...
```

### Example: IEX Cloud Adapter

**File**: `services/marketdata/iex_adapter.py`

```python
import requests
from datetime import datetime
from typing import List, Dict
from services.marketdata.base import MarketData
import os

class IEXCloudAdapter(MarketData):
    def __init__(self):
        self.api_key = os.getenv("IEX_CLOUD_API_KEY")
        self.base_url = "https://cloud.iexapis.com/stable"
        if not self.api_key:
            raise ValueError("IEX_CLOUD_API_KEY environment variable required")
    
    def last_quote(self, ticker: str) -> dict:
        """Get real-time quote from IEX Cloud"""
        url = f"{self.base_url}/stock/{ticker}/quote"
        params = {"token": self.api_key}
        
        response = requests.get(url, params=params, timeout=10)
        response.raise_for_status()
        data = response.json()
        
        return {
            "price": float(data["latestPrice"]),
            "bid": float(data.get("iexBidPrice", data["latestPrice"])),
            "ask": float(data.get("iexAskPrice", data["latestPrice"])),
            "timestamp": datetime.utcnow().isoformat(),
        }
    
    def daily_ohlc(self, ticker: str, lookback: int = 60) -> List[Dict]:
        """Get historical OHLC data"""
        url = f"{self.base_url}/stock/{ticker}/chart/{lookback}d"
        params = {"token": self.api_key}
        
        response = requests.get(url, params=params, timeout=10)
        response.raise_for_status()
        data = response.json()
        
        return [
            {
                "date": item["date"],
                "open": float(item["open"]),
                "high": float(item["high"]),
                "low": float(item["low"]),
                "close": float(item["close"]),
                "volume": int(item["volume"]),
            }
            for item in data
        ]
    
    def spread_proxy(self, ticker: str) -> float:
        """Get actual spread from IEX"""
        quote = self.last_quote(ticker)
        spread = quote["ask"] - quote["bid"]
        return max(0.01, spread)  # Minimum 1 cent
```

### Example: Alpha Vantage Adapter

**File**: `services/marketdata/alphavantage_adapter.py`

```python
import requests
from datetime import datetime
from typing import List, Dict
from services.marketdata.base import MarketData
import os

class AlphaVantageAdapter(MarketData):
    def __init__(self):
        self.api_key = os.getenv("ALPHAVANTAGE_API_KEY")
        self.base_url = "https://www.alphavantage.co/query"
        if not self.api_key:
            raise ValueError("ALPHAVANTAGE_API_KEY environment variable required")
    
    def last_quote(self, ticker: str) -> dict:
        """Get real-time quote"""
        params = {
            "function": "GLOBAL_QUOTE",
            "symbol": ticker,
            "apikey": self.api_key
        }
        
        response = requests.get(self.base_url, params=params, timeout=10)
        response.raise_for_status()
        data = response.json()["Global Quote"]
        
        return {
            "price": float(data["05. price"]),
            "bid": float(data.get("09. change", data["05. price"])),
            "ask": float(data.get("05. price", data["05. price"])),
            "timestamp": datetime.utcnow().isoformat(),
        }
    
    def daily_ohlc(self, ticker: str, lookback: int = 60) -> List[Dict]:
        """Get historical data"""
        params = {
            "function": "TIME_SERIES_DAILY",
            "symbol": ticker,
            "apikey": self.api_key,
            "outputsize": "compact" if lookback <= 100 else "full"
        }
        
        response = requests.get(self.base_url, params=params, timeout=10)
        response.raise_for_status()
        data = response.json()["Time Series (Daily)"]
        
        results = []
        for date, values in list(data.items())[:lookback]:
            results.append({
                "date": date,
                "open": float(values["1. open"]),
                "high": float(values["2. high"]),
                "low": float(values["3. low"]),
                "close": float(values["4. close"]),
                "volume": int(values["5. volume"]),
            })
        
        return sorted(results, key=lambda x: x["date"])
    
    def spread_proxy(self, ticker: str) -> float:
        """Estimate spread (Alpha Vantage doesn't provide bid/ask)"""
        quote = self.last_quote(ticker)
        # Estimate 0.1% spread
        return max(0.01, quote["price"] * 0.001)
```

### Switching Providers

**In `apps/api/main.py`** (around line 92-94):

```python
# Current (Yahoo Finance):
from services.marketdata.yf_adapter import YFMarketData
market_data = YFMarketData()

# Switch to IEX Cloud:
from services.marketdata.iex_adapter import IEXCloudAdapter
market_data = IEXCloudAdapter()

# Or Alpha Vantage:
from services.marketdata.alphavantage_adapter import AlphaVantageAdapter
market_data = AlphaVantageAdapter()
```

### Environment Variables

Add to `.env`:
```bash
# IEX Cloud
IEX_CLOUD_API_KEY=your_key_here

# OR Alpha Vantage
ALPHAVANTAGE_API_KEY=your_key_here

# OR Polygon.io
POLYGON_API_KEY=your_key_here
```

---

## 🚀 Quick Start: IEX Cloud (Recommended)

### Step 1: Sign Up
1. Go to https://iexcloud.io
2. Sign up for free account (50K messages/month)
3. Get your API key from dashboard

### Step 2: Install Dependencies
```bash
pip install requests
```

### Step 3: Create Adapter
Create `services/marketdata/iex_adapter.py` (see code above)

### Step 4: Update Environment
```bash
export IEX_CLOUD_API_KEY=pk_your_key_here
```

### Step 5: Switch in Code
Update `apps/api/main.py` line 94:
```python
from services.marketdata.iex_adapter import IEXCloudAdapter
market_data = IEXCloudAdapter()
```

### Step 6: Test
```bash
curl http://127.0.0.1:8000/analyze/AAPL
```

---

## 💰 Cost Analysis

### Current Usage Estimate
Assuming you analyze:
- 10 stocks/day
- 30 days/month
- = 300 API calls/month

### Provider Costs for 300 calls/month:

| Provider | Plan | Cost/Month | Calls/Month | Cost per Call |
|----------|------|------------|-------------|---------------|
| **IEX Cloud** | Free | $0 | 50,000 | Free |
| **IEX Cloud** | Launch | $9 | 1,000,000 | $0.000009 |
| **Alpha Vantage** | Premium | $29.99 | ~36,000 | $0.00083 |
| **Polygon.io** | Starter | $49 | Unlimited | Fixed |
| **Tiingo** | Starter | $10 | ~60,000 | $0.00017 |

**Recommendation**: Start with **IEX Cloud Free** (50K/month is plenty), upgrade to Launch ($9/month) if needed.

---

## 🔄 Fallback Strategy

You can implement a **fallback chain**:

```python
# apps/api/main.py
from services.marketdata.iex_adapter import IEXCloudAdapter
from services.marketdata.yf_adapter import YFMarketData

class FallbackMarketData:
    def __init__(self):
        self.primary = IEXCloudAdapter()
        self.fallback = YFMarketData()
    
    def last_quote(self, ticker: str) -> dict:
        try:
            return self.primary.last_quote(ticker)
        except Exception as e:
            logger.warning(f"Primary provider failed, using fallback: {e}")
            return self.fallback.last_quote(ticker)
    
    # Similar for daily_ohlc and spread_proxy

market_data = FallbackMarketData()
```

This way:
- ✅ Primary: Fast, reliable paid provider
- ✅ Fallback: Free Yahoo Finance if primary fails
- ✅ Best of both worlds!

---

## 📝 Next Steps

1. **Choose Provider**: I recommend **IEX Cloud** (free tier is generous)
2. **Sign Up**: Get API key
3. **Create Adapter**: Use code examples above
4. **Update Code**: Switch in `apps/api/main.py`
5. **Test**: Verify it works
6. **Optional**: Add fallback to Yahoo Finance

---

## 🆘 Need Help?

- **IEX Cloud Docs**: https://iexcloud.io/docs/
- **Alpha Vantage Docs**: https://www.alphavantage.co/documentation/
- **Polygon.io Docs**: https://polygon.io/docs/

---

**Recommendation**: Start with **IEX Cloud Free** ($0) - it gives you 50,000 calls/month which is more than enough for testing. If you need more, upgrade to Launch ($9/month) for 1M calls.

