import { RiskData, ExchangeStatus } from '../api'
import { Activity, Shield, Wifi, WifiOff, Zap } from 'lucide-react'
import './StatusBar.css'

interface Props {
  status: ExchangeStatus | null
  risk: RiskData | null
  connected: boolean
  latency: number
}

export default function StatusBar({ status, risk, connected, latency }: Props) {
  return (
    <header className="status-bar">
      <div className="brand">
        <div className="logo">Æ</div>
        <div>
          <h1>Aegis Exchange</h1>
          <span className="version">v{status?.version ?? '1.0.0'}</span>
        </div>
      </div>

      <div className="metrics-row">
        <div className="metric">
          <Activity size={14} />
          <span className="label">Instruments</span>
          <span className="value">{status?.instruments?.length ?? 0}</span>
        </div>
        <div className="metric">
          <Zap size={14} />
          <span className="label">Latency</span>
          <span className="value">{latency}ms</span>
        </div>
        <div className="metric">
          {connected ? <Wifi size={14} className="connected" /> : <WifiOff size={14} className="disconnected" />}
          <span className="label">Status</span>
          <span className={`value ${connected ? 'connected' : 'disconnected'}`}>
            {connected ? 'Live' : 'Offline'}
          </span>
        </div>
        <div className="metric">
          <Shield size={14} />
          <span className="label">Risk</span>
          <span className={`value ${risk?.kill_switch ? 'kill' : 'ok'}`}>
            {risk?.kill_switch ? 'KILL SWITCH' : 'Normal'}
          </span>
        </div>
      </div>
    </header>
  )
}
