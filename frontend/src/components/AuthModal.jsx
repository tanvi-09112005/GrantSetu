import React, { useState } from 'react'
import { supabase } from '../lib/supabase'
import { autoConfirmEmail } from '../lib/api'
import { KeyRound, Mail, Lock, LogIn, AlertCircle, Loader2 } from 'lucide-react'

// Sign-in only. New accounts are created through the NGO registration wizard,
// so the account and the NGO profile can never get out of sync.
export default function AuthModal({ onAuthSuccess, onClose, onRegister }) {
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState(null)

  const signIn = async (mail, pass) => {
    let res = await supabase.auth.signInWithPassword({ email: mail, password: pass })
    if (res.error && /not confirmed/i.test(res.error.message)) {
      await autoConfirmEmail(mail)
      res = await supabase.auth.signInWithPassword({ email: mail, password: pass })
    }
    if (res.error) throw res.error
    return res.data.session?.user
  }

  const handleSubmit = async (e) => {
    e.preventDefault()
    if (!supabase) {
      setError('Supabase is not configured (check frontend/.env.local).')
      return
    }
    setLoading(true)
    setError(null)
    try {
      const user = await signIn(email.trim().toLowerCase(), password)
      if (user) onAuthSuccess(user)
    } catch (err) {
      setError(
        /invalid login/i.test(err.message || '')
          ? 'Incorrect email or password. New here? Use “Register your NGO”.'
          : err.message || 'Sign in failed',
      )
    } finally {
      setLoading(false)
    }
  }

  // Developer shortcut: only exists in `npm run dev`, never in a production build.
  const handleDemoSignIn = async () => {
    setLoading(true)
    setError(null)
    try {
      const mail = 'demo.ngo@grantsetu.org'
      const pass = 'GrantSetu@2026'
      let res = await supabase.auth.signInWithPassword({ email: mail, password: pass })
      if (res.error && /invalid login/i.test(res.error.message)) {
        await supabase.auth.signUp({ email: mail, password: pass })
      }
      const user = await signIn(mail, pass)
      if (user) onAuthSuccess(user)
    } catch (err) {
      setError(err.message)
    } finally {
      setLoading(false)
    }
  }

  const fieldCls =
    'w-full pl-9 pr-3 py-2 text-sm rounded-lg border border-neutral-300 focus:outline-none focus:ring-2 focus:ring-indigo-500/20 focus:border-indigo-500'

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40 backdrop-blur-xs p-4">
      <div className="w-full max-w-md bg-white rounded-2xl shadow-xl border border-neutral-200 p-6">
        <div className="flex justify-between items-start mb-4">
          <div>
            <h2 className="text-xl font-semibold text-neutral-900">Sign in to GrantSetu</h2>
            <p className="text-xs text-neutral-500 mt-1">Use the email and password you registered with</p>
          </div>
          {onClose && (
            <button onClick={onClose} className="text-neutral-400 hover:text-neutral-600 text-lg leading-none" aria-label="Close">
              &times;
            </button>
          )}
        </div>

        {error && (
          <div className="mb-4 flex items-start gap-2 rounded-lg bg-red-50 p-3 text-xs text-red-700 border border-red-200">
            <AlertCircle className="size-4 shrink-0 mt-0.5" />
            <span>{error}</span>
          </div>
        )}

        <form onSubmit={handleSubmit} className="space-y-3">
          <div>
            <label className="block text-xs font-medium text-neutral-700 mb-1">Email address</label>
            <div className="relative">
              <Mail className="absolute left-3 top-2.5 size-4 text-neutral-400" />
              <input type="email" required autoComplete="email" value={email}
                onChange={(e) => setEmail(e.target.value)} placeholder="ngo@example.org" className={fieldCls} />
            </div>
          </div>
          <div>
            <label className="block text-xs font-medium text-neutral-700 mb-1">Password</label>
            <div className="relative">
              <Lock className="absolute left-3 top-2.5 size-4 text-neutral-400" />
              <input type="password" required autoComplete="current-password" value={password}
                onChange={(e) => setPassword(e.target.value)} placeholder="••••••••" className={fieldCls} />
            </div>
          </div>
          <button type="submit" disabled={loading}
            className="w-full mt-2 py-2.5 px-4 rounded-lg bg-indigo-600 hover:bg-indigo-700 text-white text-sm font-medium transition disabled:opacity-50 flex items-center justify-center gap-2">
            {loading ? <Loader2 className="size-4 animate-spin" /> : <LogIn className="size-4" />}
            {loading ? 'Signing in…' : 'Sign in'}
          </button>
        </form>

        {import.meta.env.DEV && (
          <button type="button" onClick={handleDemoSignIn} disabled={loading}
            className="w-full mt-3 py-2 px-4 rounded-lg bg-neutral-100 hover:bg-neutral-200 text-neutral-700 text-xs font-medium flex items-center justify-center gap-2">
            <KeyRound className="size-3.5" /> Dev only: sign in with demo account
          </button>
        )}

        <p className="mt-4 text-center text-xs text-neutral-500">
          New NGO?{' '}
          <button type="button" onClick={onRegister} className="text-indigo-600 font-semibold hover:underline">
            Register your NGO
          </button>
        </p>
      </div>
    </div>
  )
}
