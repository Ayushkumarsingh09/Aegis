export const SIM_METRICS = {
  ordersPerSec: 142_850,
  avgLatencyUs: 4.2,
  uptime: 99.97,
  activeStrategies: 12,
  backtestsToday: 47,
  mlExperiments: 8,
  var95: -0.0182,
  sharpe: 1.84,
  pnlToday: 124_580,
}

export const SIM_ACTIVITY = [
  { time: '2m ago', event: 'Backtest completed', detail: 'momentum / BTC-USD — Sharpe 1.33', module: 'quant' },
  { time: '5m ago', event: 'Order filled', detail: 'BUY 10 BTC-USD @ 50,125.00', module: 'exchange' },
  { time: '12m ago', event: 'MM simulation', detail: 'PnL +$2,340 — 847 fills', module: 'market-maker' },
  { time: '18m ago', event: 'Options priced', detail: 'BTC call K=52000 — IV 42.3%', module: 'options' },
  { time: '24m ago', event: 'TWAP execution', detail: 'IS -2.1 bps vs arrival', module: 'execution' },
  { time: '31m ago', event: 'Stress test', detail: 'Market crash scenario — VaR -4.2%', module: 'analytics' },
]

export const RELEASE_NOTES = [
  { version: '1.0.0', date: '2026-07-07', highlights: ['Unified platform portal', 'Execution engine (TWAP/VWAP/POV)', 'Options analytics & Greeks', 'Avellaneda-Stoikov market maker', '45+ integration tests'] },
]

export const ARCHITECTURE_LAYERS = [
  { name: 'Exchange', desc: 'C++ matching engine, order book, risk', color: '#6366f1' },
  { name: 'Market Data', desc: 'Publisher, recorder, replay', color: '#8b5cf6' },
  { name: 'Quant Research', desc: 'Features, backtesting, ML, portfolio', color: '#06b6d4' },
  { name: 'Execution', desc: 'TWAP, VWAP, POV, TCA, smart routing', color: '#10b981' },
  { name: 'Options', desc: 'Black-Scholes, Greeks, vol surface', color: '#f59e0b' },
  { name: 'Market Making', desc: 'Inventory-aware quoting, simulation', color: '#ec4899' },
  { name: 'Analytics', desc: 'VaR, attribution, stress testing', color: '#ef4444' },
]
