import { useState, useMemo } from 'react'
import { compareVariants } from '../api'

const T = {
  bg:      '#0f1117',
  surface: '#151821',
  border:  '#1e2130',
  border2: '#2a2e3e',
  teal:    '#1D9E75',
  amber:   '#EF9F27',
  text:    '#e8e6df',
  muted:   '#5F5E5A',
  mid:     '#888780',
}

const TYPE_STYLE = {
  SNP: { background: '#3D1515', color: '#F09595' },
  INS: { background: '#0D2E1F', color: '#5DCAA5' },
  DEL: { background: '#2E1F0A', color: '#FAC775' },
}

const IMPACT_STYLE = {
  disrupts_pam:  { background: '#6B1D1D', color: '#F09595' },
  disrupts_seed: { background: '#633806', color: '#FAC775' },
  safe:          { background: '#085041', color: '#5DCAA5' },
}

const SANITIZE = s => (s || '').toUpperCase().replace(/[^ACGT]/g, '')

function useHover() {
  const [h, setH] = useState(false)
  return [h, { onMouseEnter: () => setH(true), onMouseLeave: () => setH(false) }]
}

function TypeBadge({ type }) {
  const s = TYPE_STYLE[type] ?? { background: T.border, color: T.mid }
  return (
    <span style={{
      ...s, padding: '2px 7px', borderRadius: 4,
      fontSize: 11, fontWeight: 700,
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
      fontSize: 11, fontWeight: 600,
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
            {/* reference row */}
            <div style={{ display: 'flex', alignItems: 'baseline', lineHeight: 1.7 }}>
              <span style={posStyle}>{start}</span>
              <span>
                {Array.from({ length: end - start }, (_, i) => {
                  const pos = start + i
                  const v = variantMap[pos]
                  const ch = pos < refSeq.length ? refSeq[pos] : '-'
                  return (
                    <span key={i} style={v ? TYPE_STYLE[v.type] : { color: T.mid }}>{ch}</span>
                  )
                })}
              </span>
            </div>
            {/* query row */}
            <div style={{ display: 'flex', alignItems: 'baseline', lineHeight: 1.7 }}>
              <span style={{ ...posStyle, visibility: 'hidden' }}>0</span>
              <span>
                {Array.from({ length: end - start }, (_, i) => {
                  const pos = start + i
                  const v = variantMap[pos]
                  const ch = pos < qrySeq.length ? qrySeq[pos] : '-'
                  return (
                    <span key={i} style={v ? TYPE_STYLE[v.type] : { color: T.mid }}>{ch}</span>
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
    background: T.bg,
    border: `0.5px solid ${T.border2}`,
    borderRadius: 6,
    padding: '8px 12px',
    fontFamily: 'monospace',
    fontSize: 12,
    color: T.text,
    outline: 'none',
    resize: 'vertical',
    boxSizing: 'border-box',
  }

  const thStyle = {
    padding: '8px 12px', color: T.muted, fontSize: 10,
    textTransform: 'uppercase', letterSpacing: '0.8px',
    fontWeight: 500, textAlign: 'left',
  }

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 16 }}>

      {/* Input panel */}
      <div style={{
        background: T.surface, border: `0.5px solid ${T.border}`,
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
              fontSize: 10, color: T.muted,
              textTransform: 'uppercase', letterSpacing: '0.8px',
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
              padding: '8px 16px', borderRadius: 6,
              background: compareH && !compareDisabled ? '#0F6E56' : T.teal,
              color: '#04342C', fontWeight: 500, fontSize: 13,
              border: 'none',
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
              fontSize: 10, color: T.muted,
              textTransform: 'uppercase', letterSpacing: '0.8px',
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

      {/* Error */}
      {error && (
        <div style={{
          padding: '8px 16px', background: '#1a0808',
          border: '0.5px solid #4a1010', borderRadius: 6,
          color: '#f09595', fontSize: 12,
        }}>
          <span style={{ fontWeight: 700 }}>Error: </span>{error}
        </div>
      )}

      {/* Empty state */}
      {!result && !error && (
        <div style={{
          display: 'flex', alignItems: 'center', justifyContent: 'center',
          padding: '48px 0', color: T.muted, fontSize: 13,
          background: T.surface, border: `0.5px solid ${T.border}`,
          borderRadius: 8,
        }}>
          Paste a reference and query sequence to compare variants
        </div>
      )}

      {/* Stat row */}
      {result && (
        <div style={{ display: 'flex', gap: 12 }}>
          {[
            { label: 'SNPs',       count: result.snp_count, color: T.amber    },
            { label: 'Insertions', count: result.ins_count, color: T.teal     },
            { label: 'Deletions',  count: result.del_count, color: '#F09595'  },
          ].map(({ label, count, color }) => (
            <div key={label} style={{
              flex: 1, background: T.surface, border: `0.5px solid ${T.border}`,
              borderRadius: 8, padding: '12px 16px',
              display: 'flex', alignItems: 'center', gap: 12,
            }}>
              <span style={{ fontSize: 22, fontFamily: 'monospace', color, fontWeight: 500 }}>
                {count}
              </span>
              <span style={{ fontSize: 10, color: T.muted, textTransform: 'uppercase', letterSpacing: '0.8px' }}>
                {label}
              </span>
            </div>
          ))}
        </div>
      )}

      {/* Diff viewer */}
      {result && (
        <div style={{
          background: T.surface, border: `0.5px solid ${T.border}`,
          borderRadius: 8, overflow: 'hidden',
        }}>
          <div style={{
            padding: '8px 16px', borderBottom: `0.5px solid ${T.border}`,
            display: 'flex', alignItems: 'center', justifyContent: 'space-between',
          }}>
            <span style={{ fontSize: 10, color: T.muted, textTransform: 'uppercase', letterSpacing: '0.8px' }}>
              Inline Diff
            </span>
            <div style={{ display: 'flex', gap: 14, fontSize: 11, color: T.muted }}>
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

      {/* Variant table */}
      {result && result.variants.length > 0 && (
        <div style={{
          background: T.surface, border: `0.5px solid ${T.border}`,
          borderRadius: 8, overflow: 'hidden',
        }}>
          <div style={{ padding: '8px 16px', borderBottom: `0.5px solid ${T.border}` }}>
            <span style={{ fontSize: 10, color: T.muted, textTransform: 'uppercase', letterSpacing: '0.8px' }}>
              Variant Table — {result.total} variants
            </span>
          </div>
          <div style={{ overflowX: 'auto' }}>
            <table style={{ width: '100%', borderCollapse: 'collapse' }}>
              <thead>
                <tr style={{ borderBottom: `0.5px solid ${T.border}` }}>
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
                    style={{ borderBottom: `0.5px solid ${T.border}` }}
                    onMouseEnter={e => { e.currentTarget.style.background = '#1a1f2e' }}
                    onMouseLeave={e => { e.currentTarget.style.background = 'transparent' }}
                  >
                    <td style={{ padding: '8px 12px', color: T.mid, fontFamily: 'monospace', fontSize: 12 }}>
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

      {/* Identical sequences */}
      {result && result.variants.length === 0 && (
        <div style={{
          display: 'flex', alignItems: 'center', justifyContent: 'center',
          padding: '48px 0', color: T.muted, fontSize: 13,
          background: T.surface, border: `0.5px solid ${T.border}`,
          borderRadius: 8,
        }}>
          Sequences are identical — no variants found
        </div>
      )}

    </div>
  )
}
