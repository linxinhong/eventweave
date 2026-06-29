"""Abstract base class for semantic generation providers."""

from __future__ import annotations

import logging
import string
from abc import ABC, abstractmethod
from collections.abc import Mapping
from typing import Any

from eventweave.core.event import Event
from eventweave.core.scenario import Scenario
from eventweave.core.semantic import SemanticAsset, SemanticTask

logger = logging.getLogger("eventweave.ai")


class ProviderConfig:
    """Common configuration for a provider."""

    def __init__(self, provider_type: str, **kwargs: Any) -> None:
        self.provider_type = provider_type
        self.options = kwargs


class GenerationContext:
    """Context passed to a provider when generating a semantic asset."""

    def __init__(
        self,
        scenario: Scenario,
        task: SemanticTask,
        entities: dict[str, Any],
        event: Event | None = None,
    ) -> None:
        self.scenario = scenario
        self.task = task
        self.entities = entities
        self.event = event


class _DotFormatter(string.Formatter):
    """Formatter that resolves dotted keys like {user.name}."""

    def get_field(
        self, field_name: str, args: Any, kwargs: Mapping[str, Any]
    ) -> tuple[Any, str]:
        obj: Any = kwargs
        for part in field_name.split("."):
            obj = obj.get(part, "") if isinstance(obj, dict) else getattr(obj, part, "")
        return obj, field_name


class Provider(ABC):
    """Abstract base class for semantic asset generation providers."""

    def __init__(self, config: ProviderConfig | None = None) -> None:
        self.config = config or ProviderConfig(provider_type=self.provider_type)

    @property
    @abstractmethod
    def provider_type(self) -> str:
        """Return the provider type identifier."""

    @abstractmethod
    def generate(
        self,
        task: SemanticTask,
        context: GenerationContext,
    ) -> SemanticAsset:
        """Generate a semantic asset for the given task and context."""

    def _render_template(
        self,
        template: str | None,
        context: GenerationContext,
    ) -> tuple[str, bool]:
        """Simple template rendering using {variable} placeholders.

        Returns the rendered text and a boolean indicating whether rendering
        succeeded. On failure the original template is returned and a warning
        is logged so callers can mark the asset for review.
        """
        if not template:
            return "", True

        variables: dict[str, Any] = {
            "scenario_id": context.scenario.id,
            "domain": context.scenario.domain,
        }
        for role, entity in context.entities.items():
            if isinstance(entity, dict):
                entity_vars = dict(entity.get("attributes", {}))
                entity_vars["type"] = entity.get("type", "")
                entity_vars["id"] = entity.get("id", "")
                variables[role] = entity_vars
            else:
                entity_vars = dict(getattr(entity, "attributes", {}))
                entity_vars["type"] = getattr(entity, "type", "")
                entity_vars["id"] = getattr(entity, "id", "")
                variables[role] = entity_vars

        if context.event:
            variables["event_type"] = context.event.event_type
            for key, value in context.event.attributes.items():
                variables[f"event.{key}"] = value

        try:
            return _DotFormatter().format(template, **variables), True
        except (KeyError, ValueError) as exc:
            logger.warning(
                "Template render failed for task %s: %s. Returning raw template for review.",
                context.task.id if context.task else "unknown",
                exc,
            )
            return template, False
