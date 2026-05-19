import { createContext, useContext, useState } from 'react'

const HelixCtx = createContext(null)

export function HelixProvider({ children }) {
  const [sequence,        setSequence]        = useState(() => localStorage.getItem('helix_sandbox_sequence') || '')
  const [enzyme,          setEnzyme]          = useState('SpCas9')
  const [grnas,           setGrnas]           = useState([])
  const [topGuide,        setTopGuide]        = useState(null)
  const [proteinSequence, setProteinSequence] = useState('')
  const [selectedOrf,     setSelectedOrf]     = useState(null)
  const [selectedGuide,   setSelectedGuide]   = useState(null)
  const [analysisResults, setAnalysisResults] = useState(null)

  function update(patch) {
    if ('sequence' in patch) {
      const v = patch.sequence ?? ''
      localStorage.setItem('helix_sandbox_sequence', v)
      setSequence(v)
    }
    if ('enzyme'          in patch) setEnzyme(patch.enzyme)
    if ('grnas'           in patch) setGrnas(patch.grnas)
    if ('topGuide'        in patch) setTopGuide(patch.topGuide)
    if ('proteinSequence' in patch) setProteinSequence(patch.proteinSequence)
    if ('selectedOrf'     in patch) setSelectedOrf(patch.selectedOrf)
    if ('selectedGuide'   in patch) setSelectedGuide(patch.selectedGuide)
    if ('analysisResults' in patch) setAnalysisResults(patch.analysisResults)
  }

  return (
    <HelixCtx.Provider value={{ sequence, enzyme, grnas, topGuide, proteinSequence, selectedOrf, selectedGuide, analysisResults, update }}>
      {children}
    </HelixCtx.Provider>
  )
}

export function useHelixStore() {
  const ctx = useContext(HelixCtx)
  if (!ctx) throw new Error('useHelixStore must be used within HelixProvider')
  return ctx
}
