import { useEffect, useState } from 'react'
import { api, getHealth } from '../api'

interface PlatformStatus {
  platform_modules: boolean
  modules: Record<string, boolean | string>
}

export default function Settings() {
  const [health, setHealth] = useState('checking…')
  const [platform, setPlatform] = useState<PlatformStatus | null>(null)

  useEffect(() => {
    getHealth().then(h => setHealth(h.status)).catch(() => setHealth('offline'))
    api<PlatformStatus>('/api/v1/platform/status').then(setPlatform).catch(() => {})
  }, [])

  const endpoints = [
    { name: 'Quant API', url: 'http://localhost:8090', status: health },
    { name: 'API Docs (Swagger)', url: 'http://localhost:8090/docs', status: health },
    { name: 'Exchange API', url: String(platform?.modules.exchange_url ?? 'http://localhost:9080'), status: 'external' },
    { name: 'Prometheus Metrics', url: 'http://localhost:8090/metrics', status: health },
  ]

  return (
    <div className="page fade-in">
      <h2>Settings</h2>

      <div className="card">
        <h3>Service Endpoints</h3>
        <table className="data-table">
          <thead><tr><th>Service</th><th>URL</th><th>Status</th></tr></thead>
          <tbody>
            {endpoints.map(e => (
              <tr key={e.name}>
                <td>{e.name}</td>
                <td><a href={e.url} target="_blank" rel="noreferrer" style={{ color: 'var(--accent)' }}>{e.url}</a></td>
                <td>
                  <span className={`badge ${e.status === 'healthy' ? 'green' : e.status === 'external' ? 'blue' : 'red'}`}>
                    {e.status}
                  </span>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      <div className="card" style={{ marginTop: 16 }}>
        <h3>Platform Modules</h3>
        {platform ? (
          <table className="data-table">
            <thead><tr><th>Module</th><th>Status</th></tr></thead>
            <tbody>
              {Object.entries(platform.modules).filter(([, v]) => typeof v === 'boolean').map(([name, up]) => (
                <tr key={name}>
                  <td style={{ textTransform: 'capitalize' }}>{name.replace(/_/g, ' ')}</td>
                  <td><span className={`badge ${up ? 'green' : 'red'}`}>{up ? 'installed' : 'missing'}</span></td>
                </tr>
              ))}
            </tbody>
          </table>
        ) : <p className="muted" style={{ marginTop: 8 }}>Loading…</p>}
      </div>

      <div className="card" style={{ marginTop: 16 }}>
        <h3>Configuration</h3>
        <p className="muted" style={{ marginTop: 8, lineHeight: 1.9 }}>
          Environment variables use the <code>AEGIS_QUANT_</code> prefix (see <code>.env.example</code>).<br />
          Data store: DuckDB at <code>data/aegis_quant.duckdb</code> · Models: <code>data/models/</code> · MLflow: <code>data/mlflow.db</code>
        </p>
      </div>
    </div>
  )
}
