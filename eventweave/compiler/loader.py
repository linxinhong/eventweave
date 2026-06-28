"""Load scenario definitions from YAML/JSON files."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import yaml

from eventweave.core.scenario import Scenario


class ScenarioLoadError(Exception):
    """Raised when a scenario file cannot be loaded or parsed."""


SUPPORTED_EXTENSIONS = {".yaml", ".yml", ".json"}


def load_scenario(path: str | Path) -> Scenario:
    """Load a scenario from a YAML or JSON file.

    Args:
        path: Path to the scenario file.

    Returns:
        Parsed Scenario model.

    Raises:
        ScenarioLoadError: If the file is missing, has an unsupported extension,
            or cannot be parsed.
    """
    path = Path(path)
    if not path.exists():
        raise ScenarioLoadError(f"Scenario file not found: {path}")

    if path.suffix.lower() not in SUPPORTED_EXTENSIONS:
        raise ScenarioLoadError(
            f"Unsupported scenario file extension: {path.suffix}. "
            f"Supported: {', '.join(SUPPORTED_EXTENSIONS)}"
        )

    try:
        if path.suffix.lower() == ".json":
            with path.open("r", encoding="utf-8") as f:
                data: dict[str, Any] = json.load(f)
        else:
            with path.open("r", encoding="utf-8") as f:
                data = yaml.safe_load(f) or {}
    except Exception as exc:
        raise ScenarioLoadError(f"Failed to parse scenario file {path}: {exc}") from exc

    if not isinstance(data, dict):
        raise ScenarioLoadError(f"Scenario file {path} must contain a top-level mapping.")

    try:
        return Scenario.model_validate(data)
    except Exception as exc:
        raise ScenarioLoadError(f"Invalid scenario schema in {path}: {exc}") from exc
