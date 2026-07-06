import { useEffect, useState, useCallback } from 'react'
import { fetchBook, fetchTrades, fetchStatus, fetchRisk, connectEventStream, BookData, Trade, ExchangeStatus, RiskData } from '../api'
import { marketSimulator } from '../simulation'

export function useExchangeData(instrumentId: number) {
  const [book, setBook] = useState<BookData | null>(null)
  const [trades, setTrades] = useState<Trade[]>([])
  const [status, setStatus] = useState<ExchangeStatus | null>(null)
  const [risk, setRisk] = useState<RiskData | null>(null)
  const [connected, setConnected] = useState(false)
  const [simulated, setSimulated] = useState(false)
  const [latency, setLatency] = useState(0)

  const refresh = useCallback(async () => {
    const start = performance.now()
    try {
      const [bookData, tradeData, statusData, riskData] = await Promise.all([
        fetchBook(instrumentId),
        fetchTrades(instrumentId),
        fetchStatus(),
        fetchRisk(),
      ])
      setBook(bookData)
      setTrades(tradeData.slice(-50).reverse())
      setStatus(statusData)
      setRisk(riskData)
      setLatency(Math.round(performance.now() - start))
      setConnected(true)
      setSimulated(false)
    } catch {
      // Backend unavailable — switch to Simulation Mode so the UI stays alive
      setBook(marketSimulator.book(instrumentId))
      setTrades(marketSimulator.nextTrades(instrumentId))
      setStatus(marketSimulator.status())
      setRisk(marketSimulator.risk())
      setLatency(Math.round(performance.now() - start))
      setConnected(false)
      setSimulated(true)
    }
  }, [instrumentId])

  useEffect(() => {
    refresh()
    const interval = setInterval(refresh, 1000)

    const es = connectEventStream((data: unknown) => {
      const msg = data as Record<string, unknown>
      if (msg.type === 'trade') {
        setTrades(prev => [msg as unknown as Trade, ...prev].slice(0, 50))
      }
      if (msg.type === 'book_snapshot') {
        setBook(msg as unknown as BookData)
      }
    })

    return () => {
      clearInterval(interval)
      es.close()
    }
  }, [refresh])

  return { book, trades, status, risk, connected, simulated, latency, refresh }
}
