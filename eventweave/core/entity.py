"""Domain-agnostic entity model."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from pydantic import BaseModel, Field


def _now_utc() -> datetime:
    return datetime.now(UTC)


class Entity(BaseModel):
    """An entity is any object that participates in a scenario."""

    id: str = Field(..., description="Globally unique entity identifier.")
    type: str = Field(..., description="Entity type, e.g. user, order, host.")
    domain: str | None = Field(
        default=None,
        description="Domain pack that defines this entity type.",
    )
    attributes: dict[str, Any] = Field(default_factory=dict)
    tags: list[str] = Field(default_factory=list)
    created_at: datetime = Field(default_factory=_now_utc)

    def ref(self) -> EntityRef:
        return EntityRef(id=self.id, type=self.type)


class EntityRef(BaseModel):
    """A lightweight reference to an entity."""

    id: str
    type: str

    def __str__(self) -> str:
        return f"{self.type}:{self.id}"
