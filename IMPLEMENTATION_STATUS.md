# 🚀 Critical Improvements - Implementation Status

**Goal**: Implement 7 critical improvements to make notebook defensible and ship-safe

---

## ✅ Implementation Plan

### Phase 1: Foundation (Do First)
1. ✅ **Determinism & Provenance** - run_id generation and stamping
2. ✅ **Trading Calendar Integrity** - US market calendar validation

### Phase 2: Validity Guards
3. ✅ **Hard Look-Ahead Guard** - Leakage detection
4. ✅ **Event De-dup on Settled Bars** - Use prior day values, reason codes

### Phase 3: Statistical Rigor
5. ✅ **CAR Robustness** - Newey-West + Block Bootstrap CIs

### Phase 4: Safety Checks
6. ✅ **Small-N Safeguard** - Limited power tagging + effect floor
7. ✅ **Economics Realism Veto** - Two cost models + impact budget

---

## 📋 Detailed Implementation Checklist

### 1. Determinism & Provenance (run_id)

**Status**: 🔄 In Progress

**Tasks**:
- [ ] Create run_id generation cell (after Cell 3)
- [ ] Hash inputs: ticker, window, provider, seed, versions
- [ ] Update run_id after Cell 6 (when data_source known)
- [ ] Stamp run_id into:
  - [ ] investor_card.json
  - [ ] run_meta.json
  - [ ] analysis_contract.json
- [ ] Add determinism validation cell (check identical run_id on re-run)

**Acceptance**: Two consecutive runs produce identical run_id and byte-identical artifacts

---

### 2. Trading Calendar Integrity

**Status**: ⏳ Pending

**Tasks**:
- [ ] Install pandas_market_calendars
- [ ] Create calendar validation cell (after Cell 6)
- [ ] Validate all data dates are trading days
- [ ] Validate event dates are trading days
- [ ] Validate forward windows land on trading days
- [ ] Assert 0 invalid bars

**Acceptance**: Calendar check prints 0 invalid bars, raises on any off-calendar date

---

### 3. Hard Look-Ahead Guard

**Status**: ⏳ Pending

**Tasks**:
- [ ] Create leakage check cell (after Cell 11)
- [ ] Assert signal features at t0 equal shift(1)
- [ ] Assert entries use open_{t+1} (next session's open)
- [ ] Fail fast on violations
- [ ] Test: Remove .shift(1) from one feature → should fail

**Acceptance**: Leakage check cell fails fast when .shift(1) removed

---

### 4. Event De-dup on Settled Bars

**Status**: ⏳ Pending

**Tasks**:
- [ ] Update Cell 18 to use settled (prior day) values
- [ ] Record drop reason codes (persistence/cool-down/opposite)
- [ ] Create summary table with counts by reason
- [ ] Assert no events < cool-down apart
- [ ] Use close_{t-1} for EMA calculations

**Acceptance**: Summary table shows counts by reason, assertion confirms spacing

---

### 5. CAR Robustness (Newey-West + Bootstrap)

**Status**: ⏳ Pending

**Tasks**:
- [ ] Install statsmodels (for Newey-West)
- [ ] Update Cell 23 to compute NW-CI (lag=5)
- [ ] Add 5-day block bootstrap CI
- [ ] Compare widths, flag if disagreement >25%
- [ ] Add yellow "unstable CI" badge to investor card
- [ ] Update xover_stats with both CIs

**Acceptance**: Each horizon reports NW-CI and block-bootstrap CI; yellow badge on disagreement

---

### 6. Small-N Safeguard

**Status**: ⏳ Pending

**Tasks**:
- [ ] Update Cell 35 (Investor Card) verdict logic
- [ ] Tag n<20 as "limited power"
- [ ] Require effect floor (30-50 bps) even if q<0.10
- [ ] Yellow chip for small-N cases
- [ ] Only green when both q<0.10 AND effect floor pass

**Acceptance**: Investor card shows yellow chip for small-N, green only when both conditions pass

---

### 7. Economics Realism Veto

**Status**: ⏳ Pending

**Tasks**:
- [ ] Update Cell 29 (capacity checks)
- [ ] Compute ATR-based slippage: `slip_bps = k * ATR/price` (k=0.5)
- [ ] Compute impact budget: `impact_bps = c * (size/ADV)^0.5` (c=10)
- [ ] Cost = max(quote, ATR-based)
- [ ] Veto if impact > threshold (20 bps)
- [ ] Downgrade to HOLD/SKIP when cost/impact gate fails
- [ ] Red reason chip in investor card

**Acceptance**: Trade can be stat-sig & positive yet downgraded when cost/impact gate fails

---

## 🎯 Next Steps

1. **Start with Foundation** (Items 1-2)
2. **Add Validity Guards** (Items 3-4)
3. **Enhance Statistics** (Item 5)
4. **Add Safety Checks** (Items 6-7)
5. **Test All Acceptance Criteria**

---

## 📝 Notes

- All improvements are **critical** (not optional)
- Each has clear acceptance criteria
- Implementation order matters (foundation first)
- Test determinism early (run_id validation)

---

**Last Updated**: Starting implementation now...

