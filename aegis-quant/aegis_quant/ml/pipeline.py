from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import mlflow
import numpy as np
import pandas as pd
from sklearn.ensemble import RandomForestClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.model_selection import TimeSeriesSplit, cross_val_score

from aegis_quant.core.config import settings
from aegis_quant.validation.walk_forward import WalkForwardValidator


@dataclass
class MLResult:
    model_name: str
    metrics: dict[str, float]
    feature_importance: pd.Series | None
    run_id: str


class MLPipeline:
    """Machine learning pipeline with MLflow tracking."""

    MODELS = {
        "logistic_regression": LogisticRegression,
        "random_forest": lambda: RandomForestClassifier(n_estimators=100, max_depth=5, random_state=42),
        "mlp": lambda: __import__("sklearn.neural_network", fromlist=["MLPClassifier"]).MLPClassifier(
            hidden_layer_sizes=(64, 32), max_iter=200, random_state=42
        ),
    }

    def __init__(self, experiment_name: str = "aegis-quant"):
        mlflow.set_tracking_uri(settings.mlflow_uri)
        mlflow.set_experiment(experiment_name)

    def train(
        self,
        features: pd.DataFrame,
        target: pd.Series,
        model_name: str = "random_forest",
        params: dict[str, Any] | None = None,
    ) -> MLResult:
        X = features.dropna()
        y = target.loc[X.index].dropna()
        common = X.index.intersection(y.index)
        X, y = X.loc[common], y.loc[common]

        factory = self.MODELS.get(model_name)
        if factory is None:
            factory = self._get_boosting_model(model_name)
        model = factory(**(params or {})) if params else factory()

        with mlflow.start_run() as run:
            mlflow.log_param("model", model_name)
            mlflow.log_param("n_samples", len(X))
            mlflow.log_param("n_features", X.shape[1])

            tscv = TimeSeriesSplit(n_splits=5)
            scores = cross_val_score(model, X, y, cv=tscv, scoring="accuracy")
            mlflow.log_metric("cv_accuracy_mean", float(scores.mean()))
            mlflow.log_metric("cv_accuracy_std", float(scores.std()))

            model.fit(X, y)
            mlflow.sklearn.log_model(model, "model")

            importance = None
            if hasattr(model, "feature_importances_"):
                importance = pd.Series(model.feature_importances_, index=X.columns).sort_values(ascending=False)
                for feat, imp in importance.head(20).items():
                    mlflow.log_metric(f"importance_{feat}", float(imp))

            return MLResult(
                model_name=model_name,
                metrics={"cv_accuracy": float(scores.mean()), "cv_std": float(scores.std())},
                feature_importance=importance,
                run_id=run.info.run_id,
            )

    def walk_forward_optimize(
        self,
        features: pd.DataFrame,
        target: pd.Series,
        model_name: str = "random_forest",
        n_splits: int = 5,
    ) -> dict[str, float]:
        validator = WalkForwardValidator(n_splits=n_splits)
        return validator.validate(features, target, lambda X, y: self._fit_predict(model_name, X, y))

    def _fit_predict(self, model_name: str, X: pd.DataFrame, y: pd.Series) -> np.ndarray:
        factory = self.MODELS.get(model_name, self.MODELS["random_forest"])
        model = factory()
        model.fit(X, y)
        return model.predict(X)

    @staticmethod
    def _get_boosting_model(name: str):
        if name == "xgboost":
            from xgboost import XGBClassifier

            return lambda: XGBClassifier(n_estimators=100, max_depth=4, random_state=42, verbosity=0)
        if name == "lightgbm":
            from lightgbm import LGBMClassifier

            return lambda: LGBMClassifier(n_estimators=100, max_depth=4, random_state=42, verbose=-1)
        if name == "catboost":
            from catboost import CatBoostClassifier

            return lambda: CatBoostClassifier(iterations=100, depth=4, random_state=42, verbose=0)
        raise ValueError(f"Unknown model: {name}")
