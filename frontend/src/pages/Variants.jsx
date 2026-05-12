import { useState, useMemo } from 'react'
import { compareVariants } from '../api'

const T = {
  bg:      '#020a06',
  surface: '#0a1f10',
  border:  'rgba(0, 255, 136, 0.12)',
  border2: 'rgba(0, 255, 136, 0.3)',
  deep:    '#051209',
  green:   '#00ff88',
  greenDk: '#004422',
  amber:   '#ffaa00',
  red:     '#ff2244',
  text:    '#c8f5d8',
  dim:     '#4a8a5a',
  muted:   '#1a4a2a',
}

const TYPE_STYLE = {
  SNP: { background: 'rgba(255,34,68,0.12)',  color: '#ff2244' },
  INS: { background: 'rgba(0,255,136,0.1)',   color: '#00ff88' },
  DEL: { background: 'rgba(255,170,0,0.1)',   color: '#ffaa00' },
}

const IMPACT_STYLE = {
  disrupts_pam:  { background: 'rgba(255,34,68,0.1)',   color: '#ff2244' },
  disrupts_seed: { background: 'rgba(255,170,0,0.1)',   color: '#ffaa00' },
  safe:          { background: 'rgba(0,255,136,0.1)',   color: '#00ff88' },
}

const SANITIZE = s => (s || '').toUpperCase().replace(/[^ACGT]/g, '')

function useHover() {
  const [h, setH] = useState(false)
  return [h, { onMouseEnter: () => setH(true), onMouseLeave: () => setH(false) }]
}

function TypeBadge({ type }) {
  const s = TYPE_STYLE[type] ?? { background: T.border, color: T.dim }
  return (
    <span style={{
      ...s, padding: '2px 7px', borderRadius: 4,
      fontSize: 10, fontWeight: 700, fontFamily: 'monospace',
    }}>
      {type}
    </span>
  )
}

function ImpactBadge({ impact }) {
  const s = IMPACT_STYLE[impact] ?? IMPACT_STYLE.safe
  return (
    <span style={{
      ...s, padding: '2px 7px', borderRadius: 4,
      fontSize: 10, fontWeight: 600, fontFamily: 'monospace',
    }}>
      {impact.replace(/_/g, ' ')}
    </span>
  )
}

// ─── diff viewer ──────────────────────────────────────────────────────────────

const CHUNK = 60

function DiffViewer({ refSeq, qrySeq, variantMap }) {
  const maxLen = Math.max(refSeq.length, qrySeq.length)
  if (!maxLen) return null

  const posStyle = {
    color: T.muted, fontSize: 10, fontFamily: 'monospace',
    minWidth: 52, textAlign: 'right', paddingRight: 10,
    flexShrink: 0, userSelect: 'none',
  }

  const chunks = []
  for (let start = 0; start < maxLen; start += CHUNK) {
    chunks.push(start)
  }

  return (
    <div style={{ fontFamily: 'monospace', fontSize: 12, overflowX: 'auto' }}>
      {chunks.map(start => {
        const end = Math.min(start + CHUNK, maxLen)
        return (
          <div key={start} style={{ marginBottom: 8 }}>
            <div style={{ display: 'flex', alignItems: 'baseline', lineHeight: 1.7 }}>
              <span style={posStyle}>{start}</span>
              <span>
                {Array.from({ length: end - start }, (_, i) => {
                  const pos = start + i
                  const v = variantMap[pos]
                  const ch = pos < refSeq.length ? refSeq[pos] : '-'
                  return (
                    <span key={i} style={v ? TYPE_STYLE[v.type] : { color: T.dim }}>{ch}</span>
                  )
                })}
              </span>
            </div>
            <div style={{ display: 'flex', alignItems: 'baseline', lineHeight: 1.7 }}>
              <span style={{ ...posStyle, visibility: 'hidden' }}>0</span>
              <span>
                {Array.from({ length: end - start }, (_, i) => {
                  const pos = start + i
                  const v = variantMap[pos]
                  const ch = pos < qrySeq.length ? qrySeq[pos] : '-'
                  return (
                    <span key={i} style={v ? TYPE_STYLE[v.type] : { color: T.dim }}>{ch}</span>
                  )
                })}
              </span>
            </div>
          </div>
        )
      })}
    </div>
  )
}

// ─── main page ────────────────────────────────────────────────────────────────

export default function Variants() {
  const [refSeq, setRefSeq]         = useState('')
  const [qrySeq, setQrySeq]         = useState('')
  const [displayRef, setDisplayRef] = useState('')
  const [displayQry, setDisplayQry] = useState('')
  const [result, setResult]         = useState(null)
  const [loading, setLoading]       = useState(false)
  const [error, setError]           = useState(null)
  const [compareH, compareEvents]   = useHover()

  const variantMap = useMemo(() => {
    const m = {}
    for (const v of result?.variants ?? []) m[v.pos] = v
    return m
  }, [result])

  async function handleCompare() {
    if (!refSeq.trim() || !qrySeq.trim()) return
    setLoading(true)
    setError(null)
    setDisplayRef(SANITIZE(refSeq.trim()))
    setDisplayQry(SANITIZE(qrySeq.trim()))
    try {
      const data = await compareVariants(qrySeq.trim(), refSeq.trim())
      setResult(data)
    } catch (err) {
      setError(err?.response?.data?.detail ?? err.message ?? 'Comparison failed')
    } finally {
      setLoading(false)
    }
  }

  const compareDisabled = loading || !refSeq.trim() || !qrySeq.trim()

  const textareaStyle = {
    width: '100%',
    minHeight: 120,
    background: T.deep,
    border: `1px solid ${T.border}`,
    borderRadius: 4,
    padding: '8px 12px',
    fontFamily: 'monospace',
    fontSize: 12,
    color: T.green,
    outline: 'none',
    resize: 'vertical',
    boxSizing: 'border-box',
  }

  const thStyle = {
    padding: '8px 12px', color: T.muted, fontSize: 9,
    textTransform: 'uppercase', letterSpacing: '2px',
    fontWeight: 500, textAlign: 'left', fontFamily: 'monospace',
  }

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 16 }}>

      {/* Input panel */}
      <div style={{
        background: T.surface, border: `1px solid ${T.border}`,
        borderRadius: 8, padding: 16,
      }}>
        <div style={{
          display: 'grid',
          gridTemplateColumns: '1fr auto 1fr',
          gap: 12,
          alignItems: 'center',
        }}>
          <div style={{ display: 'flex', flexDirection: 'column', gap: 6 }}>
            <span style={{
              fontSize: 9, color: T.muted,
              textTransform: 'uppercase', letterSpacing: '2px', fontFamily: 'monospace',
            }}>
              Reference Sequence
            </span>
            <textarea
              value={refSeq}
              onChange={e => setRefSeq(e.target.value)}
              placeholder="Paste reference DNA sequence (ACGT)…"
              spellCheck={false}
              style={textareaStyle}
            />
          </div>

          <button
            onClick={handleCompare}
            disabled={compareDisabled}
            {...compareEvents}
            style={{
              padding: '8px 16px', borderRadius: 4,
              background: compareH && !compareDisabled ? T.greenDk : T.green,
              color: '#020a06', fontWeight: 700, fontSize: 12,
              fontFamily: 'monospace', border: 'none',
              cursor: compareDisabled ? 'not-allowed' : 'pointer',
              opacity: compareDisabled ? 0.5 : 1,
              whiteSpace: 'nowrap',
              transition: 'background 0.15s',
            }}
          >
            {loading ? 'Comparing…' : 'Compare'}
          </button>

          <div style={{ display: 'flex', flexDirection: 'column', gap: 6 }}>
            <span style={{
              fontSize: 9, color: T.muted,
              textTransform: 'uppercase', letterSpacing: '2px', fontFamily: 'monospace',
            }}>
              Query Sequence
            </span>
            <textarea
              value={qrySeq}
              onChange={e => setQrySeq(e.target.value)}
              placeholder="Paste query DNA sequence (ACGT)…"
              spellCheck={false}
              style={textareaStyle}
            />
          </div>
        </div>
      </div>

      {error && (
        <div style={{
          padding: '8px 16px', background: 'rgba(255,34,68,0.08)',
          border: '1px solid rgba(255,34,68,0.3)', borderRadius: 6,
          color: T.red, fontSize: 12, fontFamily: 'monospace',
        }}>
          <span style={{ fontWeight: 700 }}>Error: </span>{error}
        </div>
      )}

      {!result && !error && (
        <div style={{
          display: 'flex', alignItems: 'center', justifyContent: 'center',
          padding: '48px 0', color: T.muted, fontSize: 12,
          background: T.surface, border: `1px solid ${T.border}`,
          borderRadius: 8, fontFamily: 'monospace',
        }}>
          Paste a reference and query sequence to compare variants
        </div>
      )}

      {result && (
        <div style={{ display: 'flex', gap: 12 }}>
          {[
            { label: 'SNPs',       count: result.snp_count, color: T.amber  },
            { label: 'Insertions', count: result.ins_count, color: T.green  },
            { label: 'Deletions',  count: result.del_count, color: T.red    },
          ].map(({ label, count, color }) => (
            <div key={label} style={{
              flex: 1, background: T.surface, border: `1px solid ${T.border}`,
              borderRadius: 6, padding: '12px 16px',
              display: 'flex', alignItems: 'center', gap: 12,
            }}>
              <span style={{ fontSize: 22, fontFamily: 'monospace', color, fontWeight: 500 }}>
                {count}
              </span>
              <span style={{ fontSize: 9, color: T.muted, textTransform: 'uppercase', letterSpacing: '2px', fontFamily: 'monospace' }}>
                {label}
              </span>
            </div>
          ))}
        </div>
      )}

      {result && (
        <div style={{
          background: T.surface, border: `1px solid ${T.border}`,
          borderRadius: 8, overflow: 'hidden',
        }}>
          <div style={{
            padding: '8px 16px', borderBottom: `1px solid ${T.border}`,
            display: 'flex', alignItems: 'center', justifyContent: 'space-between',
          }}>
            <span style={{ fontSize: 9, color: T.muted, textTransform: 'uppercase', letterSpacing: '2px', fontFamily: 'monospace' }}>
              Inline Diff
            </span>
            <div style={{ display: 'flex', gap: 14, fontSize: 10, color: T.muted, fontFamily: 'monospace' }}>
              {[
                ['SNP', TYPE_STYLE.SNP.color],
                ['INS', TYPE_STYLE.INS.color],
                ['DEL', TYPE_STYLE.DEL.color],
              ].map(([label, color]) => (
                <span key={label} style={{ display: 'flex', alignItems: 'center', gap: 4 }}>
                  <span style={{ display: 'inline-block', width: 8, height: 8, borderRadius: 2, background: color }} />
                  {label}
                </span>
              ))}
            </div>
          </div>
          <div style={{ padding: 16 }}>
            <DiffViewer refSeq={displayRef} qrySeq={displayQry} variantMap={variantMap} />
          </div>
        </div>
      )}

      {result && result.variants.length > 0 && (
        <div style={{
          background: T.surface, border: `1px solid ${T.border}`,
          borderRadius: 8, overflow: 'hidden',
        }}>
          <div style={{ padding: '8px 16px', borderBottom: `1px solid ${T.border}` }}>
            <span style={{ fontSize: 9, color: T.muted, textTransform: 'uppercase', letterSpacing: '2px', fontFamily: 'monospace' }}>
              Variant Table — {result.total} variants
            </span>
          </div>
          <div style={{ overflowX: 'auto' }}>
            <table style={{ width: '100%', borderCollapse: 'collapse' }}>
              <thead>
                <tr style={{ borderBottom: `1px solid ${T.border}` }}>
                  <th style={thStyle}>Position</th>
                  <th style={thStyle}>Type</th>
                  <th style={thStyle}>Ref</th>
                  <th style={thStyle}>Alt</th>
                  <th style={thStyle}>CRISPR Impact</th>
                </tr>
              </thead>
              <tbody>
                {result.variants.map(v => (
                  <tr
                    key={v.pos}
                    style={{ borderBottom: `1px solid ${T.border}` }}
                    onMouseEnter={e => { e.currentTarget.style.background = 'rgba(0,255,136,0.03)' }}
                    onMouseLeave={e => { e.currentTarget.style.background = 'transparent' }}
                  >
                    <td style={{ padding: '8px 12px', color: T.dim, fontFamily: 'monospace', fontSize: 12 }}>
                      {v.pos}
                    </td>
                    <td style={{ padding: '8px 12px' }}><TypeBadge type={v.type} /></td>
                    <td style={{ padding: '8px 12px', fontFamily: 'monospace', color: T.text, fontSize: 12 }}>
                      {v.ref}
                    </td>
                    <td style={{ padding: '8px 12px', fontFamily: 'monospace', color: T.text, fontSize: 12 }}>
                      {v.alt}
                    </td>
                    <td style={{ padding: '8px 12px' }}><ImpactBadge impact={v.impact} /></td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {result && result.variants.length === 0 && (
        <div style={{
          display: 'flex', alignItems: 'center', justifyContent: 'center',
          padding: '48px 0', color: T.muted, fontSize: 12,
          background: T.surface, border: `1px solid ${T.border}`,
          borderRadius: 8, fontFamily: 'monospace',
        }}>
          Sequences are identical — no variants found
        </div>
      )}

    </div>
  )
}
