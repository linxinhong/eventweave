import pytest

from eventweave.ai.cache import SemanticCache
from eventweave.ai.mock_provider import MockProvider
from eventweave.ai.provider import ProviderConfig
from eventweave.ai.sidecar import SemanticSidecar, create_provider
from eventweave.ai.template_provider import TemplateProvider
from eventweave.core.event import Event
from eventweave.core.scenario import EntityTemplate, Scenario
from eventweave.core.semantic import SemanticTask


def test_create_provider_mock():
    provider = create_provider(ProviderConfig("mock"))
    assert isinstance(provider, MockProvider)


def test_create_provider_template():
    provider = create_provider(ProviderConfig("template"))
    assert isinstance(provider, TemplateProvider)


def test_create_provider_unknown():
    with pytest.raises(ValueError):
        create_provider(ProviderConfig("unknown"))


def make_scenario():
    return Scenario(
        id="sc1",
        version="1.0",
        domain="test",
        entities={"user": EntityTemplate(type="User", attributes={"name": "Alice"})},
    )


def test_sidecar_mock_generate(tmp_path):
    scenario = make_scenario()
    task = SemanticTask(id="t1", type="bio")
    sidecar = SemanticSidecar(
        scenario,
        provider=MockProvider(),
        cache=SemanticCache(tmp_path),
    )
    asset = sidecar.generate_task(task)
    assert asset.type == "bio"
    assert "Mock semantic content" in asset.text


def test_sidecar_template_render(tmp_path):
    scenario = make_scenario()
    task = SemanticTask(
        id="t1",
        type="bio",
        template="Hello {user.name}!",
    )
    sidecar = SemanticSidecar(
        scenario,
        provider=TemplateProvider(),
        cache=SemanticCache(tmp_path),
    )
    asset = sidecar.generate_task(task)
    assert asset.text == "Hello Alice!"


def test_sidecar_generate_all_with_events(tmp_path):
    scenario = make_scenario()
    task = SemanticTask(id="t1", type="greeting", valid_for=["login"], count=2)
    event = Event(
        event_id="e1",
        scenario_id=scenario.id,
        source_id="src1",
        event_type="login",
        event_time="2024-01-01T00:00:00Z",
    )
    sidecar = SemanticSidecar(
        scenario,
        provider=MockProvider(),
        cache=SemanticCache(tmp_path),
    )
    pool = sidecar.generate_all([task], events=[event])
    assert len(pool.assets) == 2
    assert all("-e1-" in asset.id for asset in pool.assets)
    assert len({asset.id for asset in pool.assets}) == 2
