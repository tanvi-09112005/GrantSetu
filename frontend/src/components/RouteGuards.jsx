import React from 'react'
import { Link, Outlet } from 'react-router-dom'
import { Loader2 } from 'lucide-react'
import { useApp } from '../context/AppContext'

export function PageSpinner({ label = 'Loading…' }) {
    return (
        <div className="flex flex-col items-center justify-center gap-3 py-24 text-neutral-500" role="status">
            <Loader2 className="size-7 animate-spin text-indigo-600" />
            <p className="text-sm">{label}</p>
        </div>
    )
}

export function GateCard({ title, body, children }) {
    return (
        <div className="mx-auto max-w-lg rounded-2xl border border-indigo-200 bg-indigo-50 p-8 text-center">
            <h3 className="text-base font-bold text-indigo-950">{title}</h3>
            <p className="mt-1 text-xs text-indigo-700">{body}</p>
            <div className="mt-4 flex flex-wrap items-center justify-center gap-2">{children}</div>
        </div>
    )
}

export const gatePrimary =
    'rounded-xl bg-indigo-600 hover:bg-indigo-700 px-4 py-2 text-xs font-semibold text-white shadow-xs cursor-pointer'
export const gateSecondary =
    'rounded-xl border border-indigo-200 bg-white hover:bg-indigo-50 px-4 py-2 text-xs font-semibold text-indigo-700 cursor-pointer'

// Needs a signed-in user
export function RequireAuth() {
    const { user, authLoading, setAuthModalOpen } = useApp()
    if (authLoading) return <PageSpinner label="Checking your session…" />
    if (!user) {
        return (
            <GateCard
                title="Sign in to continue"
                body="This page needs your NGO account. Your link will still work after you sign in."
            >
                <button type="button" onClick={() => setAuthModalOpen(true)} className={gatePrimary}>
                    Sign In
                </button>
                <Link to="/register" className={gateSecondary}>
                    Register your NGO
                </Link>
            </GateCard>
        )
    }
    return <Outlet />
}

// Needs a signed-in user who has an NGO profile
export function RequireOrg() {
    const { activeProfile, profilesLoaded } = useApp()
    if (!profilesLoaded) return <PageSpinner label="Loading your organization…" />
    if (!activeProfile) {
        return (
            <GateCard
                title="Set up your organization first"
                body="Choose a pre-verified NGO or create a custom profile to unlock this step."
            >
                <Link to="/profile" className={gatePrimary}>
                    Go to Organization details
                </Link>
            </GateCard>
        )
    }
    return <Outlet />
}