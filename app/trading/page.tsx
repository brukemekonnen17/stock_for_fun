'use client'

import { useState, useEffect } from 'react'
import '../page.css'

interface BanditLog {
  ts: string
  arm_name: string
  reward: number
}

interface ArmStats {
  arm_name: string
  count: number
  avg_reward: number
  min_reward: number
  max_reward: number
}

export default function TradingDashboard() {
  const [recentLogs, setRecentLogs] = useState<BanditLog[]>([])
  const [armStats, setArmStats] = useState<ArmStats[]>([])
  const [totalDecisions, setTotalDecisions] = useState(0)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [autoRefresh, setAutoRefresh] = useState(true)
  const [lastUpdate, setLastUpdate] = useState<Date | null>(null)

  const fetchData = async () => {
    setLoading(true)
    setError(null)
    
    try {
      // Fetch recent logs
      const logsResponse = await fetch('/api/bandit/logs?limit=10')
      if (!logsResponse.ok) throw new Error('Failed to fetch logs')
      const logsData = await logsResponse.json()
      setRecentLogs(logsData.logs || [])
      
      // Fetch arm statistics
      const statsResponse = await fetch('/api/bandit/stats')
      if (!statsResponse.ok) throw new Error('Failed to fetch stats')
      const statsData = await statsResponse.json()
      setArmStats(statsData.arm_stats || [])
      setTotalDecisions(statsData.total || 0)
      
      setLastUpdate(new Date())
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to fetch data')
      console.error('Dashboard error:', err)
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    fetchData()

    if (autoRefresh) {
      const interval = setInterval(fetchData, 5000) // Refresh every 5 seconds
      return () => clearInterval(interval)
    }
  }, [autoRefresh])

  const formatTimestamp = (ts: string) => {
    return new Date(ts).toLocaleTimeString()
  }

  const getRewardColor = (reward: number) => {
    if (reward > 0.5) return '#4ade80' // green
    if (reward > 0) return '#fbbf24' // yellow
    return '#f87171' // red
  }

  const getArmBadgeColor = (armName: string) => {
    const colors: Record<string, string> = {
      'EARNINGS_PRE': '#8b5cf6',
      'POST_EVENT_MOMO': '#3b82f6',
      'NEWS_SPIKE': '#ef4444',
      'REACTIVE': '#f59e0b',
      'SKIP': '#6b7280'
    }
    return colors[armName] || '#6b7280'
  }

  return (
    <div className="container" style={{ maxWidth: '1400px' }}>
      <header className="header">
        <h1>📊 Trading Dashboard</h1>
        <p className="subtitle">Live bandit performance and trading activity</p>
      </header>

      <div className="controls">
        <button 
          onClick={fetchData} 
          disabled={loading}
          className="scan-button"
        >
          {loading ? 'Updating...' : '🔄 Refresh'}
        </button>
        
        <label className="toggle">
          <input
            type="checkbox"
            checked={autoRefresh}
            onChange={(e) => setAutoRefresh(e.target.checked)}
          />
          <span>Auto-refresh (5s)</span>
        </label>

        {lastUpdate && (
          <span className="last-scan">
            Last update: {lastUpdate.toLocaleTimeString()}
          </span>
        )}

        <a href="/" className="scan-button" style={{ marginLeft: 'auto', textDecoration: 'none' }}>
          🎯 Catalyst Radar
        </a>
      </div>

      {error && (
        <div className="error-banner">
          ⚠️ {error}
        </div>
      )}

      {/* Summary Stats */}
      <div style={{ marginBottom: '2rem' }}>
        <div style={{ 
          background: 'rgba(255, 255, 255, 0.1)', 
          backdropFilter: 'blur(10px)',
          borderRadius: '12px',
          padding: '1.5rem',
          border: '1px solid rgba(255, 255, 255, 0.2)'
        }}>
          <h2 style={{ marginBottom: '1rem', fontSize: '1.5rem' }}>📈 Overview</h2>
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(200px, 1fr))', gap: '1rem' }}>
            <div>
              <div style={{ fontSize: '0.9rem', opacity: 0.7 }}>Total Decisions</div>
              <div style={{ fontSize: '2rem', fontWeight: 'bold' }}>{totalDecisions}</div>
            </div>
            <div>
              <div style={{ fontSize: '0.9rem', opacity: 0.7 }}>Active Arms</div>
              <div style={{ fontSize: '2rem', fontWeight: 'bold' }}>{armStats.length}</div>
            </div>
            <div>
              <div style={{ fontSize: '0.9rem', opacity: 0.7 }}>Best Performer</div>
              <div style={{ fontSize: '1.2rem', fontWeight: 'bold', marginTop: '0.5rem' }}>
                {armStats.length > 0 ? armStats[0].arm_name : '-'}
              </div>
            </div>
          </div>
        </div>
      </div>

      {/* Arm Performance */}
      <div style={{ marginBottom: '2rem' }}>
        <h2 style={{ marginBottom: '1rem', fontSize: '1.5rem' }}>🎯 Strategy Performance</h2>
        
        {armStats.length === 0 && !loading ? (
          <div className="empty-state">
            <p>No trading data yet. Start paper trading to see performance.</p>
          </div>
        ) : (
          <div className="results-grid">
            {armStats.map((stat) => (
              <div key={stat.arm_name} className="result-card">
                <div className="card-header">
                  <div 
                    style={{
                      padding: '0.5rem 1rem',
                      borderRadius: '20px',
                      backgroundColor: getArmBadgeColor(stat.arm_name),
                      fontWeight: 'bold',
                      fontSize: '0.9rem'
                    }}
                  >
                    {stat.arm_name}
                  </div>
                  <div 
                    className="confidence-badge"
                    style={{ 
                      backgroundColor: getRewardColor(stat.avg_reward),
                      fontSize: '1rem'
                    }}
                  >
                    {stat.avg_reward.toFixed(3)}
                  </div>
                </div>
                
                <div style={{ marginTop: '1rem' }}>
                  <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '0.5rem' }}>
                    <span style={{ opacity: 0.8 }}>Times Selected:</span>
                    <strong>{stat.count}</strong>
                  </div>
                  <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '0.5rem' }}>
                    <span style={{ opacity: 0.8 }}>Best:</span>
                    <strong style={{ color: '#4ade80' }}>{stat.max_reward.toFixed(3)}</strong>
                  </div>
                  <div style={{ display: 'flex', justifyContent: 'space-between' }}>
                    <span style={{ opacity: 0.8 }}>Worst:</span>
                    <strong style={{ color: '#f87171' }}>{stat.min_reward.toFixed(3)}</strong>
                  </div>
                </div>

                {/* Performance bar */}
                <div style={{ marginTop: '1rem' }}>
                  <div style={{ 
                    height: '8px', 
                    background: 'rgba(255,255,255,0.1)', 
                    borderRadius: '4px',
                    overflow: 'hidden'
                  }}>
                    <div style={{
                      height: '100%',
                      width: `${Math.max(0, Math.min(100, (stat.avg_reward + 1) * 50))}%`,
                      background: getRewardColor(stat.avg_reward),
                      transition: 'width 0.3s ease'
                    }} />
                  </div>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>

      {/* Recent Activity */}
      <div>
        <h2 style={{ marginBottom: '1rem', fontSize: '1.5rem' }}>📝 Recent Decisions</h2>
        
        {recentLogs.length === 0 && !loading ? (
          <div className="empty-state">
            <p>No decisions logged yet.</p>
          </div>
        ) : (
          <div style={{
            background: 'rgba(255, 255, 255, 0.1)',
            backdropFilter: 'blur(10px)',
            borderRadius: '12px',
            padding: '1.5rem',
            border: '1px solid rgba(255, 255, 255, 0.2)'
          }}>
            <table style={{ width: '100%', borderCollapse: 'collapse' }}>
              <thead>
                <tr style={{ borderBottom: '1px solid rgba(255,255,255,0.2)' }}>
                  <th style={{ padding: '0.75rem', textAlign: 'left' }}>Time</th>
                  <th style={{ padding: '0.75rem', textAlign: 'left' }}>Strategy Arm</th>
                  <th style={{ padding: '0.75rem', textAlign: 'right' }}>Reward</th>
                  <th style={{ padding: '0.75rem', textAlign: 'right' }}>R-Multiple</th>
                </tr>
              </thead>
              <tbody>
                {recentLogs.map((log, idx) => (
                  <tr 
                    key={idx}
                    style={{ 
                      borderBottom: idx < recentLogs.length - 1 ? '1px solid rgba(255,255,255,0.1)' : 'none',
                      opacity: 1 - (idx * 0.08)
                    }}
                  >
                    <td style={{ padding: '0.75rem' }}>
                      {formatTimestamp(log.ts)}
                    </td>
                    <td style={{ padding: '0.75rem' }}>
                      <span style={{
                        padding: '0.25rem 0.75rem',
                        borderRadius: '12px',
                        backgroundColor: getArmBadgeColor(log.arm_name),
                        fontSize: '0.85rem',
                        fontWeight: '600'
                      }}>
                        {log.arm_name}
                      </span>
                    </td>
                    <td style={{ padding: '0.75rem', textAlign: 'right' }}>
                      <span style={{
                        color: getRewardColor(log.reward),
                        fontWeight: 'bold'
                      }}>
                        {log.reward > 0 ? '+' : ''}{log.reward.toFixed(4)}
                      </span>
                    </td>
                    <td style={{ padding: '0.75rem', textAlign: 'right' }}>
                      <span style={{
                        padding: '0.25rem 0.5rem',
                        borderRadius: '8px',
                        backgroundColor: log.reward > 0 ? 'rgba(74, 222, 128, 0.2)' : 'rgba(248, 113, 113, 0.2)',
                        fontSize: '0.85rem'
                      }}>
                        {log.reward.toFixed(2)}R
                      </span>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </div>
  )
}

