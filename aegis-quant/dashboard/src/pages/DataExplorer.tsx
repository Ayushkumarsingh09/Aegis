import { useEffect, useState } from 'react'
import { LineChart, Line, XAxis, YAxis, Tooltip, ResponsiveContainer, BarChart, Bar } from 'recharts'
import { getSymbols, api } from '../api'

interface BarRow { timestamp: string; open: number; high: number; low: number; close: number; volume: number }

export default function DataExplorer() {
  const [symbols, setSymbols] = useState<string[]>([])
  const [selected, setSelected] = useState('')
  const [bars, setBars] = useState<BarRow[]>([])
  const [features, setFeatures] = useState<string[]>([])
  const [loading, setLoading] = useState(false)

  useEffect(() => {
    getSymbols().then(s => {
      setSymbols(s.symbols)
      if (s.symbols.length) setSelected(s.symbols[0])
    }).catch(() => {})
  }, [])

  useEffect(() => {
    if (!selected) return
    setLoading(true)
    Promise.all([
      api<BarRow[]>(`/api/v1/data/${selected}`).catch(() => [] as BarRow[]),
      api<{ features: string[] }>(`/api/v1/features/${selected}`).then(f => f.features).catch(() => [] as string[]),
    ]).then(([b, f]) => {
      setBars(b)
      setFeatures(f)
      setLoading(false)
    })
  }, [selected])

  const chartData = bars.map(b => ({ t: b.timestamp.slice(5, 16), close: b.close, volume: b.volume }))
  const returns = bars.length > 1
    ? bars.slice(1).map((b, i) => (b.close - bars[i].close) / bars[i].close)
    : []
  const vol = returns.length ? Math.sqrt(returns.reduce((s, r) => s + r * r, 0) / returns.length) * Math.sqrt(252 * 24) : 0

  return (
    <div className="page fade-in">
      <h2>Data Explorer</h2>
      <div className="form-row">
        <select value={selected} onChange={e => setSelected(e.target.value)}>
          {symbols.map(s => <option key={s} value={s}>{s}</option>)}
        </select>
        {loading && <span className="muted">Loading…</span>}
      </div>

      <div className="metric-grid" style={{ marginTop: 0 }}>
        <div className="metric"><div className="label">Bars</div><div className="val">{bars.length}</div></div>
        <div className="metric"><div className="label">Last Close</div><div className="val">{bars.length ? bars[bars.length - 1].close.toFixed(2) : '—'}</div></div>
        <div className="metric"><div className="label">Ann. Volatility</div><div className="val">{(vol * 100).toFixed(1)}%</div></div>
        <div className="metric"><div className="label">Features</div><div className="val">{features.length}</div></div>
      </div>

      {chartData.length > 0 && (
        <>
          <div className="card" style={{ marginTop: 16, height: 300 }}>
            <h3>Price — {selected}</h3>
            <ResponsiveContainer width="100%" height={250}>
              <LineChart data={chartData}>
                <XAxis dataKey="t" tick={{ fill: '#6b7a94', fontSize: 10 }} minTickGap={40} />
                <YAxis domain={['auto', 'auto']} tick={{ fill: '#6b7a94', fontSize: 10 }} />
                <Tooltip contentStyle={{ background: '#161e2e', border: '1px solid #243044' }} />
                <Line type="monotone" dataKey="close" stroke="#6366f1" strokeWidth={2} dot={false} />
              </LineChart>
            </ResponsiveContainer>
          </div>
          <div className="card" style={{ marginTop: 16, height: 220 }}>
            <h3>Volume</h3>
            <ResponsiveContainer width="100%" height={170}>
              <BarChart data={chartData}>
                <XAxis dataKey="t" tick={{ fill: '#6b7a94', fontSize: 10 }} minTickGap={40} />
                <YAxis tick={{ fill: '#6b7a94', fontSize: 10 }} />
                <Tooltip contentStyle={{ background: '#161e2e', border: '1px solid #243044' }} />
                <Bar dataKey="volume" fill="#8b5cf6" />
              </BarChart>
            </ResponsiveContainer>
          </div>
        </>
      )}

      {features.length > 0 && (
        <div className="card" style={{ marginTop: 16 }}>
          <h3>Available Features ({features.length})</h3>
          <p className="muted" style={{ lineHeight: 1.9 }}>
            {features.map(f => <span key={f} className="badge blue" style={{ marginRight: 6 }}>{f}</span>)}
          </p>
        </div>
      )}

      {bars.length > 0 && (
        <div className="card" style={{ marginTop: 16 }}>
          <h3>Latest Bars</h3>
          <table className="data-table">
            <thead><tr><th>Timestamp</th><th>Open</th><th>High</th><th>Low</th><th>Close</th><th>Volume</th></tr></thead>
            <tbody>
              {bars.slice(-10).reverse().map((b, i) => (
                <tr key={i}>
                  <td>{b.timestamp.slice(0, 16)}</td>
                  <td>{b.open.toFixed(2)}</td>
                  <td>{b.high.toFixed(2)}</td>
                  <td>{b.low.toFixed(2)}</td>
                  <td>{b.close.toFixed(2)}</td>
                  <td>{b.volume.toFixed(0)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  )
}
