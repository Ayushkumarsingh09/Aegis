const API = import.meta.env.VITE_API_URL || ''

export async function api<T>(path: string, opts?: RequestInit): Promise<T> {
  const res = await fetch(`${API}${path}`, opts)
  if (!res.ok) throw new Error(await res.text())
  return res.json()
}

export const getHealth = () => api<{ status: string }>('/health')
export const getSymbols = () => api<{ symbols: string[] }>('/api/v1/symbols')
export const getStrategies = () => api<{ strategies: string[] }>('/api/v1/strategies')
export const runBacktest = (body: object) =>
  api('/api/v1/backtest', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(body) })
export const getRisk = (symbol: string) => api<Record<string, number>>(`/api/v1/risk/metrics/${symbol}`)
export const trainML = (symbol: string, model: string) =>
  api('/api/v1/ml/train', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ symbol, model }) })
export const getFactorIC = (symbol: string) =>
  api<{ symbol: string; ic: number; quantile_spread: Record<string, number> }>(`/api/v1/factors/${symbol}/ic`)
export const optimize = (symbols: string[], method: string) =>
  api<{ method: string; weights: Record<string, number> }>('/api/v1/portfolio/optimize', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ symbols, method }) })
