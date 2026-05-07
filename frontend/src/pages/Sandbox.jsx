import { useState, useEffect } from 'react'
import { useNavigate } from 'react-router-dom'
import { analyzeGrnas, saveSequence } from '../api'
import { useHelixStore } from '../store.jsx'
import DnaHelix3D from '../components/DnaHelix3D'

// ─── constants ───────────────────────────────────────────────────────────────

const ENZYMES = ['SpCas9', 'SaCas9', 'Cas12a', 'Cpf1']
const TABS    = ['gRNA Ranking', '2D Tracks', '3D Helix', 'ORFs', 'Variants']

const EXAMPLE_SEQUENCE =
  'ATGCGTACGTACGTAGGCTAGGCTAGGCTAGGCTAGGCTAGGCTAGGCT' +
  'AGGCTAGGCTAGGCTAGGCTAGGCTAGGCTAGGCTAGGCTAGGCTAGGC'

const RISK_STYLE = {
  low:  { background: '#085041', color: '#5DCAA5' },
  med:  { background: '#633806', color: '#FAC775' },
  high: { background: '#6B1D1D', color: '#F09595' },
}

// ─── design tokens ────────────────────────────────────────────────────────────

const T = {
  bg:      '#0f1117',
  surface: '#151821',
  border:  '#1e2130',
  deep:    '#111318',
  border2: '#2a2e3e',
  teal:    '#1D9E75',
  amber:   '#EF9F27',
  text:    '#e8e6df',
  muted:   '#5F5E5A',
  mid:     '#888780',
}

// ─── small helpers ────────────────────────────────────────────────────────────

function scoreColor(score) {
  if (score >= 0.8) return T.teal
  if (score >= 0.6) return T.amber
  return '#993C1D'
}

function useHover() {
  const [h, setH] = useState(false)
  return [h, { onMouseEnter: () => setH(true), onMouseLeave: () => setH(false) }]
}

function RiskBadge({ risk }) {
  const s = RISK_STYLE[risk] ?? RISK_STYLE.high
  return (
    <span style={{ ...s, padding: '2px 8px', borderRadius: 4, fontSize: 11, fontWeight: 700, textTransform: 'uppercase' }}>
      {risk}
    </span>
  )
}

function GcBar({ gc }) {
  return (
    <div style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
      <div style={{ width: 48, height: 4, borderRadius: 2, background: T.border, overflow: 'hidden' }}>
        <div style={{ width: `${Math.min(gc, 100)}%`, height: '100%', borderRadius: 2, background: T.teal }} />
      </div>
      <span style={{ fontSize: 11, color: T.mid }}>{gc.toFixed(0)}%</span>
    </div>
  )
}

function ScoreBar({ score }) {
  const color = scoreColor(score)
  return (
    <div style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
      <div style={{ width: 48, height: 4, borderRadius: 2, background: T.border, overflow: 'hidden' }}>
        <div style={{ width: `${Math.min(score * 100, 100)}%`, height: '100%', borderRadius: 2, background: color }} />
      </div>
      <span style={{ fontSize: 11, fontFamily: 'monospace', fontWeight: 600, color }}>{score.toFixed(3)}</span>
    </div>
  )
}

// ─── stat card ────────────────────────────────────────────────────────────────

function StatCard({ label, value, color }) {
  return (
    <div style={{
      flex: 1,
      background: T.surface,
      border: `0.5px solid ${T.border}`,
      borderRadius: 8,
      padding: '12px 14px',
    }}>
      <div style={{ color, fontSize: 20, fontWeight: 500, fontFamily: 'monospace' }}>{value}</div>
      <div style={{ color: T.muted, fontSize: 10, textTransform: 'uppercase', letterSpacing: '0.8px', marginTop: 4 }}>
        {label}
      </div>
    </div>
  )
}

// ─── loading skeleton ─────────────────────────────────────────────────────────

function TableSkeleton() {
  const bar = (w) => (
    <div style={{ height: 12, width: w, background: T.border, borderRadius: 3 }} />
  )
  return (
    <div style={{ overflowX: 'auto' }}>
      <table style={{ width: '100%', borderCollapse: 'collapse' }}>
        <thead>
          <tr style={{ borderBottom: `0.5px solid ${T.border}` }}>
            {['Rank', 'Sequence', 'GC%', 'Score', 'Risk'].map(h => (
              <th key={h} style={{
                padding: '8px 12px', color: T.muted, fontSize: 10,
                textTransform: 'uppercase', letterSpacing: '0.8px',
                fontWeight: 500, textAlign: 'left',
              }}>{h}</th>
            ))}
          </tr>
        </thead>
        <tbody>
          {Array.from({ length: 5 }).map((_, i) => (
            <tr key={i} className="animate-pulse" style={{ borderBottom: `0.5px solid ${T.border}` }}>
              <td style={{ padding: '12px 12px' }}>{bar(16)}</td>
              <td style={{ padding: '12px 12px' }}>{bar(192)}</td>
              <td style={{ padding: '12px 12px' }}>{bar(64)}</td>
              <td style={{ padding: '12px 12px' }}>{bar(48)}</td>
              <td style={{ padding: '12px 12px' }}>{bar(40)}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  )
}

// ─── grna table ───────────────────────────────────────────────────────────────

function GrnaTable({ grnas, loading, emptyMessage = 'Run an analysis to see gRNA rankings', onView3D, onOffTarget, onPrimers, onAnimate }) {
  if (loading) return <TableSkeleton />

  if (!grnas.length) {
    return (
      <div style={{
        display: 'flex', alignItems: 'center', justifyContent: 'center',
        padding: '64px 0', color: T.muted, fontSize: 13,
      }}>
        {emptyMessage}
      </div>
    )
  }

  const thStyle = {
    padding: '8px 12px', color: T.muted, fontSize: 10,
    textTransform: 'uppercase', letterSpacing: '0.8px',
    fontWeight: 500, textAlign: 'left',
  }

  return (
    <div style={{ overflowX: 'auto' }}>
      <table style={{ width: '100%', borderCollapse: 'collapse' }}>
        <thead>
          <tr style={{ borderBottom: `0.5px solid ${T.border}` }}>
            <th style={thStyle}>Rank</th>
            <th style={thStyle}>Sequence</th>
            <th style={thStyle}>GC%</th>
            <th style={thStyle}>Score</th>
            <th style={thStyle}>Risk</th>
            <th style={thStyle}>Actions</th>
          </tr>
        </thead>
        <tbody>
          {grnas.slice(0, 20).map((row, i) => {
            const body = row.guide.slice(0, -3)
            const pam  = row.guide.slice(-3)
            return (
              <tr
                key={i}
                style={{ borderBottom: `0.5px solid ${T.border}` }}
                onMouseEnter={e => { e.currentTarget.style.background = '#1a1f2e' }}
                onMouseLeave={e => { e.currentTarget.style.background = 'transparent' }}
              >
                <td style={{ padding: '8px 12px', color: T.muted, fontSize: 13 }}>{i + 1}</td>
                <td style={{ padding: '8px 12px', fontFamily: 'monospace', color: T.text, fontSize: 13 }}>
                  {body}<span style={{ color: T.amber }}>{pam}</span>
                </td>
                <td style={{ padding: '8px 12px' }}><GcBar gc={row.gc} /></td>
                <td style={{ padding: '8px 12px' }}><ScoreBar score={row.score} /></td>
                <td style={{ padding: '8px 12px' }}><RiskBadge risk={row.risk} /></td>
                <td style={{ padding: '6px 12px' }}>
                  <div style={{ display: 'flex', gap: 4 }}>
                    {[
                      { label: 'View 3D',      handler: onView3D,    color: T.teal    },
                      { label: 'Off-target',   handler: onOffTarget, color: '#9B8FEF' },
                      { label: 'Primers',      handler: onPrimers,   color: T.amber   },
                      { label: 'Animate cut →', handler: onAnimate,  color: '#F09595' },
                    ].map(({ label, handler, color }) => (
                      <button
                        key={label}
                        onClick={() => handler?.(row)}
                        style={{
                          padding: '2px 7px', borderRadius: 4, fontSize: 10,
                          cursor: 'pointer', border: `0.5px solid ${T.border2}`,
                          color: T.mid, background: 'transparent', whiteSpace: 'nowrap',
                          transition: 'color 0.15s, border-color 0.15s',
                        }}
                        onMouseEnter={e => { e.currentTarget.style.color = color; e.currentTarget.style.borderColor = color }}
                        onMouseLeave={e => { e.currentTarget.style.color = T.mid; e.currentTarget.style.borderColor = T.border2 }}
                      >
                        {label}
                      </button>
                    ))}
                  </div>
                </td>
              </tr>
            )
          })}
        </tbody>
      </table>
    </div>
  )
}

// ─── model strip ──────────────────────────────────────────────────────────────

function ModelStrip() {
  const chips = [
    { label: 'Helix scorer v1.2', active: true  },
    { label: 'Off-target kmer',   active: true  },
    { label: 'AI assistant',      active: false },
  ]
  return (
    <div style={{
      display: 'flex', alignItems: 'center', gap: 16,
      padding: '8px 12px',
      borderTop: `0.5px solid ${T.border}`,
    }}>
      {chips.map(({ label, active }) => (
        <div key={label} style={{ display: 'flex', alignItems: 'center', gap: 6, fontSize: 11, color: T.muted }}>
          <span style={{
            width: 6, height: 6, borderRadius: '50%',
            background: active ? T.teal : T.muted,
            display: 'inline-block', flexShrink: 0,
          }} />
          {label}
        </div>
      ))}
    </div>
  )
}

// ─── gc% svg chart ────────────────────────────────────────────────────────────

const VW = 1000, VL = 40, VR = 12, VT = 8, VB = 22
const VCW = VW - VL - VR
const GC_VH = 120, GC_CH = GC_VH - VT - VB

function GcChart({ gcTrack }) {
  if (!gcTrack?.x?.length) return null

  const { x, y } = gcTrack
  const xMin = x[0], xMax = x[x.length - 1]
  const xRange = xMax - xMin || 1
  const yMax = Math.max(...y)
  const toGcPct = v => (yMax > 1 ? v : v * 100)

  const xs = v => VL + ((v - xMin) / xRange) * VCW
  const ys = v => VT + (1 - toGcPct(v) / 100) * GC_CH

  const points = x.map((xi, i) => `${xs(xi).toFixed(1)},${ys(y[i]).toFixed(1)}`).join(' ')
  const gridGc = [0, 25, 50, 75, 100]
  const xTicks = Array.from({ length: 5 }, (_, i) => Math.round(xMin + (xRange * i) / 4))

  const labelStyle = { fill: T.muted, fontSize: 11 }

  return (
    <svg viewBox={`0 0 ${VW} ${GC_VH}`} width="100%" style={{ display: 'block', height: 120 }}>
      <rect x={VL} y={VT} width={VCW} height={GC_CH} fill={T.surface} />
      {gridGc.map(gc => {
        const cy = VT + (1 - gc / 100) * GC_CH
        return (
          <g key={gc}>
            <line x1={VL} y1={cy} x2={VL + VCW} y2={cy} stroke={T.border} strokeWidth="1" />
            <text x={VL - 4} y={cy} {...labelStyle} textAnchor="end" dominantBaseline="middle">{gc}</text>
          </g>
        )
      })}
      <polyline points={points} fill="none" stroke={T.teal} strokeWidth="1.5" strokeLinejoin="round" />
      <line x1={VL} y1={VT + GC_CH} x2={VL + VCW} y2={VT + GC_CH} stroke={T.border} strokeWidth="1" />
      {xTicks.map(pos => (
        <text key={pos} x={xs(pos).toFixed(1)} y={GC_VH - 4} {...labelStyle} textAnchor="middle">{pos}</text>
      ))}
    </svg>
  )
}

// ─── pam / grna position track ────────────────────────────────────────────────

const PT_VH = 60

function PositionTrack({ grnas, seqLen }) {
  if (!grnas.length || !seqLen) return null

  const xs = pos => VL + (pos / seqLen) * VCW
  const ticks = Array.from({ length: 5 }, (_, i) => Math.round((seqLen * i) / 4))
  const labelStyle = { fill: T.muted, fontSize: 11 }

  return (
    <svg viewBox={`0 0 ${VW} ${PT_VH}`} width="100%" style={{ display: 'block', height: 60 }}>
      <rect x={VL} y={0} width={VCW} height={PT_VH} fill={T.surface} />
      <rect x={VL} y={27} width={VCW} height={4} rx="2" fill={T.border} />

      {grnas.map((g, i) => (
        <line key={`p${i}`}
          x1={xs(g.pos).toFixed(1)} y1={23}
          x2={xs(g.pos).toFixed(1)} y2={37}
          stroke={T.amber} strokeWidth="1" opacity="0.75"
        />
      ))}
      {grnas.map((g, i) => (
        <line key={`g${i}`}
          x1={xs(g.pos).toFixed(1)} y1={19}
          x2={xs(g.pos).toFixed(1)} y2={41}
          stroke={T.teal} strokeWidth="1.5" opacity="0.85"
        />
      ))}

      {ticks.map(pos => (
        <text key={pos} x={xs(pos).toFixed(1)} y={55} {...labelStyle} textAnchor="middle">{pos}</text>
      ))}

      <line x1={VL} y1={10} x2={VL + 14} y2={10} stroke={T.amber} strokeWidth="1.5" />
      <text x={VL + 18} y={14} {...labelStyle}>PAM</text>
      <line x1={VL + 52} y1={10} x2={VL + 66} y2={10} stroke={T.teal} strokeWidth="1.5" />
      <text x={VL + 70} y={14} {...labelStyle}>gRNA</text>
    </svg>
  )
}

// ─── window selector ──────────────────────────────────────────────────────────

function WindowSelector({ grnas, seqLen, onZoom }) {
  const [start, setStart]   = useState(0)
  const [end, setEnd]       = useState(seqLen || 0)
  const [zoomH, zoomEvents] = useHover()

  useEffect(() => { setEnd(seqLen || 0) }, [seqLen])

  const inWindow = grnas.filter(g => g.pos >= start && g.pos <= end).length

  const inputStyle = {
    width: 80, background: T.bg, border: `0.5px solid ${T.border2}`,
    borderRadius: 6, padding: '4px 8px', fontSize: 12,
    color: T.text, outline: 'none', fontFamily: 'monospace',
  }
  const labelStyle = { fontSize: 11, color: T.muted }

  return (
    <div style={{
      display: 'flex', flexWrap: 'wrap', alignItems: 'center', gap: 12,
      padding: '12px 16px', borderTop: `0.5px solid ${T.border}`,
    }}>
      <span style={{ fontSize: 10, color: T.muted, textTransform: 'uppercase', letterSpacing: '0.8px' }}>
        Window
      </span>
      <div style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
        <label style={labelStyle}>Start</label>
        <input type="number" value={start} min={0} max={seqLen}
          onChange={e => setStart(Math.max(0, Number(e.target.value)))}
          style={inputStyle}
        />
      </div>
      <div style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
        <label style={labelStyle}>End</label>
        <input type="number" value={end} min={0} max={seqLen}
          onChange={e => setEnd(Math.min(seqLen, Number(e.target.value)))}
          style={inputStyle}
        />
      </div>
      <button
        onClick={() => onZoom(start, end)}
        {...zoomEvents}
        style={{
          padding: '4px 12px', borderRadius: 6, cursor: 'pointer',
          border: `0.5px solid ${zoomH ? T.teal : T.border2}`,
          color: zoomH ? T.teal : T.mid,
          background: 'transparent', fontSize: 12,
          transition: 'color 0.15s, border-color 0.15s',
        }}
      >
        Zoom
      </button>
      <span style={{ fontSize: 11, color: T.muted }}>
        {inWindow} guide{inWindow !== 1 ? 's' : ''} in window
      </span>
    </div>
  )
}

// ─── tracks panel ─────────────────────────────────────────────────────────────

function TracksPanel({ result, seqLen, grnas, onZoom }) {
  if (!result) {
    return (
      <div style={{
        display: 'flex', alignItems: 'center', justifyContent: 'center',
        padding: '64px 0', color: T.muted, fontSize: 13,
      }}>
        Run an analysis first to see tracks
      </div>
    )
  }

  const sectionLabel = {
    fontSize: 10, color: T.muted,
    textTransform: 'uppercase', letterSpacing: '0.8px', marginBottom: 8,
  }
  const chartWrap = {
    borderRadius: 6, overflow: 'hidden',
    border: `0.5px solid ${T.border}`,
  }
  const divider = { borderTop: `0.5px solid ${T.border}` }

  return (
    <div>
      <div style={{ padding: 16 }}>
        <div style={sectionLabel}>GC% track (60 bp window)</div>
        <div style={chartWrap}><GcChart gcTrack={result.gc_track} /></div>
      </div>
      <div style={divider} />
      <div style={{ padding: 16 }}>
        <div style={sectionLabel}>PAM sites &amp; gRNA positions</div>
        <div style={chartWrap}><PositionTrack grnas={grnas} seqLen={seqLen} /></div>
      </div>
      <div style={divider} />
      <WindowSelector grnas={grnas} seqLen={seqLen} onZoom={onZoom} />
    </div>
  )
}

// ─── main page ────────────────────────────────────────────────────────────────

export default function Sandbox() {
  const { sequence, enzyme, topGuide, update: storeUpdate } = useHelixStore()
  const [loading, setLoading]         = useState(false)
  const [error, setError]             = useState(null)
  const [result, setResult]           = useState(null)
  const [activeTab, setActiveTab]     = useState('gRNA Ranking')
  const [windowStart, setWindowStart] = useState(null)
  const [windowEnd, setWindowEnd]     = useState(null)
  const [selectedGrna, setSelectedGrna]   = useState(null)
  const [showSaveModal, setShowSaveModal] = useState(false)
  const [saveName, setSaveName]           = useState('')
  const [saving, setSaving]               = useState(false)
  const [toast, setToast]                 = useState(null)

  const navigate = useNavigate()

  const [analyzeH, analyzeEvents] = useHover()
  const [exampleH, exampleEvents] = useHover()
  const [orfsH, orfsEvents]       = useHover()

  async function handleAnalyze() {
    if (!sequence.trim()) return
    setLoading(true)
    setError(null)
    setWindowStart(null)
    setWindowEnd(null)
    try {
      const data = await analyzeGrnas(sequence.trim(), enzyme, false)
      setResult(data)
      storeUpdate({ grnas: data.grnas ?? [], topGuide: data.grnas?.[0] ?? null })
    } catch (err) {
      setError(err?.response?.data?.detail ?? err.message ?? 'Analysis failed')
    } finally {
      setLoading(false)
    }
  }

  function handleZoom(start, end) {
    setWindowStart(start)
    setWindowEnd(end)
  }

  function handleView3D(grna) {
    setSelectedGrna(grna)
    setActiveTab('3D Helix')
  }

  function handleOffTarget(grna) {
    storeUpdate({ selectedGuide: grna })
    navigate('/offtarget')
  }

  function handlePrimers(grna) {
    storeUpdate({ selectedGuide: grna })
    navigate('/primers')
  }

  function handleAnimate(grna) {
    storeUpdate({ selectedGuide: grna })
    navigate('/animation')
  }

  async function handleSaveToLibrary() {
    if (!sequence.trim()) return
    setSaving(true)
    try {
      await saveSequence(saveName.trim() || 'Sandbox sequence', sequence.trim())
      setShowSaveModal(false)
      setSaveName('')
      setToast('Sequence saved to library')
      setTimeout(() => setToast(null), 2800)
    } catch {
      setToast('Save failed — try again')
      setTimeout(() => setToast(null), 2800)
    } finally {
      setSaving(false)
    }
  }

  const grnas      = result?.grnas     ?? []
  const pamCount   = result?.pam_count ?? 0
  const seqLen     = sequence.replace(/[^ACGTacgt]/g, '').length
  const offTargets = 0

  const visibleGrnas = (windowStart !== null && windowEnd !== null)
    ? grnas.filter(g => g.pos >= windowStart && g.pos <= windowEnd)
    : grnas

  const analyzeDisabled = loading || !sequence.trim()

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 16 }}>

      {/* ── sequence input bar ── */}
      <div style={{
        display: 'flex', alignItems: 'center', gap: 12,
        background: T.surface,
        borderBottom: `1px solid ${T.border}`,
        padding: '12px 16px',
      }}>
        <input
          type="text"
          value={sequence}
          onChange={e => storeUpdate({ sequence: e.target.value })}
          onKeyDown={e => e.key === 'Enter' && handleAnalyze()}
          placeholder="Paste DNA sequence (ACGT)..."
          spellCheck={false}
          style={{
            flex: 1, minWidth: 0,
            background: T.bg,
            border: `0.5px solid ${T.border2}`,
            borderRadius: 6,
            padding: '7px 12px',
            fontFamily: 'monospace', fontSize: 13,
            color: T.teal,
            outline: 'none',
          }}
        />

        <span style={{
          fontSize: 11, fontFamily: 'monospace', whiteSpace: 'nowrap',
          color: seqLen > 20 ? T.teal : T.muted,
        }}>
          {seqLen} bp
        </span>

        <select
          value={enzyme}
          onChange={e => storeUpdate({ enzyme: e.target.value })}
          style={{
            background: T.bg,
            border: `0.5px solid ${T.border2}`,
            borderRadius: 6,
            padding: '7px 8px',
            fontSize: 12, color: T.text,
            outline: 'none', cursor: 'pointer',
          }}
        >
          {ENZYMES.map(e => <option key={e} value={e}>{e}</option>)}
        </select>

        <button
          onClick={() => storeUpdate({ sequence: EXAMPLE_SEQUENCE })}
          {...exampleEvents}
          style={{
            padding: '6px 12px', borderRadius: 6, cursor: 'pointer',
            border: `0.5px solid ${exampleH ? T.teal : T.border2}`,
            color: exampleH ? T.teal : T.mid,
            background: 'transparent', fontSize: 12,
            whiteSpace: 'nowrap',
            transition: 'color 0.15s, border-color 0.15s',
          }}
        >
          Use example
        </button>

        <button
          onClick={handleAnalyze}
          disabled={analyzeDisabled}
          {...analyzeEvents}
          style={{
            padding: '6px 16px', borderRadius: 6,
            background: analyzeH && !analyzeDisabled ? '#0F6E56' : T.teal,
            color: '#04342C', fontWeight: 500, fontSize: 13,
            border: 'none',
            cursor: analyzeDisabled ? 'not-allowed' : 'pointer',
            opacity: analyzeDisabled ? 0.5 : 1,
            whiteSpace: 'nowrap',
            transition: 'background 0.15s',
          }}
        >
          {loading ? 'Analyzing…' : 'Analyze'}
        </button>

        <button
          onClick={() => navigate('/orfs')}
          {...orfsEvents}
          style={{
            padding: '6px 12px', borderRadius: 6, cursor: 'pointer',
            border: `0.5px solid ${orfsH ? T.amber : T.border2}`,
            color: orfsH ? T.amber : T.mid,
            background: 'transparent', fontSize: 12,
            whiteSpace: 'nowrap',
            transition: 'color 0.15s, border-color 0.15s',
          }}
        >
          View ORFs →
        </button>

        <button
          onClick={() => { setSaveName(''); setShowSaveModal(true) }}
          disabled={!sequence.trim()}
          style={{
            padding: '6px 12px', borderRadius: 6, cursor: sequence.trim() ? 'pointer' : 'not-allowed',
            border: `0.5px solid ${T.border2}`,
            color: T.mid, background: 'transparent', fontSize: 12,
            whiteSpace: 'nowrap', opacity: sequence.trim() ? 1 : 0.4,
            transition: 'color 0.15s, border-color 0.15s',
          }}
          onMouseEnter={e => { if (sequence.trim()) { e.currentTarget.style.color = T.teal; e.currentTarget.style.borderColor = T.teal } }}
          onMouseLeave={e => { e.currentTarget.style.color = T.mid; e.currentTarget.style.borderColor = T.border2 }}
        >
          Save to library
        </button>
      </div>

      {/* error bar */}
      {error && (
        <div style={{
          display: 'flex', alignItems: 'center', gap: 8,
          padding: '8px 16px',
          background: '#1a0808',
          border: '0.5px solid #4a1010',
          borderRadius: 6,
          color: '#f09595', fontSize: 12,
        }}>
          <span style={{ fontWeight: 700 }}>Error:</span>
          {error}
        </div>
      )}

      {/* ── stat cards ── */}
      <div style={{ display: 'flex', gap: 12 }}>
        <StatCard label="PAM sites"       value={pamCount}     color={T.teal}  />
        <StatCard label="gRNAs found"     value={grnas.length} color={T.amber} />
        <StatCard label="Sequence length" value={seqLen || 0}  color={T.text}  />
        <StatCard label="Off-target hits" value={offTargets}   color={T.teal}  />
      </div>

      {/* ── tab panel ── */}
      <div style={{
        background: T.surface,
        border: `0.5px solid ${T.border}`,
        borderRadius: 8,
        overflow: 'hidden',
      }}>
        {/* tab bar */}
        <div style={{
          display: 'flex',
          background: T.surface,
          borderBottom: `0.5px solid ${T.border}`,
        }}>
          {TABS.map(tab => (
            <button
              key={tab}
              onClick={() => setActiveTab(tab)}
              style={{
                padding: '8px 14px', fontSize: 12, fontWeight: 400,
                color: activeTab === tab ? T.amber : T.muted,
                background: 'transparent', border: 'none',
                borderBottom: `2px solid ${activeTab === tab ? T.amber : 'transparent'}`,
                cursor: 'pointer',
                transition: 'color 0.15s',
                whiteSpace: 'nowrap',
              }}
            >
              {tab}
            </button>
          ))}
        </div>

        {/* tab content */}
        <div>
          {activeTab === 'gRNA Ranking' && (
            <>
              <GrnaTable
                grnas={visibleGrnas}
                loading={loading}
                emptyMessage={result ? 'No guides in this window' : 'Run an analysis to see gRNA rankings'}
                onView3D={handleView3D}
                onOffTarget={handleOffTarget}
                onPrimers={handlePrimers}
                onAnimate={handleAnimate}
              />
              {grnas.length > 0 && (
                <div style={{ padding: '12px 0 4px', display: 'flex', justifyContent: 'flex-end' }}>
                  <button
                    onClick={() => navigate('/game')}
                    style={{ background: 'rgba(0,40,20,0.8)', border: '1px solid rgba(0,255,136,0.3)', borderRadius: 6, color: '#00ff88', padding: '7px 16px', fontSize: 12, fontWeight: 600, cursor: 'pointer', fontFamily: 'monospace', boxShadow: '0 0 10px rgba(0,255,136,0.15)' }}
                    onMouseEnter={e => { e.currentTarget.style.background = '#003318' }}
                    onMouseLeave={e => { e.currentTarget.style.background = 'rgba(0,40,20,0.8)' }}
                  >
                    🎮 Play in game mode →
                  </button>
                </div>
              )}
              <ModelStrip />
            </>
          )}

          {activeTab === '2D Tracks' && (
            <TracksPanel result={result} seqLen={seqLen} grnas={grnas} onZoom={handleZoom} />
          )}

          {activeTab === '3D Helix' && (
            <div style={{ padding: 16 }}>
              <DnaHelix3D
                sequence={sequence}
                grnas={grnas}
                orfs={[]}
                selectedGrna={selectedGrna}
              />
            </div>
          )}

          {activeTab !== 'gRNA Ranking' && activeTab !== '2D Tracks' && activeTab !== '3D Helix' && (
            <div style={{
              display: 'flex', alignItems: 'center', justifyContent: 'center',
              padding: '64px 0', color: T.muted, fontSize: 13,
            }}>
              {activeTab} — coming soon
            </div>
          )}
        </div>
      </div>

      {/* ── Save to library modal ── */}
      {showSaveModal && (
        <div
          onClick={() => setShowSaveModal(false)}
          style={{
            position: 'fixed', inset: 0, background: 'rgba(0,0,0,0.6)',
            display: 'flex', alignItems: 'center', justifyContent: 'center',
            zIndex: 1000,
          }}
        >
          <div
            onClick={e => e.stopPropagation()}
            style={{
              background: T.surface, border: `0.5px solid ${T.border}`,
              borderRadius: 10, padding: 24, width: 340,
              display: 'flex', flexDirection: 'column', gap: 14,
            }}
          >
            <div style={{ fontSize: 14, fontWeight: 500, color: T.text }}>
              Save sequence to library
            </div>
            <input
              autoFocus
              value={saveName}
              onChange={e => setSaveName(e.target.value)}
              onKeyDown={e => e.key === 'Enter' && handleSaveToLibrary()}
              placeholder="Sequence name (optional)"
              style={{
                background: T.bg, border: `0.5px solid ${T.border2}`, borderRadius: 6,
                padding: '8px 12px', fontSize: 13, color: T.text,
                outline: 'none', fontFamily: 'monospace',
              }}
            />
            <div style={{ fontSize: 11, color: T.muted }}>
              {seqLen.toLocaleString()} bp will be saved
            </div>
            <div style={{ display: 'flex', gap: 8, justifyContent: 'flex-end' }}>
              <button
                onClick={() => setShowSaveModal(false)}
                style={{
                  padding: '7px 16px', borderRadius: 6, fontSize: 12,
                  border: `0.5px solid ${T.border2}`, color: T.mid,
                  background: 'transparent', cursor: 'pointer',
                }}
              >
                Cancel
              </button>
              <button
                onClick={handleSaveToLibrary}
                disabled={saving}
                style={{
                  padding: '7px 16px', borderRadius: 6, fontSize: 12,
                  background: T.teal, color: '#04342C',
                  border: 'none', fontWeight: 500,
                  cursor: saving ? 'not-allowed' : 'pointer',
                  opacity: saving ? 0.6 : 1,
                }}
              >
                {saving ? 'Saving…' : 'Save'}
              </button>
            </div>
          </div>
        </div>
      )}

      {/* ── Toast notification ── */}
      {toast && (
        <div style={{
          position: 'fixed', bottom: 24, right: 24, zIndex: 2000,
          background: toast.includes('failed') ? '#3D1515' : '#0F2E1F',
          border: `0.5px solid ${toast.includes('failed') ? '#F09595' : T.teal}`,
          borderRadius: 8, padding: '10px 16px',
          color: toast.includes('failed') ? '#F09595' : T.teal,
          fontSize: 13, fontWeight: 500,
          boxShadow: '0 4px 20px rgba(0,0,0,0.4)',
          animation: 'fadeIn 0.2s ease',
        }}>
          {toast}
        </div>
      )}
      <style>{`@keyframes fadeIn{from{opacity:0;transform:translateY(6px)}to{opacity:1;transform:translateY(0)}}`}</style>

    </div>
  )
}
