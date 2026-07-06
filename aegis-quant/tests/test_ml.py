import time

import numpy as np
import pandas as pd
import pytest

from aegis_quant.ml.registry import ModelRegistry
from aegis_quant.ml.trainer import TrainingManager


@pytest.fixture
def dataset():
    rng = np.random.default_rng(42)
    n = 300
    X = pd.DataFrame({
        "f1": rng.standard_normal(n),
        "f2": rng.standard_normal(n),
        "f3": rng.standard_normal(n),
    })
    # Learnable target: sign of f1 + noise
    y = ((X["f1"] + rng.standard_normal(n) * 0.3) > 0).astype(int)
    return X, y


@pytest.fixture
def registry(tmp_path):
    return ModelRegistry(tmp_path / "models")


def _rf_factory():
    from sklearn.ensemble import RandomForestClassifier

    return RandomForestClassifier(n_estimators=20, max_depth=3, random_state=42)


def test_train_sync_full_evaluation(dataset, registry):
    X, y = dataset
    manager = TrainingManager(registry)
    result = manager.train_sync(X, y, _rf_factory, "random_forest", "TEST")

    assert result["model_id"]
    assert result["metrics"]["test_accuracy"] > 0.6
    assert "roc_auc" in result["metrics"]
    ev = result["evaluation"]
    assert len(ev["confusion_matrix"]) == 2
    assert len(ev["cv_fold_scores"]) == 5
    assert "roc_curve" in ev
    assert ev["feature_importance"]["f1"] > ev["feature_importance"]["f3"]


def test_registry_persistence_and_load(dataset, registry):
    X, y = dataset
    manager = TrainingManager(registry)
    result = manager.train_sync(X, y, _rf_factory, "random_forest", "TEST")
    model_id = result["model_id"]

    models = registry.list_models()
    assert any(m["model_id"] == model_id for m in models)

    loaded = registry.load_model(model_id)
    preds = loaded.predict(X.head(10))
    assert len(preds) == 10

    entry = registry.get(model_id)
    assert entry["feature_cols"] == ["f1", "f2", "f3"]


def test_registry_compare_and_delete(dataset, registry):
    X, y = dataset
    manager = TrainingManager(registry)
    id1 = manager.train_sync(X, y, _rf_factory, "random_forest", "A")["model_id"]
    id2 = manager.train_sync(X, y, _rf_factory, "random_forest", "B")["model_id"]

    rows = registry.compare([id1, id2])
    assert len(rows) == 2

    assert registry.delete(id1)
    assert registry.get(id1) is None
    assert not registry.delete(id1)


def test_async_job_progress(dataset, registry):
    X, y = dataset
    manager = TrainingManager(registry)
    job_id = manager.submit(X, y, _rf_factory, "random_forest", "TEST")

    for _ in range(100):
        job = manager.get_job(job_id)
        if job.status in ("completed", "failed"):
            break
        time.sleep(0.2)

    job = manager.get_job(job_id)
    assert job.status == "completed", job.error
    assert job.progress == 1.0
    assert job.result is not None
    assert job.result["metrics"]["test_accuracy"] > 0.5


def test_train_fails_on_tiny_dataset(registry):
    X = pd.DataFrame({"f1": [1.0, 2.0, 3.0]})
    y = pd.Series([0, 1, 0])
    manager = TrainingManager(registry)
    with pytest.raises(RuntimeError):
        manager.train_sync(X, y, _rf_factory, "random_forest", "TINY")
