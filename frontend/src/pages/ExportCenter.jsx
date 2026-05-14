import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { useHelixStore } from '../store.jsx'
import api from '../api.js'

const T = {
  green:   '#00ff88',
  amber:   '#ffaa00',
  red:     '#ff2244',
  dim:     '#1a4a2a',
  muted:   '#4a8a5a',
  text:    '#c8f5d8',
  border:  'rgba(0,255,136,0.12)',
  bg:      '#0a1f10',
  deepBg:  'rgba(5,18,9,0.9)',
}

function downloadFile(content, filename, type) {
  const blob = new Blob([content], { type })
  const url  = URL.createObjectURL(blob)
  const a    = document.createElement('a')
  a.href     = url
  a.download = filename
  a.click()
  URL.revokeObjectURL(url)
}

function Toast({ message }) {
  return (
    <div style={{
      position: 'fixed', bottom: 24, right: 24, zIndex: 9999,
      background: 'rgba(0,40,20,0.97)',
      border: `1px solid ${T.green}`,
      borderRadius: 6, padding: '10px 18px',
      color: T.green, fontFamily: 'monospace', fontSize: 12,
      boxShadow: '0 0 20px rgba(0,255,136,0.25)',
      animation: 'fadeInUp 0.2s ease',
    }}>
      {message}
    </div>
  )
}

const CHECKLIST_ITEMS = {
  protocol: [
    '✓ gRNA sequences & scores',
    '✓ IDT ordering information',
    '✓ Verification primer sequences',
    '✓ Expected outcomes',
    '✓ Step-by-step procedure',
  ],
  idt: [
    '✓ Forward guide oligos',
    '✓ Reverse complement oligos',
    '✓ ACCG/AAAC cloning overhangs',
    '✓ 25nmole scale, standard purification',
    '✓ Experiment labels and scores',
  ],
  genbank: [
    '✓ Full sequence with annotations',
    '✓ gRNA binding sites marked',
    '✓ ORF annotations',
    '✓ Compatible with SnapGene & Benchling',
    '✓ Standard GenBank format',
  ],
}

function ExportCard({ icon, title, description, checklist, btnLabel, onDownload, loading }) {
  const [hovered, setHovered] = useState(false)
  return (
    <div style={{
      background: T.bg,
      border: `1px solid ${hovered ? 'rgba(0,255,136,0.3)' : T.border}`,
      borderRadius: 8, padding: 20,
      display: 'flex', flexDirection: 'column', gap: 14,
      transition: 'border-color 0.2s',
    }}
      onMouseEnter={() => setHovered(true)}
      onMouseLeave={() => setHovered(false)}
    >
      <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
        <span style={{ fontSize: 22 }}>{icon}</span>
        <span style={{ color: T.green, fontFamily: 'monospace', fontSize: 13, fontWeight: 700, letterSpacing: '1px' }}>
          {title}
        </span>
      </div>

      <p style={{ color: T.muted, fontSize: 11, fontFamily: 'monospace', margin: 0, lineHeight: 1.6 }}>
        {description}
      </p>

      <div style={{ display: 'flex', flexDirection: 'column', gap: 4 }}>
        {checklist.map(item => (
          <span key={item} style={{ color: T.dim, fontSize: 10, fontFamily: 'monospace' }}>{item}</span>
        ))}
      </div>

      <button
        onClick={onDownload}
        disabled={loading}
        style={{
          marginTop: 'auto',
          padding: '8px 14px',
          background: loading ? 'rgba(0,40,20,0.4)' : 'rgba(0,40,20,0.8)',
          border: `1px solid ${T.green}`,
          borderRadius: 4, color: T.green,
          fontSize: 11, fontFamily: 'monospace', fontWeight: 700,
          cursor: loading ? 'not-allowed' : 'pointer',
          letterSpacing: '0.5px',
          boxShadow: '0 0 10px rgba(0,255,136,0.1)',
          transition: 'background 0.15s, box-shadow 0.15s',
          opacity: loading ? 0.6 : 1,
        }}
        onMouseEnter={e => { if (!loading) e.currentTarget.style.background = 'rgba(0,60,30,0.9)' }}
        onMouseLeave={e => { if (!loading) e.currentTarget.style.background = 'rgba(0,40,20,0.8)' }}
      >
        {loading ? '⟳ Generating...' : btnLabel}
      </button>
    </div>
  )
}

export default function ExportCenter() {
  const { sequence, enzyme, grnas } = useHelixStore()
  const navigate = useNavigate()

  const [expName, setExpName]   = useState('Helix_Experiment')
  const [toast, setToast]       = useState(null)
  const [loadingKey, setLoading] = useState(null)

  function showToast(msg) {
    setToast(msg)
    setTimeout(() => setToast(null), 3000)
  }

  async function handleDownload(endpoint, filename, fileType, body) {
    setLoading(endpoint)
    try {
      const res = await api.post(`/api/export/${endpoint}`, body, {
        responseType: 'text',
        transformResponse: [d => d],
      })
      downloadFile(res.data, filename, fileType)
      showToast(`✓ ${filename} downloaded successfully`)
    } catch (err) {
      showToast(`✗ Export failed: ${err.message}`)
    } finally {
      setLoading(null)
    }
  }

  const safeName = expName.trim() || 'Helix_Experiment'

  if (!sequence) {
    return (
      <div style={{
        display: 'flex', flexDirection: 'column', alignItems: 'center',
        justifyContent: 'center', height: '60vh', gap: 16,
      }}>
        <div style={{ color: T.green, fontFamily: 'monospace', fontSize: 14, letterSpacing: '2px' }}>
          // NO ANALYSIS LOADED
        </div>
        <div style={{ color: T.muted, fontFamily: 'monospace', fontSize: 11 }}>
          Run an analysis in Sandbox first
        </div>
        <button
          onClick={() => navigate('/')}
          style={{
            padding: '8px 20px', background: 'rgba(0,40,20,0.8)',
            border: `1px solid ${T.green}`, borderRadius: 4,
            color: T.green, fontFamily: 'monospace', fontSize: 11,
            fontWeight: 700, cursor: 'pointer', letterSpacing: '0.5px',
          }}
        >
          Go to Sandbox
        </button>
      </div>
    )
  }

  return (
    <div style={{ maxWidth: 1100, margin: '0 auto', display: 'flex', flexDirection: 'column', gap: 24 }}>
      {/* header */}
      <div>
        <div style={{ color: T.green, fontFamily: 'monospace', fontSize: 15, fontWeight: 700, letterSpacing: '2px' }}>
          // EXPORT CENTER
        </div>
        <div style={{ color: T.dim, fontFamily: 'monospace', fontSize: 11, marginTop: 4 }}>
          Export your analysis in lab-ready formats
        </div>
      </div>

      {/* experiment name */}
      <div style={{ display: 'flex', flexDirection: 'column', gap: 6 }}>
        <label style={{ color: T.green, fontFamily: 'monospace', fontSize: 10, letterSpacing: '1.5px' }}>
          // EXPERIMENT NAME
        </label>
        <input
          value={expName}
          onChange={e => setExpName(e.target.value)}
          placeholder="e.g. TP53_knockout_HEK293"
          style={{
            width: '100%', boxSizing: 'border-box',
            background: T.bg, border: `1px solid ${T.border}`,
            borderRadius: 4, padding: '8px 12px',
            color: T.text, fontFamily: 'monospace', fontSize: 12,
            outline: 'none',
          }}
          onFocus={e => { e.target.style.borderColor = T.green }}
          onBlur={e => { e.target.style.borderColor = T.border }}
        />
      </div>

      {/* cards grid */}
      <div style={{
        display: 'grid',
        gridTemplateColumns: 'repeat(auto-fit, minmax(300px, 1fr))',
        gap: 16,
      }}>
        <ExportCard
          icon="📋"
          title="Lab Protocol"
          description={"Complete step-by-step protocol with reagent list, ordering info, and verification steps. Ready to print."}
          checklist={CHECKLIST_ITEMS.protocol}
          btnLabel="⬇ Download Protocol (.txt)"
          loading={loadingKey === 'protocol'}
          onDownload={() => handleDownload(
            'protocol',
            `${safeName}_protocol.txt`,
            'text/plain',
            { sequence, enzyme, grnas, experiment_name: safeName },
          )}
        />

        <ExportCard
          icon="🧬"
          title="IDT Order Sheet"
          description={"Ready-to-upload CSV for IDT DNA synthesis. Includes forward and reverse oligos with cloning overhangs."}
          checklist={CHECKLIST_ITEMS.idt}
          btnLabel="⬇ Download Order Sheet (.csv)"
          loading={loadingKey === 'idt_order'}
          onDownload={() => handleDownload(
            'idt_order',
            `${safeName}_IDT_order.csv`,
            'text/csv',
            { grnas, experiment_name: safeName },
          )}
        />

        <ExportCard
          icon="🗺️"
          title="GenBank Annotation"
          description={"Annotated sequence file compatible with SnapGene, Benchling, and NCBI. Includes gRNA and ORF annotations."}
          checklist={CHECKLIST_ITEMS.genbank}
          btnLabel="⬇ Download GenBank (.gb)"
          loading={loadingKey === 'genbank'}
          onDownload={() => handleDownload(
            'genbank',
            `${safeName}.gb`,
            'text/plain',
            { sequence, name: safeName, grnas, orfs: [] },
          )}
        />
      </div>

      {toast && <Toast message={toast} />}
    </div>
  )
}
