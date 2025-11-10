#!/usr/bin/env python3
"""
Quick verification that providers return adj_close
"""
from services.marketdata.service import MarketDataProviderService
import json

print("="*70)
print("VERIFYING ADJ_CLOSE IN PROVIDER DATA")
print("="*70)

md = MarketDataProviderService()

print(f"\nProvider chain: {[p.__class__.__name__ for p in md.providers]}")

# Test with NVDA
ticker = "NVDA"
print(f"\nFetching data for {ticker}...")

data = md.daily_ohlc(ticker, lookback=10)

if data:
    print(f"✅ Fetched {len(data)} bars")
    print(f"\nFirst bar:")
    print(json.dumps(data[0], indent=2))
    
    if 'adj_close' in data[0]:
        print("\n✅✅✅ SUCCESS: adj_close field is present!")
    else:
        print("\n❌ ERROR: adj_close field is MISSING!")
        print(f"Available fields: {list(data[0].keys())}")
else:
    print("❌ ERROR: No data returned!")

print("="*70)

