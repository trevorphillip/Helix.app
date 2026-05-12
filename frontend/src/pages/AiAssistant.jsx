import { useState, useEffect, useRef } from 'react'
import { chatWithAI } from '../api'

// ─── design tokens ────────────────────────────────────────────────────────────

const T = {
  bg:      '#020a06',
  surface: '#0a1f10',
  border:  'rgba(0, 255, 136, 0.12)',
  border2: 'rgba(0, 255, 136, 0.3)',
  deep:    '#051209',
  green:   '#00ff88',
  greenDk: '#004422',
  amber:   '#ffaa00',
  text:    '#c8f5d8',
  dim:     '#4a8a5a',
  muted:   '#1a4a2a',
  userBg:  '#0d2614',
}

// ─── starter message ──────────────────────────────────────────────────────────

const STARTER = {
  id:   0,
  role: 'ai',
  text: "Hello! I'm your CRISPR assistant. Run an analysis in the Sandbox and I'll have full context about your sequence, enzyme, and top guides. What would you like to know?",
  ts:   new Date(),
}

// ─── helpers ──────────────────────────────────────────────────────────────────

function fmtTime(date) {
  return date.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })
}

// ─── typing indicator ─────────────────────────────────────────────────────────

function TypingDots() {
  return (
    <div style={{ display: 'flex', alignItems: 'center', gap: 4, padding: '4px 0' }}>
      {[0, 1, 2].map(i => (
        <span
          key={i}
          style={{
            width: 6, height: 6, borderRadius: '50%',
            background: T.green,
            display: 'inline-block',
            animation: `helixPulse 1.2s ease-in-out ${i * 0.2}s infinite`,
          }}
        />
      ))}
    </div>
  )
}

// ─── avatar ───────────────────────────────────────────────────────────────────

function HelixAvatar() {
  return (
    <div style={{
      width: 28, height: 28, borderRadius: '50%',
      background: T.green,
      display: 'flex', alignItems: 'center', justifyContent: 'center',
      color: '#020a06', fontSize: 11, fontWeight: 700,
      flexShrink: 0, fontFamily: 'monospace',
      boxShadow: '0 0 8px rgba(0,255,136,0.4)',
    }}>
      H
    </div>
  )
}

// ─── message bubble ───────────────────────────────────────────────────────────

function MessageBubble({ msg }) {
  const isUser = msg.role === 'user'

  if (isUser) {
    return (
      <div style={{ display: 'flex', justifyContent: 'flex-end', marginBottom: 16 }}>
        <div style={{ maxWidth: '70%' }}>
          <div style={{
            background: T.userBg,
            border: `1px solid ${T.border2}`,
            borderRadius: '10px 10px 2px 10px',
            padding: '10px 14px',
            color: T.text,
            fontSize: 13,
            lineHeight: 1.55,
            whiteSpace: 'pre-wrap',
            wordBreak: 'break-word',
            fontFamily: 'monospace',
          }}>
            {msg.text}
          </div>
          <div style={{ textAlign: 'right', marginTop: 4, fontSize: 9, color: T.muted, fontFamily: 'monospace' }}>
            {fmtTime(msg.ts)}
          </div>
        </div>
      </div>
    )
  }

  return (
    <div style={{ display: 'flex', alignItems: 'flex-start', gap: 10, marginBottom: 16 }}>
      <HelixAvatar />
      <div style={{ maxWidth: '70%' }}>
        <div style={{
          background: T.surface,
          border: `1px solid ${T.border}`,
          borderRadius: '2px 10px 10px 10px',
          padding: '10px 14px',
          color: T.text,
          fontSize: 13,
          lineHeight: 1.55,
          whiteSpace: 'pre-wrap',
          wordBreak: 'break-word',
          fontFamily: 'monospace',
        }}>
          {msg.loading ? <TypingDots /> : msg.text}
        </div>
        {!msg.loading && (
          <div style={{ marginTop: 4, fontSize: 9, color: T.muted, fontFamily: 'monospace' }}>
            {fmtTime(msg.ts)}
          </div>
        )}
      </div>
    </div>
  )
}

// ─── main page ────────────────────────────────────────────────────────────────

export default function AiAssistant({ context = {} }) {
  const [messages, setMessages] = useState([STARTER])
  const [input, setInput]       = useState('')
  const [loading, setLoading]   = useState(false)
  const bottomRef               = useRef(null)
  const inputRef                = useRef(null)

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages])

  async function handleSend() {
    const text = input.trim()
    if (!text || loading) return

    const userMsg = { id: Date.now(), role: 'user', text, ts: new Date() }
    const loadingMsg = { id: Date.now() + 1, role: 'ai', loading: true, ts: new Date() }

    setMessages(prev => [...prev, userMsg, loadingMsg])
    setInput('')
    setLoading(true)

    try {
      const data = await chatWithAI(text, context)
      const reply = data.reply ?? data.error ?? 'No response received.'
      setMessages(prev => prev.map(m =>
        m.id === loadingMsg.id ? { ...m, loading: false, text: reply } : m
      ))
    } catch (err) {
      const errText = err?.response?.data?.error ?? err.message ?? 'Request failed.'
      setMessages(prev => prev.map(m =>
        m.id === loadingMsg.id ? { ...m, loading: false, text: `Error: ${errText}` } : m
      ))
    } finally {
      setLoading(false)
      inputRef.current?.focus()
    }
  }

  function handleKeyDown(e) {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault()
      handleSend()
    }
  }

  return (
    <>
      <style>{`
        @keyframes helixPulse {
          0%, 80%, 100% { opacity: 0.2; transform: scale(0.8); }
          40%            { opacity: 1;   transform: scale(1);   }
        }
      `}</style>

      <div style={{
        display: 'flex', flexDirection: 'column',
        height: 'calc(100vh - 44px)',
        paddingTop: 44,
        background: T.bg,
      }}>

        {/* ── top bar ── */}
        <div style={{
          display: 'flex', alignItems: 'center', gap: 10,
          padding: '14px 20px',
          borderBottom: `1px solid ${T.border}`,
          background: 'rgba(2,10,6,0.95)',
          backdropFilter: 'blur(12px)',
          flexShrink: 0,
        }}>
          <div style={{
            width: 7, height: 7, borderRadius: '50%',
            background: T.green,
            boxShadow: `0 0 8px ${T.green}`,
          }} />
          <span style={{ color: T.green, fontSize: 13, fontWeight: 700, fontFamily: 'monospace', letterSpacing: '1px' }}>
            HELIX AI
          </span>
          <span style={{ color: T.muted, fontSize: 11, fontFamily: 'monospace' }}>
            CRISPR &amp; genomics assistant
          </span>
        </div>

        {/* ── message history ── */}
        <div style={{
          flex: 1,
          overflowY: 'auto',
          padding: '20px 20px 8px',
          display: 'flex', flexDirection: 'column', justifyContent: 'flex-end',
        }}>
          <div>
            {messages.map(msg => <MessageBubble key={msg.id} msg={msg} />)}
            <div ref={bottomRef} />
          </div>
        </div>

        {/* ── input bar ── */}
        <div style={{
          display: 'flex', alignItems: 'flex-end', gap: 10,
          padding: '12px 20px',
          borderTop: `1px solid ${T.border}`,
          background: 'rgba(2,10,6,0.95)',
          flexShrink: 0,
        }}>
          <textarea
            ref={inputRef}
            value={input}
            onChange={e => setInput(e.target.value)}
            onKeyDown={handleKeyDown}
            placeholder="Ask about your gRNAs, off-targets, sequence…"
            rows={1}
            style={{
              flex: 1,
              background: T.deep,
              border: `1px solid ${T.border}`,
              borderRadius: 4,
              padding: '8px 12px',
              fontFamily: 'monospace',
              fontSize: 12,
              color: T.green,
              outline: 'none',
              resize: 'none',
              lineHeight: 1.5,
              maxHeight: 120,
              overflowY: 'auto',
            }}
            onInput={e => {
              e.target.style.height = 'auto'
              e.target.style.height = Math.min(e.target.scrollHeight, 120) + 'px'
            }}
          />
          <button
            onClick={handleSend}
            disabled={loading || !input.trim()}
            style={{
              padding: '8px 18px',
              borderRadius: 4,
              background: loading || !input.trim() ? T.greenDk : T.green,
              color: '#020a06',
              fontWeight: 700,
              fontSize: 12,
              fontFamily: 'monospace',
              border: 'none',
              cursor: loading || !input.trim() ? 'not-allowed' : 'pointer',
              opacity: loading || !input.trim() ? 0.5 : 1,
              whiteSpace: 'nowrap',
              flexShrink: 0,
              transition: 'opacity 0.15s',
              letterSpacing: '0.5px',
            }}
          >
            Send
          </button>
        </div>
      </div>
    </>
  )
}
