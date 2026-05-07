import { useState } from "react"

export default function ProteinViewer3D() {
  const [query, setQuery] = useState("")
  const [results, setResults] = useState([])
  const [activePdbId, setActivePdbId] = useState(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState(null)

  const search = async () => {
    if (!query.trim()) return
    setLoading(true)
    setError(null)
    try {
      const resp = await fetch(`/api/pdb/search?query=${encodeURIComponent(query)}`)
      const data = await resp.json()
      setResults(data.results || [])
    } catch(e) {
      setError("Search failed")
    }
    setLoading(false)
  }

  const load = (pdbId) => {
    setActivePdbId(pdbId.toUpperCase())
    setResults([])
    setQuery(pdbId.toUpperCase())
  }

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>

      {/* Search bar */}
      <div style={{ display: 'flex', gap: 8, position: 'relative' }}>
        <input
          value={query}
          onChange={e => setQuery(e.target.value)}
          onKeyDown={e => e.key === 'Enter' && search()}
          placeholder="Search protein by name or PDB ID (e.g. crambin, 1CRN)"
          style={{
            flex: 1, background: '#0f1117', border: '0.5px solid #2a2e3e',
            borderRadius: 6, padding: '8px 12px', color: '#e8e6df',
            fontFamily: 'monospace', fontSize: 13, outline: 'none',
          }}
        />
        <button
          onClick={search}
          disabled={loading}
          style={{
            background: '#1D9E75', color: '#04342C', border: 'none',
            borderRadius: 6, padding: '8px 16px', fontWeight: 500,
            cursor: loading ? 'not-allowed' : 'pointer',
            opacity: loading ? 0.6 : 1,
          }}
        >
          {loading ? "Searching..." : "Search"}
        </button>
      </div>

      {/* Dropdown results */}
      {results.length > 0 && (
        <div style={{
          background: '#151821', border: '0.5px solid #1e2130',
          borderRadius: 8, overflow: 'hidden',
        }}>
          {results.map(r => (
            <div
              key={r.pdb_id}
              onClick={() => load(r.pdb_id)}
              style={{
                padding: '10px 14px', cursor: 'pointer',
                borderBottom: '0.5px solid #1e2130',
                color: '#e8e6df', fontSize: 13,
                display: 'flex', gap: 10, alignItems: 'center',
              }}
              onMouseEnter={e => e.currentTarget.style.background = '#1a1f2e'}
              onMouseLeave={e => e.currentTarget.style.background = 'transparent'}
            >
              <span style={{
                background: '#0F2E1F', color: '#1D9E75',
                padding: '2px 8px', borderRadius: 4,
                fontFamily: 'monospace', fontSize: 12, fontWeight: 500,
              }}>{r.pdb_id}</span>
              <span style={{ color: '#888780' }}>{r.title}</span>
            </div>
          ))}
        </div>
      )}

      {error && (
        <div style={{
          background: '#3D1515', border: '0.5px solid #F09595',
          borderRadius: 6, padding: '8px 12px', color: '#F09595', fontSize: 13,
        }}>{error}</div>
      )}

      {/* Mol* viewer iframe */}
      {activePdbId ? (
        <div style={{ position: 'relative' }}>
          <div style={{
            position: 'absolute', top: 10, left: 10, zIndex: 10,
            background: '#151821', border: '0.5px solid #1e2130',
            borderRadius: 6, padding: '4px 10px',
            color: '#1D9E75', fontFamily: 'monospace', fontSize: 12,
          }}>
            {activePdbId}
          </div>
          <iframe
            src={`https://molstar.org/viewer/?pdb=${activePdbId}`}
            style={{
              width: '100%', height: 500, border: 'none',
              borderRadius: 8, background: '#0f1117',
            }}
            title={`3D structure of ${activePdbId}`}
          />
        </div>
      ) : (
        <div style={{
          height: 500, background: '#151821',
          border: '0.5px solid #1e2130', borderRadius: 8,
          display: 'flex', alignItems: 'center', justifyContent: 'center',
          color: '#5F5E5A', fontSize: 13,
        }}>
          Search for a protein to view its 3D structure
        </div>
      )}

    </div>
  )
}
