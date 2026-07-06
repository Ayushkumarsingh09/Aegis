import { Routes, Route, NavLink } from 'react-router-dom'
import { LayoutDashboard, FlaskConical, LineChart, Shield, Brain, Database, Settings, BarChart3, TestTube, Zap, TrendingUp, Activity } from 'lucide-react'
import Research from './pages/Research'
import Backtests from './pages/Backtests'
import Portfolio from './pages/Portfolio'
import Risk from './pages/Risk'
import MLModels from './pages/MLModels'
import DataExplorer from './pages/DataExplorer'
import Factors from './pages/Factors'
import Experiments from './pages/Experiments'
import Executions from './pages/Executions'
import Options from './pages/Options'
import MarketMaking from './pages/MarketMaking'
import './App.css'

const NAV = [
  { to: '/', icon: LayoutDashboard, label: 'Research' },
  { to: '/backtests', icon: FlaskConical, label: 'Backtests' },
  { to: '/executions', icon: Zap, label: 'Executions' },
  { to: '/portfolio', icon: LineChart, label: 'Portfolio' },
  { to: '/risk', icon: Shield, label: 'Risk' },
  { to: '/options', icon: TrendingUp, label: 'Options' },
  { to: '/market-making', icon: Activity, label: 'Market Making' },
  { to: '/ml', icon: Brain, label: 'ML Models' },
  { to: '/data', icon: Database, label: 'Data Explorer' },
  { to: '/factors', icon: BarChart3, label: 'Factors' },
  { to: '/experiments', icon: TestTube, label: 'Experiments' },
  { to: '/settings', icon: Settings, label: 'Settings' },
]
export default function App() {
  return (
    <div className="app">
      <aside className="sidebar">
        <div className="brand">
          <span className="logo">Q</span>
          <div>
            <h1>Aegis Quant</h1>
            <span>Research Platform</span>
          </div>
        </div>
        <nav>
          {NAV.map(({ to, icon: Icon, label }) => (
            <NavLink key={to} to={to} end={to === '/'} className={({ isActive }) => isActive ? 'nav-item active' : 'nav-item'}>
              <Icon size={18} /> {label}
            </NavLink>
          ))}
        </nav>
      </aside>
      <main className="content">
        <Routes>
          <Route path="/" element={<Research />} />
          <Route path="/backtests" element={<Backtests />} />
          <Route path="/portfolio" element={<Portfolio />} />
          <Route path="/risk" element={<Risk />} />
          <Route path="/ml" element={<MLModels />} />
          <Route path="/data" element={<DataExplorer />} />
          <Route path="/factors" element={<Factors />} />
          <Route path="/experiments" element={<Experiments />} />
          <Route path="/executions" element={<Executions />} />
          <Route path="/options" element={<Options />} />
          <Route path="/market-making" element={<MarketMaking />} />
          <Route path="/settings" element={<div className="page"><h2>Settings</h2><p className="muted">API: localhost:8090 | Exchange: localhost:9080</p></div>} />
        </Routes>
      </main>
    </div>
  )
}
