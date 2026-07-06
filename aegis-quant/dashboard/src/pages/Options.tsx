import { useState } from 'react'
import { api } from '../api'

interface Greeks { delta: number; gamma: number; theta: number; vega: number; rho: number }

export default function Options() {
  const [spot, setSpot] = useState(100)
  const [strike, setStrike] = useState(100)
  const [vol, setVol] = useState(0.2)
  const [price, setPrice] = useState<number | null>(null)
  const [greeks, setGreeks] = useState<Greeks | null>(null)

  const calc = async () => {
    const r = await api<{ price: number; greeks: Greeks }>('/api/v1/options/price', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ spot, strike, expiry: 1.0, rate: 0.05, volatility: vol, option_type: 'call' }),
    })
    setPrice(r.price)
    setGreeks(r.greeks)
  }

  return (
    <div className="page fade-in">
      <h2>Options Analytics</h2>
      <div className="form-row">
        <label>Spot <input type="number" value={spot} onChange={e => setSpot(+e.target.value)} /></label>
        <label>Strike <input type="number" value={strike} onChange={e => setStrike(+e.target.value)} /></label>
        <label>Vol <input type="number" step="0.01" value={vol} onChange={e => setVol(+e.target.value)} /></label>
        <button className="btn" onClick={calc}>Price</button>
      </div>
      {price !== null && greeks && (
        <div className="metric-grid">
          <div className="metric"><div className="label">Price</div><div className="val">{price.toFixed(4)}</div></div>
          <div className="metric"><div className="label">Delta</div><div className="val">{greeks.delta.toFixed(4)}</div></div>
          <div className="metric"><div className="label">Gamma</div><div className="val">{greeks.gamma.toFixed(4)}</div></div>
          <div className="metric"><div className="label">Theta</div><div className="val">{greeks.theta.toFixed(4)}</div></div>
          <div className="metric"><div className="label">Vega</div><div className="val">{greeks.vega.toFixed(4)}</div></div>
        </div>
      )}
    </div>
  )
}
