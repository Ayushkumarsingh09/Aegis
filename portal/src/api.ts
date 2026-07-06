export const CONFIG = {
  exchangeApi: import.meta.env.VITE_EXCHANGE_URL || '/exchange-api',
  quantApi: import.meta.env.VITE_QUANT_URL || '/quant-api',
  exchangeDash: import.meta.env.VITE_EXCHANGE_DASH || 'http://localhost:4000',
  quantDash: import.meta.env.VITE_QUANT_DASH || 'http://localhost:4100',
  github: 'https://github.com/Ayushkumarsingh09/Aegis',
}

export async function fetchHealth(url: string): Promise<{ ok: boolean; data?: Record<string, unknown> }> {
  try {
    const r = await fetch(`${url}/health`, { signal: AbortSignal.timeout(3000) })
    if (!r.ok) return { ok: false }
    return { ok: true, data: await r.json() }
  } catch {
    return { ok: false }
  }
}

export async function fetchPlatformStatus() {
  const [exchange, quant] = await Promise.all([
    fetchHealth(CONFIG.exchangeApi),
    fetchHealth(CONFIG.quantApi),
  ])
  let platform: Record<string, unknown> = {}
  try {
    const r = await fetch(`${CONFIG.quantApi}/api/v1/platform/status`, { signal: AbortSignal.timeout(3000) })
    if (r.ok) platform = await r.json()
  } catch { /* simulated fallback */ }
  return { exchange, quant, platform }
}
