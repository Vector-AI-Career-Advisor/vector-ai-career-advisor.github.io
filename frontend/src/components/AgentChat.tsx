import { useState, useRef, useEffect } from 'react'
import { Job } from '../api/jobs'
import { uploadResume, getMyResume } from '../api/resumes'
import api from '../api/client'
import './AgentChat.css'

// ─── Types ──────────────────────────────────────────────────────────────────

type Role = 'user' | 'agent' | 'system'

interface Message {
  id: string
  role: Role
  text: string
  timestamp: Date
}

interface Props {
  selectedJob: Job | null
  jobs?: Job[]
}

async function callAgent(
  message: string,
  selectedJob: Job | null,
  history: Message[]
): Promise<string> {
  const { data } = await api.post('/agent/chat', {
    message,
    job_id: selectedJob?.id ?? null,
    history: history
      .filter(m => m.role === 'user' || m.role === 'agent')
      .map(m => ({ role: m.role, text: m.text })),
  })
  return data.reply
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

  // When a new job is selected, add a context message
  useEffect(() => {
    if (!selectedJob) return
    setMessages(prev => {
      const alreadyNotified = prev.some(
        m => m.role === 'agent' && m.text.includes(selectedJob.id)
      )
      if (alreadyNotified) return prev
      return [
        ...prev,
        {
          id: crypto.randomUUID(),
          role: 'agent',
          text: `I noticed you opened **${selectedJob.title}** at ${selectedJob.company}. Ask me anything about it!`,
          timestamp: new Date(),
        },
      ]
    })
  }, [selectedJob])

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
    setError(null)

    try {
      const reply = await callAgent(trimmed, selectedJob, messages)
      setMessages(prev => [
        ...prev,
        { id: crypto.randomUUID(), role: 'agent', text: reply, timestamp: new Date() },
      ])
    } catch {
      setError('Failed to reach the agent. Please try again.')
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

  return (
    <div className="agent-chat">
      {/* Header */}
      <div className="agent-header">
        <div className="agent-avatar">
          <svg width="16" height="16" viewBox="0 0 24 24" fill="none"
            stroke="currentColor" strokeWidth="2" strokeLinecap="round">
            <path d="M12 2a4 4 0 0 1 4 4v1h1a3 3 0 0 1 3 3v6a3 3 0 0 1-3 3H7a3 3 0 0 1-3-3V10a3 3 0 0 1 3-3h1V6a4 4 0 0 1 4-4z"/>
            <circle cx="9" cy="13" r="1" fill="currentColor"/>
            <circle cx="15" cy="13" r="1" fill="currentColor"/>
          </svg>
        </div>
        <div>
          <p className="agent-name">Career Agent</p>
          <p className="agent-status">{isTyping ? 'Typing…' : 'Online'}</p>
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
            <div className="agent-empty-icon">◈</div>
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
                ) : (
                  <div className={`bubble ${msg.role}`}>
                    <span
                      dangerouslySetInnerHTML={{
                        __html: msg.text
                          .replace(/&/g, '&amp;')
                          .replace(/</g, '&lt;')
                          .replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>'),
                      }}
                    />
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
                <div className="bubble agent typing-indicator">
                  <span /><span /><span />
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
