import { Trade } from '../api'
import './TradesPanel.css'

interface Props {
  trades: Trade[]
}

export default function TradesPanel({ trades }: Props) {
  return (
    <div className="trades-panel fade-in">
      <div className="panel-header">
        <h3>Recent Trades</h3>
        <span className="count">{trades.length}</span>
      </div>
      <div className="trades-columns">
        <span>Price</span>
        <span>Size</span>
        <span>Side</span>
        <span>Time</span>
      </div>
      <div className="trades-list">
        {trades.length === 0 ? (
          <div className="no-trades">No trades yet</div>
        ) : (
          trades.map((t, i) => (
            <div key={`${t.trade_id}-${i}`} className={`trade-row ${t.side === 'BUY' ? 'buy' : 'sell'}`}>
              <span className="price">{t.price?.toFixed(2) ?? '—'}</span>
              <span className="qty">{t.quantity?.toLocaleString() ?? '—'}</span>
              <span className="side">{t.side}</span>
              <span className="time">
                {t.timestamp ? new Date(t.timestamp / 1e6).toLocaleTimeString() : '—'}
              </span>
            </div>
          ))
        )}
      </div>
    </div>
  )
}
