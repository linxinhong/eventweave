
from eventweave.ai.validator import SemanticValidator
from eventweave.core.event import Event
from eventweave.core.semantic import SemanticAsset, SemanticTask


def test_valid_asset():
    validator = SemanticValidator()
    task = SemanticTask(id="t1", type="greeting")
    asset = SemanticAsset(id="a1", type="greeting", text="hello")
    assert validator.is_valid(asset, task)


def test_type_mismatch():
    validator = SemanticValidator()
    task = SemanticTask(id="t1", type="greeting")
    asset = SemanticAsset(id="a1", type="farewell", text="bye")
    assert not validator.is_valid(asset, task)


def test_empty_text_invalid():
    validator = SemanticValidator()
    task = SemanticTask(id="t1", type="greeting")
    asset = SemanticAsset(id="a1", type="greeting", text="   ")
    assert not validator.is_valid(asset, task)


def test_max_length():
    validator = SemanticValidator(max_length=5)
    task = SemanticTask(id="t1", type="greeting")
    asset = SemanticAsset(id="a1", type="greeting", text="hello world")
    assert not validator.is_valid(asset, task)


def _event(event_type: str) -> Event:
    return Event(
        event_id="e1",
        scenario_id="sc1",
        source_id="src1",
        event_type=event_type,
        event_time="2024-01-01T00:00:00Z",
    )


def test_valid_for_event_type():
    validator = SemanticValidator()
    task = SemanticTask(id="t1", type="greeting", valid_for=["login"])
    asset = SemanticAsset(id="a1", type="greeting", text="hi")
    assert validator.is_valid(asset, task, _event("login"))


def test_invalid_for_event_type():
    validator = SemanticValidator()
    task = SemanticTask(id="t1", type="greeting", valid_for=["login"])
    asset = SemanticAsset(id="a1", type="greeting", text="hi")
    assert not validator.is_valid(asset, task, _event("logout"))
