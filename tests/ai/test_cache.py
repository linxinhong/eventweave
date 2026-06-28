
from eventweave.ai.cache import SemanticCache
from eventweave.core.semantic import SemanticAsset


def test_cache_roundtrip(tmp_path):
    cache = SemanticCache(tmp_path)
    asset = SemanticAsset(id="a-1", type="greeting", text="hello")
    cache.set("k1", asset)
    cached = cache.get("k1")
    assert cached is not None
    assert cached.id == "a-1"
    assert cached.text == "hello"


def test_cache_miss_returns_none(tmp_path):
    cache = SemanticCache(tmp_path)
    assert cache.get("missing") is None


def test_cache_has_and_clear(tmp_path):
    cache = SemanticCache(tmp_path)
    cache.set("k1", SemanticAsset(id="a-1", type="greeting", text="hello"))
    assert cache.has("k1")
    cache.clear()
    assert not cache.has("k1")
