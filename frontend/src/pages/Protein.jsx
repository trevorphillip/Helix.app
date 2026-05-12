import { useState } from 'react'
import { translateProtein, analyzeProtein } from '../api'
import { useHelixStore } from '../store.jsx'
import ProteinViewer3D from '../components/ProteinViewer3D'

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
  red:     '#ff2244',
  purple:  '#aa88ff',
  text:    '#c8f5d8',
  dim:     '#4a8a5a',
  muted:   '#1a4a2a',
}

// ─── amino acid helpers ───────────────────────────────────────────────────────

const HYDROPHOBIC = new Set('AILMFWV')
const POLAR       = new Set('STNQ')
const CHARGED     = new Set('DEKRH')

function aaColor(aa) {
  if (HYDROPHOBIC.has(aa)) return T.amber
  if (POLAR.has(aa))       return T.green
  if (CHARGED.has(aa))     return T.purple
  if (aa === '*')           return T.red
  return T.text
}

const ALL_AA = ['A','C','D','E','F','G','H','I','K','L','M','N','P','Q','R','S','T','V','W','Y']

function useHover() {
  const [h, setH] = useState(false)
  return [h, { onMouseEnter: () => setH(true), onMouseLeave: () => setH(false) }]
}

// ─── codon viewer ─────────────────────────────────────────────────────────────

const MAX_CODONS    = 60
const CODONS_PER_ROW = 10

function CodonViewer({ protein, dnaUsed }) {
  if (!protein || !dnaUsed) return null

  const codons = []
  for (let i = 0; i + 2 < dnaUsed.length; i += 3) {
    codons.push({ dna: dnaUsed.slice(i, i + 3), aa: protein[i / 3] ?? '' })
  }

  const displayed = codons.slice(0, MAX_CODONS)
  const remaining = codons.length - displayed.length
  const rows      = []
  for (let i = 0; i < displayed.length; i += CODONS_PER_ROW) {
    rows.push(displayed.slice(i, i + CODONS_PER_ROW))
  }

  return (
    <div>
      {rows.map((row, ri) => (
        <div key={ri} style={{ display: 'flex', gap: 6, marginBottom: 14, flexWrap: 'wrap' }}>
          {row.map(({ dna, aa }, ci) => {
            const isStop = aa === '*'
            return (
              <div key={ci} style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', gap: 3 }}>
                <div style={{
                  padding: '2px 5px',
                  background: isStop ? 'rgba(255,34,68,0.12)' : T.deep,
                  border: `1px solid ${isStop ? 'rgba(255,34,68,0.4)' : T.border}`,
                  borderRadius: 4,
                  fontFamily: 'monospace',
                  fontSize: 11,
                  color: isStop ? T.red : T.text,
                  letterSpacing: '0.5px',
                }}>
                  {dna}
                </div>
                <span style={{ fontSize: 11, fontFamily: 'monospace', color: aaColor(aa) }}>
                  {aa || '?'}
                </span>
              </div>
            )
          })}
        </div>
      ))}
      {remaining > 0 && (
        <div style={{ fontSize: 11, color: T.muted, marginTop: 4, fontFamily: 'monospace' }}>
          … and {remaining} more codon{remaining !== 1 ? 's' : ''}
        </div>
      )}
    </div>
  )
}

// ─── protein sequence bar ─────────────────────────────────────────────────────

const SEQ_WRAP = 60

function ProteinBar({ protein }) {
  if (!protein) return null
  const chunks = []
  for (let i = 0; i < protein.length; i += SEQ_WRAP) {
    chunks.push({ start: i, seq: protein.slice(i, i + SEQ_WRAP) })
  }
  return (
    <div style={{ fontFamily: 'monospace', fontSize: 13, lineHeight: 1.9 }}>
      {chunks.map(({ start, seq }) => (
        <div key={start} style={{ display: 'flex', alignItems: 'baseline' }}>
          <span style={{
            color: T.muted, fontSize: 10, minWidth: 52,
            textAlign: 'right', paddingRight: 12, flexShrink: 0,
          }}>
            {start + 1}
          </span>
          <span>
            {[...seq].map((aa, i) => (
              <span key={i} style={{ color: aaColor(aa) }}>{aa}</span>
            ))}
          </span>
        </div>
      ))}
    </div>
  )
}

// ─── stat card ────────────────────────────────────────────────────────────────

function StatCard({ label, value, color }) {
  return (
    <div style={{
      flex: 1,
      background: 'rgba(10,31,16,0.8)',
      border: `1px solid ${T.border}`,
      borderRadius: 6,
      padding: '12px 14px',
    }}>
      <div style={{ color, fontSize: 20, fontWeight: 500, fontFamily: 'monospace' }}>{value}</div>
      <div style={{ color: T.muted, fontSize: 9, textTransform: 'uppercase', letterSpacing: '2px', marginTop: 4, fontFamily: 'monospace' }}>
        {label}
      </div>
    </div>
  )
}

// ─── AA composition chart ─────────────────────────────────────────────────────

const C_W  = 1000
const C_H  = 120
const C_ML = 30
const C_MR = 10
const C_MT = 8
const C_MB = 28
const C_IW = C_W - C_ML - C_MR
const C_IH = C_H - C_MT - C_MB
const BAR_W = C_IW / 20

function AaChart({ aaComposition, proteinLength }) {
  const [hoveredAa, setHoveredAa] = useState(null)
  if (!aaComposition) return null

  const maxCount = Math.max(...Object.values(aaComposition), 1)

  const barY  = count => C_MT + C_IH - (count / maxCount) * C_IH
  const barH  = count => (count / maxCount) * C_IH

  const hoverBar = hoveredAa ? {
    aa:    hoveredAa,
    count: aaComposition[hoveredAa] ?? 0,
    idx:   ALL_AA.indexOf(hoveredAa),
  } : null

  return (
    <svg
      viewBox={`0 0 ${C_W} ${C_H}`}
      width="100%"
      style={{ display: 'block', height: C_H }}
    >
      <rect width={C_W} height={C_H} fill={T.surface} />

      {[0, 0.25, 0.5, 0.75, 1].map(t => {
        const y = C_MT + C_IH - t * C_IH
        return (
          <line key={t} x1={C_ML} y1={y} x2={C_W - C_MR} y2={y}
            stroke={T.border} strokeWidth={1} />
        )
      })}

      {ALL_AA.map((aa, i) => {
        const count  = aaComposition[aa] ?? 0
        const x      = C_ML + i * BAR_W
        const cx     = x + BAR_W / 2
        const isHov  = hoveredAa === aa
        return (
          <g key={aa}
            onMouseEnter={() => setHoveredAa(aa)}
            onMouseLeave={() => setHoveredAa(null)}
          >
            <rect x={x} y={0} width={BAR_W} height={C_H} fill="transparent" />
            <rect
              x={x + 3} y={barY(count)}
              width={BAR_W - 6} height={Math.max(barH(count), 0)}
              fill={T.green}
              opacity={isHov ? 1 : 0.65}
              rx={2}
            />
            <text
              x={cx} y={C_H - 6}
              fill={T.muted} fontSize={9} textAnchor="middle"
            >
              {aa}
            </text>
          </g>
        )
      })}

      {hoverBar && hoverBar.count > 0 && (() => {
        const cx      = C_ML + (hoverBar.idx + 0.5) * BAR_W
        const tipW    = 72
        const tipH    = 22
        const tipX    = Math.min(Math.max(cx - tipW / 2, C_ML), C_W - C_MR - tipW)
        const tipY    = barY(hoverBar.count) - tipH - 4
        const pct     = ((hoverBar.count / proteinLength) * 100).toFixed(1)
        return (
          <g>
            <rect x={tipX} y={tipY} width={tipW} height={tipH}
              fill={T.deep} stroke={T.border} strokeWidth={0.5} rx={3} />
            <text x={tipX + tipW / 2} y={tipY + 14}
              fill={T.text} fontSize={9.5} textAnchor="middle">
              {hoverBar.count} ({pct}%)
            </text>
          </g>
        )
      })()}
    </svg>
  )
}

// ─── all-frames compact view ──────────────────────────────────────────────────

function AllFramesView({ results }) {
  return (
    <div style={{ display: 'flex', gap: 12 }}>
      {results.map(r => (
        <div key={r.frame} style={{
          flex: 1, background: T.surface, border: `1px solid ${T.border}`,
          borderRadius: 8, padding: 14,
        }}>
          <div style={{
            fontSize: 9, color: T.muted,
            textTransform: 'uppercase', letterSpacing: '2px', marginBottom: 8, fontFamily: 'monospace',
          }}>
            Frame {r.frame}
          </div>
          <div style={{ fontFamily: 'monospace', fontSize: 11, color: T.dim, wordBreak: 'break-all', marginBottom: 10 }}>
            {r.protein.length > 60 ? r.protein.slice(0, 60) + '…' : r.protein}
          </div>
          <div style={{ display: 'flex', gap: 16, fontSize: 10, color: T.muted, fontFamily: 'monospace' }}>
            <span>
              <span style={{ color: T.green }}>{r.length}</span> aa
            </span>
            <span>
              {r.stop_position !== null
                ? <>stop at <span style={{ color: T.red }}>{r.stop_position}</span></>
                : <span style={{ color: T.muted }}>no stop</span>
              }
            </span>
          </div>
        </div>
      ))}
    </div>
  )
}

// ─── main page ────────────────────────────────────────────────────────────────

const FRAME_OPTS = [
  { value: 0,     label: 'Frame 0' },
  { value: 1,     label: 'Frame 1' },
  { value: 2,     label: 'Frame 2' },
  { value: 'all', label: 'All Frames' },
]

export default function Protein() {
  const { sequence, update: storeUpdate } = useHelixStore()
  const [frame, setFrame]             = useState(0)
  const [activeTab, setActiveTab]     = useState('Analysis')
  const [transResults, setTransResults] = useState([])
  const [analyzeResult, setAnalyzeResult] = useState(null)
  const [loading, setLoading]         = useState(false)
  const [error, setError]             = useState(null)
  const [transH, transEvents]         = useHover()

  const isAll    = frame === 'all'
  const mainResult = transResults[0] ?? null

  async function handleTranslate() {
    if (!sequence) return
    setLoading(true)
    setError(null)
    setTransResults([])
    setAnalyzeResult(null)
    try {
      if (isAll) {
        const [r0, r1, r2] = await Promise.all([
          translateProtein(sequence, 0),
          translateProtein(sequence, 1),
          translateProtein(sequence, 2),
        ])
        setTransResults([r0, r1, r2])
      } else {
        const r = await translateProtein(sequence, frame)
        setTransResults([r])
        storeUpdate({ proteinSequence: r.protein })
        const a = await analyzeProtein(r.protein)
        setAnalyzeResult(a)
      }
    } catch (err) {
      setError(err?.response?.data?.detail ?? err.message ?? 'Translation failed')
    } finally {
      setLoading(false)
    }
  }

  if (!sequence) {
    return (
      <div style={{
        display: 'flex', alignItems: 'center', justifyContent: 'center',
        height: 300, color: T.muted, fontSize: 12, textAlign: 'center', lineHeight: 1.6,
        fontFamily: 'monospace',
      }}>
        Paste a sequence in the Sandbox tab<br />and run an analysis first
      </div>
    )
  }

  const Section = ({ title, children }) => (
    <div style={{
      background: T.surface, border: `1px solid ${T.border}`,
      borderRadius: 8, overflow: 'hidden',
    }}>
      <div style={{ padding: '8px 16px', borderBottom: `1px solid ${T.border}` }}>
        <span style={{ fontSize: 9, color: T.muted, textTransform: 'uppercase', letterSpacing: '2px', fontFamily: 'monospace' }}>
          {title}
        </span>
      </div>
      <div style={{ padding: 16 }}>{children}</div>
    </div>
  )

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 16 }}>

      {/* Controls */}
      <div style={{
        background: T.surface, border: `1px solid ${T.border}`,
        borderRadius: 8, padding: '12px 16px',
        display: 'flex', alignItems: 'center', gap: 12, flexWrap: 'wrap',
      }}>
        <div style={{ display: 'flex', gap: 4 }}>
          {FRAME_OPTS.map(({ value, label }) => {
            const active = frame === value
            return (
              <button
                key={value}
                onClick={() => setFrame(value)}
                style={{
                  padding: '5px 12px', borderRadius: 4, cursor: 'pointer',
                  border: `1px solid ${active ? T.green : T.border}`,
                  fontSize: 11, fontWeight: active ? 700 : 400, fontFamily: 'monospace',
                  background: active ? T.green : 'transparent',
                  color: active ? '#020a06' : T.dim,
                  transition: 'background 0.12s, color 0.12s',
                }}
              >
                {label}
              </button>
            )
          })}
        </div>

        <button
          onClick={handleTranslate}
          disabled={loading}
          {...transEvents}
          style={{
            padding: '6px 16px', borderRadius: 4,
            background: transH && !loading ? T.greenDk : T.green,
            color: '#020a06', fontWeight: 700, fontSize: 12,
            fontFamily: 'monospace', border: 'none',
            cursor: loading ? 'not-allowed' : 'pointer',
            opacity: loading ? 0.5 : 1,
            transition: 'background 0.15s',
            whiteSpace: 'nowrap',
          }}
        >
          {loading ? 'Translating…' : 'Translate'}
        </button>

        {mainResult && !isAll && (
          <div style={{ display: 'flex', gap: 16, fontSize: 10, color: T.muted, marginLeft: 'auto', fontFamily: 'monospace' }}>
            <span>
              <span style={{ color: T.green }}>{mainResult.codon_count}</span> codons
            </span>
            {mainResult.stop_position !== null && (
              <span>
                stop at <span style={{ color: T.red }}>{mainResult.stop_position}</span>
              </span>
            )}
          </div>
        )}
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

      {/* Tab selector */}
      <div style={{ display: 'flex', borderBottom: `1px solid ${T.border}` }}>
        {['Analysis', '3D Structure'].map(tab => (
          <button
            key={tab}
            onClick={() => setActiveTab(tab)}
            style={{
              padding: '8px 14px', fontSize: 10, fontWeight: 400,
              fontFamily: 'monospace', letterSpacing: '1px', textTransform: 'uppercase',
              color: activeTab === tab ? T.green : T.muted,
              background: 'transparent', border: 'none',
              borderBottom: `2px solid ${activeTab === tab ? T.green : 'transparent'}`,
              cursor: 'pointer', transition: 'color 0.15s', whiteSpace: 'nowrap',
              textShadow: activeTab === tab ? '0 0 8px rgba(0,255,136,0.5)' : 'none',
            }}
          >
            {tab}
          </button>
        ))}
      </div>

      {activeTab === 'Analysis' && (
        <>
          {isAll && transResults.length === 3 && (
            <AllFramesView results={transResults} />
          )}

          {!isAll && mainResult && (
            <>
              <Section title={`Codon Viewer — Frame ${mainResult.frame}`}>
                <CodonViewer protein={mainResult.protein} dnaUsed={mainResult.dna_used} />
              </Section>

              <Section title={`Protein Sequence — ${mainResult.length} aa`}>
                <ProteinBar protein={mainResult.protein} />
                <div style={{ display: 'flex', gap: 20, marginTop: 12, fontSize: 10, color: T.muted, fontFamily: 'monospace' }}>
                  <span><span style={{ color: T.amber }}>■</span> Hydrophobic</span>
                  <span><span style={{ color: T.green }}>■</span> Polar</span>
                  <span><span style={{ color: T.purple }}>■</span> Charged</span>
                  <span><span style={{ color: T.red }}>■</span> Stop</span>
                </div>
              </Section>

              {analyzeResult && (
                <div style={{ display: 'flex', gap: 12 }}>
                  <StatCard label="Mol. Weight (Da)" value={analyzeResult.mw.toLocaleString()} color={T.green} />
                  <StatCard label="Length (aa)"      value={mainResult.length}                  color={T.green} />
                  <StatCard label="Isoelectric Point" value={analyzeResult.pi.toFixed(1)}       color={T.amber} />
                  <StatCard label="Hydrophobic %"    value={`${analyzeResult.hydrophobic_percent}%`} color={T.amber} />
                </div>
              )}

              {analyzeResult && (
                <Section title="Amino Acid Composition">
                  <AaChart
                    aaComposition={analyzeResult.aa_composition}
                    proteinLength={mainResult.length}
                  />
                </Section>
              )}
            </>
          )}
        </>
      )}

      {activeTab === '3D Structure' && <ProteinViewer3D />}

    </div>
  )
}
