import React, { useState, useEffect, useRef } from 'react'
import { uploadDocument, listDocuments, attachCertifiedDocument } from '../lib/api'
import {
  ShieldCheck,
  UploadCloud,
  FileText,
  CheckCircle2,
  AlertCircle,
  Loader2,
  Database,
  Sparkles,
  Zap,
  Info,
  Clock,
  Layers,
} from 'lucide-react'

const STATUTORY_DOC_TYPES = [
  {
    value: 'registration',
    label: 'Registration Certificate / Darpan Proof',
    desc: 'Proves legal entity status (Trust Deed, Society Registration, or NITI Aayog Darpan acknowledgement)',
  },
  {
    value: '12a_80g',
    label: '12A & 80G Tax Exemption Certificates',
    desc: 'Income Tax department exemption orders under Section 12A/12AB and 80G',
  },
  {
    value: 'annual_report',
    label: 'Audited Financials & Annual Activity Report',
    desc: 'Audited balance sheet, expenditure report, and programmatic metrics for operational vintage proof',
  },
  {
    value: 'fcra',
    label: 'MHA FCRA Registration Certificate',
    desc: 'Ministry of Home Affairs permission letter to accept foreign contributions',
  },
]

export default function DocumentUploadCard({ ngoId, ngoProfile, onDocumentCountChange }) {
  const [documents, setDocuments] = useState([])
  const [loadingDocs, setLoadingDocs] = useState(false)
  const [selectedType, setSelectedType] = useState('annual_report')
  const [uploading, setUploading] = useState(false)
  const [attachingSample, setAttachingSample] = useState(false)
  const [error, setError] = useState(null)
  const [successMsg, setSuccessMsg] = useState(null)
  const fileInputRef = useRef(null)

  const fetchDocs = async () => {
    if (!ngoId) return
    setLoadingDocs(true)
    try {
      const data = await listDocuments(ngoId)
      setDocuments(data || [])
      if (onDocumentCountChange) onDocumentCountChange((data || []).length)
    } catch (err) {
      console.error('Failed to list documents:', err)
    } finally {
      setLoadingDocs(false)
    }
  }

  useEffect(() => {
    fetchDocs()
  }, [ngoId])

  const handle1ClickAttach = async () => {
    if (!ngoId) {
      setError('Please select or register an active NGO profile first.')
      return
    }

    setAttachingSample(true)
    setError(null)
    setSuccessMsg(null)

    // Map NGO name or preset to sample key
    let sampleKey = 'cry-india'
    const nameLower = (ngoProfile?.name || '').toLowerCase()
    if (nameLower.includes('pratham')) sampleKey = 'pratham-education'
    else if (nameLower.includes('goonj')) sampleKey = 'goonj'
    else if (nameLower.includes('akshaya')) sampleKey = 'akshaya-patra'

    try {
      const res = await attachCertifiedDocument(ngoId, selectedType, sampleKey)
      setSuccessMsg(
        `Successfully attached and processed certified statutory pack for ${ngoProfile?.name || 'NGO'} (${res.chunk_count} vector chunks indexed in Supabase DB)!`
      )
      await fetchDocs()
    } catch (err) {
      setError(err.response?.data?.detail || err.message || 'Failed to attach certified document')
    } finally {
      setAttachingSample(false)
    }
  }

  const handleFileUpload = async (e) => {
    e.preventDefault()
    const file = fileInputRef.current?.files?.[0]
    if (!ngoId) {
      setError('Please select or register an active NGO profile first.')
      return
    }
    if (!file) {
      setError('Please select a PDF document from your device.')
      return
    }

    setUploading(true)
    setError(null)
    setSuccessMsg(null)

    try {
      const res = await uploadDocument(ngoId, selectedType, file)
      setSuccessMsg(`Document "${file.name}" ingested successfully into database (${res.chunk_count} chunks indexed)!`)
      if (fileInputRef.current) fileInputRef.current.value = ''
      await fetchDocs()
    } catch (err) {
      setError(err.response?.data?.detail || err.message || 'Upload failed')
    } finally {
      setUploading(false)
    }
  }

  return (
    <div className="space-y-6">
      {/* Educational Banner Explaining Documents */}
      <div className="rounded-xl border border-blue-100 bg-blue-50/60 p-5 text-xs text-blue-900 shadow-2xs">
        <div className="flex items-start gap-3">
          <Info className="size-5 text-blue-600 shrink-0 mt-0.5" />
          <div className="space-y-2">
            <h4 className="font-semibold text-sm text-blue-950">
              Why Are Documents Required for NGO Grant Portals?
            </h4>
            <p className="text-blue-800 leading-relaxed">
              When an Indian NGO applies for Government Grant-in-Aid, CSR funding, or International grants, funders require two types of documentation:
            </p>
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-3 pt-1">
              <div className="rounded-lg bg-white/80 p-3 border border-blue-200">
                <span className="font-semibold text-blue-900 block mb-1">1. Statutory Identity & Tax Status</span>
                <span className="text-neutral-600">
                  <strong>NITI Aayog Darpan Certificate</strong>, <strong>12A Registration</strong>, and <strong>80G Approval</strong> prove that your organization is legitimate, non-profit, and legally allowed to receive grant funding.
                </span>
              </div>
              <div className="rounded-lg bg-white/80 p-3 border border-blue-200">
                <span className="font-semibold text-blue-900 block mb-1">2. Audited Financials & Past Impact</span>
                <span className="text-neutral-600">
                  Funders require <strong>Audited Balance Sheets & Annual Activity Reports</strong> to verify operating vintage (3+ years) and past budget spend. GrantSetu also chunks this data so the AI can draft verified proposals with real numbers.
                </span>
              </div>
            </div>
          </div>
        </div>
      </div>

      {/* Main Document Vault Action Card */}
      <div className="rounded-xl border border-neutral-200 bg-white p-6 shadow-xs">
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2 mb-6">
          <div>
            <h3 className="text-lg font-semibold text-neutral-900 flex items-center gap-2">
              <ShieldCheck className="size-5 text-indigo-600" />
              Compliance Document Vault
            </h3>
            <p className="text-xs text-neutral-500 mt-1">
              Active Organization: <strong className="text-neutral-900 font-semibold">{ngoProfile?.name || 'No NGO Selected'}</strong>
            </p>
          </div>
          <span className="inline-flex items-center gap-1.5 rounded-full bg-neutral-100 px-3 py-1 text-xs font-medium text-neutral-700">
            <Database className="size-3.5 text-indigo-600" />
            {documents.length} Documents in Database
          </span>
        </div>

        {error && (
          <div className="mb-5 flex items-center gap-2 rounded-lg bg-red-50 p-3 text-xs text-red-700 border border-red-200">
            <AlertCircle className="size-4 shrink-0" />
            <span>{error}</span>
          </div>
        )}

        {successMsg && (
          <div className="mb-5 flex items-center gap-2 rounded-lg bg-emerald-50 p-3 text-xs text-emerald-800 border border-emerald-200">
            <CheckCircle2 className="size-4 shrink-0" />
            <span>{successMsg}</span>
          </div>
        )}

        {/* 1-Click Fast Verification Pack */}
        <div className="rounded-xl bg-linear-to-r from-indigo-50/80 via-purple-50/50 to-white border border-indigo-200 p-5 mb-6">
          <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
            <div className="space-y-1">
              <div className="flex items-center gap-2">
                <Zap className="size-4 text-amber-500 fill-amber-500" />
                <h4 className="font-semibold text-sm text-neutral-900">
                  Don't have compliance documents on your machine?
                </h4>
              </div>
              <p className="text-xs text-neutral-600 max-w-xl">
                One-click attach the official certified statutory filing & audit report for{' '}
                <strong>{ngoProfile?.name || 'this NGO'}</strong>. GrantSetu will instantly parse, verify Darpan credentials, and index text chunks into Supabase pgvector!
              </p>
            </div>

            <button
              type="button"
              disabled={attachingSample || !ngoId}
              onClick={handle1ClickAttach}
              className="inline-flex items-center justify-center gap-2 rounded-xl bg-indigo-600 hover:bg-indigo-700 px-5 py-2.5 text-xs font-semibold text-white transition shadow-sm disabled:opacity-50 shrink-0 cursor-pointer"
            >
              {attachingSample ? (
                <>
                  <Loader2 className="size-4 animate-spin" />
                  <span>Processing & Indexing...</span>
                </>
              ) : (
                <>
                  <Sparkles className="size-4" />
                  <span>⚡ 1-Click Attach Certified Pack</span>
                </>
              )}
            </button>
          </div>
        </div>

        {/* Manual Upload Section */}
        <div className="border-t border-neutral-100 pt-5">
          <h4 className="text-xs font-semibold text-neutral-700 uppercase tracking-wide mb-3">
            Or Upload Your Organization's Own PDF
          </h4>

          <form onSubmit={handleFileUpload} className="space-y-4">
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              <div>
                <label className="block text-xs font-medium text-neutral-700 mb-1.5">
                  Document Type
                </label>
                <select
                  value={selectedType}
                  onChange={(e) => setSelectedType(e.target.value)}
                  className="w-full rounded-lg border border-neutral-300 px-3 py-2 text-xs bg-white focus:ring-2 focus:ring-indigo-500/20"
                >
                  {STATUTORY_DOC_TYPES.map((t) => (
                    <option key={t.value} value={t.value}>
                      {t.label}
                    </option>
                  ))}
                </select>
                <p className="mt-1 text-[11px] text-neutral-500">
                  {STATUTORY_DOC_TYPES.find((t) => t.value === selectedType)?.desc}
                </p>
              </div>

              <div>
                <label className="block text-xs font-medium text-neutral-700 mb-1.5">
                  Select Document File (.PDF)
                </label>
                <input
                  ref={fileInputRef}
                  type="file"
                  accept=".pdf"
                  className="w-full rounded-lg border border-neutral-300 px-3 py-1.5 text-xs file:mr-3 file:py-1 file:px-3 file:rounded-md file:border-0 file:text-xs file:font-semibold file:bg-neutral-100 file:text-neutral-700 hover:file:bg-neutral-200 cursor-pointer"
                />
              </div>
            </div>

            <div className="flex justify-end">
              <button
                type="submit"
                disabled={uploading || !ngoId}
                className="inline-flex items-center gap-2 rounded-lg bg-neutral-900 hover:bg-neutral-800 text-white px-4 py-2 text-xs font-medium transition disabled:opacity-50"
              >
                {uploading ? (
                  <>
                    <Loader2 className="size-3.5 animate-spin" />
                    <span>Ingesting PDF into Database...</span>
                  </>
                ) : (
                  <>
                    <UploadCloud className="size-3.5" />
                    <span>Upload & Process Document</span>
                  </>
                )}
              </button>
            </div>
          </form>
        </div>

        {/* Vault Table */}
        <div className="mt-8 pt-6 border-t border-neutral-200">
          <h4 className="text-xs font-semibold text-neutral-800 uppercase tracking-wider mb-3 flex items-center justify-between">
            <span>Verified Documents in Vault ({documents.length})</span>
            {loadingDocs && <Loader2 className="size-3 animate-spin text-neutral-400" />}
          </h4>

          {documents.length > 0 ? (
            <div className="overflow-x-auto rounded-xl border border-neutral-200">
              <table className="w-full text-left text-xs">
                <thead className="bg-neutral-50 text-neutral-500 uppercase border-b border-neutral-200">
                  <tr>
                    <th className="py-2.5 px-3">Document Title</th>
                    <th className="py-2.5 px-3">Category</th>
                    <th className="py-2.5 px-3">Ingestion Pipeline</th>
                    <th className="py-2.5 px-3 text-right">Extracted Chunks</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-neutral-100">
                  {documents.map((doc) => (
                    <tr key={doc.id} className="hover:bg-neutral-50/50">
                      <td className="py-3 px-3 font-medium text-neutral-900 flex items-center gap-2">
                        <FileText className="size-4 text-indigo-600 shrink-0" />
                        <span className="truncate max-w-xs">{doc.file_url || 'StatutoryDocument.pdf'}</span>
                      </td>
                      <td className="py-3 px-3 text-neutral-600 capitalize">
                        {doc.doc_type?.replace('_', ' ')}
                      </td>
                      <td className="py-3 px-3">
                        <span className="inline-flex items-center gap-1 rounded-full bg-emerald-50 px-2 py-0.5 text-[11px] font-semibold text-emerald-700 border border-emerald-200">
                          <CheckCircle2 className="size-3" />
                          {doc.ingest_status || 'Ready'}
                        </span>
                      </td>
                      <td className="py-3 px-3 text-right font-mono font-medium text-indigo-700">
                        {doc.chunk_count || 1} chunks
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          ) : (
            <div className="rounded-xl border border-dashed border-neutral-300 p-8 text-center text-xs text-neutral-500">
              No documents attached yet. Click <strong>&quot;⚡ 1-Click Attach Certified Pack&quot;</strong> above to instantly add verified credentials!
            </div>
          )}
        </div>
      </div>
    </div>
  )
}
