# 🔍 Debug Dashboard - Why Analysis Not Showing

## ✅ What I Verified

1. **API Returns Analysis** - Confirmed via curl:
   ```json
   {
     "analysis": {
       "ticker": "AAPL",
       "catalyst": {...},
       "strategy": {...},
       "news": [...],
       "history": {...},
       "market": {...}
     }
   }
   ```

2. **Dashboard Code Has Analysis Rendering** - Line 477+ in `trading_dashboard.html`

## 🔍 Debug Steps

### **Step 1: Open Browser Console**

1. Open dashboard: `file:///Users/brukemekonnen/stock_investment/trading_dashboard.html`
2. Press **F12** (or Cmd+Option+I on Mac)
3. Go to **Console** tab
4. Look for:
   - `API Response:` - Should show full response
   - `Has analysis:` - Should say "YES"
   - `Displaying proposal, data.analysis:` - Should show analysis object
   - Any **red errors**

### **Step 2: Check Network Tab**

1. In browser DevTools, go to **Network** tab
2. Refresh page (Cmd+R)
3. Find request to `127.0.0.1:8000/propose`
4. Click it
5. Check **Response** tab
6. Look for `"analysis": {...}` in the JSON

### **Step 3: Test Direct API Call**

Run this in terminal:
```bash
curl -s -X POST http://127.0.0.1:8000/propose \
  -H "Content-Type: application/json" \
  -d '{
    "ticker":"AAPL",
    "price":192.50,
    "event_type":"EARNINGS",
    "days_to_event":7,
    "rank_components":{"immediacy":0.6},
    "expected_move":0.04,
    "backtest_kpis":{"hit_rate":0.54},
    "liquidity":5000000000,
    "spread":0.01,
    "context":[0.6,0.6,1.0,0.4,0.5,0.04,7]
  }' | python3 -m json.tool | grep -A 5 '"analysis"'
```

Should show:
```json
"analysis": {
    "ticker": "AAPL",
    "catalyst": {
        ...
```

---

## 🐛 Common Issues

### **Issue 1: CORS Error**
**Symptom:** Console shows "CORS policy" error  
**Fix:** API already has CORS enabled, should work

### **Issue 2: Analysis Field Missing**
**Symptom:** Console shows `Has analysis: NO`  
**Fix:** Check API is using updated code (restart if needed)

### **Issue 3: Template String Error**
**Symptom:** Console shows JavaScript error about template  
**Fix:** Check browser console for exact error

### **Issue 4: Old Cached Dashboard**
**Symptom:** Old HTML loaded  
**Fix:** Hard refresh (Cmd+Shift+R)

---

## 🔧 Quick Fixes

### **Fix 1: Hard Refresh Dashboard**
```bash
# In browser:
Cmd + Shift + R  (Mac)
Ctrl + Shift + R (Windows)
```

### **Fix 2: Restart API (Force Reload)**
```bash
pkill -f uvicorn
cd /Users/brukemekonnen/stock_investment
source .venv/bin/activate
export DB_URL='sqlite+pysqlite:///./catalyst.db'
export DEEPSEEK_API_URL='https://api.deepseek.com/v1/chat/completions'
export DEEPSEEK_API_KEY='sk-07b32570468e4bc58f29f06720c22e2b'
uvicorn apps.api.main:app --reload --host 0.0.0.0 --port 8000
```

### **Fix 3: Check Browser Console**

Open browser console and look for:
- ✅ `API Response: {...}` - Should include `analysis` field
- ✅ `Has analysis: YES` - Confirms analysis received
- ❌ Any red errors - These will tell you what's wrong

---

## 📊 What Should Show

When working correctly, you should see:

1. **Trade Proposal Card**
   - Ticker (AAPL)
   - Entry/Stop/Target prices
   - Confidence

2. **"Why Selected" Section** (This is what's missing!)
   - 📅 Catalyst Event card
   - 🎯 Strategy Rationale card
   - 📰 Recent News card
   - 📊 Market Context cards
   - 📈 Performance History (expandable)

3. **Approve/Reject Buttons**

---

## 🎯 Next Steps

1. **Open browser console** (F12)
2. **Refresh dashboard** (Cmd+R)
3. **Check console output:**
   - Does it say `Has analysis: YES`?
   - Any JavaScript errors?
4. **Share the console output** so I can fix the exact issue!

The API is definitely returning the analysis - the issue is in the dashboard rendering. The debug logs I added will help us find it! 🔍

