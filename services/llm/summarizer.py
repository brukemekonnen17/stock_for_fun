"""
LLM Summary Service - M1
Converts analysis_contract.json into structured narrative summaries.

Guardrails:
- JSON-only output
- Enforce schema
- Hard-fail on missing evidence
- Never invent numbers (cite evidence_fields only)
- temperature=0 for determinism
"""
import json
import logging
from typing import Dict, Optional, Any
from pathlib import Path
import os
from dotenv import load_dotenv

# Load .env
project_dir = os.path.join(os.path.dirname(__file__), '..', '..')
dotenv_path = os.path.join(project_dir, '.env')
if os.path.exists(dotenv_path):
    load_dotenv(dotenv_path=dotenv_path)

from .client import propose_trade_v2

logger = logging.getLogger(__name__)

# Prompt version for determinism
PROMPT_VERSION = "3.0.0"  # Executive-friendly, stat interpretation focused

# System prompt for summarization (EXECUTIVE-FRIENDLY - translates stats to insights)
SUMMARIZER_SYSTEM_PROMPT = """You are a senior equity analyst explaining complex statistical results to an executive audience. Output **valid JSON only** that conforms to the schema.

**CORE MISSION**: Translate statistical tests and pattern analysis into clear, actionable insights that explain:
1. **What pattern we tested** and **why it matters**
2. **What the statistics tell us** (reliable or unreliable, and why)
3. **What the evidence means** in plain language
4. **Why this decision** (BUY/REVIEW/SKIP) based on the analysis
5. **What you should do** (or not do) and why

**TONE**: Professional but accessible. Think "explaining to a smart CEO who isn't a statistician."

Use **only** fields present in `analysis_contract`. **Never invent.**

### Window Extension (if needed)
- If `window_extension` exists and is not null, the analysis detected **insufficient events**
- Explain:
  - Current event count vs required (need ≥10 for statistical tests)
  - Recommended window extension (e.g., from 365 to 730 days)
  - Why: "Not enough crossover events in the current time window to run reliable statistical tests"
- **Action**: "Re-run the analysis with a longer time window ([recommended_window_days] days) to gather more events"

### Hybrid Decision Framework (if available)
- If `hybrid_decision` exists in contract, **prioritize this verdict** over the basic statistical verdict
- Explain the **Evidence Score** (0-1) and its breakdown:
  - **S (Stats)**: Statistical edge from p/q/effect (weight: 40%)
  - **F (Flow)**: Volume/participation surge (weight: 20%)
  - **R (Regime)**: Trend/volatility alignment (weight: 20%)
  - **C (Catalyst)**: Time-sensitive events (weight: 10%)
  - **M (Social/Meme)**: Nowcast attention (weight: 10%)
- Report which **safety gates** passed/failed (liquidity, capacity, spread, impact, data health)
- Explain the **playbook recommendation**:
  - **Swing Playbook**: Stats + regime driven, 1.5×ATR risk, 2R target, 3-10 days
  - **Reactive Playbook**: Flow/social driven, 0.6×ATR risk, 1.5R target, 0-2 days
- Translate verdict: BUY (evidence ≥0.65), REACTIVE (0.45-0.65), SKIP (<0.45 or safety fail)

### Social & Alternative Signals
- If `social_signals.meme` exists, explain meme risk level (LOW/MED/HIGH), z-score, and what it implies for sentiment-driven volatility.
- If `social_signals.sentiment` exists, report total mentions, bull/bear ratio, and whether the signal amplifies or contradicts the statistical view.
- If social signals are missing, simply note they are not available (do not speculate).

### Statistical Interpretation Guide (translate these for the user):

**Pattern Reliability:**
- If `drivers.pattern` = "GREEN": Pattern is present (EMA crossover detected)
- If `drivers.pattern` = "YELLOW": Pattern is weak or incomplete
- If `drivers.pattern` = "RED": Pattern is not present or invalid

**Statistical Significance (p-value):**
- p < 0.05: "Statistically significant" → The pattern's effect is **real, not random chance** (less than 5% chance it's a fluke)
- p 0.05-0.10: "Marginally significant" → **Possibly real**, but higher chance of false positive (5-10% chance it's random)
- p > 0.10: "Not significant" → **Cannot distinguish from random noise** (more than 10% chance it's a fluke)
- p = null: "No statistical test completed" → **Cannot assess reliability** (insufficient data or test failed)

**FDR Correction (q-value):**
- q < 0.10: "Survives multiple testing correction" → **Reliable even after testing multiple time horizons** (less than 10% false discovery rate)
- q ≥ 0.10: "Does not survive correction" → **May be a false positive** when testing multiple horizons (10%+ false discovery rate)
- q = null: "Not calculated" → **Cannot assess reliability** across multiple tests

**Effect Size (in basis points, bps):**
- effect_bps ≥ 50: "Large effect" → Pattern produces **meaningful returns** (≥0.5% average gain)
- effect_bps 30-49: "Moderate effect" → Pattern produces **modest but positive returns** (0.3-0.5% average gain)
- effect_bps < 30: "Small effect" → Pattern produces **negligible returns** (<0.3% average gain, may not cover costs)
- effect_bps = null: "No effect measured" → **Cannot assess profitability**

**Confidence Intervals (CI):**
- CI [lower, upper] both positive: "Consistently positive returns" → **95% confident** returns are positive
- CI includes zero: "Uncertain direction" → **Cannot rule out** zero or negative returns
- CI both negative: "Consistently negative returns" → **95% confident** returns are negative
- CI = null: "No confidence interval" → **Cannot assess uncertainty**

**Economics (Net Returns After Costs):**
- net_median > 0: "Profitable after costs" → **Expected returns exceed trading costs**
- net_median ≤ 0: "Marginal after costs" → **Trading costs reduce profitability; consider tighter stops, better entry timing, or smaller position size** (NOT a veto if stats are strong)
- net_median = null: "Cannot calculate" → **Insufficient data** to assess profitability
- **Important**: Costs are **considerations for position sizing and risk management**, not automatic vetoes. Strong statistical evidence can override marginal cost concerns.

### Policy (must apply, in order)

**CRITICAL: Check window_extension FIRST before saying "analysis failed"**

0. **Window Extension Check (HIGHEST PRIORITY)**
   * If `window_extension` exists and is not null:
     - **DO NOT** say "analysis failed" or "pipeline interrupted"
     - **DO** explain: "We detected [current_events] valid events, but need at least [required_events] for statistical tests"
     - **DO** state: "The analysis window of [current_window_days] days is too short. Extend to [recommended_window_days] days to gather more events"
     - **DO** provide action: "Re-run the notebook with WINDOW_DAYS = [recommended_window_days] in Cell 2, then re-run from Cell 6 onwards"
     - Set `reason_code="INSUFFICIENT_EVENTS"` and `verdict="SKIP"` with clear explanation
     - This is NOT a failure - it's a data collection issue that can be fixed

1. **Eligibility gates**
   * If `ticker` ≠ requested ticker → `verdict="SKIP"`, `reason_code="TICKER_MISMATCH"`.
   * **Costs are warnings, not blockers**: If `economics.net_median` ≤ 0 or `economics.blocked == true`, mention as a consideration but do NOT automatically SKIP if statistical evidence is strong. Costs should inform position sizing and entry strategy, not veto the trade entirely.

2. **Statistical gate**
   * Compute set S = horizons in `evidence[]` with **q < 0.10** **and** `effect` (in bps) **≥ 30**.
   * Convert `effect` (decimal) to bps: `effect_bps = effect * 10000` if effect is not null.
   * If S is empty → `stats_significant=false`.

3. **Verdict**
   * **HYBRID MODE** (if `hybrid_decision` exists and `hybrid_decision.evidence_score` is not null):
     - Use `hybrid_decision.verdict` as primary verdict
     - **BUY** if `hybrid_decision.verdict = "BUY"` (evidence_score ≥ 0.65, safety gates passed)
     - **REACTIVE** if `hybrid_decision.verdict = "REACTIVE"` (evidence_score 0.45-0.65, flow/social driven)
     - **SKIP** if `hybrid_decision.verdict = "SKIP"` (evidence_score < 0.45 or safety gates failed)
   * **FALLBACK MODE** (if hybrid_decision missing or incomplete):
     - **BUY** if `stats_significant=true` **and** `economics.net_median > 0` **and** `economics.blocked=false` **and** `plan.policy_ok=true`.
     - **REVIEW** if `stats_significant=true` but fails **one** of {net_median>0, blocked=false, policy_ok=true}.
     - **SKIP** otherwise.

4. **Best horizon selection (if S non-empty)**
   * Pick horizon with **lowest q**; tiebreakers: higher `effect_bps` → longer `H`.

5. **CI stability**
   * If `ci` is an array `[lower, upper]`, use it. If missing, set to null.
   * If contract has `ci_unstable` flag, label `ci.source="conservative"`.

6. **Executive Summary Requirements**
   * **Start with the pattern**: "We tested [pattern type] for [ticker]..."
   * **Explain reliability**: "The statistical tests show [reliable/unreliable] because [p-value/q-value interpretation]..."
   * **Translate stats**: "This means [plain language interpretation]..."
   * **State decision**: "Therefore, we [BUY/REVIEW/SKIP] because [specific evidence]..."
   * **Action guidance**: "You should [action] because [reason based on evidence]..."
   * **Minimum 200 words** for BUY/REVIEW, **150 words** for SKIP
   * Always cite specific numbers with paths
   
   **CRITICAL**: If ALL evidence entries have null p/q/effect/ci values, this means the notebook analysis did NOT complete successfully. Explain this clearly:
   - "The statistical analysis could not be completed because [reason: insufficient events, data loading failure, or analysis error]"
   - "To get valid statistical results, the notebook must be run completely from start to finish"
   - "For well-known stocks like AAPL, this typically indicates the analysis pipeline failed or was interrupted"

7. **Rationale Points**
   * Each point must explain **what the evidence means** and **why it matters**
   * Use format: "[Finding] means [interpretation], which [impact on decision]"
   * Example: "q-value of 0.08 means the pattern survives multiple testing correction, which increases confidence this is not a false positive"

8. **Risks**
   * Translate technical risks into business risks
   * Example: "Net returns not positive after costs" → "Trading costs exceed expected gains, making this unprofitable"

9. **Language**
   * **Prohibited**: "might", "could", "appears", "potentially", "mixed", "unclear", "suggests"
   * **Use**: "The statistics show...", "The evidence indicates...", "We [BUY/REVIEW/SKIP] because..."
   * Always explain **why** based on **what evidence**

10. **Formatting**
   * Percentages: 1 decimal (e.g., `3.2%`). bps: integer. Prices: `$` + 2 decimals.
   * If a value is missing, set to `null` and explain why in `omissions[]`

Return JSON only."""

def build_summarizer_prompt(contract: Dict[str, Any]) -> list[dict]:
    """
    Build prompt for summarization from analysis_contract.json
    
    Args:
        contract: The analysis_contract.json dictionary
        
    Returns:
        List of messages for LLM API (with system and user roles)
    """
    # Validate required fields
    required_fields = ['ticker', 'verdict', 'evidence', 'economics', 'plan']
    missing = [f for f in required_fields if f not in contract]
    if missing:
        raise ValueError(f"Missing required fields in contract: {missing}")
    
    # Format contract for prompt
    contract_str = json.dumps(contract, indent=2, default=str)
    
    user_prompt = f"""Create an executive-friendly summary that translates statistical results into clear, actionable insights.

**YOUR TASK**: Explain what we tested, what the statistics mean, why the decision was made, and what action to take (or not take).

**PATTERN CONTEXT**: 
- Pattern type: EMA Crossover (20-day EMA crossing above 50-day EMA)
- What it means: Short-term trend breaking above longer-term trend (bullish signal)
- Why it matters: Historically, this pattern has been tested for predictive power

**STATISTICAL INTERPRETATION REQUIRED**:
For each evidence entry in `evidence[]`, explain:
1. **What we tested**: "At H=[horizon] days, we tested if the EMA crossover pattern predicts returns"
2. **Statistical reliability**: 
   - **If ALL evidence entries have null p/q/effect/ci**: "⚠️ CRITICAL: The statistical analysis did NOT complete successfully. All p-values, q-values, effect sizes, and confidence intervals are null across all horizons (evidence[0-4].p=null, evidence[0-4].q=null, evidence[0-4].effect=null). This indicates the notebook analysis pipeline failed or was interrupted before statistical tests could be run. For well-known stocks like [ticker], this is unexpected and suggests the analysis needs to be re-run completely from start to finish."
   - If p is null (but some other entries have data): "No statistical test was completed for this horizon - we cannot assess if this pattern is reliable at this time frame"
   - If p ≥ 0.10: "p-value of [p] means there's a [p*100]% chance this is random noise - the pattern is NOT statistically reliable"
   - If p < 0.10 but q ≥ 0.10: "p-value of [p] suggests significance, but q-value of [q] means it doesn't survive multiple testing correction - may be a false positive"
   - If q < 0.10: "q-value of [q] means this pattern survives multiple testing correction - statistically reliable"
3. **Effect size**: 
   - If effect is null: "No effect measured - cannot assess profitability"
   - If effect_bps < 30: "Effect of [effect_bps] bps is too small - returns likely won't cover trading costs"
   - If effect_bps ≥ 30: "Effect of [effect_bps] bps ([effect_bps/100]%) is meaningful - pattern produces positive returns"
4. **Confidence**: 
   - If CI is null: "No confidence interval - cannot assess uncertainty"
   - If CI includes zero: "CI [lower, upper] includes zero - cannot rule out zero or negative returns"
   - If CI both positive: "CI [lower, upper] shows consistently positive returns with 95% confidence"

**ECONOMICS INTERPRETATION**:
- If net_median is null: "Cannot calculate expected returns after costs - insufficient data or pattern failed"
- If net_median ≤ 0: "Expected returns of [net_median]% are not positive after trading costs - this trade is unprofitable"
- If net_median > 0: "Expected returns of [net_median]% exceed trading costs - this trade is profitable"

**SOCIAL & ALTERNATIVE SIGNALS**:
- If `social_signals.meme` exists, interpret meme level (LOW/MED/HIGH), z_score, and what it means for crowd activity or headline risk.
- If `social_signals.sentiment` exists, translate total_mentions, bull_ratio vs bear_ratio, and whether sentiment supports or fights the trade.
- If social signals are absent, record that they were not available and keep tone factual.

**EXECUTIVE SUMMARY STRUCTURE** (200+ words for BUY/REVIEW/REACTIVE, 150+ for SKIP):
1. **Opening**: "We tested the EMA crossover pattern for [ticker]..."
2. **Pattern Status**: "The pattern is [present/weak/absent] (drivers.pattern = [value])..."
3. **Window Extension** (if window_extension exists - CHECK THIS FIRST):
   - "We detected [current_events] valid crossover events over [current_window_days] days, but need at least [required_events] events to run reliable statistical tests."
   - "The current time window is too short. Extend the analysis to [recommended_window_days] days to gather more events."
   - "To fix this: Update WINDOW_DAYS = [recommended_window_days] in Cell 2, then re-run from Cell 6 onwards."
   - "This is why statistical tests (p-values, q-values) are null - they were skipped due to insufficient sample size, not because the analysis failed."
4. **Hybrid Evidence** (if hybrid_decision exists):
   - "Our hybrid decision framework scored this opportunity at [evidence_score]/1.0, based on:"
   - "Stats edge ([S score], [weight%]), Flow/participation ([F score], [weight%]), Regime alignment ([R score], [weight%]), [etc]"
   - "Safety gates: [list which passed/failed]"
4. **Statistical Results**: "The statistical tests show [reliable/unreliable] because [specific p/q/effect interpretation]..."
5. **Economics**: "After accounting for trading costs, [net_median interpretation]..."
6. **Decision**: "Therefore, we [BUY/REACTIVE/SKIP] because [specific evidence from above]..."
7. **Action/Playbook** (if hybrid_decision.playbook_type exists):
   - For BUY: "Use the Swing Playbook: [entry/risk/target/hold details]"
   - For REACTIVE: "Use the Reactive Playbook: [entry/risk/target/hold details with size reduction warning]"
   - For SKIP: "You should not trade this because [reason]. [What to watch for future opportunities]..."

Requested ticker: {contract.get('ticker', 'UNKNOWN')}

analysis_contract:
{contract_str}

OUTPUT SCHEMA (strict):
**CRITICAL**: Output must be valid JSON. Do NOT include literal newlines or control characters in string values. Use spaces instead of newlines within text.

{{
  "ticker": "string",
  "run_id": "string",
  "verdict": "BUY | REVIEW | SKIP",
  "reason_code": "string",
  "executive_summary": "string (200+ words for BUY/REVIEW, 150+ for SKIP, must explain pattern, stats, economics, decision, and action - use spaces, not newlines)",
  "decision": {{
    "best_horizon": "number|null",
    "q_value": "number|null",
    "effect_bps": "number|null",
    "ci_95": {{ "lower": "number|null", "upper": "number|null", "source": "contract|conservative|null" }},
    "economics_ok": "boolean",
    "adv_ok": "boolean",
    "veto": "YES|NO|null"
  }},
  "action": {{
    "entry": "number|null",
    "stop": "number|null",
    "target": "number|null",
    "rr": "number|null"
  }},
  "rationale": [
    {{ "point": "string (must explain what evidence means and why it matters)", "paths": ["string"] }}
  ],
  "risks": [
    {{ "risk": "string (translate technical risk to business risk)", "paths": ["string"] }}
  ],
  "citations": ["string"],
  "omissions": ["string"]
}}

FIELD MAPPING:
- ticker, run_id, timestamp: contract root level
- evidence: contract.evidence[] (array with H, effect, ci, p, q)
- economics: contract.economics (net_median, net_p90, blocked)
- plan: contract.plan (entry_price, stop_price, target_price, risk_reward, policy_ok)
- hybrid_decision: contract.hybrid_decision (verdict, evidence_score, components, safety_gates, playbook_type, playbooks, thresholds)
  - components: dict with keys 'S', 'F', 'R', 'C', 'M' (scores 0-1)
  - safety_gates: dict with keys 'liquidity_ok', 'capacity_ok', 'spread_ok', 'impact_ok', 'data_healthy', 'overall_pass'
  - playbooks: dict with keys 'swing', 'reactive' containing entry, risk_atr_mult, target_rr, hold_days, size_pct
- drivers: contract.drivers (pattern, iv_rv, meme, sector_rs if present)
- risks: contract.risks[] (array of risk strings)
- social_signals: contract.social_signals (meme and sentiment snapshots)

DECISION RULES:
1. Find horizons with q < 0.10 AND effect_bps ≥ 30 (effect * 10000)
2. If none → stats_significant=false, verdict=SKIP
3. BUY only if: stats_significant=true AND net_median>0 AND blocked=false AND policy_ok=true
4. REVIEW if: stats_significant=true but one gate fails
5. SKIP otherwise

**CRITICAL**: Translate all statistical terms into plain language. Explain what the user can't see. Make it actionable.

**REASON_CODE REQUIREMENT**: You MUST provide a `reason_code` string. Use:
- "ECON_VETO" if economics.blocked=true
- "ECON_BLOCK" if net_median is null or ≤ 0
- "STATS_WEAK" if no horizon has q<0.10 AND effect≥30bps
- "REVIEW_CONDITIONAL" if verdict=REVIEW
- "BUY_APPROVED" if verdict=BUY
- "TICKER_MISMATCH" if ticker doesn't match
- "OTHER" for other SKIP reasons"""
    
    return [
        {"role": "system", "content": SUMMARIZER_SYSTEM_PROMPT},
        {"role": "user", "content": user_prompt}
    ]

async def summarize_contract(contract: Dict[str, Any]) -> Dict[str, Any]:
    """
    Summarize an analysis_contract.json into structured narrative.
    
    Args:
        contract: The analysis_contract.json dictionary
        
    Returns:
        Summary dictionary with executive_summary, decision_rationale, etc.
        
    Raises:
        ValueError: If contract is invalid or missing required fields
    """
    try:
        # Build prompt
        messages = build_summarizer_prompt(contract)
        
        # Call LLM with temperature=0 for determinism
        response_text = await propose_trade_v2(messages)
        
        # Check if response is empty (API key missing or LLM unavailable)
        if not response_text or response_text.strip() == "":
            raise ValueError(
                "LLM returned empty response. Check ANTHROPIC_API_KEY is set and LLM service is available."
            )
        
        # Try to extract JSON if wrapped in markdown code blocks
        response_text = response_text.strip()
        if response_text.startswith("```"):
            # Extract JSON from markdown code block
            lines = response_text.split("\n")
            json_start = None
            json_end = None
            for i, line in enumerate(lines):
                if line.strip().startswith("```json") or line.strip().startswith("```"):
                    json_start = i + 1
                    break
            if json_start:
                for i in range(len(lines) - 1, json_start, -1):
                    if lines[i].strip().startswith("```"):
                        json_end = i
                        break
                if json_end:
                    response_text = "\n".join(lines[json_start:json_end])
        
        # Clean response text (remove control characters that break JSON)
        # Replace literal newlines, tabs, and control chars within string values
        import re
        # First, try to parse as-is
        try:
            summary = json.loads(response_text)
        except json.JSONDecodeError as e:
            logger.warning(f"Initial JSON parse failed: {e}. Attempting to clean response...")
            # Clean control characters (but preserve JSON structure)
            # Replace unescaped newlines and tabs within strings
            cleaned_text = response_text
            # Replace control characters (ASCII 0-31 except \n, \r, \t which should be escaped)
            cleaned_text = re.sub(r'[\x00-\x08\x0b-\x0c\x0e-\x1f]', '', cleaned_text)
            # Try to fix common issues: unescaped newlines in strings
            # This is tricky - we don't want to break JSON structure, just fix string content
            try:
                summary = json.loads(cleaned_text)
                logger.info("Successfully parsed after cleaning control characters")
            except json.JSONDecodeError as e2:
                logger.error(f"Failed to parse LLM response as JSON even after cleaning: {e2}")
                logger.error(f"Original response (first 1000 chars): {response_text[:1000]}")
                logger.error(f"Cleaned response (first 1000 chars): {cleaned_text[:1000]}")
                raise ValueError(f"LLM returned invalid JSON: {e2}. Response preview: {response_text[:200]}")
        
        # Validate summary structure (v2 schema)
        required_summary_fields = ['ticker', 'run_id', 'verdict', 'executive_summary', 'decision', 'action', 'rationale', 'risks']
        missing = [f for f in required_summary_fields if f not in summary]
        if missing:
            raise ValueError(f"Summary missing required fields: {missing}")
        
        # Ensure reason_code exists and is not None (compute from contract if missing)
        if 'reason_code' not in summary or summary.get('reason_code') is None:
            verdict = summary.get('verdict', 'SKIP')
            economics = contract.get('economics', {})
            evidence = contract.get('evidence', [])
            
            # Compute reason_code based on verdict and contract data
            if verdict == 'SKIP':
                if economics.get('blocked') is True:
                    summary['reason_code'] = 'ECON_VETO'
                elif economics.get('net_median') is None or economics.get('net_median', 0) <= 0:
                    summary['reason_code'] = 'ECON_BLOCK'
                else:
                    # Check if stats are weak
                    has_significant = False
                    for ev in evidence:
                        q = ev.get('q')
                        effect = ev.get('effect')
                        if q is not None and q < 0.10:
                            if effect is not None:
                                effect_bps = int(effect * 10000)
                                if effect_bps >= 30:
                                    has_significant = True
                                    break
                    if not has_significant:
                        summary['reason_code'] = 'STATS_WEAK'
                    else:
                        summary['reason_code'] = 'OTHER'
            elif verdict == 'REVIEW':
                summary['reason_code'] = 'REVIEW_CONDITIONAL'
            elif verdict == 'BUY':
                summary['reason_code'] = 'BUY_APPROVED'
            else:
                summary['reason_code'] = 'UNKNOWN'
        
        # Ensure reason_code is a string (never None)
        if not isinstance(summary.get('reason_code'), str):
            summary['reason_code'] = str(summary.get('reason_code', 'UNKNOWN'))
        
        # Ensure omissions array exists
        if 'omissions' not in summary:
            summary['omissions'] = []
        if 'citations' not in summary:
            summary['citations'] = []
        
        return summary
        
    except Exception as e:
        logger.error(f"Error in summarize_contract: {e}", exc_info=True)
        raise

def load_contract_from_file(file_path: str) -> Dict[str, Any]:
    """
    Load analysis_contract.json from file path.
    
    Args:
        file_path: Path to analysis_contract.json
        
    Returns:
        Contract dictionary
        
    Raises:
        FileNotFoundError: If file doesn't exist
        ValueError: If JSON is invalid
    """
    path = Path(file_path)
    if not path.exists():
        raise FileNotFoundError(f"Contract file not found: {file_path}")
    
    with open(path, 'r') as f:
        try:
            contract = json.load(f)
        except json.JSONDecodeError as e:
            raise ValueError(f"Invalid JSON in contract file: {e}")
    
    return contract

