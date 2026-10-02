import React from 'react'
import { Link, useLocation } from 'react-router-dom'
import { ChevronRight } from 'lucide-react'
import { PIPELINE } from './PipelineStepper'

const DESCRIPTIONS = {
    '/vault': 'Upload and verify your statutory and financial documents. Proposals are grounded in these.',
    '/grants': 'Find funding calls that fit your organization and check statutory eligibility.',
    '/workspace': 'Draft, edit and review funder-tailored proposals.',
    '/export': 'Fact-check every claim against your vault, then export the final proposal.',
    '/profile': 'Your registered details, Darpan ID and statutory credentials.',
}

export default function PageHeader() {
    const { pathname } = useLocation()
    const step = PIPELINE.find((s) => s.path === pathname)
    const title = step ? step.label : pathname === '/profile' ? 'Organization details' : null
    if (!title) return null

    return (
        <div className="mb-5 no-print">
            <nav aria-label="Breadcrumb" className="flex items-center gap-1 text-[11px] text-neutral-500">
                <Link to="/vault" className="hover:text-neutral-800 hover:underline">GrantSetu</Link>
                <ChevronRight className="size-3" />
                <span>{step ? 'Grant pipeline' : 'Organization'}</span>
                <ChevronRight className="size-3" />
                <span aria-current="page" className="font-semibold text-neutral-800">{title}</span>
            </nav>
            <h1 className="mt-1.5 text-xl font-bold tracking-tight text-neutral-900">
                {step && <span className="text-indigo-600">Step {step.id} · </span>}
                {title}
            </h1>
            <p className="mt-0.5 text-xs text-neutral-500">{DESCRIPTIONS[pathname]}</p>
        </div>
    )
}