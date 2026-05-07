import { useState, useEffect } from 'react'
import { designPrimers } from '../api'
import { useHelixStore } from '../store.jsx'

const T = {
  bg:      '#0f1117',
  surface: '#151821',
  border:  '#1e2130',
  border2: '#2a2e3e',
  teal:    '#1D9E75',
  tealBg:  '#0F2E1F',
  amber:   '#EF9F27',
  text:    '#e8e6df',
  muted:   '#5F5E5A',
  mid:     '#888780',
  red:     '#F09595',
}

function useHover() {
  const [h, setH] = useState(false)
  return [h, { onMouseEnter: () => setH(true), onMouseLeave: () => setH(false) }]
}

// ─── sequence context display ─────────────────────────────────────────────────

function CutSitePreview({ sequence, cutPos }) {
  if (!sequence || cutPos == null) return null
  const ctx  = 15
  const seq  = sequence.replace(/[^ACGTacgt]/gi, '').toUpperCase()
  const pre  = seq.slice(Math.max(0, cutPos - ctx), cutPos)
  const post = seq.slice(cutPos, cutPos + ctx)
  return (
    <div style={{
      fontFamily: 'monospace', fontSize: 12, color: T.mid,
      background: T.bg, border: `0.5px solid ${T.border}`,
      borderRadius: 6, padding: '8px 12px',
      display: 'flex', alignItems: 'center', gap: 0,
    }}>
      <span>…{pre}</span>
      <span style={{
        display: 'inline-block', width: 2, height: 16,
        background: T.red, margin: '0 2px', borderRadius: 1, verticalAlign: 'middle',
      }} />
      <span>{post}…</span>
      <span style={{ marginLeft: 10, color: T.muted, fontSize: 10 }}>bp {cutPos}</span>
    </div>
  )
}

// ─── edit preview ─────────────────────────────────────────────────────────────

function EditPreview({ editPreview }) {
  if (!editPreview) return null
  // format: "pre[edit]post"
  const match = editPreview.match(/^(.*)\[([^\]]*)\](.*)$/)
  if (!match) return <span style={{ fontFamily: 'monospace', fontSize: 12, color: T.mid }}>{editPreview}</span>
  const [, pre, edit, post] = match
  return (
    <div style={{
      fontFamily: 'monospace', fontSize: 12,
      background: T.bg, border: `0.5px solid ${T.border}`,
      borderRadius: 6, padding: '8px 12px',
    }}>
      <span style={{ color: T.mid }}>…{pre}</span>
      <span style={{ color: T.amber, fontWeight: 700 }}>[{edit || '–'}]</span>
      <span style={{ color: T.mid }}>{post}…</span>
    </div>
  )
}

// ─── primer card ──────────────────────────────────────────────────────────────

function PrimerCard({ primer, label, accentColor }) {
  const [copied, setCopied] = useState(false)

  function copy() {
    navigator.clipboard.writeText(primer.sequence).then(() => {
      setCopied(true)
      setTimeout(() => setCopied(false), 1500)
    })
  }

  return (
    <div style={{
      flex: 1, background: T.surface, border: `0.5px solid ${T.border}`,
      borderRadius: 8, padding: 16, display: 'flex', flexDirection: 'column', gap: 10,
    }}>
      <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
        <span style={{
          width: 8, height: 8, borderRadius: '50%', background: accentColor, display: 'inline-block',
        }} />
        <span style={{ fontSize: 11, color: T.muted, textTransform: 'uppercase', letterSpacing: '0.8px' }}>
          {label}
        </span>
      </div>

      <div style={{
        fontFamily: 'monospace', fontSize: 12, color: T.text,
        wordBreak: 'break-all', lineHeight: 1.6,
        background: T.bg, border: `0.5px solid ${T.border}`,
        borderRadius: 6, padding: '8px 10px',
      }}>
        {primer.sequence}
      </div>

      <div style={{ display: 'flex', gap: 16, fontSize: 11, color: T.mid }}>
        <span>Tm <span style={{ color: T.text, fontFamily: 'monospace' }}>{primer.tm}°C</span></span>
        <span>GC <span style={{ color: T.text, fontFamily: 'monospace' }}>{primer.gc}%</span></span>
        <span>Length <span style={{ color: T.text, fontFamily: 'monospace' }}>{primer.length}nt</span></span>
      </div>

      <div style={{ fontSize: 11, color: T.muted }}>
        Position <span style={{ color: T.mid, fontFamily: 'monospace' }}>bp {primer.position}</span>
      </div>

      <button
        onClick={copy}
        style={{
          alignSelf: 'flex-start', padding: '4px 12px', borderRadius: 4,
          border: `0.5px solid ${T.border2}`, background: 'transparent',
          color: copied ? T.teal : T.mid, fontSize: 11, cursor: 'pointer',
          transition: 'color 0.15s',
        }}
      >
        {copied ? 'Copied!' : 'Copy'}
      </button>
    </div>
  )
}

// ─── HDR donor display ────────────────────────────────────────────────────────

function DonorDisplay({ leftArm, editPreview, rightArm, hdrDonor }) {
  const [copiedDonor, setCopiedDonor] = useState(false)

  function copyDonor() {
    navigator.clipboard.writeText(hdrDonor).then(() => {
      setCopiedDonor(true)
      setTimeout(() => setCopiedDonor(false), 1500)
    })
  }

  function downloadDonor() {
    const blob = new Blob([hdrDonor], { type: 'text/plain' })
    const url  = URL.createObjectURL(blob)
    const a    = document.createElement('a')
    a.href     = url
    a.download = 'hdr_donor.txt'
    a.click()
    URL.revokeObjectURL(url)
  }

  // Extract edit from preview
  const match = editPreview.match(/\[([^\]]*)\]/)
  const editSeq = match ? match[1] : ''

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 10 }}>
      <div style={{
        fontFamily: 'monospace', fontSize: 12, lineHeight: 1.7, wordBreak: 'break-all',
        background: T.bg, border: `0.5px solid ${T.border}`,
        borderRadius: 6, padding: '10px 12px',
      }}>
        <span style={{ color: T.mid }}>{leftArm}</span>
        <span style={{ color: T.amber, fontWeight: 700 }}>{editSeq || '–'}</span>
        <span style={{ color: T.mid }}>{rightArm}</span>
      </div>
      <div style={{ fontSize: 11, color: T.muted }}>
        Total length: <span style={{ color: T.text, fontFamily: 'monospace' }}>{hdrDonor.length}nt</span>
        <span style={{ marginLeft: 16 }}>
          Arms: <span style={{ color: T.text, fontFamily: 'monospace' }}>
            {leftArm.length}bp + {rightArm.length}bp
          </span>
        </span>
      </div>
      <div style={{ display: 'flex', gap: 8 }}>
        <button
          onClick={copyDonor}
          style={{
            padding: '5px 14px', borderRadius: 4, border: `0.5px solid ${T.border2}`,
            background: 'transparent', color: copiedDonor ? T.teal : T.mid,
            fontSize: 11, cursor: 'pointer', transition: 'color 0.15s',
          }}
        >
          {copiedDonor ? 'Copied!' : 'Copy oligo'}
        </button>
        <button
          onClick={downloadDonor}
          style={{
            padding: '5px 14px', borderRadius: 4, border: `0.5px solid ${T.border2}`,
            background: 'transparent', color: T.mid,
            fontSize: 11, cursor: 'pointer',
          }}
        >
          Download .txt
        </button>
      </div>
    </div>
  )
}

// ─── main page ────────────────────────────────────────────────────────────────

export default function PrimerDesigner() {
  const { sequence, grnas, selectedGuide } = useHelixStore()

  const [selectedIdx, setSelectedIdx] = useState(() => {
    if (!selectedGuide) return 0
    const i = grnas.findIndex(g => g.pos === selectedGuide.pos)
    return i >= 0 ? i : 0
  })
  const [cutPosition, setCutPosition]   = useState(null)
  const [cutOverride, setCutOverride]   = useState(false)
  const [editType, setEditType]         = useState('snp')
  const [editSequence, setEditSequence] = useState('A')
  const [editPosition, setEditPosition] = useState(null)
  const [editLength, setEditLength]     = useState(1)
  const [result, setResult]             = useState(null)
  const [loading, setLoading]           = useState(false)
  const [error, setError]               = useState(null)
  const [designH, designEvents]         = useHover()

  const selectedGrna = grnas[selectedIdx] ?? null
  const seq = (sequence || '').replace(/[^ACGTacgt]/gi, '').toUpperCase()

  // Auto-fill cut and edit position when gRNA changes
  useEffect(() => {
    if (selectedGrna && !cutOverride) {
      const cut = (selectedGrna.pos ?? 0) + 17
      setCutPosition(cut)
      setEditPosition(cut)
    }
  }, [selectedIdx, selectedGrna, cutOverride])

  async function handleDesign() {
    if (!seq || cutPosition == null) return
    setLoading(true)
    setError(null)
    try {
      const data = await designPrimers(
        seq,
        cutPosition,
        editType,
        editType === 'deletion' ? '' : editSequence,
        editPosition ?? cutPosition,
        editType === 'deletion' ? editLength : 1,
      )
      setResult(data)
    } catch (err) {
      setError(err?.response?.data?.detail ?? err.message ?? 'Primer design failed')
    } finally {
      setLoading(false)
    }
  }

  const sectionLabel = {
    fontSize: 10, color: T.muted, textTransform: 'uppercase',
    letterSpacing: '0.8px', marginBottom: 8,
  }
  const inputStyle = {
    background: T.bg, border: `0.5px solid ${T.border2}`, borderRadius: 6,
    padding: '6px 10px', fontSize: 12, color: T.text, outline: 'none',
    fontFamily: 'monospace',
  }
  const radioLabel = {
    display: 'flex', alignItems: 'center', gap: 6,
    fontSize: 13, color: T.text, cursor: 'pointer',
  }

  if (!grnas.length) {
    return (
      <div style={{
        display: 'flex', alignItems: 'center', justifyContent: 'center',
        height: 300, color: T.muted, fontSize: 13, textAlign: 'center', lineHeight: 1.6,
      }}>
        Run a gRNA analysis in Sandbox first<br />to load guides for primer design
      </div>
    )
  }

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 16 }}>

      {/* ── step 1: cut site ── */}
      <div style={{
        background: T.surface, border: `0.5px solid ${T.border}`,
        borderRadius: 8, padding: 16, display: 'flex', flexDirection: 'column', gap: 14,
      }}>
        <div style={sectionLabel}>Step 1 — Cut site</div>

        <div style={{ display: 'flex', flexWrap: 'wrap', gap: 16, alignItems: 'flex-end' }}>
          {/* gRNA selector */}
          <div style={{ flex: '1 1 300px', display: 'flex', flexDirection: 'column', gap: 6 }}>
            <label style={{ fontSize: 11, color: T.muted }}>gRNA guide</label>
            <select
              value={selectedIdx}
              onChange={e => { setSelectedIdx(Number(e.target.value)); setCutOverride(false) }}
              style={{ ...inputStyle, cursor: 'pointer' }}
            >
              {grnas.map((g, i) => (
                <option key={i} value={i}>
                  pos: {g.pos} | {g.guide.slice(0, 20)} | score: {g.score.toFixed(3)}
                </option>
              ))}
            </select>
          </div>

          {/* cut position */}
          <div style={{ flex: '0 0 160px', display: 'flex', flexDirection: 'column', gap: 6 }}>
            <label style={{ fontSize: 11, color: T.muted }}>Cut position (bp)</label>
            <input
              type="number"
              value={cutPosition ?? ''}
              onChange={e => { setCutPosition(Number(e.target.value)); setCutOverride(true) }}
              style={{ ...inputStyle, width: '100%' }}
            />
          </div>
        </div>

        <CutSitePreview sequence={seq} cutPos={cutPosition} />
      </div>

      {/* ── step 2: edit ── */}
      <div style={{
        background: T.surface, border: `0.5px solid ${T.border}`,
        borderRadius: 8, padding: 16, display: 'flex', flexDirection: 'column', gap: 14,
      }}>
        <div style={sectionLabel}>Step 2 — Define edit</div>

        {/* edit type radio */}
        <div style={{ display: 'flex', gap: 20 }}>
          {['snp', 'insertion', 'deletion'].map(type => (
            <label key={type} style={radioLabel}>
              <input
                type="radio"
                name="editType"
                value={type}
                checked={editType === type}
                onChange={() => setEditType(type)}
                style={{ accentColor: T.teal }}
              />
              {type.charAt(0).toUpperCase() + type.slice(1)}
            </label>
          ))}
        </div>

        {/* edit inputs */}
        <div style={{ display: 'flex', flexWrap: 'wrap', gap: 16, alignItems: 'flex-end' }}>
          {editType === 'snp' && (
            <div style={{ display: 'flex', flexDirection: 'column', gap: 6 }}>
              <label style={{ fontSize: 11, color: T.muted }}>New base</label>
              <select
                value={editSequence}
                onChange={e => setEditSequence(e.target.value)}
                style={{ ...inputStyle, cursor: 'pointer', width: 80 }}
              >
                {['A', 'T', 'G', 'C'].map(b => <option key={b} value={b}>{b}</option>)}
              </select>
            </div>
          )}

          {editType === 'insertion' && (
            <div style={{ flex: '1 1 200px', display: 'flex', flexDirection: 'column', gap: 6 }}>
              <label style={{ fontSize: 11, color: T.muted }}>Insert sequence</label>
              <input
                type="text"
                value={editSequence}
                onChange={e => setEditSequence(e.target.value.replace(/[^ACGTacgt]/gi, ''))}
                placeholder="e.g. ATGC"
                style={{ ...inputStyle, width: '100%' }}
              />
            </div>
          )}

          {editType === 'deletion' && (
            <div style={{ display: 'flex', flexDirection: 'column', gap: 6 }}>
              <label style={{ fontSize: 11, color: T.muted }}>Deletion length (bp)</label>
              <input
                type="number"
                value={editLength}
                min={1}
                onChange={e => setEditLength(Math.max(1, Number(e.target.value)))}
                style={{ ...inputStyle, width: 100 }}
              />
            </div>
          )}

          <div style={{ display: 'flex', flexDirection: 'column', gap: 6 }}>
            <label style={{ fontSize: 11, color: T.muted }}>Edit position (bp)</label>
            <input
              type="number"
              value={editPosition ?? ''}
              onChange={e => setEditPosition(Number(e.target.value))}
              style={{ ...inputStyle, width: 120 }}
            />
          </div>
        </div>

        {/* live preview */}
        {seq && editPosition != null && (
          <div style={{ display: 'flex', flexDirection: 'column', gap: 4 }}>
            <div style={{ fontSize: 10, color: T.muted, textTransform: 'uppercase', letterSpacing: '0.8px' }}>
              Edit preview
            </div>
            <EditPreview editPreview={(() => {
              const ep  = Math.min(Math.max(editPosition, 0), seq.length)
              const dl  = editType === 'deletion' ? editLength : 0
              const es  = editType === 'deletion' ? '' : editType === 'snp' ? editSequence.slice(0, 1) : editSequence
              const ctx = 12
              return `${seq.slice(Math.max(0, ep - ctx), ep)}[${es || '-'}]${seq.slice(ep + dl, ep + dl + ctx)}`
            })()} />
          </div>
        )}
      </div>

      {/* ── step 3: design button ── */}
      <button
        onClick={handleDesign}
        disabled={loading || !seq}
        {...designEvents}
        style={{
          width: '100%', padding: '12px 0', borderRadius: 8, fontSize: 14,
          fontWeight: 600, border: 'none',
          background: designH && !loading ? '#0F6E56' : T.teal,
          color: '#04342C',
          cursor: loading || !seq ? 'not-allowed' : 'pointer',
          opacity: loading || !seq ? 0.5 : 1,
          transition: 'background 0.15s',
        }}
      >
        {loading ? 'Designing primers…' : 'Design Primers'}
      </button>

      {/* error */}
      {error && (
        <div style={{
          padding: '8px 16px', background: '#1a0808', border: '0.5px solid #4a1010',
          borderRadius: 6, color: T.red, fontSize: 12,
        }}>
          <span style={{ fontWeight: 700 }}>Error: </span>{error}
        </div>
      )}

      {/* ── results ── */}
      {result && (
        <>
          {/* Primer pair */}
          <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
            <div style={sectionLabel}>Primer pair</div>
            <div style={{ display: 'flex', gap: 12, flexWrap: 'wrap' }}>
              <PrimerCard primer={result.forward_primer} label="Forward primer" accentColor={T.teal} />
              <PrimerCard primer={result.reverse_primer} label="Reverse primer" accentColor={T.amber} />
            </div>
          </div>

          {/* Amplicon bar */}
          <div style={{
            background: T.surface, border: `0.5px solid ${T.border}`, borderRadius: 8,
            padding: '10px 16px', display: 'flex', alignItems: 'center', gap: 10,
          }}>
            <span style={{ fontSize: 12, color: T.muted }}>Amplicon</span>
            <span style={{
              fontSize: 13, fontFamily: 'monospace', fontWeight: 600,
              color: result.amplicon_size >= 300 && result.amplicon_size <= 500 ? T.teal : T.amber,
            }}>
              {result.amplicon_size} bp
            </span>
            <span style={{ fontSize: 11, color: T.muted }}>
              {result.amplicon_size >= 300 && result.amplicon_size <= 500
                ? '— suitable for gel verification'
                : '— consider adjusting primer positions for optimal gel band'}
            </span>
          </div>

          {/* HDR donor */}
          <div style={{
            background: T.surface, border: `0.5px solid ${T.border}`,
            borderRadius: 8, padding: 16, display: 'flex', flexDirection: 'column', gap: 12,
          }}>
            <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
              <div style={sectionLabel}>HDR donor oligo (ready to order)</div>
            </div>
            <DonorDisplay
              leftArm={result.left_arm}
              editPreview={result.edit_preview}
              rightArm={result.right_arm}
              hdrDonor={result.hdr_donor}
            />
          </div>

          {/* Protocol note */}
          <div style={{
            padding: '12px 16px', background: T.surface, border: `0.5px solid ${T.border}`,
            borderRadius: 8,
          }}>
            <p style={{ margin: 0, fontSize: 11, color: T.muted, lineHeight: 1.7 }}>
              Order the HDR donor as a single-stranded ultramer oligo (IDT, Twist, or Sigma).
              Use forward + reverse primers to verify editing by PCR and Sanger sequencing.
            </p>
          </div>
        </>
      )}

    </div>
  )
}
