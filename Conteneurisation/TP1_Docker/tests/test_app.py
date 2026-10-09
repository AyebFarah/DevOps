import app as app_module


class FakeRedis:
    def __init__(self):
        self.store = {}

    def incr(self, key):
        self.store[key] = self.store.get(key, 0) + 1
        return self.store[key]


def make_client(monkeypatch):
    fake = FakeRedis()
    monkeypatch.setattr(app_module, "get_redis", lambda: fake)
    return app_module.app.test_client()


def test_counter_increments(monkeypatch):
    client = make_client(monkeypatch)
    r1 = client.get("/")
    r2 = client.get("/")
    assert r1.status_code == 200
    assert "vue 1 fois" in r1.get_data(as_text=True)
    assert "vue 2 fois" in r2.get_data(as_text=True)


def test_page_contains_container_id(monkeypatch):
    client = make_client(monkeypatch)
    body = client.get("/").get_data(as_text=True)
    assert "Je suis le conteneur" in body


def test_health(monkeypatch):
    client = make_client(monkeypatch)
    assert client.get("/health").status_code == 200