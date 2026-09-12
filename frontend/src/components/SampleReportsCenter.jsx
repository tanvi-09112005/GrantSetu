import React, { useEffect, useState } from 'react'
import { getSampleProfiles } from '../lib/api'
import { FileDown, Building2, CheckCircle2, ShieldCheck, Sparkles } from 'lucide-react'

export default function SampleReportsCenter({ onSelectProfile }) {
  const [profiles, setProfiles] = useState([])
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    getSampleProfiles()
      .then((data) => setProfiles(data))
      .catch((err) => console.error('Failed to load sample profiles:', err))
      .finally(() => setLoading(false))
  }, [])

  if (loading) {
    return (
      <div className="rounded-xl border border-neutral-200 bg-white p-6 shadow-xs animate-pulse">
        <div className="h-5 w-48 bg-neutral-200 rounded mb-4"></div>
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          <div className="h-32 bg-neutral-100 rounded-lg"></div>
          <div className="h-32 bg-neutral-100 rounded-lg"></div>
        </div>
      </div>
    )
  }

  const apiBase = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000'

  return (
    <div className="rounded-xl border border-indigo-100 bg-linear-to-b from-indigo-50/50 to-white p-6 shadow-xs">
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2 mb-4">
        <div>
          <div className="flex items-center gap-2">
            <Sparkles className="size-4 text-indigo-600" />
            <h3 className="text-base font-semibold text-neutral-900">
              Curated Real Indian NGO Profiles & Downloadable Reports
            </h3>
          </div>
          <p className="text-xs text-neutral-500 mt-0.5">
            Real registered NGOs with genuine NITI Aayog Darpan IDs, 12A/80G, and FCRA credentials.
            Download any report PDF, then test uploading it below!
          </p>
        </div>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        {profiles.map((ngo) => (
          <div
            key={ngo.id}
            className="group relative rounded-xl border border-neutral-200 bg-white p-4 transition-all hover:border-indigo-300 hover:shadow-md flex flex-col justify-between"
          >
            <div>
              <div className="flex items-start justify-between gap-2">
                <div className="flex items-center gap-2">
                  <div className="flex size-8 items-center justify-center rounded-lg bg-indigo-100 text-indigo-700 font-bold text-xs">
                    {ngo.name.substring(0, 2).toUpperCase()}
                  </div>
                  <div>
                    <h4 className="font-semibold text-sm text-neutral-900 leading-tight">
                      {ngo.name}
                    </h4>
                    <span className="text-[11px] text-neutral-500">{ngo.location} · Reg {ngo.registered_on?.slice(0, 4)}</span>
                  </div>
                </div>
                <span className="inline-flex items-center gap-1 rounded-full bg-emerald-50 px-2 py-0.5 text-[10px] font-medium text-emerald-700 border border-emerald-200">
                  <ShieldCheck className="size-3" />
                  Verified
                </span>
              </div>

              <div className="mt-3 grid grid-cols-2 gap-x-2 gap-y-1 text-xs">
                <div className="text-neutral-500">
                  Darpan ID: <span className="font-mono text-neutral-800 font-medium">{ngo.darpan_id}</span>
                </div>
                <div className="text-neutral-500">
                  FCRA Status: <span className="text-emerald-600 font-medium uppercase">{ngo.fcra_status}</span>
                </div>
                <div className="text-neutral-500">
                  12A: <span className="font-mono text-neutral-800">{ngo.reg_12a}</span>
                </div>
                <div className="text-neutral-500">
                  80G: <span className="font-mono text-neutral-800">{ngo.reg_80g}</span>
                </div>
              </div>

              <div className="mt-2.5 flex flex-wrap gap-1">
                {ngo.sectors.map((s) => (
                  <span
                    key={s}
                    className="rounded bg-neutral-100 px-1.5 py-0.5 text-[10px] text-neutral-600 font-medium"
                  >
                    #{s}
                  </span>
                ))}
              </div>
            </div>

            <div className="mt-4 pt-3 border-t border-neutral-100 flex items-center justify-between gap-2">
              <button
                type="button"
                onClick={() => onSelectProfile && onSelectProfile(ngo)}
                className="text-xs text-indigo-600 hover:text-indigo-800 font-medium hover:underline flex items-center gap-1"
              >
                Use this Profile &rarr;
              </button>
              <a
                href={`${apiBase}/sample-ngos/download/${ngo.id}`}
                target="_blank"
                rel="noreferrer"
                download
                className="inline-flex items-center gap-1.5 rounded-lg bg-neutral-900 hover:bg-neutral-800 px-3 py-1.5 text-xs font-medium text-white transition shadow-2xs"
              >
                <FileDown className="size-3.5" />
                Download Annual Report (PDF)
              </a>
            </div>
          </div>
        ))}
      </div>
    </div>
  )
}
