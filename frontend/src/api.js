import axios from 'axios'

const api = axios.create({ baseURL: 'http://localhost:8000' })

export const analyzeGrnas = (sequence, enzyme = 'SpCas9', scanReverse = false) =>
  api.post('/api/grnas', { sequence, enzyme, scan_reverse: scanReverse }).then(r => r.data)

export const getGcTrack = (sequence, enzyme = 'SpCas9') =>
  analyzeGrnas(sequence, enzyme, false)

export const scoreguides = (guides) =>
  api.post('/api/score', { guides }).then(r => r.data)

export const getSessions = (username) =>
  api.get('/api/sessions', { params: { username } }).then(r => r.data)

export const saveSession = (username, name, payload) =>
  api.post('/api/sessions/save', { username, name, payload }).then(r => r.data)

export const translateProtein = (sequence, frame = 0) =>
  api.post('/api/protein/translate', { sequence, frame }).then(r => r.data)

export const analyzeProtein = (protein) =>
  api.post('/api/protein/analyze', { protein }).then(r => r.data)

export const compareVariants = (sequence, reference) =>
  api.post('/api/variants', { sequence, reference }).then(r => r.data)

export const findOrfs = (sequence, minLength = 100) =>
  api.post('/api/orfs', { sequence, min_length: minLength }).then(r => r.data)

export const searchGenes = (query, organism = 'human') =>
  api.get('/api/genes/search', { params: { query, organism } }).then(r => r.data)

export const fetchGeneSequence = (accession) =>
  api.get(`/api/genes/fetch/${accession}`).then(r => r.data)

export const getCommonGenes = () =>
  api.get('/api/genes/common').then(r => r.data)

export const saveSequence = (name, sequence, organism = 'unknown') =>
  api.post('/api/sequences/save', { name, sequence, organism }).then(r => r.data)

export const listSequences = () =>
  api.get('/api/sequences').then(r => r.data)

export const getSequence = (id) =>
  api.get(`/api/sequences/${id}`).then(r => r.data)

export const deleteSequence = (id) =>
  api.delete(`/api/sequences/${id}`).then(r => r.data)

export const findOffTargets = (guide, sequence, maxMismatches = 3) =>
  api.post('/api/offtarget', { guide, sequence, max_mismatches: maxMismatches }).then(r => r.data)

export const designPrimers = (sequence, cutPosition, editType, editSequence, editPosition, editLength) =>
  api.post('/api/primers/design', {
    sequence, cut_position: cutPosition, edit_type: editType,
    edit_sequence: editSequence, edit_position: editPosition, edit_length: editLength,
  }).then(r => r.data)

export const chatWithAI = (message, context = {}) => {
  const body = {
    message,
    context: {
      sequence:   context.sequence   || '',
      enzyme:     context.enzyme     || 'SpCas9',
      grna_count: context.grna_count || 0,
      top_guide:  context.top_guide  || '',
      top_score:  context.top_score  || 0.0,
    },
  }
  console.log('chatWithAI request body:', JSON.stringify(body, null, 2))
  return api.post('/api/ai/chat', body).then(r => r.data)
}

export default api
