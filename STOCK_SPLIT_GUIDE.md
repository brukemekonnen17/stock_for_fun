# 📊 Stock Split Detection & Adjustment Guide

## 🔍 What You're Seeing: NVDA Example

### Current Data (Confusing!)
```
Current Price: $188.15
52-Week High: $1,255.87  ← This looks wrong!
52-Week Low: $86.62
```

**Why does this look weird?**  
The high of $1,255 doesn't make sense if current price is $188!

---

## 💡 Answer: NVIDIA Had a 10-for-1 Stock Split

### NVDA Stock Split Details
- **Date**: June 7, 2024
- **Ratio**: 10-for-1
- **Effect**: Each share became 10 shares, price divided by 10

### Before vs After Split

| Metric | Before Split (June 6) | After Split (June 7) |
|--------|----------------------|---------------------|
| **Shares owned** | 1 | 10 |
| **Price per share** | ~$1,200 | ~$120 |
| **Total value** | $1,200 | $1,200 (same) |
| **Market cap** | Same | Same |

**Key Point**: Total value unchanged, just divided into more pieces.

---

## 📈 Understanding the 52-Week Range

### Raw (Unadjusted) Data
This is what you're seeing:
```
High: $1,255.87 (before split, June 2024)
Low: $86.62 (after split, Nov 2023)
Current: $188.15 (after split, Nov 2024)
```

### Split-Adjusted Data (What You Should Use)
All prices adjusted to current split ratio:
```
High: $125.59 (adjusted: $1,255.87 ÷ 10)
Low: $86.62 (already post-split)
Current: $188.15 (post-split)
```

**Now it makes sense!** Stock went from $86 → $125 → back to $188.

---

## ✅ Solution: Use Split-Adjusted Data

### The notebook already does this correctly!

When you see:
```python
df_featured['adj_close']  # ✅ Split-adjusted
df_featured['close']       # ❌ Raw (not adjusted)
```

**Always use `adj_close`** for analysis.

---

## 🔧 New Feature: Automatic Split Detection

I've added a new cell to the notebook that will detect and display stock splits:

```python
# === Stock Split Detection ===
stock = yf.Ticker(TICKER)
splits = stock.splits

if not splits.empty:
    print(f"✅ Found {len(splits)} stock split(s):")
    for date, ratio in splits.items():
        print(f"   Date: {date}")
        print(f"   Ratio: {ratio}:1")
```

### Example Output for NVDA:
```
✅ Found 1 stock split(s) for NVDA:

   📅 Date: 2024-06-07
   📊 Ratio: 10.0:1 (each share → 10 shares)
   💰 Price adjustment: Divided by 10.0
   Example: $1,000 → $100.00

⚠️  RECENT SPLIT DETECTED (within last year):
   Date: 2024-06-07
   Split: 10.0:1
   
   This explains unusual price ranges in 52-week data!
   ✅ Using 'adj_close' ensures split-adjusted prices.
```

---

## 📊 Common Stock Splits

### Recent Major Splits

| Company | Date | Ratio | Why |
|---------|------|-------|-----|
| **NVDA** | Jun 2024 | 10:1 | Price accessibility (~$1,200 → ~$120) |
| **TSLA** | Aug 2022 | 3:1 | Price accessibility (~$900 → ~$300) |
| **AAPL** | Aug 2020 | 4:1 | Price accessibility (~$500 → ~$125) |
| **GOOGL** | Jul 2022 | 20:1 | Price accessibility (~$2,200 → ~$110) |
| **AMZN** | Jun 2022 | 20:1 | Price accessibility (~$2,400 → ~$120) |

### Why Companies Split Stock

1. **Lower price per share** → More accessible to retail investors
2. **Increase liquidity** → More shares trading
3. **Options become cheaper** → 1 contract = 100 shares
4. **Psychological appeal** → $100/share feels better than $1,000/share

**Note**: Stock splits don't change company value, just divide it into more pieces.

---

## 🔍 How to Interpret Your Data

### Scenario 1: No Split
```
Current: $150
52-Week High: $180
52-Week Low: $100
```
✅ Easy to interpret: Stock ranged from $100-$180

### Scenario 2: Split Happened (Your Case)
```
Current: $150
52-Week High: $1,000  ← Before split!
52-Week Low: $80       ← After split!
```
⚠️ Confusing! Need to adjust for split

### Scenario 2 (Adjusted):
```
Current: $150
52-Week High: $100 (adjusted from $1,000)
52-Week Low: $80
```
✅ Now clear: Stock ranged from $80-$100, currently at $150

---

## 🛠️ How the Notebook Handles This

### 1. **Uses Split-Adjusted Prices**
```python
df['adj_close']  # Automatically adjusted by yfinance/Tiingo
```

### 2. **Detects Splits**
```python
# New cell added automatically detects splits
stock.splits
```

### 3. **Shows Warning**
```
⚠️  RECENT SPLIT DETECTED
   This explains unusual price ranges!
```

---

## 🧮 Manual Split Adjustment Formula

If you need to adjust prices manually:

```python
# If stock had N:1 split on split_date
if date < split_date:
    adjusted_price = raw_price / N
else:
    adjusted_price = raw_price
```

### Example: NVDA 10:1 Split
```python
# Price before June 7, 2024
pre_split_price = 1200
adjusted_price = 1200 / 10  # = $120

# Price after June 7, 2024
post_split_price = 120
adjusted_price = 120  # No adjustment needed
```

---

## 📝 Best Practices

### ✅ DO:
1. **Use `adj_close`** for all analysis
2. **Check for splits** when data looks unusual
3. **Interpret 52-week ranges** with split context
4. **Use split-adjusted data** for returns calculations

### ❌ DON'T:
1. Use raw `close` prices for comparisons across split dates
2. Panic when you see $1,000 high with $150 current (check for splits!)
3. Compare pre-split and post-split prices directly
4. Ignore split warnings in the notebook

---

## 🔮 Future Splits

### How to Tell If a Split is Coming:
1. **High stock price** (>$1,000)
2. **Company announcement** (usually 2-4 weeks notice)
3. **Board approval** (filed with SEC)
4. **Historical pattern** (some companies split regularly)

### Upcoming Split Example:
```
Company XYZ announces 5:1 split effective Dec 1, 2024
Before: 100 shares @ $500 = $50,000
After:  500 shares @ $100 = $50,000
```

---

## 🎯 Summary for NVDA

### What Happened:
1. NVDA traded around $1,200/share (too expensive for many)
2. June 7, 2024: 10-for-1 split announced and executed
3. Price became ~$120/share (same total value)
4. Stock has since moved to $188/share

### Your 52-Week Range Explained:
```
$1,255.87 high → $125.59 adjusted (before split)
$86.62 low                       (after split)
$188.15 current                  (after split)
```

**Range in split-adjusted terms**: $86.62 - $188.15 ✅

---

## 📚 Additional Resources

- **NYSE/NASDAQ Split Calendar**: Lists upcoming splits
- **Company Investor Relations**: Announces splits
- **SEC Filings (8-K)**: Official split documentation
- **yfinance/Tiingo**: Provides split-adjusted data automatically

---

## ✅ Action Items

1. ✅ **Split detection added** to notebook
2. ✅ **Use `adj_close`** (notebook already does)
3. ✅ **Understand 52-week ranges** in split context
4. ℹ️  **Check for splits** when data looks unusual

---

**Bottom Line**: The $1,255 high is from before NVDA's 10:1 split. When adjusted, it's $125.59, which makes perfect sense with the current $188.15 price!

