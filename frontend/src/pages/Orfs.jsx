import { useState } from 'react'
import { findOrfs } from '../api'
import { useHelixStore } from '../store.jsx'

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

const FRAMES = ['+1', '+2', '+3', '-1', '-2', '-3']

const VW = 1000
const LBL = 44
const PAD_R = 10
const PAD_T = 8
const PAD_B = 8
const MAP_H = 200
const TRACK_W = VW - LBL - PAD_R
const LANE_H = (MAP_H - PAD_T - PAD_B) / 6

function useHover() {
  const [h, setH] = useState(false)
  return [h, { onMouseEnter: () => setH(true), onMouseLeave: () => setH(false) }]
}

const HYDROPHOBIC = new Set('AILMFWV')
const POLAR       = new Set('STNQ')
const CHARGED     = new Set('DEKR')

function aaColor(aa) {
  if (HYDROPHOBIC.has(aa)) return T.amber
  if (POLAR.has(aa))       return T.green
  if (CHARGED.has(aa))     return T.purple
  if (aa === '*')           return T.red
  return T.text
}

function ProteinSeq({ seq }) {
  return (
    <div style={{ fontFamily: 'monospace', fontSize: 13, lineHeight: 1.8, wordBreak: 'break-all' }}>
      {[...seq].map((aa, i) => (
        <span key={i} style={{ color: aaColor(aa) }}>{aa}</span>
      ))}
    </div>
  )
}

function SixFrameMap({ orfs, seqLen, selectedId, onSelect }) {
  if (!seqLen) return null

  const orfX = (start) => LBL + (start / seqLen) * TRACK_W
  const orfW = (start, end) => Math.max(((end - start) / seqLen) * TRACK_W, 3)

  return (
    <svg
      viewBox={`0 0 ${VW} ${MAP_H}`}
      width="100%"
      style={{ display: 'block', height: MAP_H }}
    >
      <rect x={0} y={0} width={VW} height={MAP_H} fill={T.surface} />

      {FRAMES.map((frame, idx) => {
        const cy = PAD_T + (idx + 0.5) * LANE_H
        const isForward = frame.startsWith('+')
        const blockColor = isForward ? T.green : T.amber
        const laneOrfs = orfs.filter(o => o.frame === frame)

        return (
          <g key={frame}>
            <rect x={LBL} y={cy - 1} width={TRACK_W} height={2} fill={T.border} />
            <text
              x={LBL - 6}
              y={cy}
              fill={T.muted}
              fontSize={11}
              textAnchor="end"
              dominantBaseline="middle"
            >
              {frame}
            </text>
            {laneOrfs.map(orf => {
              const isSelected = selectedId === orf.id
              return (
                <rect
                  key={orf.id}
                  x={orfX(orf.start)}
                  y={PAD_T + idx * LANE_H + 4}
                  width={orfW(orf.start, orf.end)}
                  height={LANE_H - 8}
                  rx={2}
                  fill={blockColor}
                  opacity={isSelected ? 1 : 0.7}
                  stroke={isSelected ? '#c8f5d8' : 'none'}
                  strokeWidth={1.5}
                  cursor="pointer"
                  onClick={() => onSelect(isSelected ? null : orf.id)}
                />
              )
            })}
          </g>
        )
      })}
    </svg>
  )
}

export default function Orfs() {
  const { sequence, update: storeUpdate } = useHelixStore()
  const [minLength, setMinLength]   = useState(100)
  const [result, setResult]         = useState(null)
  const [loading, setLoading]       = useState(false)
  const [error, setError]           = useState(null)
  const [selectedId, setSelectedId] = useState(null)
  const [findH, findEvents]         = useHover()

  const orfs        = result?.orfs ?? []
  const seqLen      = result?.sequence_length ?? 0
  const selectedOrf = orfs.find(o => o.id === selectedId) ?? null

  function handleSelectOrf(id) {
    setSelectedId(id)
    storeUpdate({ selectedOrf: id ? (orfs.find(o => o.id === id) ?? null) : null })
  }

  async function handleFind() {
    if (!sequence) return
    setLoading(true)
    setError(null)
    handleSelectOrf(null)
    try {
      const data = await findOrfs(sequence, minLength)
      setResult(data)
    } catch (err) {
      setError(err?.response?.data?.detail ?? err.message ?? 'ORF search failed')
    } finally {
      setLoading(false)
    }
  }

  if (!sequence) {
    return (
      <div style={{
        display: 'flex', alignItems: 'center', justifyContent: 'center',
        height: 300, color: T.muted, fontSize: 12, textAlign: 'center',
        lineHeight: 1.6, fontFamily: 'monospace',
      }}>
        Paste a sequence in the Sandbox tab<br />and run an analysis first
      </div>
    )
  }

  const thStyle = {
    padding: '8px 12px', color: T.muted, fontSize: 9,
    textTransform: 'uppercase', letterSpacing: '2px',
    fontWeight: 500, textAlign: 'left', fontFamily: 'monospace',
  }

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 16 }}>

      {/* Controls */}
      <div style={{
        display: 'flex', alignItems: 'center', gap: 16,
        background: T.surface, border: `1px solid ${T.border}`,
        borderRadius: 8, padding: '12px 16px',
      }}>
        <span style={{ fontSize: 11, color: T.muted, whiteSpace: 'nowrap', fontFamily: 'monospace' }}>Min ORF length</span>
        <input
          type="range" min={50} max={500} step={10}
          value={minLength}
          onChange={e => setMinLength(Number(e.target.value))}
          style={{ flex: 1, accentColor: T.green }}
        />
        <span style={{
          fontSize: 11, fontFamily: 'monospace', color: T.green,
          minWidth: 54, textAlign: 'right',
        }}>
          {minLength} bp
        </span>
        <button
          onClick={handleFind}
          disabled={loading}
          {...findEvents}
          style={{
            padding: '6px 16px', borderRadius: 4,
            background: findH && !loading ? T.greenDk : T.green,
            color: '#020a06', fontWeight: 700, fontSize: 12,
            fontFamily: 'monospace', border: 'none',
            cursor: loading ? 'not-allowed' : 'pointer',
            opacity: loading ? 0.5 : 1,
            transition: 'background 0.15s',
            whiteSpace: 'nowrap',
          }}
        >
          {loading ? 'Searching…' : 'Find ORFs'}
        </button>
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
              6-Frame ORF Map
            </span>
            <div style={{ display: 'flex', gap: 16, fontSize: 10, color: T.muted, alignItems: 'center', fontFamily: 'monospace' }}>
              <span style={{ display: 'flex', alignItems: 'center', gap: 4 }}>
                <span style={{ display: 'inline-block', width: 8, height: 8, borderRadius: 2, background: T.green }} />
                Forward
              </span>
              <span style={{ display: 'flex', alignItems: 'center', gap: 4 }}>
                <span style={{ display: 'inline-block', width: 8, height: 8, borderRadius: 2, background: T.amber }} />
                Reverse
              </span>
              <span style={{ color: T.dim }}>{result.total} ORFs · {seqLen} bp</span>
            </div>
          </div>
          <SixFrameMap
            orfs={orfs}
            seqLen={seqLen}
            selectedId={selectedId}
            onSelect={handleSelectOrf}
          />
        </div>
      )}

      {result && orfs.length > 0 && (
        <div style={{
          background: T.surface, border: `1px solid ${T.border}`,
          borderRadius: 8, overflow: 'hidden',
        }}>
          <div style={{ padding: '8px 16px', borderBottom: `1px solid ${T.border}` }}>
            <span style={{ fontSize: 9, color: T.muted, textTransform: 'uppercase', letterSpacing: '2px', fontFamily: 'monospace' }}>
              ORF Results — {result.total} found
            </span>
          </div>
          <div style={{ overflowX: 'auto' }}>
            <table style={{ width: '100%', borderCollapse: 'collapse' }}>
              <thead>
                <tr style={{ borderBottom: `1px solid ${T.border}` }}>
                  <th style={thStyle}>Frame</th>
                  <th style={thStyle}>Start</th>
                  <th style={thStyle}>End</th>
                  <th style={thStyle}>Length</th>
                  <th style={thStyle}>First 30 aa</th>
                </tr>
              </thead>
              <tbody>
                {orfs.map(orf => {
                  const isSelected = selectedId === orf.id
                  return (
                    <tr
                      key={orf.id}
                      onClick={() => handleSelectOrf(isSelected ? null : orf.id)}
                      style={{
                        borderBottom: `1px solid ${T.border}`,
                        borderLeft: isSelected ? `2px solid ${T.green}` : '2px solid transparent',
                        cursor: 'pointer',
                        background: isSelected ? 'rgba(0,255,136,0.04)' : 'transparent',
                        transition: 'background 0.1s',
                      }}
                      onMouseEnter={e => { if (!isSelected) e.currentTarget.style.background = 'rgba(0,255,136,0.03)' }}
                      onMouseLeave={e => { if (!isSelected) e.currentTarget.style.background = 'transparent' }}
                    >
                      <td style={{ padding: '8px 12px', fontFamily: 'monospace', fontSize: 12, color: orf.frame.startsWith('+') ? T.green : T.amber }}>
                        {orf.frame}
                      </td>
                      <td style={{ padding: '8px 12px', color: T.dim, fontSize: 12, fontFamily: 'monospace' }}>{orf.start}</td>
                      <td style={{ padding: '8px 12px', color: T.dim, fontSize: 12, fontFamily: 'monospace' }}>{orf.end}</td>
                      <td style={{ padding: '8px 12px', color: T.text, fontSize: 12, fontFamily: 'monospace' }}>{orf.length} bp</td>
                      <td style={{ padding: '8px 12px', fontFamily: 'monospace', color: T.dim, fontSize: 12 }}>{orf.protein}</td>
                    </tr>
                  )
                })}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {result && orfs.length === 0 && (
        <div style={{
          display: 'flex', alignItems: 'center', justifyContent: 'center',
          padding: '48px 0', color: T.muted, fontSize: 12, fontFamily: 'monospace',
        }}>
          No ORFs found with minimum length {minLength} bp — try reducing the slider
        </div>
      )}

      {selectedOrf && (
        <div style={{
          background: T.surface, border: `1px solid ${T.border}`,
          borderRadius: 8, padding: 16,
        }}>
          <div style={{
            display: 'flex', alignItems: 'center', justifyContent: 'space-between',
            marginBottom: 12,
          }}>
            <div style={{ display: 'flex', gap: 20, fontSize: 11, color: T.muted, fontFamily: 'monospace' }}>
              <span>
                Frame{' '}
                <span style={{ color: selectedOrf.frame.startsWith('+') ? T.green : T.amber }}>
                  {selectedOrf.frame}
                </span>
              </span>
              <span>
                Position{' '}
                <span style={{ color: T.text }}>
                  {selectedOrf.start}–{selectedOrf.end}
                </span>
              </span>
              <span>
                Length{' '}
                <span style={{ color: T.text }}>
                  {selectedOrf.length} bp
                </span>
              </span>
            </div>
            <button
              onClick={() => handleSelectOrf(null)}
              style={{
                background: 'transparent', border: 'none',
                color: T.muted, cursor: 'pointer',
                fontSize: 18, lineHeight: 1, padding: '0 4px',
              }}
            >
              ×
            </button>
          </div>

          <div style={{
            fontSize: 9, color: T.muted,
            textTransform: 'uppercase', letterSpacing: '2px', marginBottom: 8, fontFamily: 'monospace',
          }}>
            Protein Sequence ({selectedOrf.full_protein.length} aa)
          </div>

          <div style={{
            background: T.deep, borderRadius: 4, padding: 12,
            border: `1px solid ${T.border}`,
          }}>
            <ProteinSeq seq={selectedOrf.full_protein} />
          </div>

          <div style={{ display: 'flex', gap: 20, marginTop: 10, fontSize: 10, color: T.muted, fontFamily: 'monospace' }}>
            <span><span style={{ color: T.amber }}>■</span> Hydrophobic</span>
            <span><span style={{ color: T.green }}>■</span> Polar</span>
            <span><span style={{ color: T.purple }}>■</span> Charged</span>
            <span><span style={{ color: T.red }}>■</span> Stop</span>
          </div>
        </div>
      )}

    </div>
  )
}
