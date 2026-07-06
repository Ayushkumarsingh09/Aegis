import { useState } from 'react'
import { LineChart, Line, XAxis, YAxis, Tooltip, ResponsiveContainer, Legend } from 'recharts'
import { api } from '../api'

interface Greeks { delta: number; gamma: number; theta: number; vega: number; rho: number }
interface SurfacePoint { expiry: number; strike: number; iv: number }

export default function Options() {
  const [spot, setSpot] = useState(100)
  const [strike, setStrike] = useState(100)
  const [expiry, setExpiry] = useState(1.0)
  const [vol, setVol] = useState(0.2)
  const [optType, setOptType] = useState<'call' | 'put'>('call')
  const [price, setPrice] = useState<number | null>(null)
  const [greeks, setGreeks] = useState<Greeks | null>(null)
  const [payoff, setPayoff] = useState<{ s: number; price: number; delta: number }[]>([])
  const [surface, setSurface] = useState<SurfacePoint[]>([])
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')

  const calc = async () => {
    setLoading(true); setError('')
    try {
      const r = await api<{ price: number; greeks: Greeks }>('/api/v1/options/price', {
        method: 'POST', headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ spot, strike, expiry, rate: 0.05, volatility: vol, option_type: optType }),
      })
      setPrice(r.price)
      setGreeks(r.greeks)

      // Price/delta profile across spot range — real backend calls
      const spots = Array.from({ length: 21 }, (_, i) => strike * (0.7 + i * 0.03))
      const rows = await Promise.all(spots.map(async s => {
        const p = await api<{ price: number; greeks: Greeks }>('/api/v1/options/price', {
          method: 'POST', headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ spot: s, strike, expiry, rate: 0.05, volatility: vol, option_type: optType }),
        })
        return { s: +s.toFixed(1), price: +p.price.toFixed(4), delta: +p.greeks.delta.toFixed(4) }
      }))
      setPayoff(rows)

      const surf = await api<SurfacePoint[]>(`/api/v1/options/surface?spot=${spot}&rate=0.05`)
      setSurface(surf)
    } catch (e) { setError(String(e)) }
    setLoading(false)
  }

  // Group surface into smile lines per expiry
  const expiries = [...new Set(surface.map(p => p.expiry))]
  const smileData = [...new Set(surface.map(p => p.strike))].sort((a, b) => a - b).map(K => {
    const row: Record<string, number> = { strike: +K.toFixed(1) }
    for (const T of expiries) {
      const pt = surface.find(p => p.strike === K && p.expiry === T)
      if (pt) row[`T=${T.toFixed(2)}`] = +pt.iv.toFixed(4)
    }
    return row
  })

  return (
    <div className="page fade-in">
      <h2>Options Analytics</h2>
      <div className="form-row">
        <label className="muted">Spot <input type="number" value={spot} onChange={e => setSpot(+e.target.value)} style={{ width: 80, marginLeft: 6 }} /></label>
        <label className="muted">Strike <input type="number" value={strike} onChange={e => setStrike(+e.target.value)} style={{ width: 80, marginLeft: 6 }} /></label>
        <label className="muted">Expiry (y) <input type="number" step="0.05" value={expiry} onChange={e => setExpiry(+e.target.value)} style={{ width: 70, marginLeft: 6 }} /></label>
        <label className="muted">Vol <input type="number" step="0.01" value={vol} onChange={e => setVol(+e.target.value)} style={{ width: 70, marginLeft: 6 }} /></label>
        <select value={optType} onChange={e => setOptType(e.target.value as 'call' | 'put')}>
          <option value="call">Call</option>
          <option value="put">Put</option>
        </select>
        <button className="btn" onClick={calc} disabled={loading}>{loading ? 'Pricing…' : 'Price'}</button>
      </div>
      {error && <p className="negative">{error}</p>}

      {price !== null && greeks && (
        <div className="metric-grid">
          <div className="metric"><div className="label">Price</div><div className="val positive">{price.toFixed(4)}</div></div>
          <div className="metric"><div className="label">Delta</div><div className="val">{greeks.delta.toFixed(4)}</div></div>
          <div className="metric"><div className="label">Gamma</div><div className="val">{greeks.gamma.toFixed(4)}</div></div>
          <div className="metric"><div className="label">Theta</div><div className="val">{greeks.theta.toFixed(4)}</div></div>
          <div className="metric"><div className="label">Vega</div><div className="val">{greeks.vega.toFixed(4)}</div></div>
          <div className="metric"><div className="label">Rho</div><div className="val">{greeks.rho.toFixed(4)}</div></div>
        </div>
      )}

      {payoff.length > 0 && (
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(340px, 1fr))', gap: 16, marginTop: 16 }}>
          <div className="card" style={{ height: 300 }}>
            <h3>Price vs Spot</h3>
            <ResponsiveContainer width="100%" height={240}>
              <LineChart data={payoff}>
                <XAxis dataKey="s" tick={{ fill: '#6b7a94', fontSize: 10 }} />
                <YAxis tick={{ fill: '#6b7a94', fontSize: 10 }} />
                <Tooltip contentStyle={{ background: '#161e2e', border: '1px solid #243044' }} />
                <Line type="monotone" dataKey="price" stroke="#6366f1" strokeWidth={2} dot={false} />
              </LineChart>
            </ResponsiveContainer>
          </div>
          <div className="card" style={{ height: 300 }}>
            <h3>Delta vs Spot</h3>
            <ResponsiveContainer width="100%" height={240}>
              <LineChart data={payoff}>
                <XAxis dataKey="s" tick={{ fill: '#6b7a94', fontSize: 10 }} />
                <YAxis domain={[-1, 1]} tick={{ fill: '#6b7a94', fontSize: 10 }} />
                <Tooltip contentStyle={{ background: '#161e2e', border: '1px solid #243044' }} />
                <Line type="monotone" dataKey="delta" stroke="#22c55e" strokeWidth={2} dot={false} />
              </LineChart>
            </ResponsiveContainer>
          </div>
        </div>
      )}

      {smileData.length > 0 && (
        <div className="card" style={{ marginTop: 16, height: 320 }}>
          <h3>Volatility Smile (IV by strike per expiry)</h3>
          <ResponsiveContainer width="100%" height={260}>
            <LineChart data={smileData}>
              <XAxis dataKey="strike" tick={{ fill: '#6b7a94', fontSize: 10 }} />
              <YAxis domain={['auto', 'auto']} tick={{ fill: '#6b7a94', fontSize: 10 }} />
              <Tooltip contentStyle={{ background: '#161e2e', border: '1px solid #243044' }} />
              <Legend />
              {expiries.map((T, i) => (
                <Line key={T} type="monotone" dataKey={`T=${T.toFixed(2)}`}
                  stroke={['#6366f1', '#22c55e', '#f59e0b', '#ec4899', '#06b6d4'][i % 5]} strokeWidth={2} dot={false} />
              ))}
            </LineChart>
          </ResponsiveContainer>
        </div>
      )}
    </div>
  )
}
