from typing import Literal
from pydantic import BaseModel, ConfigDict, Field


class Policy(BaseModel):
    model_config = ConfigDict(extra="forbid")
    max_payment_days: int = Field(default=60, ge=1, le=365)
    max_breach_hours: int = Field(default=72, ge=1, le=720)
    min_uptime_percent: float = Field(default=99.5, ge=90, le=100)
    require_termination: bool = True
    require_audit: bool = True


class DocumentInput(BaseModel):
    model_config = ConfigDict(extra="forbid")
    title: str = Field(min_length=1, max_length=120)
    text: str = Field(min_length=30, max_length=50000)
    policy: Policy = Field(default_factory=Policy)


class ReviewInput(BaseModel):
    model_config = ConfigDict(extra="forbid")
    decision: Literal["approved", "changes_requested", "rejected"]
    reviewer: str = Field(min_length=2, max_length=60)
    note: str = Field(min_length=5, max_length=1000)
    expected_version: int = Field(ge=1)
