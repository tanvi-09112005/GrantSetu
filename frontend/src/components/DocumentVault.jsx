import React, { useCallback, useEffect, useMemo, useRef, useState } from 'react'
import { Link } from 'react-router-dom'
import {
  listDocuments,
  uploadDocument,
  deleteDocument,
  listAssets,
  uploadAsset,
  deleteAsset,
} from '../lib/api'
import { useApp } from '../context/AppContext'
import LoadingSpinner from './common/LoadingSpinner'
import {
  ShieldCheck,
  Landmark,
  TrendingUp,
  Palette,
  UploadCloud,
  FileText,
  CheckCircle2,
  AlertCircle,
  Loader2,
  Trash2,
  ImagePlus,
  Plus,
  Building2,
} from 'lucide-react'

// ---------------------------------------------------------------------------
// Vault layout. `type` is the value stored in ngo_documents.doc_type.
// ---------------------------------------------------------------------------
const CATEGORIES = [
  {
    id: 'statutory',
    title: 'Statutory Documents',
    blurb: 'Proof of legal status and tax exemptions funders check first.',
    icon: ShieldCheck,
    slots: [
      { type: 'darpan_certificate', label: 'Darpan Certificate', desc: 'NITI Aayog NGO Darpan registration certificate' },
      { type: 'cert_12a', label: '12A / 12AB Certificate', desc: 'Income-tax registration for tax-exempt status' },
      { type: 'cert_80g', label: '80G Certificate', desc: 'Lets donors claim a tax deduction' },
      { type: 'cert_fcra', label: 'FCRA Certificate', desc: 'MHA permission to accept foreign contributions' },
      { type: 'csr1', label: 'CSR-1 Registration', desc: 'MCA Form CSR-1 acknowledgement for receiving CSR funds' },
    ],
  },
  {
    id: 'financial',
    title: 'Financial & Audits',
    blurb: 'Audited numbers back every budget and financial claim in a proposal.',
    icon: Landmark,
    slots: [
      { type: 'audited_balance_sheet', label: 'Audited Balance Sheets', desc: 'Balance sheet, income & expenditure, auditor report' },
      { type: 'itr7', label: 'ITR-7 Returns', desc: 'Income-tax return filed by the trust / society' },
      { type: 'annual_budget', label: 'Annual Financial Budget', desc: 'Approved programme-wise budget for the year' },
    ],
  },
  {
    id: 'impact',
    title: 'Past Impact & Reports',
    blurb: 'The evidence GrantSetu draws on when drafting and fact-checking proposals.',
    icon: TrendingUp,
    slots: [
      { type: 'past_proposal', label: 'Past Winning Proposals', desc: 'Proposals that were funded before' },
      { type: 'annual_report', label: 'Annual Reports', desc: 'Yearly activity and impact report' },
      { type: 'project_plan', label: 'Project Plans', desc: 'Detailed plans, logframes and timelines' },
    ],
  },
]

const BRANDING_SLOTS = [
  { type: 'logo', label: 'Official Logo', desc: 'Used on proposal cover pages' },
  { type: 'stamp', label: 'Rubber Stamp / Seal', desc: 'Applied on the exported PDF' },
  { type: 'signature', label: 'Authorized Signatory Signature', desc: 'Applied on the exported PDF' },
]

const MAX_PDF_MB = 10
const MAX_IMAGE_KB = 1024

const SLOT_TYPES = new Set(CATEGORIES.flatMap((c) => c.slots.map((s) => s.type)))
const TOTAL_SLOTS = SLOT_TYPES.size + BRANDING_SLOTS.length

function errorText(err, fallback) {
  const detail = err?.response?.data?.detail
  return typeof detail === 'string' ? detail : err?.message || fallback
}

function pdfProblem(file) {
  const isPdf = file.type === 'application/pdf' || file.name.toLowerCase().endsWith('.pdf')
  if (!isPdf) return 'Only PDF files are accepted'
  if (file.size > MAX_PDF_MB * 1024 * 1024) return `File is larger than ${MAX_PDF_MB} MB`
  return null
}

function imageProblem(file) {
  const isPng = file.type === 'image/png' || file.name.toLowerCase().endsWith('.png')
  if (!isPng) return 'Only PNG images are accepted (transparent PNG recommended)'
  if (file.size > MAX_IMAGE_KB * 1024) return 'Image is larger than 1 MB'
  return null
}

// Chequerboard so transparent PNGs are visibly transparent.
const CHECKER = {
  backgroundImage:
    'linear-gradient(45deg,#e5e5e5 25%,transparent 25%),linear-gradient(-45deg,#e5e5e5 25%,transparent 25%),linear-gradient(45deg,transparent 75%,#e5e5e5 75%),linear-gradient(-45deg,transparent 75%,#e5e5e5 75%)',
  backgroundSize: '16px 16px',
  backgroundPosition: '0 0, 0 8px, 8px -8px, -8px 0',
  backgroundColor: '#fff',
}

function StatusChip({ docs }) {
  if (docs.some((d) => d.ingest_status === 'failed') && !docs.some((d) => d.ingest_status === 'ready')) {
    return <span className="rounded-full bg-red-50 text-red-700 border border-red-200 px-2 py-0.5 text-[10px] font-bold">Failed</span>
  }
  if (docs.length === 0) {
    return <span className="rounded-full bg-neutral-100 text-neutral-500 border border-neutral-200 px-2 py-0.5 text-[10px] font-bold">Empty</span>
  }
  if (docs.some((d) => d.ingest_status !== 'ready' && d.ingest_status !== 'failed')) {
    return <span className="rounded-full bg-amber-50 text-amber-700 border border-amber-200 px-2 py-0.5 text-[10px] font-bold">Processing</span>
  }
  return (
    <span className="inline-flex items-center gap-1 rounded-full bg-emerald-50 text-emerald-700 border border-emerald-200 px-2 py-0.5 text-[10px] font-bold">
      <CheckCircle2 className="size-3" /> Ready
    </span>
  )
}

// ---------------------------------------------------------------------------
// One PDF upload tile
// ---------------------------------------------------------------------------
function DocTile({ slot, docs, busy, error, onPick, onDelete }) {
  const inputRef = useRef(null)
  return (
    <div className="rounded-xl border border-neutral-200 bg-white p-4 flex flex-col gap-3 shadow-2xs">
      <div className="flex items-start justify-between gap-2">
        <div>
          <p className="text-sm font-semibold text-neutral-900">{slot.label}</p>
          <p className="text-[11px] text-neutral-500 mt-0.5">{slot.desc}</p>
        </div>
        <StatusChip docs={docs} />
      </div>

      {docs.length > 0 && (
        <ul className="space-y-1.5">
          {docs.map((d) => (
            <li key={d.id} className="flex items-center justify-between gap-2 rounded-lg bg-neutral-50 border border-neutral-200 px-2.5 py-1.5 text-xs">
              <span className="flex items-center gap-1.5 min-w-0">
                <FileText className="size-3.5 text-indigo-500 shrink-0" />
                <span className="truncate" title={d.file_url}>{d.file_url || 'document.pdf'}</span>
              </span>
              <span className="flex items-center gap-2 shrink-0 text-neutral-500">
                {d.ingest_status === 'ready' && <span>{d.chunk_count} chunks</span>}
                {d.ingest_status === 'failed' && (
                  <span className="text-red-600" title={d.ingest_error || ''}>failed</span>
                )}
                <button
                  type="button"
                  onClick={() => onDelete(d)}
                  className="text-neutral-400 hover:text-red-600 cursor-pointer"
                  title="Remove this file"
                >
                  <Trash2 className="size-3.5" />
                </button>
              </span>
            </li>
          ))}
        </ul>
      )}

      {error && (
        <p className="flex items-start gap-1.5 text-[11px] text-red-600">
          <AlertCircle className="size-3.5 shrink-0 mt-px" /> {error}
        </p>
      )}

      <button
        type="button"
        disabled={busy}
        onClick={() => inputRef.current?.click()}
        className="mt-auto inline-flex items-center justify-center gap-1.5 rounded-lg border border-dashed border-neutral-300 hover:border-indigo-400 hover:bg-indigo-50/40 py-2 text-xs font-semibold text-neutral-600 hover:text-indigo-700 disabled:opacity-60 cursor-pointer transition"
      >
        {busy ? <Loader2 className="size-4 animate-spin" /> : <UploadCloud className="size-4" />}
        {busy ? 'Uploading & indexing…' : docs.length ? 'Add another PDF' : 'Upload PDF'}
      </button>
      <input
        ref={inputRef}
        type="file"
        accept="application/pdf,.pdf"
        className="hidden"
        onChange={(ev) => {
          const file = ev.target.files?.[0]
          ev.target.value = ''
          if (file) onPick(slot.type, file)
        }}
      />
    </div>
  )
}

// ---------------------------------------------------------------------------
// One branding image tile, with instant preview
// ---------------------------------------------------------------------------
function ImageTile({ slot, asset, previewUrl, busy, error, onPick, onDelete }) {
  const inputRef = useRef(null)
  const shown = previewUrl || asset?.data_url
  return (
    <div className="rounded-xl border border-neutral-200 bg-white p-4 flex flex-col gap-3 shadow-2xs">
      <div className="flex items-start justify-between gap-2">
        <div>
          <p className="text-sm font-semibold text-neutral-900">{slot.label}</p>
          <p className="text-[11px] text-neutral-500 mt-0.5">{slot.desc}</p>
        </div>
        {shown ? (
          <span className="inline-flex items-center gap-1 rounded-full bg-emerald-50 text-emerald-700 border border-emerald-200 px-2 py-0.5 text-[10px] font-bold">
            <CheckCircle2 className="size-3" /> Saved
          </span>
        ) : (
          <span className="rounded-full bg-neutral-100 text-neutral-500 border border-neutral-200 px-2 py-0.5 text-[10px] font-bold">Empty</span>
        )}
      </div>

      <div
        className="relative flex h-32 items-center justify-center rounded-lg border border-neutral-200 overflow-hidden"
        style={CHECKER}
      >
        {shown ? (
          <img src={shown} alt={slot.label} className="max-h-full max-w-full object-contain" />
        ) : (
          <ImagePlus className="size-8 text-neutral-300" />
        )}
        {busy && (
          <div className="absolute inset-0 flex items-center justify-center bg-white/70">
            <Loader2 className="size-5 animate-spin text-indigo-600" />
          </div>
        )}
      </div>

      {error && (
        <p className="flex items-start gap-1.5 text-[11px] text-red-600">
          <AlertCircle className="size-3.5 shrink-0 mt-px" /> {error}
        </p>
      )}

      <div className="mt-auto flex gap-2">
        <button
          type="button"
          disabled={busy}
          onClick={() => inputRef.current?.click()}
          className="flex-1 inline-flex items-center justify-center gap-1.5 rounded-lg border border-dashed border-neutral-300 hover:border-indigo-400 hover:bg-indigo-50/40 py-2 text-xs font-semibold text-neutral-600 hover:text-indigo-700 disabled:opacity-60 cursor-pointer transition"
        >
          <UploadCloud className="size-4" />
          {shown ? 'Replace PNG' : 'Upload PNG'}
        </button>
        {asset && (
          <button
            type="button"
            disabled={busy}
            onClick={() => onDelete(slot.type)}
            className="rounded-lg border border-neutral-200 px-2.5 text-neutral-400 hover:text-red-600 hover:border-red-200 cursor-pointer"
            title="Remove image"
          >
            <Trash2 className="size-4" />
          </button>
        )}
      </div>
      <input
        ref={inputRef}
        type="file"
        accept="image/png,.png"
        className="hidden"
        onChange={(ev) => {
          const file = ev.target.files?.[0]
          ev.target.value = ''
          if (file) onPick(slot.type, file)
        }}
      />
    </div>
  )
}

// ---------------------------------------------------------------------------
// The vault
// ---------------------------------------------------------------------------
export default function DocumentVault({ ngoId, onDocumentCountChange }) {
  const { user } = useApp()
  const [docs, setDocs] = useState([])
  const [assets, setAssets] = useState([])
  const [loading, setLoading] = useState(true)
  const [loadError, setLoadError] = useState(null)
  const [busy, setBusy] = useState({}) // slotType -> true while uploading
  const [errors, setErrors] = useState({}) // slotType -> message
  const [previews, setPreviews] = useState({}) // assetType -> blob URL (instant preview)

  const refresh = useCallback(async () => {
    if (!ngoId || !user) {
      setDocs([])
      setAssets([])
      setLoading(false)
      return
    }
    try {
      const [d, a] = await Promise.all([listDocuments(ngoId), listAssets(ngoId)])
      setDocs(d || [])
      setAssets(a || [])
      setLoadError(null)
      onDocumentCountChange?.((d || []).length)
    } catch (err) {
      setLoadError(errorText(err, 'Could not load your vault'))
    } finally {
      setLoading(false)
    }
  }, [ngoId, user, onDocumentCountChange])

  useEffect(() => {
    setLoading(true)
    refresh()
  }, [ngoId, user]) // eslint-disable-line react-hooks/exhaustive-deps

  const setSlotBusy = (type, value) => setBusy((b) => ({ ...b, [type]: value }))
  const setSlotError = (type, msg) => setErrors((e) => ({ ...e, [type]: msg }))

  const docsByType = useMemo(() => {
    const map = {}
    for (const d of docs) (map[d.doc_type] ||= []).push(d)
    return map
  }, [docs])

  const assetByType = useMemo(() => Object.fromEntries(assets.map((a) => [a.asset_type, a])), [assets])

  // Anything that doesn't belong to a named slot (older uploads, 'other').
  const otherDocs = useMemo(() => docs.filter((d) => !SLOT_TYPES.has(d.doc_type)), [docs])

  const filledSlots =
    [...SLOT_TYPES].filter((t) => (docsByType[t] || []).length > 0).length +
    BRANDING_SLOTS.filter((s) => assetByType[s.type]).length

  const handlePickDoc = async (type, file) => {
    setSlotError(type, null)
    const problem = pdfProblem(file)
    if (problem) return setSlotError(type, problem)
    setSlotBusy(type, true)
    try {
      await uploadDocument(ngoId, type, file)
      await refresh()
    } catch (err) {
      setSlotError(type, errorText(err, 'Upload failed'))
    } finally {
      setSlotBusy(type, false)
    }
  }

  const handleDeleteDoc = async (doc) => {
    if (!window.confirm(`Remove "${doc.file_url || 'this document'}" from your vault?`)) return
    try {
      await deleteDocument(doc.id)
      await refresh()
    } catch (err) {
      setSlotError(doc.doc_type, errorText(err, 'Could not remove the document'))
    }
  }

  const handlePickImage = async (type, file) => {
    setSlotError(type, null)
    const problem = imageProblem(file)
    if (problem) return setSlotError(type, problem)
    // Instant preview: show the local file immediately, confirm with the server after.
    const url = URL.createObjectURL(file)
    setPreviews((p) => ({ ...p, [type]: url }))
    setSlotBusy(type, true)
    try {
      await uploadAsset(ngoId, type, file)
      await refresh()
      setPreviews((p) => {
        const { [type]: old, ...rest } = p
        if (old) URL.revokeObjectURL(old)
        return rest
      })
    } catch (err) {
      setPreviews((p) => {
        const { [type]: old, ...rest } = p
        if (old) URL.revokeObjectURL(old)
        return rest
      })
      setSlotError(type, errorText(err, 'Upload failed'))
    } finally {
      setSlotBusy(type, false)
    }
  }

  const handleDeleteImage = async (type) => {
    try {
      await deleteAsset(ngoId, type)
      await refresh()
    } catch (err) {
      setSlotError(type, errorText(err, 'Could not remove the image'))
    }
  }

  // ----------------------------- empty / loading states ---------------------
  if (!user) {
    return (
      <div className="rounded-2xl border border-neutral-200 bg-white p-8 text-center text-sm text-neutral-600">
        <p className="font-semibold text-neutral-900">Sign in to open your document vault</p>
        <p className="mt-1 text-xs text-neutral-500">Your documents are private to your NGO account.</p>
      </div>
    )
  }
  if (!ngoId) {
    return (
      <div className="rounded-2xl border border-neutral-200 bg-white p-8 text-center">
        <Building2 className="mx-auto size-8 text-neutral-300" />
        <p className="mt-2 text-sm font-semibold text-neutral-900">No NGO registered on this account yet</p>
        <p className="mt-1 text-xs text-neutral-500">Register your NGO to start filling your vault.</p>
        <Link to="/register" className="mt-4 inline-block rounded-lg bg-indigo-600 hover:bg-indigo-700 text-white text-xs font-semibold px-4 py-2">
          Register your NGO
        </Link>
      </div>
    )
  }
  if (loading) return <LoadingSpinner message="Opening your document vault…" />

  const pct = Math.round((filledSlots / TOTAL_SLOTS) * 100)

  return (
    <div className="space-y-8">
      {/* Completeness */}
      <div className="rounded-2xl border border-neutral-200 bg-white p-5 shadow-2xs">
        <div className="flex items-center justify-between gap-4">
          <div>
            <h2 className="text-base font-bold text-neutral-900">Document Vault</h2>
            <p className="text-xs text-neutral-500 mt-0.5">
              {filledSlots} of {TOTAL_SLOTS} slots filled · every PDF is read and indexed so proposals can be fact-checked against it
            </p>
          </div>
          <span className="text-2xl font-black text-indigo-600">{pct}%</span>
        </div>
        <div className="mt-3 h-2 rounded-full bg-neutral-100 overflow-hidden">
          <div className="h-full rounded-full bg-indigo-600 transition-all" style={{ width: `${pct}%` }} />
        </div>
        {loadError && (
          <p className="mt-3 flex items-center gap-1.5 text-xs text-red-600">
            <AlertCircle className="size-4" /> {loadError}
          </p>
        )}
      </div>

      {/* Document categories */}
      {CATEGORIES.map((cat) => {
        const Icon = cat.icon
        return (
          <section key={cat.id} className="space-y-3">
            <div className="flex items-center gap-2">
              <span className="flex size-8 items-center justify-center rounded-lg bg-indigo-50 text-indigo-600">
                <Icon className="size-4" />
              </span>
              <div>
                <h3 className="text-sm font-bold text-neutral-900">{cat.title}</h3>
                <p className="text-[11px] text-neutral-500">{cat.blurb}</p>
              </div>
            </div>
            <div className="grid sm:grid-cols-2 lg:grid-cols-3 gap-4">
              {cat.slots.map((slot) => (
                <DocTile
                  key={slot.type}
                  slot={slot}
                  docs={docsByType[slot.type] || []}
                  busy={Boolean(busy[slot.type])}
                  error={errors[slot.type]}
                  onPick={handlePickDoc}
                  onDelete={handleDeleteDoc}
                />
              ))}
            </div>
          </section>
        )
      })}

      {/* Branding assets */}
      <section className="space-y-3">
        <div className="flex items-center gap-2">
          <span className="flex size-8 items-center justify-center rounded-lg bg-indigo-50 text-indigo-600">
            <Palette className="size-4" />
          </span>
          <div>
            <h3 className="text-sm font-bold text-neutral-900">Branding Assets</h3>
            <p className="text-[11px] text-neutral-500">
              PNG only, up to 1 MB. Transparent backgrounds work best — the chequerboard shows what is see-through.
            </p>
          </div>
        </div>
        <div className="grid sm:grid-cols-2 lg:grid-cols-3 gap-4">
          {BRANDING_SLOTS.map((slot) => (
            <ImageTile
              key={slot.type}
              slot={slot}
              asset={assetByType[slot.type]}
              previewUrl={previews[slot.type]}
              busy={Boolean(busy[slot.type])}
              error={errors[slot.type]}
              onPick={handlePickImage}
              onDelete={handleDeleteImage}
            />
          ))}
        </div>
      </section>

      {/* Custom / other documents */}
      <section className="space-y-3">
        <div className="flex items-center gap-2">
          <span className="flex size-8 items-center justify-center rounded-lg bg-neutral-100 text-neutral-600">
            <Plus className="size-4" />
          </span>
          <div>
            <h3 className="text-sm font-bold text-neutral-900">Other Documents</h3>
            <p className="text-[11px] text-neutral-500">
              Anything else you want GrantSetu to know about — MoUs, newsletters, beneficiary surveys.
            </p>
          </div>
        </div>
        <div className="grid sm:grid-cols-2 lg:grid-cols-3 gap-4">
          <DocTile
            slot={{ type: 'other', label: 'Additional Documents', desc: 'Any supporting PDF' }}
            docs={otherDocs}
            busy={Boolean(busy.other)}
            error={errors.other}
            onPick={handlePickDoc}
            onDelete={handleDeleteDoc}
          />
        </div>
      </section>
    </div>
  )
}
