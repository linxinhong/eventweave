"""Abstract base class for event sinks."""

from __future__ import annotations

from abc import ABC, abstractmethod

from eventweave.core.event import Event


class Sink(ABC):
    """Destination for emitted events."""

    @abstractmethod
    def open(self) -> None:
        """Open any resources needed by the sink."""

    @abstractmethod
    def write(self, event: Event) -> None:
        """Write a single event to the sink."""

    @abstractmethod
    def close(self) -> None:
        """Close any resources used by the sink."""

    @abstractmethod
    def flush(self) -> None:
        """Flush buffered output."""

    @abstractmethod
    def count(self) -> int:
        """Return the number of events written."""
