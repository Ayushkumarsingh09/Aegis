import { useState } from 'react'
import { useExchangeData } from './hooks/useExchangeData'
import StatusBar from './components/StatusBar'
import OrderBook from './components/OrderBook'
import TradesPanel from './components/TradesPanel'
import OrderEntry from './components/OrderEntry'
import DepthChart from './components/DepthChart'
import './App.css'

function App() {
  const [instrumentId, setInstrumentId] = useState(1)
  const { book, trades, status, risk, connected, latency, refresh } = useExchangeData(instrumentId)

  return (
    <div className="app">
      <StatusBar status={status} risk={risk} connected={connected} latency={latency} />

      <div className="instrument-tabs">
        {status?.instruments?.map((inst: { id: number; symbol: string }) => (
          <button
            key={inst.id}
            className={instrumentId === inst.id ? 'active' : ''}
            onClick={() => setInstrumentId(inst.id)}
          >
            {inst.symbol}
          </button>
        )) ?? (
          <>
            <button className={instrumentId === 1 ? 'active' : ''} onClick={() => setInstrumentId(1)}>BTC-USD</button>
            <button className={instrumentId === 2 ? 'active' : ''} onClick={() => setInstrumentId(2)}>ETH-USD</button>
          </>
        )}
      </div>

      <main className="dashboard-grid">
        <section className="panel orderbook-panel">
          <OrderBook book={book} />
        </section>

        <section className="panel chart-panel">
          <DepthChart book={book} />
        </section>

        <section className="panel trades-panel">
          <TradesPanel trades={trades} />
        </section>

        <aside className="sidebar">
          <OrderEntry instrumentId={instrumentId} onOrderSubmitted={refresh} />

          <div className="risk-panel fade-in">
            <h3>Risk Status</h3>
            {risk ? (
              <div className="risk-details">
                <div className="risk-row">
                  <span>Max Order Size</span>
                  <span>{risk.limits.max_order_size.toLocaleString()}</span>
                </div>
                <div className="risk-row">
                  <span>Max Position</span>
                  <span>{risk.limits.max_position.toLocaleString()}</span>
                </div>
                <div className="risk-row">
                  <span>Accounts</span>
                  <span>{Object.keys(risk.accounts).length}</span>
                </div>
              </div>
            ) : (
              <div className="loading-text">Loading...</div>
            )}
          </div>
        </aside>
      </main>
    </div>
  )
}

export default App
