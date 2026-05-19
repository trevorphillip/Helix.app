import { useState, useEffect } from 'react'
import { useHelixStore } from '../store.jsx'
import api from '../api'

const T = {
  bg:      '#020a06',
  surface: '#0a1f10',
  border:  'rgba(0, 255, 136, 0.12)',
  border2: 'rgba(0, 255, 136, 0.3)',
  deep:    '#051209',
  green:   '#00ff88',
  amber:   '#ffaa00',
  purple:  '#aa88ff',
  red:     '#ff2244',
  text:    '#c8f5d8',
  dim:     '#4a8a5a',
  muted:   '#1a4a2a',
  cyan:    '#00ccff',
}

// ─── Utility ──────────────────────────────────────────────────────────────────

function useHover() {
  const [h, setH] = useState(false)
  return [h, { onMouseEnter: () => setH(true), onMouseLeave: () => setH(false) }]
}

function CopyBtn({ text, style }) {
  const [copied, setCopied] = useState(false)
  function copy() {
    navigator.clipboard.writeText(text).catch(() => {})
    setCopied(true)
    setTimeout(() => setCopied(false), 1500)
  }
  return (
    <button
      onClick={copy}
      style={{
        padding: '2px 8px', borderRadius: 4, fontSize: 9, cursor: 'pointer',
        border: `1px solid ${T.border}`, background: 'transparent',
        color: copied ? T.green : T.dim, fontFamily: 'monospace',
        transition: 'color 0.15s', ...style,
      }}
      onMouseEnter={e => { e.currentTarget.style.borderColor = T.green }}
      onMouseLeave={e => { e.currentTarget.style.borderColor = T.border }}
    >
      {copied ? 'Copied!' : 'Copy'}
    </button>
  )
}

function MiniBar({ value, max = 1, color = T.green }) {
  return (
    <div style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
      <div style={{ width: 52, height: 3, borderRadius: 2, background: T.deep, overflow: 'hidden' }}>
        <div style={{ width: `${Math.min((value / max) * 100, 100)}%`, height: '100%', borderRadius: 2, background: color }} />
      </div>
      <span style={{ fontSize: 11, fontFamily: 'monospace', color }}>
        {Math.round(value * 100)}%
      </span>
    </div>
  )
}

// ─── Guide window visualization ───────────────────────────────────────────────

function GuideWindowViz({ guide }) {
  const { guide_sequence, editing_window, target_base_position, bystander_bases } = guide
  const [wStart, wEnd] = editing_window
  const bystanderSet = new Set(bystander_bases.map(b => b.position))

  return (
    <div style={{ marginTop: 8 }}>
      {/* position numbers */}
      <div style={{ display: 'flex', gap: 1, marginBottom: 2 }}>
        {Array.from({ length: 20 }, (_, i) => i + 1).map(pos => (
          <div key={pos} style={{
            width: 21, textAlign: 'center',
            fontSize: 7, color: T.muted, fontFamily: 'monospace',
          }}>
            {pos}
          </div>
        ))}
      </div>

      {/* base boxes */}
      <div style={{ display: 'flex', gap: 1 }}>
        {Array.from({ length: 20 }, (_, i) => i + 1).map(pos => {
          const base = guide_sequence[pos - 1] ?? '?'
          let bg, color, fw = 400
          if (pos === target_base_position) {
            bg = T.green; color = '#020a06'; fw = 700
          } else if (bystanderSet.has(pos)) {
            bg = T.amber; color = '#020a06'
          } else if (pos >= wStart && pos <= wEnd) {
            bg = '#0a2a14'; color = T.dim
          } else {
            bg = T.deep; color = T.muted
          }
          return (
            <div key={pos} style={{
              width: 21, height: 22, background: bg, color,
              fontWeight: fw, display: 'flex', alignItems: 'center',
              justifyContent: 'center', fontFamily: 'monospace',
              fontSize: 10, borderRadius: 2, flexShrink: 0,
            }}>
              {base}
            </div>
          )
        })}
      </div>

      {/* window bracket */}
      <div style={{ display: 'flex', marginTop: 2 }}>
        <div style={{ width: (wStart - 1) * 22, flexShrink: 0 }} />
        <div style={{
          width: (wEnd - wStart + 1) * 22 - 1,
          borderLeft: `1px solid ${T.muted}`,
          borderRight: `1px solid ${T.muted}`,
          borderBottom: `1px solid ${T.muted}`,
          textAlign: 'center',
          fontSize: 8, color: T.muted, fontFamily: 'monospace',
          paddingBottom: 2, lineHeight: 1.2,
        }}>
          ◄─ editing window ─►
        </div>
      </div>

      {/* legend */}
      <div style={{ display: 'flex', gap: 12, marginTop: 8, flexWrap: 'wrap' }}>
        {[
          { color: T.green, label: 'target (editable)' },
          { color: T.amber, label: 'bystander edit' },
          { color: T.dim,   label: 'window (inactive)' },
          { color: T.muted, label: 'outside window' },
        ].map(({ color, label }) => (
          <div key={label} style={{ display: 'flex', alignItems: 'center', gap: 5, fontSize: 9, color: T.muted, fontFamily: 'monospace' }}>
            <div style={{ width: 8, height: 8, borderRadius: 1, background: color, flexShrink: 0 }} />
            {label}
          </div>
        ))}
      </div>
    </div>
  )
}

// ─── CBE / ABE results table ──────────────────────────────────────────────────

function ResultsTable({ guides, expandedIdx, onToggle }) {
  if (!guides.length) return (
    <div style={{ padding: '48px 0', textAlign: 'center', color: T.muted, fontFamily: 'monospace', fontSize: 12 }}>
      No valid editing guides found at this position
    </div>
  )

  const thStyle = {
    padding: '7px 12px', color: T.muted, fontSize: 9,
    textTransform: 'uppercase', letterSpacing: '2px',
    fontWeight: 500, textAlign: 'left', fontFamily: 'monospace',
  }

  return (
    <div style={{ overflowX: 'auto' }}>
      <table style={{ width: '100%', borderCollapse: 'collapse' }}>
        <thead>
          <tr style={{ borderBottom: `1px solid ${T.border}` }}>
            <th style={thStyle}>Editor</th>
            <th style={thStyle}>Guide</th>
            <th style={thStyle}>Window</th>
            <th style={thStyle}>Target</th>
            <th style={thStyle}>Bystanders</th>
            <th style={thStyle}>Efficiency</th>
            <th style={thStyle}>Specificity</th>
          </tr>
        </thead>
        <tbody>
          {guides.map((g, i) => {
            const isCBE = g.editor_type === 'CBE'
            const bCount = g.bystander_bases.length
            const bColor = bCount === 0 ? T.green : bCount <= 2 ? T.amber : T.red
            const isExpanded = expandedIdx === i

            return (
              <>
                <tr
                  key={i}
                  onClick={() => onToggle(i)}
                  style={{
                    borderBottom: isExpanded ? 'none' : `1px solid ${T.border}`,
                    cursor: 'pointer',
                    background: isExpanded ? 'rgba(0,255,136,0.03)' : 'transparent',
                  }}
                  onMouseEnter={e => { if (!isExpanded) e.currentTarget.style.background = 'rgba(0,255,136,0.02)' }}
                  onMouseLeave={e => { if (!isExpanded) e.currentTarget.style.background = 'transparent' }}
                >
                  <td style={{ padding: '8px 12px' }}>
                    <span style={{
                      padding: '2px 8px', borderRadius: 4, fontSize: 10,
                      fontFamily: 'monospace', fontWeight: 600,
                      background: isCBE ? 'rgba(0,255,136,0.08)' : 'rgba(255,170,0,0.08)',
                      color: isCBE ? T.green : T.amber,
                      border: `1px solid ${isCBE ? 'rgba(0,255,136,0.2)' : 'rgba(255,170,0,0.2)'}`,
                    }}>
                      {g.editor}
                    </span>
                  </td>
                  <td style={{ padding: '8px 12px', fontFamily: 'monospace', color: T.text, fontSize: 11 }}>
                    {g.guide_sequence.slice(0, 17)}
                    <span style={{ color: T.amber }}>{g.guide_sequence.slice(17)}</span>
                    <span style={{ color: T.muted, marginLeft: 4 }}>{g.strand}</span>
                  </td>
                  <td style={{ padding: '8px 12px', fontFamily: 'monospace', color: T.dim, fontSize: 11 }}>
                    {g.editing_window[0]}–{g.editing_window[1]}
                  </td>
                  <td style={{ padding: '8px 12px', fontFamily: 'monospace', fontSize: 11, color: T.green, fontWeight: 600 }}>
                    {g.target_base} → {g.result_base}
                    <span style={{ color: T.muted, marginLeft: 6, fontSize: 9 }}>pos {g.target_base_position}</span>
                  </td>
                  <td style={{ padding: '8px 12px', fontFamily: 'monospace', fontSize: 11, color: bColor }}>
                    {bCount === 0 ? 'None' : `${bCount} base${bCount > 1 ? 's' : ''}`}
                  </td>
                  <td style={{ padding: '8px 12px' }}>
                    <MiniBar value={g.efficiency_estimate} color={T.green} />
                  </td>
                  <td style={{ padding: '8px 12px' }}>
                    <MiniBar value={g.specificity_score} color={T.cyan} />
                  </td>
                </tr>
                {isExpanded && (
                  <tr key={`exp-${i}`} style={{ borderBottom: `1px solid ${T.border}` }}>
                    <td colSpan={7} style={{ padding: '12px 16px 16px', background: 'rgba(0,255,136,0.02)' }}>
                      <GuideWindowViz guide={g} />
                      <div style={{ marginTop: 10, display: 'flex', gap: 16, fontSize: 10, color: T.muted, fontFamily: 'monospace' }}>
                        <span>Position: bp {g.position} ({g.strand})</span>
                        <span>PAM: <span style={{ color: T.amber }}>{g.pam}</span></span>
                        <span>Window seq: <span style={{ color: T.dim }}>{g.window_sequence}</span></span>
                        <CopyBtn text={g.guide_sequence} style={{ marginLeft: 4 }} />
                      </div>
                    </td>
                  </tr>
                )}
              </>
            )
          })}
        </tbody>
      </table>
    </div>
  )
}

// ─── CBE / ABE panel ──────────────────────────────────────────────────────────

function CbeAbePanel({ mode, sequence }) {
  const cbeEditors = ['BE3', 'BE4max', 'NG-CBE']
  const abeEditors = ['ABE7', 'ABE8e']
  const editors = mode === 'CBE' ? cbeEditors : abeEditors

  const [selectedEditor, setSelected]   = useState(editors[0])
  const [results, setResults]           = useState(null)
  const [loading, setLoading]           = useState(false)
  const [error, setError]               = useState(null)
  const [expandedIdx, setExpandedIdx]   = useState(null)
  const [btnH, btnEvents]               = useHover()

  useEffect(() => {
    setSelected(editors[0])
    setResults(null)
    setExpandedIdx(null)
  }, [mode])

  async function handleAnalyze() {
    if (!sequence.trim()) return
    setLoading(true); setError(null); setResults(null); setExpandedIdx(null)
    try {
      const editType  = mode === 'CBE' ? 'C_to_T' : 'A_to_G'
      const { data } = await api.post('/api/baseedit/analyze', {
        sequence,
        edit_type: editType,
        editor_type: selectedEditor === 'All' ? mode : selectedEditor,
      })
      setResults(data)
    } catch (err) {
      setError(err?.response?.data?.detail ?? err.message ?? 'Analysis failed')
    } finally {
      setLoading(false)
    }
  }

  function toggleRow(i) {
    setExpandedIdx(prev => prev === i ? null : i)
  }



  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 16 }}>
      {/* controls */}
      <div style={{
        background: 'rgba(2,10,6,0.98)', border: `1px solid ${T.border}`,
        borderRadius: 8, padding: '14px 18px',
        display: 'flex', flexWrap: 'wrap', alignItems: 'flex-end', gap: 16,
      }}>
        <div>
          <div style={{ fontSize: 9, color: T.muted, letterSpacing: '2px', fontFamily: 'monospace', marginBottom: 5 }}>
            EDITOR
          </div>
          <div style={{ display: 'flex', gap: 6 }}>
            {editors.map(ed => (
              <button key={ed} onClick={() => setSelected(ed)} style={{
                padding: '4px 12px', borderRadius: 12, fontSize: 10, cursor: 'pointer',
                fontFamily: 'monospace', fontWeight: selectedEditor === ed ? 700 : 400,
                background: selectedEditor === ed ? T.green : 'transparent',
                color: selectedEditor === ed ? '#020a06' : T.green,
                border: `1px solid ${selectedEditor === ed ? T.green : 'rgba(0,255,136,0.3)'}`,
                transition: 'all 0.15s',
              }}>
                {ed}
              </button>
            ))}
          </div>
        </div>

        <button
          onClick={handleAnalyze}
          disabled={loading || !sequence.trim()}
          {...btnEvents}
          style={{
            padding: '6px 18px', borderRadius: 6, fontSize: 11, cursor: 'pointer',
            fontFamily: 'monospace', fontWeight: 700, letterSpacing: '1px',
            background: loading ? 'rgba(0,255,136,0.08)' : btnH ? T.green : 'rgba(0,255,136,0.12)',
            color: btnH && !loading ? '#020a06' : T.green,
            border: `1px solid ${T.border2}`,
            opacity: !sequence.trim() ? 0.4 : 1,
            transition: 'all 0.15s',
          }}
        >
          {loading ? 'Scanning...' : 'Find editing guides'}
        </button>
      </div>

      {error && (
        <div style={{
          padding: '8px 14px', borderRadius: 6,
          background: 'rgba(255,34,68,0.08)', border: '1px solid rgba(255,34,68,0.3)',
          color: T.red, fontSize: 12, fontFamily: 'monospace',
        }}>
          {error}
        </div>
      )}

      {results && (
        <div style={{
          background: 'rgba(5,18,9,0.9)', border: `1px solid ${T.border}`,
          borderRadius: 8, overflow: 'hidden',
        }}>
          <div style={{
            padding: '10px 16px', borderBottom: `1px solid ${T.border}`,
            display: 'flex', alignItems: 'center', justifyContent: 'space-between',
          }}>
            <span style={{ fontSize: 9, color: T.muted, fontFamily: 'monospace', letterSpacing: '2px', textTransform: 'uppercase' }}>
              // EDITING GUIDES — {results.valid_found} valid / {results.total_scanned} PAM sites scanned
            </span>
            <span style={{ fontSize: 10, color: T.dim, fontFamily: 'monospace' }}>
              {results.message}
            </span>
          </div>
          <ResultsTable guides={results.guides} expandedIdx={expandedIdx} onToggle={toggleRow} />
        </div>
      )}
    </div>
  )
}

// ─── Prime editor panel ───────────────────────────────────────────────────────

function PegRnaColoredSeq({ full_pegrna, rt_template_length, pbs_length, scaffold }) {
  if (!full_pegrna) return null
  const scaffoldLen = scaffold.length
  const spacerEnd   = 20
  const scaffoldEnd = spacerEnd + scaffoldLen
  const rtEnd       = scaffoldEnd + rt_template_length
  // pbs is the rest

  const spans = [
    { text: full_pegrna.slice(0, spacerEnd),   color: T.green,  label: 'spacer'   },
    { text: full_pegrna.slice(spacerEnd, scaffoldEnd), color: T.muted, label: 'scaffold' },
    { text: full_pegrna.slice(scaffoldEnd, rtEnd),     color: T.amber, label: 'RT tmpl'  },
    { text: full_pegrna.slice(rtEnd),                   color: T.purple, label: 'PBS'    },
  ]

  return (
    <div style={{ fontFamily: 'monospace', fontSize: 11, lineHeight: 1.6, wordBreak: 'break-all', color: T.text }}>
      {spans.map(({ text, color }) => (
        <span key={color} style={{ color }}>{text}</span>
      ))}
    </div>
  )
}

function SeqSection({ label, seq, badge, children }) {
  return (
    <div style={{
      background: T.deep, border: `1px solid ${T.border}`,
      borderRadius: 6, padding: '12px 14px',
    }}>
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: 8 }}>
        <span style={{ fontSize: 9, color: T.muted, fontFamily: 'monospace', letterSpacing: '2px' }}>
          {label}
        </span>
        <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
          {badge && (
            <span style={{
              padding: '1px 7px', borderRadius: 10, fontSize: 9,
              background: 'rgba(0,255,136,0.08)', color: T.dim,
              fontFamily: 'monospace', border: `1px solid ${T.border}`,
            }}>
              {badge}
            </span>
          )}
          {seq && <CopyBtn text={seq} />}
        </div>
      </div>
      <div style={{ fontFamily: 'monospace', fontSize: 12, color: T.green, wordBreak: 'break-all', lineHeight: 1.5 }}>
        {seq}
      </div>
      {children}
    </div>
  )
}

function PrimeEditorPanel({ sequence }) {
  const [editPos,  setEditPos]  = useState('')
  const [editType, setEditType] = useState('substitution')
  const [editSeq,  setEditSeq]  = useState('')
  const [editLen,  setEditLen]  = useState(1)
  const [result,   setResult]   = useState(null)
  const [loading,  setLoading]  = useState(false)
  const [error,    setError]    = useState(null)
  const [sciOpen,  setSciOpen]  = useState(false)
  const [btnH,     btnEvents]   = useHover()

  async function handleDesign() {
    if (!sequence.trim() || !editPos) return
    setLoading(true); setError(null); setResult(null)
    try {
      const { data } = await api.post('/api/baseedit/prime_editor', {
        sequence,
        edit_position: parseInt(editPos, 10),
        edit_type:     editType,
        edit_sequence: editSeq,
        edit_length:   parseInt(editLen, 10) || 1,
      })
      setResult(data)
    } catch (err) {
      setError(err?.response?.data?.detail ?? err.message ?? 'Design failed')
    } finally {
      setLoading(false)
    }
  }

  const inputStyle = {
    background: T.deep, border: `1px solid ${T.border}`, borderRadius: 4,
    padding: '5px 10px', fontSize: 12, color: T.green,
    outline: 'none', fontFamily: 'monospace',
  }

  const editTypes = ['substitution', 'insertion', 'deletion']

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 16 }}>
      {/* controls */}
      <div style={{
        background: 'rgba(2,10,6,0.98)', border: `1px solid ${T.border}`,
        borderRadius: 8, padding: '14px 18px',
        display: 'flex', flexWrap: 'wrap', alignItems: 'flex-end', gap: 16,
      }}>
        <div>
          <div style={{ fontSize: 9, color: T.muted, letterSpacing: '2px', fontFamily: 'monospace', marginBottom: 5 }}>
            EDIT POSITION (bp)
          </div>
          <input type="number" value={editPos} onChange={e => setEditPos(e.target.value)}
            placeholder="e.g. 50" style={{ ...inputStyle, width: 110 }} />
        </div>

        <div>
          <div style={{ fontSize: 9, color: T.muted, letterSpacing: '2px', fontFamily: 'monospace', marginBottom: 5 }}>
            EDIT TYPE
          </div>
          <div style={{ display: 'flex', gap: 6 }}>
            {editTypes.map(et => (
              <button key={et} onClick={() => setEditType(et)} style={{
                padding: '4px 12px', borderRadius: 12, fontSize: 10, cursor: 'pointer',
                fontFamily: 'monospace', textTransform: 'capitalize',
                fontWeight: editType === et ? 700 : 400,
                background: editType === et ? T.green : 'transparent',
                color: editType === et ? '#020a06' : T.green,
                border: `1px solid ${editType === et ? T.green : 'rgba(0,255,136,0.3)'}`,
                transition: 'all 0.15s',
              }}>
                {et}
              </button>
            ))}
          </div>
        </div>

        {editType !== 'deletion' ? (
          <div>
            <div style={{ fontSize: 9, color: T.muted, letterSpacing: '2px', fontFamily: 'monospace', marginBottom: 5 }}>
              {editType === 'substitution' ? 'NEW BASE(S)' : 'SEQUENCE TO INSERT'}
            </div>
            <input type="text" value={editSeq} onChange={e => setEditSeq(e.target.value.toUpperCase())}
              placeholder="e.g. T" style={{ ...inputStyle, width: 150 }} />
          </div>
        ) : (
          <div>
            <div style={{ fontSize: 9, color: T.muted, letterSpacing: '2px', fontFamily: 'monospace', marginBottom: 5 }}>
              BASES TO DELETE
            </div>
            <input type="number" value={editLen} onChange={e => setEditLen(e.target.value)}
              min={1} style={{ ...inputStyle, width: 80 }} />
          </div>
        )}

        <button
          onClick={handleDesign}
          disabled={loading || !sequence.trim() || !editPos}
          {...btnEvents}
          style={{
            width: '100%', padding: '8px 0', borderRadius: 6,
            fontSize: 11, cursor: 'pointer', fontFamily: 'monospace',
            fontWeight: 700, letterSpacing: '1px',
            background: loading ? 'rgba(0,255,136,0.08)' : btnH ? T.green : 'rgba(0,255,136,0.12)',
            color: btnH && !loading ? '#020a06' : T.green,
            border: `1px solid ${T.border2}`,
            opacity: (!sequence.trim() || !editPos) ? 0.4 : 1,
            transition: 'all 0.15s',
          }}
        >
          {loading ? 'Designing pegRNA...' : 'Design pegRNA'}
        </button>
      </div>

      {error && (
        <div style={{
          padding: '8px 14px', borderRadius: 6,
          background: 'rgba(255,34,68,0.08)', border: '1px solid rgba(255,34,68,0.3)',
          color: T.red, fontSize: 12, fontFamily: 'monospace',
        }}>
          {error}
        </div>
      )}

      {result && result.spacer && (
        <div style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
          {/* edit preview */}
          <div style={{
            background: T.deep, border: `1px solid rgba(0,255,136,0.12)`,
            borderRadius: 8, padding: '14px 16px',
          }}>
            <div style={{ fontSize: 9, color: T.muted, fontFamily: 'monospace', letterSpacing: '2px', marginBottom: 10 }}>
              // EDIT PREVIEW
            </div>
            <div style={{ display: 'flex', alignItems: 'center', gap: 16, flexWrap: 'wrap' }}>
              <div>
                <div style={{ fontSize: 9, color: T.muted, fontFamily: 'monospace', marginBottom: 3 }}>Before</div>
                <code style={{ fontFamily: 'monospace', fontSize: 12, color: T.text, letterSpacing: 1 }}>
                  {result.edit_preview.before}
                </code>
              </div>
              <div style={{ color: T.green, fontSize: 20 }}>→</div>
              <div>
                <div style={{ fontSize: 9, color: T.muted, fontFamily: 'monospace', marginBottom: 3 }}>After</div>
                <code style={{ fontFamily: 'monospace', fontSize: 12, letterSpacing: 1 }}>
                  <span style={{ color: T.text }}>
                    {result.edit_preview.after.slice(0, result.edit_preview.after.indexOf(result.edit_preview.edit_highlighted) || 0)}
                  </span>
                  <span style={{ color: T.amber, fontWeight: 700 }}>
                    {result.edit_preview.edit_highlighted}
                  </span>
                  <span style={{ color: T.text }}>
                    {result.edit_preview.after.slice(
                      (result.edit_preview.after.indexOf(result.edit_preview.edit_highlighted) || 0) +
                      result.edit_preview.edit_highlighted.length
                    )}
                  </span>
                </code>
              </div>
            </div>
          </div>

          {/* pegRNA components */}
          <SeqSection
            label="// SPACER (20nt)"
            seq={result.spacer}
            badge={`nicks bp ${result.nick_position}`}
          >
            <div style={{ fontSize: 10, color: T.dim, fontFamily: 'monospace', marginTop: 6 }}>
              PAM: <span style={{ color: T.amber }}>{result.pam}</span>
              <span style={{ marginLeft: 12 }}>strand guide — nicks at bp {result.nick_position}</span>
            </div>
          </SeqSection>

          <SeqSection
            label="// RT TEMPLATE"
            seq={result.rt_template}
            badge={`${result.rt_template_length}nt`}
          />

          <SeqSection
            label="// PBS (PRIMER BINDING SITE)"
            seq={result.pbs}
            badge={`${result.pbs_length}nt`}
          />

          {/* full pegRNA */}
          <div style={{
            background: T.deep, border: `1px solid ${T.border}`,
            borderRadius: 6, padding: '12px 14px',
          }}>
            <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: 8 }}>
              <span style={{ fontSize: 9, color: T.muted, fontFamily: 'monospace', letterSpacing: '2px' }}>
                // FULL pegRNA SEQUENCE
              </span>
              <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                <span style={{
                  padding: '1px 7px', borderRadius: 10, fontSize: 9,
                  background: 'rgba(0,255,136,0.08)', color: T.dim,
                  fontFamily: 'monospace', border: `1px solid ${T.border}`,
                }}>
                  {result.full_pegrna.length}nt total
                </span>
                <CopyBtn text={result.full_pegrna} />
              </div>
            </div>
            <PegRnaColoredSeq
              full_pegrna={result.full_pegrna}
              rt_template_length={result.rt_template_length}
              pbs_length={result.pbs_length}
              scaffold={result.scaffold}
            />
            {/* color legend */}
            <div style={{ display: 'flex', gap: 16, marginTop: 10, flexWrap: 'wrap' }}>
              {[
                { color: T.green,  label: 'spacer'      },
                { color: T.muted,  label: 'scaffold'    },
                { color: T.amber,  label: 'RT template' },
                { color: T.purple, label: 'PBS'         },
              ].map(({ color, label }) => (
                <div key={label} style={{ display: 'flex', alignItems: 'center', gap: 5, fontSize: 9, color: T.muted, fontFamily: 'monospace' }}>
                  <div style={{ width: 8, height: 8, borderRadius: 1, background: color }} />
                  {label}
                </div>
              ))}
            </div>
          </div>

          {result.pe3_nicking_guide && (
            <SeqSection
              label="// PE3 NICKING GUIDE (optional)"
              seq={result.pe3_nicking_guide}
              badge={`bp ${result.pe3_position}`}
            >
              <div style={{ fontSize: 10, color: T.dim, fontFamily: 'monospace', marginTop: 6 }}>
                Improves efficiency by 3–5× — nicks opposite strand at bp {result.pe3_position}
              </div>
            </SeqSection>
          )}

          {/* ordering info */}
          <div style={{
            background: T.deep, border: `1px solid rgba(0,255,136,0.08)`,
            borderRadius: 8, padding: '14px 16px',
          }}>
            <div style={{ fontSize: 9, color: T.muted, fontFamily: 'monospace', letterSpacing: '2px', marginBottom: 10 }}>
              // HOW TO ORDER
            </div>
            <div style={{ display: 'flex', flexDirection: 'column', gap: 6, fontSize: 11, color: T.dim, fontFamily: 'monospace', lineHeight: 1.6 }}>
              <div>
                pegRNA ({result.ordering_info.pegrna_length}nt): Order as IVT template from IDT or as Addgene plasmid
              </div>
              {result.pe3_nicking_guide && (
                <div>Nicking guide: Standard sgRNA order (25 nmole scale)</div>
              )}
              <div style={{ color: T.muted, fontSize: 10, marginTop: 4 }}>
                Recommended: Addgene #174038 (PE2 plasmid) or #132776 (PE3 plasmid)
              </div>
            </div>
          </div>
        </div>
      )}

      {result && !result.spacer && (
        <div style={{ padding: '32px 0', textAlign: 'center', color: T.muted, fontFamily: 'monospace', fontSize: 12 }}>
          No suitable PAM site found within 40bp of the edit position.<br />
          <span style={{ fontSize: 10, color: T.muted, marginTop: 6, display: 'block' }}>
            Try a nearby position or use an NG-PAM variant.
          </span>
        </div>
      )}

      {/* scientific note */}
      <div style={{ border: `1px solid ${T.border}`, borderRadius: 8, overflow: 'hidden' }}>
        <button
          onClick={() => setSciOpen(v => !v)}
          style={{
            width: '100%', padding: '10px 16px', background: 'transparent',
            border: 'none', cursor: 'pointer', textAlign: 'left',
            display: 'flex', alignItems: 'center', justifyContent: 'space-between',
          }}
        >
          <span style={{ fontSize: 10, color: T.muted, fontFamily: 'monospace', letterSpacing: '1px' }}>
            About base editors and prime editors
          </span>
          <span style={{ color: T.muted, fontSize: 10 }}>{sciOpen ? '▲' : '▼'}</span>
        </button>
        {sciOpen && (
          <div style={{
            padding: '0 16px 14px',
            borderTop: `1px solid ${T.border}`,
            fontSize: 10, color: T.muted, fontFamily: 'monospace', lineHeight: 1.8,
          }}>
            <div style={{ marginTop: 10 }}>
              <strong style={{ color: T.dim }}>Cytosine base editors (CBE)</strong> fuse a deaminase (rAPOBEC1 or AID)
              to a catalytically impaired Cas9 (nCas9 or dCas9). The deaminase converts cytosines in the editing
              window (positions 4–8 of the protospacer) to uracil, which is read as thymine — effecting a C·G → T·A
              transition. BE3 and BE4max differ in deaminase linker design and UGI copy number.
            </div>
            <div style={{ marginTop: 8 }}>
              <strong style={{ color: T.dim }}>Adenine base editors (ABE)</strong> use an evolved tRNA adenosine
              deaminase (TadA) fused to nCas9 to convert adenosine to inosine (read as guanosine), effecting
              an A·T → G·C transition. ABE8e incorporates enhanced TadA8e with a broader editing window.
            </div>
            <div style={{ marginTop: 8 }}>
              <strong style={{ color: T.dim }}>Prime editing (PE)</strong> uses a reverse transcriptase fused to nCas9
              and a pegRNA encoding both the spacer and an RT template. After nicking, the 3' flap is extended using
              the pegRNA as template, installing any substitution, insertion, or deletion without DSBs or HDR donor.
            </div>
            <div style={{ marginTop: 8, color: T.muted, fontSize: 9 }}>
              References: Komor et al. Nature 2016 (BE3) · Gaudelli et al. Nature 2017 (ABE7) ·
              Anzalone et al. Nature 2019 (PE2/PE3) · Richter et al. Nature Biotech 2020 (ABE8e)
            </div>
          </div>
        )}
      </div>
    </div>
  )
}

// ─── Main page ────────────────────────────────────────────────────────────────

export default function BaseEditor() {
  const { sequence } = useHelixStore()
  const [mode, setMode] = useState('CBE')

  const modes = [
    { id: 'CBE', label: 'CBE — C→T' },
    { id: 'ABE', label: 'ABE — A→G' },
    { id: 'PE',  label: 'Prime Editor' },
  ]

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 16, maxWidth: 1100 }}>
      {/* header */}
      <div>
        <div style={{ fontSize: 14, color: T.green, fontFamily: 'monospace', letterSpacing: '2px', fontWeight: 700 }}>
          // BASE &amp; PRIME EDITOR DESIGNER
        </div>
        <div style={{ fontSize: 11, color: T.muted, fontFamily: 'monospace', marginTop: 3 }}>
          Design guides for CBE, ABE, and Prime Editing
        </div>
        <div style={{ fontSize: 10, color: T.muted, fontFamily: 'monospace', marginTop: 2 }}>
          Based on David Liu lab editors (2016–2019)
        </div>
      </div>

      {!sequence.trim() && (
        <div style={{
          padding: '10px 14px', borderRadius: 6,
          background: 'rgba(255,170,0,0.06)', border: '1px solid rgba(255,170,0,0.2)',
          color: T.amber, fontSize: 11, fontFamily: 'monospace',
        }}>
          No sequence loaded — paste a sequence in the Sandbox first, or type directly in the target position field.
        </div>
      )}

      {/* mode selector */}
      <div style={{ display: 'flex', gap: 8 }}>
        {modes.map(({ id, label }) => (
          <button key={id} onClick={() => setMode(id)} style={{
            padding: '10px 20px', borderRadius: 6, fontSize: 12, cursor: 'pointer',
            fontFamily: 'monospace', fontWeight: mode === id ? 700 : 400,
            letterSpacing: '0.5px',
            background: mode === id ? T.green : 'transparent',
            color: mode === id ? '#020a06' : T.green,
            border: `1px solid ${mode === id ? T.green : 'rgba(0,255,136,0.3)'}`,
            transition: 'all 0.15s',
          }}>
            {label}
          </button>
        ))}
      </div>

      {/* panel */}
      {mode !== 'PE'
        ? <CbeAbePanel mode={mode} sequence={sequence} />
        : <PrimeEditorPanel sequence={sequence} />
      }
    </div>
  )
}
