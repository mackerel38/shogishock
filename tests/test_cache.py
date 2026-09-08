from surprise.engine import Cache

def test_cache_roundtrip(tmp_path):
    c = Cache(str(tmp_path / "cache.sqlite3")); c.put("a", {"nodes": 10}); assert c.get("a") == {"nodes": 10}; c.close()

def test_cache_keys_are_request_specific(tmp_path):
    c = Cache(str(tmp_path / "cache.sqlite3")); c.put("nodes-10", {"nodes": 10}); c.put("nodes-20", {"nodes": 20})
    assert c.get("nodes-10") != c.get("nodes-20"); c.close()
