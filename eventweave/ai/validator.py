"""Validation utilities for semantic assets."""

from __future__ import annotations

from eventweave.core.event import Event
from eventweave.core.semantic import SemanticAsset, SemanticTask


class ValidationError(Exception):
    """Raised when a semantic asset fails validation."""


class SemanticValidator:
    """Validate generated semantic assets against tasks and events."""

    def __init__(self, max_length: int = 4096) -> None:
        self.max_length = max_length

    def validate(
        self,
        asset: SemanticAsset,
        task: SemanticTask,
        event: Event | None = None,
    ) -> None:
        """Validate an asset. Raises ValidationError on failure."""
        if asset.type != task.type:
            raise ValidationError(
                f"Asset type {asset.type!r} does not match task type {task.type!r}"
            )

        if not asset.text or not asset.text.strip():
            raise ValidationError(f"Asset {asset.id!r} has empty text")

        if len(asset.text) > self.max_length:
            raise ValidationError(
                f"Asset {asset.id!r} text exceeds max length {self.max_length}"
            )

        if task.valid_for and event is not None and event.event_type not in task.valid_for:
            raise ValidationError(
                f"Asset {asset.id!r} not valid for event type {event.event_type!r}"
            )

    def is_valid(
        self,
        asset: SemanticAsset,
        task: SemanticTask,
        event: Event | None = None,
    ) -> bool:
        """Return True if the asset is valid."""
        try:
            self.validate(asset, task, event)
            return True
        except ValidationError:
            return False
