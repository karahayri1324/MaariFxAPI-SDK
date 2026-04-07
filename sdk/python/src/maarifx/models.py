"""MaariFx SDK data models."""

from __future__ import annotations

from typing import Any, Dict, Optional

from pydantic import BaseModel, Field


class Usage(BaseModel):
    """Token usage information."""

    input_tokens: int = 0
    output_tokens: int = 0
    cost_usd: Optional[float] = None


class SolveResult(BaseModel):
    """Result from a solve request."""

    request_id: str = Field(default="", alias="requestId")
    status: str = "completed"
    text: Optional[str] = None
    view_url: Optional[str] = None
    usage: Usage = Usage()
    subject: Optional[str] = None

    model_config = {"populate_by_name": True}


class StreamEvent(BaseModel):
    """A single server-sent event from a streaming solve request."""

    type: str
    token: Optional[str] = None
    text: Optional[str] = None
    view_url: Optional[str] = None
    request_id: Optional[str] = None
    message: Optional[str] = None
    usage: Optional[Usage] = None

    model_config = {"populate_by_name": True}


class SubUser(BaseModel):
    """A sub-user registered under an API key."""

    sub_user_id: str = ""
    external_id: str = ""
    token: Optional[str] = None
    display_name: Optional[str] = None
    daily_limit: Optional[int] = None

    model_config = {"populate_by_name": True}


class UsagePeriod(BaseModel):
    """Usage statistics for a time period."""

    requests: int = 0
    input_tokens: int = 0
    output_tokens: int = 0
    cost_usd: float = 0.0


class UsageStats(BaseModel):
    """Aggregated usage statistics."""

    today: UsagePeriod = UsagePeriod()
    this_month: UsagePeriod = UsagePeriod()
    limits: Dict[str, Any] = {}


class ViewResult(BaseModel):
    """Result from requesting a view URL."""

    view_url: str = ""
    expires_in: Optional[int] = None
    expires_at: Optional[str] = None
