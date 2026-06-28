"""Configuration for the generic AI chat provider."""

from __future__ import annotations

import os
from dataclasses import dataclass


class AIProviderError(Exception):
    """Raised when AI provider configuration is invalid."""


@dataclass
class AIProviderConfig:
    """Resolved configuration for a Chat Completions compatible endpoint."""

    base_url: str
    model: str
    api_key: str
    timeout: float = 30.0

    @classmethod
    def from_options(
        cls,
        base_url: str | None = None,
        model: str | None = None,
        api_key_env: str = "EVENTWEAVE_AI_API_KEY",
    ) -> AIProviderConfig:
        """Resolve config from CLI options and environment variables.

        Priority: CLI option > environment variable > error if missing.
        """
        resolved_base_url = base_url or os.getenv("EVENTWEAVE_AI_BASE_URL")
        if not resolved_base_url:
            raise AIProviderError(
                "missing AI base URL: set EVENTWEAVE_AI_BASE_URL or pass --base-url"
            )

        resolved_model = model or os.getenv("EVENTWEAVE_AI_MODEL")
        if not resolved_model:
            raise AIProviderError(
                "missing AI model: set EVENTWEAVE_AI_MODEL or pass --model"
            )

        api_key = os.getenv(api_key_env, "")
        if not api_key:
            raise AIProviderError(
                f"missing AI API key: set {api_key_env} or pass --api-key-env"
            )

        return cls(
            base_url=resolved_base_url.rstrip("/"),
            model=resolved_model,
            api_key=api_key,
        )
