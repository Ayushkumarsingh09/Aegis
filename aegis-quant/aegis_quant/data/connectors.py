from __future__ import annotations

from abc import ABC, abstractmethod
from datetime import datetime
from pathlib import Path
from typing import AsyncIterator, Iterator

import duckdb
import httpx
import pandas as pd
import polars as pl
import yfinance as yf

from aegis_quant.core.config import settings
from aegis_quant.core.logging import get_logger
from aegis_quant.core.types import Bar, OrderBook, Tick

logger = get_logger(__name__)


class DataConnector(ABC):
    @abstractmethod
    def load_bars(
        self, symbol: str, start: datetime | None = None, end: datetime | None = None
    ) -> pd.DataFrame:
        ...

    def stream_ticks(self, symbol: str) -> Iterator[Tick]:
        raise NotImplementedError(f"{self.__class__.__name__} does not support tick streaming")


class CSVConnector(DataConnector):
    def __init__(self, root: str | Path):
        self.root = Path(root)

    def load_bars(self, symbol: str, start: datetime | None = None, end: datetime | None = None) -> pd.DataFrame:
        path = self.root / f"{symbol}.csv"
        df = pd.read_csv(path, parse_dates=["timestamp"])
        return _filter_dates(df, start, end)


class ParquetConnector(DataConnector):
    def __init__(self, root: str | Path):
        self.root = Path(root)

    def load_bars(self, symbol: str, start: datetime | None = None, end: datetime | None = None) -> pd.DataFrame:
        path = self.root / f"{symbol}.parquet"
        df = pl.read_parquet(path).to_pandas()
        if "timestamp" in df.columns:
            df["timestamp"] = pd.to_datetime(df["timestamp"])
        return _filter_dates(df, start, end)


class DuckDBConnector(DataConnector):
    def __init__(self, db_path: str | None = None):
        self.db_path = db_path or settings.duckdb_path

    def load_bars(self, symbol: str, start: datetime | None = None, end: datetime | None = None) -> pd.DataFrame:
        con = duckdb.connect(self.db_path, read_only=True)
        query = "SELECT * FROM bars WHERE symbol = ?"
        params: list = [symbol]
        if start:
            query += " AND timestamp >= ?"
            params.append(start)
        if end:
            query += " AND timestamp <= ?"
            params.append(end)
        query += " ORDER BY timestamp"
        df = con.execute(query, params).df()
        con.close()
        return df


class YahooFinanceConnector(DataConnector):
    def load_bars(self, symbol: str, start: datetime | None = None, end: datetime | None = None) -> pd.DataFrame:
        data = yf.download(symbol, start=start, end=end, progress=False, auto_adjust=True)
        if data.empty:
            return pd.DataFrame(columns=["symbol", "timestamp", "open", "high", "low", "close", "volume"])
        data = data.reset_index()
        data.columns = [c.lower() if isinstance(c, str) else c[0].lower() for c in data.columns]
        data.rename(columns={"date": "timestamp", "adj close": "close"}, inplace=True)
        data["symbol"] = symbol
        return data[["symbol", "timestamp", "open", "high", "low", "close", "volume"]]


class AegisExchangeConnector(DataConnector):
    def __init__(self, base_url: str | None = None):
        self.base_url = (base_url or settings.aegis_exchange_url).rstrip("/")
        self._instrument_map: dict[str, int] = {}

    def _resolve_instrument(self, symbol: str) -> int:
        if symbol in self._instrument_map:
            return self._instrument_map[symbol]
        with httpx.Client(timeout=10) as client:
            resp = client.get(f"{self.base_url}/api/v1/status")
            resp.raise_for_status()
            for inst in resp.json().get("instruments", []):
                self._instrument_map[inst["symbol"]] = inst["id"]
        if symbol not in self._instrument_map:
            raise ValueError(f"Unknown instrument on Aegis Exchange: {symbol}")
        return self._instrument_map[symbol]

    def load_bars(self, symbol: str, start: datetime | None = None, end: datetime | None = None) -> pd.DataFrame:
        iid = self._resolve_instrument(symbol)
        with httpx.Client(timeout=10) as client:
            trades = client.get(f"{self.base_url}/api/v1/instruments/{iid}/trades").json()
        if not trades:
            return pd.DataFrame(columns=["symbol", "timestamp", "open", "high", "low", "close", "volume"])
        df = pd.DataFrame(trades)
        df["timestamp"] = pd.to_datetime(df["timestamp"], unit="ns")
        df["price"] = df["price"].astype(float)
        df["volume"] = df["quantity"].astype(float)
        bars = (
            df.set_index("timestamp")
            .resample("1min")
            .agg(open=("price", "first"), high=("price", "max"), low=("price", "min"), close=("price", "last"), volume=("volume", "sum"))
            .dropna()
            .reset_index()
        )
        bars["symbol"] = symbol
        return _filter_dates(bars, start, end)

    def get_order_book(self, symbol: str, depth: int = 20) -> OrderBook:
        iid = self._resolve_instrument(symbol)
        with httpx.Client(timeout=10) as client:
            data = client.get(f"{self.base_url}/api/v1/instruments/{iid}/book", params={"depth": depth}).json()
        from aegis_quant.core.types import OrderBookLevel

        return OrderBook(
            symbol=symbol,
            timestamp=pd.Timestamp.utcnow().to_pydatetime(),
            bids=[OrderBookLevel(price=b["price"], quantity=b["quantity"], orders=b.get("orders", 1)) for b in data.get("bids", [])],
            asks=[OrderBookLevel(price=a["price"], quantity=a["quantity"], orders=a.get("orders", 1)) for a in data.get("asks", [])],
            sequence=data.get("sequence", 0),
        )

    async def stream_events(self, symbol: str) -> AsyncIterator[dict]:
        import json

        import websockets

        url = self.base_url.replace("http", "ws") + "/api/v1/stream"
        async with websockets.connect(url) as ws:
            async for msg in ws:
                yield json.loads(msg)


class BinanceConnector(DataConnector):
    """Binance public kline data connector."""

    BASE_URL = "https://api.binance.com"

    def load_bars(self, symbol: str, start: datetime | None = None, end: datetime | None = None) -> pd.DataFrame:
        pair = symbol.replace("-", "").replace("/", "").upper()
        params: dict = {"symbol": pair, "interval": "1h", "limit": 1000}
        with httpx.Client(timeout=30) as client:
            resp = client.get(f"{self.BASE_URL}/api/v3/klines", params=params)
            resp.raise_for_status()
            data = resp.json()
        if not data:
            return pd.DataFrame(columns=["symbol", "timestamp", "open", "high", "low", "close", "volume"])
        rows = []
        for k in data:
            rows.append({
                "symbol": symbol,
                "timestamp": pd.to_datetime(k[0], unit="ms"),
                "open": float(k[1]),
                "high": float(k[2]),
                "low": float(k[3]),
                "close": float(k[4]),
                "volume": float(k[5]),
            })
        return _filter_dates(pd.DataFrame(rows), start, end)


class AlpacaConnector(DataConnector):
    """Alpaca market data connector."""

    def __init__(self, api_key: str | None = None, secret_key: str | None = None):
        self.api_key = api_key or settings.alpaca_api_key
        self.secret_key = secret_key or settings.alpaca_secret_key
        self.base_url = "https://data.alpaca.markets/v2"

    def load_bars(self, symbol: str, start: datetime | None = None, end: datetime | None = None) -> pd.DataFrame:
        if not self.api_key:
            logger.warning("alpaca_no_key", symbol=symbol)
            return pd.DataFrame(columns=["symbol", "timestamp", "open", "high", "low", "close", "volume"])
        headers = {"APCA-API-KEY-ID": self.api_key, "APCA-API-SECRET-KEY": self.secret_key}
        params: dict = {"timeframe": "1Hour", "limit": 1000}
        if start:
            params["start"] = start.isoformat()
        if end:
            params["end"] = end.isoformat()
        with httpx.Client(timeout=30, headers=headers) as client:
            resp = client.get(f"{self.base_url}/stocks/{symbol}/bars", params=params)
            if resp.status_code != 200:
                logger.warning("alpaca_error", status=resp.status_code)
                return pd.DataFrame(columns=["symbol", "timestamp", "open", "high", "low", "close", "volume"])
            bars = resp.json().get("bars", [])
        if not bars:
            return pd.DataFrame(columns=["symbol", "timestamp", "open", "high", "low", "close", "volume"])
        df = pd.DataFrame(bars)
        df.rename(columns={"t": "timestamp", "o": "open", "h": "high", "l": "low", "c": "close", "v": "volume"}, inplace=True)
        df["timestamp"] = pd.to_datetime(df["timestamp"])
        df["symbol"] = symbol
        return df[["symbol", "timestamp", "open", "high", "low", "close", "volume"]]


class PolygonConnector(DataConnector):
    """Polygon.io aggregate bars connector."""

    def __init__(self, api_key: str | None = None):
        self.api_key = api_key or settings.polygon_api_key

    def load_bars(self, symbol: str, start: datetime | None = None, end: datetime | None = None) -> pd.DataFrame:
        if not self.api_key:
            logger.warning("polygon_no_key", symbol=symbol)
            return pd.DataFrame(columns=["symbol", "timestamp", "open", "high", "low", "close", "volume"])
        start_str = (start or datetime(2024, 1, 1)).strftime("%Y-%m-%d")
        end_str = (end or datetime.utcnow()).strftime("%Y-%m-%d")
        url = f"https://api.polygon.io/v2/aggs/ticker/{symbol}/range/1/hour/{start_str}/{end_str}"
        with httpx.Client(timeout=30) as client:
            resp = client.get(url, params={"apiKey": self.api_key, "limit": 5000})
            if resp.status_code != 200:
                return pd.DataFrame(columns=["symbol", "timestamp", "open", "high", "low", "close", "volume"])
            results = resp.json().get("results", [])
        if not results:
            return pd.DataFrame(columns=["symbol", "timestamp", "open", "high", "low", "close", "volume"])
        rows = [{
            "symbol": symbol,
            "timestamp": pd.to_datetime(r["t"], unit="ms"),
            "open": r["o"], "high": r["h"], "low": r["l"], "close": r["c"], "volume": r["v"],
        } for r in results]
        return pd.DataFrame(rows)


class PostgresConnector(DataConnector):
    def __init__(self, url: str | None = None):
        from sqlalchemy import create_engine, text

        self.engine = create_engine(url or settings.postgres_url)

    def load_bars(self, symbol: str, start: datetime | None = None, end: datetime | None = None) -> pd.DataFrame:
        from sqlalchemy import text

        query = "SELECT * FROM bars WHERE symbol = :symbol"
        params: dict = {"symbol": symbol}
        if start:
            query += " AND timestamp >= :start"
            params["start"] = start
        if end:
            query += " AND timestamp <= :end"
            params["end"] = end
        query += " ORDER BY timestamp"
        with self.engine.connect() as conn:
            return pd.read_sql(text(query), conn, params=params)


def _filter_dates(df: pd.DataFrame, start: datetime | None, end: datetime | None) -> pd.DataFrame:
    if df.empty or "timestamp" not in df.columns:
        return df
    if start is not None:
        df = df[df["timestamp"] >= pd.Timestamp(start)]
    if end is not None:
        df = df[df["timestamp"] <= pd.Timestamp(end)]
    return df.reset_index(drop=True)
