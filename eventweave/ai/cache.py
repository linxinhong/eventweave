"""Simple file-based cache for semantic assets."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

from eventweave.core.semantic import SemanticAsset


class SemanticCache:
    """File-backed cache for generated semantic assets."""

    def __init__(self, cache_dir: str | Path) -> None:
        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(parents=True, exist_ok=True)

    @staticmethod
    def _file_name(key: str) -> str:
        """Return a deterministic, collision-resistant file name for a key."""
        digest = hashlib.sha256(key.encode("utf-8")).hexdigest()
        return f"{digest}.json"

    def _key_path(self, key: str) -> Path:
        return self.cache_dir / self._file_name(key)

    def get(self, key: str) -> SemanticAsset | None:
        path = self._key_path(key)
        if not path.exists():
            return None
        wrapper = json.loads(path.read_text(encoding="utf-8"))
        data = wrapper.get("asset") if isinstance(wrapper, dict) else wrapper
        return SemanticAsset.model_validate(data)

    def set(self, key: str, asset: SemanticAsset) -> None:
        path = self._key_path(key)
        wrapper = {
            "key": key,
            "asset": asset.model_dump(),
        }
        path.write_text(
            json.dumps(wrapper, ensure_ascii=False, default=str), encoding="utf-8"
        )

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
