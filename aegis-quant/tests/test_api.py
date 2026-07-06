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


def _first_symbol():
    symbols = client.get("/api/v1/symbols").json()["symbols"]
    if not symbols:
        import pytest

        pytest.skip("no data ingested")
    return symbols


def test_backtest_detail_payload():
    symbols = _first_symbol()
    r = client.post("/api/v1/backtest", json={"strategy": "momentum", "symbol": symbols[0]})
    assert r.status_code == 200, r.text
    body = r.json()
    assert "drawdown" in body and body["drawdown"]
    assert "trades" in body
    assert "rolling_sharpe" in body


def test_portfolio_frontier_and_backtest():
    symbols = _first_symbol()
    if len(symbols) < 2:
        import pytest

        pytest.skip("need 2 symbols")
    r = client.get(f"/api/v1/portfolio/frontier?symbols={','.join(symbols[:2])}")
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["cloud"] and body["assets"] and "weights" in body["max_sharpe"]

    r = client.post("/api/v1/portfolio/backtest", json={"weights": {s: 0.5 for s in symbols[:2]}})
    assert r.status_code == 200, r.text
    assert "equity_curve" in r.json()


def test_execution_all_algorithms():
    symbols = _first_symbol()
    for algo in ("twap", "vwap", "pov", "iceberg", "arrival_price"):
        r = client.post("/api/v1/execution/simulate", json={"symbol": symbols[0], "quantity": 50, "algorithm": algo, "n_slices": 5})
        assert r.status_code == 200, f"{algo}: {r.text}"
        body = r.json()
        assert body["fills"], algo
        assert "tca" in body and "vs_arrival_bps" in body["tca"], algo


def test_risk_rolling_correlation_montecarlo():
    symbols = _first_symbol()
    r = client.get(f"/api/v1/risk/rolling/{symbols[0]}")
    assert r.status_code == 200
    assert r.json()["rolling_sharpe"]

    r = client.get(f"/api/v1/risk/montecarlo/{symbols[0]}?n_sims=200&horizon=20")
    assert r.status_code == 200
    assert len(r.json()["bands"]["p50"]) == 20

    if len(symbols) >= 2:
        r = client.get("/api/v1/risk/correlation")
        assert r.status_code == 200
        assert r.json()["matrix"]


def test_factor_analysis():
    symbols = _first_symbol()
    r = client.get(f"/api/v1/factors/{symbols[0]}/analysis")
    assert r.status_code == 200, r.text
    body = r.json()
    assert len(body["table"]) >= 5
    assert body["rolling_ic"]["series"]


def test_experiments_persisted():
    symbols = _first_symbol()
    client.post("/api/v1/backtest", json={"strategy": "momentum", "symbol": symbols[0]})
    r = client.get("/api/v1/experiments")
    assert r.status_code == 200
    exps = r.json()["experiments"]
    assert any(e["kind"] == "backtest" for e in exps)


def test_options_method_comparison():
    r = client.post("/api/v1/options/price", json={"spot": 100, "strike": 100, "expiry": 1.0, "volatility": 0.2, "option_type": "put"})
    assert r.status_code == 200
    methods = r.json()["methods"]
    assert methods["binomial_american"] >= methods["black_scholes"] - 0.01
    assert abs(methods["monte_carlo"] - methods["black_scholes"]) < 0.5


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
