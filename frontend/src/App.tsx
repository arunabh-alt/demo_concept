import { useEffect, useRef, useState, useTransition, type FormEvent } from 'react'

import {
  buildVoicePipelineUrl,
  executeAgent,
  getMe,
  signin,
  signup,
  type AgentExecutionResponse,
  type User,
} from './api'
import { startMicrophoneStreaming, type StopMicrophoneStream } from './voice'

type Mode = 'signin' | 'signup'
type VoiceStage = 'idle' | 'connecting' | 'listening' | 'transcribing' | 'executing' | 'ready' | 'error'

type VoicePipelineMessage =
  | { type: 'ready'; session_id: string; user_id: string; message: string }
  | { type: 'session_started'; session_id: string; sample_rate: number; language_code: string }
  | { type: 'transcript'; session_id: string; is_partial: boolean; text: string }
  | { type: 'transcript_complete'; session_id: string; transcript: string }
  | { type: 'pong'; session_id: string }
  | { type: 'error'; message: string }

const TOKEN_KEY = 'fullstack-auth-token'
const VOICE_SAMPLE_RATE = 16000

export default function App() {
  const [mode, setMode] = useState<Mode>('signup')
  const [fullName, setFullName] = useState('')
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [token, setToken] = useState<string | null>(() => localStorage.getItem(TOKEN_KEY))
  const [currentUser, setCurrentUser] = useState<User | null>(null)
  const [feedback, setFeedback] = useState('Create an account or sign in with an existing one.')
  const [isPending, startTransition] = useTransition()
  const [manualCommand, setManualCommand] = useState('')
  const [voiceStage, setVoiceStage] = useState<VoiceStage>('idle')
  const [liveTranscript, setLiveTranscript] = useState('')
  const [partialTranscript, setPartialTranscript] = useState('')
  const [executionResult, setExecutionResult] = useState<AgentExecutionResponse | null>(null)
  const [eventLog, setEventLog] = useState<string[]>(['Voice workspace ready.'])

  const socketRef = useRef<WebSocket | null>(null)
  const stopMicrophoneRef = useRef<StopMicrophoneStream | null>(null)

  function appendLog(message: string) {
    setEventLog((currentLog) => [`${new Date().toLocaleTimeString()}  ${message}`, ...currentLog].slice(0, 12))
  }

  useEffect(() => {
    if (!token) {
      setCurrentUser(null)
      return
    }

    let cancelled = false
    startTransition(() => {
      getMe(token)
        .then((user) => {
          if (!cancelled) {
            setCurrentUser(user)
            setFeedback('Authenticated against the FastAPI backend. Voice commands are ready when you are.')
          }
        })
        .catch((error: Error) => {
          if (!cancelled) {
            localStorage.removeItem(TOKEN_KEY)
            setToken(null)
            setFeedback(error.message)
          }
        })
    })

    return () => {
      cancelled = true
    }
  }, [token])

  useEffect(() => {
    return () => {
      void shutdownVoiceTransport(true)
    }
  }, [])

  async function shutdownVoiceTransport(closeSocket: boolean) {
    const stopMicrophone = stopMicrophoneRef.current
    stopMicrophoneRef.current = null
    if (stopMicrophone) {
      await stopMicrophone()
    }

    if (closeSocket && socketRef.current) {
      socketRef.current.close()
      socketRef.current = null
    }
  }

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    setFeedback('Submitting request...')

    try {
      const response =
        mode === 'signup'
          ? await signup(fullName.trim(), email.trim(), password)
          : await signin(email.trim(), password)

      localStorage.setItem(TOKEN_KEY, response.access_token)
      setToken(response.access_token)
      setCurrentUser(response.user)
      setPassword('')
      setFeedback(mode === 'signup' ? 'Account created. Your digital twin is ready.' : 'Signed in successfully.')
      appendLog(mode === 'signup' ? 'User account created.' : 'User signed in.')
    } catch (error) {
      const message = error instanceof Error ? error.message : 'Something went wrong'
      setFeedback(message)
      appendLog(`Authentication error: ${message}`)
    }
  }

  async function handleSignOut() {
    await shutdownVoiceTransport(true)
    localStorage.removeItem(TOKEN_KEY)
    setToken(null)
    setCurrentUser(null)
    setPassword('')
    setExecutionResult(null)
    setLiveTranscript('')
    setPartialTranscript('')
    setVoiceStage('idle')
    setFeedback('Signed out.')
    appendLog('Session cleared.')
  }

  async function runAgentCommand(message: string, source: 'voice' | 'manual') {
    if (!token || !currentUser?.primary_agent_id) {
      const missingContextMessage = 'Sign in first so the command can be routed through your primary digital twin.'
      setFeedback(missingContextMessage)
      appendLog(missingContextMessage)
      return
    }

    setVoiceStage('executing')
    setFeedback(source === 'voice' ? 'Running voice command through the digital twin.' : 'Running typed command through the digital twin.')

    try {
      const result = await executeAgent(token, {
        user_id: currentUser.id,
        agent_id: currentUser.primary_agent_id,
        message,
      })
      setExecutionResult(result)
      setVoiceStage('ready')
      setFeedback('Digital twin response ready.')
      appendLog(`Agent responded with intent '${result.intent}' in ${result.mode} mode.`)
    } catch (error) {
      const errorMessage = error instanceof Error ? error.message : 'Unable to execute agent command.'
      setVoiceStage('error')
      setFeedback(errorMessage)
      appendLog(`Agent execution error: ${errorMessage}`)
    }
  }

  async function handleManualSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    const trimmedCommand = manualCommand.trim()
    if (!trimmedCommand) {
      return
    }

    setLiveTranscript(trimmedCommand)
    setPartialTranscript('')
    appendLog(`Manual command submitted: ${trimmedCommand}`)
    await runAgentCommand(trimmedCommand, 'manual')
  }

  async function startVoiceCommand() {
    if (!token) {
      setFeedback('Sign in first to open the authenticated voice pipeline.')
      return
    }

    if (!currentUser?.primary_agent_id) {
      setFeedback('The signed-in user does not have a primary agent yet.')
      return
    }

    await shutdownVoiceTransport(true)
    setExecutionResult(null)
    setLiveTranscript('')
    setPartialTranscript('')
    setVoiceStage('connecting')
    setFeedback('Connecting to the voice pipeline.')
    appendLog('Opening voice websocket.')

    const socket = new WebSocket(buildVoicePipelineUrl(token))
    socketRef.current = socket

    socket.onopen = () => {
      appendLog('Voice websocket connected.')
    }

    socket.onmessage = async (event) => {
      const payload = JSON.parse(String(event.data)) as VoicePipelineMessage

      if (payload.type === 'ready') {
        appendLog('Backend voice pipeline is ready.')
        socket.send(JSON.stringify({ type: 'start', sample_rate: VOICE_SAMPLE_RATE, language_code: 'en-US' }))
        return
      }

      if (payload.type === 'session_started') {
        appendLog('Amazon Transcribe session started.')
        try {
          stopMicrophoneRef.current = await startMicrophoneStreaming({
            socket,
            targetSampleRate: VOICE_SAMPLE_RATE,
          })
          setVoiceStage('listening')
          setFeedback('Listening. Speak your command, then stop the recording.')
        } catch (error) {
          const errorMessage = error instanceof Error ? error.message : 'Unable to access the microphone.'
          setVoiceStage('error')
          setFeedback(errorMessage)
          appendLog(`Microphone error: ${errorMessage}`)
          socket.close()
        }
        return
      }

      if (payload.type === 'transcript') {
        if (payload.is_partial) {
          setPartialTranscript(payload.text)
        } else {
          setLiveTranscript((currentTranscript) => (currentTranscript ? `${currentTranscript} ${payload.text}` : payload.text))
          setPartialTranscript('')
        }
        setVoiceStage('transcribing')
        return
      }

      if (payload.type === 'transcript_complete') {
        setLiveTranscript(payload.transcript)
        setPartialTranscript('')
        appendLog(`Transcript complete: ${payload.transcript}`)
        await shutdownVoiceTransport(false)
        socket.close()
        socketRef.current = null
        await runAgentCommand(payload.transcript, 'voice')
        return
      }

      if (payload.type === 'error') {
        setVoiceStage('error')
        setFeedback(payload.message)
        appendLog(`Voice pipeline error: ${payload.message}`)
        await shutdownVoiceTransport(true)
      }
    }

    socket.onclose = () => {
      socketRef.current = null
      appendLog('Voice websocket closed.')
    }

    socket.onerror = () => {
      setVoiceStage('error')
      setFeedback('Voice websocket failed. Check the backend and AWS configuration.')
      appendLog('Voice websocket transport error.')
    }
  }

  async function stopVoiceCommand() {
    if (!socketRef.current) {
      return
    }

    await shutdownVoiceTransport(false)
    setVoiceStage('transcribing')
    setFeedback('Microphone stopped. Waiting for the final transcript.')
    appendLog('Stop requested. Waiting for final transcript.')
    socketRef.current.send(JSON.stringify({ type: 'stop' }))
  }

  const isAuthenticated = Boolean(currentUser)
  const primaryAgentId = currentUser?.primary_agent_id ?? null
  const liveTranscriptPreview = partialTranscript ? `${liveTranscript} ${partialTranscript}`.trim() : liveTranscript

  const pipelineSteps = [
    { label: 'Session', active: isAuthenticated },
    { label: 'Mic', active: voiceStage === 'listening' || voiceStage === 'transcribing' || voiceStage === 'executing' || voiceStage === 'ready' },
    { label: 'Transcribe', active: voiceStage === 'transcribing' || voiceStage === 'executing' || voiceStage === 'ready' },
    { label: 'Agent', active: voiceStage === 'executing' || voiceStage === 'ready' },
    { label: 'Response', active: executionResult !== null },
  ]

  return (
    <div className="shell">
      <section className="hero-card">
        <div className="hero-copy">
          <p className="eyebrow">Digital Twin Voice Console</p>
          <h1>Speak a request, stream it through Amazon Transcribe, and route it into your agent.</h1>
          <p className="summary">
            The frontend now behaves like an operator console: authenticate, open the microphone pipeline, watch the transcript land in real time, and inspect the structured digital-twin response beside it.
          </p>
        </div>

        <div className="status-cluster">
          <div className="status-pill status-voice">Voice stage: <strong>{voiceStage}</strong></div>
          <div className="status-pill status-agent">Primary agent: <strong>{primaryAgentId ?? 'not available'}</strong></div>
        </div>
      </section>

      <section className="workspace-grid">
        <article className="panel auth-panel">
          <div className="panel-header">
            <div>
              <p className="panel-kicker">Access</p>
              <h2>{isAuthenticated ? 'Authenticated session' : mode === 'signup' ? 'Create account' : 'Sign in'}</h2>
            </div>
            {!isAuthenticated ? (
              <div className="toggle-row" role="tablist" aria-label="Authentication mode">
                <button className={mode === 'signup' ? 'active' : ''} onClick={() => setMode('signup')} type="button">
                  Sign up
                </button>
                <button className={mode === 'signin' ? 'active' : ''} onClick={() => setMode('signin')} type="button">
                  Sign in
                </button>
              </div>
            ) : null}
          </div>

          {isAuthenticated ? (
            <div className="profile-card">
              <strong>{currentUser?.full_name}</strong>
              <span>{currentUser?.email}</span>
              <span>Joined {currentUser ? new Date(currentUser.created_at).toLocaleString() : ''}</span>
              <span>Primary agent ID: {primaryAgentId ?? 'missing'}</span>
              <button className="secondary" onClick={() => void handleSignOut()} type="button">
                Sign out
              </button>
            </div>
          ) : (
            <form className="auth-form" onSubmit={handleSubmit}>
              {mode === 'signup' ? (
                <label>
                  Full name
                  <input value={fullName} onChange={(event) => setFullName(event.target.value)} required minLength={2} />
                </label>
              ) : null}

              <label>
                Email
                <input value={email} onChange={(event) => setEmail(event.target.value)} required type="email" />
              </label>

              <label>
                Password
                <input value={password} onChange={(event) => setPassword(event.target.value)} required minLength={8} type="password" />
              </label>

              <button className="submit" disabled={isPending} type="submit">
                {isPending ? 'Working...' : mode === 'signup' ? 'Create account' : 'Sign in'}
              </button>
            </form>
          )}

          <div className="message-box">
            <h3>Latest message</h3>
            <p>{feedback}</p>
          </div>
        </article>

        <article className="panel voice-panel">
          <div className="panel-header">
            <div>
              <p className="panel-kicker">Voice pipeline</p>
              <h2>Microphone to transcript</h2>
            </div>
            <div className="voice-actions">
              <button className="submit" disabled={!isAuthenticated || voiceStage === 'connecting' || voiceStage === 'listening' || voiceStage === 'transcribing'} onClick={() => void startVoiceCommand()} type="button">
                Start voice
              </button>
              <button className="secondary" disabled={voiceStage !== 'listening' && voiceStage !== 'transcribing'} onClick={() => void stopVoiceCommand()} type="button">
                Stop
              </button>
            </div>
          </div>

          <div className="pipeline-row">
            {pipelineSteps.map((step) => (
              <div className={`pipeline-step${step.active ? ' active' : ''}`} key={step.label}>
                <span className="pipeline-dot" />
                <span>{step.label}</span>
              </div>
            ))}
          </div>

          <div className="transcript-card">
            <p className="panel-kicker">Live transcript</p>
            <pre>{liveTranscriptPreview || 'No transcript yet. Start the microphone or use the fallback command input below.'}</pre>
          </div>

          <form className="manual-command" onSubmit={handleManualSubmit}>
            <label>
              Typed fallback command
              <textarea
                rows={4}
                value={manualCommand}
                onChange={(event) => setManualCommand(event.target.value)}
                placeholder="Transfer 500 Pounds to Alice"
              />
            </label>
            <button className="submit" disabled={!isAuthenticated} type="submit">
              Run typed command
            </button>
          </form>
        </article>

        <article className="panel response-panel">
          <div className="panel-header">
            <div>
              <p className="panel-kicker">Digital twin response</p>
              <h2>Intent, mode, and action output</h2>
            </div>
          </div>

          {executionResult ? (
            <div className="response-grid">
              <div className="response-card">
                <h3>Intent</h3>
                <p>{executionResult.intent}</p>
              </div>
              <div className="response-card">
                <h3>Execution mode</h3>
                <p>{executionResult.mode}</p>
              </div>
              <div className="response-card">
                <h3>Structured action</h3>
                <pre>{JSON.stringify(executionResult.structured_action, null, 2)}</pre>
              </div>
              <div className="response-card">
                <h3>Response text</h3>
                <p>{executionResult.response_text}</p>
              </div>
              <div className="response-card">
                <h3>Memory hits</h3>
                <p>{executionResult.memory_hits.length > 0 ? executionResult.memory_hits.join(', ') : 'No prior memory matched.'}</p>
              </div>
              <div className="response-card">
                <h3>Learning update</h3>
                <pre>{JSON.stringify(executionResult.learning_update, null, 2)}</pre>
              </div>
            </div>
          ) : (
            <p className="placeholder">No agent response yet. Record a voice command or submit a typed fallback command.</p>
          )}
        </article>

        <article className="panel log-panel">
          <div className="panel-header">
            <div>
              <p className="panel-kicker">Operations</p>
              <h2>Event log</h2>
            </div>
          </div>
          <pre className="event-log">{eventLog.join('\n')}</pre>
        </article>
      </section>
    </div>
  )
}
