"""Shared compiler exceptions."""

from __future__ import annotations


class CompileError(Exception):
    """Raised when a scenario cannot be compiled into a runtime plan."""
