"""Scenario model."""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field

from eventweave.core.ground_truth import GroundTruth
from eventweave.core.jitter import JitterConfig
from eventweave.core.noise import NoiseConfig
from eventweave.core.semantic import SemanticTask
from eventweave.core.source import Source
from eventweave.core.timeline import TimelineItem


class EntityTemplate(BaseModel):
    """Template for generating entity instances."""

    count: int = Field(default=1, ge=0)
    type: str | None = None
    attributes: dict[str, Any] = Field(default_factory=dict)
    tags: list[str] = Field(default_factory=list)


class Scenario(BaseModel):
    """A scenario definition."""

    id: str
    name: str | None = None
    domain: str
    version: str = Field(default="1.0")
    duration: str = Field(default="1h")
    seed: int | None = None
    for_each: str | None = Field(
        default=None,
        description="Primary entity type that defines a flow. "
        "If unset, inferred from the first timeline event type.",
    )
    entities: dict[str, EntityTemplate] = Field(default_factory=dict)
    sources: list[Source] = Field(default_factory=list)
    timeline: list[TimelineItem] = Field(default_factory=list)
    semantic_tasks: list[SemanticTask] = Field(default_factory=list)
    rules: list[str | dict[str, Any]] = Field(default_factory=list)
    ground_truth: GroundTruth | None = None
    noise: NoiseConfig | None = None
    jitter: JitterConfig | None = None
