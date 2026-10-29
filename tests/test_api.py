import pytest
from fastapi.testclient import TestClient
import importlib.util
from pathlib import Path

_API_PATH = Path(__file__).resolve().parents[1] / "backend" / "app" / "main.py"
_SPEC = importlib.util.spec_from_file_location("smartlab_api_under_test", _API_PATH)
api = importlib.util.module_from_spec(_SPEC)
assert _SPEC and _SPEC.loader
_SPEC.loader.exec_module(api)


@pytest.fixture
def client(tmp_path, monkeypatch):
    monkeypatch.setattr(api, "DB_PATH", tmp_path / "test-smartlab.sqlite")
    with TestClient(api.app) as test_client:
        yield test_client


def test_health_endpoint(client):
    response = client.get("/api/health")
    assert response.status_code == 200
    assert response.json()["ok"] is True


def test_default_device_is_initialized(client):
    response = client.get("/api/devices")
    assert response.status_code == 200
    assert any(device["id"] == api.DEFAULT_DEVICE for device in response.json())


def test_ingest_and_read_latest(client):
    payload = {"temperature_c": 25.5, "humidity_pct": 48.0}
    response = client.post("/api/readings", json=payload)
    assert response.status_code == 201
    latest = client.get("/api/readings/latest")
    assert latest.status_code == 200
    assert latest.json()["temperature_c"] == 25.5


def test_unknown_device_is_rejected(client):
    response = client.post(
        "/api/readings",
        json={"device_id": "not-registered", "temperature_c": 25, "humidity_pct": 50},
    )
    assert response.status_code == 404


def test_out_of_range_sensor_values_are_rejected(client):
    response = client.post(
        "/api/readings",
        json={"temperature_c": 200, "humidity_pct": 50},
    )
    assert response.status_code == 422


def test_threshold_update_and_invalid_humidity_range(client):
    good = client.put(
        "/api/settings",
        json={"temperature_limit_c": 32, "humidity_min_pct": 25, "humidity_max_pct": 70},
    )
    assert good.status_code == 200
    assert client.get("/api/settings").json()["temperature_limit_c"] == 32

    bad = client.put(
        "/api/settings",
        json={"temperature_limit_c": 32, "humidity_min_pct": 80, "humidity_max_pct": 70},
    )
    assert bad.status_code == 400


def test_high_temperature_creates_event(client):
    response = client.post(
        "/api/readings",
        json={"temperature_c": 35, "humidity_pct": 50},
    )
    assert response.status_code == 201
    events = client.get("/api/events")
    assert events.status_code == 200
    assert len(events.json()) == 1
    assert events.json()[0]["severity"] == "warning"
