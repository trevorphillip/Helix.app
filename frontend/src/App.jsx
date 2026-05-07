import { useState } from 'react'
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

const NAV_LINKS = [
  { to: '/',           label: 'Sandbox'      },
  { to: '/ai',         label: 'AI Assistant' },
  { to: '/library',    label: 'Library'      },
  { to: '/orfs',       label: 'ORFs'         },
  { to: '/variants',   label: 'Variants'     },
  { to: '/protein',    label: 'Protein'      },
  { to: '/offtarget',  label: 'Off-target'   },
  { to: '/primers',    label: 'Primers'      },
  { to: '/animation',  label: 'Animation'    },
  { to: '/game',       label: '🎮 Game'      },
  { to: '/medprep',    label: 'Med-Prep'     },
  { to: '/models',     label: 'Models'       },
  { to: '/sessions',   label: 'Sessions'     },
]

// ─── helix logo svg ──────────────────────────────────────────────────────────

function HelixIcon() {
  return (
    <svg width="13" height="13" viewBox="0 0 13 13" fill="none">
      <path d="M1 2.5 C4 3.8 9 3.8 12 2.5"  stroke="white" strokeWidth="1.4" strokeLinecap="round" />
      <path d="M1 6.5 C4 7.8 9 5.2 12 6.5"  stroke="white" strokeWidth="1.4" strokeLinecap="round" />
      <path d="M1 10.5 C4 9.2 9 9.2 12 10.5" stroke="white" strokeWidth="1.4" strokeLinecap="round" />
    </svg>
  )
}

// ─── nav item with hover ──────────────────────────────────────────────────────

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
        padding: '0 16px',
        height: 48,
        fontSize: 13,
        fontWeight: 400,
        color: isActive ? '#EF9F27' : hovered ? '#e8e6df' : '#5F5E5A',
        borderBottom: `2px solid ${isActive ? '#EF9F27' : 'transparent'}`,
        textDecoration: 'none',
        boxSizing: 'border-box',
        transition: 'color 0.15s',
        whiteSpace: 'nowrap',
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
      display: 'flex',
      alignItems: 'center',
      justifyContent: 'space-between',
      background: '#151821',
      borderBottom: '1px solid #1e2130',
      height: 48,
      padding: '0 24px',
    }}>
      {/* logo */}
      <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
        <div style={{
          width: 22, height: 22, borderRadius: '50%',
          background: '#1D9E75',
          display: 'flex', alignItems: 'center', justifyContent: 'center',
          flexShrink: 0,
        }}>
          <HelixIcon />
        </div>
        <span style={{ color: '#e8e6df', fontSize: 14, fontWeight: 500 }}>Helix</span>
      </div>

      {/* nav links */}
      <div style={{ display: 'flex', height: 48 }}>
        {NAV_LINKS.map(({ to, label }) => (
          <NavItem key={to} to={to} label={label} />
        ))}
      </div>

      {/* xp pill + avatar */}
      <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
        <div style={{
          background: '#1a1f2e',
          border: '0.5px solid #2a2e3e',
          color: '#1D9E75',
          padding: '4px 12px',
          borderRadius: 20,
          fontSize: 12,
          fontFamily: 'monospace',
          fontWeight: 600,
          whiteSpace: 'nowrap',
        }}>
          Lv 1 · 110 XP
        </div>
        <div style={{
          width: 28, height: 28, borderRadius: '50%',
          background: '#1a1f2e',
          border: '0.5px solid #2a2e3e',
          display: 'flex', alignItems: 'center', justifyContent: 'center',
          color: '#888780', fontSize: 10, fontWeight: 600,
          flexShrink: 0,
        }}>
          DA
        </div>
      </div>
    </nav>
  )
}

// ─── placeholder ─────────────────────────────────────────────────────────────

function Placeholder({ name }) {
  return (
    <div style={{
      display: 'flex', alignItems: 'center', justifyContent: 'center',
      height: 256, color: '#5F5E5A', fontSize: 13,
    }}>
      {name}
    </div>
  )
}

// ─── app ─────────────────────────────────────────────────────────────────────

export default function App() {
  return (
    <HelixProvider>
    <BrowserRouter>
      <div style={{ minHeight: '100vh', background: '#0f1117', color: '#e8e6df' }}>
        <NavBar />
        <Routes>
          <Route path="/ai"   element={<AiAssistant />} />
          <Route path="/game" element={<CrisprGame />} />
          <Route path="*" element={
            <main style={{ padding: 24 }}>
              <Routes>
                <Route path="/"         element={<Sandbox />} />
                <Route path="/orfs"      element={<Orfs />} />
                <Route path="/variants"  element={<Variants />} />
                <Route path="/protein"    element={<Protein />} />
                <Route path="/library"   element={<Library />} />
                <Route path="/offtarget" element={<OffTarget />} />
                <Route path="/primers"   element={<PrimerDesigner />} />
                <Route path="/animation" element={<Animation />} />
                <Route path="/medprep"   element={<Placeholder name="Med-Prep" />} />
                <Route path="/models"   element={<Placeholder name="Models" />} />
                <Route path="/sessions" element={<Placeholder name="Sessions" />} />
              </Routes>
            </main>
          } />
        </Routes>
      </div>
    </BrowserRouter>
    </HelixProvider>
  )
}
