import React, { useEffect, useRef, useState } from 'react'
// import { getHealth, listProfiles, listDocuments } from './lib/api'
// import { supabase, isSupabaseConfigured } from './lib/supabase'
//import React, { useState } from 'react'
import { AppProvider, useApp } from './context/AppContext'
import AuthModal from './components/AuthModal'
import NGOProfileCard from './components/NGOProfileCard'
import NgoRegisterWizard from './components/NgoRegisterWizard'
import DocumentUploadCard from './components/DocumentUploadCard'
import GrantDiscoveryCard from './components/GrantDiscoveryCard'
import ProposalWorkspace from './components/ProposalWorkspace'
import { Navigate, useLocation, useNavigate } from 'react-router-dom'
import { PipelineStepper, PipelineNav } from './components/PipelineStepper'
import {
  Building2,
  FileText,
  Compass,
  ShieldCheck,
  User,
  LogOut,
  Sparkles,
  ChevronRight,
  Database,
  Award,
  Layers,
  CheckCircle2,
  AlertTriangle,
} from 'lucide-react'

// ---------------------------------------------------------------------------
// Banner helpers: derive what to show from the REAL profile, never from defaults.
// ---------------------------------------------------------------------------
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
  // Wizard sets has_12a / has_80g; profiles made via the older form store a number in reg_12a / reg_80g.
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

// Temporary mapping while the old tab UI still exists. Layout step replaces this.
const SECTION_PATHS = {
  discovery: '/grants',
  documents: '/vault',
  proposal: '/workspace',
  profile: '/profile',
}
const PATH_SECTIONS = {
  ...Object.fromEntries(Object.entries(SECTION_PATHS).map(([section, path]) => [path, section])),
  '/export': 'proposal',
}

function AppShell() {
  const {
    user, setUser, health,
    profiles, activeProfile, setActiveProfile,
    docCount, setDocCount,
    activeGrant, setActiveGrant,
    discoveredGrants, setDiscoveredGrants,
    batchGrants,
    selectGrant, selectBatch,
    reloadProfiles, handleProfileSaved, handleSignOut,
  } = useApp()

  // UI-only state stays here for now; it moves to routes in later steps
  const [showAuthModal, setShowAuthModal] = useState(false)
  const [discoveryCache, setDiscoveryCache] = useState(null)
  const proposalCache = useRef(null)
  const navigate = useNavigate()
  const { pathname } = useLocation()

  const activeSection = PATH_SECTIONS[pathname]
  const showRegister = pathname === '/register'

  const [visited, setVisited] = useState({})
  useEffect(() => {
    if (activeSection) setVisited((v) => (v[activeSection] ? v : { ...v, [activeSection]: true }))
  }, [activeSection])
  const shown = (key) => activeSection === key
  const paneCls = (key) => (activeSection === key ? '' : 'hidden')

  // Shims so the existing JSX keeps working unchanged
  const setActiveSection = (section) => navigate(SECTION_PATHS[section])
  const setShowRegister = (open) => {
    if (open) navigate('/register')
    else if (pathname === '/register') navigate('/vault') // only leave if we're on the register page
  }

  const handleDraftProposal = (grant) => {
    selectGrant(grant)
    setActiveSection('proposal')
  }

  const handleBatchDraft = (grants) => {
    if (grants && grants.length > 0) {
      selectBatch(grants)
      setActiveSection('proposal')
    }
  }

  const handleRegistered = async () => {
    setShowRegister(false)
    try {
      await reloadProfiles()
    } catch (err) {
      console.error('Failed to load profile after registration:', err)
    }
  }

  if (!activeSection && !showRegister) {
    return <Navigate to="/vault" replace />
  }

  return (
    <div className="min-h-screen bg-neutral-50/60 text-neutral-900 font-sans pb-20">
      {/* Top Header */}
      <header className="sticky top-0 z-40 bg-white/95 backdrop-blur-md border-b border-neutral-200 shadow-2xs">
        <div className="mx-auto max-w-6xl px-4 sm:px-6 h-16 flex items-center justify-between">
          <div className="flex items-center gap-3">
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
          </div>

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
                  onClick={() => setShowRegister(true)}
                  className="rounded-xl border border-indigo-200 bg-white hover:bg-indigo-50 px-4 py-2 text-xs font-semibold text-indigo-700 transition cursor-pointer"
                >
                  Register your NGO
                </button>
                <button
                  type="button"
                  onClick={() => setShowAuthModal(true)}
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

      {showRegister && (
        <main className="mx-auto max-w-6xl px-4 sm:px-6 pt-8">
          <NgoRegisterWizard onComplete={handleRegistered} onCancel={() => setShowRegister(false)} />
        </main>
      )}

      {/* Main Workspace */}
      <main className={`mx-auto max-w-6xl px-4 sm:px-6 pt-6 ${showRegister ? 'hidden' : ''}`}>
        {/* At-a-glance Status Banner */}
        <div className="mb-6 rounded-2xl bg-white border border-neutral-200 p-5 shadow-xs no-print">
          <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
            <div className="space-y-1">
              <div className="flex items-center gap-2">
                <h2 className="text-lg font-bold text-neutral-900">
                  {activeProfile?.name ||
                    (user ? 'No NGO registered yet' : 'Sign in or register your NGO')}
                </h2>
                {activeProfile && (() => {
                  const badge =
                    VERIFICATION_BADGES[activeProfile.verification_status] ||
                    VERIFICATION_BADGES.pending_review
                  return (
                    <span
                      title={badge.hint}
                      className={`inline-flex items-center gap-1 rounded-full px-2 py-0.5 text-[10px] font-bold border ${badge.cls}`}
                    >
                      <ShieldCheck className="size-3" />
                      {badge.label}
                    </span>
                  )
                })()}
              </div>
              {activeProfile ? (
                <p className="text-xs text-neutral-500">
                  Darpan ID:{' '}
                  <strong className="font-mono text-neutral-800">
                    {activeProfile.darpan_id || 'Not provided'}
                  </strong>
                  {vintageLabel(activeProfile) && (
                    <> · <span className="text-neutral-700">{vintageLabel(activeProfile)}</span></>
                  )}
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

            {/* Quick Metrics */}
            <div className="flex flex-wrap items-center gap-2 text-xs">
              <div className="rounded-xl bg-neutral-50 px-3 py-2 border border-neutral-200 text-center">
                <span className="text-[10px] text-neutral-500 block uppercase font-medium">Income Tax (declared)</span>
                {(() => {
                  if (!activeProfile) return <span className="font-bold text-neutral-400">—</span>
                  const it = incomeTaxLabel(activeProfile)
                  return (
                    <span className={`font-bold ${it.ok ? 'text-emerald-700' : 'text-neutral-500'}`}>
                      {it.text}
                    </span>
                  )
                })()}
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

          {/* Organization Switcher if multiple exist */}
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

        <PipelineStepper docCount={docCount} />

        {/* Section Content */}
        {!user && (
          <div className="mb-6 rounded-2xl bg-indigo-50 border border-indigo-200 p-4 text-xs text-indigo-950 flex flex-col sm:flex-row items-start sm:items-center justify-between gap-3">
            <div>
              <p className="font-bold text-sm">You&apos;re not signed in</p>
              <p className="text-indigo-700 mt-0.5">
                Sign in to save your own NGO profiles and attach custom compliance filings to your account.
              </p>
            </div>
            <button
              type="button"
              onClick={() => setShowAuthModal(true)}
              className="rounded-xl bg-indigo-600 hover:bg-indigo-700 text-white px-4 py-2 font-semibold text-xs shadow-xs shrink-0 cursor-pointer"
            >
              Sign In
            </button>
          </div>
        )}

        {shown('discovery') && (
          <div key={activeProfile?.id || 'none'} className={paneCls('discovery')}>
            <GrantDiscoveryCard
              ngoId={activeProfile?.id}
              ngoProfile={activeProfile}
              onDraftProposal={handleDraftProposal}
              onBatchDraft={handleBatchDraft}
              onResultsLoaded={(grants) => {
                setDiscoveredGrants(grants)
                if (!activeGrant && grants.length > 0) {
                  setActiveGrant(grants[0])
                }
              }}
              cache={discoveryCache?.ngoId === activeProfile?.id ? discoveryCache : null}
              onCacheChange={(c) => setDiscoveryCache({ ...c, ngoId: activeProfile?.id })}
            />
          </div>
        )}

        {shown('documents') && (
          <div key={activeProfile?.id || 'none'} className={paneCls('documents')}>
            <DocumentUploadCard
              ngoId={activeProfile?.id}
              ngoProfile={activeProfile}
              onDocumentCountChange={(c) => setDocCount(c)}
            />
          </div>
        )}

        {shown('proposal') && (
          <div key={activeProfile?.id || 'none'} className={paneCls('proposal')}>
            <ProposalWorkspace
              activeNgo={
                activeProfile || {
                  id: 'b6b3f1a9-01ed-4def-8b14-58e4c3e0863e',
                  name: 'Child Rights and You (CRY)',
                  darpan_id: 'DL/2009/0014766',
                }
              }
              activeGrant={activeGrant}
              batchGrants={batchGrants}
              grants={discoveredGrants}
              onSelectGrant={(grant) => setActiveGrant(grant)}
              cache={proposalCache.current?.ngoId === activeProfile?.id ? proposalCache.current : null}
              onCacheChange={(c) => { proposalCache.current = { ...c, ngoId: activeProfile?.id } }}
              viewModeRequest={pathname === '/export' ? 'audit' : 'editor'}
              exportStage={pathname === '/export'}
            />
          </div>
        )}

        {shown('profile') && (
          <div key={activeProfile?.id || 'none'} className={paneCls('profile')}>
            <NGOProfileCard
              currentProfile={activeProfile}
              onProfileSaved={handleProfileSaved}
            />
          </div>
        )}
        <PipelineNav />
      </main>

      {/* Auth Modal */}
      {showAuthModal && (
        <AuthModal
          onAuthSuccess={(u) => {
            setUser(u)
            setShowAuthModal(false)
            setShowRegister(false)
          }}
          onClose={() => setShowAuthModal(false)}
          onRegister={() => {
            setShowAuthModal(false)
            setShowRegister(true)
          }}
        />
      )}
    </div>
  )
}

export default function App() {
  return (
    <AppProvider>
      <AppShell />
    </AppProvider>
  )
}
