from __future__ import annotations

import numpy as np
import pandas as pd
from sklearn.metrics import accuracy_score


class WalkForwardValidator:
    """Walk-forward validation for time-series models."""

    def __init__(self, n_splits: int = 5, train_size: float = 0.7):
        self.n_splits = n_splits
        self.train_size = train_size

    def validate(self, features: pd.DataFrame, target: pd.Series, fit_fn) -> dict[str, float]:
        n = len(features)
        window = int(n * self.train_size)
        step = max(1, (n - window) // self.n_splits)
        scores = []

        for i in range(self.n_splits):
            start = i * step
            train_end = start + window
            test_end = min(train_end + step, n)
            if test_end <= train_end:
                break

            X_train = features.iloc[start:train_end].dropna()
            y_train = target.loc[X_train.index]
            X_test = features.iloc[train_end:test_end].dropna()
            y_test = target.loc[X_test.index]

            if len(X_train) < 10 or len(X_test) < 5:
                continue

            preds = fit_fn(X_train, y_train)
            test_preds = fit_fn(X_test, y_test)
            if len(test_preds) == len(y_test):
                scores.append(accuracy_score(y_test, test_preds))

        return {
            "wf_mean_accuracy": float(np.mean(scores)) if scores else 0.0,
            "wf_std_accuracy": float(np.std(scores)) if scores else 0.0,
            "n_folds": len(scores),
        }

    def optimize_hyperparams(self, features, target, param_grid: dict, model_factory) -> dict:
        import optuna

        def objective(trial):
            params = {k: trial.suggest_categorical(k, v) if isinstance(v, list) else trial.suggest_float(k, v[0], v[1]) for k, v in param_grid.items()}
            model = model_factory(**params)
            scores = []
            n = len(features)
            window = int(n * 0.7)
            X_train, y_train = features.iloc[:window].dropna(), target.iloc[:window]
            X_test, y_test = features.iloc[window:].dropna(), target.iloc[window:]
            model.fit(X_train, y_train)
            preds = model.predict(X_test)
            return accuracy_score(y_test, preds)

        study = optuna.create_study(direction="maximize")
        study.optimize(objective, n_trials=20, show_progress_bar=False)
        return study.best_params
