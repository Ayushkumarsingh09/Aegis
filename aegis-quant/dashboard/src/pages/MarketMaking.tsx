import { useState } from 'react'
import { api } from '../api'

export default function MarketMaking() {
  const [symbol, setSymbol] = useState('BTC-USD')
  const [gamma, setGamma] = useState(0.1)
  const [result, setResult] = useState<Record<string, number> | null>(null)

  const run = async () => {
    const r = await api<Record<string, number>>('/api/v1/market-maker/simulate', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ symbol, gamma, base_size: 5 }),
    })
    setResult(r)
  }

  return (
    <div className="page fade-in">
      <h2>Market Making</h2>
      <div className="form-row">
        <select value={symbol} onChange={e => setSymbol(e.target.value)}>
          <option>BTC-USD</option>
          <option>ETH-USD</option>
        </select>
        <label>Gamma <input type="number" step="0.01" value={gamma} onChange={e => setGamma(+e.target.value)} /></label>
        <button className="btn" onClick={run}>Simulate</button>
      </div>
      {result && (
        <div className="metric-grid">
          <div className="metric"><div className="label">PnL</div><div className="val">{result.pnl?.toFixed(2)}</div></div>
          <div className="metric"><div className="label">Fills</div><div className="val">{result.n_fills}</div></div>
          <div className="metric"><div className="label">Spread Captured</div><div className="val">{result.avg_spread_captured?.toFixed(4)}</div></div>
          <div className="metric"><div className="label">Max Inventory</div><div className="val">{result.max_inventory?.toFixed(1)}</div></div>
        </div>
      )}
    </div>
  )
}
