"""Simple file-based cache for semantic assets."""

from __future__ import annotations

import json
from pathlib import Path

from eventweave.core.semantic import SemanticAsset


class SemanticCache:
    """File-backed cache for generated semantic assets."""

    def __init__(self, cache_dir: str | Path) -> None:
        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(parents=True, exist_ok=True)

    def _key_path(self, key: str) -> Path:
        # Sanitize key for filesystem safety.
        safe = "".join(c if c.isalnum() or c in "-_" else "_" for c in key)
        return self.cache_dir / f"{safe}.json"

    def get(self, key: str) -> SemanticAsset | None:
        path = self._key_path(key)
        if not path.exists():
            return None
        data = json.loads(path.read_text(encoding="utf-8"))
        return SemanticAsset.model_validate(data)

    def set(self, key: str, asset: SemanticAsset) -> None:
        path = self._key_path(key)
        path.write_text(asset.model_dump_json(), encoding="utf-8")

    def has(self, key: str) -> bool:
        return self._key_path(key).exists()

    def clear(self) -> None:
        for path in self.cache_dir.glob("*.json"):
            path.unlink(missing_ok=True)

    def build_key(
        self,
        provider_type: str,
        scenario_id: str,
        task_id: str,
        event_id: str | None = None,
    ) -> str:
        parts = [provider_type, scenario_id, task_id]
        if event_id:
            parts.append(event_id)
        return "_".join(parts)
