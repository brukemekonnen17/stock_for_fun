# 🎯 Critical Improvements Implementation Plan

**Goal**: Make notebook defensible and ship-safe with 7 critical improvements

---

## Implementation Order

1. **Determinism & Provenance** (run_id) - Foundation
2. **Trading Calendar Integrity** - Foundation  
3. **Hard Look-Ahead Guard** - Validity
4. **Event De-dup on Settled Bars** - Event quality
5. **CAR Robustness** (Newey-West + Bootstrap) - Statistical rigor
6. **Small-N Safeguard** - Safety check
7. **Economics Realism Veto** - Final gate

---

## 1. Determinism & Provenance (run_id)

### Implementation
- **Location**: New cell after Cell 3 (after global init)
- **Function**: Generate deterministic `run_id` hash
- **Hash Inputs**:
  - `ticker`: TICKER
  - `window_days`: WINDOW_DAYS
  - `data_source`: Provider name (Tiingo/AlphaVantage/yfinance)
  - `seed`: Random seed (SEED or 42)
  - `pandas_version`: pd.__version__
  - `numpy_version`: np.__version__
  - `python_version`: sys.version_info

### Code
```python
import hashlib
import sys
import pandas as pd
import numpy as np

def generate_run_id(ticker, window_days, data_source, seed, versions):
    """Generate deterministic run_id hash"""
    components = {
        'ticker': str(ticker),
        'window_days': int(window_days),
        'data_source': str(data_source),
        'seed': int(seed),
        'pandas': versions.get('pandas', ''),
        'numpy': versions.get('numpy', ''),
        'python': versions.get('python', '')
    }
    # Create deterministic string
    hash_str = '|'.join(f'{k}:{v}' for k, v in sorted(components.items()))
    # Generate SHA256 hash
    run_id = hashlib.sha256(hash_str.encode()).hexdigest()[:16]
    return run_id

# Get versions
versions = {
    'pandas': pd.__version__,
    'numpy': np.__version__,
    'python': f"{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}"
}

# Generate run_id (data_source will be set in Cell 6, use placeholder for now)
RUN_ID = generate_run_id(
    ticker=TICKER,
    window_days=WINDOW_DAYS,
    data_source='pending',  # Will update after Cell 6
    seed=globals().get('SEED', 42),
    versions=versions
)

print(f"✅ Run ID generated: {RUN_ID}")
print(f"   Components: ticker={TICKER}, window={WINDOW_DAYS}, seed={globals().get('SEED', 42)}")
```

### Updates Required
- **Cell 6**: Update `RUN_ID` after `data_source` is known
- **Cell 35** (Investor Card): Add `run_id` field
- **Cell 38** (LLM Contract): Add `run_id` field
- **Cell 51** (Run Meta): Add `run_id` field
- **New Validation Cell**: Check determinism (identical run_id on re-run)

---

## 2. Trading Calendar Integrity

### Implementation
- **Location**: New cell after Cell 6 (after data loading)
- **Library**: `pandas_market_calendars` or `pandas.tseries.holiday`
- **Function**: Validate all dates are valid trading days

### Code
```python
import pandas_market_calendars as mcal
from datetime import datetime

def get_us_trading_calendar(start_date, end_date):
    """Get US market trading calendar"""
    nyse = mcal.get_calendar('NYSE')
    schedule = nyse.schedule(start_date=start_date, end_date=end_date)
    return set(schedule.index.date)

def validate_trading_calendar(df, events_df=None):
    """Validate all dates are valid trading days"""
    trading_days = get_us_trading_calendar(
        df['date'].min().date(),
        df['date'].max().date()
    )
    
    # Check data dates
    data_dates = set(df['date'].dt.date)
    invalid_data = data_dates - trading_days
    
    # Check event dates
    invalid_events = []
    if events_df is not None and not events_df.empty:
        event_dates = set(pd.to_datetime(events_df['date']).dt.date)
        invalid_events = list(event_dates - trading_days)
    
    return {
        'invalid_data_bars': len(invalid_data),
        'invalid_event_dates': invalid_events,
        'all_valid': len(invalid_data) == 0 and len(invalid_events) == 0
    }

# Validate calendar
if 'df_clean' in globals() and not df_clean.empty:
    calendar_check = validate_trading_calendar(df_clean)
    print("="*70)
    print("TRADING CALENDAR INTEGRITY CHECK")
    print("="*70)
    print(f"Invalid data bars: {calendar_check['invalid_data_bars']}")
    print(f"Invalid event dates: {len(calendar_check['invalid_event_dates'])}")
    
    if not calendar_check['all_valid']:
        raise ValueError("Calendar integrity check failed - invalid trading days detected!")
    else:
        print("✅ All dates are valid trading days")
```

### Updates Required
- **Cell 6**: Add calendar validation after data loading
- **Cell 18**: Validate event dates and forward windows

---

## 3. Hard Look-Ahead Guard

### Implementation
- **Location**: New cell after Cell 11 (after feature engineering)
- **Function**: Assert all signal features are shifted

### Code
```python
def assert_no_lookahead_leakage(df_featured, events):
    """Assert no look-ahead bias in signal features"""
    print("="*70)
    print("HARD LOOK-AHEAD GUARD: Leakage Check")
    print("="*70)
    
    # Signal features that must be shifted
    signal_features = ['ema20', 'ema50', 'rv', 'rv_annualized']
    
    violations = []
    
    for idx, event in events.iterrows():
        event_date = pd.to_datetime(event['date'])
        event_idx = df_featured[df_featured['date'] == event_date].index
        
        if len(event_idx) == 0:
            continue
            
        event_idx = event_idx[0]
        
        # Check each signal feature
        for feat in signal_features:
            if feat not in df_featured.columns:
                continue
                
            # Feature at event time should equal previous day's value
            feat_at_t0 = df_featured.loc[event_idx, feat]
            feat_prev = df_featured.loc[event_idx - 1, feat] if event_idx > 0 else None
            
            if feat_prev is not None and not np.isclose(feat_at_t0, feat_prev, rtol=1e-5):
                violations.append({
                    'event_date': event_date,
                    'feature': feat,
                    't0_value': feat_at_t0,
                    'prev_value': feat_prev,
                    'diff': abs(feat_at_t0 - feat_prev)
                })
    
    if violations:
        print(f"❌ LEAKAGE DETECTED: {len(violations)} violations")
        for v in violations[:5]:  # Show first 5
            print(f"   {v['event_date']}: {v['feature']} differs (t0={v['t0_value']:.6f}, prev={v['prev_value']:.6f})")
        raise ValueError("Look-ahead leakage detected! Features must use shift(1) at event time.")
    else:
        print("✅ No look-ahead leakage detected")
        print("   All signal features properly lagged (shift(1))")

# Run check
if 'df_featured' in globals() and 'events' in globals():
    assert_no_lookahead_leakage(df_featured, events)
```

### Updates Required
- **Cell 11**: Ensure all features use `.shift(1)` for event detection
- **Cell 18**: Ensure entries use `open_{t+1}` (next session's open)

---

## 4. Event De-dup on Settled Bars

### Implementation
- **Location**: Update Cell 18 (event detection)
- **Function**: Use settled (prior day) values, record reason codes

### Code Changes
```python
# In event detection, use settled values:
# - Use close_{t-1} for EMA calculations
# - Use settled EMA20/50 from prior day
# - Record drop reasons

drop_reasons = {
    'persistence_fail': 0,
    'cooldown': 0,
    'opposite_cross': 0,
    'volume_fail': 0
}

# After filtering, create summary
reason_summary = pd.DataFrame({
    'reason': list(drop_reasons.keys()),
    'count': list(drop_reasons.values())
})

print("Event De-duplication Summary:")
print(reason_summary)

# Assert spacing
if len(events) > 1:
    event_dates = pd.to_datetime(events['date']).sort_values()
    gaps = (event_dates.diff().dt.days).dropna()
    min_gap = gaps.min()
    assert min_gap >= COOLDOWN_DAYS, f"Events too close: min gap = {min_gap} days"
```

---

## 5. CAR Robustness (Newey-West + Bootstrap)

### Implementation
- **Location**: Update Cell 23 (statistical comparison)
- **Libraries**: `statsmodels` for Newey-West, custom bootstrap

### Code
```python
from statsmodels.stats.sandwich_covariance import cov_hac
from scipy import stats

def compute_newey_west_ci(car_series, lag=5, alpha=0.05):
    """Compute Newey-West HAC standard errors and CI"""
    n = len(car_series)
    mean_car = car_series.mean()
    
    # Newey-West HAC covariance
    # For simplicity, use manual calculation
    residuals = car_series - mean_car
    # ... (full implementation)
    
    se_nw = np.sqrt(variance_nw / n)
    t_crit = stats.t.ppf(1 - alpha/2, df=n-1)
    ci_lower = mean_car - t_crit * se_nw
    ci_upper = mean_car + t_crit * se_nw
    
    return {
        'mean': mean_car,
        'se_nw': se_nw,
        'ci_lower_nw': ci_lower,
        'ci_upper_nw': ci_upper
    }

def block_bootstrap_ci(car_series, block_size=5, n_bootstrap=1000, alpha=0.05):
    """5-day block bootstrap CI"""
    n = len(car_series)
    bootstrap_means = []
    
    for _ in range(n_bootstrap):
        # Sample blocks
        blocks = []
        i = 0
        while i < n:
            block_end = min(i + block_size, n)
            blocks.append(car_series.iloc[i:block_end].values)
            i = block_end
        # Resample blocks with replacement
        resampled = np.concatenate(np.random.choice(blocks, size=len(blocks), replace=True))
        bootstrap_means.append(np.mean(resampled[:n]))
    
    ci_lower = np.percentile(bootstrap_means, 100 * alpha/2)
    ci_upper = np.percentile(bootstrap_means, 100 * (1 - alpha/2))
    
    return {
        'ci_lower_bs': ci_lower,
        'ci_upper_bs': ci_upper
    }

# For each horizon
for H in [1, 3, 5, 10, 20]:
    h_cars = ev_outcomes[ev_outcomes['H'] == H]['car_fwd']
    
    # Newey-West CI
    nw_result = compute_newey_west_ci(h_cars, lag=5)
    
    # Block bootstrap CI
    bs_result = block_bootstrap_ci(h_cars, block_size=5)
    
    # Compare widths
    nw_width = nw_result['ci_upper_nw'] - nw_result['ci_lower_nw']
    bs_width = bs_result['ci_upper_bs'] - bs_result['ci_lower_bs']
    width_ratio = abs(nw_width - bs_width) / min(nw_width, bs_width)
    
    # Flag if disagreement > 25%
    ci_unstable = width_ratio > 0.25
    
    # Add to xover_stats
    xover_stats.loc[xover_stats['H'] == H, 'ci_lower_nw'] = nw_result['ci_lower_nw']
    xover_stats.loc[xover_stats['H'] == H, 'ci_upper_nw'] = nw_result['ci_upper_nw']
    xover_stats.loc[xover_stats['H'] == H, 'ci_lower_bs'] = bs_result['ci_lower_bs']
    xover_stats.loc[xover_stats['H'] == H, 'ci_upper_bs'] = bs_result['ci_upper_bs']
    xover_stats.loc[xover_stats['H'] == H, 'ci_unstable'] = ci_unstable
```

---

## 6. Small-N Safeguard

### Implementation
- **Location**: Update Cell 35 (Investor Card)
- **Function**: Tag small-N, require effect floor

### Code
```python
MIN_EFFECT_BPS = 30  # 30 basis points minimum

# In verdict logic
for H in [1, 3, 5, 10, 20]:
    h_stats = xover_stats[xover_stats['H'] == H].iloc[0]
    n = h_stats['n']
    q_val = h_stats['q']
    median_car = h_stats['median_car']
    median_car_bps = median_car * 10000
    
    # Small-N check
    limited_power = n < 20
    
    # Effect floor check
    effect_floor_pass = abs(median_car_bps) >= MIN_EFFECT_BPS
    
    # Significance (requires both q < 0.10 AND effect floor)
    is_significant = (q_val < 0.10) and effect_floor_pass
    
    # Tag in investor card
    if limited_power:
        investor_card['evidence'][f'H{H}_limited_power'] = True
        investor_card['evidence'][f'H{H}_chip'] = 'YELLOW'
    elif is_significant:
        investor_card['evidence'][f'H{H}_chip'] = 'GREEN'
    else:
        investor_card['evidence'][f'H{H}_chip'] = 'RED'
```

---

## 7. Economics Realism Veto

### Implementation
- **Location**: Update Cell 29 (capacity checks)
- **Function**: Two cost estimates + impact budget

### Code
```python
def compute_atr_based_slippage(df, k=0.5):
    """ATR-based slippage model"""
    # ATR = Average True Range
    high_low = df['high'] - df['low']
    high_close = abs(df['high'] - df['close'].shift(1))
    low_close = abs(df['low'] - df['close'].shift(1))
    tr = pd.concat([high_low, high_close, low_close], axis=1).max(axis=1)
    atr = tr.rolling(14).mean()
    
    # Slippage = k * ATR / price
    slippage_bps = (k * atr / df['close']) * 10000
    return slippage_bps.clip(2, 50)  # Clip to reasonable range

def compute_impact_budget(size_usd, adv_usd, c=10):
    """Market impact model"""
    # impact_bps = c * (size/ADV)^0.5
    size_ratio = size_usd / adv_usd
    impact_bps = c * np.sqrt(size_ratio) * 100
    return impact_bps

# Two cost estimates
cost_quote = COSTS['total_bps']  # Existing quote-based
cost_atr = compute_atr_based_slippage(df_featured.tail(30)).median()

# Take maximum
total_cost_bps = max(cost_quote, cost_atr)

# Impact budget
position_size_usd = 1_000_000  # Example
impact_bps = compute_impact_budget(position_size_usd, ADV_USD)

# Veto if impact too high
IMPACT_THRESHOLD_BPS = 20
impact_veto = impact_bps > IMPACT_THRESHOLD_BPS

# Update economics gate
if impact_veto:
    investor_card['economics']['impact_veto'] = True
    investor_card['economics']['impact_bps'] = impact_bps
    investor_card['verdict'] = 'SKIP'  # Override verdict
```

---

## Acceptance Checklist

- [ ] NW-CI + block-bootstrap CI present; yellow badge on disagreement
- [ ] Leakage assertion proves all signal features are `.shift(1)` at `t0`; entries use `open_{t+1}`
- [ ] Event de-dup summary + assertions on spacing/persistence
- [ ] Small-N + effect-floor gating wired into verdict
- [ ] Cost = max(quote, ATR-based) and **impact budget** can veto a BUY
- [ ] Market-calendar guard: 0 invalid bars across all windows
- [ ] `run_id` stamped; rerun produces identical outputs

---

## Next Steps

1. Implement each improvement in order
2. Add validation cells for each
3. Update investor card with new fields
4. Test determinism (identical run_id on re-run)
5. Update documentation

