import { useState } from 'react'
import { findOffTargets } from '../api'
import { useHelixStore } from '../store.jsx'

const T = {
  bg:      '#0f1117',
  surface: '#151821',
  border:  '#1e2130',
  border2: '#2a2e3e',
  teal:    '#1D9E75',
  tealBg:  '#085041',
  tealFg:  '#5DCAA5',
  amber:   '#EF9F27',
  amberBg: '#633806',
  text:    '#e8e6df',
  muted:   '#5F5E5A',
  mid:     '#888780',
  red:     '#F09595',
  redBg:   '#6B1D1D',
}

function useHover() {
  const [h, setH] = useState(false)
  return [h, { onMouseEnter: () => setH(true), onMouseLeave: () => setH(false) }]
}

function RiskBadge({ risk }) {
  const s = risk === 'high'
    ? { background: T.redBg,   color: T.red   }
    : risk === 'medium'
    ? { background: T.amberBg, color: '#FAC775' }
    : { background: T.tealBg,  color: T.tealFg }
  return (
    <span style={{ ...s, padding: '2px 8px', borderRadius: 4, fontSize: 10, fontWeight: 700, textTransform: 'uppercase' }}>
      {risk}
    </span>
  )
}

function StatCard({ label, value, color }) {
  return (
    <div style={{
      flex: 1, background: T.surface, border: `0.5px solid ${T.border}`,
      borderRadius: 8, padding: '12px 14px',
    }}>
      <div style={{ color, fontSize: 22, fontWeight: 500, fontFamily: 'monospace' }}>{value}</div>
      <div style={{ color: T.muted, fontSize: 10, textTransform: 'uppercase', letterSpacing: '0.8px', marginTop: 4 }}>
        {label}
      </div>
    </div>
  )
}

// ─── mismatch heatmap ─────────────────────────────────────────────────────────

function MismatchHeatmap({ sites, guide }) {
  const [showAll, setShowAll] = useState(false)
  const rows = showAll ? sites : sites.slice(0, 10)

  return (
    <div style={{ background: T.surface, border: `0.5px solid ${T.border}`, borderRadius: 8, overflow: 'hidden' }}>
      <div style={{
        padding: '8px 16px', borderBottom: `0.5px solid ${T.border}`,
        display: 'flex', alignItems: 'center', justifyContent: 'space-between',
      }}>
        <span style={{ fontSize: 10, color: T.muted, textTransform: 'uppercase', letterSpacing: '0.8px' }}>
          Mismatch Position Heatmap
        </span>
        <div style={{ display: 'flex', gap: 12, fontSize: 10, color: T.muted, alignItems: 'center' }}>
          <span><span style={{ color: T.red }}>■</span> Seed mismatch</span>
          <span><span style={{ color: '#FAC775' }}>■</span> Distal mismatch</span>
        </div>
      </div>

      <div style={{ padding: '12px 16px', overflowX: 'auto' }}>
        {/* Column headers */}
        <div style={{ display: 'flex', gap: 1, marginBottom: 4, paddingLeft: 40 }}>
          {/* Seed label */}
          <div style={{ display: 'flex', gap: 1, position: 'relative', flex: '0 0 auto' }}>
            {Array.from({ length: 12 }, (_, i) => (
              <div key={i} style={{
                width: 18, height: 14, display: 'flex', alignItems: 'center', justifyContent: 'center',
                fontSize: 8, color: T.muted, fontFamily: 'monospace',
                background: 'rgba(29,158,117,0.07)', borderRadius: 2,
              }}>
                {i + 1}
              </div>
            ))}
          </div>
          <div style={{ width: 4 }} />
          {/* Distal label */}
          <div style={{ display: 'flex', gap: 1, flex: '0 0 auto' }}>
            {Array.from({ length: 8 }, (_, i) => (
              <div key={i} style={{
                width: 18, height: 14, display: 'flex', alignItems: 'center', justifyContent: 'center',
                fontSize: 8, color: T.muted, fontFamily: 'monospace',
              }}>
                {i + 13}
              </div>
            ))}
          </div>
        </div>

        {/* Region labels */}
        <div style={{ display: 'flex', gap: 1, marginBottom: 6, paddingLeft: 40 }}>
          <div style={{
            flex: '0 0 auto', width: 12 * 18 + 11, fontSize: 8,
            color: T.teal, textAlign: 'center', letterSpacing: '0.4px',
            textTransform: 'uppercase',
          }}>
            Seed region
          </div>
          <div style={{ width: 4 }} />
          <div style={{
            flex: '0 0 auto', width: 8 * 18 + 7, fontSize: 8,
            color: T.mid, textAlign: 'center', letterSpacing: '0.4px',
            textTransform: 'uppercase',
          }}>
            Distal
          </div>
        </div>

        {/* Rows */}
        {rows.map((site, ri) => (
          <div key={ri} style={{ display: 'flex', alignItems: 'center', gap: 4, marginBottom: 2 }}>
            <span style={{
              width: 36, fontSize: 9, color: T.muted, textAlign: 'right',
              fontFamily: 'monospace', flexShrink: 0,
            }}>
              {ri + 1}
            </span>
            <div style={{ display: 'flex', gap: 1 }}>
              {site.mismatch_map.slice(0, 12).map((mm, ci) => (
                <div key={ci} style={{
                  width: 18, height: 14, borderRadius: 2,
                  background: mm ? T.red : '#1a1f2e',
                  opacity: mm ? 0.9 : 0.6,
                }} />
              ))}
            </div>
            <div style={{ width: 4 }} />
            <div style={{ display: 'flex', gap: 1 }}>
              {site.mismatch_map.slice(12, 20).map((mm, ci) => (
                <div key={ci} style={{
                  width: 18, height: 14, borderRadius: 2,
                  background: mm ? '#FAC775' : '#1a1f2e',
                  opacity: mm ? 0.85 : 0.6,
                }} />
              ))}
            </div>
          </div>
        ))}

        {sites.length > 10 && (
          <button
            onClick={() => setShowAll(v => !v)}
            style={{
              marginTop: 8, background: 'transparent', border: `0.5px solid ${T.border2}`,
              borderRadius: 4, padding: '4px 12px', color: T.mid, fontSize: 11,
              cursor: 'pointer',
            }}
          >
            {showAll ? 'Show fewer' : `Show all ${sites.length} sites`}
          </button>
        )}
      </div>
    </div>
  )
}

// ─── sequence with mismatches highlighted ────────────────────────────────────

function SeqWithMismatches({ seq, guide, mismatchMap }) {
  return (
    <span style={{ fontFamily: 'monospace', fontSize: 12 }}>
      {[...seq].map((ch, i) => (
        <span key={i} style={{ color: mismatchMap[i] ? T.red : T.mid }}>
          {ch}
        </span>
      ))}
    </span>
  )
}

// ─── main page ────────────────────────────────────────────────────────────────

export default function OffTarget() {
  const { sequence, grnas, selectedGuide, update: storeUpdate } = useHelixStore()

  const [selectedIdx, setSelectedIdx] = useState(() => {
    if (!selectedGuide) return 0
    const i = grnas.findIndex(g => g.pos === selectedGuide.pos)
    return i >= 0 ? i : 0
  })
  const [maxMismatches, setMaxMismatches] = useState(3)
  const [result, setResult]               = useState(null)
  const [loading, setLoading]             = useState(false)
  const [error, setError]                 = useState(null)
  const [expandedRow, setExpandedRow]     = useState(null)
  const [runH, runEvents]                 = useHover()

  const selectedGrna = grnas[selectedIdx] ?? null

  async function handleRun() {
    if (!selectedGrna || !sequence) return
    setLoading(true)
    setError(null)
    setResult(null)
    setExpandedRow(null)
    try {
      const data = await findOffTargets(
        selectedGrna.guide.slice(0, 20),
        sequence,
        maxMismatches,
      )
      setResult(data)
    } catch (err) {
      setError(err?.response?.data?.detail ?? err.message ?? 'Off-target search failed')
    } finally {
      setLoading(false)
    }
  }

  const thStyle = {
    padding: '8px 12px', color: T.muted, fontSize: 10,
    textTransform: 'uppercase', letterSpacing: '0.8px',
    fontWeight: 500, textAlign: 'left',
  }

  if (!grnas.length) {
    return (
      <div style={{
        display: 'flex', alignItems: 'center', justifyContent: 'center',
        height: 300, color: T.muted, fontSize: 13, textAlign: 'center', lineHeight: 1.6,
      }}>
        Run a gRNA analysis in Sandbox first<br />to load guides for off-target checking
      </div>
    )
  }

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 16 }}>

      {/* ── controls ── */}
      <div style={{
        background: T.surface, border: `0.5px solid ${T.border}`,
        borderRadius: 8, padding: '16px',
        display: 'flex', flexDirection: 'column', gap: 14,
      }}>
        <div style={{ display: 'flex', flexWrap: 'wrap', gap: 16, alignItems: 'flex-end' }}>
          {/* gRNA selector */}
          <div style={{ flex: '1 1 300px', display: 'flex', flexDirection: 'column', gap: 6 }}>
            <label style={{ fontSize: 10, color: T.muted, textTransform: 'uppercase', letterSpacing: '0.8px' }}>
              gRNA
            </label>
            <select
              value={selectedIdx}
              onChange={e => setSelectedIdx(Number(e.target.value))}
              style={{
                background: T.bg, border: `0.5px solid ${T.border2}`, borderRadius: 6,
                padding: '7px 10px', fontSize: 12, color: T.text, outline: 'none',
                cursor: 'pointer', fontFamily: 'monospace',
              }}
            >
              {grnas.map((g, i) => (
                <option key={i} value={i}>
                  pos: {g.pos} | {g.guide.slice(0, 20)} | score: {g.score.toFixed(3)}
                </option>
              ))}
            </select>
          </div>

          {/* max mismatches */}
          <div style={{ flex: '0 0 200px', display: 'flex', flexDirection: 'column', gap: 6 }}>
            <label style={{ fontSize: 10, color: T.muted, textTransform: 'uppercase', letterSpacing: '0.8px' }}>
              Max mismatches — <span style={{ color: T.teal, fontFamily: 'monospace' }}>{maxMismatches}</span>
            </label>
            <input
              type="range" min={1} max={4} step={1}
              value={maxMismatches}
              onChange={e => setMaxMismatches(Number(e.target.value))}
              style={{ accentColor: T.teal }}
            />
          </div>

          {/* run button */}
          <button
            onClick={handleRun}
            disabled={loading || !selectedGrna}
            {...runEvents}
            style={{
              padding: '8px 20px', borderRadius: 6, fontWeight: 500, fontSize: 13,
              background: runH && !loading ? '#0F6E56' : T.teal,
              color: '#04342C', border: 'none',
              cursor: loading ? 'not-allowed' : 'pointer',
              opacity: loading ? 0.5 : 1,
              transition: 'background 0.15s',
              whiteSpace: 'nowrap',
            }}
          >
            {loading ? 'Searching…' : 'Find Off-targets'}
          </button>
        </div>

        <div style={{ fontSize: 11, color: T.muted }}>
          Higher mismatch tolerance = slower search and more false positives
        </div>
      </div>

      {/* error */}
      {error && (
        <div style={{
          padding: '8px 16px', background: '#1a0808', border: '0.5px solid #4a1010',
          borderRadius: 6, color: T.red, fontSize: 12,
        }}>
          <span style={{ fontWeight: 700 }}>Error: </span>{error}
        </div>
      )}

      {/* ── summary cards ── */}
      {result && (
        <div style={{ display: 'flex', gap: 12 }}>
          <StatCard label="Total sites"  value={result.total_sites}  color={T.text} />
          <StatCard label="High risk"    value={result.high_risk}    color={T.red} />
          <StatCard label="Medium risk"  value={result.medium_risk}  color={T.amber} />
          <StatCard label="Low risk"     value={result.low_risk}     color={T.tealFg} />
        </div>
      )}

      {/* ── heatmap ── */}
      {result && result.sites.length > 0 && (
        <MismatchHeatmap sites={result.sites} guide={result.guide} />
      )}

      {/* ── results table ── */}
      {result && result.sites.length > 0 && (
        <div style={{ background: T.surface, border: `0.5px solid ${T.border}`, borderRadius: 8, overflow: 'hidden' }}>
          <div style={{ padding: '8px 16px', borderBottom: `0.5px solid ${T.border}` }}>
            <span style={{ fontSize: 10, color: T.muted, textTransform: 'uppercase', letterSpacing: '0.8px' }}>
              Off-target sites — {result.total_sites} found
            </span>
          </div>
          <div style={{ overflowX: 'auto' }}>
            <table style={{ width: '100%', borderCollapse: 'collapse' }}>
              <thead>
                <tr style={{ borderBottom: `0.5px solid ${T.border}` }}>
                  <th style={thStyle}>Risk</th>
                  <th style={thStyle}>Position</th>
                  <th style={thStyle}>Sequence (vs guide)</th>
                  <th style={thStyle}>PAM</th>
                  <th style={thStyle}>Total MM</th>
                  <th style={thStyle}>Seed MM</th>
                  <th style={thStyle}>Score</th>
                </tr>
              </thead>
              <tbody>
                {result.sites.map((site, i) => {
                  const isExpanded = expandedRow === i
                  return [
                    <tr
                      key={`row-${i}`}
                      onClick={() => setExpandedRow(isExpanded ? null : i)}
                      style={{
                        borderBottom: isExpanded ? 'none' : `0.5px solid ${T.border}`,
                        cursor: 'pointer',
                        background: isExpanded ? '#161c2e' : 'transparent',
                        transition: 'background 0.1s',
                      }}
                      onMouseEnter={e => { if (!isExpanded) e.currentTarget.style.background = '#1a1f2e' }}
                      onMouseLeave={e => { if (!isExpanded) e.currentTarget.style.background = 'transparent' }}
                    >
                      <td style={{ padding: '8px 12px' }}><RiskBadge risk={site.risk_level} /></td>
                      <td style={{ padding: '8px 12px', fontFamily: 'monospace', color: T.mid, fontSize: 12 }}>
                        {site.strand}{site.position}
                      </td>
                      <td style={{ padding: '8px 12px' }}>
                        <SeqWithMismatches seq={site.sequence} guide={result.guide} mismatchMap={site.mismatch_map} />
                      </td>
                      <td style={{ padding: '8px 12px', fontFamily: 'monospace', color: T.amber, fontSize: 12 }}>
                        {site.pam}
                      </td>
                      <td style={{ padding: '8px 12px', fontFamily: 'monospace', color: T.text, fontSize: 12 }}>
                        {site.total_mismatches}
                      </td>
                      <td style={{ padding: '8px 12px', fontFamily: 'monospace', color: T.red, fontSize: 12 }}>
                        {site.seed_mismatches}
                      </td>
                      <td style={{ padding: '8px 12px', fontFamily: 'monospace', color: T.mid, fontSize: 12 }}>
                        {site.risk_score.toFixed(3)}
                      </td>
                    </tr>,
                    isExpanded && (
                      <tr key={`expand-${i}`} style={{ borderBottom: `0.5px solid ${T.border}`, background: '#161c2e' }}>
                        <td colSpan={7} style={{ padding: '8px 16px 12px' }}>
                          <div style={{ fontSize: 10, color: T.muted, marginBottom: 6, textTransform: 'uppercase', letterSpacing: '0.8px' }}>
                            Mismatch map vs guide
                          </div>
                          <div style={{ display: 'flex', gap: 4, alignItems: 'center', marginBottom: 6 }}>
                            <span style={{ fontSize: 11, color: T.muted, fontFamily: 'monospace', marginRight: 8 }}>Guide</span>
                            {[...result.guide].map((b, j) => (
                              <div key={j} style={{
                                width: 20, height: 20, borderRadius: 3, display: 'flex',
                                alignItems: 'center', justifyContent: 'center',
                                fontSize: 10, fontFamily: 'monospace', fontWeight: 600,
                                background: '#1a1f2e', color: T.teal,
                              }}>{b}</div>
                            ))}
                          </div>
                          <div style={{ display: 'flex', gap: 4, alignItems: 'center' }}>
                            <span style={{ fontSize: 11, color: T.muted, fontFamily: 'monospace', marginRight: 4 }}>Target</span>
                            {[...site.sequence].map((b, j) => (
                              <div key={j} style={{
                                width: 20, height: 20, borderRadius: 3, display: 'flex',
                                alignItems: 'center', justifyContent: 'center',
                                fontSize: 10, fontFamily: 'monospace', fontWeight: 600,
                                background: site.mismatch_map[j]
                                  ? (j < 12 ? T.redBg : T.amberBg)
                                  : '#1a1f2e',
                                color: site.mismatch_map[j]
                                  ? (j < 12 ? T.red : '#FAC775')
                                  : T.mid,
                              }}>{b}</div>
                            ))}
                          </div>
                        </td>
                      </tr>
                    ),
                  ]
                })}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {/* ── no results ── */}
      {result && result.sites.length === 0 && (
        <div style={{
          display: 'flex', alignItems: 'center', justifyContent: 'center',
          padding: '48px 0', color: T.muted, fontSize: 13,
        }}>
          No off-target sites found within {maxMismatches} mismatches
        </div>
      )}

      {/* ── empty state ── */}
      {!result && !loading && (
        <div style={{
          display: 'flex', alignItems: 'center', justifyContent: 'center',
          padding: '48px 0', color: T.muted, fontSize: 13,
        }}>
          Select a gRNA and run off-target analysis
        </div>
      )}

    </div>
  )
}
