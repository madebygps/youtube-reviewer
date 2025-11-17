import { useState, useRef, useEffect } from 'react'
import aspireLogo from '/Aspire.png'
import './App.css'

interface ActionableInsight {
  description: string
  timestamp: string
}

interface WebSocketEvent {
  type: string
  event?: any
  id?: string
  message?: string
  output?: ActionableInsight[]
  timestamp: string
}

function App() {
  const [videoUrl, setVideoUrl] = useState('')
  const [customPrompt, setCustomPrompt] = useState('')
  const [insights, setInsights] = useState<ActionableInsight[]>([])
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [progress, setProgress] = useState<string[]>([])
  const wsRef = useRef<WebSocket | null>(null)

  const generateInsights = async () => {
    if (!videoUrl.trim()) {
      setError('Please enter a YouTube URL')
      return
    }

    setLoading(true)
    setError(null)
    setInsights([])
    setProgress([])

    try {
      // Use relative path which will be proxied by Vite
      const ws = new WebSocket(`ws://${window.location.host}/ws/generateinsights`)
      wsRef.current = ws

      ws.onopen = () => {
        setProgress(prev => [...prev, '🔌 Connected to server...'])
        ws.send(JSON.stringify({ 
          video_url: videoUrl,
          custom_prompt: customPrompt.trim() || undefined
        }))
      }

      ws.onmessage = (event) => {
        const data: WebSocketEvent = JSON.parse(event.data)
        
        switch (data.type) {
          case 'started':
            setProgress(prev => [...prev, `🚀 ${data.message || 'Workflow started'}`])
            break
          case 'workflow_started':
            setProgress(prev => [...prev, '📝 Extracting video captions...'])
            break
          case 'step_started':
            const startMsg = data.id === 'caption_extractor' 
              ? '📹 Downloading captions from YouTube...'
              : data.id === 'actionable_summary_generator'
              ? '🤖 Generating actionable insights with AI...'
              : `Starting: ${data.id}`
            setProgress(prev => [...prev, startMsg])
            break
          case 'step_completed':
            const completeMsg = data.id === 'caption_extractor'
              ? '✅ Captions extracted successfully'
              : data.id === 'actionable_summary_generator'
              ? '✅ AI analysis complete'
              : `Completed: ${data.id}`
            setProgress(prev => [...prev, completeMsg])
            break
          case 'workflow_output':
          case 'completed':
            if (data.output) {
              setInsights(data.output)
            }
            setProgress(prev => [...prev, `🎉 Generated ${data.output?.length || 0} actionable insights!`])
            setLoading(false)
            break
          case 'error':
            setError(data.message || 'An error occurred')
            setLoading(false)
            break
          case 'step_failed':
            setError(`Step failed: ${data.message}`)
            setLoading(false)
            break
          default:
            console.log('Event:', data.type, data)
        }
      }

      ws.onerror = () => {
        setError('WebSocket connection error. Make sure the backend is running.')
        setLoading(false)
      }

      ws.onclose = () => {
        if (loading) {
          setProgress(prev => [...prev, '🔌 Connection closed'])
        }
        wsRef.current = null
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to connect via WebSocket')
      setLoading(false)
    }
  }

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault()
    generateInsights()
  }

  const cancelWebSocket = () => {
    if (wsRef.current) {
      wsRef.current.close()
      wsRef.current = null
    }
    setLoading(false)
    setProgress(prev => [...prev, '❌ Cancelled by user'])
  }

  useEffect(() => {
    return () => {
      if (wsRef.current) {
        wsRef.current.close()
      }
    }
  }, [])

  return (
    <div className="app-container">
      <header className="app-header">
        <a 
          href="https://aspire.dev" 
          target="_blank" 
          rel="noopener noreferrer"
          aria-label="Visit Aspire website (opens in new tab)"
          className="logo-link"
        >
          <img src={aspireLogo} className="logo" alt="Aspire logo" />
        </a>
        <h1 className="app-title">YouTube Insights</h1>
        <p className="app-subtitle">Generate actionable insights from YouTube videos</p>
      </header>

      <main className="main-content">
        <section className="weather-section" aria-labelledby="insights-heading">
          <div className="card">
            <div className="section-header">
              <h2 id="insights-heading" className="section-title">Video Insights Generator</h2>
            </div>

            <form onSubmit={handleSubmit} className="url-form">
              <div className="form-group">
                <label htmlFor="video-url" className="form-label">
                  YouTube Video URL
                </label>
                <input
                  id="video-url"
                  type="text"
                  className="form-input"
                  placeholder="https://www.youtube.com/watch?v=..."
                  value={videoUrl}
                  onChange={(e) => setVideoUrl(e.target.value)}
                  disabled={loading}
                />
              </div>
              <div className="form-group">
                <label htmlFor="custom-prompt" className="form-label">
                  Custom Prompt (Optional)
                </label>
                <textarea
                  id="custom-prompt"
                  className="form-input"
                  placeholder="Enter a custom prompt for insight generation (e.g., 'Extract all technical concepts mentioned' or 'Identify marketing strategies discussed')..."
                  value={customPrompt}
                  onChange={(e) => setCustomPrompt(e.target.value)}
                  disabled={loading}
                  rows={4}
                  style={{ resize: 'vertical', fontFamily: 'inherit' }}
                />
                <p className="form-help-text">
                  Leave blank to use the default prompt. Custom prompts help tailor insights to your specific needs.
                </p>
              </div>
              <div className="form-actions">
                <button 
                  type="submit"
                  className="submit-button"
                  disabled={loading || !videoUrl.trim()}
                >
                  {loading ? '⏳ Generating Insights...' : '🚀 Generate Insights'}
                </button>
                {loading && (
                  <button 
                    type="button"
                    className="cancel-button"
                    onClick={cancelWebSocket}
                  >
                    ❌ Cancel
                  </button>
                )}
              </div>
            </form>
            
            {error && (
              <div className="error-message" role="alert" aria-live="polite">
                <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" aria-hidden="true">
                  <circle cx="12" cy="12" r="10"/>
                  <line x1="12" y1="8" x2="12" y2="12"/>
                  <line x1="12" y1="16" x2="12.01" y2="16"/>
                </svg>
                <span>{error}</span>
              </div>
            )}

            {progress.length > 0 && (
              <div className="progress-section">
                <h3 className="progress-title">📊 Progress</h3>
                <div className="progress-log">
                  {progress.map((msg, idx) => (
                    <div key={idx} className="progress-item">
                      <span>{msg}</span>
                    </div>
                  ))}
                </div>
              </div>
            )}
            
            {loading && (
              <div className="loading-skeleton" role="status" aria-live="polite" aria-label="Generating insights">
                {[...Array(3)].map((_, i) => (
                  <div key={i} className="skeleton-row" aria-hidden="true" />
                ))}
                <span className="visually-hidden">Generating insights...</span>
              </div>
            )}
            
            {insights.length > 0 && (
              <div className="insights-container">
                <h3 className="insights-title">Actionable Insights ({insights.length})</h3>
                <div className="insights-grid">
                  {insights.map((insight, index) => (
                    <article key={index} className="insight-card">
                      <div className="insight-header">
                        <span className="insight-number">#{index + 1}</span>
                        <span className="insight-timestamp">{insight.timestamp}</span>
                      </div>
                      <p className="insight-description">{insight.description}</p>
                    </article>
                  ))}
                </div>
              </div>
            )}
          </div>
        </section>
      </main>

      <footer className="app-footer">
        <nav aria-label="Footer navigation">
          <a href="https://aspire.dev" target="_blank" rel="noopener noreferrer">
            Learn more about Aspire<span className="visually-hidden"> (opens in new tab)</span>
          </a>
          <a 
            href="https://github.com/dotnet/aspire" 
            target="_blank" 
            rel="noopener noreferrer"
            className="github-link"
            aria-label="View Aspire on GitHub (opens in new tab)"
          >
            <img src="/github.svg" alt="" width="24" height="24" aria-hidden="true" />
            <span className="visually-hidden">GitHub</span>
          </a>
        </nav>
      </footer>
    </div>
  )
}

export default App
