import { useEffect, useState } from 'react'
import { LineChart, Line, XAxis, YAxis, Tooltip, ResponsiveContainer, Area, AreaChart } from 'recharts'
import { api, getStrategies, getSymbols } from '../api'

interface Trade { timestamp: string; side: string; quantity: number; price: number; commission: number }
interface BacktestResult {
  strategy: string
  symbol: string
  metrics: Record<string, number>
  n_trades: number
  equity_final: number
  equity_curve: Record<string, number>
  drawdown: Record<string, number>
  rolling_sharpe: Record<string, number>
  trades: Trade[]
}

export default function Backtests() {
  const [strategy, setStrategy] = useState('mean_reversion')
  const [symbol, setSymbol] = useState('BTC-USD')
  const [cash, setCash] = useState(1_000_000)
  const [strategies, setStrategies] = useState<string[]>([])
  const [symbols, setSymbols] = useState<string[]>([])
  const [result, setResult] = useState<BacktestResult | null>(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')

  useEffect(() => {
    getStrategies().then(s => setStrategies(s.strategies)).catch(() => {})
    getSymbols().then(s => {
      setSymbols(s.symbols.length ? s.symbols : ['BTC-USD'])
      if (s.symbols.length) setSymbol(s.symbols[0])
    }).catch(() => {})
  }, [])

  const run = async () => {
    setLoading(true); setError('')
    try {
      const r = await api<BacktestResult>('/api/v1/backtest', {
        method: 'POST', headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ strategy, symbol, initial_cash: cash }),
      })
      setResult(r)
    } catch (e) { setError(String(e)) }
    setLoading(false)
  }

  const toSeries = (obj: Record<string, number>) =>
    Object.entries(obj).map(([t, v]) => ({ t: t.slice(5, 16), v }))

  const equityData = result ? toSeries(result.equity_curve) : []
  const ddData = result ? toSeries(result.drawdown).map(d => ({ ...d, v: d.v * 100 })) : []
  const rsData = result ? toSeries(result.rolling_sharpe) : []

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
        <label className="muted">Capital
          <input type="number" step={100000} value={cash} onChange={e => setCash(+e.target.value)} style={{ width: 110, marginLeft: 8 }} />
        </label>
        <button className="btn" onClick={run} disabled={loading}>{loading ? 'Running…' : 'Run Backtest'}</button>
      </div>
      {error && <p className="negative">{error}</p>}

      {result && (
        <>
          <div className="metric-grid">
            {Object.entries(result.metrics).map(([k, v]) => (
              <div key={k} className="metric">
                <div className="label">{k}</div>
                <div className={`val ${['sharpe', 'sortino', 'calmar', 'total_return'].includes(k) ? (v >= 0 ? 'positive' : 'negative') : ''}`}>{v.toFixed(4)}</div>
              </div>
            ))}
            <div className="metric"><div className="label">trades</div><div className="val">{result.n_trades}</div></div>
            <div className="metric"><div className="label">final equity</div><div className="val">{result.equity_final.toLocaleString(undefined, { maximumFractionDigits: 0 })}</div></div>
          </div>

          <div className="card" style={{ marginTop: 16, height: 300 }}>
            <h3>Equity Curve</h3>
            <ResponsiveContainer width="100%" height={250}>
              <LineChart data={equityData}>
                <XAxis dataKey="t" tick={{ fill: '#6b7a94', fontSize: 10 }} minTickGap={40} />
                <YAxis domain={['auto', 'auto']} tick={{ fill: '#6b7a94', fontSize: 10 }} />
                <Tooltip contentStyle={{ background: '#161e2e', border: '1px solid #243044' }} />
                <Line type="monotone" dataKey="v" name="equity" stroke="#6366f1" strokeWidth={2} dot={false} />
              </LineChart>
            </ResponsiveContainer>
          </div>

          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(340px, 1fr))', gap: 16, marginTop: 16 }}>
            <div className="card" style={{ height: 260 }}>
              <h3>Drawdown (%)</h3>
              <ResponsiveContainer width="100%" height={210}>
                <AreaChart data={ddData}>
                  <XAxis dataKey="t" tick={{ fill: '#6b7a94', fontSize: 10 }} minTickGap={40} />
                  <YAxis tick={{ fill: '#6b7a94', fontSize: 10 }} />
                  <Tooltip contentStyle={{ background: '#161e2e', border: '1px solid #243044' }} />
                  <Area type="monotone" dataKey="v" name="drawdown" stroke="#ef4444" fill="rgba(239,68,68,0.15)" />
                </AreaChart>
              </ResponsiveContainer>
            </div>
            {rsData.length > 0 && (
              <div className="card" style={{ height: 260 }}>
                <h3>Rolling Sharpe (30-bar)</h3>
                <ResponsiveContainer width="100%" height={210}>
                  <LineChart data={rsData}>
                    <XAxis dataKey="t" tick={{ fill: '#6b7a94', fontSize: 10 }} minTickGap={40} />
                    <YAxis tick={{ fill: '#6b7a94', fontSize: 10 }} />
                    <Tooltip contentStyle={{ background: '#161e2e', border: '1px solid #243044' }} />
                    <Line type="monotone" dataKey="v" name="sharpe" stroke="#22c55e" strokeWidth={2} dot={false} />
                  </LineChart>
                </ResponsiveContainer>
              </div>
            )}
          </div>

          {result.trades.length > 0 && (
            <div className="card" style={{ marginTop: 16 }}>
              <h3>Trades (last {result.trades.length})</h3>
              <div style={{ maxHeight: 320, overflowY: 'auto' }}>
                <table className="data-table">
                  <thead><tr><th>Timestamp</th><th>Side</th><th>Qty</th><th>Price</th><th>Commission</th></tr></thead>
                  <tbody>
                    {result.trades.slice().reverse().map((t, i) => (
                      <tr key={i}>
                        <td>{t.timestamp.slice(0, 19)}</td>
                        <td><span className={`badge ${t.side === 'buy' ? 'green' : 'red'}`}>{t.side.toUpperCase()}</span></td>
                        <td>{t.quantity}</td>
                        <td>{t.price.toFixed(2)}</td>
                        <td>{t.commission.toFixed(4)}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>
          )}
        </>
      )}
    </div>
  )
}
