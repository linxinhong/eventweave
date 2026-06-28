"""Resolve semantic_refs placeholders to concrete asset ids."""

from __future__ import annotations

from eventweave.core.event import Event
from eventweave.core.semantic import SemanticAsset, SemanticPool


class SemanticResolver:
    """Resolve event semantic_refs to concrete semantic asset ids."""

    def __init__(self, pool: SemanticPool) -> None:
        self.pool = pool
        self._index: dict[str, list[SemanticAsset]] | None = None

    def _build_index(self) -> dict[str, list[SemanticAsset]]:
        if self._index is None:
            index: dict[str, list[SemanticAsset]] = {}
            for asset in self.pool.assets:
                if asset.meta.source_event:
                    index.setdefault(asset.meta.source_event, []).append(asset)
            self._index = index
        return self._index

    def resolve_event(self, event: Event) -> Event:
        """Return a copy of the event with semantic_refs resolved to asset ids."""
        index = self._build_index()
        assets = index.get(event.event_id, [])
        refs = [asset.id for asset in assets]
        resolved = event.model_copy()
        resolved.semantic_refs = refs
        return resolved

    def resolve_events(self, events: list[Event]) -> list[Event]:
        """Resolve semantic_refs for all events."""
        return [self.resolve_event(event) for event in events]

    def stats(self, events: list[Event]) -> dict[str, int]:
        """Return resolution statistics."""
        resolved = 0
        unresolved = 0
        for event in events:
            if event.semantic_refs:
                if any(ref.startswith("semantic://") for ref in event.semantic_refs):
                    unresolved += 1
                else:
                    resolved += 1
        return {
            "resolved": resolved,
            "unresolved": unresolved,
            "total_assets": len(self.pool.assets),
        }
