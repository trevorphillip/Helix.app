import { useState, useEffect, useRef } from 'react'
import { useNavigate } from 'react-router-dom'
import { searchGenes, fetchGeneSequence, getCommonGenes, saveSequence, listSequences, getSequence, deleteSequence } from '../api'
import { useHelixStore } from '../store.jsx'

// ─── tokens ───────────────────────────────────────────────────────────────────

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
  redBg:   '#6B1D1D',
  purple:  '#9B8FEF',
}

const TABS = ['Gene Database', 'gRNA Libraries', 'My Sequences']

const CATEGORIES = [
  { key: 'all',               label: 'All'                },
  { key: 'tumor_suppressor',  label: 'Tumor suppressors'  },
  { key: 'oncogene',          label: 'Oncogenes'           },
  { key: 'immune_checkpoint', label: 'Immune checkpoints' },
  { key: 'housekeeping',      label: 'Housekeeping'        },
  { key: 'crispr_essential',  label: 'CRISPR essential'   },
]

const ORGANISM_OPTIONS = [
  { value: 'human', label: 'Human'   },
  { value: 'mouse', label: 'Mouse'   },
  { value: 'ecoli', label: 'E. coli' },
  { value: 'yeast', label: 'Yeast'   },
  { value: 'all',   label: 'All'     },
]

const CAT_COLORS = {
  tumor_suppressor:  { bg: '#1a1025', color: T.purple },
  oncogene:          { bg: '#3D1515', color: T.red    },
  immune_checkpoint: { bg: '#0F2E1F', color: T.teal   },
  housekeeping:      { bg: '#2a1f00', color: T.amber  },
  crispr_essential:  { bg: '#1a1f2e', color: T.mid    },
}

// ─── helpers ─────────────────────────────────────────────────────────────────

function useHover() {
  const [h, setH] = useState(false)
  return [h, { onMouseEnter: () => setH(true), onMouseLeave: () => setH(false) }]
}

function CatBadge({ category }) {
  const s = CAT_COLORS[category] ?? CAT_COLORS.housekeeping
  const label = CATEGORIES.find(c => c.key === category)?.label ?? category
  return (
    <span style={{
      ...s, padding: '2px 8px', borderRadius: 4,
      fontSize: 9, fontWeight: 600, textTransform: 'uppercase', letterSpacing: '0.5px',
    }}>
      {label}
    </span>
  )
}

function SkeletonCard() {
  const bar = (w) => (
    <div style={{ height: 10, width: w, background: T.border, borderRadius: 3 }} />
  )
  return (
    <div style={{
      background: T.surface, border: `0.5px solid ${T.border}`,
      borderRadius: 8, padding: 14, display: 'flex', flexDirection: 'column', gap: 10,
    }}>
      {bar('60%')}
      {bar('90%')}
      {bar('40%')}
      <div style={{ height: 26, background: T.border, borderRadius: 6, marginTop: 4 }} />
    </div>
  )
}

// ─── gene card ────────────────────────────────────────────────────────────────

function GeneCard({ gene, onLoad, loadingAcc }) {
  const isLoading = loadingAcc === gene.accession
  const [hLoad, hLoadEvents] = useHover()

  const desc = gene.description?.length > 62
    ? gene.description.slice(0, 59) + '…'
    : (gene.description || '')

  const ncbiUrl = `https://www.ncbi.nlm.nih.gov/gene/?term=${encodeURIComponent(gene.name)}`

  return (
    <div style={{
      background: T.surface, border: `0.5px solid ${T.border}`,
      borderRadius: 8, padding: 14,
      display: 'flex', flexDirection: 'column', gap: 8,
    }}>
      <div style={{ display: 'flex', alignItems: 'flex-start', justifyContent: 'space-between', gap: 8 }}>
        <span style={{ fontSize: 14, fontWeight: 600, color: T.text, fontFamily: 'monospace' }}>
          {gene.name}
        </span>
        <CatBadge category={gene.category} />
      </div>

      <p style={{ margin: 0, fontSize: 12, color: T.mid, lineHeight: 1.5 }}>{desc}</p>

      <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
        <span style={{ fontFamily: 'monospace', fontSize: 11, color: T.muted }}>
          {gene.accession}
        </span>
        {gene.organism && (
          <span style={{ fontSize: 10, color: T.muted, fontStyle: 'italic' }}>
            · {gene.organism}
          </span>
        )}
      </div>

      <div style={{ display: 'flex', gap: 8, marginTop: 2 }}>
        <button
          onClick={() => onLoad(gene)}
          disabled={!!loadingAcc}
          {...hLoadEvents}
          style={{
            flex: 1, padding: '6px 0', borderRadius: 6, fontSize: 12,
            fontWeight: 500, border: 'none',
            background: hLoad && !loadingAcc ? '#0F6E56' : T.teal,
            color: '#04342C',
            cursor: loadingAcc ? 'not-allowed' : 'pointer',
            opacity: !!loadingAcc && !isLoading ? 0.4 : 1,
            transition: 'background 0.15s',
          }}
        >
          {isLoading
            ? <span style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', gap: 6 }}>
                <span style={{
                  width: 10, height: 10, borderRadius: '50%',
                  border: `2px solid #04342C`, borderTopColor: 'transparent',
                  display: 'inline-block', animation: 'spin 0.7s linear infinite',
                }} />
                Loading…
              </span>
            : 'Load into Sandbox'}
        </button>
        <a
          href={ncbiUrl}
          target="_blank"
          rel="noopener noreferrer"
          style={{
            padding: '6px 10px', borderRadius: 6, fontSize: 12,
            border: `0.5px solid ${T.border2}`, color: T.mid,
            textDecoration: 'none', whiteSpace: 'nowrap',
            transition: 'color 0.15s, border-color 0.15s',
          }}
          onMouseEnter={e => { e.currentTarget.style.color = T.amber; e.currentTarget.style.borderColor = T.amber }}
          onMouseLeave={e => { e.currentTarget.style.color = T.mid;   e.currentTarget.style.borderColor = T.border2 }}
        >
          NCBI →
        </a>
      </div>
    </div>
  )
}

// ─── gene database tab ────────────────────────────────────────────────────────

function GeneDatabaseTab() {
  const [searchQuery, setSearchQuery]   = useState('')
  const [organism, setOrganism]         = useState('human')
  const [category, setCategory]         = useState('all')
  const [commonGenes, setCommonGenes]   = useState([])
  const [searchResults, setSearchResults] = useState(null)
  const [searching, setSearching]       = useState(false)
  const [loadingCommon, setLoadingCommon] = useState(true)
  const [loadingAcc, setLoadingAcc]     = useState(null)
  const [error, setError]               = useState(null)
  const { update: storeUpdate }         = useHelixStore()
  const navigate                        = useNavigate()

  useEffect(() => {
    getCommonGenes()
      .then(data => setCommonGenes(data))
      .catch(() => setError('Failed to load common genes'))
      .finally(() => setLoadingCommon(false))
  }, [])

  async function handleSearch() {
    if (!searchQuery.trim()) {
      setSearchResults(null)
      return
    }
    setSearching(true)
    setError(null)
    try {
      const data = await searchGenes(searchQuery.trim(), organism)
      setSearchResults(data.results ?? [])
    } catch (err) {
      setError(err?.response?.data?.detail ?? 'NCBI search failed')
    } finally {
      setSearching(false)
    }
  }

  async function handleLoad(gene) {
    setLoadingAcc(gene.accession)
    setError(null)
    try {
      const data = await fetchGeneSequence(gene.accession)
      storeUpdate({ sequence: data.sequence })
      navigate('/')
    } catch (err) {
      setError(err?.response?.data?.detail ?? 'Failed to fetch gene sequence')
    } finally {
      setLoadingAcc(null)
    }
  }

  const displayGenes = searchResults !== null
    ? searchResults
    : category === 'all'
    ? commonGenes
    : commonGenes.filter(g => g.category === category)

  const inputStyle = {
    background: T.bg, border: `0.5px solid ${T.border2}`, borderRadius: 6,
    padding: '7px 10px', fontSize: 13, color: T.text, outline: 'none',
  }

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 16 }}>
      {/* Search bar */}
      <div style={{
        background: T.surface, border: `0.5px solid ${T.border}`,
        borderRadius: 8, padding: 16, display: 'flex', flexDirection: 'column', gap: 12,
      }}>
        <div style={{ display: 'flex', gap: 10, flexWrap: 'wrap' }}>
          <input
            value={searchQuery}
            onChange={e => { setSearchQuery(e.target.value); if (!e.target.value) setSearchResults(null) }}
            onKeyDown={e => e.key === 'Enter' && handleSearch()}
            placeholder="Search gene name (e.g. BRCA1, TP53, KRAS)"
            style={{ ...inputStyle, flex: '1 1 240px', fontFamily: 'monospace' }}
          />
          <select
            value={organism}
            onChange={e => setOrganism(e.target.value)}
            style={{ ...inputStyle, cursor: 'pointer' }}
          >
            {ORGANISM_OPTIONS.map(o => <option key={o.value} value={o.value}>{o.label}</option>)}
          </select>
          <button
            onClick={handleSearch}
            disabled={searching}
            style={{
              padding: '7px 20px', borderRadius: 6, fontWeight: 500, fontSize: 13,
              background: T.teal, color: '#04342C', border: 'none',
              cursor: searching ? 'not-allowed' : 'pointer',
              opacity: searching ? 0.6 : 1,
            }}
          >
            {searching ? 'Searching…' : 'Search'}
          </button>
        </div>

        {searchResults === null && (
          <p style={{ margin: 0, fontSize: 12, color: T.muted }}>
            Or browse common CRISPR targets:
          </p>
        )}
      </div>

      {/* Category pills — only shown when browsing common genes */}
      {searchResults === null && (
        <div style={{ display: 'flex', flexWrap: 'wrap', gap: 6 }}>
          {CATEGORIES.map(cat => (
            <button
              key={cat.key}
              onClick={() => setCategory(cat.key)}
              style={{
                padding: '4px 12px', borderRadius: 20, fontSize: 11,
                cursor: 'pointer', border: 'none', fontWeight: 500,
                background: category === cat.key ? T.teal : '#1a1f2e',
                color:      category === cat.key ? '#04342C' : T.mid,
                transition: 'background 0.15s',
              }}
            >
              {cat.label}
            </button>
          ))}
        </div>
      )}

      {searchResults !== null && (
        <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
          <span style={{ fontSize: 12, color: T.muted }}>
            {searchResults.length} result{searchResults.length !== 1 ? 's' : ''} for "{searchQuery}"
          </span>
          <button
            onClick={() => { setSearchResults(null); setSearchQuery('') }}
            style={{
              background: 'transparent', border: `0.5px solid ${T.border2}`,
              borderRadius: 4, padding: '2px 8px', fontSize: 11,
              color: T.mid, cursor: 'pointer',
            }}
          >
            Clear
          </button>
        </div>
      )}

      {error && (
        <div style={{
          padding: '8px 14px', background: '#1a0808', border: '0.5px solid #4a1010',
          borderRadius: 6, color: T.red, fontSize: 12,
        }}>
          {error}
        </div>
      )}

      {/* Gene cards grid */}
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(320px, 1fr))', gap: 12 }}>
        {loadingCommon && searchResults === null
          ? Array.from({ length: 4 }, (_, i) => <SkeletonCard key={i} />)
          : displayGenes.length === 0
          ? (
            <div style={{
              gridColumn: '1 / -1', padding: '48px 0',
              color: T.muted, fontSize: 13, textAlign: 'center',
            }}>
              {searchResults !== null ? 'No genes found — try a different search term' : 'No genes in this category'}
            </div>
          )
          : displayGenes.map((gene, i) => (
            <GeneCard
              key={gene.accession ?? i}
              gene={gene}
              onLoad={handleLoad}
              loadingAcc={loadingAcc}
            />
          ))}
      </div>
    </div>
  )
}

// ─── my sequences tab ─────────────────────────────────────────────────────────

function SeqCard({ seq, onLoad, onDelete }) {
  const [confirmDelete, setConfirmDelete] = useState(false)
  const [hLoad, hLoadEvents] = useHover()

  const date = seq.created_at ? new Date(seq.created_at).toLocaleDateString() : ''

  return (
    <div style={{
      background: T.surface, border: `0.5px solid ${T.border}`,
      borderRadius: 8, padding: 14, display: 'flex', flexDirection: 'column', gap: 8,
    }}>
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
        <span style={{ fontSize: 14, fontWeight: 600, color: T.text }}>{seq.name}</span>
        <span style={{ fontSize: 10, color: T.muted }}>{date}</span>
      </div>

      <div style={{ display: 'flex', gap: 12, fontSize: 11, color: T.muted }}>
        <span>{seq.length?.toLocaleString()} bp</span>
        {seq.organism && seq.organism !== 'unknown' && (
          <span style={{ fontStyle: 'italic' }}>{seq.organism}</span>
        )}
      </div>

      <div style={{ display: 'flex', gap: 8, marginTop: 4 }}>
        <button
          onClick={() => onLoad(seq.id)}
          {...hLoadEvents}
          style={{
            flex: 1, padding: '6px 0', borderRadius: 6, fontSize: 12,
            fontWeight: 500, border: 'none',
            background: hLoad ? '#0F6E56' : T.teal,
            color: '#04342C', cursor: 'pointer',
            transition: 'background 0.15s',
          }}
        >
          Load into Sandbox
        </button>
        {confirmDelete ? (
          <div style={{ display: 'flex', gap: 4 }}>
            <button
              onClick={() => onDelete(seq.id)}
              style={{
                padding: '6px 10px', borderRadius: 6, fontSize: 11,
                background: T.redBg, color: T.red, border: 'none', cursor: 'pointer',
              }}
            >
              Confirm
            </button>
            <button
              onClick={() => setConfirmDelete(false)}
              style={{
                padding: '6px 10px', borderRadius: 6, fontSize: 11,
                background: '#1a1f2e', color: T.mid, border: `0.5px solid ${T.border2}`,
                cursor: 'pointer',
              }}
            >
              Cancel
            </button>
          </div>
        ) : (
          <button
            onClick={() => setConfirmDelete(true)}
            style={{
              padding: '6px 10px', borderRadius: 6, fontSize: 12,
              border: `0.5px solid ${T.border2}`, color: T.muted,
              background: 'transparent', cursor: 'pointer',
              transition: 'color 0.15s, border-color 0.15s',
            }}
            onMouseEnter={e => { e.currentTarget.style.color = T.red; e.currentTarget.style.borderColor = T.red }}
            onMouseLeave={e => { e.currentTarget.style.color = T.muted; e.currentTarget.style.borderColor = T.border2 }}
          >
            Delete
          </button>
        )}
      </div>
    </div>
  )
}

function MySequencesTab() {
  const [sequences, setSequences]   = useState([])
  const [loading, setLoading]       = useState(true)
  const [error, setError]           = useState(null)
  const fileRef                     = useRef(null)
  const { update: storeUpdate }     = useHelixStore()
  const navigate                    = useNavigate()

  function reload() {
    setLoading(true)
    listSequences()
      .then(data => setSequences(data))
      .catch(() => setError('Failed to load sequences'))
      .finally(() => setLoading(false))
  }

  useEffect(reload, [])

  async function handleLoad(id) {
    try {
      const data = await getSequence(id)
      storeUpdate({ sequence: data.sequence })
      navigate('/')
    } catch {
      setError('Failed to load sequence')
    }
  }

  async function handleDelete(id) {
    try {
      await deleteSequence(id)
      setSequences(prev => prev.filter(s => s.id !== id))
    } catch {
      setError('Failed to delete sequence')
    }
  }

  function handleFastaUpload(e) {
    const file = e.target.files[0]
    if (!file) return
    const reader = new FileReader()
    reader.onload = async (ev) => {
      const text = ev.target.result
      const lines = text.trim().split('\n')
      const header = lines.find(l => l.startsWith('>')) ?? ''
      const name = header.slice(1).trim().split(/\s+/)[0] || file.name.replace('.fasta','').replace('.fa','')
      const seq  = lines.filter(l => !l.startsWith('>')).join('').replace(/\s/g, '').toUpperCase()
      if (!seq) return

      try {
        await saveSequence(name, seq, 'uploaded')
        reload()
      } catch {
        setError('Failed to save uploaded sequence')
      }
    }
    reader.readAsText(file)
    e.target.value = ''
  }

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 16 }}>
      {/* header row */}
      <div style={{
        display: 'flex', alignItems: 'center', justifyContent: 'space-between',
        background: T.surface, border: `0.5px solid ${T.border}`,
        borderRadius: 8, padding: '12px 16px',
      }}>
        <span style={{ fontSize: 12, color: T.muted }}>
          {sequences.length} saved sequence{sequences.length !== 1 ? 's' : ''}
        </span>
        <div style={{ display: 'flex', gap: 8 }}>
          <input
            ref={fileRef}
            type="file"
            accept=".fasta,.fa,.txt"
            style={{ display: 'none' }}
            onChange={handleFastaUpload}
          />
          <button
            onClick={() => fileRef.current?.click()}
            style={{
              padding: '6px 14px', borderRadius: 6, fontSize: 12,
              border: `0.5px solid ${T.border2}`, color: T.mid,
              background: 'transparent', cursor: 'pointer',
              transition: 'color 0.15s, border-color 0.15s',
            }}
            onMouseEnter={e => { e.currentTarget.style.color = T.teal; e.currentTarget.style.borderColor = T.teal }}
            onMouseLeave={e => { e.currentTarget.style.color = T.mid;  e.currentTarget.style.borderColor = T.border2 }}
          >
            Upload FASTA
          </button>
        </div>
      </div>

      {error && (
        <div style={{
          padding: '8px 14px', background: '#1a0808', border: '0.5px solid #4a1010',
          borderRadius: 6, color: T.red, fontSize: 12,
        }}>
          {error}
        </div>
      )}

      {loading ? (
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(280px, 1fr))', gap: 12 }}>
          {Array.from({ length: 3 }, (_, i) => <SkeletonCard key={i} />)}
        </div>
      ) : sequences.length === 0 ? (
        <div style={{
          display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center',
          padding: '64px 0', gap: 10,
        }}>
          <div style={{ color: T.muted, fontSize: 13 }}>No saved sequences yet</div>
          <div style={{ color: T.muted, fontSize: 12, opacity: 0.7 }}>
            Sequences you save from the Sandbox will appear here
          </div>
        </div>
      ) : (
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(280px, 1fr))', gap: 12 }}>
          {sequences.map(seq => (
            <SeqCard
              key={seq.id}
              seq={seq}
              onLoad={handleLoad}
              onDelete={handleDelete}
            />
          ))}
        </div>
      )}
    </div>
  )
}

// ─── gRNA libraries tab (placeholder) ────────────────────────────────────────

function GrnaLibrariesTab() {
  return (
    <div style={{
      background: T.surface, border: `0.5px solid ${T.border}`,
      borderRadius: 8, padding: '48px 32px',
      display: 'flex', flexDirection: 'column', alignItems: 'center', gap: 12,
    }}>
      <div style={{ fontSize: 14, color: T.text, fontWeight: 500 }}>
        Coming soon — Brunello and GeCKO libraries
      </div>
      <div style={{
        fontSize: 12, color: T.muted, textAlign: 'center', lineHeight: 1.7,
        maxWidth: 420,
      }}>
        Genome-wide CRISPR knockout libraries (Brunello, GeCKO v2, Brie) will be searchable here.
        You'll be able to look up pre-validated gRNA sequences for any human or mouse gene
        and load them directly into the Sandbox.
      </div>
    </div>
  )
}

// ─── main page ────────────────────────────────────────────────────────────────

export default function Library() {
  const [activeTab, setActiveTab] = useState('Gene Database')

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 16 }}>
      {/* spinner keyframe */}
      <style>{`@keyframes spin{to{transform:rotate(360deg)}}`}</style>

      {/* tab bar */}
      <div style={{
        background: T.surface, border: `0.5px solid ${T.border}`,
        borderRadius: 8, overflow: 'hidden',
      }}>
        <div style={{
          display: 'flex', borderBottom: `0.5px solid ${T.border}`,
        }}>
          {TABS.map(tab => (
            <button
              key={tab}
              onClick={() => setActiveTab(tab)}
              style={{
                padding: '10px 18px', fontSize: 13, fontWeight: 400,
                color: activeTab === tab ? T.amber : T.muted,
                background: 'transparent', border: 'none',
                borderBottom: `2px solid ${activeTab === tab ? T.amber : 'transparent'}`,
                cursor: 'pointer', transition: 'color 0.15s', whiteSpace: 'nowrap',
              }}
            >
              {tab}
            </button>
          ))}
        </div>

        <div style={{ padding: 16 }}>
          {activeTab === 'Gene Database'   && <GeneDatabaseTab />}
          {activeTab === 'gRNA Libraries'  && <GrnaLibrariesTab />}
          {activeTab === 'My Sequences'    && <MySequencesTab />}
        </div>
      </div>
    </div>
  )
}
