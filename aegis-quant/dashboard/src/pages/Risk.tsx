import { useEffect, useState } from 'react'
import { LineChart, Line, XAxis, YAxis, Tooltip, ResponsiveContainer } from 'recharts'
import { getRisk, getSymbols, api } from '../api'

interface StressResult {
  scenarios: Record<string, number>
  monte_carlo: { var: number; cvar: number; n_sims: number }
  risk: Record<string, number>
}

export default function Risk() {
  const [symbol, setSymbol] = useState('BTC-USD')
  const [symbols, setSymbols] = useState<string[]>([])
  const [metrics, setMetrics] = useState<Record<string, number> | null>(null)
  const [stress, setStress] = useState<StressResult | null>(null)
  const [bars, setBars] = useState<{ timestamp: string; close: number }[]>([])
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')

  useEffect(() => {
    getSymbols().then(s => setSymbols(s.symbols.length ? s.symbols : ['BTC-USD'])).catch(() => {})
  }, [])

  const load = async () => {
    setLoading(true); setError('')
    try {
      const [m, st, b] = await Promise.all([
        getRisk(symbol),
        api<StressResult>(`/api/v1/analytics/stress/${symbol}`).catch(() => null),
        api<{ timestamp: string; close: number }[]>(`/api/v1/data/${symbol}`).catch(() => []),
      ])
      setMetrics(m)
      setStress(st)
      setBars(b)
    } catch (e) { setError(String(e)) }
    setLoading(false)
  }

  // Drawdown series from price data
  let peak = -Infinity
  const ddData = bars.map(b => {
    peak = Math.max(peak, b.close)
    return { t: b.timestamp.slice(5, 16), dd: ((b.close - peak) / peak) * 100 }
  })

  return (
    <div className="page fade-in">
      <h2>Risk Analytics</h2>
      <div className="form-row">
        <select value={symbol} onChange={e => setSymbol(e.target.value)}>
          {symbols.map(s => <option key={s} value={s}>{s}</option>)}
        </select>
        <button className="btn" onClick={load} disabled={loading}>{loading ? 'Analyzing…' : 'Analyze'}</button>
      </div>
      {error && <p className="negative">{error}</p>}

      {metrics && (
        <div className="metric-grid">
          {Object.entries(metrics).map(([k, v]) => (
            <div key={k} className="metric">
              <div className="label">{k}</div>
              <div className={`val ${k.includes('return') || k === 'sharpe' ? (v >= 0 ? 'positive' : 'negative') : ''}`}>{v.toFixed(4)}</div>
            </div>
          ))}
        </div>
      )}

      {ddData.length > 0 && (
        <div className="card" style={{ marginTop: 16, height: 260 }}>
          <h3>Drawdown</h3>
          <ResponsiveContainer width="100%" height={210}>
            <LineChart data={ddData}>
              <XAxis dataKey="t" tick={{ fill: '#6b7a94', fontSize: 10 }} minTickGap={40} />
              <YAxis tick={{ fill: '#6b7a94', fontSize: 10 }} unit="%" />
              <Tooltip contentStyle={{ background: '#161e2e', border: '1px solid #243044' }} />
              <Line type="monotone" dataKey="dd" stroke="#ef4444" strokeWidth={2} dot={false} />
            </LineChart>
          </ResponsiveContainer>
        </div>
      )}

      {stress && (
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(320px, 1fr))', gap: 16, marginTop: 16 }}>
          <div className="card">
            <h3>Stress Scenarios (annualized return)</h3>
            <table className="data-table">
              <thead><tr><th>Scenario</th><th>Impact</th></tr></thead>
              <tbody>
                {Object.entries(stress.scenarios).map(([name, v]) => (
                  <tr key={name}>
                    <td>{name.replace(/_/g, ' ')}</td>
                    <td className={v >= 0 ? 'positive' : 'negative'}>{(v * 100).toFixed(2)}%</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
          <div className="card">
            <h3>Monte Carlo VaR ({stress.monte_carlo.n_sims.toLocaleString()} sims)</h3>
            <div className="metric-grid">
              <div className="metric"><div className="label">VaR 95%</div><div className="val negative">{(stress.monte_carlo.var * 100).toFixed(2)}%</div></div>
              <div className="metric"><div className="label">CVaR 95%</div><div className="val negative">{(stress.monte_carlo.cvar * 100).toFixed(2)}%</div></div>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}
