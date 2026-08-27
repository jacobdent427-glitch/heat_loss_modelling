import json

import app.api.geocode as geocode_module


class FakeResponse:
    def __init__(self, payload):
        self._payload = payload

    def read(self):
        return json.dumps(self._payload).encode("utf-8")

    def __enter__(self):
        return self

    def __exit__(self, *args):
        return False


def test_geocode_missing_address_param(client):
    res = client.get("/api/geocode")
    assert res.status_code == 400
    assert "address" in res.get_json()["error"]


def test_geocode_blank_address_param(client):
    res = client.get("/api/geocode?address=   ")
    assert res.status_code == 400


def test_geocode_address_not_found(client, monkeypatch):
    monkeypatch.setattr(geocode_module.urllib.request, "urlopen", lambda req, timeout=10: FakeResponse([]))
    res = client.get("/api/geocode?address=Nonexistent Place Zzzzzz")
    assert res.status_code == 404
    assert "No location found" in res.get_json()["error"]


def test_geocode_address_found(client, monkeypatch):
    fake_result = [{"lat": "50.9097", "lon": "-1.4044", "display_name": "Eastleigh, Hampshire, UK"}]
    monkeypatch.setattr(geocode_module.urllib.request, "urlopen", lambda req, timeout=10: FakeResponse(fake_result))
    res = client.get("/api/geocode?address=Eastleigh College")
    assert res.status_code == 200
    body = res.get_json()
    assert body["latitude"] == 50.9097
    assert body["longitude"] == -1.4044
    assert body["display_name"] == "Eastleigh, Hampshire, UK"


def test_geocode_upstream_failure_returns_502(client, monkeypatch):
    def raise_error(req, timeout=10):
        raise OSError("network unreachable")

    monkeypatch.setattr(geocode_module.urllib.request, "urlopen", raise_error)
    res = client.get("/api/geocode?address=Somewhere")
    assert res.status_code == 502
