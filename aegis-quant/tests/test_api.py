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


def test_ml_models_listing():
    r = client.get("/api/v1/ml/models")
    assert r.status_code == 200
    assert "models" in r.json()


def test_ml_unknown_job():
    r = client.get("/api/v1/ml/train/nonexistent")
    assert r.status_code == 404


def test_ml_unknown_model():
    r = client.get("/api/v1/ml/models/nonexistent")
    assert r.status_code == 404


def test_platform_status():
    r = client.get("/api/v1/platform/status")
    assert r.status_code == 200
    assert "modules" in r.json()


def test_ml_end_to_end_training():
    """Full ML workflow: sync train on real stored data, then predict."""
    symbols = client.get("/api/v1/symbols").json()["symbols"]
    if not symbols:
        import pytest

        pytest.skip("no data ingested")
    symbol = symbols[0]

    r = client.post(
        "/api/v1/ml/train",
        json={"symbol": symbol, "model": "random_forest", "target_horizon": 5, "async_mode": False},
    )
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["model_id"]
    assert "test_accuracy" in body["metrics"]
    assert body["evaluation"]["confusion_matrix"]

    model_id = body["model_id"]
    r = client.post(f"/api/v1/ml/models/{model_id}/predict", json={"n_bars": 5})
    assert r.status_code == 200, r.text
    preds = r.json()["predictions"]
    assert len(preds) == 5
    assert all("prediction" in p for p in preds)

    r = client.post("/api/v1/ml/compare", json={"model_ids": [model_id]})
    assert r.status_code == 200

    r = client.delete(f"/api/v1/ml/models/{model_id}")
    assert r.status_code == 200
