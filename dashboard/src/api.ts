export interface BookLevel {
  price: number
  quantity: number
  orders: number
}

export interface BookData {
  instrument_id: number
  sequence: number
  timestamp: number
  bids: BookLevel[]
  asks: BookLevel[]
}

export interface Trade {
  trade_id: number
  instrument_id: number
  price: number
  quantity: number
  side: string
  sequence: number
  timestamp: number
}

export interface ExchangeStatus {
  service: string
  version: string
  instruments: { id: number; symbol: string }[]
  kill_switch: boolean
  ws_clients: number
}

export interface RiskData {
  kill_switch: boolean
  reason: string
  limits: {
    max_order_size: number
    max_position: number
    max_exposure: number
    daily_loss_limit: number
  }
  accounts: Record<string, {
    net_position: number
    realized_pnl: number
    exposure: number
  }>
}

const API_BASE = import.meta.env.VITE_API_URL || ''

export async function fetchStatus(): Promise<ExchangeStatus> {
  const res = await fetch(`${API_BASE}/api/v1/status`)
  return res.json()
}

export async function fetchBook(instrumentId: number, depth = 20): Promise<BookData> {
  const res = await fetch(`${API_BASE}/api/v1/instruments/${instrumentId}/book?depth=${depth}`)
  return res.json()
}

export async function fetchTrades(instrumentId: number): Promise<Trade[]> {
  const res = await fetch(`${API_BASE}/api/v1/instruments/${instrumentId}/trades`)
  return res.json()
}

export async function fetchRisk(): Promise<RiskData> {
  const res = await fetch(`${API_BASE}/api/v1/risk`)
  return res.json()
}

export async function submitOrder(order: {
  client_order_id: number
  account_id: number
  instrument_id: number
  side: string
  type: string
  price?: number
  quantity: number
  stop_price?: number
}) {
  const res = await fetch(`${API_BASE}/api/v1/orders`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(order),
  })
  return res.json()
}

export function connectEventStream(onMessage: (data: unknown) => void): EventSource {
  const es = new EventSource(`${API_BASE}/api/v1/stream`)
  es.onmessage = (event) => {
    try {
      onMessage(JSON.parse(event.data))
    } catch {
      // ignore parse errors
    }
  }
  return es
}
