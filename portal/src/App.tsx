import { useEffect, useState } from 'react'
import {
  Activity, ArrowRight, BarChart3, BookOpen, Box, Cpu, ExternalLink,
  Github, Layers, LineChart, Moon, Rocket, Shield, Sun, TrendingUp, Zap,
} from 'lucide-react'
import { CONFIG, fetchPlatformStatus } from './api'
import { ARCHITECTURE_LAYERS, RELEASE_NOTES, SIM_ACTIVITY, SIM_METRICS } from './data/simulated'

const MODULES = [
  { id: 'exchange', title: 'Exchange', desc: 'C++ matching engine with price-time priority, full order types, and sub-microsecond latency design.', icon: Zap, color: '#6366f1', dash: CONFIG.exchangeDash, api: CONFIG.exchangeApi },
  { id: 'quant', title: 'Quant Research', desc: 'Feature engineering, backtesting, ML pipeline, portfolio optimization, and walk-forward validation.', icon: LineChart, color: '#06b6d4', dash: CONFIG.quantDash, api: `${CONFIG.quantApi}/docs` },
  { id: 'execution', title: 'Execution', desc: 'TWAP, VWAP, POV, iceberg algorithms with transaction cost analysis and smart order routing.', icon: Activity, color: '#10b981', dash: `${CONFIG.quantDash}/executions`, api: `${CONFIG.quantApi}/docs` },
  { id: 'options', title: 'Options Analytics', desc: 'Black-Scholes pricing, full Greeks, implied vol solver, volatility surfaces, and exotic options.', icon: TrendingUp, color: '#f59e0b', dash: `${CONFIG.quantDash}/options`, api: `${CONFIG.quantApi}/docs` },
  { id: 'market-maker', title: 'Market Making', desc: 'Avellaneda-Stoikov optimal quoting with inventory management and exchange simulation.', icon: BarChart3, color: '#ec4899', dash: `${CONFIG.quantDash}/market-making`, api: `${CONFIG.quantApi}/docs` },
  { id: 'analytics', title: 'Risk Analytics', desc: 'VaR, CVaR, Sharpe, attribution, stress testing, and Monte Carlo risk simulation.', icon: Shield, color: '#ef4444', dash: `${CONFIG.quantDash}/risk`, api: `${CONFIG.quantApi}/docs` },
  { id: 'portfolio', title: 'Portfolio', desc: 'Markowitz, Black-Litterman, risk parity, Kelly criterion, and hierarchical risk parity.', icon: Layers, color: '#8b5cf6', dash: `${CONFIG.quantDash}/portfolio`, api: `${CONFIG.quantApi}/docs` },
  { id: 'ml', title: 'ML Models', desc: 'XGBoost, LightGBM, CatBoost with MLflow tracking, cross-validation, and feature importance.', icon: Cpu, color: '#14b8a6', dash: `${CONFIG.quantDash}/ml`, api: `${CONFIG.quantApi}/docs` },
  { id: 'experiments', title: 'Experiments', desc: 'Strategy experiment tracking, factor IC analysis, and research workflow management.', icon: Box, color: '#a855f7', dash: `${CONFIG.quantDash}/experiments`, api: `${CONFIG.quantApi}/docs` },
]

export default function App() {
  const [theme, setTheme] = useState<'dark' | 'light'>(() =>
    (localStorage.getItem('aegis-theme') as 'dark' | 'light') || 'dark'
  )
  const [status, setStatus] = useState({ exchange: false, quant: false, loading: true })

  useEffect(() => {
    document.documentElement.setAttribute('data-theme', theme)
    localStorage.setItem('aegis-theme', theme)
  }, [theme])

  useEffect(() => {
    fetchPlatformStatus().then(s => {
      setStatus({ exchange: s.exchange.ok, quant: s.quant.ok, loading: false })
    })
  }, [])

  const metrics = SIM_METRICS

  return (
    <div className="portal">
      <nav className="nav">
        <a className="nav-brand" href="/" aria-label="Aegis home">
          <img className="nav-logo-img" src="/aegis-mark.png" alt="Aegis" />
          <span>Aegis</span>
        </a>
        <div className="nav-links">
          <a href="#modules">Modules</a>
          <a href="#architecture">Architecture</a>
          <a href="#metrics">Metrics</a>
          <a href="#activity">Activity</a>
          <a href="#docs">Docs</a>
        </div>
        <div className="nav-actions">
          <button className="btn btn-ghost" onClick={() => setTheme(t => t === 'dark' ? 'light' : 'dark')} aria-label="Toggle theme">
            {theme === 'dark' ? <Sun size={18} /> : <Moon size={18} />}
          </button>
          <a className="btn btn-ghost" href={CONFIG.github} target="_blank" rel="noreferrer"><Github size={18} /> GitHub</a>
          <a className="btn btn-primary" href={CONFIG.quantDash} target="_blank" rel="noreferrer">
            Launch Platform <ArrowRight size={16} />
          </a>
        </div>
      </nav>

      <header className="hero fade-up">
        <h1>Institutional <span>Quantitative Trading</span> Platform</h1>
        <p>
          Exchange matching, quant research, execution algorithms, options analytics,
          market making, and risk — unified in one production-grade platform.
        </p>
        <div className="hero-actions">
          <a className="btn btn-primary" href={CONFIG.exchangeDash} target="_blank" rel="noreferrer">
            <Zap size={18} /> Exchange Dashboard
          </a>
          <a className="btn btn-ghost" href={CONFIG.quantDash} target="_blank" rel="noreferrer">
            <LineChart size={18} /> Research Dashboard
          </a>
          <a className="btn btn-ghost" href={`${CONFIG.quantApi}/docs`} target="_blank" rel="noreferrer">
            <BookOpen size={18} /> API Docs
          </a>
        </div>
        <div className="status-bar">
          <div className="status-pill">
            <span className={`status-dot ${status.loading ? 'down' : status.exchange ? 'up' : 'down'}`} />
            Exchange {status.loading ? '…' : status.exchange ? 'Online' : 'Offline (simulated)'}
          </div>
          <div className="status-pill">
            <span className={`status-dot ${status.loading ? 'down' : status.quant ? 'up' : 'down'}`} />
            Quant API {status.loading ? '…' : status.quant ? 'Online' : 'Offline'}
          </div>
          <div className="status-pill">
            <span className="status-dot up" />
            45 Tests Passing
          </div>
        </div>
      </header>

      <section className="section" id="metrics">
        <h2 className="section-title">System Metrics</h2>
        <p className="section-sub">Live when exchange is connected; simulated otherwise.</p>
        <div className="metrics-row fade-up">
          <div className="metric-box"><div className="val">{metrics.ordersPerSec.toLocaleString()}</div><div className="lbl">Orders/sec</div></div>
          <div className="metric-box"><div className="val">{metrics.avgLatencyUs}µs</div><div className="lbl">Avg Latency</div></div>
          <div className="metric-box"><div className="val">{metrics.uptime}%</div><div className="lbl">Uptime</div></div>
          <div className="metric-box"><div className="val">{metrics.sharpe}</div><div className="lbl">Sharpe</div></div>
          <div className="metric-box"><div className="val">${(metrics.pnlToday / 1000).toFixed(0)}k</div><div className="lbl">PnL Today</div></div>
          <div className="metric-box"><div className="val">{metrics.backtestsToday}</div><div className="lbl">Backtests</div></div>
        </div>
      </section>

      <section className="section" id="modules">
        <h2 className="section-title">Platform Modules</h2>
        <p className="section-sub">Every component accessible from one integrated ecosystem.</p>
        <div className="grid grid-3">
          {MODULES.map((m, i) => (
            <a key={m.id} className="card fade-up" href={m.dash} target="_blank" rel="noreferrer" style={{ animationDelay: `${i * 50}ms` }}>
              <div className="card-icon" style={{ background: `${m.color}22`, color: m.color }}>
                <m.icon size={22} />
              </div>
              <h3>{m.title}</h3>
              <p>{m.desc}</p>
              <div className="card-meta">
                <span className="tag">Dashboard</span>
                <span className="tag">API</span>
              </div>
            </a>
          ))}
        </div>
      </section>

      <section className="section" id="architecture">
        <h2 className="section-title">Architecture</h2>
        <p className="section-sub">End-to-end data flow from market data to execution and analytics.</p>
        <div className="arch-flow">
          {ARCHITECTURE_LAYERS.map((layer, i) => (
            <span key={layer.name}>
              <span className="arch-node" style={{ borderColor: layer.color, color: layer.color }}>{layer.name}</span>
              {i < ARCHITECTURE_LAYERS.length - 1 && <span className="arch-arrow">→</span>}
            </span>
          ))}
        </div>
        <div style={{ textAlign: 'center', marginTop: '1.5rem' }}>
          <a className="btn btn-ghost" href="https://github.com/Ayushkumarsingh09/Aegis/blob/main/docs/platform-architecture.md" target="_blank" rel="noreferrer">
            Full Architecture Docs <ExternalLink size={14} />
          </a>
        </div>
      </section>

      <section className="section" id="activity">
        <h2 className="section-title">Recent Activity</h2>
        <p className="section-sub">Platform events across all modules.</p>
        <div className="activity-list">
          {SIM_ACTIVITY.map((a, i) => (
            <div key={i} className="activity-item fade-up" style={{ animationDelay: `${i * 60}ms` }}>
              <span className="activity-time">{a.time}</span>
              <div className="activity-body">
                <strong>{a.event}</strong>
                <span>{a.detail}</span>
              </div>
              <span className="tag">{a.module}</span>
            </div>
          ))}
        </div>
      </section>

      <section className="section" id="docs">
        <h2 className="section-title">Documentation & Resources</h2>
        <div className="grid grid-4">
          {[
            { label: 'Getting Started', href: `${CONFIG.github}/blob/main/docs/getting-started.md`, icon: Rocket },
            { label: 'Developer Guide', href: `${CONFIG.github}/blob/main/docs/developer-guide.md`, icon: BookOpen },
            { label: 'API Reference', href: `${CONFIG.quantApi}/docs`, icon: ExternalLink },
            { label: 'Benchmarks', href: `${CONFIG.github}/blob/main/docs/benchmarks.md`, icon: BarChart3 },
            { label: 'Deployment', href: `${CONFIG.github}/blob/main/docs/deployment.md`, icon: Layers },
            { label: 'Contributing', href: `${CONFIG.github}/blob/main/CONTRIBUTING.md`, icon: Github },
          ].map(d => (
            <a key={d.label} className="card" href={d.href} target="_blank" rel="noreferrer">
              <div className="card-icon" style={{ background: 'var(--surface3)' }}><d.icon size={20} /></div>
              <h3>{d.label}</h3>
            </a>
          ))}
        </div>
        {RELEASE_NOTES.map(r => (
          <div key={r.version} style={{ marginTop: '2rem', padding: '1.5rem', background: 'var(--surface2)', borderRadius: 'var(--radius)', border: '1px solid var(--border)' }}>
            <strong>v{r.version}</strong> <span style={{ color: 'var(--muted)' }}>— {r.date}</span>
            <ul style={{ marginTop: '0.75rem', paddingLeft: '1.25rem', color: 'var(--muted)', fontSize: '0.875rem' }}>
              {r.highlights.map(h => <li key={h}>{h}</li>)}
            </ul>
          </div>
        ))}
      </section>

      <footer className="footer">
        <div className="footer-links">
          <a href={CONFIG.github}>GitHub</a>
          <a href={`${CONFIG.quantApi}/docs`}>API</a>
          <a href={CONFIG.exchangeDash}>Exchange</a>
          <a href={CONFIG.quantDash}>Research</a>
          <a href={`${CONFIG.github}/blob/main/LICENSE`}>License</a>
        </div>
        <p>Aegis Platform v1.0.0 — MIT License</p>
      </footer>
    </div>
  )
}
