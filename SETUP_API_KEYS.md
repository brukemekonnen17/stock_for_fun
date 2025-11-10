# 🔑 API Key Setup Guide - Market Data Providers

## 🎯 Goal: Use yfinance ONLY as Last Resort

Your current setup uses **yfinance as primary** because the proper providers aren't configured. This guide fixes that.

---

## ⚠️ Current Problem

```
Provider Chain (Current):
1. Tiingo       ❌ Not configured (returns empty [])
2. Alpha Vantage ✅ Configured BUT hitting rate limits (25 calls/day free tier)
3. yfinance     ✅ Being used (unreliable, rate-limited)
```

**Result**: yfinance is being used because Alpha Vantage hits its daily limit quickly.

---

## ✅ Recommended Solution

### Option 1: Add Tiingo (RECOMMENDED) 🌟
**Best choice for production use**

#### Why Tiingo?
- ✅ **Reliable** (production-grade API)
- ✅ **Good limits**: 50 requests/day (free), 1000/day (basic $10/month)
- ✅ **Split-adjusted data** available
- ✅ **Real-time quotes** + historical data
- ✅ **Used by professionals**

#### How to Setup:
1. **Sign up** (free): https://api.tiingo.com/
2. **Get API key**: https://www.tiingo.com/account/api/token
3. **Add to `.env`**:
   ```bash
   TIINGO_API_KEY=your_key_here
   ```

4. **Implement Tiingo historical data** (currently returns empty):
   ```python
   # services/marketdata/tiingo_adapter.py
   # Line 109: Replace the empty daily_ohlc with actual implementation
   ```

#### Cost:
- **Free**: 50 requests/day, 500 unique symbols/month
- **Basic** ($10/month): 1,000 requests/day, 5,000 symbols/month
- **Premium** ($60/month): 20,000 requests/day, 50,000 symbols/month

**Recommendation**: Start with free tier, upgrade to Basic ($10/mo) if you run the notebook frequently.

---

### Option 2: Upgrade Alpha Vantage
**Cheaper but less reliable**

#### Current Status:
- ✅ Already configured
- ❌ Free tier: **25 calls/day** (gets exhausted quickly)
- ✅ Works, but falls back to yfinance after limit

#### How to Fix:
1. **Upgrade to Premium**: https://www.alphavantage.co/premium/
2. **Cost**: $29.99/month for 1,200 requests/day
3. **Keep existing key** in `.env` - just upgrade your account

#### Pros:
- Already set up
- Simple upgrade

#### Cons:
- More expensive than Tiingo Basic ($30 vs $10)
- Less reliable than Tiingo (based on user reviews)

---

### Option 3: Keep Current Setup (NOT RECOMMENDED)
**Free but unreliable**

If you don't want to pay:
- ✅ Alpha Vantage (25 calls/day)
- ✅ yfinance (fallback, rate-limited)

**Limitations**:
- Can only run notebook ~2-3 times per day (Alpha Vantage limit)
- Falls back to yfinance (429 errors common)
- Not suitable for production

---

## 🚀 Implementation Plan

### Immediate (Do This Now):
1. **Get Tiingo free API key** (5 minutes)
2. **Add to `.env`**:
   ```bash
   TIINGO_API_KEY=your_key_here_from_tiingo
   ALPHA_VANTAGE_API_KEY=your_existing_key
   ```

3. **Test the provider chain**:
   ```python
   from services.marketdata.service import MarketDataProviderService
   
   md = MarketDataProviderService()
   print(f"Providers: {[p.__class__.__name__ for p in md.providers]}")
   
   # Should show: ['TiingoAdapter', 'AlphaVantageAdapter', 'YFMarketData']
   ```

### Next (Implement Tiingo Historical):
Currently, Tiingo returns `[]` for historical data (lines 109-112 in `tiingo_adapter.py`). 

**To implement**:
1. Use Tiingo's EOD (End of Day) endpoint: 
   - API: `https://api.tiingo.com/tiingo/daily/{ticker}/prices`
   - Docs: https://api.tiingo.com/documentation/end-of-day
   
2. Update `daily_ohlc` method to fetch and format data

3. Add `adj_close` from response

**Would you like me to implement this?**

---

## 🎯 Final Provider Chain (After Setup)

```
1. Tiingo         ✅ Primary (50-1000 calls/day)
                     Reliable, production-grade
                     
2. Alpha Vantage  ✅ Secondary (25-1200 calls/day)
                     Backup if Tiingo fails
                     
3. yfinance       ✅ Last Resort (unreliable)
                     Only used if both above fail
```

---

## 📊 Cost Comparison

| Provider | Free Tier | Paid Tier | Reliability | Recommendation |
|----------|-----------|-----------|-------------|----------------|
| **Tiingo** | 50 calls/day | $10/mo (1000/day) | ⭐⭐⭐⭐⭐ | ✅ **BEST** |
| **Alpha Vantage** | 25 calls/day | $30/mo (1200/day) | ⭐⭐⭐ | Backup |
| **yfinance** | Unlimited* | Free | ⭐⭐ | Last resort |

\* *yfinance is "free" but has unpredictable rate limits (429 errors)*

---

## 🧪 Testing Your Setup

After adding API keys, test with this notebook cell:

```python
import logging
logging.basicConfig(level=logging.INFO)

from services.marketdata.service import MarketDataProviderService

# Initialize service
md = MarketDataProviderService()

# Check provider chain
print("="*70)
print("PROVIDER CHAIN STATUS")
print("="*70)
for i, p in enumerate(md.providers, 1):
    print(f"{i}. {p.__class__.__name__}")

# Test historical data fetch
print("\n" + "="*70)
print("TESTING HISTORICAL DATA FETCH")
print("="*70)

data = md.daily_ohlc("NVDA", lookback=365)
print(f"\nFetched {len(data)} bars")
print(f"Has adj_close: {'adj_close' in data[0] if data else 'N/A'}")
```

Expected output (after Tiingo setup):
```
======================================================================
PROVIDER CHAIN STATUS
======================================================================
1. TiingoAdapter
2. AlphaVantageAdapter  
3. YFMarketData

======================================================================
TESTING HISTORICAL DATA FETCH
======================================================================
Fetching historical data for NVDA (lookback=365d)
Provider chain: ['TiingoAdapter', 'AlphaVantageAdapter', 'YFMarketData']
Trying provider 1/3: TiingoAdapter
✅ Historical data fetched from TiingoAdapter (253 bars)

Fetched 253 bars
Has adj_close: True
```

---

## ❓ FAQ

### Q: Do I need both Tiingo and Alpha Vantage?
**A**: No, but it's recommended for redundancy. If Tiingo goes down or you hit limits, Alpha Vantage kicks in.

### Q: Can I use only the free tiers?
**A**: Yes! Tiingo free (50/day) + Alpha Vantage free (25/day) = 75 data fetches/day. Good for development.

### Q: When should I upgrade to paid tiers?
**A**: When you run the notebook > 3-4 times per day or need production reliability.

### Q: What if I don't want to pay anything?
**A**: Keep current setup (Alpha Vantage free + yfinance fallback). Just accept that:
- Only 2-3 notebook runs per day
- 429 errors when limits hit
- Not production-ready

---

## 🎯 Action Items

- [ ] Sign up for Tiingo (free): https://api.tiingo.com/
- [ ] Get Tiingo API key
- [ ] Add `TIINGO_API_KEY` to `.env`
- [ ] Test provider chain (run test cell above)
- [ ] **(Optional)** Upgrade Alpha Vantage to premium
- [ ] **(Next)** Implement Tiingo historical data endpoint

---

**Need help implementing Tiingo historical data? Let me know and I'll do it!** 🚀

