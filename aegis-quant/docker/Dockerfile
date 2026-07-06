FROM python:3.11-slim

WORKDIR /app
RUN apt-get update && apt-get install -y build-essential libgomp1 && rm -rf /var/lib/apt/lists/*

COPY pyproject.toml .
COPY aegis_quant/ aegis_quant/
COPY scripts/ scripts/
COPY data/sample/ data/sample/

RUN pip install --no-cache-dir -e ".[dev]" 2>/dev/null || pip install --no-cache-dir .
RUN python scripts/generate_sample_data.py
RUN python -c "
from aegis_quant.data.engine import MarketDataEngine
from aegis_quant.data.connectors import CSVConnector
e = MarketDataEngine()
e.ingest(CSVConnector('data/sample'), 'BTC-USD')
e.ingest(CSVConnector('data/sample'), 'ETH-USD')
print('Data seeded')
"

EXPOSE 8090
CMD ["uvicorn", "aegis_quant.api.app:app", "--host", "0.0.0.0", "--port", "8090"]
