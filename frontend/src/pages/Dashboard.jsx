import { useState, useEffect } from 'react'
import { BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer, PieChart, Pie, Cell, AreaChart, Area } from 'recharts'
import { getDashboardStats, getHeatmapData } from '../api'
import MapView from '../components/MapView'

const SEVERITY_COLORS = { Low: '#22c55e', Medium: '#eab308', High: '#f97316', Critical: '#ef4444' }
const CHART_COLORS = ['#3b82f6', '#8b5cf6', '#06b6d4', '#f97316', '#22c55e', '#ef4444', '#eab308', '#ec4899', '#14b8a6', '#f59e0b']

export default function Dashboard() {
  const [stats, setStats] = useState(null)
  const [heatmap, setHeatmap] = useState(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)

  useEffect(() => {
    const fetchData = async () => {
      try {
        const [statsData, heatmapData] = await Promise.all([
          getDashboardStats(),
          getHeatmapData(),
        ])
        setStats(statsData)
        setHeatmap(heatmapData)
      } catch (err) {
        setError('Failed to load dashboard data. Make sure the API server is running on port 8000.')
        console.error(err)
      } finally {
        setLoading(false)
      }
    }
    fetchData()
  }, [])

  if (loading) return <LoadingSkeleton />
  if (error) return <ErrorState message={error} />

  const causeData = Object.entries(stats.events_by_cause || {})
    .map(([name, value]) => ({ name: name.replace(/_/g, ' '), value }))
    .sort((a, b) => b.value - a.value)

  const zoneData = Object.entries(stats.events_by_zone || {})
    .map(([name, value]) => ({ name, value }))
    .sort((a, b) => b.value - a.value)

  const monthlyData = Object.entries(stats.events_by_month || {})
    .map(([name, value]) => ({ name, value }))
    .sort((a, b) => a.name.localeCompare(b.name))

  const hourlyData = Object.entries(stats.events_by_hour || {})
    .map(([hour, count]) => ({ hour: `${hour}:00`, count }))
    .sort((a, b) => parseInt(a.hour) - parseInt(b.hour))

  const priorityData = Object.entries(stats.events_by_priority || {})
    .map(([name, value]) => ({ name, value }))

  return (
    <div>
      {/* Header */}
      <div style={{ marginBottom: 24, display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
        <div>
          <h1 style={{ fontSize: 28, fontWeight: 800 }} className="gradient-text">
            Command Center
          </h1>
          <p style={{ color: 'var(--text-secondary)', marginTop: 4, fontSize: 14 }}>
            Bengaluru Traffic Intelligence Dashboard — Real-time event monitoring & analytics
          </p>
        </div>
        <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
          <div style={{ width: 8, height: 8, borderRadius: '50%', background: '#22c55e', animation: 'pulse-red 2s infinite' }} />
          <span style={{ color: 'var(--text-secondary)', fontSize: 13 }}>System Online</span>
        </div>
      </div>

      {/* KPI Cards */}
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(200px, 1fr))', gap: 16, marginBottom: 24 }}>
        <StatCard title="Total Events" value={stats.total_events?.toLocaleString()} icon="📋" color="#3b82f6" />
        <StatCard title="Active Events" value={stats.active_events} icon="🔴" color="#ef4444" highlight />
        <StatCard title="Avg Resolution" value={`${Math.round(stats.avg_resolution_minutes)} min`} icon="⏱️" color="#06b6d4" />
        <StatCard title="High Priority" value={`${stats.high_priority_percentage}%`} icon="⚠️" color="#f97316" />
        <StatCard title="Road Closures" value={`${stats.road_closure_percentage}%`} icon="🚧" color="#eab308" />
      </div>

      {/* Map + Charts Row */}
      <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 16, marginBottom: 24 }}>
        {/* Map */}
        <div className="glass-card" style={{ padding: 16, minHeight: 400 }}>
          <h3 style={{ fontSize: 14, fontWeight: 600, marginBottom: 12, color: 'var(--text-secondary)' }}>
            📍 Event Heatmap — Bengaluru
          </h3>
          <MapView heatmapPoints={heatmap?.points || []} height="350px" />
        </div>

        {/* Events by Cause */}
        <div className="glass-card" style={{ padding: 16 }}>
          <h3 style={{ fontSize: 14, fontWeight: 600, marginBottom: 12, color: 'var(--text-secondary)' }}>
            🔍 Events by Cause
          </h3>
          <ResponsiveContainer width="100%" height={350}>
            <BarChart data={causeData} layout="vertical" margin={{ left: 100 }}>
              <XAxis type="number" tick={{ fontSize: 11 }} />
              <YAxis type="category" dataKey="name" tick={{ fontSize: 11 }} width={95} />
              <Tooltip
                contentStyle={{ background: 'var(--bg-card)', border: '1px solid var(--border-color)', borderRadius: 8, fontSize: 12 }}
                itemStyle={{ color: 'var(--text-primary)' }}
              />
              <Bar dataKey="value" fill="#3b82f6" radius={[0, 4, 4, 0]}>
                {causeData.map((_, i) => (
                  <Cell key={i} fill={CHART_COLORS[i % CHART_COLORS.length]} />
                ))}
              </Bar>
            </BarChart>
          </ResponsiveContainer>
        </div>
      </div>

      {/* Second Row */}
      <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr 1fr', gap: 16, marginBottom: 24 }}>
        {/* Monthly Trend */}
        <div className="glass-card" style={{ padding: 16 }}>
          <h3 style={{ fontSize: 14, fontWeight: 600, marginBottom: 12, color: 'var(--text-secondary)' }}>
            📈 Monthly Trend
          </h3>
          <ResponsiveContainer width="100%" height={200}>
            <AreaChart data={monthlyData}>
              <defs>
                <linearGradient id="blueGradient" x1="0" y1="0" x2="0" y2="1">
                  <stop offset="0%" stopColor="#3b82f6" stopOpacity={0.3} />
                  <stop offset="100%" stopColor="#3b82f6" stopOpacity={0} />
                </linearGradient>
              </defs>
              <XAxis dataKey="name" tick={{ fontSize: 10 }} />
              <YAxis tick={{ fontSize: 10 }} />
              <Tooltip contentStyle={{ background: 'var(--bg-card)', border: '1px solid var(--border-color)', borderRadius: 8, fontSize: 12 }} />
              <Area type="monotone" dataKey="value" stroke="#3b82f6" fill="url(#blueGradient)" strokeWidth={2} />
            </AreaChart>
          </ResponsiveContainer>
        </div>

        {/* Hourly Distribution */}
        <div className="glass-card" style={{ padding: 16 }}>
          <h3 style={{ fontSize: 14, fontWeight: 600, marginBottom: 12, color: 'var(--text-secondary)' }}>
            🕐 Hourly Distribution
          </h3>
          <ResponsiveContainer width="100%" height={200}>
            <BarChart data={hourlyData}>
              <XAxis dataKey="hour" tick={{ fontSize: 9 }} interval={2} />
              <YAxis tick={{ fontSize: 10 }} />
              <Tooltip contentStyle={{ background: 'var(--bg-card)', border: '1px solid var(--border-color)', borderRadius: 8, fontSize: 12 }} />
              <Bar dataKey="count" fill="#8b5cf6" radius={[2, 2, 0, 0]} />
            </BarChart>
          </ResponsiveContainer>
        </div>

        {/* Priority Distribution */}
        <div className="glass-card" style={{ padding: 16 }}>
          <h3 style={{ fontSize: 14, fontWeight: 600, marginBottom: 12, color: 'var(--text-secondary)' }}>
            🎯 Priority Split
          </h3>
          <ResponsiveContainer width="100%" height={200}>
            <PieChart>
              <Pie data={priorityData} cx="50%" cy="50%" innerRadius={50} outerRadius={80}
                dataKey="value" nameKey="name" paddingAngle={4}>
                {priorityData.map((entry, i) => (
                  <Cell key={i} fill={entry.name === 'High' ? '#ef4444' : '#22c55e'} />
                ))}
              </Pie>
              <Tooltip contentStyle={{ background: 'var(--bg-card)', border: '1px solid var(--border-color)', borderRadius: 8, fontSize: 12 }} />
            </PieChart>
          </ResponsiveContainer>
          <div style={{ display: 'flex', justifyContent: 'center', gap: 16, marginTop: 4 }}>
            {priorityData.map((entry, i) => (
              <div key={i} style={{ display: 'flex', alignItems: 'center', gap: 6, fontSize: 12 }}>
                <div style={{ width: 8, height: 8, borderRadius: '50%', background: entry.name === 'High' ? '#ef4444' : '#22c55e' }} />
                <span style={{ color: 'var(--text-secondary)' }}>{entry.name}: {entry.value}</span>
              </div>
            ))}
          </div>
        </div>
      </div>

      {/* Zone Distribution */}
      <div className="glass-card" style={{ padding: 16 }}>
        <h3 style={{ fontSize: 14, fontWeight: 600, marginBottom: 12, color: 'var(--text-secondary)' }}>
          🗺️ Events by Zone
        </h3>
        <ResponsiveContainer width="100%" height={250}>
          <BarChart data={zoneData}>
            <XAxis dataKey="name" tick={{ fontSize: 10 }} angle={-15} textAnchor="end" height={60} />
            <YAxis tick={{ fontSize: 10 }} />
            <Tooltip contentStyle={{ background: 'var(--bg-card)', border: '1px solid var(--border-color)', borderRadius: 8, fontSize: 12 }} />
            <Bar dataKey="value" radius={[4, 4, 0, 0]}>
              {zoneData.map((_, i) => (
                <Cell key={i} fill={CHART_COLORS[i % CHART_COLORS.length]} />
              ))}
            </Bar>
          </BarChart>
        </ResponsiveContainer>
      </div>
    </div>
  )
}

function StatCard({ title, value, icon, color, highlight }) {
  return (
    <div className={`stat-card ${highlight ? 'pulse-critical' : ''}`}
      style={highlight ? { borderColor: 'rgba(239,68,68,0.4)' } : {}}>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start' }}>
        <div>
          <div style={{ fontSize: 12, color: 'var(--text-muted)', marginBottom: 6, fontWeight: 500 }}>{title}</div>
          <div style={{ fontSize: 28, fontWeight: 800, color }}>{value}</div>
        </div>
        <span style={{ fontSize: 24 }}>{icon}</span>
      </div>
    </div>
  )
}

function LoadingSkeleton() {
  return (
    <div style={{ padding: 24 }}>
      <div style={{ display: 'flex', alignItems: 'center', gap: 12, marginBottom: 32 }}>
        <div className="spinner" />
        <span style={{ color: 'var(--text-secondary)' }}>Loading command center data...</span>
      </div>
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(5, 1fr)', gap: 16 }}>
        {[...Array(5)].map((_, i) => (
          <div key={i} style={{ height: 100, background: 'var(--bg-card)', borderRadius: 12, animation: 'pulse 2s infinite' }} />
        ))}
      </div>
    </div>
  )
}

function ErrorState({ message }) {
  return (
    <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center', minHeight: '60vh', gap: 16 }}>
      <span style={{ fontSize: 48 }}>⚠️</span>
      <h2 style={{ fontSize: 20, fontWeight: 600 }}>Connection Error</h2>
      <p style={{ color: 'var(--text-secondary)', maxWidth: 400, textAlign: 'center', fontSize: 14 }}>{message}</p>
      <button className="btn-primary" onClick={() => window.location.reload()}>Retry</button>
    </div>
  )
}
