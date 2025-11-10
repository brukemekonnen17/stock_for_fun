# LLM v2 Enhancements - Statistical Analysis & Efficiency

## Summary

Enhanced LLM v2 with comprehensive statistical analysis, removed legacy v1, and added more data fields for better decision-making.

## Changes Made

### 1. ✅ Removed LLM v1 (Legacy)

- **Removed**: All references to `propose_trade()` (legacy LLM)
- **Fallback**: Now uses `_mock_plan()` if v2 is disabled or fails
- **Result**: Cleaner codebase, only one LLM path to maintain

### 2. ✅ Enhanced LLM Prompt (`PROMPTS/LLM_SYSTEM.md`)

**New Statistical Analysis Section:**
- Effect size interpretation (Small/Medium/Large)
- Statistical significance rules (p-value thresholds)
- Confidence interval interpretation
- Multiple testing correction (FDR)
- Volatility regime analysis (IV vs RV)
- Volume & participation analysis
- Pattern confidence assessment

**Time Horizon Analysis:**
- **Intraday (0-1 day)**: ORB breakouts, momentum, gap fills
- **Swing (1-5 days)**: Pattern completion, catalyst playout
- **Long-term (5-30 days)**: Sector context, trend alignment

**Decision Logic:**
- Strong BUY (0.75+ confidence): Clear criteria
- REACTIVE (0.60-0.74): Medium confidence setups
- SKIP (<0.60): Clear rejection criteria

**Efficiency Rules:**
- Prioritize high-value signals
- Reject early (spread violations)
- Combine evidence (2+ confirming signals)
- Quantify uncertainty

### 3. ✅ Enhanced Schema (`apps/api/schemas_llm.py`)

**Added:**
```python
statistical_analysis: Optional[Dict[str, object]] = None
```

**Required Structure:**
```json
{
  "statistical_analysis": {
    "effect_sizes": {
      "volume_surge": "LARGE|MEDIUM|SMALL",
      "price_momentum": "LARGE|MEDIUM|SMALL",
      "iv_rv_gap": "LARGE|MEDIUM|SMALL",
      "sector_strength": "LARGE|MEDIUM|SMALL"
    },
    "significance": {
      "event_study_p": 0.05,
      "event_study_significant": true,
      "fdr_q": 0.03,
      "interpretation": "CAR significant at T+1, survives FDR correction"
    },
    "confidence_intervals": {
      "car_t1_ci": [-0.005, 0.025],
      "width_interpretation": "NARROW|WIDE|MODERATE"
    },
    "volatility_regime": {
      "iv_rv_interpretation": "IV > RV by 2%, options expensive",
      "volatility_trend": "INCREASING|DECREASING|STABLE"
    },
    "time_horizon_analysis": {
      "intraday_setup": "ORB breakout candidate, strong morning volume",
      "swing_setup": "Pattern completion expected in 2-3 days",
      "long_term_context": "Sector relative strength +0.05, supportive"
    },
    "risk_reward": {
      "intraday_rr": 2.5,
      "swing_rr": 3.2,
      "explain": "Intraday: 1.3% target, 0.5% stop. Swing: 4.5% target, 1.4% stop"
    }
  }
}
```

### 4. ✅ Enhanced Data Payload (`apps/api/main.py`)

**Added Fields:**
- **Technical Indicators**: ADR20, ATR14, EMA20, EMA50, RSI14, Bollinger Bands
- **Statistical Tests**: Volume test p-values, effect sizes, CIs
- **FDR Correction**: Multiple testing correction results
- **Event Study**: Full CAR summary with significance
- **Social Sentiment**: Score, mentions, bull ratio
- **Event Context**: Event type, days to event, materiality

**Before:**
```python
payload_for_llm = {
    "price": float(body.price),
    "volume_surge_ratio": float(body.volume_surge_ratio),
    "evidence": {"event_study": {"significant": event_study_car_sig}}
}
```

**After:**
```python
payload_for_llm = {
    "ticker": body.ticker,
    "price": float(body.price),
    "volume_surge_ratio": float(body.volume_surge_ratio),
    # Technical indicators
    "adr20": float(tech_indicators.get("adr20", 0.02)),
    "atr14": float(tech_indicators.get("atr14", body.price * 0.02)),
    "ema20": float(tech_indicators.get("ema20", body.price)),
    "rsi14": float(tech_indicators.get("rsi14", 50.0)),
    # Statistical tests
    "evidence": {
        "event_study": {
            "significant": event_study_car_sig,
            "car_summary": event_study_summary
        },
        "statistical_tests": evidence_stats,
        "fdr_correction": fdr_results
    },
    # Social sentiment
    "social_sentiment": {
        "score": social_data.get("sentiment_score", 0.0),
        "mentions": social_data.get("mention_count_total", 0),
        "bull_ratio": social_data.get("bullish_pct", 0.5)
    }
    # ... more fields
}
```

## Additional Data Needed

### Currently Available:
✅ Technical indicators (RSI, ATR, EMA, BB)  
✅ Volume surge ratio  
✅ Statistical tests (Mann-Whitney, p-values, CIs)  
✅ Event study CAR  
✅ FDR correction  
✅ Pattern detection  
✅ Social sentiment  
✅ Sector relative strength  
✅ IV-RV gap  

### Could Add (Future Enhancements):

1. **Order Flow Data:**
   - Bid-ask imbalance
   - Large block trades
   - Dark pool activity

2. **Options Flow:**
   - Put/call ratio
   - Unusual options activity
   - Gamma exposure

3. **Market Microstructure:**
   - Order book depth
   - Trade size distribution
   - Time-weighted average price (TWAP)

4. **Alternative Data:**
   - Insider trading
   - Earnings revisions
   - Analyst upgrades/downgrades

5. **Intraday Patterns:**
   - Opening range (ORB) high/low
   - VWAP distance
   - Time-of-day effects

6. **Historical Performance:**
   - Similar setups win rate
   - Expected return distribution
   - Maximum drawdown

## Usage

### Enable LLM v2:
```bash
export ENABLE_LLM_PHASE1=1
```

### Test Enhanced Output:
```bash
python show_llm_output.py
```

### Check Metrics:
```bash
curl http://127.0.0.1:8000/metrics/llm_phase1 | jq
```

## Benefits

1. **Better Decisions**: Statistical rigor ensures high-confidence trades
2. **Risk Management**: Clear effect sizes and confidence intervals
3. **Efficiency**: Early rejection of poor setups saves compute
4. **Transparency**: Detailed statistical interpretation for audit
5. **Time Horizon Awareness**: Separate intraday vs swing analysis

## Next Steps

1. **Monitor Performance**: Track SLOs with enhanced metrics
2. **Calibrate Confidence**: Use historical data to calibrate confidence scores
3. **A/B Testing**: Compare v2 enhanced vs previous version
4. **Add More Data**: Implement order flow, options flow as available
5. **Refine Prompts**: Iterate based on real-world performance

