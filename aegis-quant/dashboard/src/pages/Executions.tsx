import { useState } from 'react'
import { api } from '../api'

export default function Executions() {
  const [symbol, setSymbol] = useState('BTC-USD')
  const [algo, setAlgo] = useState('twap')
  const [result, setResult] = useState<Record<string, unknown> | null>(null)

  const run = async () => {
    const r = await api<Record<string, unknown>>('/api/v1/execution/simulate', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ symbol, quantity: 100, side: 'buy', algorithm: algo, n_slices: 10 }),
    })
    setResult(r)
  }

  return (
    <div className="page fade-in">
      <h2>Execution</h2>
      <div className="form-row">
        <select value={symbol} onChange={e => setSymbol(e.target.value)}>
          <option>BTC-USD</option>
          <option>ETH-USD</option>
        </select>
        <select value={algo} onChange={e => setAlgo(e.target.value)}>
          <option value="twap">TWAP</option>
          <option value="vwap">VWAP</option>
        </select>
        <button className="btn" onClick={run}>Simulate</button>
      </div>
      {result && (
        <div className="metric-grid">
          <div className="metric"><div className="label">Avg Price</div><div className="val">{String(result.avg_price)}</div></div>
          <div className="metric"><div className="label">IS (bps)</div><div className="val">{String(result.implementation_shortfall_bps)}</div></div>
        </div>
      )}
    </div>
  )
}
