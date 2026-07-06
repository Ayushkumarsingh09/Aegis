from __future__ import annotations

from contextlib import asynccontextmanager
from datetime import datetime
from typing import Any

import pandas as pd
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from prometheus_client import Counter, Histogram, generate_latest
from pydantic import BaseModel
from starlette.responses import PlainTextResponse, Response

from aegis_quant.backtest.engine import BacktestConfig, EventDrivenBacktester
from aegis_quant.core.config import settings
from aegis_quant.core.logging import get_logger, setup_logging
from aegis_quant.data.engine import MarketDataEngine
from aegis_quant.features.engine import FeatureEngine
from aegis_quant.ml.pipeline import MLPipeline
from aegis_quant.ml.registry import ModelRegistry
from aegis_quant.ml.trainer import TrainingManager
from aegis_quant.portfolio.optimizer import PortfolioOptimizer
from aegis_quant.risk.metrics import RiskEngine
from aegis_quant.attribution.performance import PerformanceAttributor
from aegis_quant.data.feature_store import FeatureStore
from aegis_quant.factors.research import FactorResearchEngine
from aegis_quant.strategy.strategies import STRATEGY_REGISTRY, run_strategy

try:
    from aegis_execution.algorithms import (
        ArrivalPriceExecutor,
        IcebergExecutor,
        OrderSide,
        POVExecutor,
        TWAPExecutor,
        VWAPExecutor,
    )
    from aegis_execution.simulator import ExecutionSimulator as AlgoSim
    from aegis_execution.tca import TransactionCostAnalyzer
    from aegis_options import black_scholes, compute_greeks
    from aegis_options.pricing import american_binomial, monte_carlo_european
    from aegis_options.surface import VolatilitySurface
    from aegis_market_maker.engine import MMConfig
    from aegis_market_maker.simulator import MMSimulator
    from aegis_analytics.risk import RiskAnalytics as PlatformRisk
    from aegis_analytics.stress import StressTester
    PLATFORM_MODULES = True
except ImportError:
    PLATFORM_MODULES = False

setup_logging()
logger = get_logger(__name__)

REQUESTS = Counter("aegis_quant_requests_total", "Total API requests", ["endpoint"])
LATENCY = Histogram("aegis_quant_request_latency_seconds", "Request latency")

data_engine = MarketDataEngine()
feature_engine = FeatureEngine()
risk_engine = RiskEngine()
portfolio_optimizer = PortfolioOptimizer()
ml_pipeline = MLPipeline()
model_registry = ModelRegistry()
training_manager = TrainingManager(model_registry)
feature_store = FeatureStore()
factor_engine = FactorResearchEngine()
attributor = PerformanceAttributor()


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("starting", port=settings.api_port)
    yield
    logger.info("shutdown")


app = FastAPI(
    title="Aegis Quant API",
    version="1.0.0",
    description="Institutional quantitative research platform",
    lifespan=lifespan,
)
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])


class BacktestRequest(BaseModel):
    strategy: str
    symbol: str
    symbol_b: str | None = None
    initial_cash: float = 1_000_000


class OptimizeRequest(BaseModel):
    symbols: list[str]
    method: str = "max_sharpe"


class MLTrainRequest(BaseModel):
    symbol: str
    model: str = "random_forest"
    target_horizon: int = 5
    async_mode: bool = True


class MLPredictRequest(BaseModel):
    n_bars: int = 20


class MLCompareRequest(BaseModel):
    model_ids: list[str]


class ExecutionRequest(BaseModel):
    symbol: str
    quantity: float
    side: str = "buy"
    algorithm: str = "twap"
    n_slices: int = 10


class OptionsRequest(BaseModel):
    spot: float
    strike: float
    expiry: float
    rate: float = 0.05
    volatility: float = 0.2
    option_type: str = "call"


class MarketMakerRequest(BaseModel):
    symbol: str
    gamma: float = 0.1
    base_size: float = 5.0


@app.get("/health")
def health():
    REQUESTS.labels(endpoint="health").inc()
    return {"status": "healthy", "service": "aegis-quant", "version": "1.0.0"}


@app.get("/metrics")
def metrics():
    return PlainTextResponse(generate_latest().decode())


@app.get("/api/v1/symbols")
def list_symbols():
    REQUESTS.labels(endpoint="symbols").inc()
    return {"symbols": data_engine.list_symbols()}


@app.get("/api/v1/data/{symbol}")
def get_bars(symbol: str, start: datetime | None = None, end: datetime | None = None):
    REQUESTS.labels(endpoint="data").inc()
    df = data_engine.get_bars(symbol, start, end)
    if df.empty:
        raise HTTPException(404, f"No data for {symbol}")
    return df.to_dict(orient="records")


@app.get("/api/v1/features/{symbol}")
def get_features(symbol: str):
    REQUESTS.labels(endpoint="features").inc()
    df = data_engine.get_bars(symbol)
    if df.empty:
        raise HTTPException(404, f"No data for {symbol}")
    featured = feature_engine.compute_all(df)
    cols = [c for c in featured.columns if c not in ("symbol", "timestamp")]
    return {"symbol": symbol, "features": cols, "rows": len(featured)}


def _log_experiment(kind: str, name: str, symbol: str, metrics: dict) -> None:
    """Persist an experiment record to DuckDB."""
    import json as _json

    import duckdb

    con = duckdb.connect(settings.duckdb_path)
    con.execute(
        """
        CREATE TABLE IF NOT EXISTS experiments (
            id VARCHAR, created_at TIMESTAMP, kind VARCHAR,
            name VARCHAR, symbol VARCHAR, metrics VARCHAR
        )
        """
    )
    import uuid as _uuid

    con.execute(
        "INSERT INTO experiments VALUES (?, current_timestamp, ?, ?, ?, ?)",
        [_uuid.uuid4().hex[:10], kind, name, symbol, _json.dumps({k: round(float(v), 6) for k, v in metrics.items() if isinstance(v, (int, float))})],
    )
    con.close()


@app.get("/api/v1/experiments")
def list_experiments(limit: int = 50):
    import json as _json

    import duckdb

    con = duckdb.connect(settings.duckdb_path, read_only=True)
    try:
        rows = con.execute(
            "SELECT id, created_at, kind, name, symbol, metrics FROM experiments ORDER BY created_at DESC LIMIT ?",
            [limit],
        ).fetchall()
    except duckdb.CatalogException:
        rows = []
    con.close()
    return {
        "experiments": [
            {
                "id": r[0],
                "created_at": str(r[1]),
                "kind": r[2],
                "name": r[3],
                "symbol": r[4],
                "metrics": _json.loads(r[5]),
            }
            for r in rows
        ]
    }


@app.post("/api/v1/backtest")
def run_backtest(req: BacktestRequest):
    REQUESTS.labels(endpoint="backtest").inc()
    df = data_engine.get_bars(req.symbol)
    if df.empty:
        raise HTTPException(404, f"No data for {req.symbol}")

    strat_cls = STRATEGY_REGISTRY.get(req.strategy)
    if not strat_cls:
        raise HTTPException(400, f"Unknown strategy: {req.strategy}")

    if req.strategy == "pairs_trading" and req.symbol_b:
        strategy = strat_cls(req.symbol, req.symbol_b)
    else:
        strategy = strat_cls(req.symbol)

    bt = EventDrivenBacktester(BacktestConfig(initial_cash=req.initial_cash))
    result = bt.run(df, strategy.get_handler())

    eq = result.equity_curve
    peak = eq.cummax()
    drawdown = ((eq - peak) / peak).fillna(0)
    rets = result.returns
    rolling_sharpe = (
        (rets.rolling(30).mean() / rets.rolling(30).std() * (252**0.5)).fillna(0)
        if len(rets) > 30 else pd.Series(dtype=float)
    )

    trades = [
        {
            "timestamp": str(f.timestamp),
            "side": f.side.value,
            "quantity": round(f.quantity, 4),
            "price": round(f.price, 4),
            "commission": round(f.commission, 4),
        }
        for f in result.fills[-100:]
    ]

    _log_experiment("backtest", req.strategy, req.symbol, result.metrics)

    return {
        "strategy": req.strategy,
        "symbol": req.symbol,
        "metrics": result.metrics,
        "n_trades": len(result.fills),
        "equity_final": float(eq.iloc[-1]) if len(eq) else req.initial_cash,
        "equity_curve": {str(k): round(float(v), 2) for k, v in eq.items()},
        "drawdown": {str(k): round(float(v), 5) for k, v in drawdown.items()},
        "rolling_sharpe": {str(k): round(float(v), 3) for k, v in rolling_sharpe.items()},
        "trades": trades,
    }


@app.post("/api/v1/portfolio/optimize")
def optimize_portfolio(req: OptimizeRequest):
    REQUESTS.labels(endpoint="optimize").inc()
    returns = pd.DataFrame()
    for sym in req.symbols:
        df = data_engine.get_bars(sym)
        if not df.empty:
            returns[sym] = df.set_index("timestamp")["close"].pct_change()
    returns = returns.dropna()
    if returns.empty:
        raise HTTPException(404, "No return data")

    if req.method == "risk_parity":
        weights = portfolio_optimizer.risk_parity(returns)
    elif req.method == "equal_weight":
        weights = portfolio_optimizer.equal_weight(req.symbols)
    else:
        mu = returns.mean() * 252
        cov = portfolio_optimizer.sample_cov(returns)
        weights = portfolio_optimizer.markowitz(mu, cov, req.method)

    return {"method": req.method, "weights": weights.to_dict()}


def _aligned_returns(symbols: list[str]) -> pd.DataFrame:
    returns = pd.DataFrame()
    for sym in symbols:
        df = data_engine.get_bars(sym)
        if not df.empty:
            returns[sym] = df.set_index("timestamp")["close"].pct_change()
    return returns.dropna()


class PortfolioBacktestRequest(BaseModel):
    weights: dict[str, float]
    initial_cash: float = 1_000_000


@app.get("/api/v1/portfolio/frontier")
def efficient_frontier(symbols: str, n_portfolios: int = 3000):
    """Random-portfolio efficient frontier cloud + individual assets + max-Sharpe point."""
    import numpy as np

    syms = [s.strip() for s in symbols.split(",") if s.strip()]
    returns = _aligned_returns(syms)
    if returns.empty or len(returns.columns) < 2:
        raise HTTPException(404, "Need at least 2 symbols with overlapping data")

    mu = returns.mean().values * 252
    cov = returns.cov().values * 252
    rng = np.random.default_rng(42)
    n_assets = len(returns.columns)

    w = rng.dirichlet(np.ones(n_assets), size=n_portfolios)
    port_ret = w @ mu
    port_vol = np.sqrt(np.einsum("ij,jk,ik->i", w, cov, w))
    sharpe = np.where(port_vol > 0, port_ret / port_vol, 0)

    best = int(np.argmax(sharpe))
    # Downsample cloud for the UI
    step = max(1, n_portfolios // 800)
    cloud = [
        {"vol": round(float(port_vol[i]), 5), "ret": round(float(port_ret[i]), 5), "sharpe": round(float(sharpe[i]), 3)}
        for i in range(0, n_portfolios, step)
    ]
    assets = [
        {"symbol": c, "vol": round(float(np.sqrt(cov[i][i])), 5), "ret": round(float(mu[i]), 5)}
        for i, c in enumerate(returns.columns)
    ]
    return {
        "cloud": cloud,
        "assets": assets,
        "max_sharpe": {
            "vol": round(float(port_vol[best]), 5),
            "ret": round(float(port_ret[best]), 5),
            "sharpe": round(float(sharpe[best]), 3),
            "weights": {c: round(float(w[best][i]), 4) for i, c in enumerate(returns.columns)},
        },
    }


@app.post("/api/v1/portfolio/backtest")
def portfolio_backtest(req: PortfolioBacktestRequest):
    """Backtest a fixed-weight portfolio: equity curve + risk metrics."""
    returns = _aligned_returns(list(req.weights.keys()))
    if returns.empty:
        raise HTTPException(404, "No return data for requested symbols")
    weights = pd.Series(req.weights).reindex(returns.columns).fillna(0)
    total = weights.abs().sum()
    if total <= 0:
        raise HTTPException(422, "Weights must not all be zero")
    weights = weights / total

    port_rets = (returns * weights).sum(axis=1)
    equity = req.initial_cash * (1 + port_rets).cumprod()
    peak = equity.cummax()
    drawdown = (equity - peak) / peak
    metrics = risk_engine.compute_all(port_rets, equity)

    _log_experiment("portfolio", "fixed_weights", ",".join(req.weights.keys()), metrics)

    return {
        "weights": weights.round(4).to_dict(),
        "metrics": metrics,
        "equity_curve": {str(k): round(float(v), 2) for k, v in equity.items()},
        "drawdown": {str(k): round(float(v), 5) for k, v in drawdown.items()},
    }


def _build_ml_dataset(symbol: str, target_horizon: int) -> tuple[pd.DataFrame, pd.Series, pd.DataFrame]:
    """Build features/target from stored bars. Returns (X, y, featured_df)."""
    df = data_engine.get_bars(symbol)
    if df.empty:
        raise HTTPException(404, f"No data for {symbol}")
    featured = feature_engine.compute_all(df)
    feature_cols = [
        c for c in featured.columns
        if c not in ("symbol", "timestamp", "open", "high", "low", "close", "volume")
    ]
    X = featured[feature_cols].dropna()
    future_ret = featured["close"].shift(-target_horizon) / featured["close"] - 1
    y = (future_ret > 0).astype(int).loc[X.index]
    # Drop tail rows whose forward return is unknown
    valid = future_ret.loc[X.index].notna()
    return X.loc[valid], y.loc[valid], featured


@app.post("/api/v1/ml/train")
def train_model(req: MLTrainRequest):
    REQUESTS.labels(endpoint="ml_train").inc()
    X, y, _ = _build_ml_dataset(req.symbol, req.target_horizon)
    factory = ml_pipeline.get_factory(req.model)
    params = {"target_horizon": req.target_horizon}

    if req.async_mode:
        job_id = training_manager.submit(
            X, y, factory, req.model, req.symbol, params=params, mlflow_log=ml_pipeline.log_run
        )
        return {"job_id": job_id, "status": "pending"}

    return training_manager.train_sync(
        X, y, factory, req.model, req.symbol, params=params, mlflow_log=ml_pipeline.log_run
    )


@app.get("/api/v1/ml/train/{job_id}")
def train_status(job_id: str):
    job = training_manager.get_job(job_id)
    if job is None:
        raise HTTPException(404, f"Unknown job: {job_id}")
    return {
        "job_id": job.job_id,
        "status": job.status,
        "progress": job.progress,
        "stage": job.stage,
        "fold_scores": job.fold_scores,
        "result": job.result,
        "error": job.error,
    }


@app.get("/api/v1/ml/models")
def list_models():
    REQUESTS.labels(endpoint="ml_models").inc()
    return {"models": model_registry.list_models()}


@app.get("/api/v1/ml/models/{model_id}")
def get_model(model_id: str):
    entry = model_registry.get(model_id)
    if entry is None:
        raise HTTPException(404, f"Model not found: {model_id}")
    return entry


@app.delete("/api/v1/ml/models/{model_id}")
def delete_model(model_id: str):
    if not model_registry.delete(model_id):
        raise HTTPException(404, f"Model not found: {model_id}")
    return {"deleted": model_id}


@app.get("/api/v1/ml/models/{model_id}/download")
def download_model(model_id: str):
    from starlette.responses import FileResponse

    try:
        path = model_registry.artifact_path(model_id)
    except KeyError:
        raise HTTPException(404, f"Model not found: {model_id}")
    return FileResponse(path, filename=f"aegis-model-{model_id}.joblib", media_type="application/octet-stream")


@app.post("/api/v1/ml/models/{model_id}/predict")
def predict_model(model_id: str, req: MLPredictRequest):
    entry = model_registry.get(model_id)
    if entry is None:
        raise HTTPException(404, f"Model not found: {model_id}")
    model = model_registry.load_model(model_id)
    horizon = int(entry.get("params", {}).get("target_horizon", 5))
    X, y, featured = _build_ml_dataset(entry["symbol"], horizon)
    missing = [c for c in entry["feature_cols"] if c not in X.columns]
    if missing:
        raise HTTPException(422, f"Current features missing columns: {missing[:5]}")
    X_recent = X[entry["feature_cols"]].tail(req.n_bars)
    preds = model.predict(X_recent)
    proba = model.predict_proba(X_recent)[:, 1].tolist() if hasattr(model, "predict_proba") else None
    ts = featured.loc[X_recent.index, "timestamp"].astype(str).tolist()
    closes = featured.loc[X_recent.index, "close"].round(2).tolist()
    return {
        "model_id": model_id,
        "symbol": entry["symbol"],
        "predictions": [
            {
                "timestamp": ts[i],
                "close": closes[i],
                "prediction": int(preds[i]),
                "probability_up": round(proba[i], 4) if proba else None,
                "actual": int(y.loc[X_recent.index[i]]),
            }
            for i in range(len(preds))
        ],
    }


@app.post("/api/v1/ml/compare")
def compare_models(req: MLCompareRequest):
    rows = model_registry.compare(req.model_ids)
    if not rows:
        raise HTTPException(404, "No matching models")
    return {"comparison": rows}


@app.get("/api/v1/strategies")
def list_strategies():
    return {"strategies": list(STRATEGY_REGISTRY.keys())}


@app.get("/api/v1/risk/metrics/{symbol}")
def risk_metrics(symbol: str):
    df = data_engine.get_bars(symbol)
    if df.empty:
        raise HTTPException(404, f"No data for {symbol}")
    rets = df["close"].pct_change().dropna()
    eq = (1 + rets).cumprod()
    return risk_engine.compute_all(rets, eq)


@app.post("/api/v1/features/{symbol}/store")
def store_features(symbol: str):
    df = data_engine.get_bars(symbol)
    if df.empty:
        raise HTTPException(404, f"No data for {symbol}")
    featured = feature_engine.compute_all(df)
    count = feature_store.write_features(featured, symbol)
    return {"symbol": symbol, "features_stored": count}


@app.get("/api/v1/features/{symbol}/stored")
def get_stored_features(symbol: str):
    df = feature_store.read_features(symbol)
    if df.empty:
        raise HTTPException(404, f"No stored features for {symbol}")
    return df.to_dict(orient="records")


@app.get("/api/v1/factors/{symbol}/ic")
def factor_ic(symbol: str, horizon: int = 5):
    df = data_engine.get_bars(symbol)
    if df.empty:
        raise HTTPException(404, f"No data for {symbol}")
    featured = feature_engine.compute_all(df)
    fwd = featured["close"].shift(-horizon) / featured["close"] - 1
    ic = factor_engine.factor_ic(featured["momentum_12"], fwd)
    spread = factor_engine.quantile_spread(featured["momentum_12"], fwd)
    return {"symbol": symbol, "ic": ic, "quantile_spread": spread}


FACTOR_CANDIDATES = [
    "momentum_12", "momentum_26", "rsi_14", "macd", "zscore_20",
    "rolling_vol_20", "volume_zscore", "realized_vol_20", "vol_clustering", "volume_profile",
]


@app.get("/api/v1/factors/{symbol}/analysis")
def factor_analysis(symbol: str, horizon: int = 5):
    """Multi-factor IC table + rolling IC of the strongest factor."""
    df = data_engine.get_bars(symbol)
    if df.empty:
        raise HTTPException(404, f"No data for {symbol}")
    featured = feature_engine.compute_all(df)
    fwd = featured["close"].shift(-horizon) / featured["close"] - 1

    table = []
    for factor in FACTOR_CANDIDATES:
        if factor not in featured.columns:
            continue
        series = featured[factor]
        ic = factor_engine.factor_ic(series, fwd)
        spread = factor_engine.quantile_spread(series, fwd)
        table.append({
            "factor": factor,
            "ic": round(ic, 4),
            "abs_ic": round(abs(ic), 4),
            "long_short": round(spread.get("long_short", 0.0), 5),
        })
    table.sort(key=lambda r: r["abs_ic"], reverse=True)

    rolling = {}
    if table:
        best = table[0]["factor"]
        roll = factor_engine.rolling_ic(featured[best], fwd, window=60).dropna()
        ts = featured.loc[roll.index, "timestamp"].astype(str)
        rolling = {"factor": best, "series": {str(t): round(float(v), 4) for t, v in zip(ts, roll)}}

    return {"symbol": symbol, "horizon": horizon, "table": table, "rolling_ic": rolling}


@app.get("/api/v1/risk/rolling/{symbol}")
def risk_rolling(symbol: str, window: int = 30):
    """Rolling Sharpe and volatility series."""
    df = data_engine.get_bars(symbol)
    if df.empty:
        raise HTTPException(404, f"No data for {symbol}")
    rets = df.set_index("timestamp")["close"].pct_change().dropna()
    roll_sharpe = (rets.rolling(window).mean() / rets.rolling(window).std() * (252**0.5)).dropna()
    roll_vol = (rets.rolling(window).std() * (252**0.5)).dropna()
    return {
        "window": window,
        "rolling_sharpe": {str(k): round(float(v), 3) for k, v in roll_sharpe.items()},
        "rolling_vol": {str(k): round(float(v), 4) for k, v in roll_vol.items()},
    }


@app.get("/api/v1/risk/correlation")
def risk_correlation(symbols: str | None = None):
    """Correlation matrix across all (or selected) symbols."""
    syms = [s.strip() for s in symbols.split(",")] if symbols else data_engine.list_symbols()
    returns = _aligned_returns(syms)
    if returns.empty or len(returns.columns) < 2:
        raise HTTPException(404, "Need at least 2 symbols with overlapping data")
    corr = returns.corr().round(3)
    return {"symbols": list(corr.columns), "matrix": corr.values.tolist()}


@app.get("/api/v1/risk/montecarlo/{symbol}")
def risk_montecarlo(symbol: str, n_sims: int = 2000, horizon: int = 60):
    """Monte Carlo fan chart: percentile bands of simulated equity paths."""
    import numpy as np

    df = data_engine.get_bars(symbol)
    if df.empty:
        raise HTTPException(404, f"No data for {symbol}")
    rets = df["close"].pct_change().dropna()
    paths = risk_engine.monte_carlo(rets, n_sims=n_sims, horizon=horizon)
    percentiles = [5, 25, 50, 75, 95]
    bands = {f"p{p}": np.percentile(paths.values, p, axis=0).round(4).tolist() for p in percentiles}
    return {"horizon": horizon, "n_sims": n_sims, "steps": list(range(1, horizon + 1)), "bands": bands}


@app.get("/api/v1/attribution/{symbol}")
def pnl_attribution(symbol: str):
    df = data_engine.get_bars(symbol)
    if df.empty:
        raise HTTPException(404, f"No data for {symbol}")
    strat_cls = STRATEGY_REGISTRY["mean_reversion"]
    bt = EventDrivenBacktester(BacktestConfig())
    result = bt.run(df, strat_cls(symbol).get_handler())
    trades = pd.DataFrame([f.model_dump() for f in result.fills]) if result.fills else pd.DataFrame()
    attr = attributor.trade_pnl_attribution(trades)
    return {"symbol": symbol, "attribution": attr.to_dict(orient="records"), "metrics": result.metrics}


@app.post("/api/v1/execution/simulate")
def simulate_execution(req: ExecutionRequest):
    if not PLATFORM_MODULES:
        raise HTTPException(503, "Platform execution module not installed")
    from datetime import timedelta

    df = data_engine.get_bars(req.symbol)
    if df.empty:
        raise HTTPException(404, f"No data for {req.symbol}")
    start = df["timestamp"].iloc[0].to_pydatetime()
    end = df["timestamp"].iloc[min(len(df) - 1, req.n_slices)].to_pydatetime()
    side = OrderSide.BUY if req.side == "buy" else OrderSide.SELL
    algos = {
        "twap": lambda: TWAPExecutor(req.n_slices),
        "vwap": lambda: VWAPExecutor(req.n_slices),
        "pov": lambda: POVExecutor(participation_rate=0.15, n_slices=req.n_slices),
        "iceberg": lambda: IcebergExecutor(display_pct=0.15, interval_sec=3600),
        "arrival_price": lambda: ArrivalPriceExecutor(urgency=0.6, n_slices=req.n_slices),
    }
    if req.algorithm not in algos:
        raise HTTPException(400, f"Unknown algorithm: {req.algorithm}. Available: {list(algos)}")
    schedule = algos[req.algorithm]().schedule(req.quantity, side, req.symbol, start, end, df)
    result = AlgoSim().run(schedule, df)

    # TCA vs standard benchmarks over the execution window
    window = df.iloc[: max(req.n_slices, 2)]
    benchmarks = {
        "arrival": float(df["close"].iloc[0]),
        "twap": float(window["close"].mean()),
        "vwap": float((window["close"] * window["volume"]).sum() / max(window["volume"].sum(), 1e-9)),
    }
    fills_df = pd.DataFrame([
        {"price": f.price, "quantity": f.quantity, "commission": f.commission,
         "slippage": f.quantity * f.price * f.slippage_bps / 10_000}
        for f in result.fills
    ])
    tca = TransactionCostAnalyzer().analyze(fills_df, benchmarks, req.side) if not fills_df.empty else {}

    _log_experiment("execution", req.algorithm, req.symbol, {
        "is_bps": result.implementation_shortfall_bps, **{k: v for k, v in result.metrics.items()},
    })

    return {
        "algorithm": req.algorithm,
        "avg_price": result.avg_price,
        "implementation_shortfall_bps": result.implementation_shortfall_bps,
        "metrics": result.metrics,
        "tca": tca,
        "benchmarks": benchmarks,
        "fills": [
            {
                "timestamp": str(f.timestamp),
                "quantity": round(f.quantity, 4),
                "price": round(f.price, 4),
                "slippage_bps": round(f.slippage_bps, 3),
                "commission": round(f.commission, 4),
            }
            for f in result.fills
        ],
    }


@app.post("/api/v1/options/price")
def price_option(req: OptionsRequest):
    if not PLATFORM_MODULES:
        raise HTTPException(503, "Platform options module not installed")
    price = black_scholes(req.spot, req.strike, req.expiry, req.rate, req.volatility, req.option_type)
    greeks = compute_greeks(req.spot, req.strike, req.expiry, req.rate, req.volatility, req.option_type)
    binomial = american_binomial(req.spot, req.strike, req.expiry, req.rate, req.volatility, req.option_type, steps=200)
    mc_price, mc_se = monte_carlo_european(req.spot, req.strike, req.expiry, req.rate, req.volatility, req.option_type, n_paths=30_000)
    return {
        "price": price,
        "greeks": greeks.__dict__,
        "methods": {
            "black_scholes": round(price, 4),
            "binomial_american": round(binomial, 4),
            "monte_carlo": round(mc_price, 4),
            "monte_carlo_stderr": round(mc_se, 5),
        },
    }


@app.get("/api/v1/options/surface")
def options_surface(spot: float = 100, rate: float = 0.05):
    if not PLATFORM_MODULES:
        raise HTTPException(503, "Platform options module not installed")
    surface = VolatilitySurface(spot=spot, r=rate)
    for K in [90, 95, 100, 105, 110]:
        iv = 0.2 + (100 - K) * 0.002
        mkt = black_scholes(spot, K, 0.5, rate, iv, "call")
        surface.add_point(0.5, K, mkt)
    return surface.grid(5, 5).to_dict(orient="records")


@app.post("/api/v1/market-maker/simulate")
def simulate_market_maker(req: MarketMakerRequest):
    if not PLATFORM_MODULES:
        raise HTTPException(503, "Platform market-maker module not installed")
    df = data_engine.get_bars(req.symbol)
    if df.empty:
        raise HTTPException(404, f"No data for {req.symbol}")
    config = MMConfig(symbol=req.symbol, gamma=req.gamma, base_size=req.base_size)
    result = MMSimulator(config).run(df)
    history = []
    if not result.history.empty:
        hist = result.history.iloc[:: max(1, len(result.history) // 200)]
        history = [
            {
                "timestamp": str(row["timestamp"]),
                "mid": round(float(row["mid"]), 2),
                "bid": round(float(row["bid"]), 2),
                "ask": round(float(row["ask"]), 2),
                "inventory": round(float(row["inventory"]), 2),
                "pnl": round(float(row["pnl"]), 2),
            }
            for _, row in hist.iterrows()
        ]
    _log_experiment("market_making", f"gamma={req.gamma}", req.symbol, {
        "pnl": result.pnl, "n_fills": result.n_fills, "fill_rate": result.fill_rate,
    })
    return {
        "pnl": result.pnl,
        "n_fills": result.n_fills,
        "avg_spread_captured": result.avg_spread_captured,
        "max_inventory": result.max_inventory,
        "fill_rate": result.fill_rate,
        "history": history,
    }


@app.get("/api/v1/analytics/stress/{symbol}")
def analytics_stress(symbol: str):
    if not PLATFORM_MODULES:
        raise HTTPException(503, "Platform analytics module not installed")
    df = data_engine.get_bars(symbol)
    if df.empty:
        raise HTTPException(404, f"No data for {symbol}")
    rets = df["close"].pct_change().dropna()
    stress = StressTester()
    return {
        "scenarios": stress.scenario_analysis(rets),
        "monte_carlo": stress.monte_carlo_var(rets),
        "risk": PlatformRisk().compute_all(rets, (1 + rets).cumprod()),
    }


@app.get("/api/v1/platform/status")
def platform_status():
    return {
        "platform_modules": PLATFORM_MODULES,
        "modules": {
            "execution": PLATFORM_MODULES,
            "options": PLATFORM_MODULES,
            "market_maker": PLATFORM_MODULES,
            "analytics": PLATFORM_MODULES,
            "quant": True,
            "exchange_url": settings.aegis_exchange_url,
        },
    }


def create_app() -> FastAPI:
    return app
