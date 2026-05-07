import { useState } from 'react'
import { useHelixStore } from '../store.jsx'
import CrisprAnimation from '../components/CrisprAnimation'

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

const PHASE_EXPLANATIONS = [
  {
    phase: 'Scanning',
    text:  'Cas9, loaded with its guide RNA (gRNA), drifts along the DNA helix. It rapidly checks short sequences called PAM sites (NGG for SpCas9). If no match, it moves on.',
  },
  {
    phase: 'Binding',
    text:  'When Cas9 finds a matching PAM sequence, it grips the DNA and begins to open its two lobes like a clamp, exposing the target strand.',
  },
  {
    phase: 'Unwinding',
    text:  'Cas9 locally unwinds the double helix at the target site. The non-template strand is displaced, forming an R-loop structure while the template strand remains accessible.',
  },
  {
    phase: 'Hybridizing',
    text:  'The 20-nucleotide gRNA base-pairs with the complementary DNA strand one nucleotide at a time. If all 20 bases match, the complex stabilizes and cleavage proceeds.',
  },
  {
    phase: 'Cleaving',
    text:  'Two nuclease domains activate simultaneously: HNH cuts the strand complementary to the gRNA, while RuvC cuts the opposite strand. This creates a blunt-ended double-strand break (DSB).',
  },
  {
    phase: 'Repair',
    text:  'Cas9 releases and the cell detects the break. Non-Homologous End Joining (NHEJ) recruits Ku70/Ku80 proteins to rejoin the broken ends — often introducing a small insertion or deletion (indel) that disrupts the gene.',
  },
]

function PhaseCard({ phase, text }) {
  return (
    <div style={{
      padding: '12px 16px',
      background: T.bg,
      border: `0.5px solid ${T.border}`,
      borderRadius: 6,
    }}>
      <div style={{ fontSize: 12, fontWeight: 600, color: T.teal, marginBottom: 5 }}>{phase}</div>
      <div style={{ fontSize: 13, color: T.mid, lineHeight: 1.6 }}>{text}</div>
    </div>
  )
}

export default function Animation() {
  const { selectedGuide } = useHelixStore()
  const [expanded, setExpanded] = useState(false)

  const guide       = selectedGuide?.guide ?? 'GGCCGCCTCCGCGGCCGCCTGGG'
  const cutPosition = selectedGuide?.pos    ?? 42
  const displaySeq  = guide.slice(0, 20)

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 16 }}>

      {/* header */}
      <div>
        <h1 style={{ margin: 0, fontSize: 20, fontWeight: 600, color: T.text }}>
          CRISPR-Cas9 Mechanism — Live Animation
        </h1>
        <p style={{ margin: '6px 0 0', fontSize: 13, color: T.muted }}>
          Visualizing your gRNA:{' '}
          <span style={{ fontFamily: 'monospace', color: T.teal }}>{displaySeq}</span>
          <span style={{ fontFamily: 'monospace', color: T.amber }}>{guide.slice(20)}</span>
          {' '}&mdash; cut at position{' '}
          <span style={{ color: T.text }}>{cutPosition}</span>
        </p>
      </div>

      {/* animation canvas */}
      <div style={{
        background: T.surface,
        border: `0.5px solid ${T.border}`,
        borderRadius: 8,
        overflow: 'hidden',
        height: 560,
      }}>
        <CrisprAnimation guide={guide} cutPosition={cutPosition} />
      </div>

      {/* expandable explanation */}
      <div style={{
        background: T.surface,
        border: `0.5px solid ${T.border}`,
        borderRadius: 8,
        overflow: 'hidden',
      }}>
        <button
          onClick={() => setExpanded(v => !v)}
          style={{
            width: '100%',
            display: 'flex', alignItems: 'center', justifyContent: 'space-between',
            padding: '12px 16px',
            background: 'transparent', border: 'none', cursor: 'pointer',
            color: T.text, fontSize: 13, fontWeight: 500,
          }}
        >
          <span>What&apos;s happening?</span>
          <span style={{ color: T.muted, fontSize: 16, lineHeight: 1 }}>{expanded ? '−' : '+'}</span>
        </button>

        {expanded && (
          <div style={{ padding: '0 16px 16px', display: 'flex', flexDirection: 'column', gap: 8 }}>
            <p style={{ margin: '0 0 8px', fontSize: 13, color: T.mid, lineHeight: 1.6 }}>
              CRISPR-Cas9 is a bacterial immune system repurposed as a precision gene-editing tool.
              A guide RNA (gRNA) directs the Cas9 protein to a specific DNA sequence, where it makes
              a double-strand cut. The cell then repairs the break — often imperfectly — allowing
              researchers to knock out genes or introduce precise edits.
            </p>
            {PHASE_EXPLANATIONS.map(e => (
              <PhaseCard key={e.phase} phase={e.phase} text={e.text} />
            ))}
          </div>
        )}
      </div>

    </div>
  )
}
