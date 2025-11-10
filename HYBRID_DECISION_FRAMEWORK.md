# Hybrid Decision Framework Implementation

## Overview
Implemented a two-stage hybrid decision system that combines statistical rigor with contextual market signals (flow, regime, social/meme, catalysts) to provide more actionable trading decisions.

## Architecture

### Stage A: Hard Safety Gates (Must Pass)
Binary filters that prevent trading when fundamental safety requirements aren't met:

1. **Liquidity Gate**: ADV ≥ $1M minimum
2. **Capacity Gate**: Position size within ADV limits (from capacity_status)
3. **Spread Gate**: Spread ≤ 50 bps max
4. **Impact Gate**: Market impact ≤ 20 bps threshold
5. **Data Health Gate**: 
   - No small-N issues (n ≥ 10 for significance)
   - No look-ahead bias
   - CI stability checks

All gates must pass for BUY/REACTIVE consideration. Failure → immediate SKIP.

### Stage B: Evidence Score (Weighted Components)
Continuous scoring system (0.0 to 1.0) combining five components:

#### Component Weights
```
stats (S):     40%  # Statistical edge
flow (F):      20%  # Volume/participation  
regime (R):    20%  # Trend/volatility alignment
catalyst (C):  10%  # Time-sensitive events
social (M):    10%  # Nowcast attention (capped)
```

#### S: Statistical Edge (40% weight)
- Uses best horizon (typically H=5) from `xover_stats`
- Scoring: `sigmoid((effect_bps - 30) / 20) * FDR_penalty`
- FDR penalty: 1.0 if q<0.15, 0.5 if q<0.25, 0.0 otherwise
- Based on:
  - `hl_diff_bps`: Hodges-Lehmann effect size in basis points
  - `q`: FDR-corrected significance value
  - `effect_g`: Hedges' g effect size

#### F: Flow/Participation (20% weight)
- Primary: Volume surge ratio from `vol_surge_stats` (5d/30d)
- Fallback: Recent 5d volume / 30d average from `df_featured`
- Scoring: `clip((vol_ratio - 1.0) / 1.0, 0, 1)`
- Neutral (0.5) if no data available

#### R: Regime Alignment (20% weight)
Combines three checks (each contributing to total score):
- **EMA Trend** (+0.4): EMA20 > EMA50 (bullish trend)
- **ADX** (+0.3): ADX > 20 (trending, not choppy)
- **IV-RV** (+0.3): IV-RV in 'expansion' or 'balanced' (favorable vol regime)
- Score clipped to [0, 1]

#### C: Catalyst Proximity (10% weight)
- Placeholder: 0.5 (neutral) pending earnings calendar integration
- Future: Distance to earnings, guidance, FTC decisions

#### M: Social/Meme Nowcast (10% weight)
- Uses `meme_result` z-score
- Scoring: `(clip(z_score, -2, 2) + 2) / 4` → maps [-2,2] to [0,1]
- Incorporates:
  - Reddit thread count Δ7d
  - Twitter/X mentions Δ3d
  - Google Trends Δ7d
  - Options unusual volume
- Neutral (0.5) if no social data

### Stage C: Verdict Mapping (3-Way Decision)

#### Thresholds
```
THRESHOLD_BUY      = 0.65  # High confidence
THRESHOLD_REACTIVE = 0.45  # Medium confidence (flow/social driven)
```

#### Decision Logic
```python
if not safety_gates.overall_pass:
    verdict = "SKIP"
    reason = "Safety gates failed"
elif evidence_score >= 0.65:
    verdict = "BUY"
    playbook = "swing"
elif evidence_score >= 0.45:
    verdict = "REACTIVE"
    playbook = "reactive"
else:
    verdict = "SKIP"
    reason = "Evidence score too low"
```

## Playbooks

### Swing Playbook (Evidence-Led)
**Conditions**: Strong stats (S) + regime alignment (R); social (M) optional

| Parameter | Value | Rationale |
|-----------|-------|-----------|
| Entry | Breakout + volume confirm | High conviction, wait for confirmation |
| Risk | 1.5 × ATR | Standard swing stop |
| Target | 2.0R (risk-reward) | Asymmetric upside |
| Hold | 3-10 days | Swing timeframe |
| Size | 100% (subject to Kelly) | Full position |

### Reactive Playbook (Flow/Social-Led)
**Conditions**: Stats weak BUT flow (F) + social (M) strong; safety gates pass

| Parameter | Value | Rationale |
|-----------|-------|-----------|
| Entry | VWAP reclaim or ORB with delta-volume | Momentum/flow entry |
| Risk | 0.6 × ATR | Tight stop (lower conviction) |
| Target | 1.5R | Quick profit take |
| Hold | Intraday to 2 days | Short-term scalp |
| Size | 50% | Reduced size (lower edge) |

## Integration Points

### Notebook (Cell 27)
- Implemented in new cell "7D: Hybrid Decision Framework"
- Runs after statistical tests (Cell 26)
- Produces `hybrid_decision` dict with all components

### Data Contract
Needs to export:
```python
{
  'verdict_hybrid': 'BUY | REACTIVE | SKIP',
  'evidence_score': 0.xxx,
  'components': {'S': x, 'F': x, 'R': x, 'C': x, 'M': x},
  'weights': {...},
  'safety_gates': {...},
  'playbook_type': 'swing | reactive | null',
  'playbooks': {...},
  'thresholds': {'buy': 0.65, 'reactive': 0.45}
}
```

### LLM Summary
Should explain:
1. Evidence score breakdown with interpretation
2. Why each component scored as it did
3. Which safety gates passed/failed
4. Why verdict landed at BUY/REACTIVE/SKIP
5. Specific playbook recommendations with entry/stop/target

Example:
> "**BUY – Evidence 0.71** (Stats +0.35, Regime +0.18, Flow +0.11, Social +0.07). *q=0.06, effect=+42bps [CI +12,+68]; capacity OK; impact 14bps < 20bps.* Use Swing Playbook: breakout entry, 1.5× ATR stop, 2R target, 3-10 day hold."

## Guardrails

### Weight Constraints
- Social (M) and Flow (F) are capped at 30% combined
- Cannot override an ECON_VETO or data-integrity fail
- Stats (S) always weighted highest (40%)

### Evaluation Metrics
Track per mode:
- **Swing**: hit rate, net median, max DD
- **Reactive**: expectancy per trade, win-streak risk

### Calibration
- Weights and thresholds calibrated on train data
- Frozen before OOS evaluation
- Backtest with anchored walk-forward (no overlap)

## Benefits

1. **More Actionable**: Provides clear guidance even when stats alone are inconclusive
2. **Risk-Bounded**: Hard safety gates prevent trading in unsafe conditions
3. **Context-Aware**: Incorporates real-time market signals (flow, social, regime)
4. **Transparent**: Full evidence breakdown shows why each decision was made
5. **Disciplined**: Still requires statistical foundation (40% weight on stats)

## Next Steps

1. ✅ Notebook implementation (Cell 27)
2. ✅ LLM JSON parsing robustness (control character handling)
3. 🔄 Update `create_analysis_json_contract` to include hybrid_decision
4. 🔄 Update LLM prompt to explain evidence-based decisions
5. ⏳ Add catalyst calendar integration (earnings, FTC)
6. ⏳ Implement spread-widening penalty for social (M)
7. ⏳ Backtest evaluation on train/test split
8. ⏳ Weight calibration and threshold tuning

## Files Modified

1. **Analyst_Trade_Study.ipynb** (Cell 27): Core hybrid decision logic
2. **services/llm/summarizer.py**: 
   - Enhanced JSON parsing with control character cleaning
   - Updated prompt to prevent literal newlines in JSON
3. **HYBRID_DECISION_FRAMEWORK.md** (this file): Documentation

## Status
✅ **Stage A, B, C fully implemented**  
✅ **Two playbooks defined**  
🔄 **LLM integration in progress**  
⏳ **Backtest validation pending**

