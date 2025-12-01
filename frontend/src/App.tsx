import { useState, useRef, useEffect } from 'react'
import aspireLogo from '/Aspire.png'
import './App.css'

interface ConceptExplanation {
  term: string
  definition: string
  relevance: string
  timestamp?: string
  timestamp_seconds?: number
}

interface ArgumentChain {
  title: string
  premise: string
  reasoning_steps: string[]
  conclusion: string
  implications?: string
}

// Phase 1 response - just key concepts
interface KeyConceptsResponse {
  key_concepts: ConceptExplanation[]
}

// Phase 2 response - thesis + arguments
interface ThesisArgumentResponse {
  main_thesis: string
  argument_chains: ArgumentChain[]
}

// Phase 3 response - connections
interface ConnectionInsight {
  concept_a: string
  concept_b: string
  relationship: string
  significance: string
}

interface ConnectionsResponse {
  connections: ConnectionInsight[]
  synthesis: string
}

// Phase 4 response - claim verification
interface VerifiedClaim {
  claim: string
  claim_type: string
  verdict: string
  reasoning: string
  evidence?: string
}

interface ClaimVerifierResponse {
  verified_claims: VerifiedClaim[]
  overall_credibility: string
  summary: string
  cautions?: string[]
}

// Phase 5 response - quiz
interface QuizQuestion {
  question: string
  options: string[]
  correct_answer: number
  explanation: string
  difficulty: string
  related_concept?: string
}

interface QuizResponse {
  questions: QuizQuestion[]
  passing_score: number
  quiz_focus: string
}

interface WebSocketEvent {
  type: string
  event?: any
  id?: string
  message?: string
  output?: any
  phase?: number
  // Phase 2 output shape
  output_thesis?: ThesisArgumentResponse
  output_phase?: any
  phase_output?: any
  output_generic?: any
  outputGeneric?: any
  output_any?: any
  timestamp: string
}

function App() {
  const [videoUrl, setVideoUrl] = useState('')
  const [videoId, setVideoId] = useState<string | null>(null)
  const [notes, setNotes] = useState<KeyConceptsResponse | null>(null)
  const [phase2, setPhase2] = useState<ThesisArgumentResponse | null>(null)
  const [phase3, setPhase3] = useState<ConnectionsResponse | null>(null)
  const [phase4, setPhase4] = useState<ClaimVerifierResponse | null>(null)
  const [phase5, setPhase5] = useState<QuizResponse | null>(null)
  const [quizAnswers, setQuizAnswers] = useState<Map<number, number>>(new Map())
  const [quizSubmitted, setQuizSubmitted] = useState(false)
  const [quizScore, setQuizScore] = useState<number | null>(null)
  const [loading, setLoading] = useState(false)
  const [loadingPhase, setLoadingPhase] = useState<number | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [progress, setProgress] = useState<string[]>([])
  const [progressPercent, setProgressPercent] = useState(0)
  const [progressStep, setProgressStep] = useState<string>('')
  const [expandedConcepts, setExpandedConcepts] = useState<Set<number>>(new Set())
  const [expandedArguments, setExpandedArguments] = useState<Set<number>>(new Set())
  const [expandedConnections, setExpandedConnections] = useState<Set<number>>(new Set())
  const [expandedClaims, setExpandedClaims] = useState<Set<number>>(new Set())
  const [expandedSections, setExpandedSections] = useState<Set<string>>(new Set(['concepts']))
  const [activePhase, setActivePhase] = useState<number>(1)
  const [knowledgeLevel, setKnowledgeLevel] = useState<'beginner' | 'intermediate' | 'advanced'>('intermediate')
  const wsRef = useRef<WebSocket | null>(null)
  const playerRef = useRef<HTMLIFrameElement | null>(null)

  const seekToTime = (seconds: number) => {
    if (playerRef.current && videoId) {
      // Use YouTube's postMessage API to seek
      playerRef.current.contentWindow?.postMessage(
        JSON.stringify({
          event: 'command',
          func: 'seekTo',
          args: [seconds, true]
        }),
        '*'
      )
    }
  }

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

  const toggleArgument = (index: number) => {
    setExpandedArguments(prev => {
      const next = new Set(prev)
      if (next.has(index)) next.delete(index)
      else next.add(index)
      return next
    })
  }

  const toggleConnection = (index: number) => {
    setExpandedConnections(prev => {
      const next = new Set(prev)
      if (next.has(index)) next.delete(index)
      else next.add(index)
      return next
    })
  }

  const toggleClaim = (index: number) => {
    setExpandedClaims(prev => {
      const next = new Set(prev)
      if (next.has(index)) next.delete(index)
      else next.add(index)
      return next
    })
  }

  const copyNotes = async () => {
    if (!notes) return
    
    const formatted = [
      `# Key Concepts`,
      ...notes.key_concepts.map(c => 
        `## ${c.term}\n${c.definition}\n\n**Relevance:** ${c.relevance}${c.timestamp ? ` (${c.timestamp})` : ''}`
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
    setLoadingPhase(1)
    setError(null)
    setNotes(null)
    setPhase2(null)
    setPhase3(null)
    setPhase4(null)
    setPhase5(null)
    setQuizAnswers(new Map())
    setQuizSubmitted(false)
    setQuizScore(null)
    setProgress([])
    setProgressPercent(0)
    setProgressStep('')
    setExpandedConcepts(new Set())
    setExpandedArguments(new Set())
    setExpandedConnections(new Set())
    setExpandedClaims(new Set())
    setActivePhase(1)

    try {
      const ws = new WebSocket(`ws://${window.location.host}/ws/phase1`)
      wsRef.current = ws

      ws.onopen = () => {
        setProgress(prev => [...prev, '🔌 Connected to server...'])
        setProgressPercent(5)
        setProgressStep('Connecting...')
        ws.send(JSON.stringify({ video_url: videoUrl, knowledge_level: knowledgeLevel }))
      }

      ws.onmessage = (event) => {
        const data: WebSocketEvent = JSON.parse(event.data)
        
        switch (data.type) {
          case 'started':
            setProgress(prev => [...prev, `🚀 ${data.message || 'Workflow started'}`])
            setProgressPercent(10)
            setProgressStep('Starting workflow...')
            break
          case 'workflow_started':
            setProgress(prev => [...prev, '📝 Extracting video captions...'])
            setProgressPercent(15)
            setProgressStep('Initializing...')
            break
          case 'step_started':
            const startMsg = data.id === 'caption_extractor' 
              ? '📹 Downloading captions from YouTube...'
              : data.id === 'key_concepts_extractor'
              ? '🧠 Extracting key concepts with AI...'
              : `Starting: ${data.id}`
            setProgress(prev => [...prev, startMsg])
            if (data.id === 'caption_extractor') {
              setProgressPercent(25)
              setProgressStep('Downloading captions...')
            } else if (data.id === 'key_concepts_extractor') {
              setProgressPercent(50)
              setProgressStep('AI analyzing content...')
            }
            break
          case 'step_completed':
            const completeMsg = data.id === 'caption_extractor'
              ? '✅ Captions extracted successfully'
              : data.id === 'key_concepts_extractor'
              ? '✅ Key concepts extracted'
              : `Completed: ${data.id}`
            setProgress(prev => [...prev, completeMsg])
            if (data.id === 'caption_extractor') {
              setProgressPercent(45)
              setProgressStep('Captions ready!')
            } else if (data.id === 'key_concepts_extractor') {
              setProgressPercent(95)
              setProgressStep('Almost done...')
            }
            break
          case 'workflow_output':
          case 'completed':
            if (data.event) {
              setNotes(data.event)
            }
            break
          case 'phase_completed':
            if (data.phase === 1) {
              if (data.output) {
                setNotes(data.output as KeyConceptsResponse)
              }
              setActivePhase(1)
              setProgress(prev => [...prev, '🎉 Phase 1 complete - Key concepts ready!'])
              setProgressPercent(100)
              setProgressStep('Complete!')
              setLoading(false)
              setLoadingPhase(null)
            }
            if (data.phase === 2) {
              setProgress(prev => [...prev, '🎉 Phase 2 complete - Thesis & arguments ready!'])
              setProgressPercent(100)
              setProgressStep('Complete!')
              setLoadingPhase(null)
            }
            break
          case 'phase_started':
            if (data.phase === 2) {
              setActivePhase(2)
              setLoadingPhase(2)
              setProgress(prev => [...prev, '🧠 Phase 2: Extracting thesis & arguments...'])
            }
            break
          case 'phase_output':
            if (data.phase === 2 && data.output) {
              setPhase2(data.output as ThesisArgumentResponse)
              setActivePhase(2)
              setLoadingPhase(null)
              setExpandedSections(new Set(['thesis']))  // Collapse concepts, expand thesis
              setProgress(prev => [...prev, '📝 Thesis & argument chains received'])
            }
            break
          case 'error':
            setError(data.message || 'An error occurred')
            setLoading(false)
            setLoadingPhase(null)
            break
          case 'step_failed':
            setError(`Step failed: ${data.message}`)
            setLoading(false)
            setLoadingPhase(null)
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
    setLoadingPhase(null)
    setProgress(prev => [...prev, '❌ Cancelled by user'])
  }

  const startPhase2 = () => {
    if (!videoId) {
      setError('No video ID available. Please run Phase 1 first.')
      return
    }

    setLoadingPhase(2)
    setActivePhase(2)
    setProgress(prev => [...prev, '➡️ Starting Phase 2...'])
    setProgressPercent(0)
    setProgressStep('Starting Phase 2...')

    try {
      const ws = new WebSocket(`ws://${window.location.host}/ws/phase2`)
      wsRef.current = ws

      ws.onopen = () => {
        setProgress(prev => [...prev, '🔌 Connected to Phase 2...'])
        setProgressPercent(10)
        setProgressStep('Connecting...')
        ws.send(JSON.stringify({ video_id: videoId }))
      }

      ws.onmessage = (event) => {
        const data: WebSocketEvent = JSON.parse(event.data)

        switch (data.type) {
          case 'phase_started':
            setProgress(prev => [...prev, '🧠 Extracting thesis & arguments...'])
            setProgressPercent(25)
            setProgressStep('Analyzing...')
            break
          case 'step_started':
            const startMsg = data.id === 'thesis_argument_extractor'
              ? '🧠 Analyzing argument chains...'
              : `Starting: ${data.id}`
            setProgress(prev => [...prev, startMsg])
            setProgressPercent(50)
            setProgressStep('AI analyzing arguments...')
            break
          case 'workflow_output':
            if (data.event) {
              setPhase2(data.event as ThesisArgumentResponse)
              setExpandedSections(new Set(['thesis']))
              setProgressPercent(90)
              setProgressStep('Processing results...')
              setProgress(prev => [...prev, '📝 Thesis & argument chains received'])
            }
            break
          case 'phase_completed':
            setProgress(prev => [...prev, '🎉 Phase 2 complete - Thesis & arguments ready!'])
            setProgressPercent(100)
            setProgressStep('Complete!')
            setLoadingPhase(null)
            break
          case 'error':
            setError(data.message || 'An error occurred in Phase 2')
            setLoadingPhase(null)
            break
          case 'step_failed':
            setError(`Phase 2 step failed: ${data.message}`)
            setLoadingPhase(null)
            break
          default:
            console.log('Phase 2 Event:', data.type, data)
        }
      }

      ws.onerror = () => {
        setError('Phase 2 WebSocket connection error.')
        setLoadingPhase(null)
      }

      ws.onclose = () => {
        if (loadingPhase === 2) {
          setProgress(prev => [...prev, '🔌 Phase 2 connection closed'])
        }
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to connect to Phase 2')
      setLoadingPhase(null)
    }
  }

  const startPhase3 = () => {
    if (!notes) {
      setError('No key concepts available. Please run Phase 1 first.')
      return
    }

    setLoadingPhase(3)
    setActivePhase(3)
    setProgress(prev => [...prev, '➡️ Starting Phase 3...'])
    setProgressPercent(0)
    setProgressStep('Starting Phase 3...')

    try {
      const ws = new WebSocket(`ws://${window.location.host}/ws/phase3`)
      wsRef.current = ws

      ws.onopen = () => {
        setProgress(prev => [...prev, '🔌 Connected to Phase 3...'])
        setProgressPercent(10)
        setProgressStep('Connecting...')
        ws.send(JSON.stringify({ key_concepts: notes.key_concepts }))
      }

      ws.onmessage = (event) => {
        const data: WebSocketEvent = JSON.parse(event.data)

        switch (data.type) {
          case 'phase_started':
            setProgress(prev => [...prev, '🔗 Finding connections between concepts...'])
            setProgressPercent(25)
            setProgressStep('Analyzing...')
            break
          case 'step_started':
            const startMsg = data.id === 'connections_extractor'
              ? '🔗 Discovering concept relationships...'
              : `Starting: ${data.id}`
            setProgress(prev => [...prev, startMsg])
            setProgressPercent(50)
            setProgressStep('AI finding connections...')
            break
          case 'workflow_output':
            if (data.event) {
              setPhase3(data.event as ConnectionsResponse)
              setExpandedSections(new Set(['connections']))
              setProgressPercent(90)
              setProgressStep('Processing results...')
              setProgress(prev => [...prev, '🔗 Connections discovered'])
            }
            break
          case 'phase_completed':
            setProgress(prev => [...prev, '🎉 Phase 3 complete - Connections ready!'])
            setProgressPercent(100)
            setProgressStep('Complete!')
            setLoadingPhase(null)
            break
          case 'error':
            setError(data.message || 'An error occurred in Phase 3')
            setLoadingPhase(null)
            break
          case 'step_failed':
            setError(`Phase 3 step failed: ${data.message}`)
            setLoadingPhase(null)
            break
          default:
            console.log('Phase 3 Event:', data.type, data)
        }
      }

      ws.onerror = () => {
        setError('Phase 3 WebSocket connection error.')
        setLoadingPhase(null)
      }

      ws.onclose = () => {
        if (loadingPhase === 3) {
          setProgress(prev => [...prev, '🔌 Phase 3 connection closed'])
        }
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to connect to Phase 3')
      setLoadingPhase(null)
    }
  }

  const startPhase4 = () => {
    if (!phase2) {
      setError('No thesis or arguments available. Please run Phase 2 first.')
      return
    }

    setLoadingPhase(4)
    setActivePhase(4)
    setProgress(prev => [...prev, '➡️ Starting Phase 4...'])
    setProgressPercent(0)
    setProgressStep('Starting Phase 4...')

    try {
      const ws = new WebSocket(`ws://${window.location.host}/ws/phase4`)
      wsRef.current = ws

      ws.onopen = () => {
        setProgress(prev => [...prev, '🔌 Connected to Phase 4...'])
        setProgressPercent(10)
        setProgressStep('Connecting...')
        ws.send(JSON.stringify({
          thesis: phase2.main_thesis,
          argument_chains: phase2.argument_chains,
          claims: phase2.argument_chains.map(a => a.conclusion)
        }))
      }

      ws.onmessage = (event) => {
        const data: WebSocketEvent = JSON.parse(event.data)

        switch (data.type) {
          case 'phase_started':
            setProgress(prev => [...prev, '🔍 Verifying claims...'])
            setProgressPercent(25)
            setProgressStep('Analyzing...')
            break
          case 'step_started':
            const startMsg = data.id === 'claim_verifier'
              ? '🔍 Fact-checking claims...'
              : `Starting: ${data.id}`
            setProgress(prev => [...prev, startMsg])
            setProgressPercent(50)
            setProgressStep('AI verifying claims...')
            break
          case 'workflow_output':
            if (data.event) {
              setPhase4(data.event as ClaimVerifierResponse)
              setExpandedSections(new Set(['claims']))
              setProgressPercent(90)
              setProgressStep('Processing results...')
              setProgress(prev => [...prev, '🔍 Claims verified'])
            }
            break
          case 'phase_completed':
            setProgress(prev => [...prev, '🎉 Phase 4 complete - Verification ready!'])
            setProgressPercent(100)
            setProgressStep('Complete!')
            setLoadingPhase(null)
            break
          case 'error':
            setError(data.message || 'An error occurred in Phase 4')
            setLoadingPhase(null)
            break
          case 'step_failed':
            setError(`Phase 4 step failed: ${data.message}`)
            setLoadingPhase(null)
            break
          default:
            console.log('Phase 4 Event:', data.type, data)
        }
      }

      ws.onerror = () => {
        setError('Phase 4 WebSocket connection error.')
        setLoadingPhase(null)
      }

      ws.onclose = () => {
        if (loadingPhase === 4) {
          setProgress(prev => [...prev, '🔌 Phase 4 connection closed'])
        }
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to connect to Phase 4')
      setLoadingPhase(null)
    }
  }

  const startPhase5 = () => {
    if (!notes) {
      setError('No content available for quiz generation.')
      return
    }

    setLoadingPhase(5)
    setActivePhase(5)
    setQuizAnswers(new Map())
    setQuizSubmitted(false)
    setQuizScore(null)
    setProgress(prev => [...prev, '➡️ Starting Phase 5...'])
    setProgressPercent(0)
    setProgressStep('Starting Phase 5...')

    try {
      const ws = new WebSocket(`ws://${window.location.host}/ws/phase5`)
      wsRef.current = ws

      ws.onopen = () => {
        setProgress(prev => [...prev, '🔌 Connected to Phase 5...'])
        setProgressPercent(10)
        setProgressStep('Connecting...')
        ws.send(JSON.stringify({
          key_concepts: notes.key_concepts,
          thesis: phase2?.main_thesis || '',
          argument_chains: phase2?.argument_chains || [],
          connections: phase3?.connections || [],
        }))
      }

      ws.onmessage = (event) => {
        const data: WebSocketEvent = JSON.parse(event.data)

        switch (data.type) {
          case 'phase_started':
            setProgress(prev => [...prev, '📝 Generating quiz...'])
            setProgressPercent(25)
            setProgressStep('Creating questions...')
            break
          case 'step_started':
            const startMsg = data.id === 'quiz_generator'
              ? '📝 Crafting quiz questions...'
              : `Starting: ${data.id}`
            setProgress(prev => [...prev, startMsg])
            setProgressPercent(50)
            setProgressStep('AI generating quiz...')
            break
          case 'workflow_output':
            if (data.event) {
              setPhase5(data.event as QuizResponse)
              setExpandedSections(new Set(['quiz']))
              setProgressPercent(90)
              setProgressStep('Processing results...')
              setProgress(prev => [...prev, '📝 Quiz generated'])
            }
            break
          case 'phase_completed':
            setProgress(prev => [...prev, '🎉 Phase 5 complete - Quiz ready!'])
            setProgressPercent(100)
            setProgressStep('Complete!')
            setLoadingPhase(null)
            break
          case 'error':
            setError(data.message || 'An error occurred in Phase 5')
            setLoadingPhase(null)
            break
          case 'step_failed':
            setError(`Phase 5 step failed: ${data.message}`)
            setLoadingPhase(null)
            break
          default:
            console.log('Phase 5 Event:', data.type, data)
        }
      }

      ws.onerror = () => {
        setError('Phase 5 WebSocket connection error.')
        setLoadingPhase(null)
      }

      ws.onclose = () => {
        if (loadingPhase === 5) {
          setProgress(prev => [...prev, '🔌 Phase 5 connection closed'])
        }
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to connect to Phase 5')
      setLoadingPhase(null)
    }
  }

  const handleQuizAnswer = (questionIndex: number, answerIndex: number) => {
    if (quizSubmitted) return
    setQuizAnswers(prev => {
      const next = new Map(prev)
      next.set(questionIndex, answerIndex)
      return next
    })
  }

  const submitQuiz = () => {
    if (!phase5) return
    
    let correct = 0
    phase5.questions.forEach((q, idx) => {
      if (quizAnswers.get(idx) === q.correct_answer) {
        correct++
      }
    })
    
    const score = Math.round((correct / phase5.questions.length) * 100)
    setQuizScore(score)
    setQuizSubmitted(true)
  }

  const retakeQuiz = () => {
    setQuizAnswers(new Map())
    setQuizSubmitted(false)
    setQuizScore(null)
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
          <select
            className="knowledge-select"
            value={knowledgeLevel}
            onChange={(e) => setKnowledgeLevel(e.target.value as 'beginner' | 'intermediate' | 'advanced')}
            disabled={loading}
            title="Your knowledge level"
          >
            <option value="beginner">🌱 Beginner</option>
            <option value="intermediate">📚 Intermediate</option>
            <option value="advanced">🎓 Advanced</option>
          </select>
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
        <a 
          href="https://github.com/madebygps/yt-reviewer" 
          target="_blank" 
          rel="noopener noreferrer"
          className="header-github-link"
          aria-label="View source on GitHub (opens in new tab)"
        >
          <img src="/github.svg" alt="" width="20" height="20" aria-hidden="true" />
        </a>
      </header>

      {error && (
        <div className="error-banner" role="alert" aria-live="polite">
          <span>{error}</span>
          <button onClick={() => setError(null)} className="error-dismiss">✕</button>
        </div>
      )}

      <main className="main-content">
        {/* Video + Notes Split View */}
        {(videoId || notes) && (
          <section className="study-section">
            <div className="study-layout">
              {/* Video Player - Sticky */}
              {videoId && (
                <div className="video-panel">
                  <div className="video-container">
                    <iframe
                      ref={playerRef}
                      src={`https://www.youtube.com/embed/${videoId}?enablejsapi=1`}
                      title="YouTube video player"
                      frameBorder="0"
                      allow="accelerometer; autoplay; clipboard-write; encrypted-media; gyroscope; picture-in-picture; web-share"
                      allowFullScreen
                    />
                  </div>
                </div>
              )}

              {/* Notes Panel - Scrollable */}
              {videoId && (
                <div className="notes-panel">
                  <div className="notes-container">
                    <div className="notes-header">
                      <h3 className="notes-title">📚 Phase 1: Key Concepts</h3>
                      {notes && (
                        <button className="copy-all-button" onClick={copyNotes} title="Copy all notes as Markdown">
                          <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                            <rect x="9" y="9" width="13" height="13" rx="2" ry="2"></rect>
                            <path d="M5 15H4a2 2 0 0 1-2-2V4a2 2 0 0 1 2-2h9a2 2 0 0 1 2 2v1"></path>
                          </svg>
                        </button>
                      )}
                    </div>

                    {/* Phase indicator */}
                    <div className="phase-indicator">
                      <span className={`phase-badge ${activePhase === 1 ? 'phase-active' : (phase2 || phase3 || phase4 || phase5) ? 'phase-completed' : ''}`}>Phase 1: Orient</span>
                      <span className={`phase-badge ${activePhase === 2 ? 'phase-active' : (phase3 || phase4 || phase5) ? 'phase-completed' : phase2 ? 'phase-completed' : 'phase-upcoming'}`}>Phase 2: Understand</span>
                      <span className={`phase-badge ${activePhase === 3 ? 'phase-active' : (phase4 || phase5) ? 'phase-completed' : phase3 ? 'phase-completed' : 'phase-upcoming'}`}>Phase 3: Connect</span>
                      <span className={`phase-badge ${activePhase === 4 ? 'phase-active' : phase5 ? 'phase-completed' : phase4 ? 'phase-completed' : 'phase-upcoming'}`}>Phase 4: Verify</span>
                      <span className={`phase-badge ${activePhase === 5 ? 'phase-active' : phase5 ? 'phase-completed' : 'phase-upcoming'}`}>Phase 5: Test</span>
                    </div>

                    <p className="phase-instruction">
                      Watch the video with these key concepts in mind. When ready, you'll be able to proceed to deeper analysis.
                    </p>

                    {/* Key Concepts */}
                    <div className="notes-section">
                      <button className="section-toggle" onClick={() => toggleSection('concepts')} aria-expanded={expandedSections.has('concepts')}>
                        <span>📖 Key Concepts {notes ? `(${notes.key_concepts.length})` : ''}</span>
                        <span className={`expand-icon ${expandedSections.has('concepts') ? 'expanded' : ''}`}>▼</span>
                      </button>
                      {expandedSections.has('concepts') && (
                        <div className="concepts-list">
                          {!notes ? (
                            /* Loading skeleton */
                            <div className="concepts-loading">
                              <div className="progress-bar-container">
                                <div className="progress-bar-track">
                                  <div className="progress-bar-fill" style={{ width: `${progressPercent}%` }} />
                                </div>
                                <span className="progress-percent">{progressPercent}%</span>
                              </div>
                              <div className="progress-step">{progressStep}</div>
                              {[1, 2, 3].map(i => (
                                <div key={i} className="concept-card skeleton">
                                  <div className="skeleton-line" style={{ width: '60%' }}></div>
                                </div>
                              ))}
                            </div>
                          ) : (
                            notes.key_concepts.map((concept, index) => (
                              <div key={index} className="concept-card">
                                <button 
                                  className="concept-header"
                                  onClick={() => toggleConcept(index)}
                                  aria-expanded={expandedConcepts.has(index)}
                                >
                                  <span className="concept-term">{concept.term}</span>
                                  {concept.timestamp && (
                                    <span 
                                      className="concept-timestamp clickable"
                                      onClick={(e) => {
                                        e.stopPropagation()
                                        if (concept.timestamp_seconds !== undefined) {
                                          seekToTime(concept.timestamp_seconds)
                                        }
                                      }}
                                      title="Jump to this point in video"
                                    >
                                      {concept.timestamp}
                                    </span>
                                  )}
                                  <span className={`expand-icon ${expandedConcepts.has(index) ? 'expanded' : ''}`}>▼</span>
                                </button>
                                {expandedConcepts.has(index) && (
                                  <div className="concept-details">
                                    <p className="concept-definition"><strong>Definition:</strong> {concept.definition}</p>
                                    <p className="concept-relevance"><strong>Relevance:</strong> {concept.relevance}</p>
                                  </div>
                                )}
                              </div>
                            ))
                          )}
                        </div>
                      )}
                    </div>

                    {/* Proceed to Phase 2 */}
                    {!phase2 && notes && (
                    <div className="phase-actions">
                      <button 
                        className="phase-next-button"
                        disabled={!notes || !videoId || loadingPhase === 2}
                        onClick={startPhase2}
                      >
                        {loadingPhase === 2 ? '⏳ Analyzing...' : 'Move to analysis phase →'}
                      </button>
                    </div>
                    )}

                    {/* Phase 2 Output */}
                    {phase2 && (
                      <div className="notes-section">
                        <button className="section-toggle" onClick={() => toggleSection('thesis')} aria-expanded={expandedSections.has('thesis')}>
                          <span>🧠 Thesis & Arguments ({phase2.argument_chains.length})</span>
                          <span className={`expand-icon ${expandedSections.has('thesis') ? 'expanded' : ''}`}>▼</span>
                        </button>
                        {expandedSections.has('thesis') && (
                          <div className="thesis-section">
                            <div className="thesis-card">
                              <button 
                                className="thesis-header"
                                onClick={() => toggleSection('main-thesis')}
                                aria-expanded={expandedSections.has('main-thesis')}
                              >
                                <span className="thesis-title">Main Thesis</span>
                                <span className={`expand-icon ${expandedSections.has('main-thesis') ? 'expanded' : ''}`}>▼</span>
                              </button>
                              {expandedSections.has('main-thesis') && (
                                <div className="thesis-details">
                                  <p>{phase2.main_thesis}</p>
                                </div>
                              )}
                            </div>
                            <div className="arguments-list">
                              {phase2.argument_chains.map((arg, idx) => (
                                <div key={idx} className="argument-card">
                                  <button 
                                    className="argument-header"
                                    onClick={() => toggleArgument(idx)}
                                    aria-expanded={expandedArguments.has(idx)}
                                  >
                                    <span className="argument-title">{arg.title}</span>
                                    <span className={`expand-icon ${expandedArguments.has(idx) ? 'expanded' : ''}`}>▼</span>
                                  </button>
                                  {expandedArguments.has(idx) && (
                                    <div className="argument-details">
                                      <p><strong>Premise:</strong> {arg.premise}</p>
                                      <p><strong>Reasoning Steps:</strong></p>
                                      <ul>
                                        {arg.reasoning_steps.map((step, i) => (
                                          <li key={i}>{step}</li>
                                        ))}
                                      </ul>
                                      <p><strong>Conclusion:</strong> {arg.conclusion}</p>
                                      {arg.implications && (
                                        <p><strong>Implications:</strong> {arg.implications}</p>
                                      )}
                                    </div>
                                  )}
                                </div>
                              ))}
                            </div>
                          </div>
                        )}
                      </div>
                    )}

                    {/* Proceed to Phase 3 */}
                    {phase2 && !phase3 && (
                      <div className="phase-actions">
                        <button 
                          className="phase-next-button"
                          disabled={!notes || loadingPhase === 3}
                          onClick={startPhase3}
                        >
                          {loadingPhase === 3 ? '⏳ Finding connections...' : 'Find connections between concepts →'}
                        </button>
                      </div>
                    )}

                    {/* Phase 3 Output */}
                    {phase3 && (
                      <div className="notes-section">
                        <button className="section-toggle" onClick={() => toggleSection('connections')} aria-expanded={expandedSections.has('connections')}>
                          <span>🔗 Connections ({phase3.connections.length})</span>
                          <span className={`expand-icon ${expandedSections.has('connections') ? 'expanded' : ''}`}>▼</span>
                        </button>
                        {expandedSections.has('connections') && (
                          <div className="connections-section">
                            <div className="synthesis-card">
                              <button className="synthesis-header" onClick={() => toggleSection('synthesis')} aria-expanded={expandedSections.has('synthesis')}>
                                <span className="synthesis-title">Synthesis</span>
                                <span className={`expand-icon ${expandedSections.has('synthesis') ? 'expanded' : ''}`}>▼</span>
                              </button>
                              {expandedSections.has('synthesis') && (
                                <div className="synthesis-details">
                                  <p>{phase3.synthesis}</p>
                                </div>
                              )}
                            </div>
                            <div className="connections-list">
                              {phase3.connections.map((conn, idx) => (
                                <div key={idx} className="connection-card">
                                  <button 
                                    className="connection-header"
                                    onClick={() => toggleConnection(idx)}
                                    aria-expanded={expandedConnections.has(idx)}
                                  >
                                    <span className="connection-title">{conn.concept_a} ↔ {conn.concept_b}</span>
                                    <span className={`expand-icon ${expandedConnections.has(idx) ? 'expanded' : ''}`}>▼</span>
                                  </button>
                                  {expandedConnections.has(idx) && (
                                    <div className="connection-details">
                                      <p><strong>Relationship:</strong> {conn.relationship}</p>
                                      <p><strong>Significance:</strong> {conn.significance}</p>
                                    </div>
                                  )}
                                </div>
                              ))}
                            </div>
                          </div>
                        )}
                      </div>
                    )}

                    {/* Proceed to Phase 4 */}
                    {phase3 && !phase4 && (
                      <div className="phase-actions">
                        <button 
                          className="phase-next-button"
                          disabled={!phase2 || loadingPhase === 4}
                          onClick={startPhase4}
                        >
                          {loadingPhase === 4 ? '⏳ Verifying claims...' : 'Verify claims →'}
                        </button>
                      </div>
                    )}

                    {/* Phase 4 Output */}
                    {phase4 && (
                      <div className="notes-section">
                        <button className="section-toggle" onClick={() => toggleSection('claims')} aria-expanded={expandedSections.has('claims')}>
                          <span>🔍 Claim Verification ({phase4.verified_claims.length})</span>
                          <span className={`expand-icon ${expandedSections.has('claims') ? 'expanded' : ''}`}>▼</span>
                        </button>
                        {expandedSections.has('claims') && (
                          <div className="claims-section">
                            <div className="credibility-card">
                              <div className="credibility-header">
                                <span className="credibility-label">Overall Credibility:</span>
                                <span className={`credibility-badge credibility-${phase4.overall_credibility.toLowerCase()}`}>
                                  {phase4.overall_credibility}
                                </span>
                              </div>
                              <p className="credibility-summary">{phase4.summary}</p>
                              {phase4.cautions && phase4.cautions.length > 0 && (
                                <div className="cautions-list">
                                  <strong>⚠️ Cautions:</strong>
                                  <ul>
                                    {phase4.cautions.map((caution, idx) => (
                                      <li key={idx}>{caution}</li>
                                    ))}
                                  </ul>
                                </div>
                              )}
                            </div>
                            <div className="claims-list">
                              {phase4.verified_claims.map((claim, idx) => (
                                <div key={idx} className="claim-card">
                                  <button 
                                    className="claim-header"
                                    onClick={() => toggleClaim(idx)}
                                    aria-expanded={expandedClaims.has(idx)}
                                  >
                                    <span className={`verdict-badge verdict-${claim.verdict.toLowerCase().replace('_', '-')}`}>
                                      {claim.verdict === 'supported' ? '✓' : claim.verdict === 'refuted' ? '✗' : claim.verdict === 'partially_true' ? '◐' : '?'}
                                    </span>
                                    <span className="claim-text">{claim.claim}</span>
                                    <span className={`expand-icon ${expandedClaims.has(idx) ? 'expanded' : ''}`}>▼</span>
                                  </button>
                                  {expandedClaims.has(idx) && (
                                    <div className="claim-details">
                                      <p><strong>Type:</strong> <span className="claim-type">{claim.claim_type}</span></p>
                                      <p><strong>Verdict:</strong> <span className={`verdict-text verdict-${claim.verdict.toLowerCase().replace('_', '-')}`}>{claim.verdict.replace('_', ' ')}</span></p>
                                      <p><strong>Reasoning:</strong> {claim.reasoning}</p>
                                      {claim.evidence && (
                                        <p><strong>Evidence:</strong> {claim.evidence}</p>
                                      )}
                                    </div>
                                  )}
                                </div>
                              ))}
                            </div>
                          </div>
                        )}
                      </div>
                    )}

                    {/* Proceed to Phase 5 */}
                    {phase4 && !phase5 && (
                      <div className="phase-actions">
                        <button 
                          className="phase-next-button"
                          disabled={!notes || loadingPhase === 5}
                          onClick={startPhase5}
                        >
                          {loadingPhase === 5 ? '⏳ Generating quiz...' : 'Test your understanding →'}
                        </button>
                      </div>
                    )}

                    {/* Phase 5 Output - Quiz */}
                    {phase5 && (
                      <div className="notes-section">
                        <button className="section-toggle" onClick={() => toggleSection('quiz')} aria-expanded={expandedSections.has('quiz')}>
                          <span>📝 Comprehension Quiz ({phase5.questions.length} questions)</span>
                          <span className={`expand-icon ${expandedSections.has('quiz') ? 'expanded' : ''}`}>▼</span>
                        </button>
                        {expandedSections.has('quiz') && (
                          <div className="quiz-section">
                            <div className="quiz-header">
                              <p className="quiz-focus">{phase5.quiz_focus}</p>
                              {quizSubmitted && quizScore !== null && (
                                <div className={`quiz-score ${quizScore >= phase5.passing_score ? 'quiz-passed' : 'quiz-failed'}`}>
                                  <span className="score-value">{quizScore}%</span>
                                  <span className="score-label">
                                    {quizScore >= phase5.passing_score ? '✓ Passed!' : `Need ${phase5.passing_score}% to pass`}
                                  </span>
                                </div>
                              )}
                            </div>
                            <div className="questions-list">
                              {phase5.questions.map((q, qIdx) => {
                                const userAnswer = quizAnswers.get(qIdx)
                                const isCorrect = userAnswer === q.correct_answer
                                const showResult = quizSubmitted
                                
                                return (
                                  <div key={qIdx} className={`question-card ${showResult ? (isCorrect ? 'correct' : 'incorrect') : ''}`}>
                                    <div className="question-header">
                                      <span className={`difficulty-badge difficulty-${q.difficulty}`}>{q.difficulty}</span>
                                      <span className="question-number">Q{qIdx + 1}</span>
                                      {q.related_concept && (
                                        <span className="related-concept">{q.related_concept}</span>
                                      )}
                                    </div>
                                    <p className="question-text">{q.question}</p>
                                    <div className="options-list">
                                      {q.options.map((option, oIdx) => {
                                        const isSelected = userAnswer === oIdx
                                        const isCorrectOption = q.correct_answer === oIdx
                                        let optionClass = 'option-button'
                                        if (isSelected) optionClass += ' selected'
                                        if (showResult) {
                                          if (isCorrectOption) optionClass += ' correct-option'
                                          else if (isSelected && !isCorrect) optionClass += ' wrong-option'
                                        }
                                        
                                        return (
                                          <button
                                            key={oIdx}
                                            className={optionClass}
                                            onClick={() => handleQuizAnswer(qIdx, oIdx)}
                                            disabled={quizSubmitted}
                                          >
                                            <span className="option-letter">{String.fromCharCode(65 + oIdx)}</span>
                                            <span className="option-text">{option}</span>
                                            {showResult && isCorrectOption && <span className="option-indicator">✓</span>}
                                            {showResult && isSelected && !isCorrect && <span className="option-indicator">✗</span>}
                                          </button>
                                        )
                                      })}
                                    </div>
                                    {showResult && (
                                      <div className="explanation-box">
                                        <strong>Explanation:</strong> {q.explanation}
                                      </div>
                                    )}
                                  </div>
                                )
                              })}
                            </div>
                            <div className="quiz-actions">
                              {!quizSubmitted ? (
                                <button 
                                  className="submit-quiz-button"
                                  onClick={submitQuiz}
                                  disabled={quizAnswers.size < phase5.questions.length}
                                >
                                  {quizAnswers.size < phase5.questions.length 
                                    ? `Answer all questions (${quizAnswers.size}/${phase5.questions.length})`
                                    : 'Submit Quiz'}
                                </button>
                              ) : (
                                <button className="retake-quiz-button" onClick={retakeQuiz}>
                                  Retake Quiz
                                </button>
                              )}
                            </div>
                          </div>
                        )}
                      </div>
                    )}
                  </div>
                </div>
              )}
            </div>
          </section>
        )}
      </main>
    </div>
  )
}

export default App
