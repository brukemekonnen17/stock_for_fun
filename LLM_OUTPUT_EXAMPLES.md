# LLM Output Examples

This document shows real examples of LLM outputs from the system.

## LLM v1 (Legacy) Output

The legacy LLM returns a simple trade plan structure:

```json
{
  "ticker": "AAPL",
  "action": "SKIP",
  "entry_type": "limit",
  "entry_price": 191.7875,
  "stop_price": 188.65,
  "target_price": 198.075,
  "timeout_days": 5,
  "confidence": 0.5,
  "reason": "SKIP: Spread of 0.01 is within constraints, but volume surge ratio of 1.0 is below 1.2 threshold and no technical pattern detected. Require confirmation of volume surge and technical pattern.",
  "missing_fields": []
}
```

### Fields:
- **ticker**: Stock symbol
- **action**: "BUY", "SELL", or "SKIP"
- **entry_type**: "limit", "market", or "trigger"
- **entry_price**: Entry price for the trade
- **stop_price**: Stop loss price
- **target_price**: Target price
- **timeout_days**: Days until trade expires
- **confidence**: Confidence score (0.5-1.0)
- **reason**: Detailed explanation of the decision
- **missing_fields**: List of missing input fields (if any)

---

## LLM v2 (Phase-1) Output

The new Phase-1 LLM returns a more detailed analysis structure:

```json
{
  "schema": "TradeAnalysisV2",
  "verdict_intraday": "BUY",
  "verdict_swing_1to5d": "BUY",
  "confidence": 0.75,
  "room": {
    "intraday_room_up_pct": 0.013,
    "intraday_room_down_pct": 0.008,
    "swing_room_up_pct": 0.045,
    "swing_room_down_pct": 0.03,
    "explain": "IV EM & distance to resistance"
  },
  "pattern": {
    "state": "BREAKOUT",
    "key_levels": {
      "support_1": 188.0,
      "resistance_1": 195.0
    }
  },
  "participation": {
    "quality": "HIGH",
    "volume_surge_ratio": 1.5
  },
  "catalyst_alignment": {
    "alignment": "SUPPORTS"
  },
  "meme_social": {
    "diagnosis": "CONFIRMING"
  },
  "plan": {
    "entry_type": "trigger",
    "entry_price": 192.6,
    "stop_price": 190.8,
    "targets": [196.0, 197.5],
    "timeout_days": 1,
    "rationale": "Breakout + participation"
  },
  "risk": {
    "policy_pass": true,
    "reasons": ["Spread within policy"]
  },
  "evidence": {
    "summary": "CAR sig T+1"
  },
  "evidence_fields": [
    "spread",
    "policy_limits",
    "recent_high_10d",
    "volume_surge_ratio",
    "pattern_detected",
    "evidence.event_study.significant"
  ],
  "missing_fields": [],
  "assumptions": {
    "formulas": "room per spec"
  }
}
```

### Key Differences from v1:

1. **Dual Verdicts**: Separate verdicts for intraday and swing (1-5 day) trades
2. **Room Analysis**: Calculated upside/downside room for both timeframes
3. **Pattern Detection**: Detailed pattern state and key levels
4. **Participation Quality**: Assessment of volume and liquidity
5. **Catalyst Alignment**: How the event aligns with the trade
6. **Meme/Social Analysis**: Social sentiment diagnostics
7. **Multiple Targets**: Array of target prices
8. **Evidence Tracking**: Lists which input fields were used
9. **Risk Assessment**: Policy compliance and warnings

---

## Example: SKIP Action (v1)

When the LLM decides to skip a trade, it still returns all required fields:

```json
{
  "ticker": "AAPL",
  "action": "SKIP",
  "entry_type": "limit",
  "entry_price": 191.5375,
  "stop_price": 188.65,
  "target_price": 198.275,
  "timeout_days": 5,
  "confidence": 0.5,
  "reason": "SKIP: Missing required fields [pattern_detected, volume, volume_surge_ratio]. Insufficient data for trade analysis.",
  "missing_fields": ["pattern_detected", "volume", "volume_surge_ratio"]
}
```

**Note**: Even when skipping, all required fields are provided with safe default values.

---

## Example: SKIP Action (v2)

```json
{
  "schema": "TradeAnalysisV2",
  "verdict_intraday": "SKIP",
  "verdict_swing_1to5d": "SKIP",
  "confidence": 0.5,
  "room": {
    "intraday_room_up_pct": 0.0,
    "intraday_room_down_pct": 0.0,
    "swing_room_up_pct": 0.0,
    "swing_room_down_pct": 0.0,
    "explain": "Spread violation"
  },
  "pattern": {
    "state": "RANGE"
  },
  "participation": {
    "quality": "LOW"
  },
  "catalyst_alignment": {
    "alignment": "NEUTRAL"
  },
  "meme_social": {
    "diagnosis": "NOISE"
  },
  "plan": {
    "entry_type": "limit",
    "entry_price": 20.0,
    "stop_price": 19.8,
    "targets": [],
    "timeout_days": 1,
    "rationale": "N/A"
  },
  "risk": {
    "policy_pass": false,
    "warnings": ["Spread too wide"]
  },
  "evidence": {},
  "evidence_fields": ["spread", "policy_limits"],
  "missing_fields": [],
  "assumptions": {
    "policy_override": true
  }
}
```

---

## Testing LLM Output

To see live LLM output examples, run:

```bash
python show_llm_output.py
```

This will show:
1. Input payload sent to the LLM
2. Raw JSON response from the LLM
3. Parsed and validated response

---

## Common Issues

### Missing Required Fields

If the LLM omits required fields, the response will be rejected and fall back to a mock plan. The fixed prompt now ensures all fields are always included.

### JSON Parsing Errors

The parser handles:
- Code fences (```json ... ```)
- Trailing commas
- Common formatting issues

If parsing fails, the error is classified and logged for analysis.

---

## Version Information

All LLM responses include version metadata:
- **Model**: `claude-3-haiku-20240307`
- **Schema**: `2.0.0` (v2) or legacy format (v1)
- **Prompt**: `1.1.0`
- **Validator**: `1.1.0`

