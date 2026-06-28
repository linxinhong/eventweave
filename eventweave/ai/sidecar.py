"""Semantic sidecar orchestrates LLM/template generation for a scenario."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from eventweave.ai.cache import SemanticCache
from eventweave.ai.mock_provider import MockProvider
from eventweave.ai.provider import GenerationContext, Provider, ProviderConfig
from eventweave.ai.template_provider import TemplateProvider
from eventweave.ai.validator import SemanticValidator
from eventweave.core.event import Event
from eventweave.core.scenario import Scenario
from eventweave.core.semantic import SemanticAsset, SemanticPool, SemanticTask

_PROVIDER_REGISTRY: dict[str, type[Provider]] = {
    "mock": MockProvider,
    "template": TemplateProvider,
}


def register_provider(name: str, cls: type[Provider]) -> None:
    """Register a provider implementation by name."""
    _PROVIDER_REGISTRY[name] = cls


def create_provider(config: ProviderConfig) -> Provider:
    """Create a provider instance from a configuration."""
    cls = _PROVIDER_REGISTRY.get(config.provider_type)
    if cls is None:
        raise ValueError(f"Unknown provider type: {config.provider_type!r}")
    return cls(config)


class SemanticSidecar:
    """Generate and cache semantic assets for a scenario."""

    def __init__(
        self,
        scenario: Scenario,
        provider: Provider | ProviderConfig | None = None,
        cache: SemanticCache | None = None,
        validator: SemanticValidator | None = None,
    ) -> None:
        self.scenario = scenario
        self.provider = (
            provider
            if isinstance(provider, Provider)
            else create_provider(provider or ProviderConfig("mock"))
        )
        self.cache = cache or SemanticCache(Path.cwd() / ".eventweave" / "semantic_cache")
        self.validator = validator or SemanticValidator()

    def _entity_map(self, event: Event | None = None) -> dict[str, Any]:
        entities: dict[str, Any] = {}
        for role, template in self.scenario.entities.items():
            entities[role] = {"type": template.type, "attributes": dict(template.attributes)}
        if event:
            for role, entity_id in event.entity_refs.items():
                if role in entities:
                    entities[role]["id"] = entity_id
                else:
                    entities[role] = {"id": entity_id}
        return entities

    def _build_context(self, task: SemanticTask, event: Event | None = None) -> GenerationContext:
        return GenerationContext(
            scenario=self.scenario,
            task=task,
            entities=self._entity_map(event),
            event=event,
        )

    def generate_task(
        self,
        task: SemanticTask,
        event: Event | None = None,
        force: bool = False,
    ) -> SemanticAsset:
        """Generate a semantic asset for a task, using cache when available."""
        cache_key = self.cache.build_key(
            self.provider.provider_type,
            self.scenario.id,
            task.id,
            event.event_id if event else None,
        )

        if not force:
            cached = self.cache.get(cache_key)
            if cached is not None and self.validator.is_valid(cached, task, event):
                return cached

        context = self._build_context(task, event)
        asset = self.provider.generate(task, context)
        self.validator.validate(asset, task, event)
        self.cache.set(cache_key, asset)
        return asset

    def generate_all(
        self,
        tasks: list[SemanticTask],
        events: list[Event] | None = None,
        force: bool = False,
    ) -> SemanticPool:
        """Generate semantic assets for all tasks, expanding per-event tasks."""
        events = events or []
        assets: list[SemanticAsset] = []

        for task in tasks:
            if task.valid_for and events:
                for event in events:
                    if event.event_type in task.valid_for:
                        for index in range(task.count):
                            asset = self.generate_task(task, event, force=force).model_copy()
                            asset.id = f"{asset.id}-{event.event_id}-{index}"
                            assets.append(asset)
            else:
                for index in range(task.count):
                    asset = self.generate_task(task, None, force=force).model_copy()
                    asset.id = f"{asset.id}-{index}"
                    assets.append(asset)

        return SemanticPool(scenario_id=self.scenario.id, assets=assets)
