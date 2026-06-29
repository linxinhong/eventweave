"""Mock provider that returns deterministic placeholder semantic assets."""

from eventweave.ai.provider import GenerationContext, Provider
from eventweave.core.semantic import SemanticAsset, SemanticAssetMeta, SemanticTask


class MockProvider(Provider):
    """Provider that generates deterministic placeholder text.

    This provider requires no API keys and is useful for testing and CI.
    """

    @property
    def provider_type(self) -> str:
        return "mock"

    def generate(
        self,
        task: SemanticTask,
        context: GenerationContext,
    ) -> SemanticAsset:
        text, render_ok = self._render_template(task.template, context)
        if not text:
            text = f"[{task.type}] Mock semantic content for task {task.id}."

        return SemanticAsset(
            id=f"{task.id}-mock",
            type=task.type,
            text=text,
            valid_for=list(task.valid_for),
            meta=SemanticAssetMeta(
                provider=self.provider_type,
                source_task=task.id,
                source_event=context.event.event_id if context.event else None,
                review_status="approved" if render_ok else "pending",
            ),
        )
