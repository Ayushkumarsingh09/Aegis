import { useEffect, useState } from 'react'
import { LineChart, Line, XAxis, YAxis, Tooltip, ResponsiveContainer, ReferenceLine, BarChart, Bar, Cell } from 'recharts'
import { api, getSymbols } from '../api'

interface FactorRow { factor: string; ic: number; abs_ic: number; long_short: number }
interface FactorAnalysis {
  symbol: string
  horizon: number
  table: FactorRow[]
  rolling_ic: { factor: string; series: Record<string, number> }
}

export default function Factors() {
  const [symbols, setSymbols] = useState<string[]>([])
  const [symbol, setSymbol] = useState('BTC-USD')
  const [horizon, setHorizon] = useState(5)
  const [analysis, setAnalysis] = useState<FactorAnalysis | null>(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')

  useEffect(() => {
    getSymbols().then(r => {
      setSymbols(r.symbols)
      if (r.symbols.length) setSymbol(r.symbols[0])
    }).catch(() => {})
  }, [])

  const analyze = async () => {
    setLoading(true); setError('')
    try {
      const r = await api<FactorAnalysis>(`/api/v1/factors/${symbol}/analysis?horizon=${horizon}`)
      setAnalysis(r)
    } catch (e) { setError(String(e)) }
    setLoading(false)
  }

  const rollingData = analysis?.rolling_ic?.series
    ? Object.entries(analysis.rolling_ic.series).map(([t, v]) => ({ t: t.slice(5, 16), ic: v }))
    : []
  const barData = analysis?.table.map(r => ({ factor: r.factor, ic: r.ic })) ?? []

  return (
    <div className="page fade-in">
      <h2>Factor Research</h2>
      <div className="form-row">
        <select value={symbol} onChange={e => setSymbol(e.target.value)}>
          {symbols.map(s => <option key={s} value={s}>{s}</option>)}
        </select>
        <label className="muted">Horizon
          <input type="number" min={1} max={50} value={horizon} onChange={e => setHorizon(+e.target.value)} style={{ width: 64, marginLeft: 8 }} />
        </label>
        <button className="btn" onClick={analyze} disabled={loading}>{loading ? 'Analyzing…' : 'Analyze All Factors'}</button>
      </div>
      {error && <p className="negative">{error}</p>}

      {analysis && (
        <>
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(380px, 1fr))', gap: 16 }}>
            <div className="card">
              <h3>Factor IC Table (fwd {analysis.horizon}-bar returns)</h3>
              <table className="data-table">
                <thead><tr><th>Factor</th><th>IC</th><th>Long-Short Spread</th></tr></thead>
                <tbody>
                  {analysis.table.map(r => (
                    <tr key={r.factor}>
                      <td>{r.factor}</td>
                      <td className={r.ic >= 0 ? 'positive' : 'negative'}>{r.ic.toFixed(4)}</td>
                      <td className={r.long_short >= 0 ? 'positive' : 'negative'}>{r.long_short.toFixed(5)}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
            <div className="card" style={{ height: 340 }}>
              <h3>IC by Factor</h3>
              <ResponsiveContainer width="100%" height={290}>
                <BarChart data={barData} layout="vertical" margin={{ left: 40 }}>
                  <XAxis type="number" tick={{ fill: '#6b7a94', fontSize: 10 }} />
                  <YAxis dataKey="factor" type="category" width={110} tick={{ fill: '#6b7a94', fontSize: 10 }} />
                  <Tooltip contentStyle={{ background: '#161e2e', border: '1px solid #243044' }} />
                  <ReferenceLine x={0} stroke="#6b7a94" />
                  <Bar dataKey="ic">
                    {barData.map((d, i) => <Cell key={i} fill={d.ic >= 0 ? '#22c55e' : '#ef4444'} />)}
                  </Bar>
                </BarChart>
              </ResponsiveContainer>
            </div>
          </div>

          {rollingData.length > 0 && (
            <div className="card" style={{ marginTop: 16, height: 300 }}>
              <h3>Rolling IC (60-bar) — strongest factor: {analysis.rolling_ic.factor}</h3>
              <ResponsiveContainer width="100%" height={240}>
                <LineChart data={rollingData}>
                  <XAxis dataKey="t" tick={{ fill: '#6b7a94', fontSize: 10 }} minTickGap={40} />
                  <YAxis domain={[-1, 1]} tick={{ fill: '#6b7a94', fontSize: 10 }} />
                  <Tooltip contentStyle={{ background: '#161e2e', border: '1px solid #243044' }} />
                  <ReferenceLine y={0} stroke="#6b7a94" strokeDasharray="4 4" />
                  <Line type="monotone" dataKey="ic" stroke="#6366f1" strokeWidth={2} dot={false} />
                </LineChart>
              </ResponsiveContainer>
            </div>
          )}
        </>
      )}
    </div>
  )
}
