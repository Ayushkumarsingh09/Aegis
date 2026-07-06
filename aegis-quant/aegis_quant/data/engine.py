from __future__ import annotations

from pathlib import Path

import duckdb
import pandas as pd
import polars as pl

from aegis_quant.core.config import settings
from aegis_quant.core.logging import get_logger
from aegis_quant.data.connectors import DataConnector

logger = get_logger(__name__)


class MarketDataEngine:
    """Unified market data ingestion, storage, and retrieval."""

    def __init__(self, duckdb_path: str | None = None, parquet_root: str | None = None):
        self.duckdb_path = duckdb_path or settings.duckdb_path
        self.parquet_root = Path(parquet_root or settings.parquet_root)
        self.parquet_root.mkdir(parents=True, exist_ok=True)
        self._init_duckdb()

    def _init_duckdb(self) -> None:
        Path(self.duckdb_path).parent.mkdir(parents=True, exist_ok=True)
        con = duckdb.connect(self.duckdb_path)
        con.execute(
            """
            CREATE TABLE IF NOT EXISTS bars (
                symbol VARCHAR,
                timestamp TIMESTAMP,
                open DOUBLE, high DOUBLE, low DOUBLE, close DOUBLE,
                volume DOUBLE,
                PRIMARY KEY (symbol, timestamp)
            )
            """
        )
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

    def ingest(self, connector: DataConnector, symbol: str, **kwargs) -> int:
        df = connector.load_bars(symbol, **kwargs)
        if df.empty:
            logger.warning("no_data", symbol=symbol)
            return 0
        self.store_bars(df)
        return len(df)

    def store_bars(self, df: pd.DataFrame) -> None:
        con = duckdb.connect(self.duckdb_path)
        con.register("incoming", df)
        con.execute(
            """
            INSERT OR REPLACE INTO bars
            SELECT symbol, timestamp, open, high, low, close, volume FROM incoming
            """
        )
        con.close()
        for symbol, grp in df.groupby("symbol"):
            path = self.parquet_root / f"{symbol}.parquet"
            pl.from_pandas(grp).write_parquet(path)

    def get_bars(self, symbol: str, start=None, end=None) -> pd.DataFrame:
        from aegis_quant.data.connectors import DuckDBConnector

        return DuckDBConnector(self.duckdb_path).load_bars(symbol, start, end)

    def list_symbols(self) -> list[str]:
        con = duckdb.connect(self.duckdb_path, read_only=True)
        rows = con.execute("SELECT DISTINCT symbol FROM bars ORDER BY symbol").fetchall()
        con.close()
        return [r[0] for r in rows]
