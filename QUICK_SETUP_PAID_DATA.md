# 🚀 Quick Setup: Paid Market Data (IEX Cloud)

## ✅ Recommended: IEX Cloud

**Why**: 
- ✅ Free tier: 50,000 calls/month (more than enough!)
- ✅ $9/month if you need more (1M calls)
- ✅ Real-time data
- ✅ Official API (no rate limit issues)
- ✅ Reliable

---

## 📝 5-Minute Setup

### Step 1: Sign Up (Free)
1. Go to https://iexcloud.io
2. Click "Sign Up"
3. Create free account
4. Go to Dashboard → API Keys
5. Copy your **publishable token** (starts with `pk_`)

### Step 2: Add API Key
```bash
# In your .env file or export:
export IEX_CLOUD_API_KEY=pk_your_key_here
```

### Step 3: Install Requests (if not already)
```bash
pip install requests
```

### Step 4: Update Code

**File**: `apps/api/main.py` (around line 92-94)

**Change from**:
```python
from services.marketdata.yf_adapter import YFMarketData
market_data = YFMarketData()
```

**Change to**:
```python
from services.marketdata.iex_adapter import IEXCloudAdapter

try:
    market_data = IEXCloudAdapter()
    logger.info("✅ Using IEX Cloud for market data")
except ValueError as e:
    logger.warning(f"⚠️ IEX Cloud not configured, falling back to Yahoo Finance: {e}")
    from services.marketdata.yf_adapter import YFMarketData
    market_data = YFMarketData()
```

### Step 5: Restart API
```bash
# Stop current API (Ctrl+C)
# Restart:
uvicorn apps.api.main:app --reload --host 0.0.0.0 --port 8000
```

### Step 6: Test
```bash
curl http://127.0.0.1:8000/analyze/AAPL
```

**Should work instantly without rate limits!** ✅

---

## 💰 Pricing

### Free Tier (Recommended to Start)
- **Cost**: $0/month
- **Calls**: 50,000/month
- **Data**: Real-time (IEX exchange)
- **Perfect for**: Testing, development, light usage

**Example**: If you analyze 10 stocks/day × 30 days = 300 calls/month (well within limit!)

### Paid Tier (If Needed)
- **Cost**: $9/month
- **Calls**: 1,000,000/month
- **Data**: Real-time + additional features
- **When to upgrade**: If you exceed 50K calls/month

---

## 🔄 Fallback Option

The code above automatically falls back to Yahoo Finance if IEX Cloud isn't configured. This means:
- ✅ If you have IEX key → Uses IEX (fast, reliable)
- ✅ If no key → Uses Yahoo Finance (free, but rate limited)

**Best of both worlds!**

---

## 🧪 Verify It's Working

Check API logs when you start:
```
✅ Using IEX Cloud for market data
```

If you see:
```
⚠️ IEX Cloud not configured, falling back to Yahoo Finance
```

Then check your `IEX_CLOUD_API_KEY` environment variable.

---

## 📊 Other Providers (If You Prefer)

### Alpha Vantage ($29.99/month)
- Change import to: `from services.marketdata.alphavantage_adapter import AlphaVantageAdapter`
- Set: `ALPHAVANTAGE_API_KEY`

### Polygon.io ($49/month)
- More features, WebSocket support
- Better for high-frequency trading

See `PAID_MARKET_DATA_GUIDE.md` for full comparison.

---

## 🎯 Recommendation

**Start with IEX Cloud Free** ($0):
- No credit card needed
- 50K calls/month is plenty
- Upgrade later if needed ($9/month)

**You'll immediately notice**:
- ✅ No more rate limit errors
- ✅ Faster responses
- ✅ Real-time data
- ✅ More reliable

---

**That's it!** You should now have reliable market data without rate limits. 🚀

