import { useState, useEffect } from 'react'
import { predictEventImpact, getDiversionPlan, getCorridors, getZones, getPoliceStations } from '../api'
import MapView from '../components/MapView'
import SeverityGauge from '../components/SeverityGauge'
import { BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer, Cell } from 'recharts'

const EVENT_CAUSES = [
  'vehicle_breakdown', 'accident', 'construction', 'pot_holes', 'water_logging',
  'tree_fall', 'road_conditions', 'congestion', 'public_event', 'procession',
  'vip_movement', 'protest', 'debris', 'fog_low_visibility', 'others'
]
const VEH_TYPES = ['not_applicable', 'bmtc_bus', 'heavy_vehicle', 'lcv', 'others', 'private_bus', 'private_car', 'truck', 'ksrtc_bus', 'taxi', 'auto']

export default function Predictor() {
  const [form, setForm] = useState({
    event_type: 'unplanned', event_cause: 'vehicle_breakdown',
    latitude: 12.9716, longitude: 77.5946,
    requires_road_closure: false, priority: 'High',
    corridor: 'Non-corridor', zone: 'Unknown',
    police_station: 'Cubbon Park', veh_type: 'not_applicable',
    description: '', start_datetime: new Date().toISOString(),
  })
  const [prediction, setPrediction] = useState(null)
  const [diversion, setDiversion] = useState(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState(null)
  const [corridors, setCorridors] = useState([])
  const [zones, setZones] = useState([])
  const [stations, setStations] = useState([])
  const [activeTab, setActiveTab] = useState('form')

  useEffect(() => {
    getCorridors().then(d => setCorridors(d.corridors || [])).catch(() => {})
    getZones().then(d => setZones(d.zones || [])).catch(() => {})
    getPoliceStations().then(d => setStations(d.police_stations || [])).catch(() => {})
  }, [])

  const handleSubmit = async (e, formDataOverride) => {
    if (e?.preventDefault) e.preventDefault()
    const dataToSubmit = formDataOverride || form
    
    setLoading(true)
    setError(null)
    try {
      const result = await predictEventImpact(dataToSubmit)
      setPrediction(result)
      setActiveTab('results')

      // Get diversion plan
      if (result.congestion_severity) {
        const divPlan = await getDiversionPlan({
          severity: result.congestion_severity.value,
          latitude: dataToSubmit.latitude, longitude: dataToSubmit.longitude,
          requires_road_closure: dataToSubmit.requires_road_closure,
          event_cause: dataToSubmit.event_cause,
          corridor: dataToSubmit.corridor, zone: dataToSubmit.zone,
          police_station: dataToSubmit.police_station,
          manpower_needed: result.required_manpower?.value || '3-5',
        })
        setDiversion(divPlan)
      }
    } catch (err) {
      setError(err.response?.data?.detail || 'Prediction failed. Check API connection.')
    } finally {
      setLoading(false)
    }
  }

  const handleChaosMode = () => {
    const randomItem = (arr) => arr[Math.floor(Math.random() * arr.length)]
    
    const newForm = {
      ...form,
      event_type: 'unplanned',
      event_cause: randomItem(['accident', 'water_logging', 'protest', 'tree_fall']),
      latitude: parseFloat((12.9716 + (Math.random() - 0.5) * 0.1).toFixed(4)),
      longitude: parseFloat((77.5946 + (Math.random() - 0.5) * 0.1).toFixed(4)),
      requires_road_closure: Math.random() > 0.5,
      priority: 'Critical',
      corridor: corridors.length ? randomItem(corridors) : 'Non-corridor',
      zone: zones.length ? randomItem(zones) : 'Unknown',
      police_station: stations.length ? randomItem(stations) : 'Cubbon Park',
      veh_type: randomItem(['heavy_vehicle', 'private_bus', 'truck']),
      description: 'CRITICAL SYSTEM SIMULATION: Unexpected high-impact incident detected.',
    }
    
    setForm(newForm)
    handleSubmit(null, newForm)
  }

  const updateField = (field, value) => setForm(prev => ({ ...prev, [field]: value }))

  return (
    <div>
      <div style={{ marginBottom: 24 }}>
        <h1 style={{ fontSize: 28, fontWeight: 800 }} className="gradient-text">Event Impact Predictor</h1>
        <p style={{ color: 'var(--text-secondary)', marginTop: 4, fontSize: 14 }}>
          Enter event details to predict severity, manpower, and resolution time
        </p>
      </div>

      {/* Tab Nav */}
      <div style={{ display: 'flex', gap: 4, marginBottom: 20, background: 'var(--bg-secondary)', padding: 4, borderRadius: 10, width: 'fit-content' }}>
        {[{ id: 'form', label: '📝 Event Input' }, { id: 'results', label: '⚡ Predictions' }].map(tab => (
          <button key={tab.id} onClick={() => setActiveTab(tab.id)}
            style={{
              padding: '8px 20px', borderRadius: 8, border: 'none', cursor: 'pointer', fontSize: 13, fontWeight: 600,
              background: activeTab === tab.id ? 'var(--gradient-primary)' : 'transparent',
              color: activeTab === tab.id ? 'white' : 'var(--text-secondary)', fontFamily: 'Inter, sans-serif',
            }}>
            {tab.label}
          </button>
        ))}
      </div>

      {activeTab === 'form' && (
        <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 20 }}>
          {/* Form */}
          <div className="glass-card" style={{ padding: 24 }}>
            <h3 style={{ fontSize: 16, fontWeight: 600, marginBottom: 20 }}>Event Details</h3>
            <form onSubmit={handleSubmit}>
              <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 14 }}>
                <FormField label="Event Type">
                  <select className="form-input form-select" value={form.event_type}
                    onChange={e => updateField('event_type', e.target.value)}>
                    <option value="unplanned">Unplanned</option>
                    <option value="planned">Planned</option>
                  </select>
                </FormField>
                <FormField label="Event Cause">
                  <select className="form-input form-select" value={form.event_cause}
                    onChange={e => updateField('event_cause', e.target.value)}>
                    {EVENT_CAUSES.map(c => <option key={c} value={c}>{c.replace(/_/g, ' ')}</option>)}
                  </select>
                </FormField>
                <FormField label="Latitude">
                  <input type="number" step="0.0001" className="form-input" value={form.latitude}
                    onChange={e => updateField('latitude', parseFloat(e.target.value))} />
                </FormField>
                <FormField label="Longitude">
                  <input type="number" step="0.0001" className="form-input" value={form.longitude}
                    onChange={e => updateField('longitude', parseFloat(e.target.value))} />
                </FormField>
                <FormField label="Priority">
                  <select className="form-input form-select" value={form.priority}
                    onChange={e => updateField('priority', e.target.value)}>
                    <option value="High">High</option>
                    <option value="Low">Low</option>
                  </select>
                </FormField>
                <FormField label="Vehicle Type">
                  <select className="form-input form-select" value={form.veh_type}
                    onChange={e => updateField('veh_type', e.target.value)}>
                    {VEH_TYPES.map(v => <option key={v} value={v}>{v.replace(/_/g, ' ')}</option>)}
                  </select>
                </FormField>
                <FormField label="Corridor">
                  <select className="form-input form-select" value={form.corridor}
                    onChange={e => updateField('corridor', e.target.value)}>
                    {(corridors.length ? corridors : ['Non-corridor']).map(c => <option key={c} value={c}>{c}</option>)}
                  </select>
                </FormField>
                <FormField label="Zone">
                  <select className="form-input form-select" value={form.zone}
                    onChange={e => updateField('zone', e.target.value)}>
                    <option value="Unknown">Unknown</option>
                    {zones.map(z => <option key={z} value={z}>{z}</option>)}
                  </select>
                </FormField>
                <FormField label="Police Station">
                  <select className="form-input form-select" value={form.police_station}
                    onChange={e => updateField('police_station', e.target.value)}>
                    {(stations.length ? stations : ['Cubbon Park']).map(s => <option key={s} value={s}>{s}</option>)}
                  </select>
                </FormField>
                <FormField label="Road Closure">
                  <label style={{ display: 'flex', alignItems: 'center', gap: 8, cursor: 'pointer', padding: '10px 0' }}>
                    <input type="checkbox" checked={form.requires_road_closure}
                      onChange={e => updateField('requires_road_closure', e.target.checked)}
                      style={{ width: 18, height: 18, cursor: 'pointer' }} />
                    <span style={{ fontSize: 14, color: 'var(--text-secondary)' }}>Requires road closure</span>
                  </label>
                </FormField>
              </div>
              <FormField label="Description (optional)" style={{ marginTop: 14 }}>
                <textarea className="form-input" rows={3} value={form.description}
                  placeholder="E.g., Major accident near junction, VIP movement expected..."
                  onChange={e => updateField('description', e.target.value)} />
              </FormField>
              {error && <div style={{ marginTop: 12, padding: 10, borderRadius: 8, background: 'rgba(239,68,68,0.1)', border: '1px solid rgba(239,68,68,0.3)', color: '#f87171', fontSize: 13 }}>{error}</div>}
              
              <div style={{ display: 'flex', gap: 12, marginTop: 20 }}>
                <button type="submit" className="btn-primary" disabled={loading} style={{ flex: 1 }}>
                  {loading ? <><div className="spinner" /> Analyzing...</> : '⚡ Predict Impact'}
                </button>
                <button type="button" onClick={handleChaosMode} className="btn-primary" disabled={loading} style={{ background: 'var(--gradient-primary)', flex: 0.5, whiteSpace: 'nowrap' }}>
                  🎲 Simulate Crisis
                </button>
              </div>
            </form>
          </div>

          {/* Map Preview */}
          <div className="glass-card" style={{ padding: 16 }}>
            <h3 style={{ fontSize: 14, fontWeight: 600, marginBottom: 12, color: 'var(--text-secondary)' }}>
              📍 Event Location (Click map to set)
            </h3>
            <MapView
              height="500px"
              center={[form.latitude, form.longitude]}
              zoom={14}
              onMapClick={(lat, lng) => {
                updateField('latitude', parseFloat(lat.toFixed(4)))
                updateField('longitude', parseFloat(lng.toFixed(4)))
              }}
              markers={[{ latitude: form.latitude, longitude: form.longitude, label: 'Event Location', severity: 'High' }]}
            />
          </div>
        </div>
      )}

      {activeTab === 'results' && prediction && (
        <PredictionResults prediction={prediction} diversion={diversion} form={form} />
      )}

      {activeTab === 'results' && !prediction && (
        <div className="glass-card" style={{ padding: 40, textAlign: 'center' }}>
          <span style={{ fontSize: 48 }}>📋</span>
          <p style={{ marginTop: 12, color: 'var(--text-secondary)' }}>No predictions yet. Fill in the event form first.</p>
          <button className="btn-primary" style={{ marginTop: 16 }} onClick={() => setActiveTab('form')}>Go to Form</button>
        </div>
      )}
    </div>
  )
}

function PredictionResults({ prediction, diversion, form }) {
  const severity = prediction.congestion_severity?.value || 'Unknown'
  const manpower = prediction.required_manpower?.value || 'N/A'
  const ttr = prediction.time_to_resolution

  const severityColor = { Low: '#22c55e', Medium: '#eab308', High: '#f97316', Critical: '#ef4444' }[severity] || '#3b82f6'

  // Probability chart data
  const probData = prediction.congestion_severity?.probabilities
    ? Object.entries(prediction.congestion_severity.probabilities)
        .map(([name, value]) => ({ name, value: Math.round(value * 100) }))
    : []

  return (
    <div>
      {/* Main Prediction Cards */}
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3, 1fr)', gap: 16, marginBottom: 20 }}>
        {/* Severity Card */}
        <div className="glass-card" style={{ padding: 24, textAlign: 'center', borderColor: severityColor + '40' }}>
          <SeverityGauge severity={severity} />
          <div style={{ marginTop: 16 }}>
            <span className={`severity-badge severity-${severity.toLowerCase()}`} style={{ fontSize: 14 }}>
              {severity} Severity
            </span>
          </div>
          {prediction.congestion_severity?.is_heuristic && (
            <div style={{ marginTop: 8, fontSize: 11, color: 'var(--text-muted)' }}>
              ⚡ Estimated via rule-based heuristic
            </div>
          )}
        </div>

        {/* Manpower Card */}
        <div className="glass-card" style={{ padding: 24, textAlign: 'center' }}>
          <div style={{ fontSize: 48, marginBottom: 8 }}>👮</div>
          <div style={{ fontSize: 32, fontWeight: 800, color: 'var(--accent-cyan)' }}>{manpower}</div>
          <div style={{ fontSize: 13, color: 'var(--text-secondary)', marginTop: 4 }}>Officers Required</div>
          {prediction.required_manpower?.is_heuristic && (
            <div style={{ marginTop: 8, fontSize: 11, color: 'var(--text-muted)' }}>
              ⚡ Estimated via rule-based heuristic
            </div>
          )}
        </div>

        {/* Resolution Time Card */}
        <div className="glass-card" style={{ padding: 24, textAlign: 'center' }}>
          <div style={{ fontSize: 48, marginBottom: 8 }}>⏱️</div>
          <div style={{ fontSize: 32, fontWeight: 800, color: 'var(--accent-purple)' }}>{ttr?.display || 'N/A'}</div>
          <div style={{ fontSize: 13, color: 'var(--text-secondary)', marginTop: 4 }}>Estimated Resolution Time</div>
          {ttr?.is_ground_truth && (
            <div style={{ marginTop: 8, fontSize: 11, color: '#22c55e' }}>
              ✓ Trained on ground-truth data
            </div>
          )}
        </div>
      </div>

      {/* Severity Probabilities + Diversion Plan */}
      <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 16, marginBottom: 20 }}>
        {/* Probability Chart */}
        {probData.length > 0 && (
          <div className="glass-card" style={{ padding: 20 }}>
            <h3 style={{ fontSize: 14, fontWeight: 600, marginBottom: 16, color: 'var(--text-secondary)' }}>
              📊 Severity Probability Distribution
            </h3>
            <ResponsiveContainer width="100%" height={180}>
              <BarChart data={probData}>
                <XAxis dataKey="name" tick={{ fontSize: 12 }} />
                <YAxis tick={{ fontSize: 11 }} unit="%" />
                <Tooltip contentStyle={{ background: 'var(--bg-card)', border: '1px solid var(--border-color)', borderRadius: 8 }} formatter={(v) => `${v}%`} />
                <Bar dataKey="value" radius={[6, 6, 0, 0]}>
                  {probData.map((entry, i) => (
                    <Cell key={i} fill={{ Low: '#22c55e', Medium: '#eab308', High: '#f97316', Critical: '#ef4444' }[entry.name] || '#3b82f6'} />
                  ))}
                </Bar>
              </BarChart>
            </ResponsiveContainer>
          </div>
        )}

        {/* Diversion Plan */}
        {diversion && (
          <div className="glass-card" style={{ padding: 20 }}>
            <h3 style={{ fontSize: 14, fontWeight: 600, marginBottom: 16, color: 'var(--text-secondary)' }}>
              🚧 Response Plan
            </h3>
            <div style={{ fontSize: 13, padding: '8px 12px', borderRadius: 8, marginBottom: 12,
              background: severity === 'Critical' ? 'rgba(239,68,68,0.1)' : severity === 'High' ? 'rgba(249,115,22,0.1)' : 'rgba(59,130,246,0.1)',
              border: `1px solid ${severityColor}30`, color: severityColor }}>
              {diversion.alert_level}
            </div>
            <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 12, marginBottom: 14 }}>
              <InfoChip label="Barricades" value={diversion.recommended_barricades} icon="🚧" />
              <InfoChip label="Officers" value={diversion.recommended_officers} icon="👮" />
            </div>
            {diversion.diversion_routes?.length > 0 && (
              <div style={{ marginBottom: 14 }}>
                <div style={{ fontSize: 12, fontWeight: 600, color: 'var(--text-muted)', marginBottom: 6 }}>DIVERSION ROUTES</div>
                {diversion.diversion_routes.map((route, i) => (
                  <div key={i} style={{ fontSize: 12, color: 'var(--text-secondary)', padding: '6px 0', borderBottom: '1px solid var(--border-color)' }}>
                    ↳ {route}
                  </div>
                ))}
              </div>
            )}
          </div>
        )}
      </div>

      {/* Nearest Police Stations + Map */}
      {diversion?.nearest_police_stations && (
        <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 16 }}>
          <div className="glass-card" style={{ padding: 20 }}>
            <h3 style={{ fontSize: 14, fontWeight: 600, marginBottom: 16, color: 'var(--text-secondary)' }}>
              🏢 Nearest Police Stations
            </h3>
            {diversion.nearest_police_stations.map((station, i) => (
              <div key={i} style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', padding: '10px 0', borderBottom: i < 2 ? '1px solid var(--border-color)' : 'none' }}>
                <div>
                  <div style={{ fontWeight: 600, fontSize: 14 }}>{station.name}</div>
                  <div style={{ fontSize: 12, color: 'var(--text-muted)' }}>{station.distance_km} km away</div>
                </div>
                <div style={{ width: 28, height: 28, borderRadius: 6, background: 'rgba(59,130,246,0.15)', display: 'flex', alignItems: 'center', justifyContent: 'center', fontSize: 14, fontWeight: 700, color: 'var(--accent-blue)' }}>
                  {i + 1}
                </div>
              </div>
            ))}
          </div>

          <div className="glass-card" style={{ padding: 16 }}>
            <h3 style={{ fontSize: 14, fontWeight: 600, marginBottom: 12, color: 'var(--text-secondary)' }}>
              📍 Deployment Map
            </h3>
            <MapView
              height="280px"
              center={[form.latitude, form.longitude]}
              zoom={13}
              markers={[
                { latitude: form.latitude, longitude: form.longitude, label: 'Event', severity, description: `${form.event_cause} - ${severity}` },
                ...diversion.nearest_police_stations.map(s => ({
                  latitude: s.latitude, longitude: s.longitude, label: s.name, severity: 'Low', description: `${s.distance_km}km`
                }))
              ]}
            />
          </div>
        </div>
      )}
    </div>
  )
}

function FormField({ label, children, style }) {
  return (
    <div style={style}>
      <label style={{ display: 'block', fontSize: 12, fontWeight: 600, color: 'var(--text-muted)', marginBottom: 6, textTransform: 'uppercase', letterSpacing: '0.5px' }}>
        {label}
      </label>
      {children}
    </div>
  )
}

function InfoChip({ label, value, icon }) {
  return (
    <div style={{ padding: '10px 12px', background: 'var(--bg-secondary)', borderRadius: 8, textAlign: 'center' }}>
      <div style={{ fontSize: 18 }}>{icon}</div>
      <div style={{ fontSize: 18, fontWeight: 700, marginTop: 4 }}>{value}</div>
      <div style={{ fontSize: 11, color: 'var(--text-muted)' }}>{label}</div>
    </div>
  )
}
