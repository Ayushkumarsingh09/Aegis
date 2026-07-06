import { useEffect, useState } from 'react'
import { LineChart, Line, XAxis, YAxis, Tooltip, ResponsiveContainer } from 'recharts'
import { api, getSymbols } from '../api'

interface MMHistoryPoint { timestamp: string; mid: number; bid: number; ask: number; inventory: number; pnl: number }
interface MMResult {
  pnl: number
  n_fills: number
  avg_spread_captured: number
  max_inventory: number
  fill_rate: number
  history: MMHistoryPoint[]
}

export default function MarketMaking() {
  const [symbols, setSymbols] = useState<string[]>([])
  const [symbol, setSymbol] = useState('BTC-USD')
  const [gamma, setGamma] = useState(0.1)
  const [size, setSize] = useState(5)
  const [result, setResult] = useState<MMResult | null>(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')

  useEffect(() => {
    getSymbols().then(s => {
      setSymbols(s.symbols.length ? s.symbols : ['BTC-USD'])
      if (s.symbols.length) setSymbol(s.symbols[0])
    }).catch(() => setSymbols(['BTC-USD']))
  }, [])

  const run = async () => {
    setLoading(true); setError('')
    try {
      const r = await api<MMResult>('/api/v1/market-maker/simulate', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ symbol, gamma, base_size: size }),
      })
      setResult(r)
    } catch (e) { setError(String(e)) }
    setLoading(false)
  }

  const chartData = result?.history.map(h => ({
    t: h.timestamp.slice(5, 16), pnl: h.pnl, inventory: h.inventory, bid: h.bid, ask: h.ask, mid: h.mid,
  })) ?? []

  return (
    <div className="page fade-in">
      <h2>Market Making</h2>
      <p className="muted" style={{ marginBottom: 16 }}>Avellaneda-Stoikov optimal quoting simulated against historical data.</p>
      <div className="form-row">
        <select value={symbol} onChange={e => setSymbol(e.target.value)}>
          {symbols.map(s => <option key={s} value={s}>{s}</option>)}
        </select>
        <label className="muted">Gamma (risk aversion)
          <input type="number" step="0.01" min={0.01} value={gamma} onChange={e => setGamma(+e.target.value)} style={{ width: 72, marginLeft: 8 }} />
        </label>
        <label className="muted">Quote Size
          <input type="number" min={1} value={size} onChange={e => setSize(+e.target.value)} style={{ width: 64, marginLeft: 8 }} />
        </label>
        <button className="btn" onClick={run} disabled={loading}>{loading ? 'Simulating…' : 'Simulate'}</button>
      </div>
      {error && <p className="negative">{error}</p>}

      {result && (
        <>
          <div className="metric-grid">
            <div className="metric"><div className="label">PnL</div><div className={`val ${result.pnl >= 0 ? 'positive' : 'negative'}`}>{result.pnl.toFixed(2)}</div></div>
            <div className="metric"><div className="label">Fills</div><div className="val">{result.n_fills}</div></div>
            <div className="metric"><div className="label">Spread Captured</div><div className="val">{result.avg_spread_captured.toFixed(4)}</div></div>
            <div className="metric"><div className="label">Max Inventory</div><div className="val">{result.max_inventory.toFixed(1)}</div></div>
            <div className="metric"><div className="label">Fill Rate</div><div className="val">{(result.fill_rate * 100).toFixed(1)}%</div></div>
          </div>

          {chartData.length > 0 && (
            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(340px, 1fr))', gap: 16, marginTop: 16 }}>
              <div className="card" style={{ height: 280 }}>
                <h3>PnL</h3>
                <ResponsiveContainer width="100%" height={220}>
                  <LineChart data={chartData}>
                    <XAxis dataKey="t" tick={{ fill: '#6b7a94', fontSize: 10 }} minTickGap={40} />
                    <YAxis tick={{ fill: '#6b7a94', fontSize: 10 }} />
                    <Tooltip contentStyle={{ background: '#161e2e', border: '1px solid #243044' }} />
                    <Line type="monotone" dataKey="pnl" stroke="#22c55e" strokeWidth={2} dot={false} />
                  </LineChart>
                </ResponsiveContainer>
              </div>
              <div className="card" style={{ height: 280 }}>
                <h3>Inventory</h3>
                <ResponsiveContainer width="100%" height={220}>
                  <LineChart data={chartData}>
                    <XAxis dataKey="t" tick={{ fill: '#6b7a94', fontSize: 10 }} minTickGap={40} />
                    <YAxis tick={{ fill: '#6b7a94', fontSize: 10 }} />
                    <Tooltip contentStyle={{ background: '#161e2e', border: '1px solid #243044' }} />
                    <Line type="monotone" dataKey="inventory" stroke="#8b5cf6" strokeWidth={2} dot={false} />
                  </LineChart>
                </ResponsiveContainer>
              </div>
              <div className="card" style={{ height: 280 }}>
                <h3>Quotes vs Mid</h3>
                <ResponsiveContainer width="100%" height={220}>
                  <LineChart data={chartData.slice(-60)}>
                    <XAxis dataKey="t" tick={{ fill: '#6b7a94', fontSize: 10 }} minTickGap={40} />
                    <YAxis domain={['auto', 'auto']} tick={{ fill: '#6b7a94', fontSize: 10 }} />
                    <Tooltip contentStyle={{ background: '#161e2e', border: '1px solid #243044' }} />
                    <Line type="monotone" dataKey="bid" stroke="#22c55e" strokeWidth={1} dot={false} />
                    <Line type="monotone" dataKey="mid" stroke="#6b7a94" strokeWidth={1} dot={false} strokeDasharray="4 4" />
                    <Line type="monotone" dataKey="ask" stroke="#ef4444" strokeWidth={1} dot={false} />
                  </LineChart>
                </ResponsiveContainer>
              </div>
            </div>
          )}
        </>
      )}
    </div>
  )
}
