# Screenshots

Capture screenshots after starting the stack:

```bash
docker compose up --build
```

Recommended captures:

1. **Dashboard** — http://localhost:4000 (order book, depth chart, trades)
2. **Grafana** — http://localhost:4001 (metrics dashboards)
3. **API** — `curl http://localhost:9080/api/v1/status`

Save PNG files to this directory for the README gallery.
