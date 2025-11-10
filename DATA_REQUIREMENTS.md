# Historical Data Requirements

## Current Implementation

### Data Fetching
- **Lookback Period**: 365 days (1 year) of daily OHLC data
- **Storage**: **NOT PERSISTED** - Data is fetched on-demand from market data providers
- **Providers**: Yahoo Finance (free), IEX Cloud (paid), Alpha Vantage (paid), Tiingo (paid)

### Where Data is Used
1. **Main Analysis** (`/decision/propose`): Fetches 365 days for:
   - Pattern detection
   - Evidence analysis (statistical tests)
   - Event study (CAR analysis)
   - Technical indicators (EMA, RSI, Bollinger Bands)
   - Sector relative strength

2. **Quick Analysis** (`/analyze/{ticker}`): Fetches 365 days for:
   - Volume surge calculation
   - Volatility metrics
   - Price position analysis

### Data Structure
Each daily record contains:
```python
{
    "date": "YYYY-MM-DD",
    "open": float,
    "high": float,
    "low": float,
    "close": float,
    "volume": int
}
```

## Recommendations

### Option 1: Add Caching Layer (Recommended)
- Cache fetched data in memory/Redis with TTL
- Reduces API calls to market data providers
- Improves response time for repeated ticker requests

### Option 2: Persistent Storage
- Store daily OHLC data in database (SQLite/PostgreSQL)
- Update daily via scheduled job
- Benefits:
  - Faster access (no API calls)
  - Historical backtesting
  - Offline analysis
  - Reduced rate limit issues

### Option 3: Hybrid Approach
- Cache recent data (last 30 days) in memory
- Store full year in database
- Update database daily via cron job

## Current Limitations

1. **No Persistence**: Data must be fetched every time
2. **Rate Limits**: Free providers (Yahoo Finance) have rate limits
3. **Network Dependency**: Requires internet connection
4. **No Historical Backtesting**: Can't analyze past events without re-fetching

## Implementation Notes

- Market data adapters support up to 5 years (IEX Cloud)
- Yahoo Finance supports up to 1 year reliably
- Alpha Vantage has daily API call limits
- Consider implementing data storage if:
  - You need offline analysis
  - You want to reduce API costs
  - You need historical backtesting
  - You're hitting rate limits frequently

