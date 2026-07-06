import { useState } from 'react'
import { getRisk, getSymbols } from '../api'
import { useEffect } from 'react'

export default function Risk() {
  const [symbol, setSymbol] = useState('BTC-USD')
  const [symbols, setSymbols] = useState<string[]>([])
  const [metrics, setMetrics] = useState<Record<string, number> | null>(null)

  useEffect(() => { getSymbols().then(s => setSymbols(s.symbols.length ? s.symbols : ['BTC-USD'])) }, [])

  const load = async () => {
    const m = await getRisk(symbol)
    setMetrics(m)
  }

  return (
    <div className="page fade-in">
      <h2>Risk Analytics</h2>
      <div className="form-row">
        <select value={symbol} onChange={e => setSymbol(e.target.value)}>
          {symbols.map(s => <option key={s} value={s}>{s}</option>)}
        </select>
        <button className="btn" onClick={load}>Analyze</button>
      </div>
      {metrics && (
        <div className="metric-grid">
          {Object.entries(metrics).map(([k, v]) => (
            <div key={k} className="metric">
              <div className="label">{k}</div>
              <div className={`val ${v >= 0 && k.includes('return') ? 'positive' : ''}`}>{v.toFixed(4)}</div>
            </div>
          ))}
        </div>
      )}
    </div>
  )
}
