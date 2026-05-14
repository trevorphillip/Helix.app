import { useState, useEffect } from 'react'
import { BrowserRouter, Routes, Route, NavLink } from 'react-router-dom'
import Sandbox from './pages/Sandbox'
import { HelixProvider } from './store.jsx'
import AiAssistant from './pages/AiAssistant'
import Orfs from './pages/Orfs'
import Variants from './pages/Variants'
import Protein from './pages/Protein'
import OffTarget from './pages/OffTarget'
import PrimerDesigner from './pages/PrimerDesigner'
import Library from './pages/Library'
import Animation from './pages/Animation'
import CrisprGame from './pages/CrisprGame'
import OutcomeSimulator from './pages/OutcomeSimulator'
import LoadingScreen from './components/LoadingScreen'
import AmbientBackground from './components/AmbientBackground'

const NAV_LINKS = [
  { to: '/',           label: 'Sandbox'      },
  { to: '/ai',         label: 'AI'           },
  { to: '/library',    label: 'Library'      },
  { to: '/orfs',       label: 'ORFs'         },
  { to: '/variants',   label: 'Variants'     },
  { to: '/protein',    label: 'Protein'      },
  { to: '/offtarget',  label: 'Off-target'   },
  { to: '/primers',    label: 'Primers'      },
  { to: '/animation',  label: 'Animation'    },
  { to: '/outcome',    label: 'Outcome'      },
  { to: '/game',       label: 'Game'         },
  { to: '/medprep',    label: 'Med-Prep'     },
  { to: '/models',     label: 'Models'       },
  { to: '/sessions',   label: 'Sessions'     },
]

// ─── helix logo svg ───────────────────────────────────────────────────────────

function HelixIcon() {
  return (
    <svg width="11" height="11" viewBox="0 0 13 13" fill="none">
      <path d="M1 2.5 C4 3.8 9 3.8 12 2.5"  stroke="#020a06" strokeWidth="1.6" strokeLinecap="round" />
      <path d="M1 6.5 C4 7.8 9 5.2 12 6.5"  stroke="#020a06" strokeWidth="1.6" strokeLinecap="round" />
      <path d="M1 10.5 C4 9.2 9 9.2 12 10.5" stroke="#020a06" strokeWidth="1.6" strokeLinecap="round" />
    </svg>
  )
}

// ─── nav item ─────────────────────────────────────────────────────────────────

function NavItem({ to, label }) {
  const [hovered, setHovered] = useState(false)
  return (
    <NavLink
      to={to}
      end={to === '/'}
      onMouseEnter={() => setHovered(true)}
      onMouseLeave={() => setHovered(false)}
      style={({ isActive }) => ({
        display: 'flex',
        alignItems: 'center',
        padding: '0 12px',
        height: 44,
        fontSize: 11,
        fontFamily: 'monospace',
        fontWeight: 400,
        letterSpacing: '1px',
        textTransform: 'uppercase',
        color: isActive ? '#00ff88' : hovered ? '#4a8a5a' : '#1a4a2a',
        borderBottom: `1px solid ${isActive ? '#00ff88' : 'transparent'}`,
        textDecoration: 'none',
        boxSizing: 'border-box',
        transition: 'color 0.15s',
        whiteSpace: 'nowrap',
        textShadow: isActive ? '0 0 8px rgba(0,255,136,0.6)' : 'none',
      })}
    >
      {label}
    </NavLink>
  )
}

// ─── navbar ───────────────────────────────────────────────────────────────────

function NavBar() {
  return (
    <nav style={{
      position: 'fixed',
      top: 0, left: 0, width: '100%',
      zIndex: 1000,
      display: 'flex',
      alignItems: 'center',
      justifyContent: 'space-between',
      background: 'rgba(2, 10, 6, 0.95)',
      borderBottom: '1px solid rgba(0, 255, 136, 0.15)',
      backdropFilter: 'blur(20px)',
      height: 44,
      padding: '0 20px',
    }}>
      {/* logo */}
      <div style={{ display: 'flex', alignItems: 'center', gap: 8, flexShrink: 0 }}>
        <div style={{
          width: 18, height: 18, borderRadius: '50%',
          background: '#00ff88',
          display: 'flex', alignItems: 'center', justifyContent: 'center',
          flexShrink: 0,
          boxShadow: '0 0 10px rgba(0,255,136,0.4)',
        }}>
          <HelixIcon />
        </div>
        <span style={{
          color: '#00ff88',
          fontSize: 13,
          fontFamily: 'monospace',
          fontWeight: 700,
          letterSpacing: '3px',
          textShadow: '0 0 10px rgba(0,255,136,0.5)',
        }}>
          HELIX
        </span>
        <span style={{
          fontSize: 9,
          color: '#020a06',
          background: '#00ff88',
          padding: '1px 5px',
          borderRadius: 2,
          fontFamily: 'monospace',
          letterSpacing: 0,
        }}>
          v0.4
        </span>
      </div>

      {/* nav links */}
      <div style={{ display: 'flex', height: 44, overflow: 'hidden' }}>
        {NAV_LINKS.map(({ to, label }) => (
          <NavItem key={to} to={to} label={label} />
        ))}
      </div>

      {/* xp + username */}
      <div style={{ display: 'flex', alignItems: 'center', gap: 12, flexShrink: 0 }}>
        <span style={{
          fontFamily: 'monospace',
          fontSize: 11,
          color: '#ffaa00',
          whiteSpace: 'nowrap',
        }}>
          ◈ 110 XP
        </span>
        <span style={{ fontSize: 11, fontFamily: 'monospace', color: '#1a4a2a' }}>
          david
        </span>
      </div>
    </nav>
  )
}

// ─── placeholder ──────────────────────────────────────────────────────────────

function Placeholder({ name }) {
  return (
    <div style={{
      display: 'flex', alignItems: 'center', justifyContent: 'center',
      height: 256, color: '#1a4a2a', fontSize: 13, fontFamily: 'monospace',
    }}>
      {name}
    </div>
  )
}

// ─── app ──────────────────────────────────────────────────────────────────────

export default function App() {
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    const t = setTimeout(() => setLoading(false), 2500)
    return () => clearTimeout(t)
  }, [])

  if (loading) return <LoadingScreen />

  return (
    <HelixProvider>
      <BrowserRouter>
        <AmbientBackground />
        <div style={{ minHeight: '100vh', background: 'transparent', color: '#c8f5d8' }}>
          <NavBar />
          <Routes>
            <Route path="/ai"   element={<AiAssistant />} />
            <Route path="/game" element={<CrisprGame />} />
            <Route path="*" element={
              <main style={{ padding: '24px', paddingTop: 'calc(44px + 24px)' }}>
                <Routes>
                  <Route path="/"         element={<Sandbox />} />
                  <Route path="/orfs"      element={<Orfs />} />
                  <Route path="/variants"  element={<Variants />} />
                  <Route path="/protein"   element={<Protein />} />
                  <Route path="/library"   element={<Library />} />
                  <Route path="/offtarget" element={<OffTarget />} />
                  <Route path="/primers"   element={<PrimerDesigner />} />
                  <Route path="/animation" element={<Animation />} />
                  <Route path="/outcome"   element={<OutcomeSimulator />} />
                  <Route path="/medprep"   element={<Placeholder name="Med-Prep" />} />
                  <Route path="/models"    element={<Placeholder name="Models" />} />
                  <Route path="/sessions"  element={<Placeholder name="Sessions" />} />
                </Routes>
              </main>
            } />
          </Routes>
        </div>
      </BrowserRouter>
    </HelixProvider>
  )
}
