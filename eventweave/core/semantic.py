"""Semantic task and asset models."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from pydantic import BaseModel, Field


class SemanticTaskSpec(BaseModel):
    """Inline semantic task specification on a timeline item."""

    type: str = Field(..., description="Semantic asset type, e.g. refund.reason.")
    inject: bool = Field(default=True, description="Whether to inject the asset into events.")
    prompt: str | None = Field(default=None, description="Optional custom prompt template.")
    variables: list[str] = Field(default_factory=list)
    review_status: str = Field(default="pending")


class SemanticTask(BaseModel):
    """A task that produces semantic assets for a scenario."""

    id: str
    type: str = Field(..., description="Semantic asset type.")
    description: str | None = None
    prompt: str | None = Field(default=None, description="Prompt template for LLM generation.")
    template: str | None = Field(
        default=None,
        description="Template-based generation without LLM.",
    )
    variables: list[str] = Field(default_factory=list)
    valid_for: list[str] = Field(
        default_factory=list,
        description="Event types that can use this asset.",
    )
    count: int = Field(default=1, ge=1)
    review_status: str = Field(default="pending")
    attributes: dict[str, Any] = Field(default_factory=dict)


class SemanticAssetMeta(BaseModel):
    """Metadata for a generated semantic asset."""

    provider: str | None = None
    prompt_id: str | None = None
    input_hash: str | None = None
    created_by: str = Field(default="system")
    quality_score: float | None = Field(default=None, ge=0, le=1)
    review_status: str = Field(default="approved")
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))


class SemanticAsset(BaseModel):
    """A validated semantic text asset ready for runtime injection."""

    id: str
    domain: str | None = None
    type: str = Field(..., description="Semantic asset type.")
    text: str
    valid_for: list[str] = Field(default_factory=list)
    variables: dict[str, Any] = Field(default_factory=dict)
    meta: SemanticAssetMeta = Field(default_factory=SemanticAssetMeta)


class SemanticPool(BaseModel):
    """Container for validated semantic assets."""

    scenario_id: str
    assets: list[SemanticAsset] = Field(default_factory=list)
    generated_at: datetime = Field(default_factory=lambda: datetime.now(UTC))

    def by_type(self, asset_type: str) -> list[SemanticAsset]:
        return [a for a in self.assets if a.type == asset_type]

    def by_valid_for(self, event_type: str) -> list[SemanticAsset]:
        return [a for a in self.assets if not a.valid_for or event_type in a.valid_for]
