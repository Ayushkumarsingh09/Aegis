from __future__ import annotations

from datetime import datetime

import duckdb
import pandas as pd

from aegis_quant.core.config import settings
from aegis_quant.core.logging import get_logger

logger = get_logger(__name__)


class FeatureStore:
    """Persistent feature storage backed by DuckDB."""

    def __init__(self, duckdb_path: str | None = None):
        self.duckdb_path = duckdb_path or settings.duckdb_path
        self._ensure_schema()

    def _ensure_schema(self) -> None:
        from pathlib import Path

        Path(self.duckdb_path).parent.mkdir(parents=True, exist_ok=True)
        con = duckdb.connect(self.duckdb_path)
        con.execute(
            """
            CREATE TABLE IF NOT EXISTS features (
                symbol VARCHAR,
                timestamp TIMESTAMP,
                feature_set VARCHAR,
                feature_name VARCHAR,
                value DOUBLE,
                PRIMARY KEY (symbol, timestamp, feature_set, feature_name)
            )
            """
        )
        con.close()

    def write_features(
        self,
        df: pd.DataFrame,
        symbol: str,
        feature_set: str = "default",
        timestamp_col: str = "timestamp",
    ) -> int:
        feature_cols = [c for c in df.columns if c not in (timestamp_col, "symbol")]
        if not feature_cols:
            return 0
        rows = []
        for _, row in df.iterrows():
            ts = row[timestamp_col]
            for feat in feature_cols:
                val = row[feat]
                if pd.notna(val):
                    rows.append((symbol, ts, feature_set, feat, float(val)))
        if not rows:
            return 0
        con = duckdb.connect(self.duckdb_path)
        con.executemany(
            """
            INSERT OR REPLACE INTO features (symbol, timestamp, feature_set, feature_name, value)
            VALUES (?, ?, ?, ?, ?)
            """,
            rows,
        )
        con.close()
        logger.info("features_written", symbol=symbol, count=len(rows))
        return len(rows)

    def read_features(
        self,
        symbol: str,
        feature_set: str = "default",
        start: datetime | None = None,
        end: datetime | None = None,
    ) -> pd.DataFrame:
        con = duckdb.connect(self.duckdb_path, read_only=True)
        query = "SELECT timestamp, feature_name, value FROM features WHERE symbol = ? AND feature_set = ?"
        params: list = [symbol, feature_set]
        if start:
            query += " AND timestamp >= ?"
            params.append(start)
        if end:
            query += " AND timestamp <= ?"
            params.append(end)
        df = con.execute(query, params).df()
        con.close()
        if df.empty:
            return pd.DataFrame()
        return df.pivot(index="timestamp", columns="feature_name", values="value").reset_index()

    def list_feature_sets(self, symbol: str | None = None) -> list[str]:
        con = duckdb.connect(self.duckdb_path, read_only=True)
        if symbol:
            rows = con.execute(
                "SELECT DISTINCT feature_set FROM features WHERE symbol = ?", [symbol]
            ).fetchall()
        else:
            rows = con.execute("SELECT DISTINCT feature_set FROM features").fetchall()
        con.close()
        return [r[0] for r in rows]
