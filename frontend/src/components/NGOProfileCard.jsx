import React, { useState, useEffect } from 'react'
import { createProfile, updateProfile, getSampleProfiles } from '../lib/api'
import {
  Building2,
  Save,
  CheckCircle2,
  AlertTriangle,
  ShieldCheck,
  Sparkles,
  Award,
  Globe,
  PlusCircle,
  FileCheck,
} from 'lucide-react'

const AVAILABLE_SECTORS = [
  'education',
  'health',
  'child_welfare',
  'nutrition',
  'rural_development',
  'environment',
  'skill_development',
  'technology',
  'social_welfare',
  'disaster_relief',
  'women_empowerment',
]

export default function NGOProfileCard({ currentProfile, onProfileSaved }) {
  const [sampleProfiles, setSampleProfiles] = useState([])
  const [selectedSampleKey, setSelectedSampleKey] = useState('cry-india')
  const [formData, setFormData] = useState({
    name: 'Child Rights and You (CRY)',
    darpan_id: 'DL/2009/0014766',
    location: 'New Delhi, Delhi',
    registered_on: '1979-04-18',
    reg_12a: 'AAATC1234A',
    reg_80g: 'AAATC1234B',
    reg_fcra: '231650035',
    fcra_status: 'active',
    fcra_valid_until: '2028-09-30',
    mission: 'To enable individuals and organizations to collaborate and build an India where all children enjoy their rights to happy, healthy and creative childhoods.',
    sectors: ['education', 'health', 'child_welfare', 'social_welfare'],
  })

  const [saving, setSaving] = useState(false)
  const [success, setSuccess] = useState(false)
  const [error, setError] = useState(null)

  useEffect(() => {
    getSampleProfiles()
      .then((data) => setSampleProfiles(data || []))
      .catch((err) => console.error(err))
  }, [])

  useEffect(() => {
    if (currentProfile) {
      setFormData({
        name: currentProfile.name || '',
        darpan_id: currentProfile.darpan_id || '',
        location: currentProfile.location || '',
        registered_on: currentProfile.registered_on || '',
        reg_12a: currentProfile.reg_12a || '',
        reg_80g: currentProfile.reg_80g || '',
        reg_fcra: currentProfile.reg_fcra || '',
        fcra_status: currentProfile.fcra_status || 'unknown',
        fcra_valid_until: currentProfile.fcra_valid_until || '',
        mission: currentProfile.mission || '',
        sectors: currentProfile.sectors || [],
      })
    }
  }, [currentProfile])

  const handleSelectSample = (sample) => {
    setSelectedSampleKey(sample.id)
    setFormData({
      name: sample.name,
      darpan_id: sample.darpan_id,
      location: sample.location,
      registered_on: sample.registered_on,
      reg_12a: sample.reg_12a,
      reg_80g: sample.reg_80g,
      reg_fcra: sample.reg_fcra,
      fcra_status: sample.fcra_status,
      fcra_valid_until: sample.fcra_valid_until,
      mission: sample.mission,
      sectors: sample.sectors,
    })
    setSuccess(true)
    setTimeout(() => setSuccess(false), 3000)
  }

  const handleClearForNew = () => {
    setSelectedSampleKey('')
    setFormData({
      name: '',
      darpan_id: '',
      location: '',
      registered_on: '',
      reg_12a: '',
      reg_80g: '',
      reg_fcra: '',
      fcra_status: 'never_held',
      fcra_valid_until: '',
      mission: '',
      sectors: [],
    })
  }

  const toggleSector = (sector) => {
    setFormData((prev) => {
      const exists = prev.sectors.includes(sector)
      return {
        ...prev,
        sectors: exists ? prev.sectors.filter((s) => s !== sector) : [...prev.sectors, sector],
      }
    })
  }

  const isDarpanValid = (id) => {
    if (!id) return true
    return /^[A-Z]{2}\/\d{4}\/\d{7}$/.test(id.trim().toUpperCase())
  }

  const handleSubmit = async (e) => {
    e.preventDefault()
    setSaving(true)
    setError(null)
    setSuccess(false)

    if (formData.darpan_id && !isDarpanValid(formData.darpan_id)) {
      setError('Darpan ID must strictly follow official NITI Aayog format: XX/YYYY/0123456 (e.g. MH/2017/0151740)')
      setSaving(false)
      return
    }

    try {
      let saved
      if (currentProfile?.id) {
        saved = await updateProfile(currentProfile.id, formData)
      } else {
        saved = await createProfile(formData)
      }
      setSuccess(true)
      if (onProfileSaved) onProfileSaved(saved)
      setTimeout(() => setSuccess(false), 4000)
    } catch (err) {
      setError(err.response?.data?.detail || err.message || 'Failed to save profile')
    } finally {
      setSaving(false)
    }
  }

  return (
    <div className="space-y-6">
      {/* Top Banner: Quick Select Real Indian NGOs */}
      <div className="rounded-xl border border-indigo-100 bg-linear-to-r from-indigo-50/70 via-white to-indigo-50/30 p-5 shadow-2xs">
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 mb-3">
          <div>
            <h4 className="text-sm font-semibold text-neutral-900 flex items-center gap-2">
              <Sparkles className="size-4 text-indigo-600" />
              Quick Onboarding: Choose a Pre-Verified Indian NGO
            </h4>
            <p className="text-xs text-neutral-500 mt-0.5">
              Select one of India&apos;s leading genuine NGOs to immediately test grant discovery and statutory compliance:
            </p>
          </div>
          <button
            type="button"
            onClick={handleClearForNew}
            className="inline-flex items-center gap-1.5 text-xs text-neutral-700 bg-white border border-neutral-300 rounded-lg px-3 py-1.5 hover:bg-neutral-50 font-medium shrink-0"
          >
            <PlusCircle className="size-3.5 text-neutral-500" />
            Create Custom NGO
          </button>
        </div>

        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-3">
          {sampleProfiles.map((s) => {
            const isCurrent = formData.name === s.name
            return (
              <button
                type="button"
                key={s.id}
                onClick={() => handleSelectSample(s)}
                className={`p-3 rounded-xl border text-left transition cursor-pointer flex flex-col justify-between ${
                  isCurrent
                    ? 'border-indigo-600 bg-white shadow-xs ring-2 ring-indigo-500/20'
                    : 'border-neutral-200 bg-white/80 hover:border-neutral-300 hover:bg-white'
                }`}
              >
                <div>
                  <div className="flex items-center justify-between gap-1 mb-1">
                    <span className="font-semibold text-xs text-neutral-900 line-clamp-1">{s.name}</span>
                    {isCurrent && <CheckCircle2 className="size-3.5 text-indigo-600 shrink-0" />}
                  </div>
                  <div className="text-[11px] font-mono text-neutral-500">ID: {s.darpan_id}</div>
                </div>
                <div className="mt-2 text-[10px] text-emerald-700 font-medium">
                  Active FCRA · 12A/80G
                </div>
              </button>
            )
          })}
        </div>
      </div>

      {/* Main Profile Form */}
      <div className="rounded-xl border border-neutral-200 bg-white p-6 shadow-xs">
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2 mb-6">
          <div>
            <h3 className="text-lg font-semibold text-neutral-900 flex items-center gap-2">
              <Building2 className="size-5 text-indigo-600" />
              Organization Profile & Statutory Credentials
            </h3>
            <p className="text-xs text-neutral-500 mt-1">
              Information registered here is evaluated deterministically against funder eligibility criteria
            </p>
          </div>

          {currentProfile?.id && (
            <span className="inline-flex items-center gap-1.5 rounded-full bg-emerald-50 px-3 py-1 text-xs font-medium text-emerald-700 border border-emerald-200">
              <ShieldCheck className="size-3.5" />
              Active in Supabase
            </span>
          )}
        </div>

        {error && (
          <div className="mb-5 flex items-center gap-2 rounded-lg bg-red-50 p-3 text-xs text-red-700 border border-red-200">
            <AlertTriangle className="size-4 shrink-0" />
            <span>{error}</span>
          </div>
        )}

        {success && (
          <div className="mb-5 flex items-center gap-2 rounded-lg bg-emerald-50 p-3 text-xs text-emerald-700 border border-emerald-200">
            <CheckCircle2 className="size-4 shrink-0" />
            <span>Organization profile saved and updated in PostgreSQL database!</span>
          </div>
        )}

        <form onSubmit={handleSubmit} className="space-y-5">
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div>
              <label className="block text-xs font-semibold text-neutral-700 mb-1">
                Legal Entity Name <span className="text-red-500">*</span>
              </label>
              <input
                type="text"
                required
                value={formData.name}
                onChange={(e) => setFormData({ ...formData, name: e.target.value })}
                placeholder="e.g. Pratham Education Foundation"
                className="w-full rounded-lg border border-neutral-300 px-3 py-2 text-sm focus:ring-2 focus:ring-indigo-500/20 focus:border-indigo-500"
              />
            </div>

            <div>
              <label className="block text-xs font-semibold text-neutral-700 mb-1">
                NITI Aayog NGO Darpan ID
                <span className="text-neutral-400 font-normal ml-1">(Format: XX/YYYY/0123456)</span>
              </label>
              <input
                type="text"
                value={formData.darpan_id}
                onChange={(e) => setFormData({ ...formData, darpan_id: e.target.value.toUpperCase() })}
                placeholder="e.g. MH/2017/0151740"
                className={`w-full rounded-lg border px-3 py-2 text-sm font-mono focus:ring-2 ${
                  formData.darpan_id && !isDarpanValid(formData.darpan_id)
                    ? 'border-red-400 bg-red-50/40 focus:ring-red-500/20'
                    : 'border-neutral-300 focus:ring-indigo-500/20 focus:border-indigo-500'
                }`}
              />
              <p className="mt-1 text-[11px] text-neutral-500">
                Mandatory for Central Government grants-in-aid under NITI Aayog guidelines.
              </p>
            </div>

            <div>
              <label className="block text-xs font-semibold text-neutral-700 mb-1">
                Registered Office Location
              </label>
              <input
                type="text"
                value={formData.location}
                onChange={(e) => setFormData({ ...formData, location: e.target.value })}
                placeholder="e.g. Mumbai, Maharashtra"
                className="w-full rounded-lg border border-neutral-300 px-3 py-2 text-sm focus:ring-2 focus:ring-indigo-500/20"
              />
            </div>

            <div>
              <label className="block text-xs font-semibold text-neutral-700 mb-1">
                Registration / Trust Deed Date
              </label>
              <input
                type="date"
                value={formData.registered_on}
                onChange={(e) => setFormData({ ...formData, registered_on: e.target.value })}
                className="w-full rounded-lg border border-neutral-300 px-3 py-2 text-sm focus:ring-2 focus:ring-indigo-500/20"
              />
              <p className="mt-1 text-[11px] text-neutral-500">
                Determines operational vintage (e.g. many CSR grants require minimum 3 years of active operation).
              </p>
            </div>
          </div>

          {/* Statutory Credentials Card */}
          <div className="rounded-xl border border-neutral-200 bg-neutral-50/70 p-5">
            <h4 className="text-xs font-bold text-neutral-800 uppercase tracking-wider mb-3 flex items-center gap-1.5">
              <Award className="size-4 text-indigo-600" />
              Income Tax & Foreign Contribution Compliance
            </h4>

            <div className="grid grid-cols-1 md:grid-cols-3 gap-3">
              <div>
                <label className="block text-xs font-medium text-neutral-700 mb-1">
                  Section 12A/12AB Ref (Charitable Trust Exemption)
                </label>
                <input
                  type="text"
                  value={formData.reg_12a}
                  onChange={(e) => setFormData({ ...formData, reg_12a: e.target.value.toUpperCase() })}
                  placeholder="e.g. AAATP1234A"
                  className="w-full rounded-lg border border-neutral-300 px-3 py-1.5 text-xs font-mono bg-white"
                />
              </div>

              <div>
                <label className="block text-xs font-medium text-neutral-700 mb-1">
                  Section 80G Approval Ref (Donor Tax Deduction)
                </label>
                <input
                  type="text"
                  value={formData.reg_80g}
                  onChange={(e) => setFormData({ ...formData, reg_80g: e.target.value.toUpperCase() })}
                  placeholder="e.g. AAATP1234B"
                  className="w-full rounded-lg border border-neutral-300 px-3 py-1.5 text-xs font-mono bg-white"
                />
              </div>

              <div>
                <label className="block text-xs font-medium text-neutral-700 mb-1">
                  FCRA Registration Number (MHA)
                </label>
                <input
                  type="text"
                  value={formData.reg_fcra}
                  onChange={(e) => setFormData({ ...formData, reg_fcra: e.target.value })}
                  placeholder="e.g. 083780582"
                  className="w-full rounded-lg border border-neutral-300 px-3 py-1.5 text-xs font-mono bg-white"
                />
              </div>

              <div>
                <label className="block text-xs font-medium text-neutral-700 mb-1">
                  FCRA Status (Foreign Funding Gate)
                </label>
                <select
                  value={formData.fcra_status}
                  onChange={(e) => setFormData({ ...formData, fcra_status: e.target.value })}
                  className="w-full rounded-lg border border-neutral-300 px-2.5 py-1.5 text-xs font-semibold bg-white"
                >
                  <option value="active">Active (Eligible for Foreign Grants)</option>
                  <option value="expired">Expired (Form FC-3C Renewal Needed)</option>
                  <option value="cancelled">Cancelled by MHA</option>
                  <option value="suspended">Suspended</option>
                  <option value="never_held">Never Held</option>
                  <option value="unknown">Unknown</option>
                </select>
              </div>

              <div>
                <label className="block text-xs font-medium text-neutral-700 mb-1">
                  FCRA Valid Until
                </label>
                <input
                  type="date"
                  value={formData.fcra_valid_until}
                  onChange={(e) => setFormData({ ...formData, fcra_valid_until: e.target.value })}
                  className="w-full rounded-lg border border-neutral-300 px-3 py-1.5 text-xs bg-white"
                />
              </div>
            </div>
          </div>

          {/* Mission */}
          <div>
            <label className="block text-xs font-semibold text-neutral-700 mb-1">
              Mission Statement & Core Purpose
            </label>
            <textarea
              rows={2}
              value={formData.mission}
              onChange={(e) => setFormData({ ...formData, mission: e.target.value })}
              placeholder="Describe your organization's core social goals..."
              className="w-full rounded-lg border border-neutral-300 px-3 py-2 text-sm focus:ring-2 focus:ring-indigo-500/20"
            />
          </div>

          {/* Sectors */}
          <div>
            <label className="block text-xs font-semibold text-neutral-700 mb-1.5">
              Operating Thematic Sectors (Used for semantic grant matching)
            </label>
            <div className="flex flex-wrap gap-1.5">
              {AVAILABLE_SECTORS.map((sector) => {
                const active = formData.sectors.includes(sector)
                return (
                  <button
                    type="button"
                    key={sector}
                    onClick={() => toggleSector(sector)}
                    className={`rounded-full px-3 py-1 text-xs font-medium transition cursor-pointer ${
                      active
                        ? 'bg-indigo-600 text-white shadow-2xs'
                        : 'bg-neutral-100 text-neutral-600 hover:bg-neutral-200'
                    }`}
                  >
                    {sector.replace('_', ' ')}
                  </button>
                )
              })}
            </div>
          </div>

          <div className="pt-3 border-t border-neutral-100 flex items-center justify-between">
            <span className="text-xs text-neutral-500">
              Changes will persist to Supabase <code>ngo_profiles</code> table.
            </span>
            <button
              type="submit"
              disabled={saving}
              className="inline-flex items-center gap-2 rounded-xl bg-indigo-600 hover:bg-indigo-700 px-6 py-2.5 text-sm font-semibold text-white transition shadow-sm disabled:opacity-50 cursor-pointer"
            >
              <Save className="size-4" />
              {saving ? 'Saving to Database...' : currentProfile?.id ? 'Update Profile' : 'Register Organization'}
            </button>
          </div>
        </form>
      </div>
    </div>
  )
}
