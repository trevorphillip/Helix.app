import { useEffect, useState } from 'react'

const STATUS_MESSAGES = [
  'Initializing helix core...',
  'Loading sequence database...',
  'Calibrating ML scorer...',
  'Rendering 3D engine...',
  'Ready.',
]

function DnaHelixSvg() {
  const numPts = 60
  const W = 80
  const H = 200
  const cx = W / 2
  const r = 28
  const cycles = 2.5

  const strand1 = Array.from({ length: numPts + 1 }, (_, i) => {
    const t = i / numPts
    const x = cx + r * Math.sin(t * cycles * 2 * Math.PI)
    const y = t * H
    return `${x.toFixed(1)},${y.toFixed(1)}`
  }).join(' ')

  const strand2 = Array.from({ length: numPts + 1 }, (_, i) => {
    const t = i / numPts
    const x = cx + r * Math.sin(t * cycles * 2 * Math.PI + Math.PI)
    const y = t * H
    return `${x.toFixed(1)},${y.toFixed(1)}`
  }).join(' ')

  const pairs = Array.from({ length: numPts + 1 }, (_, i) => {
    if (i % 6 !== 0) return null
    const t = i / numPts
    const x1 = cx + r * Math.sin(t * cycles * 2 * Math.PI)
    const x2 = cx + r * Math.sin(t * cycles * 2 * Math.PI + Math.PI)
    const y = t * H
    const phase = (t * cycles * 2 * Math.PI) % (2 * Math.PI)
    const inFront = Math.sin(phase) >= 0
    return { x1: x1.toFixed(1), x2: x2.toFixed(1), y: y.toFixed(1), inFront }
  }).filter(Boolean)

  return (
    <div style={{ perspective: 400 }}>
      <div style={{ animation: 'helixSpin 3s linear infinite', transformStyle: 'preserve-3d' }}>
        <svg width={W} height={H} viewBox={`0 0 ${W} ${H}`} style={{ display: 'block' }}>
          <defs>
            <filter id="hglow">
              <feGaussianBlur stdDeviation="2" result="blur" />
              <feMerge><feMergeNode in="blur" /><feMergeNode in="SourceGraphic" /></feMerge>
            </filter>
          </defs>
          {pairs.filter(p => !p.inFront).map((p, i) => (
            <line key={`b${i}`} x1={p.x1} y1={p.y} x2={p.x2} y2={p.y}
              stroke="rgba(0,255,136,0.25)" strokeWidth="1.5" />
          ))}
          <polyline points={strand1} fill="none" stroke="#00ff88" strokeWidth="2.5"
            filter="url(#hglow)" strokeLinecap="round" strokeLinejoin="round" />
          <polyline points={strand2} fill="none" stroke="#00cc66" strokeWidth="2.5"
            filter="url(#hglow)" strokeLinecap="round" strokeLinejoin="round" />
          {pairs.filter(p => p.inFront).map((p, i) => (
            <line key={`f${i}`} x1={p.x1} y1={p.y} x2={p.x2} y2={p.y}
              stroke="rgba(0,255,136,0.5)" strokeWidth="1.5" />
          ))}
        </svg>
      </div>
    </div>
  )
}

export default function LoadingScreen() {
  const [statusIdx, setStatusIdx] = useState(0)
  const [barW, setBarW] = useState(0)

  useEffect(() => {
    const iv = setInterval(() => {
      setStatusIdx(prev => Math.min(prev + 1, STATUS_MESSAGES.length - 1))
    }, 500)
    const raf = requestAnimationFrame(() => setBarW(100))
    return () => { clearInterval(iv); cancelAnimationFrame(raf) }
  }, [])

  return (
    <div style={{
      position: 'fixed', inset: 0,
      background: '#020a06',
      display: 'flex', flexDirection: 'column',
      alignItems: 'center', justifyContent: 'center',
      zIndex: 9000,
      fontFamily: 'monospace',
    }}>
      <style>{`
        @keyframes helixSpin {
          from { transform: rotateY(0deg); }
          to   { transform: rotateY(360deg); }
        }
        @keyframes loadFill {
          from { width: 0%; }
          to   { width: 100%; }
        }
      `}</style>

      <DnaHelixSvg />

      <div style={{
        marginTop: 28,
        fontSize: 32,
        letterSpacing: 12,
        color: '#00ff88',
        textShadow: '0 0 20px rgba(0,255,136,0.6)',
        fontWeight: 700,
      }}>
        HELIX
      </div>

      <div style={{
        marginTop: 8,
        fontSize: 10,
        letterSpacing: 6,
        color: '#1a4a2a',
        textTransform: 'uppercase',
      }}>
        CRISPR ANALYSIS SUITE
      </div>

      <div style={{
        marginTop: 28,
        width: 200,
        height: 1,
        background: '#051209',
        position: 'relative',
        overflow: 'hidden',
      }}>
        <div style={{
          position: 'absolute', top: 0, left: 0, height: '100%',
          background: '#00ff88',
          boxShadow: '0 0 8px rgba(0,255,136,0.5)',
          animation: 'loadFill 2.5s ease-out forwards',
        }} />
      </div>

      <div style={{
        marginTop: 14,
        fontSize: 11,
        color: '#004422',
        minHeight: 18,
        transition: 'opacity 0.3s',
      }}>
        {STATUS_MESSAGES[statusIdx]}
      </div>
    </div>
  )
}
