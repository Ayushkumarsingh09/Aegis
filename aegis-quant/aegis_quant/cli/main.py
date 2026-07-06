"""Aegis Quant CLI."""

from __future__ import annotations

import argparse
import json
import sys

import httpx
import pandas as pd

from aegis_quant.core.config import settings
from aegis_quant.data.engine import MarketDataEngine
from aegis_quant.data.connectors import CSVConnector, YahooFinanceConnector
from aegis_quant.features.engine import FeatureEngine
from aegis_quant.strategy.strategies import MeanReversionStrategy, run_strategy


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="aegis-quant", description="Aegis Quant CLI")
    sub = parser.add_subparsers(dest="command")

    ingest = sub.add_parser("ingest", help="Ingest market data")
    ingest.add_argument("--source", choices=["csv", "yahoo"], default="yahoo")
    ingest.add_argument("--symbol", required=True)
    ingest.add_argument("--csv-path", default="data/sample")

    bt = sub.add_parser("backtest", help="Run backtest")
    bt.add_argument("--strategy", default="mean_reversion")
    bt.add_argument("--symbol", default="BTC-USD")

    api = sub.add_parser("serve", help="Start API server")
    api.add_argument("--port", type=int, default=settings.api_port)

    status = sub.add_parser("status", help="Check API status")
    status.add_argument("--url", default=f"http://localhost:{settings.api_port}")

    args = parser.parse_args(argv)

    if args.command == "ingest":
        engine = MarketDataEngine()
        connector = CSVConnector(args.csv_path) if args.source == "csv" else YahooFinanceConnector()
        n = engine.ingest(connector, args.symbol)
        print(f"Ingested {n} bars for {args.symbol}")
        return 0

    if args.command == "backtest":
        engine = MarketDataEngine()
        df = engine.get_bars(args.symbol)
        if df.empty:
            print(f"No data for {args.symbol}. Run: aegis-quant ingest --symbol {args.symbol}")
            return 1
        df = FeatureEngine().compute_all(df)
        result = run_strategy(MeanReversionStrategy(args.symbol), df)
        print(json.dumps(result.metrics, indent=2))
        return 0

    if args.command == "serve":
        import uvicorn

        uvicorn.run("aegis_quant.api.app:app", host=settings.api_host, port=args.port, reload=False)
        return 0

    if args.command == "status":
        resp = httpx.get(f"{args.url}/health", timeout=5)
        print(resp.json())
        return 0

    parser.print_help()
    return 1


if __name__ == "__main__":
    sys.exit(main())
