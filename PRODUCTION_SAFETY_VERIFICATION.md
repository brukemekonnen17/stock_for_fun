# Production Safety Verification & Hardening

## ✅ Completed Implementations

### Verification Improvements

1. **CAR Robustness Gate (Verification #4)**
   - ✅ Updated `crossover_verdict()` to use conservative CI when `ci_unstable` flag is set
   - ✅ Uses block bootstrap CI (most conservative) when unstable
   - ✅ Falls back to Newey-West CI if bootstrap not available
   - ✅ Updated `create_investor_card()` to use robust CIs in evidence section
   - ✅ Tracks `ci_source` and `ci_unstable` in investor card

2. **Run Summary Line (Hardening)**
   - ✅ Added CI-parseable run summary at end of notebook
   - ✅ Format: `RUN <run_id> | n_ev=<n> | best_H=<H> | q=<q> | eff=<bps>bps | veto=<YES/NO> | verdict=<VERDICT> | nw_vs_bs_width=<ratio> | adv_ok=<YES/NO>`
   - ✅ Enables CI/CD parsing and gating

### Hardening Improvements

1. **Version Pinning**
   - ✅ Pinned `statsmodels==0.14.1` (for CAR robustness)
   - ✅ Pinned `pandas-market-calendars==4.3.4` (for trading calendar)
   - ✅ Pinned `scipy==1.13.1` (for statistical tests)
   - ✅ All versions recorded in `requirements.txt`

2. **Cold-Start Guard** (TODO: Add to Cell 6)
   - ⚠️ **Needs manual addition** to Cell 6 after `raw_df, data_source = load_ohlcv_data(...)`
   - Should fail fast if:
     - No data returned (provider down)
     - <200 bars loaded (partial history)
   - Prevents silent failures with stale cache

3. **Verification Scripts**
   - ✅ Created `verify_production_safety.py` (7 verification checks)
   - ✅ Created `smoke_matrix_test.py` (5 test cases)

## 📋 Remaining Tasks

### Verification Tasks (Manual Testing Required)

1. **Determinism Verification (#1)**
   - Run notebook end-to-end twice with identical inputs
   - Compute SHA256 of all artifacts
   - Verify byte-for-byte match
   - Test with different `np.random.seed` → outputs should not change

2. **Calendar + Look-Ahead Guards (#2)**
   - Test with ticker spanning holidays (e.g., Thanksgiving)
   - Test with halt days
   - Temporarily drop `.shift(1)` in feature cell → guard should fail loudly

3. **Event De-dup Correctness (#3)**
   - Use choppy, low-ATR stock to force back-to-back crosses
   - Verify cool-down ≥ N bars enforced
   - Verify "dropped by reason" counts reflect persistence/opposite dedup
   - Verify no event dated on same day as cross computation

4. **Small-N + Effect Floor (#5)**
   - Construct case with q<0.10 but effect < 30 bps → must NOT show green
   - Test n=12 case → must show limited_power yellow chip even if q is green

5. **Economics Veto (#6)**
   - Test mega-cap (AAPL/NVDA) → should pass
   - Test mid-cap with wide ATR → should veto on impact
   - Test micro-cap → should fail ADV gate
   - Verify veto overrides statistical green to SKIP

6. **Provenance & Caching (#7)**
   - Delete cache → run_id must stay identical if raw provider output is identical
   - Change provider order → provenance stamps differ, but evidence should be same

### Hardening Tasks

1. **JSON Schema Validation (#2)**
   - Add JSON schema for `investor_card.json`, `run_meta.json`, `analysis_contract.json`
   - Validate before marking run green

2. **Unit Fixtures (#4)**
   - Add tiny CSV fixtures (10-20 rows) to exercise each guard
   - Test calendar, dedup, leakage, small-N, veto without network calls

## 🧪 Smoke Matrix Test Cases

Run these 5 test cases manually:

1. **Mega-cap/liquid**: AAPL/NVDA → expect BUY or REVIEW, no economics veto
2. **Mid-cap**: AMD/SHOP → one should fail **impact veto** or **effect floor**
3. **Low-liquidity**: Small ticker → **ADV gate** must fail
4. **Event-sparse**: BRK.B → small-N yellow chip likely
5. **Holiday window**: Any name spanning market holiday → 0 invalid bars

## 📝 Notes

- The cold-start guard needs to be manually added to Cell 6 (data loading)
- All verification checks are implemented but require manual execution
- The run summary line is automatically generated at the end of the notebook
- Conservative CI logic is fully implemented and will be used when `ci_unstable` is True

## 🎯 Next Steps

1. Manually add cold-start guard to Cell 6
2. Run verification script: `python verify_production_safety.py`
3. Execute smoke matrix tests for each ticker
4. Add JSON schema validation (optional but recommended)
5. Create unit test fixtures (optional but recommended)

