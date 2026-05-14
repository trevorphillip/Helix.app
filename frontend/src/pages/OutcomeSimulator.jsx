import { useState, useEffect } from 'react'
import { useNavigate } from 'react-router-dom'
import { useHelixStore } from '../store.jsx'
import { simulateOutcome } from '../api.js'

// ─── design tokens ────────────────────────────────────────────────────────────

const T = {
  bg:      '#020a06',
  surface: '#0a1f10',
  deep:    '#051209',
  green:   '#00ff88',
  amber:   '#ffaa00',
  red:     '#ff2244',
  purple:  '#aa88ff',
  text:    '#c8f5d8',
  dim:     '#4a8a5a',
  muted:   '#1a4a2a',
  border:  'rgba(0,255,136,0.12)',
  border2: 'rgba(0,255,136,0.3)',
}

// ─── helpers ──────────────────────────────────────────────────────────────────

function fsColor(pct) {
  if (pct > 50) return T.red
  if (pct > 30) return T.amber
  return T.green
}

function deletionColor(size) {
  const t   = Math.min(Math.abs(size) / 20, 1)
  const r   = 255
  const g   = Math.round(170 - 128 * t)
  const b   = Math.round(68 * t)
  return `rgb(${r},${g},${b})`
}

function sizeLabel(item) {
  if (item.type === 'hdr')       return 'full edit'
  if (item.type === 'insertion') return `+${item.size}bp`
  return `${item.size}bp`
}

// ─── distribution chart ───────────────────────────────────────────────────────

function DistributionChart({ distribution, mostCommonSize }) {
  const [hovered, setHovered]   = useState(null)
  const [tipPos,  setTipPos]    = useState({ x: 0, y: 0 })

  // build size → item lookup
  const lookup = {}
  distribution.forEach(d => { lookup[d.size] = d })

  // sizes -20 to +5 on x axis (HDR at 0)
  const SIZES = []
  for (let s = -20; s <= 5; s++) SIZES.push(s)

  const filtered = SIZES.map(s => lookup[s] || null)
  const maxProb  = Math.max(...distribution.map(d => d.probability), 0.001)

  // chart geometry
  const VW    = 580
  const VH    = 200
  const ML    = 44   // left margin
  const MR    = 16
  const MT    = 24
  const MB    = 46
  const CW    = VW - ML - MR
  const CH    = VH - MT - MB
  const BW    = CW / SIZES.length   // slot width per size
  const GAP   = 2
  const BARW  = Math.max(BW - GAP, 2)

  function barX(idx)   { return ML + idx * BW + GAP / 2 }
  function barH(prob)  { return (prob / maxProb) * CH }
  function barY(prob)  { return MT + CH - barH(prob) }

  function handleMouseEnter(e, item) {
    const rect = e.currentTarget.closest('svg').getBoundingClientRect()
    setHovered(item)
    setTipPos({ x: e.clientX - rect.left, y: e.clientY - rect.top })
  }

  const zeroIdx = SIZES.indexOf(0)
  const zeroX   = ML + zeroIdx * BW + BW / 2

  // y-axis tick values
  const yTicks = [0, 5, 10, 15, 20].filter(p => p / 100 <= maxProb * 1.1)

  return (
    <div style={{ position: 'relative' }}>
      <svg
        viewBox={`0 0 ${VW} ${VH}`}
        style={{ width: '100%', height: VH, background: T.bg, borderRadius: 6, overflow: 'visible' }}
        onMouseLeave={() => setHovered(null)}
      >
        {/* grid lines */}
        {yTicks.map(p => {
          const frac = (p / 100) / maxProb
          if (frac > 1) return null
          const y = MT + CH - frac * CH
          return (
            <line key={p}
              x1={ML} y1={y} x2={VW - MR} y2={y}
              stroke="rgba(0,255,136,0.06)" strokeWidth="1"
            />
          )
        })}

        {/* x axis */}
        <line x1={ML} y1={MT + CH} x2={VW - MR} y2={MT + CH}
          stroke="rgba(0,255,136,0.2)" strokeWidth="1" />

        {/* cut site vertical */}
        <line x1={zeroX} y1={MT} x2={zeroX} y2={MT + CH}
          stroke="rgba(255,170,0,0.35)" strokeWidth="1"
          strokeDasharray="4,3"
        />
        <text x={zeroX} y={MT - 6} textAnchor="middle"
          fontSize="8" fill={T.amber} fontFamily="monospace">CUT</text>

        {/* bars */}
        {filtered.map((item, idx) => {
          if (!item) {
            // empty slot — still render x label at key intervals
            return null
          }
          const x   = barX(idx)
          const bh  = barH(item.probability)
          const by  = barY(item.probability)
          const col = item.type === 'hdr' ? T.purple
                    : item.type === 'insertion' ? T.green
                    : deletionColor(item.size)
          const isTop  = item.size === mostCommonSize
          const isHov  = hovered?.size === item.size

          return (
            <g key={item.size}
              onMouseEnter={e => handleMouseEnter(e, item)}
              style={{ cursor: 'pointer' }}
            >
              <rect
                x={x} y={by} width={BARW} height={bh}
                fill={col}
                opacity={isTop ? 1.0 : 0.75}
                stroke={item.frameshift ? 'rgba(255,255,255,0.25)' : isTop ? col : 'none'}
                strokeWidth={item.frameshift ? 0.8 : isTop ? 1.5 : 0}
                strokeDasharray={item.frameshift ? '3,2' : 'none'}
                rx="1"
              />
              {isTop && bh > 8 && (
                <text x={x + BARW / 2} y={by - 4}
                  textAnchor="middle" fontSize="7"
                  fill={col} fontFamily="monospace">
                  {(item.probability * 100).toFixed(1)}%
                </text>
              )}
              {item.frameshift && bh > 14 && (
                <text x={x + BARW / 2} y={MT + CH + 12}
                  textAnchor="middle" fontSize="7"
                  fill={T.muted} fontFamily="monospace">FS</text>
              )}
            </g>
          )
        })}

        {/* x axis size labels at key intervals */}
        {[-20, -15, -10, -5, -1, 0, 3, 5].map(s => {
          const idx = SIZES.indexOf(s)
          if (idx < 0) return null
          const x = ML + idx * BW + BW / 2
          return (
            <text key={s} x={x} y={MT + CH + 22}
              textAnchor="middle" fontSize="8"
              fill={s === 0 ? T.amber : T.muted}
              fontFamily="monospace">
              {s > 0 ? `+${s}` : s}
            </text>
          )
        })}

        {/* y axis labels */}
        {yTicks.map(p => {
          const frac = (p / 100) / maxProb
          if (frac > 1.05) return null
          const y = MT + CH - frac * CH
          return (
            <text key={p} x={ML - 6} y={y + 3}
              textAnchor="end" fontSize="8"
              fill={T.muted} fontFamily="monospace">
              {p}%
            </text>
          )
        })}

        {/* x axis label */}
        <text x={ML + CW / 2} y={VH - 2}
          textAnchor="middle" fontSize="8"
          fill={T.muted} fontFamily="monospace">
          indel size (bp)
        </text>
      </svg>

      {/* hover tooltip */}
      {hovered && (
        <div style={{
          position:    'absolute',
          top:         Math.min(tipPos.y + 8, VH - 110),
          left:        Math.min(tipPos.x + 10, 380),
          background:  'rgba(2,10,6,0.96)',
          border:      `1px solid ${T.border2}`,
          borderRadius: 6,
          padding:     '8px 10px',
          pointerEvents: 'none',
          zIndex:      10,
          minWidth:    160,
        }}>
          <div style={{ fontFamily: 'monospace', fontSize: 10, color: T.muted, marginBottom: 4 }}>
            {hovered.type.toUpperCase()}
            <span style={{ color: T.amber, marginLeft: 6 }}>{sizeLabel(hovered)}</span>
          </div>
          <div style={{ fontFamily: 'monospace', fontSize: 13, color: T.green, fontWeight: 700, marginBottom: 2 }}>
            {(hovered.probability * 100).toFixed(2)}%
          </div>
          <div style={{ fontSize: 10, color: hovered.frameshift ? T.red : T.dim }}>
            {hovered.frameshift ? 'FRAMESHIFT' : 'In-frame'}
          </div>
          <div style={{ fontFamily: 'monospace', fontSize: 9, color: T.muted, marginTop: 4 }}>
            {hovered.sequence_preview}
          </div>
        </div>
      )}

      {/* legend */}
      <div style={{ display: 'flex', gap: 16, marginTop: 6, flexWrap: 'wrap' }}>
        {[
          { color: '#ff2244', label: 'Deletion' },
          { color: '#00ff88', label: 'Insertion' },
          { color: '#aa88ff', label: 'HDR' },
        ].map(({ color, label }) => (
          <div key={label} style={{ display: 'flex', alignItems: 'center', gap: 5, fontSize: 10, color: T.muted, fontFamily: 'monospace' }}>
            <span style={{ width: 10, height: 10, background: color, display: 'inline-block', borderRadius: 2, opacity: 0.8 }} />
            {label}
          </div>
        ))}
        <div style={{ display: 'flex', alignItems: 'center', gap: 5, fontSize: 10, color: T.muted, fontFamily: 'monospace' }}>
          <span style={{ width: 10, height: 10, border: '1px dashed rgba(255,255,255,0.3)', display: 'inline-block', borderRadius: 2 }} />
          Frameshift
        </div>
      </div>
    </div>
  )
}

// ─── summary card ─────────────────────────────────────────────────────────────

function SummaryCard({ label, value, color, sub }) {
  return (
    <div style={{
      flex:         1,
      background:   T.surface,
      border:       `1px solid ${T.border}`,
      borderRadius: 6,
      padding:      '12px 14px',
      minWidth:     0,
    }}>
      <div style={{
        fontFamily:   'monospace',
        fontSize:     22,
        fontWeight:   700,
        color,
        marginBottom: 4,
        textShadow:   `0 0 12px ${color}55`,
      }}>
        {value}
      </div>
      <div style={{ fontSize: 9, color: T.muted, textTransform: 'uppercase', letterSpacing: '1.5px', fontFamily: 'monospace' }}>
        {label}
      </div>
      {sub && <div style={{ fontSize: 9, color: T.dim, marginTop: 2, fontFamily: 'monospace' }}>{sub}</div>}
    </div>
  )
}

// ─── outcome simulator ────────────────────────────────────────────────────────

export default function OutcomeSimulator() {
  const { sequence, grnas, selectedGuide, update: storeUpdate } = useHelixStore()
  const navigate = useNavigate()

  const [cutPosition,   setCutPosition]   = useState(0)
  const [cellType,      setCellType]      = useState('dividing')
  const [hasDonor,      setHasDonor]      = useState(false)
  const [nSims,         setNSims]         = useState(10000)
  const [result,        setResult]        = useState(null)
  const [loading,       setLoading]       = useState(false)
  const [error,         setError]         = useState(null)
  const [selGrnaIdx,    setSelGrnaIdx]    = useState(-1)
  const [sciOpen,       setSciOpen]       = useState(false)

  // pre-fill from store selectedGuide
  useEffect(() => {
    if (selectedGuide && grnas.length > 0) {
      const idx = grnas.findIndex(g => g.pos === selectedGuide.pos)
      if (idx >= 0) {
        setSelGrnaIdx(idx)
        setCutPosition(selectedGuide.pos + 17)
      }
    }
  }, [selectedGuide, grnas])

  function handleGrnaChange(e) {
    const idx = parseInt(e.target.value, 10)
    setSelGrnaIdx(idx)
    if (grnas[idx]) {
      setCutPosition(grnas[idx].pos + 17)
      storeUpdate({ selectedGuide: grnas[idx] })
    }
  }

  async function runSim() {
    if (!sequence.trim()) return
    setLoading(true)
    setError(null)
    try {
      const data = await simulateOutcome(sequence, cutPosition, nSims, cellType, hasDonor)
      setResult(data)
    } catch (e) {
      setError(e?.response?.data?.detail || 'Simulation failed — check API connection')
    } finally {
      setLoading(false)
    }
  }

  const inp = {
    background:   T.deep,
    border:       `1px solid rgba(0,255,136,0.15)`,
    color:        T.green,
    fontFamily:   'monospace',
    borderRadius: 4,
    padding:      '6px 10px',
    fontSize:     12,
    outline:      'none',
  }

  const label = {
    fontSize:      9,
    color:         T.muted,
    textTransform: 'uppercase',
    letterSpacing: '1.5px',
    fontFamily:    'monospace',
    marginBottom:  5,
    display:       'block',
  }

  const panel = {
    background:   T.surface,
    border:       `1px solid ${T.border}`,
    borderRadius: 8,
    padding:      '14px 16px',
    marginTop:    12,
  }

  const cellBtn = (active) => ({
    padding:      '5px 14px',
    borderRadius: 4,
    fontSize:     11,
    fontFamily:   'monospace',
    cursor:       'pointer',
    border:       `1px solid ${active ? T.green : T.border2}`,
    background:   active ? T.green : 'transparent',
    color:        active ? '#020a06' : T.green,
    fontWeight:   active ? 700 : 400,
    transition:   'all 0.15s',
  })

  if (!sequence) {
    return (
      <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center', minHeight: 400, gap: 12 }}>
        <div style={{ fontFamily: 'monospace', fontSize: 13, color: T.muted, letterSpacing: 2 }}>// NO SEQUENCE LOADED</div>
        <div style={{ fontSize: 11, color: T.muted }}>Run an analysis in Sandbox first</div>
        <button
          onClick={() => navigate('/')}
          style={{ background: T.green, color: '#020a06', border: 'none', borderRadius: 6, padding: '8px 20px', fontWeight: 700, cursor: 'pointer', fontSize: 12, fontFamily: 'monospace' }}
        >
          Go to Sandbox →
        </button>
      </div>
    )
  }

  const fs   = result?.summary?.frameshift_percent ?? 0
  const top  = result?.summary

  return (
    <div style={{ fontFamily: 'monospace', color: T.text, maxWidth: 900, margin: '0 auto' }}>

      {/* ── header ── */}
      <div style={{ fontSize: 14, color: T.green, letterSpacing: '2px', fontWeight: 700 }}>
        // OUTCOME SIMULATOR
      </div>
      <div style={{ fontSize: 11, color: T.muted, marginTop: 3 }}>
        Monte Carlo CRISPR repair prediction
      </div>
      <div style={{ fontSize: 10, color: T.muted, marginTop: 2 }}>
        Model: Helix inDelphi-simplified v1.0 — based on Shen et al. 2018 Nature Biotechnology
      </div>

      {/* ── controls ── */}
      <div style={panel}>

        <div style={{ display: 'flex', gap: 16, flexWrap: 'wrap', marginBottom: 14 }}>

          {/* gRNA selector */}
          <div style={{ flex: 2, minWidth: 200 }}>
            <span style={label}>// Select gRNA</span>
            {grnas.length > 0 ? (
              <select
                value={selGrnaIdx >= 0 ? selGrnaIdx : ''}
                onChange={handleGrnaChange}
                style={{ ...inp, width: '100%' }}
              >
                <option value="" disabled>— select a guide —</option>
                {grnas.slice(0, 30).map((g, i) => (
                  <option key={i} value={i}>
                    {`bp${g.pos} | ${(g.guide || '').substring(0, 10)}... | score ${(g.score ?? 0).toFixed(3)}`}
                  </option>
                ))}
              </select>
            ) : (
              <div style={{ fontSize: 11, color: T.muted, padding: '6px 0' }}>
                No gRNAs — run Sandbox analysis first
              </div>
            )}
          </div>

          {/* cut position */}
          <div style={{ flex: 1, minWidth: 120 }}>
            <span style={label}>// Cut Position (bp)</span>
            <input
              type="number"
              value={cutPosition}
              onChange={e => setCutPosition(parseInt(e.target.value, 10) || 0)}
              style={{ ...inp, width: '100%', boxSizing: 'border-box' }}
            />
          </div>
        </div>

        {/* cell type */}
        <div style={{ marginBottom: 14 }}>
          <span style={label}>// Cell Type</span>
          <div style={{ display: 'flex', gap: 8, alignItems: 'center' }}>
            <button style={cellBtn(cellType === 'dividing')}   onClick={() => setCellType('dividing')}>
              Dividing cells
            </button>
            <button style={cellBtn(cellType === 'non-dividing')} onClick={() => setCellType('non-dividing')}>
              Non-dividing
            </button>
            <span style={{ fontSize: 10, color: T.muted, marginLeft: 4 }}>
              HDR only works in dividing cells
            </span>
          </div>
        </div>

        {/* simulations slider */}
        <div style={{ marginBottom: 14 }}>
          <span style={label}>// Simulations: {nSims.toLocaleString()}</span>
          <input
            type="range"
            min={1000} max={10000} step={1000}
            value={nSims}
            onChange={e => setNSims(parseInt(e.target.value, 10))}
            style={{ width: '100%', accentColor: T.green }}
          />
          <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: 9, color: T.muted }}>
            <span>1,000</span><span>10,000</span>
          </div>
        </div>

        {/* HDR toggle */}
        <div style={{ marginBottom: 14, display: 'flex', alignItems: 'center', gap: 8 }}>
          <input
            type="checkbox"
            id="hdr-toggle"
            checked={hasDonor}
            onChange={e => setHasDonor(e.target.checked)}
            style={{ accentColor: T.green }}
          />
          <label htmlFor="hdr-toggle" style={{ fontSize: 11, color: T.dim, cursor: 'pointer' }}>
            Include HDR template (dividing cells only)
          </label>
        </div>

        {/* run button */}
        <button
          onClick={runSim}
          disabled={loading}
          style={{
            width:        '100%',
            padding:      '10px',
            background:   loading ? T.surface : T.green,
            color:        loading ? T.dim : '#020a06',
            border:       `1px solid ${loading ? T.border : T.green}`,
            borderRadius: 4,
            fontFamily:   'monospace',
            fontWeight:   700,
            fontSize:     12,
            letterSpacing:'2px',
            cursor:       loading ? 'not-allowed' : 'pointer',
            boxShadow:    loading ? 'none' : '0 0 20px rgba(0,255,136,0.3)',
            transition:   'all 0.2s',
          }}
        >
          {loading ? `SIMULATING ${nSims.toLocaleString()} EVENTS...` : '▶ RUN SIMULATION'}
        </button>

        {error && (
          <div style={{
            marginTop:    10,
            background:   'rgba(255,34,68,0.08)',
            border:       '1px solid rgba(255,34,68,0.3)',
            borderRadius: 4,
            padding:      '8px 10px',
            fontSize:     11,
            color:        T.red,
          }}>
            {error}
          </div>
        )}
      </div>

      {/* ── results ── */}
      {result && (
        <>
          {/* summary cards */}
          <div style={{ display: 'flex', gap: 10, marginTop: 16, flexWrap: 'wrap' }}>
            <SummaryCard
              label="NHEJ Repair"
              value={`${top.nhej_percent.toFixed(1)}%`}
              color={T.amber}
            />
            <SummaryCard
              label="HDR Efficiency"
              value={`${top.hdr_percent.toFixed(1)}%`}
              color={hasDonor ? T.green : T.muted}
            />
            <SummaryCard
              label="Frameshift Rate"
              value={`${top.frameshift_percent.toFixed(1)}%`}
              color={fsColor(fs)}
            />
            <SummaryCard
              label={`Top outcome (${top.most_common_prob}%)`}
              value={top.most_common_size > 0 ? `+${top.most_common_size}bp` : `${top.most_common_size}bp`}
              color={T.amber}
              sub={top.most_common_outcome}
            />
          </div>

          {/* distribution chart */}
          <div style={{ ...panel, marginTop: 16 }}>
            <div style={{ fontSize: 10, color: T.green, letterSpacing: '2px', marginBottom: 12, fontWeight: 700 }}>
              // INDEL DISTRIBUTION
            </div>
            <DistributionChart
              distribution={result.distribution}
              mostCommonSize={top.most_common_size}
            />
          </div>

          {/* top outcomes table */}
          <div style={{ ...panel, marginTop: 16 }}>
            <div style={{ fontSize: 10, color: T.green, letterSpacing: '2px', marginBottom: 12, fontWeight: 700 }}>
              // TOP REPAIR OUTCOMES
            </div>
            <div style={{ overflowX: 'auto' }}>
              <table style={{ width: '100%', borderCollapse: 'collapse' }}>
                <thead>
                  <tr style={{ borderBottom: `1px solid rgba(0,255,136,0.1)` }}>
                    {['Rank', 'Type', 'Size', 'Probability', 'Frameshift', 'Sequence'].map(h => (
                      <th key={h} style={{
                        padding:       '6px 10px',
                        fontSize:      9,
                        color:         T.muted,
                        textTransform: 'uppercase',
                        letterSpacing: '1px',
                        textAlign:     'left',
                        fontFamily:    'monospace',
                        fontWeight:    500,
                      }}>{h}</th>
                    ))}
                  </tr>
                </thead>
                <tbody>
                  {result.top_outcomes.map((item, i) => (
                    <tr key={i}
                      style={{ borderBottom: `1px solid rgba(0,255,136,0.06)` }}
                      onMouseEnter={e => { e.currentTarget.style.background = 'rgba(0,255,136,0.02)' }}
                      onMouseLeave={e => { e.currentTarget.style.background = 'transparent' }}
                    >
                      <td style={{ padding: '8px 10px', fontSize: 12, color: T.muted }}>{i + 1}</td>
                      <td style={{ padding: '8px 10px' }}>
                        <span style={{
                          padding:      '2px 6px',
                          borderRadius: 3,
                          fontSize:     10,
                          fontFamily:   'monospace',
                          background:   item.type === 'deletion'  ? 'rgba(255,34,68,0.1)'
                                      : item.type === 'insertion' ? 'rgba(0,255,136,0.1)'
                                      : 'rgba(170,136,255,0.1)',
                          color:        item.type === 'deletion'  ? T.red
                                      : item.type === 'insertion' ? T.green
                                      : T.purple,
                          border:       `1px solid ${item.type === 'deletion'  ? 'rgba(255,34,68,0.3)'
                                        : item.type === 'insertion' ? 'rgba(0,255,136,0.3)'
                                        : 'rgba(170,136,255,0.3)'}`,
                        }}>
                          {item.type}
                        </span>
                      </td>
                      <td style={{ padding: '8px 10px', fontFamily: 'monospace', fontSize: 12, color: T.amber, fontWeight: 700 }}>
                        {sizeLabel(item)}
                      </td>
                      <td style={{ padding: '8px 10px' }}>
                        <div style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
                          <div style={{
                            width:        `${Math.min(item.probability * 400, 80)}px`,
                            height:       3,
                            background:   T.green,
                            borderRadius: 2,
                            flexShrink:   0,
                          }} />
                          <span style={{ fontSize: 11, color: T.green, fontFamily: 'monospace' }}>
                            {(item.probability * 100).toFixed(1)}%
                          </span>
                        </div>
                      </td>
                      <td style={{ padding: '8px 10px' }}>
                        <span style={{
                          padding:      '2px 6px',
                          borderRadius: 3,
                          fontSize:     9,
                          fontFamily:   'monospace',
                          fontWeight:   700,
                          background:   item.frameshift ? 'rgba(255,34,68,0.1)'   : 'rgba(0,255,136,0.05)',
                          color:        item.frameshift ? T.red                    : T.muted,
                          border:       `1px solid ${item.frameshift ? 'rgba(255,34,68,0.3)' : 'transparent'}`,
                        }}>
                          {item.frameshift ? 'FS' : 'IF'}
                        </span>
                      </td>
                      <td style={{ padding: '8px 10px', fontFamily: 'monospace', fontSize: 10, color: T.dim }}>
                        {item.sequence_preview}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>

          {/* microhomology panel */}
          <div style={{ ...panel, marginTop: 16 }}>
            <div style={{ fontSize: 10, color: T.green, letterSpacing: '2px', marginBottom: 10, fontWeight: 700 }}>
              // MICROHOMOLOGY ANALYSIS
            </div>
            {result.microhomology.length > 0 ? (
              <>
                <div style={{ fontSize: 11, color: T.dim, marginBottom: 10 }}>
                  Microhomology sequences detected — these drive deletion patterns through MMEJ
                </div>
                <div style={{ display: 'flex', flexDirection: 'column', gap: 6 }}>
                  {result.microhomology.slice(0, 5).map((mh, i) => (
                    <div key={i} style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
                      <span style={{
                        fontFamily:   'monospace',
                        fontSize:     12,
                        color:        T.green,
                        background:   T.deep,
                        padding:      '3px 8px',
                        borderRadius: 3,
                        border:       `1px solid rgba(0,255,136,0.15)`,
                        letterSpacing: '2px',
                      }}>
                        {mh.sequence}
                      </span>
                      <span style={{ fontSize: 10, color: T.muted }}>
                        Length: <span style={{ color: T.amber }}>{mh.length}nt</span>
                      </span>
                      <span style={{ fontSize: 10, color: T.muted }}>
                        GC: <span style={{ color: T.dim }}>{(mh.gc_content * 100).toFixed(0)}%</span>
                      </span>
                      <span style={{ fontSize: 10, color: T.muted }}>
                        pos +{mh.position}
                      </span>
                    </div>
                  ))}
                </div>
              </>
            ) : (
              <div style={{ fontSize: 11, color: T.muted }}>
                No significant microhomology detected
              </div>
            )}
          </div>

          {/* scientific note */}
          <div style={{ marginTop: 16 }}>
            <button
              onClick={() => setSciOpen(v => !v)}
              style={{
                background:   'transparent',
                border:       'none',
                color:        T.muted,
                fontFamily:   'monospace',
                fontSize:     10,
                letterSpacing:'1px',
                cursor:       'pointer',
                padding:      '4px 0',
                textTransform:'uppercase',
              }}
            >
              // ABOUT THIS MODEL {sciOpen ? '▲' : '▼'}
            </button>
            {sciOpen && (
              <div style={{
                background:   T.deep,
                border:       `1px solid rgba(0,255,136,0.08)`,
                borderRadius: 6,
                padding:      '14px 16px',
                marginTop:    6,
                fontSize:     11,
                color:        T.muted,
                lineHeight:   1.8,
              }}>
                <p style={{ margin: '0 0 10px' }}>
                  <span style={{ color: T.green }}>NHEJ</span> (Non-Homologous End Joining): The primary repair pathway after a double-strand break.
                  Fast but error-prone — introduces random insertions and deletions at the cut site. Active in all cell types.
                </p>
                <p style={{ margin: '0 0 10px' }}>
                  <span style={{ color: T.purple }}>HDR</span> (Homology Directed Repair): Precise repair using a provided DNA template.
                  Only active in dividing cells (S/G2 phase). Efficiency is much lower than NHEJ. Requires an HDR donor template.
                </p>
                <p style={{ margin: '0 0 10px' }}>
                  <span style={{ color: T.red }}>Frameshift</span>: When an indel size is not divisible by 3 it shifts the reading frame,
                  usually destroying gene function. This is the desired outcome for gene knockout experiments.
                </p>
                <p style={{ margin: '0 0 10px' }}>
                  <span style={{ color: T.amber }}>Microhomology</span>: Short repeated sequences flanking the cut site drive specific deletion patterns
                  through MMEJ (Microhomology-Mediated End Joining). Longer MH sequences with higher GC content produce more predictable deletions.
                </p>
                <p style={{ margin: 0, color: T.dim }}>
                  Reference: Shen MW et al. <em>Predictable and programmable DNA deletions using CRISPR/Cas nucleases.</em> Nature Biotechnology (2018). DOI: 10.1038/nbt.4194
                </p>
              </div>
            )}
          </div>
        </>
      )}
    </div>
  )
}
