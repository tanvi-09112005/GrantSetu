import axios from 'axios'
import { getAccessToken } from './supabase'

export const api = axios.create({
  baseURL: import.meta.env.VITE_API_BASE_URL ?? '/api',
})

// Every NGO-scoped endpoint authenticates with the Supabase session JWT.
api.interceptors.request.use(async (config) => {
  const token = await getAccessToken()
  if (token) config.headers.Authorization = `Bearer ${token}`
  return config
})

export const getHealth = () => api.get('/health').then((r) => r.data)
export const getGraphShape = () => api.get('/graph').then((r) => r.data)
export const getSampleProfiles = () => api.get('/sample-ngos/profiles').then((r) => r.data)
export const autoConfirmEmail = (email) => api.post('/auth/auto-confirm', { email }).then((r) => r.data)

// NGO Profile
export const createProfile = (payload) => api.post('/ngo/profile', payload).then((r) => r.data)
export const updateProfile = (ngoId, payload) => api.put(`/ngo/profile/${ngoId}`, payload).then((r) => r.data)
export const listProfiles = () => api.get('/ngo/profile').then((r) => r.data)
export const getProfile = (ngoId) => api.get(`/ngo/profile/${ngoId}`).then((r) => r.data)

// Documents
export const listDocuments = (ngoId) =>
  api.get('/ngo/documents', { params: { ngo_id: ngoId } }).then((r) => r.data)

export const uploadDocument = (ngoId, docType, file) => {
  const formData = new FormData()
  formData.append('ngo_id', ngoId)
  formData.append('doc_type', docType)
  formData.append('file', file)
  return api.post('/ngo/documents', formData, {
    headers: { 'Content-Type': 'multipart/form-data' },
  }).then((r) => r.data)
}

export const attachCertifiedDocument = (ngoId, docType = 'annual_report', sampleKey = 'cry-india') =>
  api.post('/ngo/documents/attach-certified', {
    ngo_id: ngoId,
    doc_type: docType,
    sample_key: sampleKey,
  }).then((r) => r.data)

export const getDocumentStatus = (documentId) =>
  api.get(`/ngo/documents/${documentId}/status`).then((r) => r.data)

// Grants & Discovery (Phase 2)
export const listGrants = (limit = 50, offset = 0) =>
  api.get('/grants', { params: { limit, offset } }).then((r) => r.data)

export const discoverGrants = (ngoId, topK = 5, query = '') =>
  api.get('/grants/discover', {
    params: { ngo_id: ngoId, top_k: topK, ...(query ? { q: query } : {}) },
  }).then((r) => r.data)

// Eligibility Rules Engine (Phase 2)
export const checkEligibility = (ngoId, grantId) =>
  api.post('/eligibility/check', { ngo_id: ngoId, grant_id: grantId }).then((r) => r.data)

