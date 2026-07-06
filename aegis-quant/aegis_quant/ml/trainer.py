from __future__ import annotations

import threading
import traceback
import uuid
from dataclasses import dataclass, field
from typing import Any, Callable

import numpy as np
import pandas as pd
from sklearn.metrics import (
    accuracy_score,
    confusion_matrix,
    f1_score,
    precision_score,
    recall_score,
    roc_auc_score,
    roc_curve,
)
from sklearn.model_selection import TimeSeriesSplit

from aegis_quant.core.logging import get_logger
from aegis_quant.ml.registry import ModelRegistry

logger = get_logger(__name__)


@dataclass
class TrainJob:
    job_id: str
    status: str = "pending"  # pending | running | completed | failed
    progress: float = 0.0
    stage: str = "queued"
    result: dict[str, Any] | None = None
    error: str | None = None
    fold_scores: list[float] = field(default_factory=list)


class TrainingManager:
    """Background training jobs with progress reporting and full evaluation."""

    def __init__(self, registry: ModelRegistry | None = None):
        self.registry = registry or ModelRegistry()
        self._jobs: dict[str, TrainJob] = {}
        self._lock = threading.Lock()

    def get_job(self, job_id: str) -> TrainJob | None:
        with self._lock:
            return self._jobs.get(job_id)

    def submit(
        self,
        features: pd.DataFrame,
        target: pd.Series,
        model_factory: Callable[[], Any],
        model_name: str,
        symbol: str,
        params: dict[str, Any] | None = None,
        mlflow_log: Callable[[str, dict[str, float]], str] | None = None,
    ) -> str:
        job_id = uuid.uuid4().hex[:12]
        job = TrainJob(job_id=job_id)
        with self._lock:
            self._jobs[job_id] = job
        thread = threading.Thread(
            target=self._run,
            args=(job, features, target, model_factory, model_name, symbol, params, mlflow_log),
            daemon=True,
        )
        thread.start()
        return job_id

    def train_sync(
        self,
        features: pd.DataFrame,
        target: pd.Series,
        model_factory: Callable[[], Any],
        model_name: str,
        symbol: str,
        params: dict[str, Any] | None = None,
        mlflow_log: Callable[[str, dict[str, float]], str] | None = None,
    ) -> dict[str, Any]:
        job = TrainJob(job_id=uuid.uuid4().hex[:12])
        self._run(job, features, target, model_factory, model_name, symbol, params, mlflow_log)
        if job.status == "failed":
            raise RuntimeError(job.error or "training failed")
        assert job.result is not None
        return job.result

    def _update(self, job: TrainJob, progress: float, stage: str) -> None:
        with self._lock:
            job.progress = round(progress, 3)
            job.stage = stage

    def _run(
        self,
        job: TrainJob,
        features: pd.DataFrame,
        target: pd.Series,
        model_factory: Callable[[], Any],
        model_name: str,
        symbol: str,
        params: dict[str, Any] | None,
        mlflow_log: Callable[[str, dict[str, float]], str] | None,
    ) -> None:
        try:
            job.status = "running"
            self._update(job, 0.05, "preparing data")

            X = features.dropna()
            y = target.loc[X.index].dropna()
            common = X.index.intersection(y.index)
            X, y = X.loc[common], y.loc[common]
            if len(X) < 50:
                raise ValueError(f"Not enough samples to train: {len(X)}")

            # Time-ordered holdout: last 25% for evaluation
            split = int(len(X) * 0.75)
            X_train, X_test = X.iloc[:split], X.iloc[split:]
            y_train, y_test = y.iloc[:split], y.iloc[split:]

            self._update(job, 0.1, "cross-validation")
            n_folds = 5
            tscv = TimeSeriesSplit(n_splits=n_folds)
            fold_scores: list[float] = []
            for i, (tr_idx, va_idx) in enumerate(tscv.split(X_train)):
                cv_model = model_factory()
                cv_model.fit(X_train.iloc[tr_idx], y_train.iloc[tr_idx])
                score = accuracy_score(y_train.iloc[va_idx], cv_model.predict(X_train.iloc[va_idx]))
                fold_scores.append(float(score))
                with self._lock:
                    job.fold_scores = list(fold_scores)
                self._update(job, 0.1 + 0.5 * (i + 1) / n_folds, f"cross-validation fold {i + 1}/{n_folds}")

            self._update(job, 0.65, "fitting final model")
            model = model_factory()
            model.fit(X_train, y_train)

            self._update(job, 0.8, "evaluating holdout")
            y_pred = model.predict(X_test)
            metrics: dict[str, float] = {
                "cv_accuracy": float(np.mean(fold_scores)),
                "cv_std": float(np.std(fold_scores)),
                "test_accuracy": float(accuracy_score(y_test, y_pred)),
                "precision": float(precision_score(y_test, y_pred, zero_division=0)),
                "recall": float(recall_score(y_test, y_pred, zero_division=0)),
                "f1": float(f1_score(y_test, y_pred, zero_division=0)),
            }

            evaluation: dict[str, Any] = {
                "confusion_matrix": confusion_matrix(y_test, y_pred).tolist(),
                "cv_fold_scores": fold_scores,
                "n_train": len(X_train),
                "n_test": len(X_test),
            }

            if hasattr(model, "predict_proba"):
                proba = model.predict_proba(X_test)[:, 1]
                if len(np.unique(y_test)) > 1:
                    metrics["roc_auc"] = float(roc_auc_score(y_test, proba))
                    fpr, tpr, _ = roc_curve(y_test, proba)
                    # Downsample ROC to at most 100 points for the UI
                    idx = np.linspace(0, len(fpr) - 1, min(100, len(fpr))).astype(int)
                    evaluation["roc_curve"] = {
                        "fpr": fpr[idx].round(4).tolist(),
                        "tpr": tpr[idx].round(4).tolist(),
                    }

            importance: dict[str, float] = {}
            if hasattr(model, "feature_importances_"):
                imp = pd.Series(model.feature_importances_, index=X.columns)
                importance = imp.sort_values(ascending=False).head(20).round(5).to_dict()
            elif hasattr(model, "coef_"):
                imp = pd.Series(np.abs(np.ravel(model.coef_)), index=X.columns)
                importance = imp.sort_values(ascending=False).head(20).round(5).to_dict()
            evaluation["feature_importance"] = importance

            self._update(job, 0.9, "persisting model")
            run_id = ""
            if mlflow_log is not None:
                run_id = mlflow_log(model_name, metrics)
            model_id = self.registry.save(
                model=model,
                model_name=model_name,
                symbol=symbol,
                metrics=metrics,
                evaluation=evaluation,
                feature_cols=list(X.columns),
                params=params,
                run_id=run_id,
            )

            job.result = {
                "model_id": model_id,
                "model": model_name,
                "symbol": symbol,
                "metrics": metrics,
                "evaluation": evaluation,
                "run_id": run_id,
            }
            self._update(job, 1.0, "completed")
            job.status = "completed"
            logger.info("train_job_done", job_id=job.job_id, model_id=model_id)
        except Exception as exc:  # noqa: BLE001 — surface any training failure to the job
            job.status = "failed"
            job.error = f"{exc}"
            job.stage = "failed"
            logger.error("train_job_failed", job_id=job.job_id, error=str(exc), tb=traceback.format_exc())
