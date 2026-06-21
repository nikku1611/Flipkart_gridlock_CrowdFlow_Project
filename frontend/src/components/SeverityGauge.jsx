import React from 'react'

export default function SeverityGauge({ severity, size = 120 }) {
  const normalizedSeverity = severity || 'Unknown'

  // Colors and angles
  const levels = {
    Low: { color: '#22c55e', value: 25, label: 'LOW' },
    Medium: { color: '#eab308', value: 50, label: 'MED' },
    High: { color: '#f97316', value: 75, label: 'HIGH' },
    Critical: { color: '#ef4444', value: 100, label: 'CRIT' },
    Unknown: { color: '#64748b', value: 0, label: '???' }
  }

  const { color, value, label } = levels[normalizedSeverity] || levels.Unknown

  const strokeWidth = 12
  const radius = (size - strokeWidth) / 2
  const circumference = radius * 2 * Math.PI
  // Show only top half of the circle (gauge)
  const offset = circumference - (value / 100) * (circumference / 2)

  return (
    <div style={{ position: 'relative', width: size, height: size / 2 + 10, margin: '0 auto' }}>
      <svg width={size} height={size / 2} style={{ overflow: 'visible' }}>
        <defs>
          <linearGradient id="gauge-gradient" x1="0%" y1="0%" x2="100%" y2="0%">
            <stop offset="0%" stopColor="#22c55e" />
            <stop offset="33%" stopColor="#eab308" />
            <stop offset="66%" stopColor="#f97316" />
            <stop offset="100%" stopColor="#ef4444" />
          </linearGradient>
        </defs>

        {/* Background track */}
        <circle
          cx={size / 2}
          cy={size / 2}
          r={radius}
          fill="none"
          stroke="var(--bg-secondary)"
          strokeWidth={strokeWidth}
          strokeDasharray={`${circumference / 2} ${circumference / 2}`}
          strokeDashoffset={0}
          transform={`rotate(180 ${size / 2} ${size / 2})`}
        />

        {/* Value track */}
        <circle
          className={value > 0 ? 'gauge-ring' : ''}
          cx={size / 2}
          cy={size / 2}
          r={radius}
          fill="none"
          stroke="url(#gauge-gradient)"
          strokeWidth={strokeWidth}
          strokeDasharray={`${circumference / 2} ${circumference / 2}`}
          strokeDashoffset={offset}
          strokeLinecap="round"
          transform={`rotate(180 ${size / 2} ${size / 2})`}
        />
      </svg>
      <div style={{
        position: 'absolute', bottom: 0, left: 0, right: 0,
        textAlign: 'center', fontWeight: 800, fontSize: 24, color
      }}>
        {label}
      </div>
    </div>
  )
}
