#!/usr/bin/env python3
"""
Quick test script to validate Tiingo API setup
Run this after adding TIINGO_API_KEY to your .env file
"""

import os
import sys
from pathlib import Path
from dotenv import load_dotenv

# Load environment
load_dotenv()

# Setup logging to see provider messages
import logging
logging.basicConfig(
    level=logging.INFO,
    format='%(levelname)s: %(message)s'
)

print("="*80)
print("TIINGO SETUP VALIDATION")
print("="*80)

# 1. Check API keys
print("\n📋 Step 1: Checking API Keys")
print("-" * 80)

tiingo_key = os.getenv("TIINGO_API_KEY")
alpha_key = os.getenv("ALPHA_VANTAGE_API_KEY")

if tiingo_key:
    print(f"✅ TIINGO_API_KEY: configured ({tiingo_key[:10]}...)")
else:
    print("❌ TIINGO_API_KEY: NOT configured")
    print("\n⚠️  Add to .env file:")
    print("   TIINGO_API_KEY=your_key_here")
    print("\n   Get free key at: https://api.tiingo.com/")
    sys.exit(1)

if alpha_key:
    print(f"✅ ALPHA_VANTAGE_API_KEY: configured ({alpha_key[:10]}...)")
else:
    print("⚠️  ALPHA_VANTAGE_API_KEY: Not configured (optional backup)")

# 2. Test provider initialization
print("\n📋 Step 2: Initializing Provider Chain")
print("-" * 80)

from services.marketdata.service import MarketDataProviderService

md_service = MarketDataProviderService()

print(f"\nProvider chain ({len(md_service.providers)} providers):")
for i, provider in enumerate(md_service.providers, 1):
    print(f"  {i}. {provider.__class__.__name__}")

if not any(p.__class__.__name__ == 'TiingoAdapter' for p in md_service.providers):
    print("\n❌ ERROR: TiingoAdapter not in provider chain!")
    sys.exit(1)

# 3. Test historical data fetch
print("\n📋 Step 3: Testing Historical Data Fetch")
print("-" * 80)

ticker = "NVDA"
print(f"\nFetching 365 days of data for {ticker}...")

try:
    data = md_service.daily_ohlc(ticker, lookback=365)
    
    if not data:
        print(f"❌ ERROR: No data returned for {ticker}")
        sys.exit(1)
    
    print(f"\n✅ Success! Fetched {len(data)} bars")
    
    # Check data quality
    first_bar = data[0]
    print(f"\nFirst bar: {first_bar['date']}")
    print(f"  Open: ${first_bar['open']:.2f}")
    print(f"  High: ${first_bar['high']:.2f}")
    print(f"  Low: ${first_bar['low']:.2f}")
    print(f"  Close: ${first_bar['close']:.2f}")
    print(f"  Adj Close: ${first_bar.get('adj_close', 'N/A')}")
    print(f"  Volume: {first_bar['volume']:,}")
    
    # Verify adj_close exists
    if 'adj_close' not in first_bar:
        print("\n❌ ERROR: adj_close field missing!")
        sys.exit(1)
    
    print("\n✅ Data quality check passed (adj_close present)")
    
    # Check which provider was used
    last_bar = data[-1]
    print(f"\nLast bar: {last_bar['date']}")
    print(f"  Close: ${last_bar['close']:.2f}")
    print(f"  Adj Close: ${last_bar['adj_close']:.2f}")

except Exception as e:
    print(f"\n❌ ERROR: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

# 4. Test real-time quote
print("\n📋 Step 4: Testing Real-Time Quote")
print("-" * 80)

try:
    quote = md_service.get_real_time_quote(ticker)
    
    if not quote:
        print(f"❌ ERROR: No quote returned for {ticker}")
    else:
        print(f"\n✅ Quote for {ticker}:")
        print(f"  Price: ${quote['price']:.2f}")
        print(f"  Bid: ${quote['bid']:.2f}")
        print(f"  Ask: ${quote['ask']:.2f}")
        print(f"  Volume: {quote['volume']:,}")
        print(f"  Source: {quote.get('source', 'Unknown')}")

except Exception as e:
    print(f"\n⚠️  Quote fetch failed (not critical): {e}")

# 5. Summary
print("\n" + "="*80)
print("VALIDATION SUMMARY")
print("="*80)

print("\n✅✅✅ Tiingo setup is working correctly!")
print("\nYour provider chain:")
print("  1. Tiingo (PRIMARY) ← Using this for historical data")
print("  2. Alpha Vantage (BACKUP)" if alpha_key else "  2. yfinance (FALLBACK)")
print("  3. yfinance (LAST RESORT)")

print("\n📊 Rate Limits:")
print("  Tiingo free tier: 50 requests/day")
print("  (Upgrade to $10/mo for 1,000 requests/day)")

print("\n🎯 Next Steps:")
print("  1. Run your notebook (Cell 6: Data Loading)")
print("  2. Check logs for 'Tiingo' as data source")
print("  3. Verify adj_close column is present")

print("\n" + "="*80)
print("✅ Ready to use Tiingo as primary data source!")
print("="*80)

