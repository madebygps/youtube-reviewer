import { useState, useRef, useEffect } from 'react'
import aspireLogo from '/Aspire.png'
import './App.css'

interface ConceptExplanation {
  term: string
  definition: string
  historical_context?: string
  how_it_works?: string
  relevance_to_content: string
  timestamp?: string
}

// Phase 1 response - just key concepts
interface KeyConceptsResponse {
  key_concepts: ConceptExplanation[]
}

interface WebSocketEvent {
  type: string
  event?: any
  id?: string
  message?: string
  output?: KeyConceptsResponse
  timestamp: string
}

function App() {
  const [videoUrl, setVideoUrl] = useState('')
  const [videoId, setVideoId] = useState<string | null>(null)
  const [notes, setNotes] = useState<KeyConceptsResponse | null>(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [progress, setProgress] = useState<string[]>([])
  const [expandedConcepts, setExpandedConcepts] = useState<Set<number>>(new Set())
  const [expandedSections, setExpandedSections] = useState<Set<string>>(new Set(['concepts']))
  const wsRef = useRef<WebSocket | null>(null)

  const toggleSection = (section: string) => {
    setExpandedSections(prev => {
      const next = new Set(prev)
      if (next.has(section)) {
        next.delete(section)
      } else {
        next.add(section)
      }
      return next
    })
  }

  const extractVideoId = (url: string): string | null => {
    const patterns = [
      /(?:youtube\.com\/watch\?v=|youtu\.be\/|youtube\.com\/embed\/)([^&\n?#]+)/,
      /youtube\.com\/shorts\/([^&\n?#]+)/,
    ]
    for (const pattern of patterns) {
      const match = url.match(pattern)
      if (match) return match[1]
    }
    return null
  }

  const toggleConcept = (index: number) => {
    setExpandedConcepts(prev => {
      const next = new Set(prev)
      if (next.has(index)) {
        next.delete(index)
      } else {
        next.add(index)
      }
      return next
    })
  }

  const copyNotes = async () => {
    if (!notes) return
    
    const formatted = [
      `# Key Concepts`,
      ...notes.key_concepts.map(c => 
        `## ${c.term}\n${c.definition}${c.historical_context ? `\n\n**Historical Context:** ${c.historical_context}` : ''}${c.how_it_works ? `\n\n**How it works:** ${c.how_it_works}` : ''}\n\n**Relevance:** ${c.relevance_to_content}${c.timestamp ? `\n\n**Timestamp:** ${c.timestamp}` : ''}`
      ),
    ].join('\n\n')

    await navigator.clipboard.writeText(formatted)
  }

  const generateInsights = async () => {
    if (!videoUrl.trim()) {
      setError('Please enter a YouTube URL')
      return
    }

    const extractedId = extractVideoId(videoUrl)
    if (!extractedId) {
      setError('Invalid YouTube URL')
      return
    }

    setVideoId(extractedId)
    setLoading(true)
    setError(null)
    setNotes(null)
    setProgress([])
    setExpandedConcepts(new Set())

    try {
      const ws = new WebSocket(`ws://${window.location.host}/ws/generateinsights`)
      wsRef.current = ws

      ws.onopen = () => {
        setProgress(prev => [...prev, '🔌 Connected to server...'])
        ws.send(JSON.stringify({ video_url: videoUrl }))
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
              : data.id === 'key_concepts_extractor'
              ? '🧠 Extracting key concepts with AI...'
              : `Starting: ${data.id}`
            setProgress(prev => [...prev, startMsg])
            break
          case 'step_completed':
            const completeMsg = data.id === 'caption_extractor'
              ? '✅ Captions extracted successfully'
              : data.id === 'key_concepts_extractor'
              ? '✅ Key concepts extracted'
              : `Completed: ${data.id}`
            setProgress(prev => [...prev, completeMsg])
            break
          case 'workflow_output':
          case 'completed':
            if (data.output) {
              setNotes(data.output)
            }
            setProgress(prev => [...prev, `🎉 Phase 1 complete - Key concepts ready!`])
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
        
        <form onSubmit={handleSubmit} className="header-form">
          <input
            id="video-url"
            type="text"
            className="header-input"
            placeholder="Paste YouTube URL..."
            value={videoUrl}
            onChange={(e) => setVideoUrl(e.target.value)}
            disabled={loading}
          />
          <button 
            type="submit"
            className="header-submit"
            disabled={loading || !videoUrl.trim()}
            title="Generate Study Notes"
          >
            {loading ? '⏳' : '🧠'}
          </button>
          {loading && (
            <button 
              type="button"
              className="header-cancel"
              onClick={cancelWebSocket}
              title="Cancel"
            >
              ✕
            </button>
          )}
        </form>

        <span className="app-title">YouTube Deep Comprehension</span>
      </header>

      {error && (
        <div className="error-banner" role="alert" aria-live="polite">
          <span>{error}</span>
          <button onClick={() => setError(null)} className="error-dismiss">✕</button>
        </div>
      )}

      <main className="main-content">
        {/* Loading/Progress State */}
        {loading && (
          <div className="loading-overlay">
            <div className="loading-content">
              <div className="loading-spinner"></div>
              <div className="progress-compact">
                {progress.slice(-3).map((msg, idx) => (
                  <div key={idx} className="progress-item-compact">{msg}</div>
                ))}
              </div>
            </div>
          </div>
        )}

        {/* Video + Notes Split View */}
        {(videoId || notes) && (
          <section className="study-section">
            <div className="study-layout">
              {/* Video Player - Sticky */}
              {videoId && (
                <div className="video-panel">
                  <div className="video-container">
                    <iframe
                      src={`https://www.youtube.com/embed/${videoId}`}
                      title="YouTube video player"
                      frameBorder="0"
                      allow="accelerometer; autoplay; clipboard-write; encrypted-media; gyroscope; picture-in-picture; web-share"
                      allowFullScreen
                    />
                  </div>
                </div>
              )}

              {/* Notes Panel - Scrollable */}
              {notes && (
                <div className="notes-panel">
                  <div className="notes-container">
                    <div className="notes-header">
                      <h3 className="notes-title">📚 Phase 1: Key Concepts</h3>
                      <button className="copy-all-button" onClick={copyNotes} title="Copy all notes as Markdown">
                        <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                          <rect x="9" y="9" width="13" height="13" rx="2" ry="2"></rect>
                          <path d="M5 15H4a2 2 0 0 1-2-2V4a2 2 0 0 1 2-2h9a2 2 0 0 1 2 2v1"></path>
                        </svg>
                      </button>
                    </div>

                    {/* Phase indicator */}
                    <div className="phase-indicator">
                      <span className="phase-badge phase-active">Phase 1: Orient</span>
                      <span className="phase-badge phase-upcoming">Phase 2: Understand</span>
                      <span className="phase-badge phase-upcoming">Phase 3: Connect</span>
                      <span className="phase-badge phase-upcoming">Phase 4: Test</span>
                    </div>

                    <p className="phase-instruction">
                      Watch the video with these key concepts in mind. When ready, you'll be able to proceed to deeper analysis.
                    </p>

                    {/* Key Concepts */}
                    <div className="notes-section">
                      <button className="section-toggle" onClick={() => toggleSection('concepts')} aria-expanded={expandedSections.has('concepts')}>
                        <span>📖 Key Concepts ({notes.key_concepts.length})</span>
                        <span className={`expand-icon ${expandedSections.has('concepts') ? 'expanded' : ''}`}>▼</span>
                      </button>
                      {expandedSections.has('concepts') && (
                        <div className="concepts-list">
                          {notes.key_concepts.map((concept, index) => (
                            <div key={index} className="concept-card">
                              <button 
                                className="concept-header"
                                onClick={() => toggleConcept(index)}
                                aria-expanded={expandedConcepts.has(index)}
                              >
                                <span className="concept-term">{concept.term}</span>
                                {concept.timestamp && <span className="concept-timestamp">{concept.timestamp}</span>}
                                <span className={`expand-icon ${expandedConcepts.has(index) ? 'expanded' : ''}`}>▼</span>
                              </button>
                              {expandedConcepts.has(index) && (
                                <div className="concept-details">
                                  <p className="concept-definition"><strong>Definition:</strong> {concept.definition}</p>
                                  {concept.historical_context && (
                                    <p className="concept-history"><strong>Historical Context:</strong> {concept.historical_context}</p>
                                  )}
                                  {concept.how_it_works && (
                                    <p className="concept-mechanics"><strong>How it works:</strong> {concept.how_it_works}</p>
                                  )}
                                  <p className="concept-relevance"><strong>Relevance:</strong> {concept.relevance_to_content}</p>
                                </div>
                              )}
                            </div>
                          ))}
                        </div>
                      )}
                    </div>

                    {/* Future: Button to proceed to Phase 2 */}
                    <div className="phase-actions">
                      <button className="phase-next-button" disabled title="Coming soon: Proceed to deeper analysis">
                        I've watched the video - Go Deeper →
                      </button>
                    </div>
                  </div>
                </div>
              )}
            </div>
          </section>
        )}
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
