"""Template provider that fills variable placeholders without calling an LLM."""

from eventweave.ai.provider import GenerationContext, Provider
from eventweave.core.semantic import SemanticAsset, SemanticAssetMeta, SemanticTask


class TemplateProvider(Provider):
    """Provider that renders a template using scenario variables.

    This provider is deterministic and requires no external service.
    """

    @property
    def provider_type(self) -> str:
        return "template"

    def generate(
        self,
        task: SemanticTask,
        context: GenerationContext,
    ) -> SemanticAsset:
        text, render_ok = self._render_template(task.template, context)
        if not text:
            text = f"[{task.type}] Template-rendered content for task {task.id}."

        return SemanticAsset(
            id=f"{task.id}-template",
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
