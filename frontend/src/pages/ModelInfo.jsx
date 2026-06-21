import { useState, useEffect } from 'react'
import { getModelMetrics } from '../api'

export default function ModelInfo() {
  const [metrics, setMetrics] = useState(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)

  useEffect(() => {
    fetchMetrics()
  }, [])

  const fetchMetrics = async () => {
    try {
      const data = await getModelMetrics()
      setMetrics(data)
    } catch (err) {
      setError('Failed to load model metrics. Models may not be trained yet.')
    } finally {
      setLoading(false)
    }
  }

  if (loading) return <div style={{ padding: 40, textAlign: 'center' }}><div className="spinner" style={{ margin: '0 auto 16px auto' }} />Loading model metrics...</div>
  if (error) return <div style={{ padding: 40, textAlign: 'center', color: '#ef4444' }}>{error}</div>

  const targets = metrics?.metadata?.targets || {}
  const comparison = metrics?.comparison || {}

  return (
    <div>
      <div style={{ marginBottom: 24 }}>
        <h1 style={{ fontSize: 28, fontWeight: 800 }} className="gradient-text">Model Architecture & Metrics</h1>
        <p style={{ color: 'var(--text-secondary)', marginTop: 4, fontSize: 14 }}>
          Performance metrics for the CrowdFlow ML engine. Trained on {new Date(metrics?.metadata?.training_date).toLocaleString()}
        </p>
      </div>

      <div style={{ display: 'grid', gap: 20 }}>
        {Object.entries(targets).map(([targetName, targetInfo]) => {
          const compData = comparison[targetName]?.results || {}

          return (
            <div key={targetName} className="glass-card" style={{ padding: 24 }}>
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: 20 }}>
                <div>
                  <h2 style={{ fontSize: 18, fontWeight: 700, textTransform: 'capitalize' }}>
                    {targetName.replace(/_/g, ' ')}
                  </h2>
                  <div style={{ display: 'flex', gap: 8, marginTop: 8 }}>
                    <span style={{ fontSize: 11, padding: '2px 8px', borderRadius: 4, background: 'rgba(59,130,246,0.1)', color: '#3b82f6', textTransform: 'uppercase', fontWeight: 600 }}>
                      {targetInfo.task_type}
                    </span>
                    {targetInfo.ground_truth ? (
                      <span style={{ fontSize: 11, padding: '2px 8px', borderRadius: 4, background: 'rgba(34,197,94,0.1)', color: '#22c55e', fontWeight: 600 }}>GROUND TRUTH</span>
                    ) : (
                      <span style={{ fontSize: 11, padding: '2px 8px', borderRadius: 4, background: 'rgba(234,179,8,0.1)', color: '#eab308', fontWeight: 600 }}>HEURISTIC</span>
                    )}
                  </div>
                </div>
                <div style={{ textAlign: 'right' }}>
                  <div style={{ fontSize: 12, color: 'var(--text-muted)' }}>Winning Algorithm</div>
                  <div style={{ fontSize: 16, fontWeight: 700, color: 'var(--accent-purple)' }}>{targetInfo.best_algorithm}</div>
                </div>
              </div>

              <div style={{ display: 'flex', gap: 24, marginBottom: 20, padding: 16, background: 'var(--bg-secondary)', borderRadius: 8 }}>
                <div><div style={{ fontSize: 11, color: 'var(--text-muted)' }}>Train Samples</div><div style={{ fontSize: 18, fontWeight: 600 }}>{targetInfo.train_samples?.toLocaleString()}</div></div>
                <div><div style={{ fontSize: 11, color: 'var(--text-muted)' }}>Test Samples</div><div style={{ fontSize: 18, fontWeight: 600 }}>{targetInfo.test_samples?.toLocaleString()}</div></div>
                <div><div style={{ fontSize: 11, color: 'var(--text-muted)' }}>CV Score (Mean)</div><div style={{ fontSize: 18, fontWeight: 600, color: 'var(--accent-cyan)' }}>{Math.abs(targetInfo.cv_mean).toFixed(4)}</div></div>
              </div>

              {/* Algorithm Comparison Table */}
              <div style={{ overflowX: 'auto' }}>
                <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: 13 }}>
                  <thead>
                    <tr style={{ borderBottom: '1px solid var(--border-color)', color: 'var(--text-muted)' }}>
                      <th style={{ padding: '8px 0', textAlign: 'left', fontWeight: 600 }}>Algorithm</th>
                      <th style={{ padding: '8px 0', textAlign: 'right', fontWeight: 600 }}>CV Score</th>
                      {targetInfo.task_type === 'classification' ? (
                        <>
                          <th style={{ padding: '8px 0', textAlign: 'right', fontWeight: 600 }}>Test Accuracy</th>
                          <th style={{ padding: '8px 0', textAlign: 'right', fontWeight: 600 }}>Test F1 (Macro)</th>
                        </>
                      ) : (
                        <>
                          <th style={{ padding: '8px 0', textAlign: 'right', fontWeight: 600 }}>Test MAE</th>
                          <th style={{ padding: '8px 0', textAlign: 'right', fontWeight: 600 }}>Test R²</th>
                        </>
                      )}
                    </tr>
                  </thead>
                  <tbody>
                    {Object.entries(compData).map(([algo, metrics]) => {
                      const isWinner = algo === targetInfo.best_algorithm
                      return (
                        <tr key={algo} style={{ borderBottom: '1px solid var(--border-color)', background: isWinner ? 'rgba(59,130,246,0.05)' : 'transparent' }}>
                          <td style={{ padding: '10px 0', fontWeight: isWinner ? 700 : 400, color: isWinner ? 'var(--accent-blue)' : 'inherit' }}>
                            {algo} {isWinner && '🏆'}
                          </td>
                          <td style={{ padding: '10px 0', textAlign: 'right' }}>{Math.abs(metrics.cv_mean).toFixed(4)}</td>
                          {targetInfo.task_type === 'classification' ? (
                            <>
                              <td style={{ padding: '10px 0', textAlign: 'right' }}>{metrics.test_accuracy?.toFixed(4) || 'N/A'}</td>
                              <td style={{ padding: '10px 0', textAlign: 'right' }}>{metrics.test_f1_macro?.toFixed(4) || 'N/A'}</td>
                            </>
                          ) : (
                            <>
                              <td style={{ padding: '10px 0', textAlign: 'right' }}>{metrics.test_mae?.toFixed(4) || 'N/A'}</td>
                              <td style={{ padding: '10px 0', textAlign: 'right' }}>{metrics.test_r2?.toFixed(4) || 'N/A'}</td>
                            </>
                          )}
                        </tr>
                      )
                    })}
                  </tbody>
                </table>
              </div>
            </div>
          )
        })}
      </div>
    </div>
  )
}
