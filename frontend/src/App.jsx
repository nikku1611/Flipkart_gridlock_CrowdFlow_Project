import { useState, useEffect } from 'react'
import { BrowserRouter as Router, Routes, Route, NavLink } from 'react-router-dom'
import Dashboard from './pages/Dashboard'
import Predictor from './pages/Predictor'
import Analytics from './pages/Analytics'
import ModelInfo from './pages/ModelInfo'
import './index.css'

const NAV_ITEMS = [
  { path: '/', label: 'Command Center', icon: '🎯' },
  { path: '/predict', label: 'Event Predictor', icon: '⚡' },
  { path: '/analytics', label: 'Analytics', icon: '📊' },
  { path: '/model', label: 'Model Info', icon: '🧠' },
]

const THEMES = ['dark', 'light', 'cyberpunk']

function App() {
  const [sidebarCollapsed, setSidebarCollapsed] = useState(false)
  const [theme, setTheme] = useState(() => localStorage.getItem('theme') || 'dark')

  useEffect(() => {
    document.documentElement.setAttribute('data-theme', theme)
    localStorage.setItem('theme', theme)
  }, [theme])

  const toggleTheme = () => {
    const currentIndex = THEMES.indexOf(theme)
    const nextTheme = THEMES[(currentIndex + 1) % THEMES.length]
    setTheme(nextTheme)
  }

  return (
    <Router>
      <div style={{ display: 'flex', minHeight: '100vh' }}>
        {/* Sidebar */}
        <aside
          className="sidebar"
          style={{
            width: sidebarCollapsed ? 64 : 240,
            background: 'var(--bg-secondary)',
            borderRight: '1px solid var(--border-color)',
            display: 'flex', flexDirection: 'column',
            transition: 'width 0.3s ease',
            position: 'fixed', top: 0, left: 0, bottom: 0, zIndex: 50,
          }}
        >
          {/* Logo */}
          <div style={{
            padding: '20px 16px', borderBottom: '1px solid var(--border-color)',
            display: 'flex', alignItems: 'center', gap: 12,
          }}>
            <div style={{
              width: 36, height: 36, borderRadius: 10,
              background: 'var(--gradient-primary)',
              display: 'flex', alignItems: 'center', justifyContent: 'center',
              fontSize: 18, flexShrink: 0,
            }}>🚦</div>
            {!sidebarCollapsed && (
              <div>
                <div style={{ fontWeight: 700, fontSize: 16 }} className="gradient-text">CrowdFlow</div>
                <div style={{ fontSize: 11, color: 'var(--text-muted)' }}>Traffic Intelligence</div>
              </div>
            )}
          </div>

          {/* Navigation */}
          <nav style={{ padding: '12px 8px', flex: 1 }}>
            {NAV_ITEMS.map(item => (
              <NavLink
                key={item.path}
                to={item.path}
                end={item.path === '/'}
                className={({ isActive }) => `nav-link ${isActive ? 'active' : ''}`}
                style={{ marginBottom: 4 }}
              >
                <span style={{ fontSize: 18 }}>{item.icon}</span>
                {!sidebarCollapsed && <span>{item.label}</span>}
              </NavLink>
            ))}
          </nav>

          {/* Footer controls */}
          <div style={{ padding: '12px 8px', borderTop: '1px solid var(--border-color)', display: 'flex', flexDirection: 'column', gap: 8 }}>
            <button
              onClick={toggleTheme}
              style={{
                width: '100%', padding: '8px', borderRadius: 8, border: '1px solid var(--border-color)',
                background: 'var(--bg-card)', color: 'var(--text-primary)',
                cursor: 'pointer', fontSize: 13, display: 'flex', alignItems: 'center', justifyContent: 'center', gap: 8,
              }}
            >
              <span>{theme === 'dark' ? '🌙' : theme === 'light' ? '☀️' : '🤖'}</span>
              {!sidebarCollapsed && <span style={{ textTransform: 'capitalize' }}>{theme} Mode</span>}
            </button>
            <button
              onClick={() => setSidebarCollapsed(!sidebarCollapsed)}
              style={{
                width: '100%', padding: '8px', borderRadius: 8, border: 'none',
                background: 'transparent', color: 'var(--text-secondary)',
                cursor: 'pointer', fontSize: 13,
              }}
            >
              {sidebarCollapsed ? '→' : '← Collapse'}
            </button>
          </div>
        </aside>

        {/* Main content */}
        <main
          className="main-content"
          style={{
            flex: 1,
            marginLeft: sidebarCollapsed ? 64 : 240,
            transition: 'margin-left 0.3s ease',
            padding: '24px',
            minHeight: '100vh',
          }}
        >
          <Routes>
            <Route path="/" element={<Dashboard />} />
            <Route path="/predict" element={<Predictor />} />
            <Route path="/analytics" element={<Analytics />} />
            <Route path="/model" element={<ModelInfo />} />
          </Routes>
        </main>
      </div>
    </Router>
  )
}

export default App
