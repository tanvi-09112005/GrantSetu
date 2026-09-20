import React, { useState, useEffect } from 'react'
import { discoverGrants, checkEligibility } from '../lib/api'
import {
  Compass,
  Search,
  CheckCircle2,
  XCircle,
  AlertTriangle,
  ExternalLink,
  Sparkles,
  Loader2,
  Calendar,
  Layers,
  Building2,
  Filter,
  FileEdit,
  IndianRupee,
  ShieldCheck,
  Globe,
} from 'lucide-react'

export default function GrantDiscoveryCard({
  ngoId,
  ngoProfile,
  onDraftProposal,
  onBatchDraft,
  onResultsLoaded,
}) {
  const [query, setQuery] = useState('')
  const [topK, setTopK] = useState(8)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState(null)
  const [results, setResults] = useState([])
  const [queryUsed, setQueryUsed] = useState(null)
  const [filterType, setFilterType] = useState('all') // all, eligible, govt, csr, international
  const [selectedGrantIds, setSelectedGrantIds] = useState([])

  // Eligibility checking states
  const [checkingId, setCheckingId] = useState(null)
  const [eligibilityResults, setEligibilityResults] = useState({})

  const toggleSelectGrant = (grantId) => {
    setSelectedGrantIds((prev) =>
      prev.includes(grantId)
        ? prev.filter((id) => id !== grantId)
        : [...prev, grantId]
    )
  }

  const selectAllFiltered = () => {
    setSelectedGrantIds(filteredResults.map((g) => g.id))
  }

  const clearSelection = () => {
    setSelectedGrantIds([])
  }

  const handleDiscover = async (e) => {
    if (e) e.preventDefault()
    if (!ngoId) {
      setError('Please select or register an active NGO Profile first.')
      return
    }

    setLoading(true)
    setError(null)

    try {
      const data = await discoverGrants(ngoId, topK, query)
      const grants = data.results || []
      setResults(grants)
      setQueryUsed(data.query)
      if (onResultsLoaded) {
        onResultsLoaded(grants)
      }

      // Auto-evaluate eligibility for the surfaced grants in the background for a smooth UX
      grants.forEach(async (g) => {
        try {
          const v = await checkEligibility(ngoId, g.id)
          setEligibilityResults((prev) => ({ ...prev, [g.id]: v }))
        } catch {
          // Non-blocking
        }
      })
    } catch (err) {
      setError(err.response?.data?.detail || err.message || 'Discovery search failed')
    } finally {
      setLoading(false)
    }
  }

  // Auto-run discovery on mount if ngoId is present and results empty
  useEffect(() => {
    if (ngoId && results.length === 0) {
      handleDiscover()
    }
  }, [ngoId])

  const handleManualCheck = async (grantId) => {
    setCheckingId(grantId)
    try {
      const verdict = await checkEligibility(ngoId, grantId)
      setEligibilityResults((prev) => ({ ...prev, [grantId]: verdict }))
    } catch (err) {
      console.error('Eligibility check failed:', err)
    } finally {
      setCheckingId(null)
    }
  }

  const getFunderTag = (type) => {
    switch (type) {
      case 'govt':
        return (
          <span className="inline-flex items-center gap-1 rounded-full bg-blue-50 px-2.5 py-0.5 text-[11px] font-semibold text-blue-700 border border-blue-200">
            Government of India
          </span>
        )
      case 'international':
        return (
          <span className="inline-flex items-center gap-1 rounded-full bg-purple-50 px-2.5 py-0.5 text-[11px] font-semibold text-purple-700 border border-purple-200">
            <Globe className="size-3" />
            International Grant
          </span>
        )
      case 'csr':
        return (
          <span className="inline-flex items-center gap-1 rounded-full bg-emerald-50 px-2.5 py-0.5 text-[11px] font-semibold text-emerald-700 border border-emerald-200">
            Corporate CSR Grant
          </span>
        )
      default:
        return (
          <span className="inline-flex items-center gap-1 rounded-full bg-amber-50 px-2.5 py-0.5 text-[11px] font-semibold text-amber-700 border border-amber-200">
            Philanthropic Foundation
          </span>
        )
    }
  }

  const filteredResults = results.filter((r) => {
    if (filterType === 'all') return true
    if (filterType === 'eligible') return eligibilityResults[r.id]?.eligible === true
    if (filterType === 'govt') return r.funder_type === 'govt'
    if (filterType === 'csr') return r.funder_type === 'csr'
    if (filterType === 'international') return r.funder_type === 'international'
    return true
  })

  return (
    <div className="space-y-6">
      {/* Header & Search Bar */}
      <div className="rounded-xl border border-neutral-200 bg-white p-6 shadow-xs">
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2 mb-4">
          <div>
            <h3 className="text-lg font-semibold text-neutral-900 flex items-center gap-2">
              <Compass className="size-5 text-indigo-600" />
              Live Grant Opportunity Discovery
            </h3>
            <p className="text-xs text-neutral-500 mt-1">
              Matching <strong className="text-neutral-900">{ngoProfile?.name || 'NGO'}</strong> against 154 live funding calls across Government ministries, CSR foundations, and foreign bilateral programs.
            </p>
          </div>
        </div>

        {error && (
          <div className="mb-4 flex items-center gap-2 rounded-lg bg-red-50 p-3 text-xs text-red-700 border border-red-200">
            <AlertTriangle className="size-4 shrink-0" />
            <span>{error}</span>
          </div>
        )}

        <form onSubmit={handleDiscover} className="space-y-3">
          <div className="flex flex-col sm:flex-row gap-2.5">
            <div className="relative flex-1">
              <Search className="absolute left-3.5 top-3 size-4 text-neutral-400" />
              <input
                type="text"
                value={query}
                onChange={(e) => setQuery(e.target.value)}
                placeholder="Filter by focus keywords (e.g. child education, maternal health, rural drinking water)..."
                className="w-full pl-10 pr-3 py-2.5 text-sm rounded-xl border border-neutral-300 focus:outline-none focus:ring-2 focus:ring-indigo-500/20 focus:border-indigo-500"
              />
            </div>

            <div className="flex items-center gap-2">
              <select
                value={topK}
                onChange={(e) => setTopK(Number(e.target.value))}
                className="rounded-xl border border-neutral-300 px-3 py-2.5 text-xs bg-white font-medium"
              >
                <option value={6}>Show Top 6</option>
                <option value={10}>Show Top 10</option>
                <option value={15}>Show Top 15</option>
              </select>

              <button
                type="submit"
                disabled={loading || !ngoId}
                className="inline-flex items-center justify-center gap-2 rounded-xl bg-indigo-600 hover:bg-indigo-700 px-5 py-2.5 text-sm font-semibold text-white transition shadow-sm disabled:opacity-50 cursor-pointer"
              >
                {loading ? (
                  <>
                    <Loader2 className="size-4 animate-spin" />
                    <span>Searching...</span>
                  </>
                ) : (
                  <>
                    <Sparkles className="size-4" />
                    <span>Discover Matching Grants</span>
                  </>
                )}
              </button>
            </div>
          </div>

          {queryUsed && (
            <p className="text-[11px] text-neutral-400">
              Matched against NGO profile context: <span className="text-neutral-700 font-medium">{queryUsed.slice(0, 140)}...</span>
            </p>
          )}
        </form>

        {/* Filter Pills & Selection Controls */}
        {results.length > 0 && (
          <div className="flex flex-wrap items-center justify-between gap-2 pt-4 border-t border-neutral-100 mt-4">
            <div className="flex flex-wrap items-center gap-2">
              <span className="text-xs text-neutral-500 font-medium flex items-center gap-1 mr-1">
                <Filter className="size-3" /> Filters:
              </span>
              {[
                { id: 'all', label: `All Matches (${results.length})` },
                { id: 'eligible', label: 'Eligible Only' },
                { id: 'govt', label: 'Government (GoI)' },
                { id: 'csr', label: 'CSR Grants' },
                { id: 'international', label: 'International' },
              ].map((f) => (
                <button
                  key={f.id}
                  type="button"
                  onClick={() => setFilterType(f.id)}
                  className={`rounded-lg px-2.5 py-1 text-xs font-medium transition cursor-pointer ${
                    filterType === f.id
                      ? 'bg-neutral-900 text-white'
                      : 'bg-neutral-100 text-neutral-600 hover:bg-neutral-200'
                  }`}
                >
                  {f.label}
                </button>
              ))}
            </div>

            <div className="flex items-center gap-2 text-xs">
              <button
                type="button"
                onClick={selectAllFiltered}
                className="text-indigo-600 hover:text-indigo-800 font-medium cursor-pointer"
              >
                Select All Shown ({filteredResults.length})
              </button>
              {selectedGrantIds.length > 0 && (
                <>
                  <span className="text-neutral-300">|</span>
                  <button
                    type="button"
                    onClick={clearSelection}
                    className="text-neutral-500 hover:text-neutral-700 cursor-pointer"
                  >
                    Clear ({selectedGrantIds.length})
                  </button>
                </>
              )}
            </div>
          </div>
        )}
      </div>

      {/* Grant Opportunity Feed */}
      {filteredResults.length > 0 ? (
        <div className="space-y-4">
          {filteredResults.map((grant) => {
            const verdict = eligibilityResults[grant.id]
            const isChecking = checkingId === grant.id

            const isSelected = selectedGrantIds.includes(grant.id)

            return (
              <div
                key={grant.id}
                className={`rounded-xl border bg-white p-5 shadow-2xs transition ${
                  isSelected
                    ? 'border-indigo-500 ring-2 ring-indigo-500/10'
                    : 'border-neutral-200 hover:border-indigo-300'
                }`}
              >
                <div className="flex flex-col sm:flex-row sm:items-start justify-between gap-3">
                  <div className="flex items-start gap-3 flex-1">
                    <input
                      type="checkbox"
                      checked={isSelected}
                      onChange={() => toggleSelectGrant(grant.id)}
                      title="Select grant for proposal drafting"
                      className="mt-1 size-4 rounded border-neutral-300 text-indigo-600 focus:ring-indigo-500 cursor-pointer shrink-0"
                    />
                    <div className="space-y-1.5 flex-1">
                      <div className="flex flex-wrap items-center gap-2">
                        {getFunderTag(grant.funder_type)}
                        <span className="text-xs font-medium text-neutral-600 flex items-center gap-1">
                          <Building2 className="size-3 text-neutral-400" />
                          {grant.funder_name}
                        </span>
                        {grant.deadline && (
                          <span className="text-xs text-neutral-500 flex items-center gap-1">
                            <Calendar className="size-3 text-neutral-400" />
                            Deadline: {grant.deadline}
                          </span>
                        )}
                      </div>

                      <h4 className="text-base font-bold text-neutral-900 leading-snug">
                        {grant.title}
                      </h4>

                      <p className="text-xs text-neutral-600 line-clamp-2">
                        {grant.description}
                      </p>
                    </div>
                  </div>

                  <div className="flex sm:flex-col items-end justify-between sm:justify-start gap-1 shrink-0">
                    <div className="inline-flex items-center gap-1 rounded-lg bg-indigo-50 px-2.5 py-1 text-xs font-bold text-indigo-700 border border-indigo-100">
                      <Sparkles className="size-3" />
                      {Math.round(grant.score * 100)}% Fit
                    </div>
                    {verdict && (
                      <span
                        className={`inline-flex items-center gap-1 rounded-full px-2.5 py-0.5 text-[10px] font-bold mt-1 ${
                          verdict.eligible
                            ? 'bg-emerald-100 text-emerald-800'
                            : 'bg-red-100 text-red-800'
                        }`}
                      >
                        {verdict.eligible ? '✔ ELIGIBLE' : '✘ INELIGIBLE'}
                      </span>
                    )}
                  </div>
                </div>

                {/* AI Match Reason */}
                {grant.match_reason && (
                  <div className="mt-3 rounded-lg bg-indigo-50/50 p-2.5 text-xs text-indigo-950 border border-indigo-100 flex items-start gap-2">
                    <Sparkles className="size-3.5 text-indigo-600 mt-0.5 shrink-0" />
                    <div>
                      <strong className="text-indigo-900">Why this fits: </strong>
                      {grant.match_reason}
                    </div>
                  </div>
                )}

                {/* Statutory Eligibility Breakdown Accordion */}
                {verdict && (
                  <div
                    className={`mt-3 rounded-xl p-3.5 border text-xs ${
                      verdict.eligible
                        ? 'bg-emerald-50/60 border-emerald-200'
                        : 'bg-amber-50/60 border-amber-200'
                    }`}
                  >
                    <div className="flex items-center justify-between gap-2 font-semibold">
                      <span className={verdict.eligible ? 'text-emerald-900' : 'text-amber-950'}>
                        Statutory Rules Check:{' '}
                        <strong>{verdict.eligible ? 'All legal requirements satisfied' : 'Eligibility barriers detected'}</strong>
                      </span>
                      {verdict.requires_human_review && (
                        <span className="rounded bg-purple-100 text-purple-800 px-2 py-0.5 text-[10px] font-semibold">
                          Foreign Opportunity (FCRA Audit Required)
                        </span>
                      )}
                    </div>

                    {verdict.fcra_blocker && (
                      <div className="mt-2 rounded-lg bg-red-100 p-2.5 text-red-800 font-medium text-[11px]">
                        {verdict.fcra_blocker}
                      </div>
                    )}

                    <div className="mt-2 grid grid-cols-1 sm:grid-cols-2 gap-2 text-[11px] pt-1">
                      <div>
                        <span className="font-semibold text-neutral-700">Satisfied Criteria:</span>
                        <ul className="mt-1 space-y-0.5">
                          {verdict.satisfied_criteria.map((sc, i) => (
                            <li key={i} className="flex items-center gap-1 text-emerald-800">
                              <CheckCircle2 className="size-3 text-emerald-600 shrink-0" />
                              <span>{sc}</span>
                            </li>
                          ))}
                        </ul>
                      </div>

                      {verdict.missing_criteria.length > 0 && (
                        <div>
                          <span className="font-semibold text-neutral-700">Missing Requirements:</span>
                          <ul className="mt-1 space-y-0.5">
                            {verdict.missing_criteria.map((mc, i) => (
                              <li key={i} className="flex items-center gap-1 text-red-700 font-medium">
                                <XCircle className="size-3 text-red-600 shrink-0" />
                                <span>{mc}</span>
                              </li>
                            ))}
                          </ul>
                        </div>
                      )}
                    </div>
                  </div>
                )}

                {/* Footer Actions */}
                <div className="mt-4 pt-3 border-t border-neutral-100 flex flex-wrap items-center justify-between gap-2">
                  <div className="flex flex-wrap gap-1">
                    {grant.sectors?.map((s) => (
                      <span
                        key={s}
                        className="rounded bg-neutral-100 px-2 py-0.5 text-[10px] font-medium text-neutral-600"
                      >
                        #{s}
                      </span>
                    ))}
                  </div>

                  <div className="flex items-center gap-2">
                    {grant.source_url && (
                      <a
                        href={grant.source_url}
                        target="_blank"
                        rel="noreferrer"
                        className="inline-flex items-center gap-1 text-xs text-neutral-600 hover:text-neutral-900 font-medium px-2 py-1"
                      >
                        Official Notification
                        <ExternalLink className="size-3" />
                      </a>
                    )}

                    <button
                      type="button"
                      disabled={isChecking}
                      onClick={() => handleManualCheck(grant.id)}
                      className="inline-flex items-center gap-1.5 rounded-lg border border-neutral-200 bg-white hover:bg-neutral-50 px-3 py-1.5 text-xs font-semibold text-neutral-700 transition cursor-pointer"
                    >
                      {isChecking ? (
                        <Loader2 className="size-3 animate-spin" />
                      ) : (
                        <ShieldCheck className="size-3.5 text-emerald-600" />
                      )}
                      Audit Eligibility
                    </button>

                    <button
                      type="button"
                      onClick={() => onDraftProposal && onDraftProposal(grant)}
                      className="inline-flex items-center gap-1.5 rounded-lg bg-indigo-600 hover:bg-indigo-700 px-3 py-1.5 text-xs font-semibold text-white transition shadow-2xs cursor-pointer"
                    >
                      <FileEdit className="size-3.5" />
                      Draft Proposal
                    </button>
                  </div>
                </div>
              </div>
            )
          })}
        </div>
      ) : (
        !loading && (
          <div className="rounded-xl border border-dashed border-neutral-300 p-12 text-center">
            <Compass className="size-8 mx-auto text-neutral-400 mb-2" />
            <h4 className="text-sm font-semibold text-neutral-700">No Grants Match the Selected Filter</h4>
            <p className="text-xs text-neutral-500 mt-1 max-w-sm mx-auto">
              Try switching the filter to &quot;All Matches&quot; or click &quot;Discover Matching Grants&quot; above.
            </p>
          </div>
        )
      )}

      {/* Floating Bottom Batch Action Bar */}
      {selectedGrantIds.length > 0 && (
        <div className="fixed bottom-6 left-1/2 -translate-x-1/2 z-50 bg-neutral-900 text-white px-5 py-3 rounded-2xl shadow-xl border border-neutral-700 flex items-center gap-4 text-xs animate-in fade-in duration-200">
          <div className="flex items-center gap-2">
            <span className="flex size-5 items-center justify-center rounded-full bg-indigo-600 text-white font-bold text-[11px]">
              {selectedGrantIds.length}
            </span>
            <span className="font-semibold text-neutral-100">
              {selectedGrantIds.length === 1
                ? '1 Grant Selected'
                : `${selectedGrantIds.length} Grants Selected`}
            </span>
          </div>

          <div className="h-4 w-px bg-neutral-700" />

          <button
            type="button"
            onClick={() => {
              const selected = results.filter((g) => selectedGrantIds.includes(g.id))
              if (onBatchDraft) {
                onBatchDraft(selected)
              } else if (onDraftProposal && selected.length > 0) {
                onDraftProposal(selected[0])
              }
            }}
            className="inline-flex items-center gap-1.5 rounded-xl bg-indigo-600 hover:bg-indigo-500 px-4 py-2 font-semibold text-white transition shadow-sm cursor-pointer"
          >
            <Sparkles className="size-3.5" />
            Draft Proposals for Selected ({selectedGrantIds.length})
          </button>

          <button
            type="button"
            onClick={clearSelection}
            className="text-neutral-400 hover:text-white transition cursor-pointer font-medium text-xs"
          >
            Clear
          </button>
        </div>
      )}
    </div>
  )
}
