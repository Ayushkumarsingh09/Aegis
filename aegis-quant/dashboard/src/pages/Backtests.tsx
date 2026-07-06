import { useState } from 'react'
import { LineChart, Line, XAxis, YAxis, Tooltip, ResponsiveContainer } from 'recharts'
import { runBacktest, getStrategies, getSymbols } from '../api'
import { useEffect } from 'react'

export default function Backtests() {
  const [strategy, setStrategy] = useState('mean_reversion')
  const [symbol, setSymbol] = useState('BTC-USD')
  const [strategies, setStrategies] = useState<string[]>([])
  const [symbols, setSymbols] = useState<string[]>([])
  const [result, setResult] = useState<any>(null)
  const [loading, setLoading] = useState(false)

  useEffect(() => {
    getStrategies().then(s => setStrategies(s.strategies))
    getSymbols().then(s => setSymbols(s.symbols.length ? s.symbols : ['BTC-USD']))
  }, [])

  const handleRun = async () => {
    setLoading(true)
    try {
      const r = await runBacktest({ strategy, symbol })
      setResult(r)
    } catch (e) {
      setResult({ error: String(e) })
    }
    setLoading(false)
  }

  const curveData = result?.equity_curve
    ? Object.entries(result.equity_curve).map(([t, v]) => ({ t: t.slice(0, 10), equity: v as number }))
    : []

  return (
    <div className="page fade-in">
      <h2>Backtests</h2>
      <div className="form-row">
        <select value={strategy} onChange={e => setStrategy(e.target.value)}>
          {strategies.map(s => <option key={s} value={s}>{s}</option>)}
        </select>
        <select value={symbol} onChange={e => setSymbol(e.target.value)}>
          {symbols.map(s => <option key={s} value={s}>{s}</option>)}
        </select>
        <button className="btn" onClick={handleRun} disabled={loading}>{loading ? 'Running...' : 'Run Backtest'}</button>
      </div>
      {result && !result.error && (
        <>
          <div className="metric-grid">
            {Object.entries(result.metrics || {}).map(([k, v]) => (
              <div key={k} className="metric">
                <div className="label">{k}</div>
                <div className="val">{(v as number).toFixed(4)}</div>
              </div>
            ))}
          </div>
          {curveData.length > 0 && (
            <div className="card" style={{ marginTop: 20, height: 300 }}>
              <h3>Equity Curve</h3>
              <ResponsiveContainer width="100%" height={250}>
                <LineChart data={curveData}>
                  <XAxis dataKey="t" tick={{ fill: '#6b7a94', fontSize: 10 }} />
                  <YAxis tick={{ fill: '#6b7a94', fontSize: 10 }} />
                  <Tooltip contentStyle={{ background: '#161e2e', border: '1px solid #243044' }} />
                  <Line type="monotone" dataKey="equity" stroke="#6366f1" strokeWidth={2} dot={false} />
                </LineChart>
              </ResponsiveContainer>
            </div>
          )}
        </>
      )}
      {result?.error && <p className="negative">{result.error}</p>}
    </div>
  )
}
