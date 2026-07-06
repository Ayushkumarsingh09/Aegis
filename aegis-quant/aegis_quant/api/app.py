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
    from aegis_execution.algorithms import OrderSide, TWAPExecutor, VWAPExecutor
    from aegis_execution.simulator import ExecutionSimulator as AlgoSim
    from aegis_options import black_scholes, compute_greeks
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

    return {
        "strategy": req.strategy,
        "symbol": req.symbol,
        "metrics": result.metrics,
        "n_trades": len(result.fills),
        "equity_final": float(result.equity_curve.iloc[-1]) if len(result.equity_curve) else req.initial_cash,
        "equity_curve": {str(k): v for k, v in result.equity_curve.items()},
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
    algo = TWAPExecutor(req.n_slices) if req.algorithm == "twap" else VWAPExecutor(req.n_slices)
    schedule = algo.schedule(req.quantity, side, req.symbol, start, end, df)
    result = AlgoSim().run(schedule, df)
    return {
        "algorithm": req.algorithm,
        "avg_price": result.avg_price,
        "implementation_shortfall_bps": result.implementation_shortfall_bps,
        "metrics": result.metrics,
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
    return {
        "price": price,
        "greeks": greeks.__dict__,
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
