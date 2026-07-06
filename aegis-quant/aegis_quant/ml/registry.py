from __future__ import annotations

import json
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import joblib

from aegis_quant.core.logging import get_logger

logger = get_logger(__name__)


class ModelRegistry:
    """Persistent model registry backed by joblib artifacts + JSON metadata."""

    def __init__(self, root: str | Path = "data/models"):
        self.root = Path(root)
        self.root.mkdir(parents=True, exist_ok=True)
        self.index_path = self.root / "registry.json"

    def _load_index(self) -> dict[str, dict[str, Any]]:
        if not self.index_path.exists():
            return {}
        return json.loads(self.index_path.read_text())

    def _save_index(self, index: dict[str, dict[str, Any]]) -> None:
        self.index_path.write_text(json.dumps(index, indent=2, default=str))

    def save(
        self,
        model: Any,
        model_name: str,
        symbol: str,
        metrics: dict[str, float],
        evaluation: dict[str, Any],
        feature_cols: list[str],
        params: dict[str, Any] | None = None,
        run_id: str = "",
    ) -> str:
        model_id = uuid.uuid4().hex[:12]
        artifact = self.root / f"{model_id}.joblib"
        joblib.dump(model, artifact)
        index = self._load_index()
        index[model_id] = {
            "model_id": model_id,
            "model_name": model_name,
            "symbol": symbol,
            "created_at": datetime.now(timezone.utc).isoformat(),
            "metrics": metrics,
            "evaluation": evaluation,
            "feature_cols": feature_cols,
            "params": params or {},
            "mlflow_run_id": run_id,
            "artifact": str(artifact),
        }
        self._save_index(index)
        logger.info("model_saved", model_id=model_id, model=model_name, symbol=symbol)
        return model_id

    def list_models(self) -> list[dict[str, Any]]:
        index = self._load_index()
        entries = sorted(index.values(), key=lambda e: e["created_at"], reverse=True)
        # Slim listing: omit heavy evaluation payloads
        return [
            {k: v for k, v in e.items() if k != "evaluation"} | {"has_evaluation": bool(e.get("evaluation"))}
            for e in entries
        ]

    def get(self, model_id: str) -> dict[str, Any] | None:
        return self._load_index().get(model_id)

    def load_model(self, model_id: str) -> Any:
        entry = self.get(model_id)
        if entry is None:
            raise KeyError(f"Model not found: {model_id}")
        return joblib.load(entry["artifact"])

    def artifact_path(self, model_id: str) -> Path:
        entry = self.get(model_id)
        if entry is None:
            raise KeyError(f"Model not found: {model_id}")
        return Path(entry["artifact"])

    def delete(self, model_id: str) -> bool:
        index = self._load_index()
        entry = index.pop(model_id, None)
        if entry is None:
            return False
        Path(entry["artifact"]).unlink(missing_ok=True)
        self._save_index(index)
        logger.info("model_deleted", model_id=model_id)
        return True

    def compare(self, model_ids: list[str]) -> list[dict[str, Any]]:
        index = self._load_index()
        rows = []
        for mid in model_ids:
            entry = index.get(mid)
            if entry:
                rows.append({
                    "model_id": mid,
                    "model_name": entry["model_name"],
                    "symbol": entry["symbol"],
                    "created_at": entry["created_at"],
                    "metrics": entry["metrics"],
                })
        return rows
