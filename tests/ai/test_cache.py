
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
def test_cache_uses_sha256_file_names(tmp_path):
    cache = SemanticCache(tmp_path)
    cache.set("a+b", SemanticAsset(id="a", type="greeting", text="hello"))
    cache.set("a-b", SemanticAsset(id="b", type="greeting", text="world"))

    assert cache.has("a+b")
    assert cache.has("a-b")
    assert cache.get("a+b").id == "a"
    assert cache.get("a-b").id == "b"

    # The two keys should not map to the same file.
    assert len(list(tmp_path.glob("*.json"))) == 2
