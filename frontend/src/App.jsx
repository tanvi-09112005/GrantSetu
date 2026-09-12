import React, { useEffect, useState } from 'react'
import { getHealth, listProfiles, listDocuments } from './lib/api'
import { supabase, isSupabaseConfigured } from './lib/supabase'
import AuthModal from './components/AuthModal'
import NGOProfileCard from './components/NGOProfileCard'
import DocumentUploadCard from './components/DocumentUploadCard'
import GrantDiscoveryCard from './components/GrantDiscoveryCard'
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

export default function App() {
  const [user, setUser] = useState(null)
  const [showAuthModal, setShowAuthModal] = useState(false)
  const [health, setHealth] = useState(null)
  const [profiles, setProfiles] = useState([])
  const [activeProfile, setActiveProfile] = useState(null)
  const [activeSection, setActiveSection] = useState('discovery') // 'discovery' | 'documents' | 'profile'
  const [docCount, setDocCount] = useState(0)

  // Load auth state from Supabase
  useEffect(() => {
    if (!supabase) return
    supabase.auth.getSession().then(({ data }) => {
      if (data?.session?.user) {
        setUser(data.session.user)
      }
    })

    const { data: authListener } = supabase.auth.onAuthStateChange((_event, session) => {
      setUser(session?.user ?? null)
    })

    return () => {
      authListener?.subscription?.unsubscribe()
    }
  }, [])

  // Load health
  useEffect(() => {
    getHealth()
      .then(setHealth)
      .catch((err) => console.error('Health check failed:', err))
  }, [])

  // Load user profiles when user signs in
  useEffect(() => {
    if (!user) {
      setProfiles([])
      setActiveProfile(null)
      return
    }
    listProfiles()
      .then((data) => {
        setProfiles(data || [])
        if (data && data.length > 0 && !activeProfile) {
          setActiveProfile(data[0])
        }
      })
      .catch((err) => console.error('Failed to list profiles:', err))
  }, [user])

  // Count documents for active profile
  useEffect(() => {
    if (activeProfile?.id) {
      listDocuments(activeProfile.id)
        .then((docs) => setDocCount((docs || []).length))
        .catch(() => setDocCount(0))
    }
  }, [activeProfile])

  const handleSignOut = async () => {
    if (supabase) await supabase.auth.signOut()
    setUser(null)
    setActiveProfile(null)
    setProfiles([])
  }

  const handleProfileSaved = (saved) => {
    setActiveProfile(saved)
    listProfiles().then((data) => {
      setProfiles(data || [])
      setActiveProfile(saved)
    })
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
              <button
                type="button"
                onClick={() => setShowAuthModal(true)}
                className="rounded-xl bg-indigo-600 hover:bg-indigo-700 px-4 py-2 text-xs font-semibold text-white transition shadow-sm flex items-center gap-1.5 cursor-pointer"
              >
                <User className="size-3.5" />
                Sign In with 1-Click Demo
              </button>
            )}
          </div>
        </div>
      </header>

      {/* Main Workspace */}
      <main className="mx-auto max-w-6xl px-4 sm:px-6 pt-6">
        {/* At-a-glance Status Banner */}
        <div className="mb-6 rounded-2xl bg-white border border-neutral-200 p-5 shadow-xs">
          <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
            <div className="space-y-1">
              <div className="flex items-center gap-2">
                <h2 className="text-lg font-bold text-neutral-900">
                  {activeProfile?.name || 'Child Rights and You (CRY)'}
                </h2>
                <span className="inline-flex items-center gap-1 rounded-full bg-emerald-50 px-2 py-0.5 text-[10px] font-bold text-emerald-700 border border-emerald-200">
                  <ShieldCheck className="size-3" />
                  NITI Aayog Registered
                </span>
              </div>
              <p className="text-xs text-neutral-500">
                Darpan ID:{' '}
                <strong className="font-mono text-neutral-800">
                  {activeProfile?.darpan_id || 'DL/2009/0014766'}
                </strong>{' '}
                · Reg Date:{' '}
                <span className="text-neutral-700">
                  {activeProfile?.registered_on || '1979-04-18'} (47+ yrs vintage)
                </span>
              </p>
            </div>

            {/* Quick Metrics */}
            <div className="flex flex-wrap items-center gap-2 text-xs">
              <div className="rounded-xl bg-neutral-50 px-3 py-2 border border-neutral-200 text-center">
                <span className="text-[10px] text-neutral-500 block uppercase font-medium">Income Tax</span>
                <span className="font-bold text-emerald-700">12A & 80G Active</span>
              </div>

              <div className="rounded-xl bg-neutral-50 px-3 py-2 border border-neutral-200 text-center">
                <span className="text-[10px] text-neutral-500 block uppercase font-medium">FCRA Status</span>
                <span className="font-bold text-purple-700 uppercase">
                  {activeProfile?.fcra_status || 'Active'}
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

        {/* Realistic Portal Navigation Tabs */}
        <div className="flex gap-2 border-b border-neutral-200 mb-6 text-sm font-semibold overflow-x-auto pb-1">
          <button
            type="button"
            onClick={() => setActiveSection('discovery')}
            className={`flex items-center gap-2 pb-3 px-3.5 border-b-2 transition cursor-pointer shrink-0 ${
              activeSection === 'discovery'
                ? 'border-indigo-600 text-indigo-600'
                : 'border-transparent text-neutral-500 hover:text-neutral-800'
            }`}
          >
            <Compass className="size-4" />
            1. Grant Discovery & Eligibility
          </button>

          <button
            type="button"
            onClick={() => setActiveSection('documents')}
            className={`flex items-center gap-2 pb-3 px-3.5 border-b-2 transition cursor-pointer shrink-0 ${
              activeSection === 'documents'
                ? 'border-indigo-600 text-indigo-600'
                : 'border-transparent text-neutral-500 hover:text-neutral-800'
            }`}
          >
            <FileText className="size-4" />
            2. Compliance Documents Vault ({docCount})
          </button>

          <button
            type="button"
            onClick={() => setActiveSection('profile')}
            className={`flex items-center gap-2 pb-3 px-3.5 border-b-2 transition cursor-pointer shrink-0 ${
              activeSection === 'profile'
                ? 'border-indigo-600 text-indigo-600'
                : 'border-transparent text-neutral-500 hover:text-neutral-800'
            }`}
          >
            <Building2 className="size-4" />
            3. Organization Details & Darpan ID
          </button>
        </div>

        {/* Section Content */}
        {!user && (
          <div className="mb-6 rounded-2xl bg-indigo-50 border border-indigo-200 p-4 text-xs text-indigo-950 flex flex-col sm:flex-row items-start sm:items-center justify-between gap-3">
            <div>
              <p className="font-bold text-sm">Demo Mode — Sign In for Personal Workspace</p>
              <p className="text-indigo-700 mt-0.5">
                Sign in to save your own NGO profiles and attach custom compliance filings to your account.
              </p>
            </div>
            <button
              type="button"
              onClick={() => setShowAuthModal(true)}
              className="rounded-xl bg-indigo-600 hover:bg-indigo-700 text-white px-4 py-2 font-semibold text-xs shadow-xs shrink-0 cursor-pointer"
            >
              Sign In with 1-Click Demo
            </button>
          </div>
        )}

        {activeSection === 'discovery' && (
          <GrantDiscoveryCard ngoId={activeProfile?.id} ngoProfile={activeProfile} />
        )}

        {activeSection === 'documents' && (
          <DocumentUploadCard
            ngoId={activeProfile?.id}
            ngoProfile={activeProfile}
            onDocumentCountChange={(c) => setDocCount(c)}
          />
        )}

        {activeSection === 'profile' && (
          <NGOProfileCard
            currentProfile={activeProfile}
            onProfileSaved={handleProfileSaved}
          />
        )}
      </main>

      {/* Auth Modal */}
      {showAuthModal && (
        <AuthModal
          onAuthSuccess={(u) => {
            setUser(u)
            setShowAuthModal(false)
          }}
          onClose={() => setShowAuthModal(false)}
        />
      )}
    </div>
  )
}
