import { useState, useEffect } from 'react'
import { getHistoricalEvents } from '../api'

export default function Analytics() {
  const [events, setEvents] = useState([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)
  const [page, setPage] = useState(1)
  const [totalPages, setTotalPages] = useState(1)

  const [filters, setFilters] = useState({
    zone: '', event_type: '', event_cause: ''
  })

  useEffect(() => {
    fetchEvents()
  }, [page, filters])

  const fetchEvents = async () => {
    setLoading(true)
    try {
      const data = await getHistoricalEvents({
        page,
        page_size: 15,
        zone: filters.zone || undefined,
        event_type: filters.event_type || undefined,
        event_cause: filters.event_cause || undefined
      })
      setEvents(data.events)
      setTotalPages(data.total_pages)
    } catch (err) {
      setError('Failed to fetch historical events')
    } finally {
      setLoading(false)
    }
  }

  const handleFilterChange = (key, val) => {
    setFilters(prev => ({ ...prev, [key]: val }))
    setPage(1)
  }

  return (
    <div>
      <div style={{ marginBottom: 24 }}>
        <h1 style={{ fontSize: 28, fontWeight: 800 }} className="gradient-text">Event Database</h1>
        <p style={{ color: 'var(--text-secondary)', marginTop: 4, fontSize: 14 }}>
          Browse and filter historical traffic events and incidents
        </p>
      </div>

      <div className="glass-card" style={{ padding: 20, marginBottom: 20 }}>
        <div style={{ display: 'flex', gap: 16, alignItems: 'center' }}>
          <div style={{ fontSize: 14, fontWeight: 600, color: 'var(--text-secondary)' }}>Filters:</div>
          <select className="form-input form-select" style={{ width: 200 }} value={filters.event_type} onChange={e => handleFilterChange('event_type', e.target.value)}>
            <option value="">All Event Types</option>
            <option value="planned">Planned</option>
            <option value="unplanned">Unplanned</option>
          </select>
          <select className="form-input form-select" style={{ width: 200 }} value={filters.event_cause} onChange={e => handleFilterChange('event_cause', e.target.value)}>
            <option value="">All Causes</option>
            <option value="accident">Accident</option>
            <option value="vehicle_breakdown">Vehicle Breakdown</option>
            <option value="water_logging">Water Logging</option>
            <option value="tree_fall">Tree Fall</option>
            <option value="protest">Protest</option>
            <option value="vip_movement">VIP Movement</option>
            <option value="public_event">Public Event</option>
            <option value="construction">Construction</option>
            <option value="pot_holes">Potholes</option>
          </select>
        </div>
      </div>

      <div className="glass-card" style={{ overflow: 'hidden' }}>
        <div style={{ overflowX: 'auto' }}>
          <table style={{ width: '100%', borderCollapse: 'collapse', textAlign: 'left', fontSize: 13 }}>
            <thead>
              <tr style={{ background: 'var(--bg-secondary)', borderBottom: '1px solid var(--border-color)' }}>
                <th style={{ padding: '12px 16px', color: 'var(--text-muted)', fontWeight: 600 }}>Date</th>
                <th style={{ padding: '12px 16px', color: 'var(--text-muted)', fontWeight: 600 }}>Type / Cause</th>
                <th style={{ padding: '12px 16px', color: 'var(--text-muted)', fontWeight: 600 }}>Location</th>
                <th style={{ padding: '12px 16px', color: 'var(--text-muted)', fontWeight: 600 }}>Priority</th>
                <th style={{ padding: '12px 16px', color: 'var(--text-muted)', fontWeight: 600 }}>Road Closure</th>
              </tr>
            </thead>
            <tbody>
              {loading ? (
                <tr>
                  <td colSpan={5} style={{ padding: 40, textAlign: 'center', color: 'var(--text-secondary)' }}>
                    <div className="spinner" style={{ margin: '0 auto 12px auto' }} /> Loading events...
                  </td>
                </tr>
              ) : events.length === 0 ? (
                <tr>
                  <td colSpan={5} style={{ padding: 40, textAlign: 'center', color: 'var(--text-secondary)' }}>
                    No events found matching your filters.
                  </td>
                </tr>
              ) : (
                events.map((e, i) => (
                  <tr key={i} style={{ borderBottom: '1px solid var(--border-color)', background: i % 2 === 0 ? 'transparent' : 'rgba(255,255,255,0.02)' }}>
                    <td style={{ padding: '12px 16px' }}>{new Date(e.created_date || e.start_datetime).toLocaleString()}</td>
                    <td style={{ padding: '12px 16px' }}>
                      <span style={{ display: 'inline-block', padding: '2px 8px', borderRadius: 4, background: 'var(--bg-secondary)', fontSize: 11, marginBottom: 4, textTransform: 'uppercase' }}>
                        {e.event_type}
                      </span><br/>
                      <span style={{ fontWeight: 500 }}>{e.event_cause.replace(/_/g, ' ')}</span>
                    </td>
                    <td style={{ padding: '12px 16px' }}>
                      <div style={{ fontWeight: 500 }}>{e.zone}</div>
                      <div style={{ fontSize: 11, color: 'var(--text-muted)' }}>{e.corridor !== 'Non-corridor' ? e.corridor : e.police_station}</div>
                    </td>
                    <td style={{ padding: '12px 16px' }}>
                      <span style={{ color: e.priority === 'High' ? '#ef4444' : '#22c55e', fontWeight: 600 }}>{e.priority}</span>
                    </td>
                    <td style={{ padding: '12px 16px' }}>
                      {e.requires_road_closure ? <span style={{ color: '#eab308' }}>⚠️ Yes</span> : <span style={{ color: 'var(--text-muted)' }}>No</span>}
                    </td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>

        {/* Pagination */}
        <div style={{ padding: '16px', display: 'flex', justifyContent: 'space-between', alignItems: 'center', borderTop: '1px solid var(--border-color)' }}>
          <span style={{ fontSize: 13, color: 'var(--text-secondary)' }}>Page {page} of {totalPages}</span>
          <div style={{ display: 'flex', gap: 8 }}>
            <button className="btn-primary" disabled={page === 1} onClick={() => setPage(p => p - 1)} style={{ padding: '6px 12px' }}>Previous</button>
            <button className="btn-primary" disabled={page >= totalPages} onClick={() => setPage(p => p + 1)} style={{ padding: '6px 12px' }}>Next</button>
          </div>
        </div>
      </div>
    </div>
  )
}
