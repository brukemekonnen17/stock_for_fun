# services/config/flags.py
import os


def flag(name: str, default: bool = False) -> bool:
    v = os.getenv(name)
    if v is None:
        return default
    return str(v).strip().lower() in ("1", "true", "yes", "on")


def get_flags_snapshot():
    return {
        "SAFE_MODE": flag("SAFE_MODE", True),
        "ENABLE_LLM_PHASE1": flag("ENABLE_LLM_PHASE1", True),  # Enable LLM v2 for better analysis
        "ENABLE_EVENT_STUDY": flag("ENABLE_EVENT_STUDY", True),
    }

