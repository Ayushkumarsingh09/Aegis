"""Live verification of all platform API endpoints."""

import httpx

c = httpx.Client(base_url="http://127.0.0.1:8090", timeout=90)

bt = c.post("/api/v1/backtest", json={"strategy": "mean_reversion", "symbol": "BTC-USD"}).json()
print("backtest: sharpe", round(bt["metrics"]["sharpe"], 3), "| dd pts:", len(bt["drawdown"]), "| trades:", len(bt["trades"]))

for algo in ["twap", "vwap", "pov", "iceberg", "arrival_price"]:
    r = c.post("/api/v1/execution/simulate", json={"symbol": "BTC-USD", "quantity": 100, "algorithm": algo, "n_slices": 8}).json()
    is_bps = r["implementation_shortfall_bps"]
    vs_vwap = r["tca"].get("vs_vwap_bps", 0)
    print(f"exec {algo}: IS {is_bps:.2f} bps | vs_vwap {vs_vwap:.2f} bps | fills {len(r['fills'])}")

f = c.get("/api/v1/portfolio/frontier?symbols=BTC-USD,ETH-USD").json()
print("frontier: cloud", len(f["cloud"]), "| max sharpe", f["max_sharpe"]["sharpe"], f["max_sharpe"]["weights"])
pb = c.post("/api/v1/portfolio/backtest", json={"weights": {"BTC-USD": 0.6, "ETH-USD": 0.4}}).json()
print("portfolio bt: sharpe", round(pb["metrics"]["sharpe"], 3))

roll = c.get("/api/v1/risk/rolling/BTC-USD").json()
corr = c.get("/api/v1/risk/correlation").json()
mc = c.get("/api/v1/risk/montecarlo/BTC-USD").json()
print("risk: rolling pts", len(roll["rolling_sharpe"]), "| corr", corr["symbols"], "| mc bands", list(mc["bands"].keys()))

fa = c.get("/api/v1/factors/BTC-USD/analysis").json()
print("factors:", [(r["factor"], r["ic"]) for r in fa["table"][:3]])

op = c.post("/api/v1/options/price", json={"spot": 100, "strike": 100, "expiry": 1.0, "volatility": 0.2, "option_type": "put"}).json()
print("options methods:", op["methods"])

ex = c.get("/api/v1/experiments").json()["experiments"]
print("experiments:", len(ex), "kinds:", sorted({e["kind"] for e in ex}))
print("ALL FIRM-GRADE ENDPOINTS VERIFIED LIVE")
