import { useEffect, useState } from 'react'
import { LineChart, Line, XAxis, YAxis, Tooltip, ResponsiveContainer } from 'recharts'
import { api, getSymbols } from '../api'

interface Fill { timestamp: string; quantity: number; price: number; slippage_bps: number; commission: number }
interface ExecResult {
  algorithm: string
  avg_price: number
  implementation_shortfall_bps: number
  metrics: Record<string, number>
  tca: Record<string, number>
  benchmarks: Record<string, number>
  fills: Fill[]
}

export default function Executions() {
  const [symbols, setSymbols] = useState<string[]>([])
  const [symbol, setSymbol] = useState('BTC-USD')
  const [algo, setAlgo] = useState('twap')
  const [quantity, setQuantity] = useState(100)
  const [slices, setSlices] = useState(10)
  const [result, setResult] = useState<ExecResult | null>(null)
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
      const r = await api<ExecResult>('/api/v1/execution/simulate', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ symbol, quantity, side: 'buy', algorithm: algo, n_slices: slices }),
      })
      setResult(r)
    } catch (e) { setError(String(e)) }
    setLoading(false)
  }

  const fillData = result?.fills.map((f, i) => ({
    slice: i + 1, price: f.price, slippage: f.slippage_bps, qty: f.quantity,
  })) ?? []

  return (
    <div className="page fade-in">
      <h2>Execution</h2>
      <div className="form-row">
        <select value={symbol} onChange={e => setSymbol(e.target.value)}>
          {symbols.map(s => <option key={s} value={s}>{s}</option>)}
        </select>
        <select value={algo} onChange={e => setAlgo(e.target.value)}>
          <option value="twap">TWAP</option>
          <option value="vwap">VWAP</option>
          <option value="pov">POV (15%)</option>
          <option value="iceberg">Iceberg</option>
          <option value="arrival_price">Arrival Price</option>
        </select>
        <label className="muted">Qty
          <input type="number" min={1} value={quantity} onChange={e => setQuantity(+e.target.value)} style={{ width: 80, marginLeft: 8 }} />
        </label>
        <label className="muted">Slices
          <input type="number" min={1} max={50} value={slices} onChange={e => setSlices(+e.target.value)} style={{ width: 64, marginLeft: 8 }} />
        </label>
        <button className="btn" onClick={run} disabled={loading}>{loading ? 'Simulating…' : 'Simulate'}</button>
      </div>
      {error && <p className="negative">{error}</p>}

      {result && (
        <>
          <div className="metric-grid">
            <div className="metric"><div className="label">Algorithm</div><div className="val">{result.algorithm.toUpperCase()}</div></div>
            <div className="metric"><div className="label">Avg Fill Price</div><div className="val">{result.avg_price.toFixed(2)}</div></div>
            <div className="metric">
              <div className="label">Impl. Shortfall</div>
              <div className={`val ${result.implementation_shortfall_bps <= 0 ? 'positive' : 'negative'}`}>
                {result.implementation_shortfall_bps.toFixed(2)} bps
              </div>
            </div>
            <div className="metric"><div className="label">Fill Rate</div><div className="val">{((result.metrics.fill_rate ?? 0) * 100).toFixed(1)}%</div></div>
            <div className="metric"><div className="label">Avg Slippage</div><div className="val">{(result.metrics.avg_slippage_bps ?? 0).toFixed(2)} bps</div></div>
            <div className="metric"><div className="label">Fills</div><div className="val">{result.fills.length}</div></div>
          </div>

          {result.tca && Object.keys(result.tca).length > 0 && (
            <div className="card" style={{ marginTop: 16 }}>
              <h3>Transaction Cost Analysis</h3>
              <table className="data-table">
                <thead><tr><th>Benchmark</th><th>Benchmark Price</th><th>Cost vs Benchmark</th></tr></thead>
                <tbody>
                  {(['arrival', 'twap', 'vwap'] as const).map(b => (
                    <tr key={b}>
                      <td>{b.toUpperCase()}</td>
                      <td>{result.benchmarks[b]?.toFixed(2) ?? '—'}</td>
                      <td className={(result.tca[`vs_${b}_bps`] ?? 0) <= 0 ? 'positive' : 'negative'}>
                        {(result.tca[`vs_${b}_bps`] ?? 0).toFixed(2)} bps
                      </td>
                    </tr>
                  ))}
                  <tr><td>Commission</td><td>—</td><td>{(result.tca.commission_bps ?? 0).toFixed(2)} bps</td></tr>
                  <tr><td>Slippage</td><td>—</td><td>{(result.tca.slippage_bps ?? 0).toFixed(2)} bps</td></tr>
                </tbody>
              </table>
            </div>
          )}

          {fillData.length > 0 && (
            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(340px, 1fr))', gap: 16, marginTop: 16 }}>
              <div className="card" style={{ height: 280 }}>
                <h3>Fill Prices</h3>
                <ResponsiveContainer width="100%" height={220}>
                  <LineChart data={fillData}>
                    <XAxis dataKey="slice" tick={{ fill: '#6b7a94', fontSize: 10 }} />
                    <YAxis domain={['auto', 'auto']} tick={{ fill: '#6b7a94', fontSize: 10 }} />
                    <Tooltip contentStyle={{ background: '#161e2e', border: '1px solid #243044' }} />
                    <Line type="monotone" dataKey="price" stroke="#6366f1" strokeWidth={2} />
                  </LineChart>
                </ResponsiveContainer>
              </div>
              <div className="card" style={{ height: 280 }}>
                <h3>Slippage per Slice (bps)</h3>
                <ResponsiveContainer width="100%" height={220}>
                  <LineChart data={fillData}>
                    <XAxis dataKey="slice" tick={{ fill: '#6b7a94', fontSize: 10 }} />
                    <YAxis tick={{ fill: '#6b7a94', fontSize: 10 }} />
                    <Tooltip contentStyle={{ background: '#161e2e', border: '1px solid #243044' }} />
                    <Line type="monotone" dataKey="slippage" stroke="#f59e0b" strokeWidth={2} />
                  </LineChart>
                </ResponsiveContainer>
              </div>
            </div>
          )}

          <div className="card" style={{ marginTop: 16 }}>
            <h3>Child Order Fills</h3>
            <table className="data-table">
              <thead><tr><th>#</th><th>Timestamp</th><th>Qty</th><th>Price</th><th>Slippage (bps)</th><th>Commission</th></tr></thead>
              <tbody>
                {result.fills.map((f, i) => (
                  <tr key={i}>
                    <td>{i + 1}</td>
                    <td>{f.timestamp.slice(0, 19)}</td>
                    <td>{f.quantity.toFixed(2)}</td>
                    <td>{f.price.toFixed(2)}</td>
                    <td>{f.slippage_bps.toFixed(2)}</td>
                    <td>{f.commission.toFixed(4)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </>
      )}
    </div>
  )
}
