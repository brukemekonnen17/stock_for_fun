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
PROMPT_VERSION = "1.0.0"

# System prompt for summarization
SUMMARIZER_SYSTEM_PROMPT = """You are a professional investment analyst writing executive summaries for trading decisions.

Your job is to convert structured analysis data into clear, concise narratives.

RULES (STRICT):
1. NEVER invent numbers - only cite values from the provided analysis_contract.json
2. If a required field is missing or null, state "Not available" or "Insufficient data"
3. Keep executive summary to 150-250 words
4. Decision rationale must map directly to evidence fields
5. Risks must come from the "risks" array in the contract
6. Action template must use exact values from "plan" object
7. Output MUST be valid JSON matching the schema exactly

You will receive an analysis_contract.json object. Extract and summarize:
- Executive Summary: Overall verdict, key drivers, statistical evidence
- Decision Rationale: Bullet points mapping to evidence fields (effect, CI, p, q)
- Risks & What to Watch: From risks array + economics.blocked status
- Action Template: Entry/stop/target from plan object

Be factual, concise, and cite specific numbers from the contract."""

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
    
    user_prompt = f"""Convert this analysis_contract.json into a structured summary.

ANALYSIS CONTRACT:
{contract_str}

OUTPUT SCHEMA:
{{
  "executive_summary": "150-250 word summary covering verdict, key drivers, statistical evidence",
  "decision_rationale": [
    "Bullet point 1 - cite specific evidence field (e.g., 'Effect at H=5: +X% with CI [Y, Z]')",
    "Bullet point 2 - reference drivers (pattern, sector_rs, etc.)",
    "Bullet point 3 - economics status (blocked/unblocked, net_median)"
  ],
  "risks_and_watch": [
    "Risk 1 from risks array",
    "Risk 2 from risks array",
    "Additional watch item based on economics or evidence gaps"
  ],
  "action_template": {{
    "entry_price": <from plan.entry_price>,
    "stop_price": <from plan.stop_price>,
    "target_price": <from plan.target_price>,
    "stop_pct": <from plan.stop_pct>,
    "target_pct": <from plan.target_pct>,
    "risk_reward": <from plan.risk_reward>,
    "policy_ok": <from plan.policy_ok>
  }},
  "metadata": {{
    "ticker": "{contract.get('ticker', 'UNKNOWN')}",
    "run_id": "{contract.get('run_id', 'unknown')}",
    "timestamp": "{contract.get('timestamp', '')}",
    "prompt_version": "{PROMPT_VERSION}"
  }}
}}

IMPORTANT:
- If evidence[].effect is null, state "Statistical evidence unavailable"
- If economics.blocked is true, emphasize capacity/viability concerns
- If plan.policy_ok is false, note policy guardrail failures
- Never invent numbers not in the contract
- If a field is null, say "Not available" rather than making up a value
- Output ONLY valid JSON, no markdown, no code blocks"""
    
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
        
        # Validate summary structure
        required_summary_fields = ['executive_summary', 'decision_rationale', 'risks_and_watch', 'action_template']
        missing = [f for f in required_summary_fields if f not in summary]
        if missing:
            raise ValueError(f"Summary missing required fields: {missing}")
        
        # Add metadata if not present
        if 'metadata' not in summary:
            summary['metadata'] = {
                'ticker': contract.get('ticker', 'UNKNOWN'),
                'run_id': contract.get('run_id', 'unknown'),
                'timestamp': contract.get('timestamp', ''),
                'prompt_version': PROMPT_VERSION
            }
        
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

