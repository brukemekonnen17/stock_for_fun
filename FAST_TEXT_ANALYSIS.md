# ⚡ Fast Text Analysis - Quick Stock Lookup

## 🎯 New Endpoint: `/quick/{ticker}`

Get instant text-based analysis without all the heavy processing.

### Usage

```bash
# Simple text response
curl http://127.0.0.1:8000/quick/AAPL
```

**Response**:
```json
{
  "ticker": "AAPL",
  "price": 192.50,
  "analysis": "📊 QUICK ANALYSIS: AAPL\n💰 Current Price: $192.50\n..."
}
```

### Benefits

- ✅ **Fast**: Uses cache, minimal processing
- ✅ **Simple**: Just price and basic info
- ✅ **Text-based**: Easy to read
- ✅ **No heavy calculations**: Skips RSI, ATR, full history

---

## 🚀 For Full Analysis

Use `/analyze/{ticker}` for complete trade recommendation with:
- Full market context (RSI, ATR)
- News analysis
- Trade plan
- Strategy rationale

But `/quick/{ticker}` is perfect for:
- Quick price checks
- Simple lookups
- Fast responses

---

## 📝 Try It Now

```bash
curl http://127.0.0.1:8000/quick/AAPL
curl http://127.0.0.1:8000/quick/TSLA
curl http://127.0.0.1:8000/quick/NVDA
```

**Should respond in < 1 second!** ⚡

