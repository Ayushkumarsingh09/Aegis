import { useEffect, useState } from 'react'
import { LineChart, Line, XAxis, YAxis, Tooltip, ResponsiveContainer, Area, AreaChart } from 'recharts'
import { getRisk, getSymbols, api } from '../api'

interface StressResult {
  scenarios: Record<string, number>
  monte_carlo: { var: number; cvar: number; n_sims: number }
  risk: Record<string, number>
}
interface RollingData { rolling_sharpe: Record<string, number>; rolling_vol: Record<string, number> }
interface CorrData { symbols: string[]; matrix: number[][] }
interface MCData { steps: number[]; bands: Record<string, number[]> }

export default function Risk() {
  const [symbol, setSymbol] = useState('BTC-USD')
  const [symbols, setSymbols] = useState<string[]>([])
  const [metrics, setMetrics] = useState<Record<string, number> | null>(null)
  const [stress, setStress] = useState<StressResult | null>(null)
  const [rolling, setRolling] = useState<RollingData | null>(null)
  const [corr, setCorr] = useState<CorrData | null>(null)
  const [mc, setMc] = useState<MCData | null>(null)
  const [bars, setBars] = useState<{ timestamp: string; close: number }[]>([])
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')

  useEffect(() => {
    getSymbols().then(s => {
      setSymbols(s.symbols.length ? s.symbols : ['BTC-USD'])
      if (s.symbols.length) setSymbol(s.symbols[0])
    }).catch(() => {})
  }, [])

  const load = async () => {
    setLoading(true); setError('')
    try {
      const [m, st, roll, correlation, monte, b] = await Promise.all([
        getRisk(symbol),
        api<StressResult>(`/api/v1/analytics/stress/${symbol}`).catch(() => null),
        api<RollingData>(`/api/v1/risk/rolling/${symbol}`).catch(() => null),
        api<CorrData>('/api/v1/risk/correlation').catch(() => null),
        api<MCData>(`/api/v1/risk/montecarlo/${symbol}`).catch(() => null),
        api<{ timestamp: string; close: number }[]>(`/api/v1/data/${symbol}`).catch(() => []),
      ])
      setMetrics(m); setStress(st); setRolling(roll); setCorr(correlation); setMc(monte); setBars(b)
    } catch (e) { setError(String(e)) }
    setLoading(false)
  }

  let peak = -Infinity
  const ddData = bars.map(b => {
    peak = Math.max(peak, b.close)
    return { t: b.timestamp.slice(5, 16), dd: ((b.close - peak) / peak) * 100 }
  })
  const rollData = rolling
    ? Object.keys(rolling.rolling_sharpe).map(t => ({
        t: t.slice(5, 16),
        sharpe: rolling.rolling_sharpe[t],
        vol: rolling.rolling_vol[t],
      }))
    : []
  const mcData = mc
    ? mc.steps.map((s, i) => ({
        step: s,
        p5: mc.bands.p5[i], p25: mc.bands.p25[i], p50: mc.bands.p50[i], p75: mc.bands.p75[i], p95: mc.bands.p95[i],
      }))
    : []

  const corrColor = (v: number) => {
    const alpha = Math.min(1, Math.abs(v))
    return v >= 0 ? `rgba(34,197,94,${alpha * 0.7})` : `rgba(239,68,68,${alpha * 0.7})`
  }

  return (
    <div className="page fade-in">
      <h2>Risk Analytics</h2>
      <div className="form-row">
        <select value={symbol} onChange={e => setSymbol(e.target.value)}>
          {symbols.map(s => <option key={s} value={s}>{s}</option>)}
        </select>
        <button className="btn" onClick={load} disabled={loading}>{loading ? 'Analyzing…' : 'Analyze'}</button>
      </div>
      {error && <p className="negative">{error}</p>}

      {metrics && (
        <div className="metric-grid">
          {Object.entries(metrics).map(([k, v]) => (
            <div key={k} className="metric">
              <div className="label">{k}</div>
              <div className={`val ${k.includes('return') || k === 'sharpe' ? (v >= 0 ? 'positive' : 'negative') : ''}`}>{v.toFixed(4)}</div>
            </div>
          ))}
        </div>
      )}

      {(ddData.length > 0 || rollData.length > 0) && (
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(340px, 1fr))', gap: 16, marginTop: 16 }}>
          {ddData.length > 0 && (
            <div className="card" style={{ height: 260 }}>
              <h3>Drawdown (%)</h3>
              <ResponsiveContainer width="100%" height={210}>
                <AreaChart data={ddData}>
                  <XAxis dataKey="t" tick={{ fill: '#6b7a94', fontSize: 10 }} minTickGap={40} />
                  <YAxis tick={{ fill: '#6b7a94', fontSize: 10 }} />
                  <Tooltip contentStyle={{ background: '#161e2e', border: '1px solid #243044' }} />
                  <Area type="monotone" dataKey="dd" stroke="#ef4444" fill="rgba(239,68,68,0.15)" />
                </AreaChart>
              </ResponsiveContainer>
            </div>
          )}
          {rollData.length > 0 && (
            <div className="card" style={{ height: 260 }}>
              <h3>Rolling Sharpe (30-bar)</h3>
              <ResponsiveContainer width="100%" height={210}>
                <LineChart data={rollData}>
                  <XAxis dataKey="t" tick={{ fill: '#6b7a94', fontSize: 10 }} minTickGap={40} />
                  <YAxis tick={{ fill: '#6b7a94', fontSize: 10 }} />
                  <Tooltip contentStyle={{ background: '#161e2e', border: '1px solid #243044' }} />
                  <Line type="monotone" dataKey="sharpe" stroke="#22c55e" strokeWidth={2} dot={false} />
                </LineChart>
              </ResponsiveContainer>
            </div>
          )}
          {rollData.length > 0 && (
            <div className="card" style={{ height: 260 }}>
              <h3>Rolling Volatility (ann.)</h3>
              <ResponsiveContainer width="100%" height={210}>
                <LineChart data={rollData}>
                  <XAxis dataKey="t" tick={{ fill: '#6b7a94', fontSize: 10 }} minTickGap={40} />
                  <YAxis tick={{ fill: '#6b7a94', fontSize: 10 }} />
                  <Tooltip contentStyle={{ background: '#161e2e', border: '1px solid #243044' }} />
                  <Line type="monotone" dataKey="vol" stroke="#f59e0b" strokeWidth={2} dot={false} />
                </LineChart>
              </ResponsiveContainer>
            </div>
          )}
        </div>
      )}

      {mcData.length > 0 && (
        <div className="card" style={{ marginTop: 16, height: 320 }}>
          <h3>Monte Carlo Fan — {symbol} ({mc?.bands ? '2,000 sims' : ''}, 60 steps)</h3>
          <ResponsiveContainer width="100%" height={260}>
            <AreaChart data={mcData}>
              <XAxis dataKey="step" tick={{ fill: '#6b7a94', fontSize: 10 }} />
              <YAxis domain={['auto', 'auto']} tick={{ fill: '#6b7a94', fontSize: 10 }} />
              <Tooltip contentStyle={{ background: '#161e2e', border: '1px solid #243044' }} />
              <Area type="monotone" dataKey="p95" stroke="none" fill="rgba(99,102,241,0.10)" />
              <Area type="monotone" dataKey="p75" stroke="none" fill="rgba(99,102,241,0.18)" />
              <Area type="monotone" dataKey="p25" stroke="none" fill="rgba(12,16,25,0.9)" />
              <Area type="monotone" dataKey="p5" stroke="none" fill="rgba(12,16,25,0.9)" />
              <Line type="monotone" dataKey="p50" stroke="#6366f1" strokeWidth={2} dot={false} />
            </AreaChart>
          </ResponsiveContainer>
        </div>
      )}

      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(320px, 1fr))', gap: 16, marginTop: 16 }}>
        {corr && (
          <div className="card">
            <h3>Correlation Matrix</h3>
            <table className="data-table" style={{ marginTop: 12 }}>
              <thead>
                <tr><th></th>{corr.symbols.map(s => <th key={s}>{s}</th>)}</tr>
              </thead>
              <tbody>
                {corr.matrix.map((row, i) => (
                  <tr key={i}>
                    <td style={{ fontWeight: 600 }}>{corr.symbols[i]}</td>
                    {row.map((v, j) => (
                      <td key={j} style={{ background: corrColor(v), textAlign: 'center' }}>{v.toFixed(2)}</td>
                    ))}
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
        {stress && (
          <div className="card">
            <h3>Stress Scenarios (annualized)</h3>
            <table className="data-table">
              <thead><tr><th>Scenario</th><th>Impact</th></tr></thead>
              <tbody>
                {Object.entries(stress.scenarios).map(([name, v]) => (
                  <tr key={name}>
                    <td>{name.replace(/_/g, ' ')}</td>
                    <td className={v >= 0 ? 'positive' : 'negative'}>{(v * 100).toFixed(2)}%</td>
                  </tr>
                ))}
              </tbody>
            </table>
            <div className="metric-grid" style={{ marginTop: 12 }}>
              <div className="metric"><div className="label">MC VaR 95%</div><div className="val negative">{(stress.monte_carlo.var * 100).toFixed(2)}%</div></div>
              <div className="metric"><div className="label">MC CVaR 95%</div><div className="val negative">{(stress.monte_carlo.cvar * 100).toFixed(2)}%</div></div>
            </div>
          </div>
        )}
      </div>
    </div>
  )
}
