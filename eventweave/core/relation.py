"""Domain-agnostic relation model."""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field


class Relation(BaseModel):
    """A directed relation between two entities."""

    from_id: str = Field(..., alias="from", description="Source entity id.")
    to_id: str = Field(..., alias="to", description="Target entity id.")
    type: str = Field(..., description="Relation type, e.g. created, owns, triggers.")
    attributes: dict[str, Any] = Field(default_factory=dict)

    model_config = {"populate_by_name": True}
