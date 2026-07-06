import { useEffect, useState } from 'react'
import { getStrategies, getSymbols, runBacktest } from '../api'

interface Experiment {
  strategy: string
  symbol: string
  metrics: Record<string, number>
}

export default function Experiments() {
  const [experiments, setExperiments] = useState<Experiment[]>([])
  const [strategy, setStrategy] = useState('mean_reversion')
  const [symbol, setSymbol] = useState('BTC-USD')
  const [strategies, setStrategies] = useState<string[]>([])
  const [symbols, setSymbols] = useState<string[]>([])

  useEffect(() => {
    getStrategies().then(r => setStrategies(r.strategies))
    getSymbols().then(r => {
      setSymbols(r.symbols)
      if (r.symbols.length) setSymbol(r.symbols[0])
    })
  }, [])

  const run = async () => {
    const r = await runBacktest({ strategy, symbol }) as { metrics: Record<string, number> }
    setExperiments(prev => [{ strategy, symbol, metrics: r.metrics }, ...prev])
  }

  return (
    <div className="page">
      <h2>Experiments</h2>
      <div className="form-row">
        <select value={strategy} onChange={e => setStrategy(e.target.value)}>
          {strategies.map(s => <option key={s} value={s}>{s}</option>)}
        </select>
        <select value={symbol} onChange={e => setSymbol(e.target.value)}>
          {symbols.map(s => <option key={s} value={s}>{s}</option>)}
        </select>
        <button className="btn" onClick={run}>Run Experiment</button>
      </div>
      <table className="data-table">
        <thead><tr><th>Strategy</th><th>Symbol</th><th>Sharpe</th><th>Max DD</th><th>Return</th></tr></thead>
        <tbody>
          {experiments.map((e, i) => (
            <tr key={i}>
              <td>{e.strategy}</td>
              <td>{e.symbol}</td>
              <td>{e.metrics.sharpe?.toFixed(3)}</td>
              <td>{((e.metrics.max_drawdown ?? 0) * 100).toFixed(2)}%</td>
              <td>{((e.metrics.total_return ?? 0) * 100).toFixed(2)}%</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  )
}
