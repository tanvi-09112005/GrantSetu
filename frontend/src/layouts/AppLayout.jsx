import React, { Suspense } from 'react'
import { Link, Outlet, useLocation, useNavigate } from 'react-router-dom'
import { LogOut, User } from 'lucide-react'
import { useApp } from '../context/AppContext'
import AuthModal from '../components/AuthModal'
import NgoStatusBanner from '../components/NgoStatusBanner'
import { PipelineStepper } from '../components/PipelineStepper'
import PageHeader from '../components/PageHeader'
import { PageSpinner } from '../components/RouteGuards'

export default function AppLayout() {
    const { user, setUser, health, docCount, handleSignOut, authModalOpen, setAuthModalOpen } = useApp()
    const { pathname } = useLocation()
    const navigate = useNavigate()
    const onRegister = pathname === '/register'

    return (
        <div className="min-h-screen bg-neutral-50/60 text-neutral-900 font-sans pb-20">
            <header className="sticky top-0 z-40 bg-white/95 backdrop-blur-md border-b border-neutral-200 shadow-2xs no-print">
                <div className="mx-auto max-w-6xl px-4 sm:px-6 h-16 flex items-center justify-between">
                    <Link to="/vault" className="flex items-center gap-3">
                        <div className="flex size-9 items-center justify-center rounded-xl bg-indigo-600 text-white font-black text-base shadow-sm">
                            GS
                        </div>
                        <div>
                            <div className="flex items-center gap-2">
                                <span className="font-bold text-base text-neutral-900 tracking-tight">GrantSetu</span>
                                <span className="rounded-full bg-indigo-50 px-2 py-0.5 text-[10px] font-bold text-indigo-700 border border-indigo-200">
                                    NGO Portal
                                </span>
                            </div>
                            <p className="text-[11px] text-neutral-500 hidden sm:block">
                                AI Agent for NGO Grant Discovery, Eligibility & Proposal Drafting
                            </p>
                        </div>
                    </Link>

                    <div className="flex items-center gap-3">
                        {health && (
                            <div className="hidden lg:flex items-center gap-2 rounded-full bg-neutral-100 px-3 py-1 text-xs text-neutral-600">
                                <span className="size-2 rounded-full bg-emerald-500" />
                                <span className="font-medium">154 Live Schemes in DB</span>
                                <span className="text-neutral-300">|</span>
                                <span>Gemini 3.6</span>
                            </div>
                        )}

                        {user ? (
                            <div className="flex items-center gap-2">
                                <div className="flex items-center gap-1.5 rounded-lg bg-neutral-100 px-3 py-1.5 text-xs text-neutral-700">
                                    <User className="size-3.5 text-neutral-500" />
                                    <span className="font-semibold max-w-[120px] sm:max-w-xs truncate">{user.email}</span>
                                </div>
                                <button
                                    type="button"
                                    onClick={handleSignOut}
                                    title="Sign Out"
                                    className="rounded-lg p-2 text-neutral-400 hover:text-red-600 hover:bg-neutral-100 transition cursor-pointer"
                                >
                                    <LogOut className="size-4" />
                                </button>
                            </div>
                        ) : (
                            <>
                                <button
                                    type="button"
                                    onClick={() => navigate('/register')}
                                    className="rounded-xl border border-indigo-200 bg-white hover:bg-indigo-50 px-4 py-2 text-xs font-semibold text-indigo-700 transition cursor-pointer"
                                >
                                    Register your NGO
                                </button>
                                <button
                                    type="button"
                                    onClick={() => setAuthModalOpen(true)}
                                    className="rounded-xl bg-indigo-600 hover:bg-indigo-700 px-4 py-2 text-xs font-semibold text-white transition shadow-sm flex items-center gap-1.5 cursor-pointer"
                                >
                                    <User className="size-3.5" />
                                    Sign In
                                </button>
                            </>
                        )}
                    </div>
                </div>
            </header>

            <main className="mx-auto max-w-6xl px-4 sm:px-6 pt-6">
                {!onRegister && (
                    <>
                        <NgoStatusBanner />
                        <PipelineStepper docCount={docCount} />
                        <PageHeader />
                    </>
                )}
                <Suspense fallback={<PageSpinner />}>
                    <Outlet />
                </Suspense>
            </main>

            {authModalOpen && (
                <AuthModal
                    onAuthSuccess={(u) => {
                        setUser(u)
                        setAuthModalOpen(false)
                        if (onRegister) navigate('/vault')
                    }}
                    onClose={() => setAuthModalOpen(false)}
                    onRegister={() => {
                        setAuthModalOpen(false)
                        navigate('/register')
                    }}
                />
            )}
        </div>
    )
}