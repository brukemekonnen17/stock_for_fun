# AAPL LLM v2 Analysis Output Example

This document shows the expected LLM v2 enhanced analysis output for AAPL stock with statistical analysis.

## Example Input Data

```json
{
  "ticker": "AAPL",
  "price": 192.50,
  "spread": 0.01,
  "volume_surge_ratio": 1.65,
  "pattern_detected": {
    "name": "Ascending Triangle",
    "confidence": 0.75,
    "side": "BULLISH"
  },
  "rsi14": 62.5,
  "adr20": 0.019,
  "atr14": 3.85,
  "expected_move_iv": 0.045,
  "evidence": {
    "event_study": {
      "significant": true,
      "car_summary": {
        "car": [
          {"day": 1, "mean": 0.015, "ci_low": 0.008, "ci_high": 0.022}
        ]
      }
    },
    "statistical_tests": {
      "volume_test": {
        "p_value": 0.02,
        "effect_size": 0.45,
        "significant": true
      }
    }
  }
}
```

## Expected LLM Output

```json
{
  "schema": "TradeAnalysisV2",
  "verdict_intraday": "BUY",
  "verdict_swing_1to5d": "BUY",
  "confidence": 0.82,
  
  "statistical_analysis": {
    "effect_sizes": {
      "volume_surge": "LARGE",
      "price_momentum": "MEDIUM",
      "iv_rv_gap": "MEDIUM",
      "sector_strength": "LARGE"
    },
    "significance": {
      "event_study_p": 0.015,
      "event_study_significant": true,
      "fdr_q": 0.02,
      "interpretation": "CAR significant at T+1 (p=0.015), survives FDR correction (q=0.02), large volume effect size (0.45)"
    },
    "confidence_intervals": {
      "car_t1_ci": [0.008, 0.022],
      "width_interpretation": "MODERATE"
    },
    "volatility_regime": {
      "iv_rv_interpretation": "IV exceeds RV by 2%, options pricing in larger moves, aligns with high volume surge",
      "volatility_trend": "INCREASING"
    },
    "time_horizon_analysis": {
      "intraday_setup": "ORB breakout candidate: price 75% of 10d range, high volume surge (1.65x), ADR 1.9% suggests intraday target +1.9%",
      "swing_setup": "Ascending triangle pattern (75% confidence) near completion, expected move 4.5% aligns with pattern projection",
      "long_term_context": "Sector relative strength +8% (LARGE effect) supports continuation"
    },
    "risk_reward": {
      "intraday_rr": 2.6,
      "swing_rr": 3.2,
      "explain": "Intraday: +1.9% target (ADR), -0.75% stop (ATR). Swing: +4.5% target (IV EM), -1.4% stop (pattern)"
    }
  },
  
  "room": {
    "intraday_room_up_pct": 0.019,
    "intraday_room_down_pct": 0.021,
    "swing_room_up_pct": 0.045,
    "swing_room_down_pct": 0.032,
    "explain": "Intraday: ADR 1.9% less current move. Swing: IV EM 4.5% or pattern extension"
  },
  
  "pattern": {
    "state": "BREAKOUT",
    "key_levels": {
      "support_1": 188.5,
      "resistance_1": 195.8
    },
    "signals": ["Price above EMA20", "RSI 62.5 (bullish but not overbought)"]
  },
  
  "participation": {
    "quality": "HIGH",
    "volume_surge_ratio": 1.65,
    "adv_change_pct": 0.0,
    "dollar_adv": 5000000000,
    "spread": 0.01,
    "explain": "Volume surge 1.65x (LARGE effect) indicates institutional participation"
  },
  
  "catalyst_alignment": {
    "event_type": "EARNINGS",
    "days_to_event": 7,
    "expected_move_iv": 0.045,
    "alignment": "SUPPORTS",
    "explain": "Event study significant (p=0.015), CAR +1.5% at T+1, aligns with earnings in 7 days"
  },
  
  "meme_social": {
    "is_meme_risk": false,
    "social_spike_ratio": 1.2,
    "bull_ratio": 0.58,
    "diagnosis": "CONFIRMING",
    "explain": "Social sentiment positive (0.58 bull ratio) but not extreme, confirms participation"
  },
  
  "plan": {
    "entry_type": "trigger",
    "entry_price": 192.8,
    "stop_price": 190.5,
    "targets": [196.4, 200.0],
    "timeout_days": 5,
    "rationale": "ORB breakout + statistical significance + pattern completion + earnings catalyst"
  },
  
  "risk": {
    "policy_pass": true,
    "reasons": ["Spread 1% within policy", "High participation quality"],
    "warnings": []
  },
  
  "evidence": {
    "summary": "CAR significant T+1, volume surge statistically significant (p=0.02)"
  },
  
  "evidence_fields": [
    "price_position_10d",
    "volume_surge_ratio",
    "pattern_detected",
    "evidence.event_study.significant",
    "evidence.statistical_tests.volume_test.p_value",
    "sector_relative_strength",
    "rsi14",
    "adr20",
    "atr14"
  ],
  
  "missing_fields": [],
  
  "assumptions": {
    "formulas": "room per spec",
    "volatility_assumption": "IV-RV gap stable"
  }
}
```

## Key Features Demonstrated

### 1. Statistical Analysis Section
- **Effect Sizes**: Classified as LARGE/MEDIUM/SMALL
- **Significance**: p-values, FDR correction, interpretation
- **Confidence Intervals**: CAR CI with width interpretation
- **Volatility Regime**: IV vs RV analysis
- **Time Horizon**: Separate intraday, swing, long-term analysis
- **Risk/Reward**: Calculated ratios for both timeframes

### 2. Time Horizon Analysis
- **Intraday**: ORB breakout setup with specific price targets
- **Swing**: Pattern completion with expected move
- **Long-term**: Sector context supporting continuation

### 3. Statistical Rigor
- **P-values**: Event study (0.015), volume test (0.02)
- **FDR Correction**: Survives multiple testing (q=0.02)
- **Effect Sizes**: Volume surge (0.45 = LARGE)
- **Confidence Intervals**: CAR T+1 [0.8%, 2.2%]

### 4. Risk/Reward Quantification
- **Intraday R:R**: 2.6 (1.9% target, 0.75% stop)
- **Swing R:R**: 3.2 (4.5% target, 1.4% stop)

## Interpretation

**Why BUY:**
1. **Statistical Significance**: Event study p=0.015, volume test p=0.02, both survive FDR
2. **Large Effect Sizes**: Volume surge (LARGE), sector strength (LARGE)
3. **Pattern Confirmation**: Ascending triangle (75% confidence) near completion
4. **High Participation**: Volume surge 1.65x indicates institutional flow
5. **Catalyst Alignment**: Earnings in 7 days, significant CAR expected

**Risk/Reward:**
- Intraday: 2.6:1 (target +1.9%, stop -0.75%)
- Swing: 3.2:1 (target +4.5%, stop -1.4%)

**Confidence: 0.82** - High confidence based on multiple confirming signals

## Usage

To see this output in action:

```bash
python show_aapl_llm_example.py
```

Or make an API call:

```bash
curl -X POST http://127.0.0.1:8000/decision/propose \
  -H "Content-Type: application/json" \
  -d '{
    "ticker": "AAPL",
    "price": 192.50,
    "spread": 0.01,
    "volume_surge_ratio": 1.65,
    ...
  }'
```

