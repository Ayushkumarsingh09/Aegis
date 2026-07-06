import { BookData } from '../api'
import './OrderBook.css'

interface Props {
  book: BookData | null
  maxLevels?: number
}

export default function OrderBook({ book, maxLevels = 15 }: Props) {
  if (!book) {
    return <div className="orderbook loading">Loading order book...</div>
  }

  const bids = book.bids.slice(0, maxLevels)
  const asks = [...book.asks].slice(0, maxLevels).reverse()
  const maxQty = Math.max(
    ...bids.map(b => b.quantity),
    ...asks.map(a => a.quantity),
    1
  )

  const spread = asks.length > 0 && bids.length > 0
    ? (asks[asks.length - 1]?.price ?? 0) - (bids[0]?.price ?? 0)
    : 0

  return (
    <div className="orderbook fade-in">
      <div className="orderbook-header">
        <h3>Order Book</h3>
        <span className="spread">Spread: {spread.toFixed(2)}</span>
      </div>
      <div className="orderbook-columns">
        <span>Price</span>
        <span>Size</span>
        <span>Orders</span>
      </div>
      <div className="asks">
        {asks.map((level, i) => (
          <div key={`ask-${i}`} className="level ask">
            <div className="depth-bar" style={{ width: `${(level.quantity / maxQty) * 100}%` }} />
            <span className="price">{level.price.toFixed(2)}</span>
            <span className="qty">{level.quantity.toLocaleString()}</span>
            <span className="orders">{level.orders}</span>
          </div>
        ))}
      </div>
      <div className="mid-price">
        {bids[0] && asks.length > 0
          ? (((bids[0].price + (asks[asks.length - 1]?.price ?? bids[0].price)) / 2)).toFixed(2)
          : '—'}
      </div>
      <div className="bids">
        {bids.map((level, i) => (
          <div key={`bid-${i}`} className="level bid">
            <div className="depth-bar" style={{ width: `${(level.quantity / maxQty) * 100}%` }} />
            <span className="price">{level.price.toFixed(2)}</span>
            <span className="qty">{level.quantity.toLocaleString()}</span>
            <span className="orders">{level.orders}</span>
          </div>
        ))}
      </div>
    </div>
  )
}
