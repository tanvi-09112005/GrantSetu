import React, { useState } from 'react'
import { supabase } from '../lib/supabase'
import { autoConfirmEmail, registerNgo } from '../lib/api'
import {
  User,
  Building2,
  FileCheck2,
  Check,
  ChevronRight,
  ChevronLeft,
  AlertCircle,
  CheckCircle2,
  ShieldCheck,
  Upload,
  Loader2,
  X,
} from 'lucide-react'

// ---------------------------------------------------------------------------
// Constants & validators (the backend repeats these checks — never trust the UI)
// ---------------------------------------------------------------------------
const DARPAN_RE = /^[A-Z]{2}\/\d{4}\/\d{7}$/ // MH/2021/0123456
const PHONE_RE = /^(?:\+91[\s-]?)?[6-9]\d{9}$/
const EMAIL_RE = /^[^\s@]+@[^\s@]+\.[^\s@]+$/
const THIS_YEAR = new Date().getFullYear()

const DESIGNATIONS = ['Director', 'Trustee', 'Secretary', 'President', 'Treasurer', 'Founder', 'Other']

const STATES = [
  'Andhra Pradesh', 'Arunachal Pradesh', 'Assam', 'Bihar', 'Chhattisgarh', 'Goa', 'Gujarat',
  'Haryana', 'Himachal Pradesh', 'Jharkhand', 'Karnataka', 'Kerala', 'Madhya Pradesh',
  'Maharashtra', 'Manipur', 'Meghalaya', 'Mizoram', 'Nagaland', 'Odisha', 'Punjab',
  'Rajasthan', 'Sikkim', 'Tamil Nadu', 'Telangana', 'Tripura', 'Uttar Pradesh',
  'Uttarakhand', 'West Bengal', 'Andaman and Nicobar Islands', 'Chandigarh',
  'Dadra and Nagar Haveli and Daman and Diu', 'Delhi', 'Jammu and Kashmir', 'Ladakh',
  'Lakshadweep', 'Puducherry',
]

const STEPS = [
  { id: 1, label: 'Admin & Identity', icon: User },
  { id: 2, label: 'Statutory Details', icon: Building2 },
  { id: 3, label: 'Verification Proof', icon: FileCheck2 },
]

const MAX_FILE_MB = 10

const inputCls =
  'w-full px-3 py-2 text-sm rounded-lg border border-neutral-300 focus:outline-none focus:ring-2 focus:ring-indigo-500/20 focus:border-indigo-500 bg-white'
const errCls = 'mt-1 text-[11px] text-red-600'

function Field({ label, error, hint, children }) {
  return (
    <div>
      <label className="block text-xs font-medium text-neutral-700 mb-1">{label}</label>
      {children}
      {hint && !error && <p className="mt-1 text-[11px] text-neutral-500">{hint}</p>}
      {error && <p className={errCls}>{error}</p>}
    </div>
  )
}

// ---------------------------------------------------------------------------
// Per-step validation. Returns an object of {fieldName: message}.
// ---------------------------------------------------------------------------
function validateStep(step, f) {
  const e = {}
  if (step === 1) {
    if (f.adminName.trim().length < 2) e.adminName = 'Enter your full name'
    if (!EMAIL_RE.test(f.email.trim())) e.email = 'Enter a valid work email'
    if (f.password.length < 8) e.password = 'At least 8 characters'
    if (f.confirmPassword !== f.password) e.confirmPassword = 'Passwords do not match'
    if (!f.designation) e.designation = 'Select your designation'
    if (!PHONE_RE.test(f.phone.replace(/\s/g, ''))) e.phone = 'Enter a valid 10-digit Indian mobile number'
  }
  if (step === 2) {
    if (f.ngoName.trim().length < 3) e.ngoName = 'Enter the official registered NGO name'
    const y = Number(f.incorporationYear)
    if (!Number.isInteger(y) || y < 1800 || y > THIS_YEAR) e.incorporationYear = `Enter a year between 1800 and ${THIS_YEAR}`
    if (!f.state) e.state = 'Select a state'
    if (f.district.trim().length < 2) e.district = 'Enter the district'
    if (!DARPAN_RE.test(f.darpanId.trim().toUpperCase())) e.darpanId = 'Format must be XX/YYYY/0123456 (e.g. MH/2021/0123456)'
  }
  return e
}

function fileProblem(file) {
  if (!file) return null
  const isPdf = file.type === 'application/pdf' || file.name.toLowerCase().endsWith('.pdf')
  if (!isPdf) return 'Only PDF files are accepted'
  if (file.size > MAX_FILE_MB * 1024 * 1024) return `File is larger than ${MAX_FILE_MB} MB`
  return null
}

function FileSlot({ label, required, file, onChange, helper }) {
  const problem = fileProblem(file)
  return (
    <div className="rounded-xl border border-neutral-200 p-4 bg-white">
      <div className="flex items-center justify-between mb-2">
        <span className="text-xs font-semibold text-neutral-800">
          {label} {required ? <span className="text-red-500">*</span> : <span className="text-neutral-400 font-normal">(optional)</span>}
        </span>
        {file && !problem && <CheckCircle2 className="size-4 text-emerald-600" />}
      </div>
      {file ? (
        <div className="flex items-center justify-between rounded-lg bg-neutral-50 border border-neutral-200 px-3 py-2 text-xs">
          <span className="truncate max-w-[70%]">{file.name}</span>
          <button type="button" onClick={() => onChange(null)} className="text-neutral-400 hover:text-red-600" aria-label="Remove file">
            <X className="size-4" />
          </button>
        </div>
      ) : (
        <label className="flex flex-col items-center justify-center gap-1 rounded-lg border-2 border-dashed border-neutral-300 hover:border-indigo-400 py-5 cursor-pointer text-xs text-neutral-500">
          <Upload className="size-5 text-neutral-400" />
          <span>Click to choose a PDF (max {MAX_FILE_MB} MB)</span>
          <input
            type="file"
            accept="application/pdf,.pdf"
            className="hidden"
            onChange={(ev) => onChange(ev.target.files?.[0] ?? null)}
          />
        </label>
      )}
      {problem && <p className={errCls}>{problem}</p>}
      {helper && !problem && <p className="mt-1 text-[11px] text-neutral-500">{helper}</p>}
    </div>
  )
}

// ---------------------------------------------------------------------------
// The wizard
// ---------------------------------------------------------------------------
export default function NgoRegisterWizard({ onComplete, onCancel }) {
  const [step, setStep] = useState(1)
  const [errors, setErrors] = useState({})
  const [submitting, setSubmitting] = useState(false)
  const [submitError, setSubmitError] = useState(null)
  const [alreadyRegistered, setAlreadyRegistered] = useState(false)
  const [result, setResult] = useState(null) // set on success

  const [f, setF] = useState({
    // step 1
    adminName: '', email: '', password: '', confirmPassword: '', designation: '', phone: '',
    // step 2
    ngoName: '', incorporationYear: '', state: '', district: '', darpanId: '',
    has12a: false, has80g: false, hasFcra: false,
  })
  const [darpanFile, setDarpanFile] = useState(null)
  const [file12a, setFile12a] = useState(null)
  const [file80g, setFile80g] = useState(null)

  const set = (key) => (ev) => {
    const value = ev.target.type === 'checkbox' ? ev.target.checked : ev.target.value
    setF((prev) => ({ ...prev, [key]: value }))
    setErrors((prev) => ({ ...prev, [key]: undefined }))
  }

  const goNext = () => {
    const e = validateStep(step, f)
    setErrors(e)
    if (Object.keys(e).length === 0) setStep((s) => s + 1)
  }
  const goBack = () => {
    setSubmitError(null)
    setStep((s) => s - 1)
  }

  // Live "instant verification" checks shown on step 3
  const darpanFormatOk = DARPAN_RE.test(f.darpanId.trim().toUpperCase())
  const certUploadedOk = Boolean(darpanFile) && !fileProblem(darpanFile)
  const optionalOk = !fileProblem(file12a) && !fileProblem(file80g)
  const canSubmit = darpanFormatOk && certUploadedOk && optionalOk && !submitting

  const handleSubmit = async () => {
    if (!supabase) {
      setSubmitError('Supabase is not configured (check frontend/.env.local).')
      return
    }
    setSubmitting(true)
    setSubmitError(null)
    setAlreadyRegistered(false)
    try {
      const email = f.email.trim().toLowerCase()

      // 1) Create the login. If a previous attempt already created it (and only
      //    the NGO step failed), fall through and just sign in.
      const { error: signUpErr } = await supabase.auth.signUp({
        email,
        password: f.password,
        options: { data: { full_name: f.adminName.trim(), designation: f.designation } },
      })
      if (signUpErr && !/already registered/i.test(signUpErr.message)) throw signUpErr

      // 2) Get a session (the project auto-confirms email — see AuthModal).
      let login = await supabase.auth.signInWithPassword({ email, password: f.password })
      if (login.error && /not confirmed/i.test(login.error.message)) {
        await autoConfirmEmail(email)
        login = await supabase.auth.signInWithPassword({ email, password: f.password })
      }
      if (login.error) throw login.error

      // 3) Send everything else + the PDFs to the backend in one request.
      const fd = new FormData()
      fd.append('admin_name', f.adminName.trim())
      fd.append('admin_designation', f.designation)
      fd.append('admin_phone', f.phone.replace(/\s/g, ''))
      fd.append('ngo_name', f.ngoName.trim())
      fd.append('incorporation_year', String(f.incorporationYear))
      fd.append('state', f.state)
      fd.append('district', f.district.trim())
      fd.append('darpan_id', f.darpanId.trim().toUpperCase())
      fd.append('has_12a', String(f.has12a))
      fd.append('has_80g', String(f.has80g))
      fd.append('has_fcra', String(f.hasFcra))
      fd.append('darpan_certificate', darpanFile)
      if (file12a) fd.append('cert_12a', file12a)
      if (file80g) fd.append('cert_80g', file80g)

      const res = await registerNgo(fd)
      setResult(res)
    } catch (err) {
      const detail = err.response?.data?.detail
      // Step 2 already signed the user in, so this account just needs to go to its dashboard.
      if (err.response?.status === 409 && /already has an NGO/i.test(String(detail))) {
        setAlreadyRegistered(true)
        return
      }
      setSubmitError(typeof detail === 'string' ? detail : err.message || 'Registration failed. Please try again.')
    } finally {
      setSubmitting(false)
    }
  }

  // ------------------------------- success screen ---------------------------
  if (result) {
    return (
      <div className="mx-auto max-w-xl rounded-2xl bg-white border border-neutral-200 shadow-xs p-8 text-center">
        <div className="mx-auto mb-4 flex size-14 items-center justify-center rounded-full bg-emerald-50">
          <ShieldCheck className="size-8 text-emerald-600" />
        </div>
        <span className="inline-flex items-center gap-1.5 rounded-full bg-emerald-50 px-3 py-1 text-sm font-bold text-emerald-700 border border-emerald-200">
          Statutorily Verified NGO ✓
        </span>
        <h2 className="mt-4 text-lg font-bold text-neutral-900">{f.ngoName}</h2>
        <p className="text-xs text-neutral-500 mt-1">
          Darpan ID <span className="font-mono font-semibold text-neutral-800">{result.darpan_id}</span>
        </p>
        <ul className="mt-4 space-y-1.5 text-xs text-left inline-block">
          <li className="flex items-center gap-2 text-emerald-700"><CheckCircle2 className="size-4" /> Darpan ID format is valid</li>
          <li className="flex items-center gap-2 text-emerald-700"><CheckCircle2 className="size-4" /> Darpan certificate uploaded</li>
                    <li className="flex items-center gap-2 text-emerald-700">
            <CheckCircle2 className="size-4" />
            {result.verification_method === 'vision'
              ? 'Darpan ID and NGO name read from your scanned certificate and matched'
              : 'Darpan ID and NGO name matched with the uploaded certificate'}
          </li>
        </ul>
        <p className="mt-4 text-[11px] text-neutral-500">
          Badge is based on format + document checks. Final confirmation against the NGO Darpan portal is a manual step.
        </p>
        <button
          type="button"
          onClick={() => onComplete?.(result)}
          className="mt-6 w-full rounded-lg bg-indigo-600 hover:bg-indigo-700 text-white text-sm font-medium py-2.5"
        >
          Go to my dashboard
        </button>
      </div>
    )
  }

  // ------------------------------- wizard -----------------------------------
  return (
    <div className="mx-auto max-w-2xl rounded-2xl bg-white border border-neutral-200 shadow-xs overflow-hidden">
      {/* Progress stepper */}
      <div className="px-6 pt-6 pb-4 border-b border-neutral-100">
        <div className="flex items-center justify-between mb-5">
          <div>
            <h2 className="text-lg font-bold text-neutral-900">Register your NGO</h2>
            <p className="text-xs text-neutral-500">3 quick steps · create your account and verify your credentials</p>
          </div>
          {onCancel && (
            <button type="button" onClick={onCancel} className="text-neutral-400 hover:text-neutral-700" aria-label="Close">
              <X className="size-5" />
            </button>
          )}
        </div>
        <ol className="flex items-center">
          {STEPS.map((s, i) => {
            const done = step > s.id
            const active = step === s.id
            const Icon = s.icon
            return (
              <React.Fragment key={s.id}>
                <li className="flex items-center gap-2">
                  <span
                    className={`flex size-8 items-center justify-center rounded-full text-xs font-bold border ${
                      done
                        ? 'bg-emerald-600 border-emerald-600 text-white'
                        : active
                          ? 'bg-indigo-600 border-indigo-600 text-white'
                          : 'bg-white border-neutral-300 text-neutral-400'
                    }`}
                  >
                    {done ? <Check className="size-4" /> : <Icon className="size-4" />}
                  </span>
                  <span className={`hidden sm:block text-xs font-semibold ${active ? 'text-indigo-700' : done ? 'text-emerald-700' : 'text-neutral-400'}`}>
                    Step {s.id} · {s.label}
                  </span>
                </li>
                {i < STEPS.length - 1 && (
                  <div className={`flex-1 h-0.5 mx-3 ${step > s.id ? 'bg-emerald-500' : 'bg-neutral-200'}`} />
                )}
              </React.Fragment>
            )
          })}
        </ol>
      </div>

      <div className="px-6 py-6 space-y-4">
        {/* STEP 1 */}
        {step === 1 && (
          <>
            <Field label="Full name" error={errors.adminName}>
              <input className={inputCls} value={f.adminName} onChange={set('adminName')} placeholder="Asha Verma" autoComplete="name" />
            </Field>
            <Field label="Work email" error={errors.email}>
              <input type="email" className={inputCls} value={f.email} onChange={set('email')} placeholder="asha@myngo.org" autoComplete="email" />
            </Field>
            <div className="grid sm:grid-cols-2 gap-4">
              <Field label="Password" error={errors.password} hint="Minimum 8 characters">
                <input type="password" className={inputCls} value={f.password} onChange={set('password')} autoComplete="new-password" />
              </Field>
              <Field label="Confirm password" error={errors.confirmPassword}>
                <input type="password" className={inputCls} value={f.confirmPassword} onChange={set('confirmPassword')} autoComplete="new-password" />
              </Field>
            </div>
            <div className="grid sm:grid-cols-2 gap-4">
              <Field label="Official designation" error={errors.designation}>
                <select className={inputCls} value={f.designation} onChange={set('designation')}>
                  <option value="">Select…</option>
                  {DESIGNATIONS.map((d) => <option key={d} value={d}>{d}</option>)}
                </select>
              </Field>
              <Field label="Mobile contact" error={errors.phone} hint="10-digit, optionally with +91">
                <input className={inputCls} value={f.phone} onChange={set('phone')} placeholder="9876543210" inputMode="tel" autoComplete="tel" />
              </Field>
            </div>
          </>
        )}

        {/* STEP 2 */}
        {step === 2 && (
          <>
            <Field label="Official registered NGO name" error={errors.ngoName} hint="Exactly as it appears on your registration certificate">
              <input className={inputCls} value={f.ngoName} onChange={set('ngoName')} />
            </Field>
            <div className="grid sm:grid-cols-3 gap-4">
              <Field label="Year of incorporation" error={errors.incorporationYear}>
                <input className={inputCls} value={f.incorporationYear} onChange={set('incorporationYear')} placeholder="2015" inputMode="numeric" maxLength={4} />
              </Field>
              <Field label="State" error={errors.state}>
                <select className={inputCls} value={f.state} onChange={set('state')}>
                  <option value="">Select…</option>
                  {STATES.map((s) => <option key={s} value={s}>{s}</option>)}
                </select>
              </Field>
              <Field label="District" error={errors.district}>
                <input className={inputCls} value={f.district} onChange={set('district')} placeholder="Mumbai Suburban" />
              </Field>
            </div>
            <Field label="NITI Aayog Darpan ID" error={errors.darpanId} hint="Format: XX/YYYY/0123456 — e.g. MH/2021/0123456">
              <input
                className={`${inputCls} font-mono uppercase`}
                value={f.darpanId}
                onChange={(ev) => set('darpanId')({ target: { value: ev.target.value.toUpperCase(), type: 'text' } })}
                placeholder="MH/2021/0123456"
                maxLength={15}
              />
            </Field>
            <fieldset className="rounded-xl border border-neutral-200 p-4">
              <legend className="px-1 text-xs font-semibold text-neutral-700">Legal status</legend>
              <div className="grid sm:grid-cols-3 gap-3 text-sm">
                {[
                  ['has12a', '12A Active'],
                  ['has80g', '80G Active'],
                  ['hasFcra', 'FCRA Approved'],
                ].map(([key, label]) => (
                  <label key={key} className="flex items-center gap-2 cursor-pointer">
                    <input type="checkbox" checked={f[key]} onChange={set(key)} className="size-4 accent-indigo-600" />
                    {label}
                  </label>
                ))}
              </div>
            </fieldset>
          </>
        )}

        {/* STEP 3 */}
        {step === 3 && (
          <>
            <FileSlot
              label="Official Darpan Certificate (PDF)"
              required
              file={darpanFile}
              onChange={setDarpanFile}
              helper="Download it from ngodarpan.gov.in after logging in."
            />
            <div className="grid sm:grid-cols-2 gap-4">
              <FileSlot label="12A certificate" file={file12a} onChange={setFile12a} />
              <FileSlot label="80G certificate" file={file80g} onChange={setFile80g} />
            </div>

            {/* Instant verification check */}
            <div className="rounded-xl bg-neutral-50 border border-neutral-200 p-4 text-xs space-y-2">
              <p className="font-semibold text-neutral-800">Instant verification check</p>
              {[
                [darpanFormatOk, `Darpan ID format valid (${f.darpanId || '—'})`],
                [certUploadedOk, 'Darpan certificate uploaded'],
              ].map(([ok, text]) => (
                <p key={text} className={`flex items-center gap-2 ${ok ? 'text-emerald-700' : 'text-neutral-500'}`}>
                  {ok ? <CheckCircle2 className="size-4" /> : <AlertCircle className="size-4" />}
                  {text}
                </p>
              ))}
            </div>
          </>
        )}

        {alreadyRegistered && (
          <div className="rounded-lg bg-indigo-50 p-4 text-xs text-indigo-900 border border-indigo-200">
            <p className="font-semibold text-sm">This account is already registered</p>
            <p className="mt-1">An NGO is already linked to {f.email}, and you are now signed in.</p>
            <button type="button" onClick={() => onComplete?.(null)}
              className="mt-3 rounded-lg bg-indigo-600 hover:bg-indigo-700 text-white font-medium px-4 py-2">
              Go to my dashboard
            </button>
          </div>
        )}

        {submitError && (
          <div className="flex items-start gap-2 rounded-lg bg-red-50 p-3 text-xs text-red-700 border border-red-200">
            <AlertCircle className="size-4 shrink-0 mt-0.5" />
            <span>{submitError}</span>
          </div>
        )}
      </div>

      {/* Footer buttons */}
      <div className="flex items-center justify-between px-6 py-4 border-t border-neutral-100 bg-neutral-50/60">
        <button
          type="button"
          onClick={goBack}
          disabled={step === 1 || submitting}
          className="inline-flex items-center gap-1 text-sm text-neutral-600 hover:text-neutral-900 disabled:opacity-30"
        >
          <ChevronLeft className="size-4" /> Back
        </button>
        {step < 3 ? (
          <button
            type="button"
            onClick={goNext}
            className="inline-flex items-center gap-1 rounded-lg bg-indigo-600 hover:bg-indigo-700 text-white text-sm font-medium px-5 py-2"
          >
            Next <ChevronRight className="size-4" />
          </button>
        ) : (
          <button
            type="button"
            onClick={handleSubmit}
            disabled={!canSubmit}
            className="inline-flex items-center gap-2 rounded-lg bg-emerald-600 hover:bg-emerald-700 text-white text-sm font-medium px-5 py-2 disabled:opacity-50"
          >
            {submitting ? <Loader2 className="size-4 animate-spin" /> : <ShieldCheck className="size-4" />}
            {submitting ? 'Creating account & verifying…' : 'Submit & Verify'}
          </button>
        )}
      </div>
    </div>
  )
}
