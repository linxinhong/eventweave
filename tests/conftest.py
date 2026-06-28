"""Shared pytest fixtures."""

from __future__ import annotations

from pathlib import Path

import pytest


@pytest.fixture
def project_root() -> Path:
    return Path(__file__).parent.parent


@pytest.fixture
def packs_dir(project_root: Path) -> Path:
    return project_root / "packs"
