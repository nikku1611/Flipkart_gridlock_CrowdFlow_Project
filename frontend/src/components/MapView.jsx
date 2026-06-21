import { useEffect, useRef } from 'react'

export default function MapView({ heatmapPoints = [], markers = [], height = '400px', center = [12.9716, 77.5946], zoom = 12 }) {
  const mapRef = useRef(null)
  const mapInstanceRef = useRef(null)

  useEffect(() => {
    // Load Leaflet CSS
    if (!document.querySelector('link[href*="leaflet"]')) {
      const link = document.createElement('link')
      link.rel = 'stylesheet'
      link.href = 'https://unpkg.com/leaflet@1.9.4/dist/leaflet.css'
      document.head.appendChild(link)
    }

    // Load Leaflet JS
    const loadLeaflet = () => {
      return new Promise((resolve) => {
        if (window.L) { resolve(window.L); return }
        const script = document.createElement('script')
        script.src = 'https://unpkg.com/leaflet@1.9.4/dist/leaflet.js'
        script.onload = () => resolve(window.L)
        document.head.appendChild(script)
      })
    }

    loadLeaflet().then((L) => {
      if (mapInstanceRef.current) {
        mapInstanceRef.current.remove()
      }

      const map = L.map(mapRef.current).setView(center, zoom)
      mapInstanceRef.current = map

      // Dark tile layer
      L.tileLayer('https://{s}.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}{r}.png', {
        attribution: '&copy; <a href="https://carto.com/">CARTO</a>',
        maxZoom: 19,
      }).addTo(map)

      // Add heatmap points as circle markers
      heatmapPoints.forEach(point => {
        if (!point.latitude || !point.longitude) return
        const intensity = point.intensity || 0.5
        const color = intensity > 0.7 ? '#ef4444' : intensity > 0.4 ? '#f97316' : intensity > 0.2 ? '#eab308' : '#22c55e'
        const radius = 4 + intensity * 16

        L.circleMarker([point.latitude, point.longitude], {
          radius,
          fillColor: color,
          color: color,
          weight: 1,
          opacity: 0.7,
          fillOpacity: 0.4,
        }).addTo(map).bindPopup(
          `<div style="font-size:12px"><strong>${point.zone || 'Unknown Zone'}</strong><br/>Events: ${point.event_count || 0}</div>`
        )
      })

      // Add individual markers
      markers.forEach(marker => {
        if (!marker.latitude || !marker.longitude) return
        const severityColors = { Low: '#22c55e', Medium: '#eab308', High: '#f97316', Critical: '#ef4444' }
        const color = severityColors[marker.severity] || '#3b82f6'

        L.circleMarker([marker.latitude, marker.longitude], {
          radius: 8,
          fillColor: color,
          color: '#fff',
          weight: 2,
          opacity: 1,
          fillOpacity: 0.8,
        }).addTo(map).bindPopup(
          `<div style="font-size:12px">
            <strong>${marker.label || 'Event'}</strong><br/>
            ${marker.description || ''}
          </div>`
        )
      })

      // Fix map size issues
      setTimeout(() => map.invalidateSize(), 100)
    })

    return () => {
      if (mapInstanceRef.current) {
        mapInstanceRef.current.remove()
        mapInstanceRef.current = null
      }
    }
  }, [heatmapPoints, markers, center[0], center[1], zoom])

  return (
    <div ref={mapRef} style={{ width: '100%', height, borderRadius: 12, overflow: 'hidden' }} />
  )
}
