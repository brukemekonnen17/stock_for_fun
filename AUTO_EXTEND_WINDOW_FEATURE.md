# Auto-Extend Window Feature

## Problem Statement
For stocks with infrequent crossovers (like AAPL with tight filters), a 1-year window may only yield 2-4 valid events, which is insufficient for statistical testing (minimum 10 events required).

## Solution
Automatically detect insufficient events and recommend window extension.

## Implementation

### Cell 3: Configuration
```python
AUTO_EXTEND_CONFIG = {
    'enabled': True,
    'min_events_required': 10,      # Minimum for statistical tests
    'max_window_days': 1095,        # Max 3 years
    'extend_step_days': 365,        # Extend by 1 year each time
    'max_iterations': 2             # Try at most 2 extensions
}
```

### Cell 23: Auto-Extend Check
After event detection, checks if `valid_count < min_required`:

**If insufficient events:**
```
⚠️  INSUFFICIENT EVENTS DETECTED
Current valid events: 4 / 10 required
Current window: 365 days
Extending window to: 730 days

💡 ACTION REQUIRED:
   1. Update Cell 2: WINDOW_DAYS = 730
   2. Re-run from Cell 6 (Data Loading) onwards
   3. Or set AUTO_EXTEND_CONFIG['enabled'] = False to skip
```

**If at max window:**
```
⚠️  Only 4 events found, but already at max window (1095 days)
   Consider:
   - Lowering MANUAL_COOLDOWN_DAYS (currently: 8)
   - Relaxing XOVER_CFG filters
   - Using a more volatile stock
```

### Cell 57: Contract Export
Adds `window_extension` field to `analysis_contract.json`:
```json
{
  "window_extension": {
    "current_events": 4,
    "required_events": 10,
    "current_window_days": 365,
    "recommended_window_days": 730,
    "reason": "Only 4 valid events detected, need at least 10 for statistical tests"
  }
}
```

### LLM Integration
The LLM prompt now checks for `window_extension` and explains:
- Why insufficient events occurred
- How many events were found vs required
- Recommended window extension
- Actionable next step to re-run with longer window

## Example LLM Output

**Before (vague):**
> "The statistical tests show the pattern is unreliable because the p-values are null, meaning no tests were completed. This suggests the analysis failed."

**After (actionable):**
> "We only detected 4 valid EMA crossovers for AAPL over the past 365 days, but we need at least 10 events to run reliable statistical tests. This is why all p-values and q-values are null - the statistical comparison was skipped due to insufficient sample size. To get valid results, re-run the analysis with a longer time window of 730 days (2 years) to gather more crossover events. You can do this by updating WINDOW_DAYS = 730 in Cell 2 and re-running from Cell 6 onwards."

## Benefits

1. **Self-Diagnosing**: Automatically detects the small-N problem
2. **Actionable**: Provides specific window recommendation
3. **User-Friendly**: Clear output in notebook and LLM summary
4. **Configurable**: Can disable or adjust thresholds
5. **Safe**: Has max window limit (3 years) to prevent runaway extension

## Usage

### For Users
When you see the insufficient events warning:
1. Note the recommended window days
2. Update `WINDOW_DAYS` in Cell 2 (or `START_DATE`)
3. Re-run from Cell 6 onwards
4. Check if event count is now sufficient

### For Developers
Adjust `AUTO_EXTEND_CONFIG` to change:
- `min_events_required`: Raise/lower threshold
- `max_window_days`: Increase for more history
- `extend_step_days`: Smaller steps for finer control
- `enabled`: Set to `False` to disable feature

## Test Cases

### Case 1: AAPL with tight filters
- **365 days**: 4 events → Extension to 730 days recommended
- **730 days**: 8 events → Extension to 1095 days recommended
- **1095 days**: 12 events → ✅ Sufficient, tests run

### Case 2: PCSA (penny stock)
- **365 days**: 18 events → ✅ Sufficient, no extension needed

### Case 3: At max window
- **1095 days**: 6 events → Suggests relaxing filters or different stock

## Files Modified

1. **Analyst_Trade_Study.ipynb**
   - Cell 3: AUTO_EXTEND_CONFIG
   - Cell 23: Auto-extend check logic
   - Cell 57: Contract export with window_extension

2. **services/llm/summarizer.py**
   - Added "Window Extension" section to system prompt
   - LLM checks for window_extension in contract
   - Generates actionable guidance for users

## Status
✅ **Implemented and ready for testing**

Run the notebook with AAPL (365 days) to see the auto-extend feature in action!

