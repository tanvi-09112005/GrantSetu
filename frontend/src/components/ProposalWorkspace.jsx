import React, { useState, useEffect } from 'react'
import {
  FileText,
  Sparkles,
  CheckCircle2,
  AlertCircle,
  Copy,
  Download,
  Edit3,
  Save,
  Layers,
  Building2,
  Table as TableIcon,
  DollarSign,
  Calendar,
  ShieldCheck,
  Check,
  Database,
  RefreshCw,
  Printer,
  FileCheck2,
  ShieldAlert,
  Eye,
  FileDown,
  ListChecks,
  ChevronRight,
} from 'lucide-react'
import {
  generateProposal,
  batchGenerateProposals,
  exportProposal,
  verifyProposal,
} from '../lib/api'

export default function ProposalWorkspace({
  activeNgo,
  activeGrant,
  batchGrants = [],
  grants = [],
  onSelectGrant,
}) {
  const [selectedGrantId, setSelectedGrantId] = useState(
    activeGrant?.id || grants[0]?.id || '421bc942-7806-4a94-9887-7ed9bde2e254'
  )
  const [templateType, setTemplateType] = useState('standard')
  const [isGenerating, setIsGenerating] = useState(false)
  const [batchGenerating, setBatchGenerating] = useState(false)
  const [batchProposals, setBatchProposals] = useState({})
  const [proposalData, setProposalData] = useState(null)
  const [activeSectionKey, setActiveSectionKey] = useState('executive_summary')
  const [editableSections, setEditableSections] = useState({})
  const [isSaving, setIsSaving] = useState(false)
  const [copied, setCopied] = useState(false)
  const [error, setError] = useState(null)

  // View Mode: 'editor' | 'document' | 'audit'
  const [viewMode, setViewMode] = useState('editor')
  const [isVerifying, setIsVerifying] = useState(false)
  const [verificationResults, setVerificationResults] = useState([])
  const [fabricationRate, setFabricationRate] = useState(0.0)

  // Sync selected grant if activeGrant or grants list updates
  useEffect(() => {
    if (activeGrant?.id) {
      setSelectedGrantId(activeGrant.id)
    } else if (grants.length > 0 && !selectedGrantId) {
      setSelectedGrantId(grants[0].id)
    }
  }, [activeGrant, grants, selectedGrantId])

  // If we already have a generated proposal in the batch cache for this grant, show it
  useEffect(() => {
    if (batchProposals[selectedGrantId]) {
      const prop = batchProposals[selectedGrantId]
      setProposalData(prop)
      setEditableSections(prop.sections || {})
      setVerificationResults(prop.verification_results || [])
      setFabricationRate(prop.fabrication_rate || 0.0)
      const firstKey = Object.keys(prop.sections || {})[0] || 'executive_summary'
      setActiveSectionKey(firstKey)
    }
  }, [selectedGrantId, batchProposals])

  const selectedGrant =
    grants.find((g) => g.id === selectedGrantId) ||
    (activeGrant?.id === selectedGrantId ? activeGrant : null) || {
      id: selectedGrantId,
      title: 'Mission Vatsalya — Child Protection Services',
      funder_name: 'Ministry of Women & Child Development',
      funder_type: 'govt',
    }

  const handleGenerate = async (forceRegenerate = false) => {
    setIsGenerating(true)
    setError(null)
    try {
      const ngoId = activeNgo?.id || 'b6b3f1a9-01ed-4def-8b14-58e4c3e0863e'
      const res = await generateProposal(ngoId, selectedGrantId, templateType, forceRegenerate)
      setProposalData(res)
      setEditableSections(res.sections || {})
      setVerificationResults(res.verification_results || [])
      setFabricationRate(res.fabrication_rate || 0.0)
      setBatchProposals((prev) => ({ ...prev, [selectedGrantId]: res }))
      const firstKey = Object.keys(res.sections || {})[0] || 'executive_summary'
      setActiveSectionKey(firstKey)
    } catch (err) {
      console.error('Proposal generation failed:', err)
      setError(
        err.response?.data?.detail ||
          'Failed to generate proposal draft. Ensure backend is running.'
      )
    } finally {
      setIsGenerating(false)
    }
  }

  const handleBatchGenerate = async () => {
    if (!batchGrants || batchGrants.length === 0) return
    setBatchGenerating(true)
    setError(null)
    try {
      const ngoId = activeNgo?.id || 'b6b3f1a9-01ed-4def-8b14-58e4c3e0863e'
      const grantIds = batchGrants.map((g) => g.id)
      const results = await batchGenerateProposals(ngoId, grantIds, templateType, false)
      const map = {}
      results.forEach((r) => {
        if (r && r.grant_id) map[r.grant_id] = r
      })
      setBatchProposals((prev) => ({ ...prev, ...map }))
      if (map[selectedGrantId]) {
        setProposalData(map[selectedGrantId])
        setEditableSections(map[selectedGrantId].sections || {})
        setVerificationResults(map[selectedGrantId].verification_results || [])
        setFabricationRate(map[selectedGrantId].fabrication_rate || 0.0)
      } else if (results[0]) {
        setSelectedGrantId(results[0].grant_id)
        setProposalData(results[0])
        setEditableSections(results[0].sections || {})
        setVerificationResults(results[0].verification_results || [])
        setFabricationRate(results[0].fabrication_rate || 0.0)
      }
    } catch (err) {
      console.error('Batch proposal generation failed:', err)
      setError(err.response?.data?.detail || 'Failed to generate batch proposals.')
    } finally {
      setBatchGenerating(false)
    }
  }

  const handleVerify = async () => {
    if (!proposalData?.proposal_id) return
    setIsVerifying(true)
    setError(null)
    try {
      const res = await verifyProposal(proposalData.proposal_id)
      setProposalData(res)
      setVerificationResults(res.verification_results || [])
      setFabricationRate(res.fabrication_rate || 0.0)
      setBatchProposals((prev) => ({ ...prev, [selectedGrantId]: res }))
      setViewMode('audit')
    } catch (err) {
      console.error('Fact-check verification failed:', err)
      setError(err.response?.data?.detail || 'Failed to execute fact-check audit.')
    } finally {
      setIsVerifying(false)
    }
  }

  const handleSectionChange = (key, value) => {
    setEditableSections((prev) => ({ ...prev, [key]: value }))
  }

  const handleCopyFull = () => {
    if (!editableSections) return
    const text = Object.entries(editableSections)
      .map(
        ([k, v]) => `## ${k.replace(/_/g, ' ').toUpperCase()}\n\n${v}\n\n---\n`
      )
      .join('\n')
    navigator.clipboard.writeText(text)
    setCopied(true)
    setTimeout(() => setCopied(false), 2000)
  }

  const handleDownload = () => {
    if (!editableSections) return
    const text = Object.entries(editableSections)
      .map(
        ([k, v]) => `## ${k.replace(/_/g, ' ').toUpperCase()}\n\n${v}\n\n---\n`
      )
      .join('\n')
    const blob = new Blob([text], { type: 'text/markdown' })
    const url = URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = url
    a.download = `Proposal_${activeNgo?.name?.replace(/\s+/g, '_') || 'Draft'}.md`
    a.click()
    URL.revokeObjectURL(url)
  }

  const handlePrintPdf = () => {
    setViewMode('document')
    setTimeout(() => {
      window.print()
    }, 150)
  }

  const sectionKeys = Object.keys(editableSections)

  const getSectionIcon = (key) => {
    if (key.includes('budget')) return <DollarSign className="w-4 h-4 text-emerald-600" />
    if (key.includes('matrix') || key.includes('table')) return <TableIcon className="w-4 h-4 text-blue-600" />
    if (key.includes('timeline') || key.includes('plan')) return <Calendar className="w-4 h-4 text-indigo-600" />
    if (key.includes('governance') || key.includes('background')) return <Building2 className="w-4 h-4 text-purple-600" />
    return <FileText className="w-4 h-4 text-slate-600" />
  }

  // Enhanced Markdown & Table Renderer
  const renderFormattedMarkdown = (content) => {
    if (!content) return null

    // Split content into blocks by double newline or table boundaries
    const lines = content.split('\n')
    const blocks = []
    let currentTable = []
    let currentTextLines = []

    lines.forEach((line) => {
      const trimmed = line.trim()
      if (trimmed.startsWith('|')) {
        if (currentTextLines.length > 0) {
          blocks.push({ type: 'text', lines: [...currentTextLines] })
          currentTextLines = []
        }
        currentTable.push(trimmed)
      } else {
        if (currentTable.length > 0) {
          blocks.push({ type: 'table', lines: [...currentTable] })
          currentTable = []
        }
        currentTextLines.push(line)
      }
    })

    if (currentTable.length > 0) {
      blocks.push({ type: 'table', lines: [...currentTable] })
    }
    if (currentTextLines.length > 0) {
      blocks.push({ type: 'text', lines: [...currentTextLines] })
    }

    const parseInline = (text) => {
      if (!text) return ''
      // Replace bold **text**
      const parts = text.split(/(\*\*.*?\*\*)/g)
      return parts.map((p, idx) => {
        if (p.startsWith('**') && p.endsWith('**')) {
          return (
            <strong key={idx} className="font-semibold text-slate-900">
              {p.slice(2, -2)}
            </strong>
          )
        }
        // Highlight currency amounts (e.g. ₹7,92,540)
        const subparts = p.split(/(₹[\d,]+(?:\.\d{2})?)/g)
        if (subparts.length > 1) {
          return subparts.map((sp, sidx) => {
            if (sp.startsWith('₹')) {
              return (
                <span
                  key={sidx}
                  className="font-semibold text-emerald-800 bg-emerald-50 px-1 py-0.5 rounded border border-emerald-200/50 text-[11px]"
                >
                  {sp}
                </span>
              )
            }
            return sp
          })
        }
        return p
      })
    }

    return (
      <div className="space-y-3 font-sans text-xs text-slate-700 leading-relaxed">
        {blocks.map((block, bIdx) => {
          if (block.type === 'table') {
            const tableLines = block.lines
            return (
              <div
                key={bIdx}
                className="my-3 overflow-x-auto rounded-xl border border-slate-200 shadow-2xs bg-white"
              >
                <table className="min-w-full divide-y divide-slate-200 text-xs text-left">
                  <tbody className="divide-y divide-slate-100">
                    {tableLines.map((row, rIdx) => {
                      if (/^\|[-:\s|]+\|$/.test(row)) return null
                      const cols = row
                        .split('|')
                        .map((c) => c.trim())
                        .filter((c, i, arr) => i > 0 && i < arr.length - 1)

                      const isHeader =
                        rIdx === 0 ||
                        (tableLines[rIdx + 1] &&
                          /^\|[-:\s|]+\|$/.test(tableLines[rIdx + 1]))

                      return (
                        <tr
                          key={rIdx}
                          className={
                            isHeader
                              ? 'bg-slate-100 font-bold text-slate-900'
                              : 'even:bg-slate-50/50 hover:bg-indigo-50/20 transition-colors'
                          }
                        >
                          {cols.map((col, cIdx) => (
                            <td
                              key={cIdx}
                              className={`px-3.5 py-2.5 border-r border-slate-100 last:border-r-0 ${
                                isHeader ? 'text-slate-900 font-bold' : 'text-slate-800'
                              } ${
                                col.startsWith('₹') || /^\d+$/.test(col)
                                  ? 'text-right font-mono'
                                  : ''
                              }`}
                            >
                              {parseInline(col)}
                            </td>
                          ))}
                        </tr>
                      )
                    })}
                  </tbody>
                </table>
              </div>
            )
          }

          // Render text block with headings and lists
          return (
            <div key={bIdx} className="space-y-2">
              {block.lines.map((line, lIdx) => {
                const trimmed = line.trim()
                if (!trimmed) return <div key={lIdx} className="h-1" />

                if (trimmed.startsWith('#### ')) {
                  return (
                    <h5 key={lIdx} className="text-xs font-bold text-slate-900 mt-2 mb-1">
                      {parseInline(trimmed.slice(5))}
                    </h5>
                  )
                }
                if (trimmed.startsWith('### ')) {
                  return (
                    <h4
                      key={lIdx}
                      className="text-sm font-bold text-slate-900 mt-3 mb-1.5 flex items-center gap-1.5"
                    >
                      <span className="size-1.5 rounded-full bg-indigo-600 inline-block" />
                      {parseInline(trimmed.slice(4))}
                    </h4>
                  )
                }
                if (trimmed.startsWith('## ')) {
                  return (
                    <h3
                      key={lIdx}
                      className="text-base font-bold text-slate-900 mt-4 mb-2 pb-1 border-b border-slate-200"
                    >
                      {parseInline(trimmed.slice(3))}
                    </h3>
                  )
                }
                if (trimmed.startsWith('- ') || trimmed.startsWith('* ')) {
                  return (
                    <div key={lIdx} className="flex items-start gap-2 pl-2">
                      <span className="text-indigo-600 font-bold mt-0.5">•</span>
                      <p className="flex-1 text-slate-700">{parseInline(trimmed.slice(2))}</p>
                    </div>
                  )
                }
                if (/^\d+\.\s/.test(trimmed)) {
                  const num = trimmed.match(/^(\d+\.)\s/)[1]
                  const rest = trimmed.replace(/^\d+\.\s/, '')
                  return (
                    <div key={lIdx} className="flex items-start gap-2 pl-2">
                      <span className="font-semibold text-slate-900 shrink-0">{num}</span>
                      <p className="flex-1 text-slate-700">{parseInline(rest)}</p>
                    </div>
                  )
                }

                return (
                  <p key={lIdx} className="leading-relaxed">
                    {parseInline(trimmed)}
                  </p>
                )
              })}
            </div>
          )
        })}
      </div>
    )
  }

  return (
    <div className="space-y-6">
      {/* Print-specific style sheet */}
      <style>{`
        @media print {
          @page {
            size: A4;
            margin: 14mm 12mm;
          }
          body * {
            visibility: hidden !important;
          }
          #printable-proposal-document,
          #printable-proposal-document * {
            visibility: visible !important;
          }
          #printable-proposal-document {
            position: absolute !important;
            left: 0 !important;
            top: 0 !important;
            width: 100% !important;
            margin: 0 !important;
            padding: 0 !important;
            background: #ffffff !important;
            color: #0f172a !important;
            font-size: 10.5pt !important;
            border: none !important;
            box-shadow: none !important;
          }
          .print-section {
            page-break-inside: avoid !important;
            break-inside: avoid !important;
            margin-bottom: 16pt !important;
          }
          table {
            page-break-inside: avoid !important;
            break-inside: avoid !important;
            width: 100% !important;
            border-collapse: collapse !important;
          }
          th, td {
            border: 1px solid #cbd5e1 !important;
            padding: 5pt 7pt !important;
            font-size: 9pt !important;
          }
          .signature-block {
            page-break-inside: avoid !important;
            break-inside: avoid !important;
            margin-top: 20pt !important;
          }
        }
      `}</style>

      {/* Batch Drafting Mode Banner */}
      {batchGrants && batchGrants.length > 1 && (
        <div className="rounded-xl border border-indigo-200 bg-indigo-50/80 p-4 flex flex-col sm:flex-row sm:items-center justify-between gap-3 shadow-2xs no-print">
          <div>
            <span className="inline-flex items-center gap-1.5 font-bold text-xs text-indigo-900">
              <Sparkles className="w-4 h-4 text-indigo-600" />
              Batch Drafting Mode Active ({batchGrants.length} grants selected)
            </span>
            <p className="text-xs text-indigo-700 mt-0.5">
              Draft proposals for all {batchGrants.length} selected grants with rate-limiting to protect free-tier API quotas.
            </p>
          </div>
          <button
            type="button"
            disabled={batchGenerating || isGenerating}
            onClick={handleBatchGenerate}
            className="inline-flex items-center gap-2 rounded-lg bg-indigo-600 hover:bg-indigo-700 px-4 py-2 text-xs font-semibold text-white shadow-xs transition cursor-pointer shrink-0 disabled:opacity-50"
          >
            {batchGenerating ? (
              <>
                <div className="w-3.5 h-3.5 border-2 border-white/30 border-t-white rounded-full animate-spin" />
                Batch Drafting ({Object.keys(batchProposals).length}/{batchGrants.length})...
              </>
            ) : (
              <>
                <Sparkles className="w-3.5 h-3.5" />
                Batch Draft All {batchGrants.length} Proposals
              </>
            )}
          </button>
        </div>
      )}

      {/* Top Configuration Card */}
      <div className="bg-white rounded-xl shadow-xs border border-slate-200 p-6 no-print">
        <div className="flex flex-col lg:flex-row lg:items-center justify-between gap-6 pb-6 border-b border-slate-100">
          <div>
            <div className="flex items-center gap-2 mb-1">
              <span className="p-1.5 bg-indigo-50 text-indigo-700 rounded-lg">
                <Sparkles className="w-5 h-5" />
              </span>
              <h2 className="text-xl font-bold text-slate-900">
                Multi-Agent Proposal Generator
              </h2>
            </div>
            <p className="text-sm text-slate-600">
              Draft professional, funder-tailored grant proposals grounded in{' '}
              <strong className="text-slate-900">{activeNgo?.name || 'Child Rights and You (CRY)'}</strong>'s
              verified document chunks.
            </p>
          </div>

          {/* Action Buttons */}
          <div className="flex flex-wrap items-center gap-2.5">
            <button
              onClick={() => handleGenerate(false)}
              disabled={isGenerating || batchGenerating}
              className={`flex items-center gap-2 px-5 py-2.5 rounded-lg text-sm font-semibold transition-all shadow-xs ${
                isGenerating
                  ? 'bg-indigo-400 text-white cursor-not-allowed'
                  : 'bg-indigo-600 hover:bg-indigo-700 text-white shadow-indigo-100 cursor-pointer'
              }`}
            >
              {isGenerating ? (
                <>
                  <div className="w-4 h-4 border-2 border-white/30 border-t-white rounded-full animate-spin" />
                  Generating Draft...
                </>
              ) : (
                <>
                  <Sparkles className="w-4 h-4" />
                  {proposalData ? 'Load / Check Cache' : '⚡ Generate Proposal Draft'}
                </>
              )}
            </button>

            {proposalData && (
              <button
                onClick={() => handleGenerate(true)}
                disabled={isGenerating || batchGenerating}
                title="Force fresh regeneration with Gemini Flash (consumes 1 API call)"
                className="flex items-center gap-1.5 px-3.5 py-2.5 rounded-lg text-xs font-semibold bg-neutral-100 hover:bg-neutral-200 text-neutral-800 transition border border-neutral-300 disabled:opacity-50 cursor-pointer"
              >
                <RefreshCw className={`w-3.5 h-3.5 ${isGenerating ? 'animate-spin' : ''}`} />
                Force Regenerate with AI
              </button>
            )}

            {proposalData && (
              <button
                onClick={handleVerify}
                disabled={isVerifying || isGenerating}
                title="Audit factual claims against uploaded documents"
                className="flex items-center gap-1.5 px-3.5 py-2.5 rounded-lg text-xs font-semibold bg-emerald-50 hover:bg-emerald-100 text-emerald-800 transition border border-emerald-300 disabled:opacity-50 cursor-pointer"
              >
                {isVerifying ? (
                  <>
                    <div className="w-3.5 h-3.5 border-2 border-emerald-600 border-t-transparent rounded-full animate-spin" />
                    Auditing Claims...
                  </>
                ) : (
                  <>
                    <ShieldCheck className="w-3.5 h-3.5 text-emerald-600" />
                    Run Fact-Check Audit
                  </>
                )}
              </button>
            )}
          </div>
        </div>

        {/* Controls Grid */}
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4 pt-4">
          {/* Target Grant Selector */}
          <div>
            <label className="block text-xs font-semibold text-slate-700 uppercase tracking-wider mb-2">
              Target Grant Opportunity
            </label>
            <select
              value={selectedGrantId}
              onChange={(e) => setSelectedGrantId(e.target.value)}
              className="w-full text-sm rounded-lg border border-slate-300 bg-white px-3 py-2 text-slate-800 focus:border-indigo-500 focus:outline-hidden focus:ring-1 focus:ring-indigo-500"
            >
              {grants.length > 0 ? (
                grants.map((g) => (
                  <option key={g.id} value={g.id}>
                    {g.title} ({g.funder_name})
                  </option>
                ))
              ) : (
                <option value="421bc942-7806-4a94-9887-7ed9bde2e254">
                  Mission Vatsalya (Ministry of Women & Child Development)
                </option>
              )}
            </select>
          </div>

          {/* Funder Template Picker */}
          <div>
            <label className="block text-xs font-semibold text-slate-700 uppercase tracking-wider mb-2">
              Proposal Template Specification
            </label>
            <select
              value={templateType}
              onChange={(e) => setTemplateType(e.target.value)}
              className="w-full text-sm rounded-lg border border-slate-300 bg-white px-3 py-2 text-slate-800 focus:border-indigo-500 focus:outline-hidden focus:ring-1 focus:ring-indigo-500"
            >
              <option value="standard">
                Standard Indian NGO Format (8 Sections + Activity Matrix & Line-Item Budget)
              </option>
              <option value="csr">
                CSR Foundation Format (Schedule VII, Logframe & Tranche Schedule)
              </option>
              <option value="govt">
                Central Govt Grants-in-Aid (NITI Aayog Convergence & GIA Norms)
              </option>
            </select>
          </div>
        </div>

        {error && (
          <div className="mt-4 p-3 bg-rose-50 border border-rose-200 rounded-lg text-xs text-rose-800 flex items-center gap-2">
            <AlertCircle className="w-4 h-4 text-rose-600 shrink-0" />
            <span>{error}</span>
          </div>
        )}
      </div>

      {/* Proposal Drafting & Viewing Interface */}
      {proposalData && (
        <div className="bg-white rounded-xl shadow-xs border border-slate-200 overflow-hidden">
          {/* Workspace Top Toolbar & View Mode Tabs */}
          <div className="bg-slate-50 px-6 py-3 border-b border-slate-200 flex flex-wrap items-center justify-between gap-4 no-print">
            {/* Status Badges */}
            <div className="flex flex-wrap items-center gap-2">
              <span className="text-xs font-bold text-slate-500 uppercase">
                Proposal ID:
              </span>
              <code className="text-xs bg-white border border-slate-200 px-2 py-0.5 rounded text-slate-700 font-mono">
                {proposalData.proposal_id?.slice(0, 8)}...
              </code>
              <span className="inline-flex items-center gap-1 text-xs font-medium px-2 py-0.5 rounded-full bg-emerald-100 text-emerald-800">
                <CheckCircle2 className="w-3 h-3" /> Grounded in Document Vault
              </span>

              {proposalData.status === 'cached' && (
                <span
                  className="inline-flex items-center gap-1 text-xs font-semibold px-2.5 py-0.5 rounded-full bg-blue-100 text-blue-800 border border-blue-200"
                  title="Retrieved instantly from database with 0 external API calls"
                >
                  <Database className="w-3 h-3 text-blue-600" /> Loaded from DB Cache (0 API calls, &lt;50ms)
                </span>
              )}
              {proposalData.status === 'drafted' && (
                <span className="inline-flex items-center gap-1 text-xs font-semibold px-2.5 py-0.5 rounded-full bg-emerald-100 text-emerald-800 border border-emerald-200">
                  <Sparkles className="w-3 h-3 text-emerald-600" /> Newly Generated with Gemini Flash
                </span>
              )}
              {verificationResults.length === 0 ? (
                <span className="inline-flex items-center gap-1 text-xs font-semibold px-2.5 py-0.5 rounded-full bg-amber-50 text-amber-800 border border-amber-200">
                  <AlertCircle className="w-3 h-3 text-amber-600" /> Audit Pending — Click &quot;Run Fact-Check Audit&quot;
                </span>
              ) : (
                <span
                  className={`inline-flex items-center gap-1 text-xs font-bold px-2.5 py-0.5 rounded-full border ${
                    fabricationRate === 0
                      ? 'bg-emerald-50 text-emerald-800 border-emerald-200'
                      : fabricationRate <= 0.1
                      ? 'bg-blue-50 text-blue-800 border-blue-200'
                      : 'bg-rose-50 text-rose-800 border-rose-200'
                  }`}
                >
                  <ShieldCheck className="w-3 h-3" />
                  {verificationResults.filter((r) => r.verdict === 'supported').length}/{verificationResults.length} Claims Verified
                  {' '}({(fabricationRate * 100).toFixed(1)}% Unsupported)
                </span>
              )}
            </div>

            {/* View Mode Switcher */}
            <div className="flex items-center bg-slate-200/70 p-1 rounded-lg text-xs font-semibold">
              <button
                type="button"
                onClick={() => setViewMode('editor')}
                className={`px-3 py-1.5 rounded-md transition-all cursor-pointer flex items-center gap-1.5 ${
                  viewMode === 'editor'
                    ? 'bg-white text-indigo-700 shadow-xs'
                    : 'text-slate-600 hover:text-slate-900'
                }`}
              >
                <Edit3 className="w-3.5 h-3.5" />
                Section Editor
              </button>
              <button
                type="button"
                onClick={() => setViewMode('document')}
                className={`px-3 py-1.5 rounded-md transition-all cursor-pointer flex items-center gap-1.5 ${
                  viewMode === 'document'
                    ? 'bg-white text-indigo-700 shadow-xs'
                    : 'text-slate-600 hover:text-slate-900'
                }`}
              >
                <Eye className="w-3.5 h-3.5" />
                Full Formal Document
              </button>
              <button
                type="button"
                onClick={() => setViewMode('audit')}
                className={`px-3 py-1.5 rounded-md transition-all cursor-pointer flex items-center gap-1.5 ${
                  viewMode === 'audit'
                    ? 'bg-white text-indigo-700 shadow-xs'
                    : 'text-slate-600 hover:text-slate-900'
                }`}
              >
                <FileCheck2 className="w-3.5 h-3.5" />
                Fact-Check Audit ({verificationResults.length})
              </button>
            </div>

            {/* Export Actions */}
            <div className="flex items-center gap-2">
              <button
                onClick={handlePrintPdf}
                title="Print or Save as Vector PDF"
                className="flex items-center gap-1.5 px-3 py-1.5 text-xs font-semibold text-white bg-indigo-600 rounded-lg hover:bg-indigo-700 transition-colors shadow-2xs cursor-pointer"
              >
                <Printer className="w-3.5 h-3.5" />
                Export as PDF
              </button>
              <button
                onClick={handleCopyFull}
                className="flex items-center gap-1.5 px-3 py-1.5 text-xs font-medium text-slate-700 bg-white border border-slate-200 rounded-lg hover:bg-slate-50 transition-colors shadow-2xs cursor-pointer"
              >
                {copied ? (
                  <>
                    <Check className="w-3.5 h-3.5 text-emerald-600" />
                    Copied!
                  </>
                ) : (
                  <>
                    <Copy className="w-3.5 h-3.5 text-slate-500" />
                    Copy .md
                  </>
                )}
              </button>
              <button
                onClick={handleDownload}
                className="flex items-center gap-1.5 px-3 py-1.5 text-xs font-medium text-slate-700 bg-white border border-slate-200 rounded-lg hover:bg-slate-50 transition-colors shadow-2xs cursor-pointer"
              >
                <Download className="w-3.5 h-3.5" />
                Export .md
              </button>
            </div>
          </div>

          {/* VIEW MODE 1: Interactive Section Editor */}
          {viewMode === 'editor' && (
            <div className="grid grid-cols-1 lg:grid-cols-12 min-h-[550px] no-print">
              {/* Sidebar Section Navigator */}
              <div className="lg:col-span-4 border-r border-slate-200 bg-slate-50/50 p-4 space-y-1">
                <div className="text-xs font-semibold text-slate-500 uppercase tracking-wider px-3 mb-2">
                  Proposal Sections ({sectionKeys.length})
                </div>
                {sectionKeys.map((key) => {
                  const isActive = activeSectionKey === key
                  const title = key
                    .replace(/_/g, ' ')
                    .replace(/\b\w/g, (l) => l.toUpperCase())

                  return (
                    <button
                      key={key}
                      onClick={() => setActiveSectionKey(key)}
                      className={`w-full text-left px-3 py-2.5 rounded-lg text-xs font-medium flex items-center justify-between transition-colors cursor-pointer ${
                        isActive
                          ? 'bg-indigo-50 text-indigo-700 font-semibold border border-indigo-200/60 shadow-2xs'
                          : 'text-slate-600 hover:bg-slate-100 hover:text-slate-900'
                      }`}
                    >
                      <div className="flex items-center gap-2 truncate">
                        {getSectionIcon(key)}
                        <span className="truncate">{title}</span>
                      </div>
                      <ChevronRight
                        className={`w-3.5 h-3.5 shrink-0 ${
                          isActive ? 'text-indigo-600' : 'text-slate-400'
                        }`}
                      />
                    </button>
                  )
                })}
              </div>

              {/* Content Area */}
              <div className="lg:col-span-8 p-6 flex flex-col justify-between">
                <div>
                  <div className="flex items-center justify-between pb-4 border-b border-slate-100 mb-4">
                    <div>
                      <h3 className="text-sm font-bold text-slate-900">
                        {activeSectionKey
                          .replace(/_/g, ' ')
                          .replace(/\b\w/g, (l) => l.toUpperCase())}
                      </h3>
                      <p className="text-[11px] text-slate-500">
                        Edit drafted text directly. Changes persist across view modes.
                      </p>
                    </div>

                    <div className="flex items-center gap-2 text-xs">
                      <span className="text-slate-400 font-mono text-[11px]">
                        {editableSections[activeSectionKey]?.length || 0} chars
                      </span>
                    </div>
                  </div>

                  {/* Enhanced Formatted Preview */}
                  <div className="space-y-4">
                    <div className="rounded-xl border border-slate-200 bg-slate-50/50 p-5">
                      <span className="text-[10px] font-bold text-slate-400 uppercase tracking-wider block mb-3">
                        Rich Formatted View
                      </span>
                      {renderFormattedMarkdown(editableSections[activeSectionKey])}
                    </div>

                    {/* Raw Edit Field */}
                    <div>
                      <label className="block text-[11px] font-semibold text-slate-700 mb-1">
                        Markdown Source (Editable)
                      </label>
                      <textarea
                        rows={8}
                        value={editableSections[activeSectionKey] || ''}
                        onChange={(e) =>
                          handleSectionChange(activeSectionKey, e.target.value)
                        }
                        className="w-full text-xs font-mono rounded-lg border border-slate-200 p-3 text-slate-800 focus:border-indigo-500 focus:outline-hidden focus:ring-1 focus:ring-indigo-500 bg-white"
                        placeholder="Enter section markdown..."
                      />
                    </div>
                  </div>
                </div>

                {/* Bottom Pagination / Navigation */}
                <div className="flex items-center justify-between pt-6 border-t border-slate-100 mt-6 text-xs text-slate-500">
                  <span>
                    Section {sectionKeys.indexOf(activeSectionKey) + 1} of{' '}
                    {sectionKeys.length}
                  </span>
                  <div className="flex gap-2">
                    <button
                      disabled={sectionKeys.indexOf(activeSectionKey) === 0}
                      onClick={() => {
                        const idx = sectionKeys.indexOf(activeSectionKey)
                        if (idx > 0) setActiveSectionKey(sectionKeys[idx - 1])
                      }}
                      className="px-3 py-1.5 border border-slate-200 rounded-lg hover:bg-slate-50 disabled:opacity-40 disabled:cursor-not-allowed cursor-pointer"
                    >
                      Previous Section
                    </button>
                    <button
                      disabled={
                        sectionKeys.indexOf(activeSectionKey) ===
                        sectionKeys.length - 1
                      }
                      onClick={() => {
                        const idx = sectionKeys.indexOf(activeSectionKey)
                        if (idx < sectionKeys.length - 1)
                          setActiveSectionKey(sectionKeys[idx + 1])
                      }}
                      className="px-3 py-1.5 bg-slate-900 text-white rounded-lg hover:bg-slate-800 disabled:opacity-40 disabled:cursor-not-allowed cursor-pointer"
                    >
                      Next Section
                    </button>
                  </div>
                </div>
              </div>
            </div>
          )}

          {/* VIEW MODE 2: Full Formal Proposal Document (Filing Preview & Print-Ready PDF) */}
          <div
            id="printable-proposal-document"
            className={`p-8 sm:p-12 max-w-4xl mx-auto ${
              viewMode === 'document' ? 'block' : 'hidden print:block'
            }`}
          >
            {/* Formal Grant Application Letterhead */}
            <div className="pb-8 mb-8 border-b-2 border-slate-800">
              <div className="flex flex-col sm:flex-row sm:items-start justify-between gap-4">
                <div>
                  <span className="text-[11px] font-mono tracking-widest text-indigo-700 uppercase font-bold">
                    Formal Grant Application Dossier
                  </span>
                  <h1 className="text-2xl font-black text-slate-900 mt-1 tracking-tight">
                    {selectedGrant?.title || 'Grant Proposal'}
                  </h1>
                  <p className="text-sm font-semibold text-slate-700 mt-1">
                    Submitted to: <strong className="text-slate-900">{selectedGrant?.funder_name}</strong>
                  </p>
                </div>

                <div className="text-left sm:text-right text-xs text-slate-600 space-y-1">
                  <div className="font-bold text-slate-900 text-sm">
                    {activeNgo?.name || 'Child Rights and You (CRY)'}
                  </div>
                  <div>
                    Darpan ID: <span className="font-mono font-semibold">{activeNgo?.darpan_id || 'DL/2009/0014766'}</span>
                  </div>
                  <div>
                    Statutory Status: <span className="text-emerald-700 font-semibold">12A & 80G Certified</span>
                  </div>
                  <div>
                    Date: <span className="font-medium">{new Date().toLocaleDateString('en-IN', { dateStyle: 'long' })}</span>
                  </div>
                </div>
              </div>
            </div>

            {/* All Sections Continuous Presentation */}
            <div className="space-y-8">
              {sectionKeys.map((key, sIdx) => {
                const title = key
                  .replace(/_/g, ' ')
                  .replace(/\b\w/g, (l) => l.toUpperCase())
                const content = editableSections[key]

                return (
                  <section key={key} className="print-section pb-6 border-b border-slate-100 last:border-b-0">
                    <div className="flex items-center gap-2 mb-3">
                      <span className="flex size-6 items-center justify-center rounded-full bg-slate-900 text-white font-bold text-xs">
                        {sIdx + 1}
                      </span>
                      <h2 className="text-base font-bold text-slate-900">
                        {title}
                      </h2>
                    </div>
                    <div className="pl-8">
                      {renderFormattedMarkdown(content)}
                    </div>
                  </section>
                )
              })}
            </div>

            {/* Sign-off / Signature Block */}
            <div className="signature-block mt-12 pt-8 border-t border-slate-300 grid grid-cols-2 gap-8 text-xs text-slate-600">
              <div>
                <p className="font-bold text-slate-900 mb-1">Authorized Signatory</p>
                <p>{activeNgo?.name || 'Child Rights and You (CRY)'}</p>
                <div className="h-12 border-b border-dashed border-slate-300 mt-4" />
                <p className="text-[10px] text-slate-400 mt-1">Official Seal & Signature</p>
              </div>

              <div className="text-right">
                <p className="font-bold text-slate-900 mb-1">System Verification</p>
                <p>Certified by GrantSetu Multi-Agent System</p>
                <p className="text-[10px] text-slate-400 mt-1 font-mono">
                  Tracking ID: {proposalData.proposal_id}
                </p>
              </div>
            </div>
          </div>

          {/* VIEW MODE 3: Fact-Check & Verification Audit */}
          {viewMode === 'audit' && (
            <div className="p-6 sm:p-8 space-y-6 no-print">
              {/* Scorecard Banner */}
              <div className="rounded-2xl border border-slate-200 bg-slate-50/70 p-6">
                <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
                  <div>
                    <div className="flex items-center gap-2">
                      <ShieldCheck className="size-6 text-emerald-600" />
                      <h3 className="text-lg font-bold text-slate-900">
                        FActScore Entailment & Fact-Check Audit
                      </h3>
                    </div>
                    <p className="text-xs text-slate-600 mt-1 max-w-xl">
                      Every quantitative metric (beneficiaries, budgets, timelines) and statutory statement
                      in this proposal is verified against{' '}
                      <strong>{activeNgo?.name || 'CRY'}</strong>'s certified document vault.
                    </p>
                  </div>

                  <div className="flex items-center gap-3">
                    <div className="text-center px-4 py-2 bg-white rounded-xl border border-slate-200 shadow-2xs">
                      <span className="text-[10px] text-slate-500 block uppercase font-bold">
                        Fabrication Rate
                      </span>
                      <span
                        className={`text-xl font-black ${
                          fabricationRate === 0 ? 'text-emerald-600' : 'text-amber-600'
                        }`}
                      >
                        {(fabricationRate * 100).toFixed(1)}%
                      </span>
                    </div>

                    <button
                      type="button"
                      onClick={handleVerify}
                      disabled={isVerifying}
                      className="inline-flex items-center gap-1.5 px-4 py-3 rounded-xl bg-indigo-600 hover:bg-indigo-700 text-white text-xs font-semibold shadow-xs transition cursor-pointer disabled:opacity-50"
                    >
                      {isVerifying ? (
                        <>
                          <div className="size-3.5 border-2 border-white border-t-transparent rounded-full animate-spin" />
                          Auditing...
                        </>
                      ) : (
                        <>
                          <RefreshCw className="size-3.5" />
                          Re-Run Audit
                        </>
                      )}
                    </button>
                  </div>
                </div>
              </div>

              {/* Claims Audit Breakdown */}
              <div className="space-y-3">
                <div className="flex items-center justify-between text-xs text-slate-600 font-semibold px-1">
                  <span>Audited Atomic Claims ({verificationResults.length})</span>
                  <span>Grounding Source: Document Vault & NITI Aayog Profile</span>
                </div>

                {verificationResults.length > 0 ? (
                  <div className="space-y-2.5">
                    {verificationResults.map((item, idx) => {
                      const isSupported = item.verdict === 'supported'
                      const isPartial = item.verdict === 'partially_supported'

                      return (
                        <div
                          key={idx}
                          className={`rounded-xl p-4 border text-xs transition-all ${
                            isSupported
                              ? 'bg-emerald-50/50 border-emerald-200'
                              : isPartial
                              ? 'bg-amber-50/50 border-amber-200'
                              : 'bg-rose-50/50 border-rose-200'
                          }`}
                        >
                          <div className="flex items-start justify-between gap-3">
                            <div className="flex items-start gap-2.5 flex-1">
                              {isSupported ? (
                                <CheckCircle2 className="size-4 text-emerald-600 shrink-0 mt-0.5" />
                              ) : isPartial ? (
                                <AlertCircle className="size-4 text-amber-600 shrink-0 mt-0.5" />
                              ) : (
                                <ShieldAlert className="size-4 text-rose-600 shrink-0 mt-0.5" />
                              )}
                              <div className="space-y-1">
                                <p className="font-semibold text-slate-900 leading-snug">
                                  {item.claim_text}
                                </p>
                                {item.evidence_span && (
                                  <p className="text-[11px] text-slate-600 flex items-start gap-1">
                                    <strong className="text-slate-800">Evidence Quote:</strong>{' '}
                                    <span className="italic font-mono bg-white/80 px-1.5 py-0.5 rounded border border-slate-200">
                                      &quot;{item.evidence_span}&quot;
                                    </span>
                                  </p>
                                )}
                              </div>
                            </div>

                            <span
                              className={`inline-flex items-center gap-1 rounded-full px-2.5 py-0.5 text-[10px] font-bold uppercase shrink-0 ${
                                isSupported
                                  ? 'bg-emerald-100 text-emerald-800'
                                  : isPartial
                                  ? 'bg-amber-100 text-amber-800'
                                  : 'bg-rose-100 text-rose-800'
                              }`}
                            >
                              {item.verdict.replace('_', ' ')}
                            </span>
                          </div>
                        </div>
                      )
                    })}
                  </div>
                ) : (
                  <div className="rounded-xl border border-dashed border-slate-300 p-8 text-center text-xs text-slate-500">
                    <ListChecks className="size-6 mx-auto text-slate-400 mb-2" />
                    <p className="font-semibold text-slate-700">No Fact-Check Audit Run Yet</p>
                    <p className="mt-1">
                      Click <strong>&quot;Run Fact-Check Audit&quot;</strong> above to extract atomic claims and verify them against the NGO vault.
                    </p>
                  </div>
                )}
              </div>
            </div>
          )}
        </div>
      )}

      {/* Empty State before generation */}
      {!proposalData && !isGenerating && (
        <div className="bg-slate-50 rounded-xl border border-dashed border-slate-300 p-12 text-center no-print">
          <div className="w-12 h-12 bg-indigo-50 text-indigo-600 rounded-xl flex items-center justify-center mx-auto mb-3">
            <Sparkles className="w-6 h-6" />
          </div>
          <h3 className="text-base font-semibold text-slate-900 mb-1">
            Ready to Draft Proposal
          </h3>
          <p className="text-xs text-slate-500 max-w-md mx-auto mb-5">
            Click <strong>&quot;⚡ Generate Proposal Draft&quot;</strong> above. Gemini will
            retrieve verified chunks from{' '}
            <strong>{activeNgo?.name || 'CRY'}</strong>&apos;s document vault and
            generate the complete 8-section proposal including the Activity Matrix
            and Itemized Budget.
          </p>
          <button
            onClick={() => handleGenerate(false)}
            className="inline-flex items-center gap-2 px-5 py-2.5 bg-indigo-600 hover:bg-indigo-700 text-white text-xs font-semibold rounded-lg shadow-xs transition-colors cursor-pointer"
          >
            <Sparkles className="w-4 h-4" />
            Generate Proposal for {activeNgo?.name || 'CRY'}
          </button>
        </div>
      )}
    </div>
  )
}
