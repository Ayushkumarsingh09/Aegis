import { useState } from 'react'
import { trainML, getSymbols } from '../api'
import { useEffect } from 'react'

export default function MLModels() {
  const [symbol, setSymbol] = useState('BTC-USD')
  const [model, setModel] = useState('random_forest')
  const [result, setResult] = useState<any>(null)
  const [loading, setLoading] = useState(false)
  const [symbols, setSymbols] = useState<string[]>([])

  useEffect(() => { getSymbols().then(s => setSymbols(s.symbols.length ? s.symbols : ['BTC-USD'])) }, [])

  const train = async () => {
    setLoading(true)
    try { setResult(await trainML(symbol, model)) } catch (e) { setResult({ error: String(e) }) }
    setLoading(false)
  }

  return (
    <div className="page fade-in">
      <h2>ML Models</h2>
      <div className="form-row">
        <select value={symbol} onChange={e => setSymbol(e.target.value)}>
          {symbols.map(s => <option key={s} value={s}>{s}</option>)}
        </select>
        <select value={model} onChange={e => setModel(e.target.value)}>
          <option value="random_forest">Random Forest</option>
          <option value="logistic_regression">Logistic Regression</option>
          <option value="xgboost">XGBoost</option>
          <option value="lightgbm">LightGBM</option>
        </select>
        <button className="btn" onClick={train} disabled={loading}>{loading ? 'Training...' : 'Train Model'}</button>
      </div>
      {result && !result.error && (
        <div className="card" style={{ marginTop: 16 }}>
          <h3>Results — {result.model}</h3>
          <p className="muted">MLflow Run: {result.run_id}</p>
          <div className="metric-grid">
            {Object.entries(result.metrics || {}).map(([k, v]) => (
              <div key={k} className="metric"><div className="label">{k}</div><div className="val">{(v as number).toFixed(4)}</div></div>
            ))}
          </div>
        </div>
      )}
    </div>
  )
}
