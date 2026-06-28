"""Sink configuration model."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field


class Sink(BaseModel):
    """Output destination for event streams."""

    type: Literal["stdout", "jsonl", "csv", "http"] = Field(default="jsonl")
    path: str | None = None
    url: str | None = None
