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
    max_retries: int = 3
    max_tokens: int | None = None
    temperature: float | None = None

    @classmethod
    def from_options(
        cls,
        base_url: str | None = None,
        model: str | None = None,
        api_key_env: str = "EVENTWEAVE_AI_API_KEY",
        timeout: float | None = None,
        max_retries: int | None = None,
        max_tokens: int | None = None,
        temperature: float | None = None,
    ) -> AIProviderConfig:
        """Resolve config from CLI options and environment variables.

        Priority: CLI option > environment variable > default.
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

        api_key = os.environ.get(api_key_env)
        if api_key is None:
            raise AIProviderError(
                f"missing AI API key: set {api_key_env} or pass --api-key-env"
            )

        def _env_float(name: str, default: float) -> float:
            value = os.getenv(name)
            if value is None:
                return default
            try:
                return float(value)
            except ValueError as exc:
                raise AIProviderError(f"invalid {name}: {value}") from exc

        def _env_int(name: str, default: int | None) -> int | None:
            value = os.getenv(name)
            if value is None:
                return default
            try:
                return int(value)
            except ValueError as exc:
                raise AIProviderError(f"invalid {name}: {value}") from exc

        resolved_timeout = (
            timeout if timeout is not None else _env_float("EVENTWEAVE_AI_TIMEOUT", 30.0)
        )
        resolved_max_retries = (
            max_retries if max_retries is not None else _env_int("EVENTWEAVE_AI_MAX_RETRIES", 3)
        )
        resolved_max_tokens = (
            max_tokens if max_tokens is not None else _env_int("EVENTWEAVE_AI_MAX_TOKENS", None)
        )
        resolved_temperature = (
            temperature
            if temperature is not None
            else _env_float("EVENTWEAVE_AI_TEMPERATURE", 0.7)
            if "EVENTWEAVE_AI_TEMPERATURE" in os.environ
            else None
        )

        return cls(
            base_url=resolved_base_url.rstrip("/"),
            model=resolved_model,
            api_key=api_key,
            timeout=resolved_timeout,
            max_retries=resolved_max_retries or 0,
            max_tokens=resolved_max_tokens,
            temperature=resolved_temperature,
        )
