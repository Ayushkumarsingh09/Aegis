from fastapi.testclient import TestClient

from aegis_quant.api.app import app

client = TestClient(app)


def test_health():
    r = client.get("/health")
    assert r.status_code == 200
    assert r.json()["status"] == "healthy"


def test_strategies_list():
    r = client.get("/api/v1/strategies")
    assert r.status_code == 200
    assert "mean_reversion" in r.json()["strategies"]


def test_symbols():
    r = client.get("/api/v1/symbols")
    assert r.status_code == 200
    assert "symbols" in r.json()
