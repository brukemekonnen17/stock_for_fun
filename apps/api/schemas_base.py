"""
Base model with strict validation - no extra fields allowed.
"""
from pydantic import BaseModel

class StrictModel(BaseModel):
    """Base model that forbids extra fields for strict API contracts"""
    model_config = {"extra": "forbid"}

