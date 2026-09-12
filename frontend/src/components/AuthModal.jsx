import React, { useState } from 'react'
import { supabase } from '../lib/supabase'
import { autoConfirmEmail } from '../lib/api'
import { KeyRound, Mail, Lock, UserPlus, LogIn, AlertCircle, CheckCircle2 } from 'lucide-react'

export default function AuthModal({ onAuthSuccess, onClose }) {
  const [isRegister, setIsRegister] = useState(false)
  const [email, setEmail] = useState('tanvi@grantsetu.org')
  const [password, setPassword] = useState('Tanvi@123456')
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState(null)
  const [msg, setMsg] = useState(null)

  const handleSubmit = async (e) => {
    e.preventDefault()
    if (!supabase) {
      setError('Supabase client is not configured.')
      return
    }
    setLoading(true)
    setError(null)
    setMsg(null)

    try {
      if (isRegister) {
        const { data, error: err } = await supabase.auth.signUp({ email, password })
        if (err) throw err
        
        // Auto-confirm in DB in case Supabase project had confirm email enabled
        try {
          await autoConfirmEmail(email)
        } catch {
          // Non-blocking
        }

        // Attempt immediate login
        const loginRes = await supabase.auth.signInWithPassword({ email, password })
        if (loginRes.data?.session) {
          onAuthSuccess(loginRes.data.session.user)
          return
        }

        setMsg('Account created & confirmed! You can now sign in.')
        setIsRegister(false)
      } else {
        let { data, error: err } = await supabase.auth.signInWithPassword({ email, password })
        
        if (err && err.message?.toLowerCase().includes('email not confirmed')) {
          // Auto-confirm via backend and retry
          await autoConfirmEmail(email)
          const retry = await supabase.auth.signInWithPassword({ email, password })
          if (retry.error) throw retry.error
          data = retry.data
          err = null
        }

        if (err) throw err
        if (data?.session) {
          onAuthSuccess(data.session.user)
        }
      }
    } catch (err) {
      setError(err.message || 'Authentication failed')
    } finally {
      setLoading(false)
    }
  }

  const handleDemoSignIn = async () => {
    setEmail('demo.ngo@grantsetu.org')
    setPassword('GrantSetu@2026')
    setLoading(true)
    setError(null)
    try {
      let res = await supabase.auth.signInWithPassword({
        email: 'demo.ngo@grantsetu.org',
        password: 'GrantSetu@2026',
      })
      if (res.error && res.error.message.includes('Invalid login credentials')) {
        await supabase.auth.signUp({
          email: 'demo.ngo@grantsetu.org',
          password: 'GrantSetu@2026',
        })
        await autoConfirmEmail('demo.ngo@grantsetu.org')
        res = await supabase.auth.signInWithPassword({
          email: 'demo.ngo@grantsetu.org',
          password: 'GrantSetu@2026',
        })
      } else if (res.error && res.error.message.toLowerCase().includes('email not confirmed')) {
        await autoConfirmEmail('demo.ngo@grantsetu.org')
        res = await supabase.auth.signInWithPassword({
          email: 'demo.ngo@grantsetu.org',
          password: 'GrantSetu@2026',
        })
      }
      if (res.error) throw res.error
      if (res.data?.session) {
        onAuthSuccess(res.data.session.user)
      }
    } catch (err) {
      setError(err.message)
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40 backdrop-blur-xs p-4">
      <div className="w-full max-w-md bg-white rounded-2xl shadow-xl border border-neutral-200 overflow-hidden p-6 animate-in fade-in zoom-in duration-150">
        <div className="flex justify-between items-start mb-4">
          <div>
            <h2 className="text-xl font-semibold text-neutral-900">
              {isRegister ? 'Create an NGO Account' : 'Sign In to GrantSetu'}
            </h2>
            <p className="text-xs text-neutral-500 mt-1">
              Secure authentication powered by Supabase Auth
            </p>
          </div>
          {onClose && (
            <button onClick={onClose} className="text-neutral-400 hover:text-neutral-600 text-lg leading-none">
              &times;
            </button>
          )}
        </div>

        {error && (
          <div className="mb-4 flex items-center gap-2 rounded-lg bg-red-50 p-3 text-xs text-red-700 border border-red-200">
            <AlertCircle className="size-4 shrink-0" />
            <span>{error}</span>
          </div>
        )}

        {msg && (
          <div className="mb-4 flex items-center gap-2 rounded-lg bg-emerald-50 p-3 text-xs text-emerald-700 border border-emerald-200">
            <CheckCircle2 className="size-4 shrink-0" />
            <span>{msg}</span>
          </div>
        )}

        <form onSubmit={handleSubmit} className="space-y-3">
          <div>
            <label className="block text-xs font-medium text-neutral-700 mb-1">Email Address</label>
            <div className="relative">
              <Mail className="absolute left-3 top-2.5 size-4 text-neutral-400" />
              <input
                type="email"
                required
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                placeholder="ngo@example.org"
                className="w-full pl-9 pr-3 py-2 text-sm rounded-lg border border-neutral-300 focus:outline-none focus:ring-2 focus:ring-indigo-500/20 focus:border-indigo-500"
              />
            </div>
          </div>

          <div>
            <label className="block text-xs font-medium text-neutral-700 mb-1">Password</label>
            <div className="relative">
              <Lock className="absolute left-3 top-2.5 size-4 text-neutral-400" />
              <input
                type="password"
                required
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                placeholder="••••••••"
                className="w-full pl-9 pr-3 py-2 text-sm rounded-lg border border-neutral-300 focus:outline-none focus:ring-2 focus:ring-indigo-500/20 focus:border-indigo-500"
              />
            </div>
          </div>

          <button
            type="submit"
            disabled={loading}
            className="w-full mt-2 py-2.5 px-4 rounded-lg bg-indigo-600 hover:bg-indigo-700 text-white text-sm font-medium transition disabled:opacity-50 flex items-center justify-center gap-2 shadow-xs"
          >
            {isRegister ? <UserPlus className="size-4" /> : <LogIn className="size-4" />}
            {loading ? 'Processing...' : isRegister ? 'Register Account' : 'Sign In'}
          </button>
        </form>

        <div className="relative my-4">
          <div className="absolute inset-0 flex items-center">
            <div className="w-full border-t border-neutral-200" />
          </div>
          <div className="relative flex justify-center text-xs uppercase">
            <span className="bg-white px-2 text-neutral-400">or 1-click test</span>
          </div>
        </div>

        <button
          type="button"
          onClick={handleDemoSignIn}
          disabled={loading}
          className="w-full py-2 px-4 rounded-lg bg-neutral-100 hover:bg-neutral-200 text-neutral-800 text-xs font-medium transition flex items-center justify-center gap-2"
        >
          <KeyRound className="size-3.5 text-neutral-600" />
          Sign In with Pre-Configured Demo Account
        </button>

        <p className="mt-4 text-center text-xs text-neutral-500">
          {isRegister ? 'Already have an account?' : "Don't have an account yet?"}{' '}
          <button
            type="button"
            onClick={() => {
              setIsRegister(!isRegister)
              setError(null)
            }}
            className="text-indigo-600 font-semibold hover:underline"
          >
            {isRegister ? 'Sign In' : 'Register Here'}
          </button>
        </p>
      </div>
    </div>
  )
}
