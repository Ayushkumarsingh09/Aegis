import { useEffect, useState } from 'react'
import {
  LineChart, Line, XAxis, YAxis, Tooltip, ResponsiveContainer,
  ScatterChart, Scatter, ZAxis, Legend, BarChart, Bar, Cell,
} from 'recharts'
import { api, getSymbols, optimize } from '../api'

interface FrontierData {
  cloud: { vol: number; ret: number; sharpe: number }[]
  assets: { symbol: string; vol: number; ret: number }[]
  max_sharpe: { vol: number; ret: number; sharpe: number; weights: Record<string, number> }
}
interface PortfolioBacktest {
  weights: Record<string, number>
  metrics: Record<string, number>
  equity_curve: Record<string, number>
  drawdown: Record<string, number>
}

const COLORS = ['#6366f1', '#22c55e', '#f59e0b', '#ec4899', '#06b6d4', '#8b5cf6']

export default function Portfolio() {
  const [symbols, setSymbols] = useState<string[]>([])
  const [method, setMethod] = useState('max_sharpe')
  const [weights, setWeights] = useState<Record<string, number> | null>(null)
  const [frontier, setFrontier] = useState<FrontierData | null>(null)
  const [backtest, setBacktest] = useState<PortfolioBacktest | null>(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')

  useEffect(() => {
    getSymbols().then(s => setSymbols(s.symbols)).catch(() => {})
  }, [])

  const run = async () => {
    if (symbols.length < 2) { setError('Need at least 2 symbols with data ingested'); return }
    setLoading(true); setError('')
    try {
      const opt = await optimize(symbols, method)
      setWeights(opt.weights)
      const [f, bt] = await Promise.all([
        api<FrontierData>(`/api/v1/portfolio/frontier?symbols=${symbols.join(',')}`).catch(() => null),
        api<PortfolioBacktest>('/api/v1/portfolio/backtest', {
          method: 'POST', headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ weights: opt.weights }),
        }).catch(() => null),
      ])
      setFrontier(f)
      setBacktest(bt)
    } catch (e) { setError(String(e)) }
    setLoading(false)
  }

  const weightData = weights
    ? Object.entries(weights).filter(([, w]) => Math.abs(w) > 1e-6).map(([sym, w]) => ({ sym, weight: +(w * 100).toFixed(2) }))
    : []
  const equityData = backtest ? Object.entries(backtest.equity_curve).map(([t, v]) => ({ t: t.slice(5, 16), equity: v })) : []
  const ddData = backtest ? Object.entries(backtest.drawdown).map(([t, v]) => ({ t: t.slice(5, 16), dd: +(v * 100).toFixed(3) })) : []

  return (
    <div className="page fade-in">
      <h2>Portfolio</h2>
      <div className="form-row">
        <select value={method} onChange={e => setMethod(e.target.value)}>
          <option value="max_sharpe">Max Sharpe</option>
          <option value="min_volatility">Min Volatility</option>
          <option value="risk_parity">Risk Parity (HRP)</option>
          <option value="equal_weight">Equal Weight</option>
        </select>
        <span className="muted">{symbols.length} symbols: {symbols.join(', ')}</span>
        <button className="btn" onClick={run} disabled={loading}>{loading ? 'Optimizing…' : 'Optimize & Backtest'}</button>
      </div>
      {error && <p className="negative">{error}</p>}

      {weightData.length > 0 && (
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(340px, 1fr))', gap: 16 }}>
          <div className="card" style={{ height: 280 }}>
            <h3>Optimal Weights ({method})</h3>
            <ResponsiveContainer width="100%" height={220}>
              <BarChart data={weightData}>
                <XAxis dataKey="sym" tick={{ fill: '#6b7a94', fontSize: 11 }} />
                <YAxis unit="%" tick={{ fill: '#6b7a94', fontSize: 10 }} />
                <Tooltip contentStyle={{ background: '#161e2e', border: '1px solid #243044' }} />
                <Bar dataKey="weight">
                  {weightData.map((_, i) => <Cell key={i} fill={COLORS[i % COLORS.length]} />)}
                </Bar>
              </BarChart>
            </ResponsiveContainer>
          </div>

          {frontier && (
            <div className="card" style={{ height: 280 }}>
              <h3>Efficient Frontier (random portfolios)</h3>
              <ResponsiveContainer width="100%" height={220}>
                <ScatterChart>
                  <XAxis dataKey="vol" name="Volatility" tick={{ fill: '#6b7a94', fontSize: 10 }}
                    label={{ value: 'σ (ann.)', fill: '#6b7a94', fontSize: 10, position: 'insideBottom' }} />
                  <YAxis dataKey="ret" name="Return" tick={{ fill: '#6b7a94', fontSize: 10 }} />
                  <ZAxis range={[12, 12]} />
                  <Tooltip contentStyle={{ background: '#161e2e', border: '1px solid #243044' }} />
                  <Legend />
                  <Scatter name="Portfolios" data={frontier.cloud} fill="rgba(99,102,241,0.35)" />
                  <Scatter name="Assets" data={frontier.assets} fill="#f59e0b" />
                  <Scatter name="Max Sharpe" data={[frontier.max_sharpe]} fill="#22c55e" />
                </ScatterChart>
              </ResponsiveContainer>
            </div>
          )}
        </div>
      )}

      {backtest && (
        <>
          <div className="metric-grid">
            {Object.entries(backtest.metrics).map(([k, v]) => (
              <div key={k} className="metric">
                <div className="label">{k}</div>
                <div className={`val ${['sharpe', 'total_return'].includes(k) ? (v >= 0 ? 'positive' : 'negative') : ''}`}>{v.toFixed(4)}</div>
              </div>
            ))}
          </div>
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(340px, 1fr))', gap: 16, marginTop: 16 }}>
            <div className="card" style={{ height: 280 }}>
              <h3>Portfolio Equity</h3>
              <ResponsiveContainer width="100%" height={220}>
                <LineChart data={equityData}>
                  <XAxis dataKey="t" tick={{ fill: '#6b7a94', fontSize: 10 }} minTickGap={40} />
                  <YAxis domain={['auto', 'auto']} tick={{ fill: '#6b7a94', fontSize: 10 }} />
                  <Tooltip contentStyle={{ background: '#161e2e', border: '1px solid #243044' }} />
                  <Line type="monotone" dataKey="equity" stroke="#6366f1" strokeWidth={2} dot={false} />
                </LineChart>
              </ResponsiveContainer>
            </div>
            <div className="card" style={{ height: 280 }}>
              <h3>Portfolio Drawdown (%)</h3>
              <ResponsiveContainer width="100%" height={220}>
                <LineChart data={ddData}>
                  <XAxis dataKey="t" tick={{ fill: '#6b7a94', fontSize: 10 }} minTickGap={40} />
                  <YAxis tick={{ fill: '#6b7a94', fontSize: 10 }} />
                  <Tooltip contentStyle={{ background: '#161e2e', border: '1px solid #243044' }} />
                  <Line type="monotone" dataKey="dd" stroke="#ef4444" strokeWidth={2} dot={false} />
                </LineChart>
              </ResponsiveContainer>
            </div>
          </div>
        </>
      )}
    </div>
  )
}
