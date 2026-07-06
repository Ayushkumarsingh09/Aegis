export class AegisQuantClient {
  constructor(private baseUrl = 'http://localhost:8090') {}

  private async request<T>(path: string, init?: RequestInit): Promise<T> {
    const res = await fetch(`${this.baseUrl}${path}`, {
      ...init,
      headers: { 'Content-Type': 'application/json', ...init?.headers },
    })
    if (!res.ok) throw new Error(await res.text())
    return res.json()
  }

  health() { return this.request<{ status: string }>('/health') }
  symbols() { return this.request<{ symbols: string[] }>('/api/v1/symbols') }
  backtest(strategy: string, symbol: string) {
    return this.request('/api/v1/backtest', { method: 'POST', body: JSON.stringify({ strategy, symbol }) })
  }
  riskMetrics(symbol: string) { return this.request(`/api/v1/risk/metrics/${symbol}`) }
  optimize(symbols: string[], method = 'max_sharpe') {
    return this.request('/api/v1/portfolio/optimize', { method: 'POST', body: JSON.stringify({ symbols, method }) })
  }
}
