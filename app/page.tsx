'use client'

import { useState, useEffect } from 'react'
import './page.css'

interface ScanResult {
  symbol: string
  catalyst: string
  confidence: number
  timestamp: string
  context?: Record<string, any>
}

export default function CatalystRadar() {
  const [scanResults, setScanResults] = useState<ScanResult[]>([])
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [autoRefresh, setAutoRefresh] = useState(true)
  const [lastScanTime, setLastScanTime] = useState<Date | null>(null)

  const fetchScan = async () => {
    setLoading(true)
    setError(null)
    
    try {
      const response = await fetch('/api/scan')
      if (!response.ok) {
        throw new Error(`Scan failed: ${response.statusText}`)
      }
      
      const data = await response.json()
      
      // Handle both single result and array of results
      const results = Array.isArray(data) ? data : (data.results || [data])
      
      setScanResults(results)
      setLastScanTime(new Date())
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to fetch scan results')
      console.error('Scan error:', err)
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    // Initial scan
    fetchScan()

    // Auto-refresh if enabled
    if (autoRefresh) {
      const interval = setInterval(fetchScan, 30000) // Refresh every 30 seconds
      return () => clearInterval(interval)
    }
  }, [autoRefresh])

  const formatTimestamp = (ts: string) => {
    return new Date(ts).toLocaleString()
  }

  const getConfidenceColor = (confidence: number) => {
    if (confidence >= 0.8) return '#4ade80' // green
    if (confidence >= 0.6) return '#fbbf24' // yellow
    return '#f87171' // red
  }

  return (
    <div className="container">
      <header className="header">
        <h1>🎯 Catalyst Radar</h1>
        <p className="subtitle">Real-time catalyst scanning and insights</p>
      </header>

      <div style={{ textAlign: 'center', marginBottom: '1rem' }}>
        <a 
          href="/trading" 
          style={{
            display: 'inline-block',
            background: 'rgba(255, 255, 255, 0.2)',
            border: '2px solid rgba(255, 255, 255, 0.3)',
            color: 'white',
            padding: '0.5rem 1rem',
            borderRadius: '8px',
            textDecoration: 'none',
            fontWeight: '600',
            transition: 'all 0.2s'
          }}
          onMouseOver={(e) => {
            e.currentTarget.style.background = 'rgba(255, 255, 255, 0.3)'
            e.currentTarget.style.transform = 'translateY(-2px)'
          }}
          onMouseOut={(e) => {
            e.currentTarget.style.background = 'rgba(255, 255, 255, 0.2)'
            e.currentTarget.style.transform = 'translateY(0)'
          }}
        >
          📊 View Trading Dashboard
        </a>
      </div>

      <div className="controls">
        <button 
          onClick={fetchScan} 
          disabled={loading}
          className="scan-button"
        >
          {loading ? 'Scanning...' : '🔍 Scan Now'}
        </button>
        
        <label className="toggle">
          <input
            type="checkbox"
            checked={autoRefresh}
            onChange={(e) => setAutoRefresh(e.target.checked)}
          />
          <span>Auto-refresh (30s)</span>
        </label>

        {lastScanTime && (
          <span className="last-scan">
            Last scan: {lastScanTime.toLocaleTimeString()}
          </span>
        )}
      </div>

      {error && (
        <div className="error-banner">
          ⚠️ {error}
        </div>
      )}

      <div className="results-container">
        {scanResults.length === 0 && !loading ? (
          <div className="empty-state">
            <p>No catalysts detected yet.</p>
            <p className="hint">Click "Scan Now" to search for trading opportunities.</p>
          </div>
        ) : (
          <div className="results-grid">
            {scanResults.map((result, idx) => (
              <div key={idx} className="result-card">
                <div className="card-header">
                  <h2 className="symbol">{result.symbol}</h2>
                  <div 
                    className="confidence-badge"
                    style={{ backgroundColor: getConfidenceColor(result.confidence) }}
                  >
                    {(result.confidence * 100).toFixed(0)}%
                  </div>
                </div>
                
                <div className="catalyst-text">
                  {result.catalyst}
                </div>
                
                <div className="card-footer">
                  <span className="timestamp">
                    {formatTimestamp(result.timestamp)}
                  </span>
                  
                  {result.context && Object.keys(result.context).length > 0 && (
                    <details className="context-details">
                      <summary>Context</summary>
                      <pre>{JSON.stringify(result.context, null, 2)}</pre>
                    </details>
                  )}
                </div>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  )
}

