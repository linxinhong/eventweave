"""Source configuration model."""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field


class RatePolicy(BaseModel):
    """Rate control for a simulated source."""

    base_qps: float = Field(default=1.0, ge=0)
    burst_qps: float | None = Field(default=None, ge=0)
    jitter: float = Field(default=0.0, ge=0, le=1)


class TimePolicy(BaseModel):
    """Time behavior configuration for a source."""

    mode: str = Field(default="realtime")
    late_arrival_ratio: float = Field(default=0.0, ge=0, le=1)
    out_of_order_ratio: float = Field(default=0.0, ge=0, le=1)


class Source(BaseModel):
    """A simulated event source."""

    id: str
    type: str
    domain: str | None = None
    role: str | None = None
    rate: RatePolicy = Field(default_factory=RatePolicy)
    time_policy: TimePolicy = Field(default_factory=TimePolicy)
    outputs: list[dict[str, Any]] = Field(default_factory=list)
