"""Write runtime plan artifacts to disk."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from eventweave.core.runtime_plan import RuntimePlan


class PlanWriter:
    """Write a runtime plan to the standard dist layout."""

    def __init__(self, output_dir: str | Path) -> None:
        self.output_dir = Path(output_dir)

    def write(self, plan: RuntimePlan) -> dict[str, Path]:
        self.output_dir.mkdir(parents=True, exist_ok=True)
        written: dict[str, Path] = {}

        written["scenario"] = self._write_json("scenario.json", plan.scenario.model_dump())
        written["entities"] = self._write_json(
            "entities.json", [e.model_dump() for e in plan.entities]
        )
        written["relations"] = self._write_json(
            "relations.json", [r.model_dump(by_alias=True) for r in plan.relations]
        )
        written["sources"] = self._write_json(
            "sources.json", [s.model_dump() for s in plan.sources]
        )
        written["runtime_plan"] = self._write_json("runtime_plan.json", plan.model_dump())

        event_plan_path = self.output_dir / "event_plan.jsonl"
        with event_plan_path.open("w", encoding="utf-8") as f:
            for event in plan.events:
                f.write(json.dumps(event.model_dump(), default=str) + "\n")
        written["event_plan"] = event_plan_path

        return written

    def _write_json(self, filename: str, data: Any) -> Path:
        path = self.output_dir / filename
        with path.open("w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, default=str, ensure_ascii=False)
        return path
