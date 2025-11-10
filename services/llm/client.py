import httpx, os, json
import logging
import asyncio
from typing import Optional

# Explicitly load .env before any other code runs
from dotenv import load_dotenv
project_dir = os.path.join(os.path.dirname(__file__), '..', '..')
dotenv_path = os.path.join(project_dir, '.env')
if os.path.exists(dotenv_path):
    load_dotenv(dotenv_path=dotenv_path)

from .schema import LLM_SYSTEM, LLM_USER_TEMPLATE

logger = logging.getLogger(__name__)

# --- Updated for Anthropic Claude ---
API_URL = "https://api.anthropic.com/v1/messages"
API_KEY = os.getenv("ANTHROPIC_API_KEY")
# Strip quotes if present (some .env files have quotes around values)
if API_KEY:
    API_KEY = API_KEY.strip('"').strip("'")
# Try haiku first (known to work), can upgrade to sonnet later
MODEL_NAME = "claude-3-haiku-20240307" # Using Haiku (fast, reliable)
MAX_RETRIES = int(os.getenv("LLM_MAX_RETRIES", "2"))

# Debug logging for API key (first/last chars only for security)
if API_KEY:
    logger.info(f"ANTHROPIC_API_KEY loaded (length: {len(API_KEY)}, starts: {API_KEY[:10]}...)")
else:
    logger.error("ANTHROPIC_API_KEY not found in environment")

# Import policy constants for LLM template
from services.policy.validators import (
    MAX_TICKET, MAX_PER_TRADE_LOSS, SPREAD_CENTS_MAX, SPREAD_BPS_MAX
)

def _mock_plan(ticker: str, price: float, reason: str = "LLM unavailable - generated mock plan") -> dict:
    """Generate a mock trade plan when LLM fails."""
    return {
        "action": "SKIP",
        "ticker": ticker,
        "entry_type": "limit",
        "entry_price": price * 0.995,
        "stop_price": price * 0.98,
        "target_price": price * 1.03,
        "timeout_days": 5,
        "confidence": 0.5,
        "reason": reason
    }

async def propose_trade_v2(messages: list[dict]) -> str:
    """
    Ask Anthropic Claude for a trade analysis (Phase-1 LLM layer).
    Returns raw JSON string for strict parsing.
    
    Note: Claude Messages API requires system prompt as top-level parameter,
    not as a message role.
    """
    if not API_KEY:
        logger.error("ANTHROPIC_API_KEY not found in environment.")
        return ""

    # Extract system prompt and user message from messages array
    system_prompt = ""
    user_message = None
    
    for msg in messages:
        if msg.get("role") == "system":
            system_prompt = msg.get("content", "")
        elif msg.get("role") == "user":
            user_message = msg
    
    if not user_message:
        logger.error("No user message found in messages array")
        return ""
    
    headers = {
        "x-api-key": API_KEY,
        "anthropic-version": "2023-06-01",
        "content-type": "application/json"
    }
    
    # Claude Messages API format: system is top-level, messages only contains user/assistant
    # Haiku max_tokens: 4096, Sonnet/Opus: 8192
    max_tokens_limit = 4096 if "haiku" in MODEL_NAME.lower() else 8192
    body = {
        "model": MODEL_NAME,
        "messages": [user_message],  # Only user/assistant messages
        "max_tokens": max_tokens_limit,
        "temperature": 0.0  # Deterministic for summarization
    }
    
    # Add system prompt as top-level parameter if present
    if system_prompt:
        body["system"] = system_prompt

    for attempt in range(MAX_RETRIES + 1):
        try:
            timeout = httpx.Timeout(60.0, connect=10.0)  # Increased timeout for Sonnet's detailed responses
            async with httpx.AsyncClient(timeout=timeout) as client:
                r = await client.post(API_URL, headers=headers, json=body)
                r.raise_for_status()
                
                response_data = r.json()
                text = response_data.get("content", [{}])[0].get("text", "")
                
                if not text:
                    raise ValueError("LLM response was empty.")
                
                logger.info(f"Claude Phase-1 response received ({len(text)} chars)")
                return text
                
        except httpx.TimeoutException:
            logger.warning(f"Claude timeout on attempt {attempt + 1}/{MAX_RETRIES + 1}")
            if attempt < MAX_RETRIES:
                await asyncio.sleep(0.5 * (2 ** attempt))
                
        except httpx.HTTPStatusError as e:
            error_details = e.response.text
            logger.error(f"Claude HTTP error {e.response.status_code}: {error_details}")
            if 400 <= e.response.status_code < 500:
                return ""
            if attempt < MAX_RETRIES:
                await asyncio.sleep(0.5 * (2 ** attempt))
            else:
                return ""
                
        except Exception as e:
            logger.error(f"Unexpected LLM error: {e}", exc_info=True)
            if attempt < MAX_RETRIES:
                await asyncio.sleep(0.5 * (2 ** attempt))
            else:
                return ""
    
    logger.warning(f"LLM failed after {MAX_RETRIES + 1} attempts")
    return ""


async def propose_trade(payload: dict) -> dict:
    """
    Ask Anthropic Claude for a trade plan.
    """
    if not API_KEY:
        logger.error("ANTHROPIC_API_KEY not found in environment.")
        return _mock_plan(payload.get("ticker", "UNKNOWN"), payload.get("price", 100), "ANTHROPIC_API_KEY not configured")

    template_payload = payload.copy()
    template_payload.update({
        "MAX_TICKET": MAX_TICKET,
        "MAX_PER_TRADE_LOSS": MAX_PER_TRADE_LOSS,
        "SPREAD_CENTS_MAX": SPREAD_CENTS_MAX,
        "SPREAD_BPS_MAX": SPREAD_BPS_MAX,
        "rank_components": json.dumps(payload.get("rank_components", {})),
        "backtest_kpis": json.dumps(payload.get("backtest_kpis", {})),
        "market_context": payload.get("market_context", json.dumps({})),
        "social_sentiment": payload.get("social_sentiment", json.dumps({})),
    })

    try:
        user_prompt = LLM_USER_TEMPLATE.format(**template_payload)
    except (KeyError, ValueError) as e:
        logger.error(f"Template formatting error: {e}")
        return _mock_plan(payload.get("ticker", "UNKNOWN"), payload.get("price", 100))

    headers = {
        "x-api-key": API_KEY,
        "anthropic-version": "2023-06-01",
        "content-type": "application/json"
    }
    body = {
        "model": MODEL_NAME,
        "system": LLM_SYSTEM,
        "messages": [{"role": "user", "content": user_prompt}],
        "max_tokens": 1024,
        "temperature": 0.2
    }

    for attempt in range(MAX_RETRIES + 1):
        try:
            timeout = httpx.Timeout(30.0, connect=10.0) # 30s timeout is plenty for Claude
            async with httpx.AsyncClient(timeout=timeout) as client:
                r = await client.post(API_URL, headers=headers, json=body)
                r.raise_for_status()
                
                response_data = r.json()
                text = response_data.get("content", [{}])[0].get("text", "")
                
                if not text:
                    raise ValueError("LLM response was empty.")

                plan = json.loads(text)
                
                required_keys = {"ticker", "action", "entry_type", "entry_price", "stop_price", 
                               "target_price", "timeout_days", "confidence", "reason"}
                if not required_keys.issubset(plan.keys()):
                    raise ValueError(f"LLM response missing keys: {required_keys - plan.keys()}")
                
                logger.info(f"Claude plan generated for {plan.get('ticker')} with confidence {plan.get('confidence')}")
                return plan
                
        except httpx.TimeoutException:
            logger.warning(f"Claude timeout on attempt {attempt + 1}/{MAX_RETRIES + 1}")
            if attempt < MAX_RETRIES:
                await asyncio.sleep(0.5 * (2 ** attempt))
                
        except httpx.HTTPStatusError as e:
            error_details = e.response.text
            logger.error(f"Claude HTTP error {e.response.status_code}: {error_details}")
            # No retry on auth errors or bad requests
            if 400 <= e.response.status_code < 500:
                return _mock_plan(payload.get("ticker", "UNKNOWN"), payload.get("price", 100), f"Claude API Error: {error_details}")
            if attempt < MAX_RETRIES:
                await asyncio.sleep(0.5 * (2 ** attempt))
            else:
                return _mock_plan(payload.get("ticker", "UNKNOWN"), payload.get("price", 100), "Claude API server error after retries")
                
        except (json.JSONDecodeError, KeyError, ValueError) as e:
            logger.error(f"Claude response parsing error: {e}. Raw text: '{text}'")
            return _mock_plan(payload.get("ticker", "UNKNOWN"), payload.get("price", 100), "Failed to parse LLM JSON response")
            
        except Exception as e:
            logger.error(f"Unexpected LLM error: {e}", exc_info=True)
            break
    
    logger.warning(f"LLM failed after {MAX_RETRIES + 1} attempts, using mock plan")
    return _mock_plan(payload.get("ticker", "UNKNOWN"), payload.get("price", 100))

