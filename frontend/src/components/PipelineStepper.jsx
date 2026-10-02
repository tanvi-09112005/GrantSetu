import React from 'react'
import { Link, useLocation } from 'react-router-dom'
import { Check, ChevronLeft, ChevronRight, Compass, FileText, ShieldCheck, Sparkles } from 'lucide-react'

export const PIPELINE = [
    { id: 1, path: '/vault', label: 'Org Vault & Credentials', icon: FileText },
    { id: 2, path: '/grants', label: 'Match & Screen Grants', icon: Compass },
    { id: 3, path: '/workspace', label: 'Proposal Studio', icon: Sparkles },
    { id: 4, path: '/export', label: 'Audit & Export', icon: ShieldCheck },
]

function usePipelineStep() {
    const { pathname } = useLocation()
    const index = PIPELINE.findIndex((s) => s.path === pathname)
    return { index, prev: PIPELINE[index - 1], next: PIPELINE[index + 1] }
}

export function PipelineStepper({ docCount = 0 }) {
    const { index } = usePipelineStep()

    return (
        <nav aria-label="Grant pipeline" className="mb-6 no-print">
            <ol className="flex items-center gap-2 overflow-x-auto pb-1">
                {PIPELINE.map((s, i) => {
                    const active = i === index
                    const passed = index >= 0 && i < index
                    const Icon = s.icon
                    return (
                        <li key={s.id} className="flex items-center gap-2 shrink-0">
                            <Link
                                to={s.path}
                                aria-current={active ? 'step' : undefined}
                                className={`flex items-center gap-2 rounded-xl border px-3 py-2 text-xs font-semibold transition ${active
                                        ? 'border-indigo-600 bg-indigo-600 text-white shadow-sm'
                                        : passed
                                            ? 'border-emerald-200 bg-emerald-50 text-emerald-800 hover:bg-emerald-100'
                                            : 'border-neutral-200 bg-white text-neutral-600 hover:bg-neutral-50'
                                    }`}
                            >
                                <span
                                    className={`flex size-5 items-center justify-center rounded-full text-[10px] font-bold ${active ? 'bg-white/20' : passed ? 'bg-emerald-600 text-white' : 'bg-neutral-100'
                                        }`}
                                >
                                    {passed ? <Check className="size-3" /> : s.id}
                                </span>
                                <Icon className="size-3.5 hidden sm:block" />
                                <span>{s.label}</span>
                                {s.path === '/vault' && (
                                    <span className={`rounded-full px-1.5 py-0.5 text-[10px] ${active ? 'bg-white/20' : 'bg-neutral-100 text-neutral-600'}`}>
                                        {docCount}
                                    </span>
                                )}
                            </Link>
                            {i < PIPELINE.length - 1 && <ChevronRight className="size-4 text-neutral-300 shrink-0" />}
                        </li>
                    )
                })}
            </ol>
            <div className="mt-2 text-right">
                <Link to="/profile" className="text-[11px] font-medium text-indigo-600 hover:text-indigo-800 hover:underline">
                    Organization details &amp; Darpan ID
                </Link>
            </div>
        </nav>
    )
}

export function PipelineNav() {
    const { index, prev, next } = usePipelineStep()
    if (index < 0) return null

    return (
        <div className="mt-8 flex items-center justify-between border-t border-neutral-200 pt-4 no-print">
            {prev ? (
                <Link to={prev.path} className="inline-flex items-center gap-1 text-sm font-medium text-neutral-600 hover:text-neutral-900">
                    <ChevronLeft className="size-4" /> Back: {prev.label}
                </Link>
            ) : (
                <span />
            )}
            {next ? (
                <Link to={next.path} className="inline-flex items-center gap-1 rounded-lg bg-indigo-600 hover:bg-indigo-700 px-4 py-2 text-sm font-semibold text-white shadow-xs">
                    Next: {next.label} <ChevronRight className="size-4" />
                </Link>
            ) : (
                <span />
            )}
        </div>
    )
}