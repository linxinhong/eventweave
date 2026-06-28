"""Runtime plan model."""

from __future__ import annotations

from datetime import UTC, datetime

from pydantic import BaseModel, Field

from eventweave.core.entity import Entity
from eventweave.core.event import Event
from eventweave.core.relation import Relation
from eventweave.core.scenario import Scenario
from eventweave.core.source import Source


def _now_utc() -> datetime:
    return datetime.now(UTC)


class RuntimePlan(BaseModel):
    """Compiled, deterministic output of the Scenario Compiler."""

    scenario: Scenario
    entities: list[Entity] = Field(default_factory=list)
    relations: list[Relation] = Field(default_factory=list)
    events: list[Event] = Field(default_factory=list)
    sources: list[Source] = Field(default_factory=list)
    generated_at: datetime = Field(default_factory=_now_utc)
