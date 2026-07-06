import { useEffect, useState } from 'react'
import { getSymbols, api } from '../api'

export default function DataExplorer() {
  const [symbols, setSymbols] = useState<string[]>([])
  const [selected, setSelected] = useState('')
  const [bars, setBars] = useState<any[]>([])
  const [features, setFeatures] = useState<string[]>([])

  useEffect(() => {
    getSymbols().then(s => {
      setSymbols(s.symbols)
      if (s.symbols.length) setSelected(s.symbols[0])
    })
  }, [])

  useEffect(() => {
    if (!selected) return
    api<any[]>(`/api/v1/data/${selected}`).then(setBars).catch(() => setBars([]))
    api<{ features: string[] }>(`/api/v1/features/${selected}`).then(f => setFeatures(f.features)).catch(() => {})
  }, [selected])

  return (
    <div className="page fade-in">
      <h2>Data Explorer</h2>
      <div className="form-row">
        <select value={selected} onChange={e => setSelected(e.target.value)}>
          {symbols.map(s => <option key={s} value={s}>{s}</option>)}
        </select>
      </div>
      <div className="grid">
        <div className="card">
          <h3>Bars Loaded</h3>
          <div className="value">{bars.length}</div>
          {bars.length > 0 && <p className="muted">Latest close: {bars[bars.length - 1]?.close?.toFixed(2)}</p>}
        </div>
        <div className="card">
          <h3>Features</h3>
          <div className="value">{features.length}</div>
          <p className="muted">{features.slice(0, 8).join(', ')}{features.length > 8 ? '...' : ''}</p>
        </div>
      </div>
    </div>
  )
}
