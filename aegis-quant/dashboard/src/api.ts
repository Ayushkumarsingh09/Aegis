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

export interface MLMetrics { [k: string]: number }
export interface MLEvaluation {
  confusion_matrix: number[][]
  cv_fold_scores: number[]
  n_train: number
  n_test: number
  roc_curve?: { fpr: number[]; tpr: number[] }
  feature_importance: Record<string, number>
}
export interface MLTrainResult {
  model_id: string
  model: string
  symbol: string
  metrics: MLMetrics
  evaluation: MLEvaluation
  run_id: string
}
export interface MLJobStatus {
  job_id: string
  status: 'pending' | 'running' | 'completed' | 'failed'
  progress: number
  stage: string
  fold_scores: number[]
  result: MLTrainResult | null
  error: string | null
}
export interface MLModelEntry {
  model_id: string
  model_name: string
  symbol: string
  created_at: string
  metrics: MLMetrics
  mlflow_run_id: string
}
export interface MLPrediction {
  timestamp: string
  close: number
  prediction: number
  probability_up: number | null
  actual: number
}

export const startTraining = (symbol: string, model: string, target_horizon: number) =>
  api<{ job_id: string; status: string }>('/api/v1/ml/train', {
    method: 'POST', headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ symbol, model, target_horizon, async_mode: true }),
  })
export const getTrainingStatus = (jobId: string) => api<MLJobStatus>(`/api/v1/ml/train/${jobId}`)
export const listMLModels = () => api<{ models: MLModelEntry[] }>('/api/v1/ml/models')
export const getMLModel = (id: string) => api<MLModelEntry & { evaluation: MLEvaluation }>(`/api/v1/ml/models/${id}`)
export const deleteMLModel = (id: string) => api<{ deleted: string }>(`/api/v1/ml/models/${id}`, { method: 'DELETE' })
export const predictMLModel = (id: string, n_bars = 20) =>
  api<{ predictions: MLPrediction[] }>(`/api/v1/ml/models/${id}/predict`, {
    method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ n_bars }),
  })
export const compareMLModels = (model_ids: string[]) =>
  api<{ comparison: MLModelEntry[] }>('/api/v1/ml/compare', {
    method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ model_ids }),
  })
export const getFactorIC = (symbol: string) =>
  api<{ symbol: string; ic: number; quantile_spread: Record<string, number> }>(`/api/v1/factors/${symbol}/ic`)
export const optimize = (symbols: string[], method: string) =>
  api<{ method: string; weights: Record<string, number> }>('/api/v1/portfolio/optimize', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ symbols, method }) })
