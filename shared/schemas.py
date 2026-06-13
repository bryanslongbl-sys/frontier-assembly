"""Durable state schemas for the Frontier Assembly debate.

Everything an ephemeral Serverless Job needs lives in DebateState, which is
checkpointed to Object Storage after every turn. The job can die and be
restarted from the last snapshot with zero loss.
"""
from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Literal, Optional

from pydantic import BaseModel, Field

Role = Literal["architect", "critic", "synthesizer"]


def _now() -> datetime:
    return datetime.now(timezone.utc)


class UserRequest(BaseModel):
    concept: str = Field(min_length=8)
    target_audience: Optional[str] = None
    constraints: List[str] = Field(default_factory=list)
    max_rounds: int = Field(default=2, ge=1, le=6)


class AgentTurn(BaseModel):
    agent: Role
    provider: str
    model: str
    round: int
    content: str
    timestamp: datetime = Field(default_factory=_now)
    tokens_in: int = 0
    tokens_out: int = 0
    degraded: bool = False


class DebateState(BaseModel):
    schema_version: str = "1.0"
    job_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    request: UserRequest
    turns: List[AgentTurn] = Field(default_factory=list)
    status: Literal["init", "debating", "synthesized", "completed", "failed"] = "init"
    s3_brief_key: Optional[str] = None
    metrics: Dict[str, Any] = Field(default_factory=dict)
    created_at: datetime = Field(default_factory=_now)
    updated_at: datetime = Field(default_factory=_now)
