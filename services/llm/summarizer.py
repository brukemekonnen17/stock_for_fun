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
PROMPT_VERSION = "2.0.0"  # Updated for hardline summarizer

# System prompt for summarization (HARDLINE - decisive, rule-driven)
SUMMARIZER_SYSTEM_PROMPT = """You are an execution-grade equities analyst. Output **valid JSON only** that conforms to the schema.

Be **decisive**: return a single verdict with explicit reasons and numbers.

Use **only** fields present in `analysis_contract`. **Never invent.**

If information is missing, **return SKIP** with a reason code.

All numbers must cite the **exact JSON path(s)** used.

### Policy (must apply, in order)

1. **Eligibility gates**
   * If `ticker` ≠ requested ticker → `verdict="SKIP"`, `reason_code="TICKER_MISMATCH"`.
   * If `economics.blocked == true` → `verdict="SKIP"`, `reason_code="ECON_VETO"`.
   * If `economics.net_median` is null or ≤ 0 → `verdict="SKIP"`, `reason_code="ECON_BLOCK"`.

2. **Statistical gate**
   * Compute set S = horizons in `evidence[]` with **q < 0.10** **and** `effect` (in bps) **≥ 30**.
   * Convert `effect` (decimal) to bps: `effect_bps = effect * 10000` if effect is not null.
   * If S is empty → `stats_significant=false`.

3. **Verdict**
   * **BUY** if `stats_significant=true` **and** `economics.net_median > 0` **and** `economics.blocked=false` **and** `plan.policy_ok=true`.
   * **REVIEW** if `stats_significant=true` but fails **one** of {net_median>0, blocked=false, policy_ok=true}.
   * **SKIP** otherwise.

4. **Best horizon selection (if S non-empty)**
   * Pick horizon with **lowest q**; tiebreakers: higher `effect_bps` → longer `H`.

5. **CI stability**
   * If `ci` is an array `[lower, upper]`, use it. If missing, set to null.
   * If contract has `ci_unstable` flag, label `ci.source="conservative"`.

6. **Language**
   * **Prohibited**: "might", "could", "appears", "potentially", "mixed", "unclear", "suggests".
   * Use: "BUY because…", "SKIP because…", "REVIEW because…".
   * Always list **exact numeric thresholds** and **paths**.

7. **Formatting**
   * Percentages: 1 decimal (e.g., `3.2%`). bps: integer. Prices: `$` + 2 decimals.
   * If a value is missing, set to `null` and add a **single-line** reason in `omissions[]`.

8. **Executive Summary Length**
   * **Minimum 150 words** (approximately 750+ characters) for BUY/REVIEW cases.
   * **Minimum 100 words** (approximately 400+ characters) for SKIP cases is acceptable.
   * Always be comprehensive and cite specific numbers with paths.

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
    
    user_prompt = f"""Summarize decisively per the policy. Use only the fields in `analysis_contract`. 

Return JSON only.

Requested ticker: {contract.get('ticker', 'UNKNOWN')}

analysis_contract:
{contract_str}

OUTPUT SCHEMA (strict):
{{
  "ticker": "string",
  "run_id": "string",
  "verdict": "BUY | REVIEW | SKIP",
  "reason_code": "string",
  "executive_summary": "string (150-250 words, decisive tone, minimum 100 characters)",
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
    {{ "point": "string", "paths": ["string"] }}
  ],
  "risks": [
    {{ "risk": "string", "paths": ["string"] }}
  ],
  "citations": ["string"],
  "omissions": ["string"]
}}

FIELD MAPPING:
- ticker, run_id, timestamp: contract root level
- evidence: contract.evidence[] (array with H, effect, ci, p, q)
- economics: contract.economics (net_median, net_p90, blocked)
- plan: contract.plan (entry_price, stop_price, target_price, risk_reward, policy_ok)
- drivers: contract.drivers (pattern, iv_rv, meme, sector_rs if present)
- risks: contract.risks[] (array of risk strings)

DECISION RULES:
1. Find horizons with q < 0.10 AND effect_bps ≥ 30 (effect * 10000)
2. If none → stats_significant=false, verdict=SKIP
3. BUY only if: stats_significant=true AND net_median>0 AND blocked=false AND policy_ok=true
4. REVIEW if: stats_significant=true but one gate fails
5. SKIP otherwise

CITE ALL NUMBERS with exact paths (e.g., "evidence[2].q", "economics.net_median")"""
    
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
        
        # Parse JSON response
        try:
            summary = json.loads(response_text)
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse LLM response as JSON: {e}")
            logger.error(f"Response text (first 1000 chars): {response_text[:1000]}")
            raise ValueError(f"LLM returned invalid JSON: {e}. Response preview: {response_text[:200]}")
        
        # Validate summary structure (v2 schema)
        required_summary_fields = ['ticker', 'run_id', 'verdict', 'reason_code', 'executive_summary', 'decision', 'action', 'rationale', 'risks']
        missing = [f for f in required_summary_fields if f not in summary]
        if missing:
            raise ValueError(f"Summary missing required fields: {missing}")
        
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

