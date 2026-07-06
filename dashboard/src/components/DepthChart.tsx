import { BookData } from '../api'
import { AreaChart, Area, XAxis, YAxis, Tooltip, ResponsiveContainer } from 'recharts'
import './DepthChart.css'

interface Props {
  book: BookData | null
}

export default function DepthChart({ book }: Props) {
  if (!book) {
    return <div className="depth-chart loading">Loading depth chart...</div>
  }

  const bidData = book.bids.map(b => ({
    price: b.price,
    bidQty: b.quantity,
    askQty: 0,
  }))

  const askData = book.asks.map(a => ({
    price: a.price,
    bidQty: 0,
    askQty: a.quantity,
  }))

  const data = [...bidData, ...askData].sort((a, b) => a.price - b.price)

  return (
    <div className="depth-chart fade-in">
      <div className="panel-header">
        <h3>Market Depth</h3>
      </div>
      <ResponsiveContainer width="100%" height={280}>
        <AreaChart data={data} margin={{ top: 10, right: 10, left: 0, bottom: 0 }}>
          <XAxis
            dataKey="price"
            tick={{ fill: '#5a6478', fontSize: 11 }}
            tickFormatter={(v: number) => v.toFixed(0)}
          />
          <YAxis tick={{ fill: '#5a6478', fontSize: 11 }} />
          <Tooltip
            contentStyle={{
              background: '#1a2332',
              border: '1px solid #2a3548',
              borderRadius: 6,
              fontFamily: 'JetBrains Mono',
              fontSize: 12,
            }}
          />
          <Area
            type="stepAfter"
            dataKey="bidQty"
            stroke="#10b981"
            fill="rgba(16, 185, 129, 0.15)"
            strokeWidth={2}
          />
          <Area
            type="stepAfter"
            dataKey="askQty"
            stroke="#ef4444"
            fill="rgba(239, 68, 68, 0.15)"
            strokeWidth={2}
          />
        </AreaChart>
      </ResponsiveContainer>
    </div>
  )
}
