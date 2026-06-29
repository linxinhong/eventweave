"""Write runtime plan artifacts to disk."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from eventweave.core.runtime_plan import RuntimePlan
from eventweave.core.semantic import SemanticTask


class PlanWriter:
    """Write a runtime plan to the standard dist layout."""

    def __init__(
        self,
        output_dir: str | Path,
        *,
        force: bool = False,
        allowed_root: str | Path | None = None,
    ) -> None:
        self.output_dir = Path(output_dir)
        self.force = force
        self.allowed_root = Path(allowed_root) if allowed_root is not None else None

    def _validate_output_dir(self) -> None:
        """Ensure the output directory is safe and writable."""
        output = self.output_dir.expanduser().resolve()

        if self.allowed_root is not None:
            root = self.allowed_root.expanduser().resolve()
            try:
                output.relative_to(root)
            except ValueError as exc:
                raise ValueError(
                    f"Output directory {output} is outside allowed root {root}"
                ) from exc

        if output.exists() and any(output.iterdir()) and not self.force:
            raise ValueError(
                f"Output directory {output} is not empty. Use --force to overwrite."
            )

    def write(
        self,
        plan: RuntimePlan,
        semantic_tasks: list[SemanticTask] | None = None,
    ) -> dict[str, Path]:
        self._validate_output_dir()
        self.output_dir.mkdir(parents=True, exist_ok=True)
        written: dict[str, Path] = {}

        written["scenario"] = self._write_json("scenario.json", plan.scenario.model_dump())
        if plan.scenario.ground_truth is not None:
            written["ground_truth"] = self._write_json(
                "ground_truth.json", plan.scenario.ground_truth.model_dump()
            )
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

        semantic_tasks = semantic_tasks or []
        written["semantic_tasks"] = self._write_json(
            "semantic_tasks.json",
            [t.model_dump() for t in semantic_tasks],
        )

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
