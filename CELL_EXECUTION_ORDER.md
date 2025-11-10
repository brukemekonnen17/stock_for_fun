# 📋 Cell Execution Order Guide

## ⚠️ Important: Correct Cell Execution Sequence

The notebook has **validation cells** that must run AFTER data loading. Here's the correct order:

---

## ✅ Correct Execution Order

### Step 1: Configuration (Cells 1-3)
```
Cell 1: Header (markdown)
Cell 2: Config & Inputs  → Run this first (defines TICKER, WINDOW_DAYS, etc.)
Cell 3: Section header (markdown)
```

### Step 2: Data Loading (Cell 6)
```
Cell 6: Data Loading & Hygiene  → Run this SECOND (loads df_clean, data_source)
```
**Creates**: `df_clean`, `data_source`, `raw_df`

### Step 3: Data Validation (Cell 4)
```
Cell 4: DATA INTEGRITY CHECK  → Run this THIRD (validates real data)
```
**Requires**: `df_clean`, `data_source` from Cell 6

**Note**: Cell 4 appears before Cell 6 in the notebook, but should be **executed after** Cell 6.

---

## 🔧 Current Issue & Fix

### Problem
You're seeing:
```
❌ WARNING: Some critical data checks failed
Failed checks: price_data_loaded, adj_close_available, real_data_source, ...
```

### Root Cause
Cell 4 (Data Integrity Check) was executed **before** Cell 6 (Data Loading).

### Solution Options

**Option A: Re-run in Correct Order**
1. Click Cell 2 → Run (Config)
2. Click Cell 6 → Run (Data Loading)
3. Click Cell 4 → Run (Data Integrity Check)

**Option B: Run All in Sequence**
```
Kernel → Restart & Run All
```
This will run cells in order, but Cell 4 will still fail. After completion, manually re-run Cell 4.

**Option C: Move Cell 4 After Cell 6** (Recommended)
- Cut Cell 4 (Edit → Cut Cells)
- Click after Cell 6
- Paste (Edit → Paste Cells Below)
- Now "Run All" will work correctly

---

## ✅ Expected Output (When Run Correctly)

After running Cell 6, then Cell 4:

```
======================================================================
DATA INTEGRITY VALIDATION - Ensuring No Placeholder Data
======================================================================
✅ Data found - proceeding with validation...

✅ Critical Data Validation (Must be Real):
   ✅ Price data loaded: True
   ✅ Split-adjusted prices: True
   ✅ Real data source (not mock): True
   ✅ Adequate history (≥200 days): True
   ✅ Volume data for ADV: True
   ✅ High/Low for spread proxy: True

📋 Optional Data (Not Required for Core Analysis):
   ℹ️  Implied Volatility: Not fetched (future enhancement)
   ℹ️  Sector RS: Will use simple mapping (optional)
   ℹ️  Transaction costs: Using industry-standard defaults (configurable)

✅✅✅ ALL CRITICAL DATA IS REAL - NO PLACEHOLDERS ✅✅✅
======================================================================
```

---

## 🚀 Quick Fix Commands

### If you see "data_source not defined" error:
1. **Don't panic** - it just means data hasn't been loaded yet
2. **Run Cell 6 first** (Data Loading)
3. **Then run Cell 4** (Data Integrity Check)

### To verify current state:
```python
# Run this in a new cell to check what's loaded:
print("df_clean exists:", 'df_clean' in globals())
print("data_source exists:", 'data_source' in globals())
if 'df_clean' in globals():
    print(f"df_clean has {len(df_clean)} rows")
```

---

## 📝 Cell Dependencies Summary

```
Cell 2 (Config)
    ↓ provides TICKER, WINDOW_DAYS
Cell 6 (Data Loading)
    ↓ provides df_clean, data_source
Cell 4 (Data Integrity) ← Run AFTER Cell 6
Cell 7 (Feature Engineering) ← Run AFTER Cell 6
Cell 8+ (Analysis) ← Run AFTER Cell 7
```

---

## ✅ After Running Cell 4 Successfully

You should see:
- ✅ All critical checks passing
- ✅ "ALL CRITICAL DATA IS REAL" message
- ✅ No errors about undefined variables

Then you can proceed with the rest of the notebook in order!

