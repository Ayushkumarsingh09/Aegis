import { useState } from 'react'
import { optimize, getSymbols } from '../api'
import { useEffect } from 'react'

export default function Portfolio() {
  const [symbols, setSymbols] = useState<string[]>(['BTC-USD', 'ETH-USD'])
  const [method, setMethod] = useState('max_sharpe')
  const [weights, setWeights] = useState<Record<string, number> | null>(null)

  useEffect(() => {
    getSymbols().then(s => { if (s.symbols.length >= 2) setSymbols(s.symbols.slice(0, 2)) })
  }, [])

  const run = async () => {
    const r = await optimize(symbols, method)
    setWeights(r.weights)
  }

  return (
    <div className="page fade-in">
      <h2>Portfolio Optimization</h2>
      <div className="form-row">
        <select value={method} onChange={e => setMethod(e.target.value)}>
          <option value="max_sharpe">Max Sharpe</option>
          <option value="min_volatility">Min Volatility</option>
          <option value="risk_parity">Risk Parity</option>
          <option value="equal_weight">Equal Weight</option>
        </select>
        <button className="btn" onClick={run}>Optimize</button>
      </div>
      {weights && (
        <div className="metric-grid">
          {Object.entries(weights).map(([sym, w]) => (
            <div key={sym} className="metric">
              <div className="label">{sym}</div>
              <div className="val">{(w * 100).toFixed(1)}%</div>
            </div>
          ))}
        </div>
      )}
    </div>
  )
}
