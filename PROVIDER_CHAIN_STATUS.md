# 🔗 Market Data Provider Chain - Split-Adjusted Data

## ✅ Provider Fallback Chain

The system uses a **3-tier fallback** for market data:

```
1. Tiingo (Primary) → If configured
2. Alpha Vantage (Secondary) → If configured  
3. yfinance (Fallback) → Always available
```

---

## 📊 Split-Adjusted Data Status

### 1. **Tiingo** (Primary)
- **Status**: ⚠️ **Historical data not implemented (MVP)**
- **Real-time quotes**: ✅ Works
- **Historical OHLC**: ❌ Returns empty `[]` (forces fallback)
- **adj_close**: N/A (not returning historical data)
- **Impact**: Falls through to Alpha Vantage or yfinance

**Code**:
```python
def daily_ohlc(self, ticker: str, lookback: int = 60) -> list:
    # MVP: Historical data falls back to yfinance
    return []  # Forces fallback
```

---

### 2. **Alpha Vantage** (Secondary)
- **Status**: ✅ **FIXED - Now includes adj_close**
- **Endpoint**: `TIME_SERIES_DAILY_ADJUSTED`
- **adj_close**: ✅ Field `"5. adjusted close"`
- **Rate Limits**: 
  - Free: 5 calls/min, 25 calls/day
  - Premium: 30 calls/min, 1200 calls/day

**Fixed Code**:
```python
def daily_ohlc(self, ticker: str, lookback: int = 60):
    data = self._get({
        "function": "TIME_SERIES_DAILY_ADJUSTED",  # ✅ Changed from TIME_SERIES_DAILY
        "symbol": ticker,
        "outputsize": "compact" if lookback <= 100 else "full"
    })
    
    for date_str in sorted_dates:
        day_data = series[date_str]
        out.append({
            "date": date_str,
            "open": float(day_data["1. open"]),
            "high": float(day_data["2. high"]),
            "low": float(day_data["3. low"]),
            "close": float(day_data["4. close"]),
            "adj_close": float(day_data["5. adjusted close"]),  # ✅ Added
            "volume": int(float(day_data["6. volume"])),
        })
```

---

### 3. **yfinance** (Fallback)
- **Status**: ✅ **FIXED - Now includes adj_close**
- **Source**: Yahoo Finance (free)
- **adj_close**: ✅ From `df["Adj Close"]`
- **Rate Limits**: Unpredictable (429 errors common)

**Fixed Code**:
```python
def daily_ohlc(self, ticker: str, lookback: int = 60):
    df = t.history(period=f"{lookback}d", interval="1d")
    
    for idx, row in df.iterrows():
        out.append({
            "date": idx.to_pydatetime().date().isoformat(),
            "open": float(row["Open"]),
            "high": float(row["High"]),
            "low": float(row["Low"]),
            "close": float(row["Close"]),
            "adj_close": float(row.get("Adj Close", row["Close"])),  # ✅ Added
            "volume": int(row["Volume"]) if not pd.isna(row["Volume"]) else 0,
        })
```

---

## 🎯 What This Means

### If You Have API Keys Configured:

#### **Scenario 1: Tiingo + Alpha Vantage configured**
```
Real-time quotes: Tiingo ✅
Historical data:  Alpha Vantage ✅ (with adj_close)
Fallback:         yfinance ✅
```

#### **Scenario 2: Only Alpha Vantage configured**
```
Real-time quotes: Alpha Vantage ✅
Historical data:  Alpha Vantage ✅ (with adj_close)
Fallback:         yfinance ✅
```

#### **Scenario 3: No API keys (default)**
```
Real-time quotes: yfinance ✅
Historical data:  yfinance ✅ (with adj_close)
Fallback:         None (yfinance is last resort)
```

---

## ✅ Testing Your Setup

### Check which provider is being used:

In your notebook, after running Cell 6 (Data Loading):

```python
print(f"Data source: {data_source}")
print(f"Has adj_close: {'adj_close' in df_clean.columns}")

# Check provider chain
from services.marketdata.service import MarketDataProviderService
md_service = MarketDataProviderService()
print(f"\nConfigured providers: {len(md_service.providers)}")
for i, p in enumerate(md_service.providers, 1):
    print(f"  {i}. {p.__class__.__name__}")
```

### Expected output (no API keys):
```
Data source: provider
Has adj_close: True

Configured providers: 1
  1. YFMarketData
```

### Expected output (with Alpha Vantage key):
```
Data source: provider
Has adj_close: True

Configured providers: 2
  1. AlphaVantageAdapter
  2. YFMarketData
```

---

## 📋 Recommendations

### For Production Use:

1. **Get Alpha Vantage API key** (free tier is fine for notebook use)
   - Sign up: https://www.alphavantage.co/support/#api-key
   - Add to `.env`: `ALPHA_VANTAGE_API_KEY=your_key_here`

2. **Optional: Get Tiingo key** (for real-time quotes)
   - Sign up: https://api.tiingo.com/
   - Add to `.env`: `TIINGO_API_KEY=your_key_here`
   - Note: Historical data still falls back to Alpha Vantage

3. **Keep yfinance as fallback** (always configured)
   - No API key needed
   - Unreliable but free
   - Good for development/testing

---

## ✅ Status Summary

| Provider | Real-time | Historical | adj_close | Status |
|----------|-----------|------------|-----------|--------|
| **Tiingo** | ✅ Works | ❌ MVP limitation | N/A | Falls through |
| **Alpha Vantage** | ✅ Works | ✅ **FIXED** | ✅ **FIXED** | Ready |
| **yfinance** | ✅ Works | ✅ **FIXED** | ✅ **FIXED** | Ready |

**All providers now return `adj_close` when they provide historical data!** ✅

---

## 🚀 Next Steps

1. ✅ Code fixed for all providers
2. 🔄 **Clear cache**: `rm -f cache/*.parquet`
3. 🔄 **Re-run Cell 6** in notebook
4. ✅ **Verify**: Cell 4 should show all green checkmarks

The notebook will now use **split-adjusted prices** regardless of which provider succeeds!

