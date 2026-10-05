import React from 'react'
import { ShieldCheck } from 'lucide-react'
import { useApp } from '../context/AppContext'

const VERIFICATION_BADGES = {
    document_matched: {
        label: 'Statutorily Verified NGO ✓',
        cls: 'bg-emerald-50 text-emerald-700 border-emerald-200',
        hint: 'Darpan ID format valid and found inside the uploaded certificate',
    },
    format_verified: {
        label: 'Format verified · document review pending',
        cls: 'bg-amber-50 text-amber-700 border-amber-200',
        hint: 'Darpan ID format valid and certificate uploaded, but the ID could not be read from the PDF',
    },
    pending_review: {
        label: 'Verification pending',
        cls: 'bg-neutral-100 text-neutral-600 border-neutral-200',
        hint: 'No verification proof on file yet',
    },
    rejected: {
        label: 'Verification rejected',
        cls: 'bg-red-50 text-red-700 border-red-200',
        hint: 'Please re-upload a valid certificate',
    },
}

function incomeTaxLabel(profile) {
    const has12a = Boolean(profile?.has_12a || profile?.reg_12a)
    const has80g = Boolean(profile?.has_80g || profile?.reg_80g)
    if (has12a && has80g) return { text: '12A & 80G', ok: true }
    if (has12a) return { text: '12A only', ok: true }
    if (has80g) return { text: '80G only', ok: true }
    return { text: 'None declared', ok: false }
}

function vintageLabel(profile) {
    const year = profile?.incorporation_year || parseInt((profile?.registered_on || '').slice(0, 4), 10)
    if (!year || Number.isNaN(year)) return null
    return `Inc. ${year} (${Math.max(0, new Date().getFullYear() - year)} yrs)`
}

export default function NgoStatusBanner() {
    const { user, activeProfile, profiles, setActiveProfile, docCount } = useApp()
    const badge = activeProfile
        ? VERIFICATION_BADGES[activeProfile.verification_status] || VERIFICATION_BADGES.pending_review
        : null
    const tax = activeProfile ? incomeTaxLabel(activeProfile) : null
    const vintage = activeProfile ? vintageLabel(activeProfile) : null

    return (
        <div className="mb-6 rounded-2xl bg-white border border-neutral-200 p-5 shadow-xs no-print">
            <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
                <div className="space-y-1">
                    <div className="flex flex-wrap items-center gap-2">
                        <h2 className="text-lg font-bold text-neutral-900">
                            {activeProfile?.name || (user ? 'No NGO registered yet' : 'Sign in or register your NGO')}
                        </h2>
                        {badge && (
                            <span
                                title={badge.hint}
                                className={`inline-flex items-center gap-1 rounded-full px-2 py-0.5 text-[10px] font-bold border ${badge.cls}`}
                            >
                                <ShieldCheck className="size-3" />
                                {badge.label}
                            </span>
                        )}
                    </div>
                    {activeProfile ? (
                        <p className="text-xs text-neutral-500">
                            Darpan ID:{' '}
                            <strong className="font-mono text-neutral-800">{activeProfile.darpan_id || 'Not provided'}</strong>
                            {vintage && <> · <span className="text-neutral-700">{vintage}</span></>}
                            {(activeProfile.district || activeProfile.state) && (
                                <> · <span className="text-neutral-700">
                                    {[activeProfile.district, activeProfile.state].filter(Boolean).join(', ')}
                                </span></>
                            )}
                        </p>
                    ) : (
                        <p className="text-xs text-neutral-500">
                            {user
                                ? 'Complete NGO registration to unlock grant discovery and proposals.'
                                : 'Use “Register your NGO” to create a verified account.'}
                        </p>
                    )}
                </div>

                <div className="flex flex-wrap items-center gap-2 text-xs">
                    <div className="rounded-xl bg-neutral-50 px-3 py-2 border border-neutral-200 text-center">
                        <span className="text-[10px] text-neutral-500 block uppercase font-medium">Income Tax (declared)</span>
                        {tax ? (
                            <span className={`font-bold ${tax.ok ? 'text-emerald-700' : 'text-neutral-500'}`}>{tax.text}</span>
                        ) : (
                            <span className="font-bold text-neutral-400">—</span>
                        )}
                    </div>
                    <div className="rounded-xl bg-neutral-50 px-3 py-2 border border-neutral-200 text-center">
                        <span className="text-[10px] text-neutral-500 block uppercase font-medium">FCRA Status</span>
                        <span className="font-bold text-purple-700 uppercase">
                            {activeProfile ? (activeProfile.fcra_status || 'unknown').replace(/_/g, ' ') : '—'}
                        </span>
                    </div>
                    <div className="rounded-xl bg-neutral-50 px-3 py-2 border border-neutral-200 text-center">
                        <span className="text-[10px] text-neutral-500 block uppercase font-medium">Documents</span>
                        <span className="font-bold text-indigo-700">{docCount} on File</span>
                    </div>
                </div>
            </div>

            {profiles.length > 1 && (
                <div className="mt-4 pt-3 border-t border-neutral-100 flex items-center gap-2 text-xs">
                    <span className="text-neutral-500 font-medium">Switch Organization:</span>
                    <select
                        value={activeProfile?.id || ''}
                        onChange={(e) => {
                            const p = profiles.find((x) => x.id === e.target.value)
                            if (p) setActiveProfile(p)
                        }}
                        className="rounded-lg border border-neutral-300 bg-neutral-50 px-2 py-1 text-xs font-semibold text-neutral-800"
                    >
                        {profiles.map((p) => (
                            <option key={p.id} value={p.id}>
                                {p.name} ({p.darpan_id || 'Custom'})
                            </option>
                        ))}
                    </select>
                </div>
            )}
        </div>
    )
}