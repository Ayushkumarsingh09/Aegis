import { useEffect, useState } from 'react'
import { LineChart, Line, XAxis, YAxis, Tooltip, ResponsiveContainer } from 'recharts'
import { getHealth, getSymbols, getStrategies, listMLModels, api } from '../api'

interface PlatformStatus {
  platform_modules: boolean
  modules: Record<string, boolean | string>
}

export default function Research() {
  const [health, setHealth] = useState('')
  const [symbols, setSymbols] = useState<string[]>([])
  const [strategies, setStrategies] = useState<string[]>([])
  const [modelCount, setModelCount] = useState(0)
  const [platform, setPlatform] = useState<PlatformStatus | null>(null)
  const [prices, setPrices] = useState<{ t: string; close: number }[]>([])

  useEffect(() => {
    getHealth().then(h => setHealth(h.status)).catch(() => setHealth('offline'))
    getStrategies().then(s => setStrategies(s.strategies)).catch(() => {})
    listMLModels().then(r => setModelCount(r.models.length)).catch(() => {})
    api<PlatformStatus>('/api/v1/platform/status').then(setPlatform).catch(() => {})
    getSymbols().then(s => {
      setSymbols(s.symbols)
      if (s.symbols.length) {
        api<{ timestamp: string; close: number }[]>(`/api/v1/data/${s.symbols[0]}`)
          .then(bars => setPrices(bars.map(b => ({ t: b.timestamp.slice(5, 16), close: b.close }))))
          .catch(() => {})
      }
    }).catch(() => {})
  }, [])

  const moduleEntries = platform
    ? Object.entries(platform.modules).filter(([, v]) => typeof v === 'boolean') as [string, boolean][]
    : []

  return (
    <div className="page fade-in">
      <h2>Research Overview</h2>
      <div className="metric-grid" style={{ marginTop: 0 }}>
        <div className="metric">
          <div className="label">API</div>
          <div className={`val ${health === 'healthy' ? 'positive' : 'negative'}`}>{health || '…'}</div>
        </div>
        <div className="metric"><div className="label">Symbols</div><div className="val">{symbols.length}</div></div>
        <div className="metric"><div className="label">Strategies</div><div className="val">{strategies.length}</div></div>
        <div className="metric"><div className="label">Trained Models</div><div className="val">{modelCount}</div></div>
      </div>

      {prices.length > 0 && (
        <div className="card" style={{ marginTop: 16, height: 280 }}>
          <h3>{symbols[0]} — Price History</h3>
          <ResponsiveContainer width="100%" height={220}>
            <LineChart data={prices}>
              <XAxis dataKey="t" tick={{ fill: '#6b7a94', fontSize: 10 }} minTickGap={40} />
              <YAxis domain={['auto', 'auto']} tick={{ fill: '#6b7a94', fontSize: 10 }} />
              <Tooltip contentStyle={{ background: '#161e2e', border: '1px solid #243044' }} />
              <Line type="monotone" dataKey="close" stroke="#6366f1" strokeWidth={2} dot={false} />
            </LineChart>
          </ResponsiveContainer>
        </div>
      )}

      <div className="grid" style={{ marginTop: 16 }}>
        <div className="card">
          <h3>Platform Modules</h3>
          <div style={{ marginTop: 8 }}>
            {moduleEntries.map(([name, up]) => (
              <p key={name} style={{ marginBottom: 6 }}>
                <span className={`badge ${up ? 'green' : 'red'}`}>{up ? 'ACTIVE' : 'OFF'}</span>{' '}
                <span className="muted" style={{ textTransform: 'capitalize' }}>{name.replace(/_/g, ' ')}</span>
              </p>
            ))}
            {!platform && <p className="muted">Loading module status…</p>}
          </div>
        </div>
        <div className="card">
          <h3>Symbols</h3>
          <p className="muted" style={{ marginTop: 8, lineHeight: 2 }}>
            {symbols.length ? symbols.map(s => <span key={s} className="badge blue" style={{ marginRight: 6 }}>{s}</span>) : 'No data ingested — run: aegis-quant ingest'}
          </p>
        </div>
        <div className="card">
          <h3>Strategies</h3>
          <p className="muted" style={{ marginTop: 8, lineHeight: 2 }}>
            {strategies.map(s => <span key={s} className="badge blue" style={{ marginRight: 6 }}>{s}</span>)}
          </p>
        </div>
        <div className="card">
          <h3>Pipeline</h3>
          <p className="muted" style={{ marginTop: 8, lineHeight: 1.8 }}>
            Market Data → Cleaning → Features → Factors → Strategy → Backtest → Execution → Risk → Portfolio → ML
          </p>
        </div>
      </div>
    </div>
  )
}
