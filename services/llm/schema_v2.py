"""
Enhanced LLM schema with evidence-first analysis and statistical reasoning.
"""
import json

LLM_SYSTEM_V2 = """You are a professional trading analyst. You DO NOT invent numbers. 

You must reason ONLY from the fields provided in the user JSON.

If any required number is missing, output a SKIP verdict with a clear reason.

Your job:

1) Determine if the stock has ROOM TO RUN (intraday and 1–5 day horizon).

2) Assess whether the current move is supported by PARTICIPATION (volume/liquidity), 
   consistent with PATTERN (levels/volatility), and aligned with CATALYST/SENTIMENT.

3) Return a structured JSON object STRICTLY matching the schema provided below.

4) Include a Plotly figure spec (valid JSON) that the frontend can render directly.

5) Keep reasoning concise, factual, and tied to the numeric inputs.

Key analysis rules (apply ALL):

- Pattern: Use recent_high_10d / recent_low_10d and price_position_10d to determine breakout, pullback, or range.

- Participation: Use volume_surge_ratio (5d/30d), adv_change_pct, dollar_adv, spread to judge "quality of demand."

- Catalyst alignment: Use event type + days_to_event + expected_move_iv (or proxy) and news_sentiment to support or temper conviction.

- Intraday playroom: Use adr20, atr14, open_range_* (first 30/60m), distance_to_resistance/support to estimate realistic targets.

- Meme/social: Use social_* fields to diagnose meme dynamics; treat sharp social_spike_ratio with caution if participation is low or liquidity is poor.

- Risk-first: If spread > max(spread_cents_max, price*spread_bps_max), or dollar_adv < min_dollar_adv, SKIP.

- Never output URLs that were not provided; never quote headlines not provided.

- Report effect sizes and uncertainty from the provided arrays/metrics; if a metric is missing, mark `assumptions.missing` and lower confidence.

Decision Logic Heuristics:

- Breakout, strong: price > recent_high_10d AND volume_surge_ratio ≥ 1.5 AND spread within policy → intraday verdict BUY unless catalyst contradicts.

- Breakout, weak: price > high but volume_surge_ratio < 1.2 → REACTIVE or SKIP; look for first pullback to ORB high.

- Range: 0.2 < price_position_10d < 0.8 → SKIP unless catalyst within 2d with EM≥4% and participation ≥1.3×.

- Meme diagnostics: social_spike_ratio ≥ 2.0 with LOW participation → label `meme_social.diagnosis = "NOISE"` and SKIP. If participation HIGH and spread tight, allow REACTIVE intraday only with small size.

Room Calculation Formulas:

- intraday_room_up_pct = max( distance_to_resistance_1, (adr20 - abs(open_to_current_pct)) )
- intraday_room_down_pct = distance_to_support_1
- swing_room_up_pct = max( expected_move_iv, (recent_high_10d - price)/price if below high else expected_move_iv )
- swing_room_down_pct = max( expected_move_iv * 0.6, distance_to_support_1 )

If any term is missing, reduce confidence and note the missing feature in `risk.warnings`.

Return ONLY JSON matching TradeAnalysisV2 schema. No prose outside JSON.
"""

LLM_USER_TEMPLATE_V2 = """{{
  "schema": "TradeAnalysisRequestV2",
  "ticker": "{ticker}",
  "asof_utc": "{asof_utc}",
  "price": {price},
  "spread": {spread},
  "dollar_adv": {dollar_adv},
  "adr20": {adr20},
  "atr14": {atr14},
  "recent_high_10d": {recent_high_10d},
  "recent_low_10d": {recent_low_10d},
  "price_position_10d": {price_position_10d},
  "distance_to_resistance_1": {distance_to_resistance_1},
  "distance_to_support_1": {distance_to_support_1},
  "ema20": {ema20},
  "ema50": {ema50},
  "rsi14": {rsi14},
  "bb_upper": {bb_upper},
  "bb_lower": {bb_lower},
  "volume_surge_ratio": {volume_surge_ratio},
  "adv_change_pct": {adv_change_pct},
  "open_range_high": {open_range_high},
  "open_range_low": {open_range_low},
  "open_range_minutes": {open_range_minutes},
  "expected_move_iv": {expected_move_iv},
  "rv_10d": {rv_10d},
  "iv_minus_rv": {iv_minus_rv},
  "event_type": "{event_type}",
  "days_to_event": {days_to_event},
  "materiality": {materiality},
  "news_sentiment": {news_sentiment},
  "social_mentions_24h": {social_mentions_24h},
  "social_bull_ratio": {social_bull_ratio},
  "social_spike_ratio": {social_spike_ratio},
  "meme_keywords": {meme_keywords},
  "regime": {regime},
  "policy_limits": {{
    "min_dollar_adv": {min_dollar_adv},
    "spread_cents_max": {spread_cents_max},
    "spread_bps_max": {spread_bps_max}
  }},
  "bandit": {{
    "selected_arm": "{selected_arm}",
    "calibrated_confidence": {calibrated_confidence}
  }},
  "historical_returns": {historical_returns},
  "historical_volumes": {historical_volumes},
  "historical_dates": {historical_dates}
}}"""

# Expected output schema (TradeAnalysisV2)
EXPECTED_OUTPUT_SCHEMA = {
    "schema": "TradeAnalysisV2",
    "verdict_intraday": "BUY|SELL|SKIP|REACTIVE",
    "verdict_swing_1to5d": "BUY|SELL|SKIP",
    "confidence": 0.0,
    "room": {
        "intraday_room_up_pct": 0.0,
        "intraday_room_down_pct": 0.0,
        "swing_room_up_pct": 0.0,
        "swing_room_down_pct": 0.0,
        "explain": "string"
    },
    "pattern": {
        "state": "BREAKOUT|PULLBACK|RANGE",
        "price_position_10d": 0.0,
        "key_levels": {"support_1": 0.0, "resistance_1": 0.0},
        "signals": ["string"]
    },
    "participation": {
        "volume_surge_ratio": 0.0,
        "adv_change_pct": 0.0,
        "dollar_adv": 0.0,
        "spread": 0.0,
        "quality": "HIGH|MEDIUM|LOW",
        "explain": "string"
    },
    "catalyst_alignment": {
        "event_type": "string",
        "days_to_event": 0,
        "expected_move_iv": 0.0,
        "alignment": "SUPPORTS|NEUTRAL|CONTRADICTS",
        "explain": "string"
    },
    "meme_social": {
        "is_meme_risk": True,
        "social_spike_ratio": 0.0,
        "bull_ratio": 0.0,
        "diagnosis": "CONFIRMING|DIVERGENT|NOISE",
        "explain": "string"
    },
    "plan": {
        "entry_type": "limit|market|trigger",
        "entry_price": 0.0,
        "stop_price": 0.0,
        "targets": [0.0, 0.0],
        "timeout_days": 1,
        "rationale": "string"
    },
    "risk": {
        "policy_pass": True,
        "reasons": ["string"],
        "warnings": ["string"]
    },
    "evidence": {
        "tests": [
            {
                "name": "mann_whitney_u | wilson_binomial | event_study | survival | granger",
                "hypothesis": "string",
                "effect_size": 0.0,
                "p_value": 0.0,
                "ci_low": 0.0,
                "ci_high": 0.0,
                "notes": "string"
            }
        ],
        "multiple_testing": {
            "method": "BH_FDR",
            "q_values": [{"test": "string", "q": 0.0}]
        },
        "calibration": {
            "ece": 0.0,
            "brier": 0.0
        },
        "assumptions": {
            "stationarity_checked": True,
            "normality_checked": False,
            "hac_correction": True,
            "missing": ["string"]
        }
    },
    "plotly_figure": {
        "schema": "PlotlyV1",
        "figure": {}
    }
}

