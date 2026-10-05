import React, { useState } from 'react'
import { ShieldAlert, ShieldCheck, Upload, Loader2, X } from 'lucide-react'
import { useApp } from '../context/AppContext'
import { verifyNgo } from '../lib/api'

const MAX_MB = 10

const STATUS_COPY = {
  format_verified:
    'Your Darpan ID format was accepted at sign-up, but the certificate was never matched to it.',
  pending_review: 'Your Darpan certificate has not been checked yet.',
}

// Re-upload / retry card for NGOs that are not document-matched.
export default function VerificationPanel({ profile }) {
  const { reloadProfiles } = useApp()
  const [file, setFile] = useState(null)
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState(null)
  const [done, setDone] = useState(false)

  if (!profile) return null

  const pick = (f) => {
    setError(null)
    if (!f) return setFile(null)
    const isPdf = f.type === 'application/pdf' || f.name.toLowerCase().endsWith('.pdf')
    if (!isPdf) return setError('Only PDF files are accepted')
    if (f.size > MAX_MB * 1024 * 1024) return setError(`File is larger than ${MAX_MB} MB`)
    setFile(f)
  }

  const submit = async () => {
    if (!file) return
    setBusy(true)
    setError(null)
    try {
      await verifyNgo(profile.id, file)
      await reloadProfiles()
      setDone(true)
    } catch (err) {
      const detail = err.response?.data?.detail
      setError(typeof detail === 'string' ? detail : err.message || 'Verification failed. Please try again.')
    } finally {
      setBusy(false)
    }
  }

  if (done) {
    return (
      <div className="rounded-xl border border-emerald-200 bg-emerald-50 p-4 text-xs text-emerald-900 flex items-center gap-2">
        <ShieldCheck className="size-4 text-emerald-600 shrink-0" />
        <span className="font-semibold">Verified. Grant matching and proposals are now unlocked.</span>
      </div>
    )
  }

  return (
    <div className="rounded-xl border border-amber-200 bg-amber-50 p-5 text-xs text-amber-950 space-y-3">
      <div className="flex items-start gap-2">
        <ShieldAlert className="size-4 text-amber-600 shrink-0 mt-0.5" />
        <div>
          <p className="text-sm font-bold">Verify your NGO to unlock grant matching &amp; proposals</p>
          <p className="mt-0.5 text-amber-800">
            {STATUS_COPY[profile.verification_status] || 'Your NGO has not been verified yet.'} Upload your NGO
            Darpan certificate (PDF) for <span className="font-mono font-semibold">{profile.darpan_id || 'your Darpan ID'}</span>.
            Scans are fine.
          </p>
        </div>
      </div>

      {file ? (
        <div className="flex items-center justify-between rounded-lg bg-white border border-amber-200 px-3 py-2">
          <span className="truncate max-w-[70%]">{file.name}</span>
          <button type="button" onClick={() => setFile(null)} aria-label="Remove file" className="text-neutral-400 hover:text-red-600">
            <X className="size-4" />
          </button>
        </div>
      ) : (
        <label className="flex items-center justify-center gap-2 rounded-lg border-2 border-dashed border-amber-300 hover:border-amber-500 bg-white py-4 cursor-pointer text-amber-800">
          <Upload className="size-4" />
          <span>Choose Darpan certificate PDF</span>
          <input type="file" accept="application/pdf,.pdf" className="hidden" onChange={(e) => pick(e.target.files?.[0] ?? null)} />
        </label>
      )}

      {error && <p className="text-[11px] text-red-700">{error}</p>}

      <button
        type="button"
        onClick={submit}
        disabled={!file || busy}
        className="inline-flex items-center gap-2 rounded-lg bg-amber-600 hover:bg-amber-700 disabled:opacity-50 text-white font-semibold px-4 py-2"
      >
        {busy ? <Loader2 className="size-4 animate-spin" /> : <ShieldCheck className="size-4" />}
        {busy ? 'Checking certificate…' : 'Verify now'}
      </button>
    </div>
  )
}
