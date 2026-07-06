from __future__ import annotations

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="AEGIS_QUANT_", env_file=".env", extra="ignore")

    app_name: str = "Aegis Quant"
    api_host: str = "0.0.0.0"
    api_port: int = 8090
    debug: bool = False

    duckdb_path: str = "data/aegis_quant.duckdb"
    postgres_url: str = "postgresql://aegis:aegis@postgres:5432/aegis_quant"
    redis_url: str = "redis://redis:6379/0"
    parquet_root: str = "data/parquet"
    mlflow_uri: str = "sqlite:///data/mlflow.db"

    aegis_exchange_url: str = "http://localhost:9080"
    polygon_api_key: str = ""
    alpaca_api_key: str = ""
    alpaca_secret_key: str = ""
    binance_api_key: str = ""
    binance_secret_key: str = ""

    default_commission_bps: float = 1.0
    default_slippage_bps: float = 2.0
    default_latency_ms: float = 1.0


settings = Settings()
