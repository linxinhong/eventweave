"""Base types for vendor/log encoders."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any, ClassVar

from pydantic import BaseModel, Field

from eventweave.core.event import Event


class EncodeResult(BaseModel):
    """Result of encoding a single canonical event."""

    success: bool = Field(..., description="Whether encoding succeeded.")
    output: str = Field(default="", description="Encoded output when successful.")
    error_reason: str | None = Field(
        default=None,
        description="Machine-readable reason when encoding failed.",
    )


class EncodeError(Exception):
    """Raised when an event cannot be encoded to the target format."""

    def __init__(self, reason: str) -> None:
        super().__init__(reason)
        self.reason = reason


class Encoder(ABC):
    """Transform a canonical EventWeave event into a vendor/log format."""

    name: str
    content_type: str
    description: ClassVar[str] = ""
    required_fields: ClassVar[list[str]] = []
    optional_fields: ClassVar[list[str]] = []
    supported_event_types: ClassVar[list[str]] = []

    @abstractmethod
    def encode(self, event: Event) -> EncodeResult:
        """Encode one event.

        Must not mutate *event*.
        """

    def get_info(self) -> dict[str, Any]:
        """Return encoder metadata for inspection and documentation."""
        return {
            "name": self.name,
            "content_type": self.content_type,
            "description": self.description,
            "required_fields": list(self.required_fields),
            "optional_fields": list(self.optional_fields),
            "supported_event_types": list(self.supported_event_types),
        }

    def _ok(self, output: str) -> EncodeResult:
        return EncodeResult(success=True, output=output)

    def _fail(self, reason: str) -> EncodeResult:
        return EncodeResult(success=False, error_reason=reason)
