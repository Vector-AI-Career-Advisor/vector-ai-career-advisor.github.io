import { useState, useRef, useEffect } from 'react'
import { Job } from '../api/jobs'
import { uploadResume, getMyResume } from '../api/resumes'
import './AgentChat.css'

// ─── Simple markdown renderer (no external dependency) ───────────────────────
function SimpleMarkdown({ children }: { children: string }) {
  const html = children
    .replace(/\*\*(.+?)\*\*/g, '<strong>$1</strong>')
    .replace(/\*(.+?)\*/g, '<em>$1</em>')
    .replace(/`([^`]+)`/g, '<code>$1</code>')
    .replace(/\[([^\]]+)\]\((https?:\/\/[^\)]+)\)/g, '<a href="$2" target="_blank" rel="noopener noreferrer">$1</a>')
    .replace(/^### (.+)$/gm, '<h3>$1</h3>')
    .replace(/^## (.+)$/gm, '<h2>$1</h2>')
    .replace(/^# (.+)$/gm, '<h1>$1</h1>')
    .replace(/^\d+\.\s+(.+)$/gm, '<li>$1</li>')
    .replace(/^[-*]\s+(.+)$/gm, '<li>$1</li>')
    .replace(/(<li>[\s\S]+?<\/li>)/g, '<ul>$1</ul>')
    .replace(/\n/g, '<br/>')
  return <span dangerouslySetInnerHTML={{ __html: html }} />
}

// ─── Types ──────────────────────────────────────────────────────────────────

type Role = 'user' | 'agent' | 'system'

interface AgentStep {
  name: string
  description: string
}

interface Message {
  id: string
  role: Role
  text: string
  timestamp: Date
  agentsUsed?: AgentStep[]
}

const AGENT_LABELS: Record<string, string> = {
  db_agent:          'Job Search Agent',
  resume_agent:      'Resume Agent',
  job_advisor_agent: 'Career Advisor Agent',
  interview_agent:   'Interview Prep Agent',
}
const agentLabel = (name: string) => AGENT_LABELS[name] ?? name
const formatDesc = (s: string) => s ? s.charAt(0).toUpperCase() + s.slice(1) + '...' : ''

interface Props {
  selectedJob: Job | null
  jobs?: Job[]
}

async function callAgent(
  message: string,
  selectedJob: Job | null,
  history: Message[],
  onPlanning: (agents: AgentStep[]) => void,
): Promise<{ reply: string; agentsUsed: AgentStep[] }> {
  const token = localStorage.getItem('token')
  const res = await fetch('/agents/chat', {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      'Accept': 'text/event-stream',
      ...(token ? { Authorization: `Bearer ${token}` } : {}),
    },
    body: JSON.stringify({
      message,
      job_id: selectedJob?.id ?? null,
      history: history
        .filter(m => m.role === 'user' || m.role === 'agent')
        .map(m => ({ role: m.role === 'agent' ? 'agents' : 'user', text: m.text })),
    }),
  })

  if (!res.ok) {
    if (res.status === 401) {
      localStorage.removeItem('token')
      window.location.href = '/login'
    }
    throw new Error(`HTTP ${res.status}`)
  }

  const reader = res.body!.getReader()
  const decoder = new TextDecoder()
  let buffer = ''
  let reply = ''
  let agentsUsed: AgentStep[] = []

  while (true) {
    const { done, value } = await reader.read()
    if (done) break

    buffer += decoder.decode(value, { stream: true })
    const lines = buffer.split('\n')
    buffer = lines.pop() ?? ''

    for (const line of lines) {
      if (!line.startsWith('data: ')) continue
      const raw = line.slice(6).trim()
      if (!raw) continue
      try {
        const event = JSON.parse(raw)
        if (event.type === 'planning') {
          onPlanning(event.agents)
        } else if (event.type === 'reply') {
          reply = event.reply
          agentsUsed = event.agents_used ?? []
        } else if (event.type === 'error') {
          throw new Error(event.detail ?? 'Agent error')
        }
      } catch (e) {
        if (e instanceof SyntaxError) continue
        throw e
      }
    }
  }

  return { reply, agentsUsed }
}

// ─── Suggested prompts ───────────────────────────────────────────────────────

const SUGGESTIONS = [
  'What skills do I need for this role?',
  'How should I tailor my CV?',
  'What salary should I expect?',
  'Find me similar jobs',
]

// ─── Component ───────────────────────────────────────────────────────────────

export default function AgentChat({ selectedJob, jobs = [] }: Props) {
  const [messages, setMessages]         = useState<Message[]>([])
  const [input, setInput]               = useState('')
  const [isTyping, setIsTyping]         = useState(false)
  const [pendingAgents, setPendingAgents] = useState<AgentStep[]>([])
  const [error, setError]               = useState<string | null>(null)
  const [resumeFilename, setResumeFilename] = useState<string | null>(null)
  const [uploadState, setUploadState]   = useState<'idle' | 'uploading' | 'error'>('idle')

  const bottomRef  = useRef<HTMLDivElement>(null)
  const inputRef   = useRef<HTMLTextAreaElement>(null)
  const fileInputRef = useRef<HTMLInputElement>(null)

  // Fetch existing resume on mount
  useEffect(() => {
    getMyResume()
      .then(info => { if (info) setResumeFilename(info.filename) })
      .catch(() => {})
  }, [])

  // Scroll to latest message
  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages, isTyping])


  const send = async (text: string) => {
    const trimmed = text.trim()
    if (!trimmed || isTyping) return

    const userMsg: Message = {
      id: crypto.randomUUID(),
      role: 'user',
      text: trimmed,
      timestamp: new Date(),
    }

    setMessages(prev => [...prev, userMsg])
    setInput('')
    setIsTyping(true)
    setPendingAgents([])
    setError(null)

    try {
      const { reply, agentsUsed } = await callAgent(
        trimmed,
        selectedJob,
        messages,
        (agents) => setPendingAgents(agents),
      )
      setPendingAgents([])
      setMessages(prev => [
        ...prev,
        { id: crypto.randomUUID(), role: 'agent', text: reply, timestamp: new Date(), agentsUsed },
      ])
    } catch {
      setPendingAgents([])
      setError('Failed to reach the agents. Please try again.')
    } finally {
      setIsTyping(false)
      inputRef.current?.focus()
    }
  }

  const handleKeyDown = (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault()
      send(input)
    }
  }

  const handleFileChange = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0]
    if (!file) return
    e.target.value = ''

    setUploadState('uploading')
    try {
      await uploadResume(file)
      setResumeFilename(file.name)
      setUploadState('idle')
      setMessages(prev => [
        ...prev,
        {
          id: crypto.randomUUID(),
          role: 'system',
          text: `Resume "${file.name}" uploaded successfully.`,
          timestamp: new Date(),
        },
      ])
    } catch {
      setUploadState('error')
      setTimeout(() => setUploadState('idle'), 3000)
    }
  }

  const isEmpty = messages.length === 0
  const lastAgentId = [...messages].reverse().find(m => m.role === 'agent')?.id

  return (
    <div className="agent-chat">
      {/* Header */}
      <div className="agent-header">
        <div>
          <p className="agent-name">Career Agent</p>
          <p className="agent-status">
            <span className={`status-dot ${error ? 'offline' : 'online'}`} />
            {isTyping ? 'Typing…' : error ? 'Offline' : 'Online'}
          </p>
        </div>

        <div className="agent-header-pills">
          {selectedJob && (
            <div className="agent-context-pill">
              <svg width="10" height="10" viewBox="0 0 24 24" fill="none"
                stroke="currentColor" strokeWidth="2.5" strokeLinecap="round">
                <rect x="2" y="7" width="20" height="14" rx="2"/>
                <path d="M16 7V5a2 2 0 0 0-2-2h-4a2 2 0 0 0-2 2v2"/>
              </svg>
              {selectedJob.title}
            </div>
          )}
        </div>
      </div>

      {/* Hidden file input */}
      <input
        ref={fileInputRef}
        type="file"
        accept=".pdf"
        style={{ display: 'none' }}
        onChange={handleFileChange}
      />

      {/* Message area */}
      <div className="agent-messages">
        {isEmpty ? (
          <div className="agent-empty">
            <div className="agent-empty-icon">
              <svg width="52" height="52" viewBox="0 0 24 24" fill="none"
                stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round">
                <path d="M12 2v3"/>
                <circle cx="12" cy="2" r="1" fill="currentColor" stroke="none"/>
                <rect x="2" y="5" width="20" height="14" rx="6"/>
                <circle cx="9" cy="11" r="1.8" fill="currentColor" stroke="none"/>
                <circle cx="15" cy="11" r="1.8" fill="currentColor" stroke="none"/>
                <path d="M9 15 Q12 17.5 15 15"/>
                <path d="M2 10H0"/><path d="M22 10h2"/>
              </svg>
            </div>
            <p className="agent-empty-title">Your career agent</p>
            <p className="agent-empty-sub">
              Ask about any job, get CV tips, salary ranges, or let the agent
              find the best match for your profile.
            </p>
            <div className="agent-suggestions">
              {SUGGESTIONS.map(s => (
                <button key={s} className="suggestion-chip" onClick={() => send(s)}>
                  {s}
                </button>
              ))}
            </div>
          </div>
        ) : (
          <>
            {messages.map(msg => (
              <div key={msg.id} className={`message-row ${msg.role}`}>
                {msg.role === 'system' ? (
                  <div className="system-message">{msg.text}</div>
                ) : msg.role === 'agent' ? (
                  <div className="message-content">
                    <div className="bubble agent">
                      <div className="msg-text">
                        <SimpleMarkdown>{msg.text}</SimpleMarkdown>
                      </div>
                      <span className="msg-time">
                        {msg.timestamp.toLocaleTimeString([], {
                          hour: '2-digit',
                          minute: '2-digit',
                        })}
                      </span>
                    </div>
                    {msg.id === lastAgentId && !isTyping && (
                      <div className="agent-bubble-avatar">
                        <svg width="14" height="14" viewBox="0 0 24 24" fill="none"
                          stroke="currentColor" strokeWidth="1.75" strokeLinecap="round" strokeLinejoin="round">
                          <path d="M12 2v3"/>
                          <circle cx="12" cy="2" r="1" fill="currentColor" stroke="none"/>
                          <rect x="2" y="5" width="20" height="14" rx="6"/>
                          <circle cx="9" cy="11" r="1.8" fill="currentColor" stroke="none"/>
                          <circle cx="15" cy="11" r="1.8" fill="currentColor" stroke="none"/>
                          <path d="M9 15 Q12 17.5 15 15"/>
                          <path d="M2 10H0"/><path d="M22 10h2"/>
                        </svg>
                      </div>
                    )}
                  </div>
                ) : (
                  <div className="bubble user">
                      <div className="msg-text">
                      <SimpleMarkdown>{msg.text}</SimpleMarkdown>
                    </div>
                    <span className="msg-time"></span>
                   
                    <span className="msg-time">
                      {msg.timestamp.toLocaleTimeString([], {
                        hour: '2-digit',
                        minute: '2-digit',
                      })}
                    </span>
                  </div>
                )}
              </div>
            ))}

            {isTyping && (
              <div className="message-row agent">
                <div className="message-content">
                  {pendingAgents.length > 0 && (
                    <div className="agent-chain">
                      {pendingAgents.map((a, i) => (
                        <div key={a.name} className="agent-chain-row">
                          <div className="agent-chain-track">
                            <div className="agent-chain-dot pending" />
                            {i < pendingAgents.length - 1 && <div className="agent-chain-line pending" />}
                          </div>
                          <div className="agent-chain-info">
                            <span className="agent-chain-label pending">{agentLabel(a.name)}</span>
                            {a.description && <span className="agent-chain-desc pending">{formatDesc(a.description)}</span>}
                          </div>
                        </div>
                      ))}
                    </div>
                  )}
                  <div className="bubble agent typing-indicator">
                    <span /><span /><span />
                  </div>
                </div>
              </div>
            )}

            {error && <div className="agent-error">{error}</div>}
          </>
        )}
        <div ref={bottomRef} />
      </div>

      {/* Input bar */}
      <div className="agent-input-bar">
        {/* Resume upload button */}
        <button
          className={`agent-icon-btn agent-resume-btn ${resumeFilename ? 'has-resume' : ''}`}
          onClick={() => fileInputRef.current?.click()}
          disabled={uploadState === 'uploading'}
          title={
            uploadState === 'uploading' ? 'Uploading…' :
            uploadState === 'error'     ? 'Upload failed — try again' :
            resumeFilename              ? `Resume: ${resumeFilename}\nClick to replace` :
                                          'Upload resume (PDF)'
          }
          aria-label="Upload resume"
        >
          {uploadState === 'uploading' ? (
            <span className="upload-spinner" />
          ) : (
            <svg width="15" height="15" viewBox="0 0 24 24" fill="none"
              stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
              <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/>
              <polyline points="14 2 14 8 20 8"/>
              <line x1="12" y1="18" x2="12" y2="12"/>
              <line x1="9" y1="15" x2="15" y2="15"/>
            </svg>
          )}
        </button>

        <textarea
          ref={inputRef}
          className="agent-input"
          placeholder="Ask about jobs, your CV, salary…"
          rows={1}
          value={input}
          onChange={e => setInput(e.target.value)}
          onKeyDown={handleKeyDown}
          disabled={isTyping}
        />
        <button
          className="agent-icon-btn agent-send"
          onClick={() => send(input)}
          disabled={!input.trim() || isTyping}
          aria-label="Send"
        >
          <svg width="15" height="15" viewBox="0 0 24 24" fill="none"
            stroke="currentColor" strokeWidth="2.5" strokeLinecap="round">
            <path d="M22 2L11 13M22 2L15 22l-4-9-9-4 20-7z"/>
          </svg>
        </button>
      </div>
    </div>
  )
}