# 🚨 Yahoo Finance Rate Limiting - Guide

## ⚠️ **Current Issue:**

Yahoo Finance's free API has rate limits. When you make too many requests quickly, they temporarily block requests with a "429 Too Many Requests" error.

## ✅ **What I've Added:**

1. **Automatic Retries** - The system now automatically retries 3 times with exponential backoff:
   - Attempt 1: Immediate
   - Attempt 2: Wait 3 seconds
   - Attempt 3: Wait 6 seconds
   - Attempt 4: Wait 12 seconds (if needed)
2. **Better Error Messages** - Clear explanations when rate limits happen
3. **Caching** - Prices are cached for 5 minutes (300 seconds TTL) to reduce API calls

## 🎯 **What You Should Do:**

### **Option 1: Wait and Retry**
- Wait **1-2 minutes** between stock analyses
- The system will automatically retry if you get rate limited
- Try analyzing the same ticker again after waiting

### **Option 2: Try Different Tickers**
- If one ticker fails, try another
- Some popular tickers that usually work:
  - **AAPL** (Apple)
  - **MSFT** (Microsoft)
  - **GOOGL** (Alphabet)
  - **AMZN** (Amazon)
  - **META** (Meta Platforms)

### **Option 3: Use Cached Results**
- If you analyzed a stock recently, the price might be cached
- Try the same ticker again - it should be faster if cached

## 🔧 **Technical Details:**

The system now:
- ✅ Detects rate limit errors (429)
- ✅ Waits 3s, 6s, then 12s between retries
- ✅ Provides clear error messages
- ✅ Caches successful results for 5 minutes

## 💡 **Best Practices:**

1. **Don't spam requests** - Wait 30-60 seconds between analyses
2. **Use the cache** - Re-analyze the same ticker if you want updated analysis
3. **Be patient** - If you get rate limited, wait 1-2 minutes

## 🐛 **If It Still Fails:**

If you're still getting errors after waiting:
1. Check if Yahoo Finance is down: https://finance.yahoo.com
2. Try a well-known ticker like AAPL
3. Wait 5 minutes and try again

The code is working correctly - this is a Yahoo Finance API limitation. The retries and caching should help, but we're at the mercy of Yahoo Finance's rate limits.

---

**Remember: Wait between analyses and you should be fine!** ⏰

