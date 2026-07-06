import { useEffect, useState } from 'react'
import { getHealth, getSymbols, getStrategies } from '../api'

export default function Research() {
  const [health, setHealth] = useState('')
  const [symbols, setSymbols] = useState<string[]>([])
  const [strategies, setStrategies] = useState<string[]>([])

  useEffect(() => {
    getHealth().then(h => setHealth(h.status)).catch(() => setHealth('offline'))
    getSymbols().then(s => setSymbols(s.symbols)).catch(() => {})
    getStrategies().then(s => setStrategies(s.strategies)).catch(() => {})
  }, [])

  return (
    <div className="page fade-in">
      <h2>Research Overview</h2>
      <div className="grid">
        <div className="card">
          <h3>Platform Status</h3>
          <div className={`value ${health === 'healthy' ? 'positive' : 'negative'}`}>{health || '...'}</div>
        </div>
        <div className="card">
          <h3>Symbols</h3>
          <div className="value">{symbols.length}</div>
          <p className="muted">{symbols.join(', ') || 'No data ingested'}</p>
        </div>
        <div className="card">
          <h3>Strategies</h3>
          <div className="value">{strategies.length}</div>
          <p className="muted">{strategies.join(', ')}</p>
        </div>
        <div className="card">
          <h3>Pipeline</h3>
          <p className="muted" style={{ marginTop: 8, lineHeight: 1.8 }}>
            Market Data → Cleaning → Features → Strategy → Backtest → Risk → Portfolio
          </p>
        </div>
      </div>
    </div>
  )
}
