#!/usr/bin/env python3
"""
System Verification Script
Checks for import errors, missing dependencies, and integration issues
"""
import sys
import traceback

def test_import(module_name, description):
    """Test if a module can be imported"""
    try:
        __import__(module_name)
        print(f"✅ {description}: OK")
        return True
    except ImportError as e:
        print(f"❌ {description}: FAILED - {e}")
        return False
    except Exception as e:
        print(f"⚠️  {description}: ERROR - {e}")
        traceback.print_exc()
        return False

def test_function_import(module_path, function_name, description):
    """Test if a function can be imported from a module"""
    try:
        module = __import__(module_path, fromlist=[function_name])
        func = getattr(module, function_name)
        print(f"✅ {description}: OK")
        return True
    except ImportError as e:
        print(f"❌ {description}: FAILED - {e}")
        return False
    except AttributeError as e:
        print(f"❌ {description}: FAILED - Function not found - {e}")
        return False
    except Exception as e:
        print(f"⚠️  {description}: ERROR - {e}")
        traceback.print_exc()
        return False

def main():
    print("=" * 60)
    print("SYSTEM VERIFICATION")
    print("=" * 60)
    print()
    
    results = []
    
    # Core dependencies
    print("📦 Core Dependencies:")
    print("-" * 60)
    results.append(test_import("fastapi", "FastAPI"))
    results.append(test_import("sqlalchemy", "SQLAlchemy"))
    results.append(test_import("pydantic", "Pydantic"))
    results.append(test_import("numpy", "NumPy"))
    results.append(test_import("httpx", "HTTPX"))
    print()
    
    # Market data dependencies
    print("📊 Market Data Dependencies:")
    print("-" * 60)
    results.append(test_import("yfinance", "yfinance"))
    results.append(test_import("requests", "requests"))
    print()
    
    # Social dependencies
    print("📱 Social Sentiment Dependencies:")
    print("-" * 60)
    results.append(test_import("requests", "requests (for StockTwits)"))
    print()
    
    # Service modules
    print("🔧 Service Modules:")
    print("-" * 60)
    results.append(test_function_import("services.social.sentiment_scanner", "get_real_time_sentiment", "Social sentiment scanner"))
    results.append(test_function_import("services.social.stocktwits_adapter", "fetch_recent_messages", "StockTwits adapter"))
    results.append(test_function_import("services.marketdata.service", "MarketDataProviderService", "Market data service"))
    results.append(test_function_import("services.marketdata.tiingo_adapter", "TiingoAdapter", "Tiingo adapter"))
    results.append(test_function_import("services.calendar.service", "EarningsCalendarService", "Earnings calendar service"))
    results.append(test_function_import("services.analysis.events", "get_event_details", "Event details helper"))
    print()
    
    # Database models
    print("💾 Database Models:")
    print("-" * 60)
    results.append(test_import("db.models", "Database models"))
    results.append(test_import("db.session", "Database session"))
    print()
    
    # API components
    print("🌐 API Components:")
    print("-" * 60)
    try:
        # Test if we can at least import the main module (even if dependencies are missing)
        sys.path.insert(0, '.')
        from apps.api import main
        print("✅ Main API module: OK")
        results.append(True)
    except Exception as e:
        print(f"⚠️  Main API module: ERROR - {e}")
        print("   (This is expected if dependencies are missing)")
        print("   Run: pip install -r requirements.txt")
        results.append(False)
    print()
    
    # Summary
    print("=" * 60)
    passed = sum(results)
    total = len(results)
    print(f"SUMMARY: {passed}/{total} checks passed")
    print("=" * 60)
    
    if passed == total:
        print("✅ All checks passed! System is ready.")
        return 0
    else:
        print("⚠️  Some checks failed. Review errors above.")
        print("💡 Install missing dependencies: pip install -r requirements.txt")
        return 1

if __name__ == "__main__":
    sys.exit(main())

