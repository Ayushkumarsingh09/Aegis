import numpy as np
import pandas as pd
from datetime import datetime, timedelta

np.random.seed(42)
n = 500
start = datetime(2024, 1, 1)
timestamps = [start + timedelta(hours=i) for i in range(n)]
price = 50000.0
rows = []
for i, ts in enumerate(timestamps):
    ret = np.random.normal(0, 0.002)
    price *= 1 + ret
    vol = np.random.randint(10, 200)
    rows.append({
        "symbol": "BTC-USD",
        "timestamp": ts,
        "open": price * (1 - abs(ret) / 2),
        "high": price * (1 + abs(ret)),
        "low": price * (1 - abs(ret)),
        "close": price,
        "volume": vol,
    })

df = pd.DataFrame(rows)
df.to_csv("data/sample/BTC-USD.csv", index=False)
try:
    df.to_parquet("data/sample/BTC-USD.parquet", index=False)
except ImportError:
    pass

# ETH sample
price = 3000.0
rows = []
for i, ts in enumerate(timestamps):
    ret = np.random.normal(0, 0.003)
    price *= 1 + ret
    rows.append({
        "symbol": "ETH-USD",
        "timestamp": ts,
        "open": price, "high": price * 1.002, "low": price * 0.998,
        "close": price, "volume": np.random.randint(50, 500),
    })
pd.DataFrame(rows).to_csv("data/sample/ETH-USD.csv", index=False)
print("Sample data generated")
