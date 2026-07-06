import { useCallback, useEffect, useState } from 'react'
import { api } from '../api'

interface Experiment {
  id: string
  created_at: string
  kind: string
  name: string
  symbol: string
  metrics: Record<string, number>
}

const KIND_COLORS: Record<string, string> = {
  backtest: 'blue', execution: 'green', portfolio: 'blue', market_making: 'red',
}

export default function Experiments() {
  const [experiments, setExperiments] = useState<Experiment[]>([])
  const [kindFilter, setKindFilter] = useState('all')
  const [loading, setLoading] = useState(true)

  const refresh = useCallback(() => {
    setLoading(true)
    api<{ experiments: Experiment[] }>('/api/v1/experiments')
      .then(r => setExperiments(r.experiments))
      .catch(() => setExperiments([]))
      .finally(() => setLoading(false))
  }, [])

  useEffect(() => { refresh() }, [refresh])

  const kinds = ['all', ...new Set(experiments.map(e => e.kind))]
  const filtered = kindFilter === 'all' ? experiments : experiments.filter(e => e.kind === kindFilter)

  const keyMetric = (e: Experiment): [string, number] | null => {
    for (const k of ['sharpe', 'is_bps', 'pnl', 'total_return']) {
      if (k in e.metrics) return [k, e.metrics[k]]
    }
    const first = Object.entries(e.metrics)[0]
    return first ?? null
  }

  return (
    <div className="page fade-in">
      <h2>Experiments</h2>
      <p className="muted" style={{ marginBottom: 16 }}>
        Every backtest, execution, portfolio, and market-making run is persisted automatically.
      </p>
      <div className="form-row">
        <select value={kindFilter} onChange={e => setKindFilter(e.target.value)}>
          {kinds.map(k => <option key={k} value={k}>{k}</option>)}
        </select>
        <button className="btn" onClick={refresh} disabled={loading}>{loading ? 'Loading…' : 'Refresh'}</button>
        <span className="muted">{filtered.length} experiments</span>
      </div>

      {filtered.length === 0 && !loading && (
        <div className="card"><p className="muted">No experiments yet — run a backtest, execution, or simulation and it will appear here.</p></div>
      )}

      {filtered.length > 0 && (
        <table className="data-table">
          <thead><tr><th>Time</th><th>Kind</th><th>Name</th><th>Symbol</th><th>Key Metric</th><th>All Metrics</th></tr></thead>
          <tbody>
            {filtered.map(e => {
              const km = keyMetric(e)
              return (
                <tr key={e.id}>
                  <td>{e.created_at.slice(0, 19)}</td>
                  <td><span className={`badge ${KIND_COLORS[e.kind] ?? 'blue'}`}>{e.kind}</span></td>
                  <td>{e.name}</td>
                  <td>{e.symbol}</td>
                  <td>
                    {km && (
                      <span className={km[1] >= 0 ? 'positive' : 'negative'}>
                        {km[0]}: {km[1].toFixed(3)}
                      </span>
                    )}
                  </td>
                  <td style={{ fontSize: 11, color: 'var(--muted)', maxWidth: 360, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
                    {Object.entries(e.metrics).map(([k, v]) => `${k}=${v.toFixed(2)}`).join(' · ')}
                  </td>
                </tr>
              )
            })}
          </tbody>
        </table>
      )}
    </div>
  )
}
