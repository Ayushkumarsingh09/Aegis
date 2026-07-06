import { useState } from 'react'
import { submitOrder } from '../api'
import './OrderEntry.css'

interface Props {
  instrumentId: number
  onOrderSubmitted: () => void
}

export default function OrderEntry({ instrumentId, onOrderSubmitted }: Props) {
  const [side, setSide] = useState<'BUY' | 'SELL'>('BUY')
  const [type, setType] = useState('LIMIT')
  const [price, setPrice] = useState('')
  const [quantity, setQuantity] = useState('10')
  const [status, setStatus] = useState('')

  const handleSubmit = async () => {
    try {
      const result = await submitOrder({
        client_order_id: Date.now(),
        account_id: 1,
        instrument_id: instrumentId,
        side,
        type,
        price: price ? parseFloat(price) : undefined,
        quantity: parseInt(quantity, 10),
      })
      setStatus(JSON.stringify(result).slice(0, 100))
      onOrderSubmitted()
    } catch (e) {
      setStatus(`Error: ${e}`)
    }
  }

  return (
    <div className="order-entry fade-in">
      <h3>Order Entry</h3>
      <div className="side-toggle">
        <button className={side === 'BUY' ? 'active buy' : ''} onClick={() => setSide('BUY')}>Buy</button>
        <button className={side === 'SELL' ? 'active sell' : ''} onClick={() => setSide('SELL')}>Sell</button>
      </div>
      <div className="field">
        <label>Type</label>
        <select value={type} onChange={e => setType(e.target.value)}>
          <option value="LIMIT">Limit</option>
          <option value="MARKET">Market</option>
          <option value="IOC">IOC</option>
          <option value="FOK">FOK</option>
          <option value="POST_ONLY">Post Only</option>
        </select>
      </div>
      <div className="field">
        <label>Price</label>
        <input type="number" value={price} onChange={e => setPrice(e.target.value)} placeholder="0.00" step="0.01" />
      </div>
      <div className="field">
        <label>Quantity</label>
        <input type="number" value={quantity} onChange={e => setQuantity(e.target.value)} />
      </div>
      <button className={`submit ${side.toLowerCase()}`} onClick={handleSubmit}>
        {side} {type}
      </button>
      {status && <div className="order-status">{status}</div>}
    </div>
  )
}
