import { useEffect, useState } from 'react'
import { getFactorIC, getSymbols } from '../api'

export default function Factors() {
  const [symbols, setSymbols] = useState<string[]>([])
  const [symbol, setSymbol] = useState('BTC-USD')
  const [ic, setIc] = useState<number | null>(null)
  const [spread, setSpread] = useState<Record<string, number>>({})

  useEffect(() => {
    getSymbols().then(r => {
      setSymbols(r.symbols)
      if (r.symbols.length) setSymbol(r.symbols[0])
    })
  }, [])

  const analyze = async () => {
    const r = await getFactorIC(symbol)
    setIc(r.ic)
    setSpread(r.quantile_spread)
  }

  return (
    <div className="page">
      <h2>Factor Research</h2>
      <div className="toolbar">
        <select value={symbol} onChange={e => setSymbol(e.target.value)}>
          {symbols.map(s => <option key={s} value={s}>{s}</option>)}
        </select>
        <button className="btn" onClick={analyze}>Analyze</button>
      </div>
      {ic !== null && (
        <div className="metric-grid">
          <div className="metric"><div className="label">IC (Momentum)</div><div className="val">{ic.toFixed(4)}</div></div>
          <div className="metric"><div className="label">Long-Short Spread</div><div className="val">{(spread.long_short ?? 0).toFixed(4)}</div></div>
          <div className="metric"><div className="label">Top Quantile</div><div className="val">{(spread.top ?? 0).toFixed(4)}</div></div>
          <div className="metric"><div className="label">Bottom Quantile</div><div className="val">{(spread.bottom ?? 0).toFixed(4)}</div></div>
        </div>
      )}
    </div>
  )
}
