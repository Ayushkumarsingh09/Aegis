import { BookData, BookLevel, ExchangeStatus, RiskData, Trade } from './api'

/**
 * Simulation Mode — generates a realistic random-walk market when the
 * exchange backend is unreachable, so the dashboard always demonstrates
 * full functionality.
 */
class MarketSimulator {
  private mid = 50_000
  private sequence = 1
  private tradeId = 1
  private trades: Trade[] = []

  private step(): void {
    // Random walk with mild mean reversion
    const drift = (50_000 - this.mid) * 0.0005
    this.mid = Math.max(1_000, this.mid * (1 + (Math.random() - 0.5) * 0.0012) + drift)
  }

  private levels(side: 'bid' | 'ask', count: number): BookLevel[] {
    const out: BookLevel[] = []
    const tick = Math.max(0.5, this.mid * 0.00005)
    const half = this.mid * 0.0001 + tick
    for (let i = 0; i < count; i++) {
      const offset = half + i * tick * (1 + Math.random() * 0.5)
      const price = side === 'bid' ? this.mid - offset : this.mid + offset
      // Liquidity grows with depth, with noise
      const quantity = Math.round((2 + i * 1.5 + Math.random() * 8) * 10) / 10
      out.push({ price: Math.round(price * 100) / 100, quantity, orders: 1 + Math.floor(Math.random() * 4) })
    }
    return out
  }

  book(instrumentId: number): BookData {
    this.step()
    return {
      instrument_id: instrumentId,
      sequence: this.sequence++,
      timestamp: Date.now() * 1e6,
      bids: this.levels('bid', 20),
      asks: this.levels('ask', 20),
    }
  }

  nextTrades(instrumentId: number): Trade[] {
    // 0–3 trades per tick
    const n = Math.random() < 0.55 ? Math.floor(Math.random() * 3) + 1 : 0
    for (let i = 0; i < n; i++) {
      const aggressive = Math.random() > 0.5 ? 'BUY' : 'SELL'
      const slip = this.mid * 0.0001 * Math.random()
      this.trades.unshift({
        trade_id: this.tradeId++,
        instrument_id: instrumentId,
        price: Math.round((aggressive === 'BUY' ? this.mid + slip : this.mid - slip) * 100) / 100,
        quantity: Math.round((0.1 + Math.random() * 5) * 100) / 100,
        side: aggressive,
        sequence: this.sequence++,
        timestamp: Date.now() * 1e6,
      })
    }
    this.trades = this.trades.slice(0, 50)
    return [...this.trades]
  }

  status(): ExchangeStatus {
    return {
      service: 'aegis-exchange (simulation)',
      version: 'sim',
      instruments: [{ id: 1, symbol: 'BTC-USD' }, { id: 2, symbol: 'ETH-USD' }],
      kill_switch: false,
      ws_clients: 1,
    }
  }

  risk(): RiskData {
    return {
      kill_switch: false,
      reason: '',
      limits: { max_order_size: 10_000, max_position: 100_000, max_exposure: 10_000_000, daily_loss_limit: 1_000_000 },
      accounts: {
        '1': {
          net_position: Math.round((Math.random() - 0.5) * 40),
          realized_pnl: Math.round((Math.random() - 0.3) * 20_000),
          exposure: Math.round(this.mid * 10),
        },
      },
    }
  }
}

export const marketSimulator = new MarketSimulator()
