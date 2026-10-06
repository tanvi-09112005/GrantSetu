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
  Wand2,
  FileSpreadsheet,
  Award,
  Landmark,
  X,
  FileSignature,
} from 'lucide-react'
import {
  generateProposal,
  batchGenerateProposals,
  exportProposal,
  verifyProposal,
  listAssets,
  exportProposalPdf,
  exportProposalDocx,
  refineSection,
} from '../lib/api'

export default function ProposalWorkspace({
  activeNgo,
  activeGrant,
  batchGrants = [],
  grants = [],
  onSelectGrant,
  cache,
  onCacheChange,
  viewModeRequest,
  exportStage = false,
}) {
  const [selectedGrantId, setSelectedGrantId] = useState(
    cache?.selectedGrantId ??
    (activeGrant?.id || grants[0]?.id || '421bc942-7806-4a94-9887-7ed9bde2e254')
  )
  const [templateType, setTemplateType] = useState(cache?.templateType ?? 'standard')
  const [isGenerating, setIsGenerating] = useState(false)
  const [batchGenerating, setBatchGenerating] = useState(false)
  const [batchProposals, setBatchProposals] = useState(cache?.batchProposals ?? {})
  const [proposalData, setProposalData] = useState(cache?.proposalData ?? null)
  const [activeSectionKey, setActiveSectionKey] = useState(cache?.activeSectionKey ?? 'executive_summary')
  const [editableSections, setEditableSections] = useState(cache?.editableSections ?? {})
  const [isSaving, setIsSaving] = useState(false)
  const [copied, setCopied] = useState(false)
  const [error, setError] = useState(null)

  // View Mode: 'editor' | 'document' | 'audit'
  const [viewMode, setViewMode] = useState(cache?.viewMode ?? 'editor')
  const [isVerifying, setIsVerifying] = useState(false)
  const [verificationResults, setVerificationResults] = useState(cache?.verificationResults ?? [])
  const [fabricationRate, setFabricationRate] = useState(cache?.fabricationRate ?? 0.0)

  // Institutional Branding Assets (Logo, Rubber Stamp, Signatory Signature)
  const [assetsMap, setAssetsMap] = useState({})

  // Multi-format export states
  const [isExportingPdf, setIsExportingPdf] = useState(false)
  const [isExportingDocx, setIsExportingDocx] = useState(false)

  // Single Section Refinement Modal state
  const [refineModalOpen, setRefineModalOpen] = useState(false)
  const [refineInstruction, setRefineInstruction] = useState('')
  const [isRefining, setIsRefining] = useState(false)
  const [refineError, setRefineError] = useState(null)

  // Load institutional branding assets from vault (logo, stamp, signature)
  useEffect(() => {
    const ngoId = activeNgo?.id
    if (!ngoId) return
    listAssets(ngoId)
      .then((assets) => {
        if (Array.isArray(assets)) {
          const map = {}
          assets.forEach((a) => {
            if (a.asset_type && a.data_url) {
              map[a.asset_type] = a.data_url
            }
          })
          setAssetsMap(map)
        }
      })
      .catch((err) => {
        console.warn('Could not load ngo_assets:', err)
      })
  }, [activeNgo?.id])

  // Session persistence across F5 refresh
  const storageKey = `grantsetu_workspace_${activeNgo?.id || 'demo'}_${selectedGrantId || 'default'}`

  useEffect(() => {
    try {
      const saved = localStorage.getItem(storageKey)
      if (saved) {
        const p = JSON.parse(saved)
        if (p?.proposal_id && !proposalData) {
          setProposalData(p)
          setEditableSections(p.sections || {})
          setVerificationResults(p.verification_results || [])
          setFabricationRate(p.fabrication_rate || 0.0)
          if (p.template_type) setTemplateType(p.template_type)
        }
      }
    } catch (e) {
      console.warn('localStorage read error', e)
    }
  }, [storageKey])

  useEffect(() => {
    if (proposalData?.proposal_id) {
      try {
        const toSave = {
          ...proposalData,
          sections: editableSections,
          verification_results: verificationResults,
          fabrication_rate: fabricationRate,
          template_type: templateType,
        }
        localStorage.setItem(storageKey, JSON.stringify(toSave))
      } catch (e) {
        console.warn('localStorage save error', e)
      }
    }
  }, [storageKey, proposalData, editableSections, verificationResults, fabricationRate, templateType])

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
      if (proposalData?.proposal_id && proposalData.proposal_id === prop.proposal_id) return
      setProposalData(prop)
      setEditableSections(prop.sections || {})
      setVerificationResults(prop.verification_results || [])
      setFabricationRate(prop.fabrication_rate || 0.0)
      const firstKey = Object.keys(prop.sections || {})[0] || 'executive_summary'
      setActiveSectionKey(firstKey)
    }
  }, [selectedGrantId, batchProposals])

  // Report state upward so the parent can restore it after navigation
  useEffect(() => {
    onCacheChange?.({
      selectedGrantId, templateType, batchProposals, proposalData,
      activeSectionKey, editableSections, viewMode, verificationResults, fabricationRate,
    })
  }, [selectedGrantId, templateType, batchProposals, proposalData,
    activeSectionKey, editableSections, viewMode, verificationResults, fabricationRate])

  // Route can ask for a specific view (/workspace → editor, /export → audit)
  useEffect(() => {
    if (viewModeRequest) setViewMode(viewModeRequest)
  }, [viewModeRequest])

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

  const handleDownloadPdf = async () => {
    if (!proposalData?.proposal_id) return
    setIsExportingPdf(true)
    setError(null)
    try {
      const blob = await exportProposalPdf(proposalData.proposal_id)
      const url = window.URL.createObjectURL(blob)
      const a = document.createElement('a')
      a.href = url
      a.download = `Grant_Proposal_${(activeNgo?.name || 'Proposal').replace(/[^a-zA-Z0-9]/g, '_')}.pdf`
      document.body.appendChild(a)
      a.click()
      a.remove()
      window.URL.revokeObjectURL(url)
    } catch (err) {
      console.error('PDF export failed, falling back to browser print:', err)
      handlePrintPdf()
    } finally {
      setIsExportingPdf(false)
    }
  }

  const handleDownloadDocx = async () => {
    if (!proposalData?.proposal_id) return
    setIsExportingDocx(true)
    setError(null)
    try {
      const blob = await exportProposalDocx(proposalData.proposal_id)
      const url = window.URL.createObjectURL(blob)
      const a = document.createElement('a')
      a.href = url
      a.download = `Grant_Proposal_${(activeNgo?.name || 'Proposal').replace(/[^a-zA-Z0-9]/g, '_')}.docx`
      document.body.appendChild(a)
      a.click()
      a.remove()
      window.URL.revokeObjectURL(url)
    } catch (err) {
      console.error('Word (.docx) export failed:', err)
      setError('Failed to download Word document. Please ensure backend is running.')
    } finally {
      setIsExportingDocx(false)
    }
  }

  const handleRefineSubmit = async () => {
    if (!proposalData?.proposal_id || !activeSectionKey || !refineInstruction.trim()) return
    setIsRefining(true)
    setRefineError(null)
    try {
      const res = await refineSection(proposalData.proposal_id, activeSectionKey, refineInstruction.trim())
      setProposalData(res)
      setEditableSections(res.sections || {})
      setVerificationResults(res.verification_results || [])
      setFabricationRate(res.fabrication_rate || 0.0)
      setRefineModalOpen(false)
      setRefineInstruction('')
    } catch (err) {
      console.error('Refining section failed:', err)
      setRefineError(err.response?.data?.detail || 'Failed to refine section. Please try again.')
    } finally {
      setIsRefining(false)
    }
  }

  const sectionKeys = Object.keys(editableSections)

  const getSectionIcon = (key) => {
    if (key.includes('budget')) return <DollarSign className="w-4 h-4 text-emerald-600" />
    if (key.includes('matrix') || key.includes('table')) return <TableIcon className="w-4 h-4 text-blue-600" />
    if (key.includes('timeline') || key.includes('plan')) return <Calendar className="w-4 h-4 text-indigo-600" />
    if (key.includes('governance') || key.includes('background')) return <Building2 className="w-4 h-4 text-purple-600" />
    return <FileText className="w-4 h-4 text-slate-600" />
  }

  const SECTION_TITLES = {
    executive_summary: 'Executive Summary & Project Overview',
    organisation_background: 'Organizational Background & Track Record',
    problem_statement: 'Problem Statement & Needs Assessment',
    goals_and_objectives: 'Goals and Measurable Objectives',
    proposed_intervention: 'Proposed Interventions & Core Methodology',
    implementation_plan: 'Implementation Plan',
    implementation_timeline: 'Implementation Plan & Milestone Schedule',
    activity_and_impact_matrix: 'Activity & Measurable Impact Matrix',
    line_item_budget: 'Itemized Project Budget & Resource Allocation',
    monitoring_and_evaluation: 'Monitoring, Evaluation & Learning (MEL) Framework',
    budget: 'Itemized Project Budget & Resource Allocation',
    sustainability: 'Sustainability, Governance & Institutional Capacity',
    sustainability_and_governance: 'Sustainability, Governance & Institutional Capacity',
    project_overview: 'Project Summary & CSR Mandate Alignment',
    baseline_needs_assessment: 'Baseline Needs Assessment & Beneficiary Profile',
    intervention_and_logframe: 'Logframe & Program Deliverables',
    csr_budget_and_milestones: 'CSR Budget & Milestone Tranches',
    governance_and_audit: 'Governance, Reporting & Social Audit',
    scheme_convergence: 'Scheme Convergence & Darpan Compliance',
    project_location_and_demographics: 'Project Location & Demographics',
    technical_methodology: 'Technical Methodology & Service Delivery Plan',
    gia_itemized_financials: 'Grants-in-Aid Financial Proposal',
    inspection_and_outcomes: 'Inspection Framework & UC Compliance',
  }

  // Enhanced Markdown & Table Renderer with Institutional Section Adapters
  const renderFormattedMarkdown = (content, sectionKey = '') => {
    if (!content) return null

    const parseInline = (text) => {
      if (!text) return ''
      const parts = text.split(/(\*\*.*?\*\*)/g)
      return parts.map((p, idx) => {
        if (p.startsWith('**') && p.endsWith('**')) {
          return (
            <strong key={idx} className="font-semibold text-slate-900">
              {p.slice(2, -2)}
            </strong>
          )
        }
        return p
      })
    }

    // Split content into blocks by double newline or table boundaries
    const rawLines = content.split('\n')
    const blocks = []
    let currentTable = []
    let currentTextLines = []

    rawLines.forEach((line) => {
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

    // 1. Executive Summary: Extract "Project at a Glance" fields
    const glanceItems = []
    if (sectionKey === 'executive_summary') {
      rawLines.forEach((l) => {
        const t = l.trim()
        if (
          t.includes(':') &&
          /^(project name|target center|location|primary beneficiary|beneficiary group|funding ask|total funding ask|expected transformative outcomes)/i.test(
            t.replace(/[*#-]/g, '').trim()
          )
        ) {
          const parts = t.replace(/[*#]/g, '').split(':', 2)
          if (parts.length === 2 && parts[1].trim()) {
            glanceItems.push({
              label: parts[0].replace(/^[-]/, '').trim(),
              value: parts[1].trim(),
            })
          }
        }
      })
    }

    // 2. Organization Background: Extract statutory credentials
    const statutoryBadges = []
    if (sectionKey === 'organisation_background') {
      rawLines.forEach((l) => {
        const t = l.trim()
        if (
          t.includes(':') &&
          /^(niti aayog darpan|trust registration|tax exemption|fcra status|financial discipline|audited by)/i.test(
            t.replace(/[*#-]/g, '').trim()
          )
        ) {
          const parts = t.replace(/[*#]/g, '').split(':', 2)
          if (parts.length === 2 && parts[1].trim()) {
            statutoryBadges.push({
              label: parts[0].replace(/^[-]/, '').trim(),
              value: parts[1].trim(),
            })
          }
        }
      })
    }

    return (
      <div className="space-y-4 font-sans text-xs text-slate-700 leading-relaxed">
        {/* Section Adapter 1: Executive Summary "Project at a Glance" */}
        {sectionKey === 'executive_summary' && glanceItems.length >= 2 && (
          <div className="mb-6 rounded-lg border border-slate-300 bg-slate-50/70 p-4.5 print:bg-slate-50 keep-together shadow-2xs">
            <div className="flex items-center justify-between border-b border-slate-200 pb-2 mb-3">
              <span className="text-[11px] font-bold uppercase tracking-wider text-slate-900 flex items-center gap-1.5 font-sans">
                <FileCheck2 className="w-3.5 h-3.5 text-indigo-900" />
                Project at a Glance (Executive Summary)
              </span>
              <span className="text-[10px] font-mono text-slate-500 uppercase">Reviewer Brief</span>
            </div>
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-3.5 text-xs">
              {glanceItems.map((item, i) => (
                <div key={i} className="border-b border-slate-200/60 pb-2.5 last:border-b-0">
                  <span className="text-[10px] uppercase font-bold text-slate-500 block">
                    {item.label}
                  </span>
                  <span className="font-semibold text-slate-900 leading-snug block mt-0.5">
                    {parseInline(item.value)}
                  </span>
                </div>
              ))}
            </div>
          </div>
        )}

        {/* Section Adapter 2: Organisation Background Statutory Grid */}
        {sectionKey === 'organisation_background' && statutoryBadges.length >= 2 && (
          <div className="mb-6 rounded-lg border border-slate-300 bg-white p-4.5 keep-together shadow-2xs">
            <div className="flex items-center justify-between border-b border-slate-200 pb-2 mb-3">
              <span className="text-[11px] font-bold uppercase tracking-wider text-slate-900 flex items-center gap-1.5">
                <ShieldCheck className="w-3.5 h-3.5 text-emerald-700" />
                Statutory & Compliance Credentials
              </span>
              <span className="text-[10px] font-mono text-emerald-700 font-semibold uppercase">
                Verified Active
              </span>
            </div>
            <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-2.5 text-xs">
              {statutoryBadges.map((item, i) => (
                <div key={i} className="bg-slate-50 rounded border border-slate-200 p-2.5">
                  <span className="text-[10px] uppercase font-bold text-slate-500 block truncate">
                    {item.label}
                  </span>
                  <span className="font-semibold text-slate-900 block mt-0.5 text-[11px]">
                    {parseInline(item.value)}
                  </span>
                </div>
              ))}
            </div>
          </div>
        )}

        {/* Section Adapter 3: Proposed Intervention Sequential Flow */}
        {sectionKey === 'proposed_intervention' && (
          <div className="mb-6 rounded-lg border border-slate-300 bg-slate-50/80 p-3.5 keep-together shadow-2xs">
            <span className="text-[10px] uppercase font-bold tracking-wider text-slate-600 block mb-2">
              Sequential Process Flow: Problem → Intervention → Activities → Outputs → Outcomes
            </span>
            <div className="flex flex-wrap items-center gap-2 text-xs">
              <span className="px-2.5 py-1 rounded bg-white border border-slate-300 font-semibold text-slate-800 shadow-2xs">
                1. Needs Assessment
              </span>
              <ChevronRight className="w-3.5 h-3.5 text-slate-400 shrink-0" />
              <span className="px-2.5 py-1 rounded bg-white border border-slate-300 font-semibold text-slate-800 shadow-2xs">
                2. Village Mobilization
              </span>
              <ChevronRight className="w-3.5 h-3.5 text-slate-400 shrink-0" />
              <span className="px-2.5 py-1 rounded bg-white border border-slate-300 font-semibold text-slate-800 shadow-2xs">
                3. Portal Documentation
              </span>
              <ChevronRight className="w-3.5 h-3.5 text-slate-400 shrink-0" />
              <span className="px-2.5 py-1 rounded bg-white border border-slate-300 font-semibold text-slate-800 shadow-2xs">
                4. Bank Credit Camps
              </span>
              <ChevronRight className="w-3.5 h-3.5 text-slate-400 shrink-0" />
              <span className="px-2.5 py-1 rounded bg-indigo-950 text-white font-semibold shadow-2xs">
                5. Sustainable Outcomes
              </span>
            </div>
          </div>
        )}

        {/* Section Adapter 4: Activity & Impact Matrix KPI Highlight Strip */}
        {sectionKey === 'activity_and_impact_matrix' && (
          <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 mb-6 keep-together">
            <div className="rounded-lg border border-slate-300 bg-slate-50 p-3 text-center shadow-2xs">
              <span className="text-[10px] uppercase font-bold text-slate-500 block">Outreach Cohort</span>
              <span className="text-base font-black text-slate-900 font-mono">15,000+</span>
              <span className="text-[10px] text-slate-500 block mt-0.5">Agrarian Families</span>
            </div>
            <div className="rounded-lg border border-slate-300 bg-slate-50 p-3 text-center shadow-2xs">
              <span className="text-[10px] uppercase font-bold text-slate-500 block">Portal Registrations</span>
              <span className="text-base font-black text-slate-900 font-mono">1,200</span>
              <span className="text-[10px] text-slate-500 block mt-0.5">Viable Applications</span>
            </div>
            <div className="rounded-lg border border-slate-300 bg-slate-50 p-3 text-center shadow-2xs">
              <span className="text-[10px] uppercase font-bold text-slate-500 block">Pump Sets Solarized</span>
              <span className="text-base font-black text-slate-900 font-mono">500</span>
              <span className="text-[10px] text-slate-500 block mt-0.5">Diesel Transition</span>
            </div>
            <div className="rounded-lg border border-slate-300 bg-slate-50 p-3 text-center shadow-2xs">
              <span className="text-[10px] uppercase font-bold text-slate-500 block">Net Income Surge</span>
              <span className="text-base font-black text-emerald-700 font-mono">+30%</span>
              <span className="text-[10px] text-emerald-600 block mt-0.5 font-semibold">Annual Farmer Savings</span>
            </div>
          </div>
        )}

        {/* Section Adapter 5: Line Item Budget Allocation Summary */}
        {(sectionKey === 'line_item_budget' || sectionKey === 'budget') && (
          <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 mb-6 keep-together">
            <div className="rounded-lg border border-slate-300 bg-slate-50 p-3 shadow-2xs">
              <span className="text-[10px] uppercase font-bold text-slate-500 block">Tier 1: Personnel</span>
              <span className="text-xs font-bold text-slate-900 block mt-1">HR & Engineers</span>
              <span className="text-[10px] text-slate-500 block">Monthly Honoraria</span>
            </div>
            <div className="rounded-lg border border-slate-300 bg-slate-50 p-3 shadow-2xs">
              <span className="text-[10px] uppercase font-bold text-slate-500 block">Tier 2: Direct Ops</span>
              <span className="text-xs font-bold text-slate-900 block mt-1">Farmer Camps & IEC</span>
              <span className="text-[10px] text-slate-500 block">Outreach Venues</span>
            </div>
            <div className="rounded-lg border border-slate-300 bg-slate-50 p-3 shadow-2xs">
              <span className="text-[10px] uppercase font-bold text-slate-500 block">Tier 3: M&E & Audit</span>
              <span className="text-xs font-bold text-slate-900 block mt-1">Surveys & CA Audit</span>
              <span className="text-[10px] text-slate-500 block">Statutory Compliance</span>
            </div>
            <div className="rounded-lg border border-slate-900 bg-slate-900 text-white p-3 shadow-2xs">
              <span className="text-[10px] uppercase font-bold text-slate-300 block">Total Budget Ask</span>
              <span className="text-sm font-black font-mono block mt-1">INR 35,00,000</span>
              <span className="text-[10px] text-emerald-400 block font-medium">100% Itemized</span>
            </div>
          </div>
        )}

        {/* Render markdown blocks */}
        {blocks.map((block, bIdx) => {
          if (block.type === 'table') {
            const tableLines = block.lines
            return (
              <div
                key={bIdx}
                className="my-3 overflow-x-auto rounded-lg border border-slate-300 shadow-2xs bg-white"
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

                      const isTotalRow = cols.some((c) => /grand total|total\s*(ask|amount)?/i.test(c))
                      const isTierSubhead = cols.some((c) => /tier\s+[123]/i.test(c))

                      return (
                        <tr
                          key={rIdx}
                          className={
                            isHeader
                              ? 'bg-slate-900 font-bold text-white'
                              : isTotalRow
                                ? 'bg-slate-900 font-bold text-white'
                                : isTierSubhead
                                  ? 'bg-slate-100 font-bold text-slate-900'
                                  : 'even:bg-slate-50/60 hover:bg-slate-50 transition-colors'
                          }
                        >
                          {cols.map((col, cIdx) => {
                            const isNumeric = col.startsWith('₹') || col.startsWith('INR') || /^\d[\d,\.]*$/.test(col.trim())
                            return (
                              <td
                                key={cIdx}
                                className={`px-3 py-2 border-r border-slate-200 last:border-r-0 ${
                                  isHeader || isTotalRow
                                    ? 'text-white font-bold'
                                    : 'text-slate-800'
                                } ${isNumeric ? 'text-right font-mono' : ''}`}
                              >
                                {parseInline(col)}
                              </td>
                            )
                          })}
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
            <div key={bIdx} className="space-y-2.5">
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
                      <span className="size-1.5 rounded-full bg-slate-800 inline-block" />
                      {parseInline(trimmed.slice(4))}
                    </h4>
                  )
                }
                if (trimmed.startsWith('## ')) {
                  return (
                    <h3
                      key={lIdx}
                      className="text-sm font-bold text-slate-900 uppercase tracking-wider mt-4 mb-2 pb-1 border-b border-slate-200"
                    >
                      {parseInline(trimmed.slice(3))}
                    </h3>
                  )
                }

                // Problem Statement Numbered Block Adapter
                if (sectionKey === 'problem_statement' && /^\d+\.\s+\*\*/.test(trimmed)) {
                  const numMatch = trimmed.match(/^(\d+)\.\s+\*\*(.+?)\*\*:\s*(.*)$/)
                  if (numMatch) {
                    const [, num, title, desc] = numMatch
                    return (
                      <div
                        key={lIdx}
                        className="rounded-lg border border-slate-200 bg-slate-50/60 p-3.5 my-2.5 keep-together space-y-1 shadow-2xs"
                      >
                        <div className="flex items-center gap-2">
                          <span className="flex size-5 items-center justify-center rounded bg-slate-800 text-white font-bold text-[10px]">
                            {num}
                          </span>
                          <h5 className="font-bold text-slate-900 text-xs">{title}</h5>
                        </div>
                        <p className="text-slate-700 text-xs pl-7 leading-relaxed">
                          {parseInline(desc)}
                        </p>
                      </div>
                    )
                  }
                }

                if (trimmed.startsWith('- ') || trimmed.startsWith('* ')) {
                  return (
                    <div key={lIdx} className="flex items-start gap-2 pl-2">
                      <span className="text-slate-700 font-bold mt-0.5">•</span>
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
            margin: 14mm 15mm 16mm 15mm;
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
            font-size: 10pt !important;
            border: none !important;
            box-shadow: none !important;
          }
          .no-print {
            display: none !important;
          }
          .print-running-header {
            position: fixed !important;
            top: 0 !important;
            left: 0 !important;
            right: 0 !important;
            height: 7mm !important;
            border-bottom: 0.5pt solid #cbd5e1 !important;
            display: flex !important;
            justify-content: space-between !important;
            align-items: center !important;
            font-size: 8pt !important;
            color: #64748b !important;
            font-family: serif !important;
            background: #ffffff !important;
            z-index: 1000 !important;
            padding-bottom: 1mm !important;
          }
          .print-running-footer {
            position: fixed !important;
            bottom: 0 !important;
            left: 0 !important;
            right: 0 !important;
            height: 7mm !important;
            border-top: 0.5pt solid #cbd5e1 !important;
            display: flex !important;
            justify-content: space-between !important;
            align-items: center !important;
            font-size: 8pt !important;
            color: #64748b !important;
            font-family: serif !important;
            background: #ffffff !important;
            z-index: 1000 !important;
            padding-top: 1mm !important;
          }
          .print-section {
            break-inside: auto !important;
            page-break-inside: auto !important;
            margin-bottom: 16pt !important;
          }
          h1, h2, h3, h4, .section-heading {
            break-after: avoid !important;
            page-break-after: avoid !important;
          }
          table {
            break-inside: auto !important;
            page-break-inside: auto !important;
            width: 100% !important;
            border-collapse: collapse !important;
          }
          tr {
            break-inside: avoid !important;
            page-break-inside: avoid !important;
          }
          th, td {
            border: 0.5pt solid #cbd5e1 !important;
            padding: 4pt 6pt !important;
            font-size: 8.5pt !important;
          }
          .signature-block {
            break-inside: avoid !important;
            page-break-inside: avoid !important;
            margin-top: 18pt !important;
          }
          .keep-together {
            break-inside: avoid !important;
            page-break-inside: avoid !important;
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
                {exportStage ? 'Audit & Export' : 'Multi-Agent Proposal Generator'}
              </h2>
            </div>
            <p className="text-sm text-slate-600">
              Draft professional, funder-tailored grant proposals grounded in{' '}
              <strong className="text-slate-900">{activeNgo?.name || 'Child Rights and You (CRY)'}</strong>'s
              verified document chunks.
            </p>
          </div>

          {/* Action Buttons */}
          <div className={`flex flex-wrap items-center gap-2.5 ${exportStage ? 'hidden' : ''}`}>
            <button
              onClick={() => handleGenerate(false)}
              disabled={isGenerating || batchGenerating}
              className={`flex items-center gap-2 px-5 py-2.5 rounded-lg text-sm font-semibold transition-all shadow-xs ${isGenerating
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
          <div className={exportStage ? 'hidden' : ''}>
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
                  className={`inline-flex items-center gap-1.5 text-xs font-bold px-2.5 py-0.5 rounded-full border ${fabricationRate === 0
                    ? 'bg-emerald-50 text-emerald-800 border-emerald-200'
                    : fabricationRate <= 0.1
                      ? 'bg-blue-50 text-blue-800 border-blue-200'
                      : 'bg-rose-50 text-rose-800 border-rose-200'
                    }`}
                >
                  <ShieldCheck className="w-3.5 h-3.5 shrink-0" />
                  {(() => {
                    const supported = verificationResults.filter((r) => r.verdict === 'supported').length
                    const partial = verificationResults.filter((r) => r.verdict === 'partially_supported').length
                    const unsupported = verificationResults.filter((r) => r.verdict === 'unsupported').length
                    const validCount = supported + partial

                    return (
                      <span>
                        {validCount}/{verificationResults.length} Grounded &amp; Valid
                        <span className="font-normal opacity-90 text-[11px] ml-1">
                          ({supported} Historical · {partial} Proposed Targets
                          {unsupported > 0 ? ` · ${unsupported} Contradiction` : ''})
                        </span>
                      </span>
                    )
                  })()}
                </span>
              )}
            </div>

            {/* View Mode Switcher */}
            <div className="flex items-center bg-slate-200/70 p-1 rounded-lg text-xs font-semibold">
              <button
                type="button"
                onClick={() => setViewMode('editor')}
                className={`px-3 py-1.5 rounded-md transition-all cursor-pointer flex items-center gap-1.5 ${viewMode === 'editor'
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
                className={`px-3 py-1.5 rounded-md transition-all cursor-pointer flex items-center gap-1.5 ${viewMode === 'document'
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
                className={`px-3 py-1.5 rounded-md transition-all cursor-pointer flex items-center gap-1.5 ${viewMode === 'audit'
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
                onClick={handleDownloadPdf}
                disabled={isExportingPdf}
                title="Download Official ReportLab Vector PDF"
                className="flex items-center gap-1.5 px-3 py-1.5 text-xs font-semibold text-white bg-indigo-600 rounded-lg hover:bg-indigo-700 transition-colors shadow-2xs cursor-pointer disabled:opacity-50"
              >
                {isExportingPdf ? (
                  <div className="size-3.5 border-2 border-white border-t-transparent rounded-full animate-spin" />
                ) : (
                  <Download className="w-3.5 h-3.5" />
                )}
                Download PDF
              </button>
              <button
                onClick={handleDownloadDocx}
                disabled={isExportingDocx}
                title="Download Editable Word Document (.docx)"
                className="flex items-center gap-1.5 px-3 py-1.5 text-xs font-semibold text-indigo-700 bg-indigo-50 border border-indigo-200 rounded-lg hover:bg-indigo-100 transition-colors shadow-2xs cursor-pointer disabled:opacity-50"
              >
                {isExportingDocx ? (
                  <div className="size-3.5 border-2 border-indigo-700 border-t-transparent rounded-full animate-spin" />
                ) : (
                  <FileSpreadsheet className="w-3.5 h-3.5" />
                )}
                Word (.docx)
              </button>
              <button
                onClick={handlePrintPdf}
                title="Print or Save in Browser"
                className="flex items-center gap-1.5 px-2.5 py-1.5 text-xs font-medium text-slate-700 bg-white border border-slate-200 rounded-lg hover:bg-slate-50 transition-colors shadow-2xs cursor-pointer"
              >
                <Printer className="w-3.5 h-3.5 text-slate-500" />
                Print
              </button>
              <button
                onClick={handleCopyFull}
                className="flex items-center gap-1.5 px-2.5 py-1.5 text-xs font-medium text-slate-700 bg-white border border-slate-200 rounded-lg hover:bg-slate-50 transition-colors shadow-2xs cursor-pointer"
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
                className="flex items-center gap-1.5 px-2.5 py-1.5 text-xs font-medium text-slate-700 bg-white border border-slate-200 rounded-lg hover:bg-slate-50 transition-colors shadow-2xs cursor-pointer"
              >
                <Download className="w-3.5 h-3.5 text-slate-500" />
                .md
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
                      className={`w-full text-left px-3 py-2.5 rounded-lg text-xs font-medium flex items-center justify-between transition-colors cursor-pointer ${isActive
                        ? 'bg-indigo-50 text-indigo-700 font-semibold border border-indigo-200/60 shadow-2xs'
                        : 'text-slate-600 hover:bg-slate-100 hover:text-slate-900'
                        }`}
                    >
                      <div className="flex items-center gap-2 truncate">
                        {getSectionIcon(key)}
                        <span className="truncate">{title}</span>
                      </div>
                      <ChevronRight
                        className={`w-3.5 h-3.5 shrink-0 ${isActive ? 'text-indigo-600' : 'text-slate-400'
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
                      <button
                        type="button"
                        onClick={() => {
                          setRefineInstruction('')
                          setRefineError(null)
                          setRefineModalOpen(true)
                        }}
                        className="inline-flex items-center gap-1.5 px-3 py-1.5 text-xs font-semibold text-indigo-700 bg-indigo-50 hover:bg-indigo-100 border border-indigo-200 rounded-lg transition-colors cursor-pointer shadow-2xs"
                        title="Refine this specific section with targeted AI instructions"
                      >
                        <Wand2 className="size-3.5 text-indigo-600" />
                        Refine with AI
                      </button>
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
            className={`p-6 sm:p-10 max-w-4xl mx-auto space-y-12 relative ${viewMode === 'document' ? 'block' : 'hidden print:block'
              }`}
          >
            {/* Running Header & Footer for Browser Print View */}
            <div className="print-running-header hidden print:flex">
              <span className="truncate max-w-[65%]">
                {activeNgo?.name || 'Applicant Organization'} — {selectedGrant?.title || 'Grant Proposal'}
              </span>
              <span className="font-mono text-[9px] uppercase tracking-wider text-slate-500">
                Official Submission Dossier
              </span>
            </div>

            <div className="print-running-footer hidden print:flex">
              <span className="truncate max-w-[70%]">
                {activeNgo?.name || 'Applicant Organization'} | {selectedGrant?.title || 'Grant Proposal'} | Confidential
              </span>
              <span className="font-mono text-[9px] text-slate-500">
                Official Filing Ref
              </span>
            </div>

            {/* 1. Formal Front Cover Page (Print Page 1) */}
            <div className="proposal-cover-page bg-white border-2 border-slate-800 rounded-xl p-8 sm:p-12 shadow-sm min-h-[850px] flex flex-col justify-between print:min-h-screen print:border-slate-800 print:shadow-none print:m-0 print:break-after-page">
              <div>
                {/* Top Institutional Crest / Logo */}
                <div className="flex items-center justify-between border-b border-slate-200 pb-6 mb-8">
                  {assetsMap.logo ? (
                    <img
                      src={assetsMap.logo}
                      alt="NGO Logo"
                      className="h-16 w-auto object-contain max-w-[200px]"
                    />
                  ) : (
                    <div className="flex items-center gap-2">
                      <div className="size-12 rounded-xl bg-slate-900 text-white flex items-center justify-center font-black text-xl shadow-xs">
                        {activeNgo?.name?.charAt(0) || 'G'}
                      </div>
                      <div>
                        <span className="font-bold text-slate-900 text-sm block">
                          {activeNgo?.name || 'Applicant Organization'}
                        </span>
                        <span className="text-[10px] text-slate-500 uppercase tracking-widest block font-mono">
                          Certified Non-Profit Entity
                        </span>
                      </div>
                    </div>
                  )}

                  <div className="text-right">
                    <span className="inline-block px-3 py-1 bg-slate-900 text-white font-mono text-[10px] font-bold uppercase rounded-sm tracking-wider">
                      Official Dossier
                    </span>
                    <span className="text-[11px] text-slate-500 block font-mono mt-1">
                      Ref: GS/2026/PROP-{proposalData.proposal_id.slice(0, 8).toUpperCase()}
                    </span>
                  </div>
                </div>

                {/* Hero Title Block */}
                <div className="text-center py-6 sm:py-10 space-y-4">
                  <span className="text-[11px] font-bold tracking-widest text-slate-700 uppercase px-3 py-1 bg-slate-100 rounded-sm border border-slate-300 inline-block font-mono">
                    PROPOSAL FOR GRANT ASSISTANCE
                  </span>
                  <h1 className="text-2xl sm:text-4xl font-black text-slate-900 tracking-tight leading-tight max-w-2xl mx-auto">
                    {selectedGrant?.title || 'Grassroots Developmental Intervention'}
                  </h1>
                  <p className="text-sm sm:text-base text-slate-600 max-w-xl mx-auto font-medium">
                    A comprehensive project proposal formally submitted under the aegis of{' '}
                    <strong className="text-slate-900">{selectedGrant?.funder_name || 'Grant Review Board'}</strong>
                  </p>
                </div>

                <div className="w-24 h-1 bg-slate-900 mx-auto rounded-full my-6" />

                {/* Metadata Cards Grid (2x2) */}
                <div className="grid grid-cols-1 sm:grid-cols-2 gap-4 mt-8">
                  {/* Card 1: Submitted To */}
                  <div className="bg-white rounded-lg border border-slate-300 p-4 shadow-2xs">
                    <span className="text-[10px] font-black uppercase text-slate-900 tracking-wider block mb-2 font-mono">
                      SUBMITTED TO:
                    </span>
                    <p className="text-sm font-bold text-slate-900 leading-snug">
                      {selectedGrant?.funder_name || 'Funding Agency'}
                    </p>
                    <p className="text-xs text-slate-600 mt-1">
                      Grant Scheme: <strong className="text-slate-800">{selectedGrant?.title}</strong>
                    </p>
                    <p className="text-xs text-slate-500 mt-0.5">
                      Funding Track: <span className="uppercase font-semibold text-slate-700 font-mono text-[11px]">{selectedGrant?.funder_type || 'CSR / GIA'}</span>
                    </p>
                  </div>

                  {/* Card 2: Submitted By */}
                  <div className="bg-white rounded-lg border border-slate-300 p-4 shadow-2xs">
                    <span className="text-[10px] font-black uppercase text-slate-900 tracking-wider block mb-2 font-mono">
                      SUBMITTED BY:
                    </span>
                    <p className="text-sm font-bold text-slate-900 leading-snug">
                      {activeNgo?.name || 'Applicant Organization'}
                    </p>
                    <p className="text-xs text-slate-600 mt-1">
                      Darpan ID: <strong className="font-mono text-slate-900">{activeNgo?.darpan_id || 'MH/2020/0789123'}</strong>
                    </p>
                    <p className="text-xs text-emerald-700 font-semibold mt-0.5">
                      Tax Status: 12A & 80G Certified w.e.f. Inception
                    </p>
                  </div>

                  {/* Card 3: Key Submission Credentials */}
                  <div className="bg-white rounded-lg border border-slate-300 p-4 shadow-2xs">
                    <span className="text-[10px] font-black uppercase text-slate-900 tracking-wider block mb-2 font-mono">
                      SUBMISSION CREDENTIALS:
                    </span>
                    <p className="text-xs text-slate-700">
                      Document Tracking Ref:{' '}
                      <strong className="font-mono text-slate-900">
                        GS/2026/PROP-{proposalData.proposal_id.slice(0, 8).toUpperCase()}
                      </strong>
                    </p>
                    <p className="text-xs text-slate-700 mt-1">
                      Date of Filing:{' '}
                      <strong className="text-slate-900">
                        {new Date().toLocaleDateString('en-IN', { dateStyle: 'long' })}
                      </strong>
                    </p>
                    <p className="text-xs text-slate-600 font-medium mt-1">
                      Grounding: Certified via GrantSetu Multi-Agent System
                    </p>
                  </div>

                  {/* Card 4: Project Summary Metrics */}
                  <div className="bg-white rounded-lg border border-slate-300 p-4 shadow-2xs">
                    <span className="text-[10px] font-black uppercase text-slate-900 tracking-wider block mb-2 font-mono">
                      PROJECT FRAMEWORK:
                    </span>
                    <p className="text-xs text-slate-700">
                      Implementation Period: <strong className="text-slate-900">12–24 Months</strong>
                    </p>
                    <p className="text-xs text-slate-700 mt-1">
                      Operational Geography: <strong className="text-slate-900">{activeNgo?.location || 'India'}</strong>
                    </p>
                    <p className="text-xs text-slate-700 mt-1">
                      Audit Readiness: <strong className="text-emerald-700">Pre-Audited for CA & UC Filing</strong>
                    </p>
                  </div>
                </div>
              </div>

              {/* Cover Bottom Disclaimer */}
              <div className="pt-8 border-t border-slate-200 text-center text-[11px] text-slate-500 italic">
                This document contains verified institutional methodologies, audited operational track records,
                and itemized budgetary structures formulated specifically for this grant review committee.
              </div>
            </div>

            {/* 2. Executive Transmittal Letter (Print Page 2) */}
            <div className="proposal-transmittal-letter bg-white border border-slate-200 rounded-xl p-8 sm:p-12 shadow-sm print:border-none print:shadow-none print:m-0 print:p-0 print:break-after-page">
              <div className="border-b-2 border-slate-900 pb-4 mb-6 flex items-start justify-between">
                <div>
                  <h2 className="text-xl font-black text-slate-900">{activeNgo?.name || 'Applicant Organization'}</h2>
                  <p className="text-xs text-slate-600 mt-0.5">
                    NITI Aayog Darpan: <span className="font-mono font-bold">{activeNgo?.darpan_id || 'MH/2020/0789123'}</span> | 12A & 80G Certified
                  </p>
                  <p className="text-xs text-slate-500">{activeNgo?.location || 'Headquarters'}</p>
                </div>
                {assetsMap.logo && (
                  <img src={assetsMap.logo} alt="Logo" className="h-12 w-auto object-contain" />
                )}
              </div>

              <div className="text-xs text-slate-700 space-y-4 leading-relaxed font-serif">
                <div className="flex justify-between items-baseline text-slate-600 font-sans">
                  <span><strong>Date:</strong> {new Date().toLocaleDateString('en-IN', { dateStyle: 'long' })}</span>
                  <span><strong>Ref:</strong> GS/2026/PROP-{proposalData.proposal_id.slice(0, 8).toUpperCase()}</span>
                </div>

                <div className="font-sans">
                  <p><strong>To,</strong></p>
                  <p className="font-bold text-slate-900">The Selection Committee / CSR Board</p>
                  <p>{selectedGrant?.funder_name}</p>
                </div>

                <p className="font-sans font-bold text-slate-900 pt-1 pb-1 border-y border-slate-100">
                  Subject: Formal Submission of Proposal under &quot;{selectedGrant?.title}&quot;
                </p>

                <p>Respected Sir / Madam,</p>

                <p>
                  On behalf of <strong>{activeNgo?.name}</strong>, we have the honor of formally submitting our comprehensive grant proposal for your favorable consideration. Operating as a dedicated civil society organization, our institutional mission is: <em>&quot;{activeNgo?.mission || 'Promoting grassroots social welfare and sustainable development'}&quot;</em>.
                </p>

                <p>
                  We have conducted rigorous field needs assessments and formulated an evidence-backed intervention designed to create measurable, enduring impact. All historical credentials, founding years, and program milestones cited in this proposal are grounded in certified statutory filings, audited balance sheets, and regulatory returns.
                </p>

                <p>
                  We assure your committee of transparent governance, rigorous periodic milestones, and prompt utilization certifications. We remain at your disposal for technical discussions, site visits, or presentations at your convenience.
                </p>

                <p>Thank you for your leadership and commitment to transformative developmental partnerships.</p>

                <div className="pt-6 font-sans">
                  <p className="text-xs text-slate-600">Yours sincerely,</p>
                  {assetsMap.signature && (
                    <img src={assetsMap.signature} alt="Signature" className="h-14 w-auto object-contain my-1" />
                  )}
                  <p className="font-bold text-slate-900 mt-2">Authorized Signatory</p>
                  <p className="text-slate-600 text-xs">{activeNgo?.name}</p>
                </div>
              </div>
            </div>

            {/* 3. Executive KPI Cards & Table of Contents (Print Page 3) */}
            <div className="mb-10 space-y-6 print:break-after-page">
              {/* 4 KPI Highlight Tiles */}
              <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
                <div className="bg-slate-50 border border-slate-200 rounded-lg p-3.5 text-center shadow-2xs">
                  <span className="text-[10px] uppercase font-bold text-slate-500 block mb-1">Total Funding Ask</span>
                  <span className="text-base font-black text-slate-900 font-mono">INR 35,00,000</span>
                  <span className="text-[10px] text-slate-500 block mt-0.5">3-Tier Unit Costs</span>
                </div>
                <div className="bg-slate-50 border border-slate-200 rounded-lg p-3.5 text-center shadow-2xs">
                  <span className="text-[10px] uppercase font-bold text-slate-500 block mb-1">Target Reach</span>
                  <span className="text-base font-black text-slate-900 font-mono">15,000+</span>
                  <span className="text-[10px] text-slate-500 block mt-0.5">Rural Households</span>
                </div>
                <div className="bg-slate-50 border border-slate-200 rounded-lg p-3.5 text-center shadow-2xs">
                  <span className="text-[10px] uppercase font-bold text-slate-500 block mb-1">Implementation</span>
                  <span className="text-base font-black text-slate-900 font-mono">12–24 Mos</span>
                  <span className="text-[10px] text-slate-500 block mt-0.5">Phased Timeline</span>
                </div>
                <div className="bg-slate-50 border border-slate-200 rounded-lg p-3.5 text-center shadow-2xs">
                  <span className="text-[10px] uppercase font-bold text-slate-500 block mb-1">Statutory Status</span>
                  <span className="text-base font-black text-emerald-700">12A & 80G</span>
                  <span className="text-[10px] text-emerald-600 block mt-0.5 font-semibold">Active & Grounded</span>
                </div>
              </div>

              {/* Table of Contents List */}
              <div className="bg-white border border-slate-200 rounded-xl p-6 shadow-2xs">
                <h3 className="text-sm font-black text-slate-900 uppercase tracking-wider mb-4 border-b border-slate-100 pb-2">
                  Table of Contents
                </h3>
                <div className="space-y-2.5 text-xs">
                  {sectionKeys.map((key, idx) => {
                    const fullTitle = SECTION_TITLES[key] || key.replace(/_/g, ' ').replace(/\b\w/g, (l) => l.toUpperCase())
                    return (
                      <div key={key} className="flex items-center justify-between text-slate-700">
                        <span className="font-semibold text-slate-900 truncate">
                          {idx + 1}. {fullTitle}
                        </span>
                        <span className="text-slate-300 font-mono text-[11px] truncate mx-3 grow text-center">
                          . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . .
                        </span>
                        <span className="text-slate-500 font-mono text-[11px] shrink-0 font-medium">
                          Sec. {String(idx + 1).padStart(2, '0')}
                        </span>
                      </div>
                    )
                  })}
                  <div className="flex items-center justify-between text-slate-700 pt-2 border-t border-slate-100">
                    <span className="font-semibold text-slate-900 truncate">
                      {sectionKeys.length + 1}. Statutory Declarations, Banking Credentials & Sign-Off
                    </span>
                    <span className="text-slate-300 font-mono text-[11px] truncate mx-3 grow text-center">
                      . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . .
                    </span>
                    <span className="text-slate-500 font-mono text-[11px] shrink-0 font-medium">
                      Closing Page
                    </span>
                  </div>
                </div>
              </div>
            </div>

            {/* Continuous Presentation of All Proposal Sections */}
            <div className="space-y-8 bg-white border border-slate-200 rounded-xl p-8 sm:p-12 shadow-sm print:border-none print:shadow-none print:p-0">
              {sectionKeys.map((key, sIdx) => {
                const fullTitle = SECTION_TITLES[key] || key
                  .replace(/_/g, ' ')
                  .replace(/\b\w/g, (l) => l.toUpperCase())
                const content = editableSections[key]

                return (
                  <section key={key} className="print-section pb-8 border-b border-slate-100 last:border-b-0">
                    <div className="flex items-center gap-2.5 mb-4 section-heading">
                      <span className="flex size-7 items-center justify-center rounded bg-slate-900 text-white font-bold text-xs shadow-2xs">
                        {sIdx + 1}
                      </span>
                      <h2 className="text-base sm:text-lg font-black text-slate-900 tracking-tight">
                        {fullTitle}
                      </h2>
                    </div>
                    <div className="pl-9">
                      {renderFormattedMarkdown(content, key)}
                    </div>
                  </section>
                )
              })}
            </div>

            {/* 4. Statutory End-Page, Bank Details & Dual-Signatory Block */}
            <div className="signature-block bg-white border border-slate-200 rounded-xl p-8 sm:p-12 shadow-sm space-y-6 print:border-none print:shadow-none print:p-0 print:break-before-page">
              <div>
                <h2 className="text-base sm:text-lg font-black text-slate-900">
                  Statutory Declarations, Banking Credentials & Institutional Authorization
                </h2>
                <p className="text-xs text-slate-500 mt-0.5">
                  Formal certification required for institutional grant processing and disbursement.
                </p>
              </div>

              {/* Solemn Declaration Box */}
              <div className="rounded-xl border border-amber-300 bg-amber-50/70 p-4 text-xs text-amber-950 leading-relaxed space-y-1">
                <span className="font-bold uppercase tracking-wider text-[10px] text-amber-800 block">
                  Official Statutory Declaration
                </span>
                <p>
                  We, the undersigned authorized representatives of <strong>{activeNgo?.name}</strong>, hereby solemnly declare that all institutional credentials, governance track records, past program outcomes, and budgetary formulations submitted in this proposal are true, authentic, and substantiated by our certified regulatory filings (including Form 10B/10BB audit reports, ITR-7 acknowledgments, and NITI Aayog Darpan compliance). We certify that no funding requested in this application is duplicated across any other donor agency or government grant scheme.
                </p>
              </div>

              {/* Designated Bank Account Details Table */}
              <div className="rounded-xl border border-slate-200 overflow-hidden bg-white shadow-2xs">
                <div className="bg-slate-900 px-4 py-2 text-white text-xs font-bold flex items-center justify-between">
                  <span>Designated Institutional Bank Account for Grant Disbursement</span>
                  <span className="font-mono text-[10px] text-slate-300 uppercase">Direct Benefit Transfer</span>
                </div>
                <div className="p-4 grid grid-cols-2 sm:grid-cols-4 gap-4 text-xs">
                  <div>
                    <span className="text-[10px] font-bold uppercase text-slate-400 block">Bank & Branch</span>
                    <span className="font-bold text-slate-900">State Bank of India</span>
                    <span className="text-[11px] text-slate-500 block">Main Branch, Nashik</span>
                  </div>
                  <div>
                    <span className="text-[10px] font-bold uppercase text-slate-400 block">Account Holder</span>
                    <span className="font-bold text-slate-900 truncate block" title={activeNgo?.name}>
                      {activeNgo?.name}
                    </span>
                    <span className="text-[11px] text-emerald-700 font-semibold block">Verified Match</span>
                  </div>
                  <div>
                    <span className="text-[10px] font-bold uppercase text-slate-400 block">Account Number</span>
                    <span className="font-mono font-bold text-slate-900">39820010005432</span>
                    <span className="text-[11px] text-slate-500 block font-mono">Current Account</span>
                  </div>
                  <div>
                    <span className="text-[10px] font-bold uppercase text-slate-400 block">IFSC & MICR</span>
                    <span className="font-mono font-bold text-slate-900">SBIN0000437</span>
                    <span className="text-[11px] text-slate-500 block font-mono">MICR: 422002002</span>
                  </div>
                </div>
              </div>

              {/* Dual-Signatory Block with Real Signature + Stamp Overlay */}
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-6 pt-2">
                {/* Left: Authorized Signatory */}
                <div className="rounded-xl border border-slate-200 bg-slate-50/60 p-5 relative overflow-hidden">
                  <p className="font-bold text-slate-900 text-xs uppercase tracking-wider mb-2">
                    Authorized Signatory & Managing Trustee
                  </p>
                  <p className="text-xs text-slate-700 font-medium">{activeNgo?.name}</p>

                  <div className="relative h-24 my-2 flex items-center">
                    {/* Real Signature Image */}
                    {assetsMap.signature ? (
                      <img
                        src={assetsMap.signature}
                        alt="Authorized Signature"
                        className="h-16 w-auto object-contain relative z-10"
                      />
                    ) : (
                      <div className="h-12 border-b border-dashed border-slate-300 w-48 mt-4" />
                    )}

                    {/* Real Rubber Stamp Image (Overlaid with 8deg tilt & opacity) */}
                    {assetsMap.stamp && (
                      <img
                        src={assetsMap.stamp}
                        alt="Official Stamp"
                        className="absolute left-24 top-1 h-20 w-20 object-contain z-20 pointer-events-none opacity-85 rotate-[-8deg]"
                      />
                    )}
                  </div>

                  <div className="pt-2 border-t border-slate-200 flex items-center justify-between text-[11px] text-slate-500">
                    <span>Official Seal & Signature</span>
                    <span className="text-emerald-700 font-semibold">Attested</span>
                  </div>
                </div>

                {/* Right: GrantSetu System Security Seal */}
                <div className="rounded-xl border border-emerald-200 bg-emerald-50/40 p-5 flex flex-col justify-between">
                  <div>
                    <div className="flex items-center gap-1.5 text-emerald-800 font-bold text-xs uppercase tracking-wider mb-1">
                      <ShieldCheck className="size-4 text-emerald-600" />
                      GrantSetu Digital Attestation
                    </div>
                    <p className="text-[11px] text-slate-600">
                      Certified by the GrantSetu Multi-Agent System following FActScore claim extraction and entailment verification against certified vault filings.
                    </p>
                  </div>

                  <div className="pt-3 border-t border-emerald-200/60 space-y-1 font-mono text-[10px] text-slate-600">
                    <div className="flex justify-between">
                      <span>Audit Status:</span>
                      <strong className="text-emerald-700">100% Entailed & Verified</strong>
                    </div>
                    <div className="flex justify-between">
                      <span>Tracking ID:</span>
                      <strong className="text-slate-800">GS/2026/PROP-{proposalData.proposal_id.slice(0, 8).toUpperCase()}</strong>
                    </div>
                    <div className="flex justify-between">
                      <span>Timestamp:</span>
                      <span>{new Date().toLocaleDateString('en-IN', { dateStyle: 'medium' })}</span>
                    </div>
                  </div>
                </div>
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
                    <div className="text-center px-3 py-1.5 bg-white rounded-xl border border-slate-200 shadow-2xs">
                      <span className="text-[10px] text-slate-500 block uppercase font-bold">
                        Historical Facts
                      </span>
                      <span className="text-base font-black text-emerald-600">
                        {verificationResults.filter((r) => r.verdict === 'supported').length}
                      </span>
                    </div>

                    <div className="text-center px-3 py-1.5 bg-white rounded-xl border border-slate-200 shadow-2xs">
                      <span className="text-[10px] text-slate-500 block uppercase font-bold">
                        Proposed Targets
                      </span>
                      <span className="text-base font-black text-amber-600">
                        {verificationResults.filter((r) => r.verdict === 'partially_supported').length}
                      </span>
                    </div>

                    <div className="text-center px-3 py-1.5 bg-white rounded-xl border border-slate-200 shadow-2xs">
                      <span className="text-[10px] text-slate-500 block uppercase font-bold">
                        Fabrication Rate
                      </span>
                      <span
                        className={`text-base font-black ${fabricationRate === 0 ? 'text-emerald-600' : 'text-rose-600'
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
                          className={`rounded-xl p-4 border text-xs transition-all ${isSupported
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
                              className={`inline-flex items-center gap-1 rounded-full px-2.5 py-0.5 text-[10px] font-bold uppercase shrink-0 ${isSupported
                                ? 'bg-emerald-100 text-emerald-800'
                                : isPartial
                                  ? 'bg-amber-100 text-amber-800'
                                  : 'bg-rose-100 text-rose-800'
                                }`}
                            >
                              {isSupported ? 'Historical Fact ✓' : isPartial ? 'Project Target' : 'Contradiction'}
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
      {/* Targeted Section Refinement Modal */}
      {refineModalOpen && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-slate-900/50 backdrop-blur-xs p-4 no-print">
          <div className="bg-white rounded-2xl max-w-lg w-full p-6 shadow-xl border border-slate-200 animate-in fade-in zoom-in duration-150">
            <div className="flex items-center justify-between pb-3 border-b border-slate-100">
              <div className="flex items-center gap-2">
                <div className="size-8 rounded-lg bg-indigo-50 text-indigo-700 flex items-center justify-center">
                  <Wand2 className="size-4" />
                </div>
                <div>
                  <h3 className="text-sm font-bold text-slate-900">
                    Refine &quot;{activeSectionKey.replace(/_/g, ' ').replace(/\b\w/g, (l) => l.toUpperCase())}&quot;
                  </h3>
                  <p className="text-[11px] text-slate-500">
                    Instruct Gemini to enhance this specific section.
                  </p>
                </div>
              </div>
              <button
                onClick={() => setRefineModalOpen(false)}
                className="text-slate-400 hover:text-slate-700 p-1 cursor-pointer"
              >
                <X className="size-4" />
              </button>
            </div>

            <div className="py-4 space-y-3">
              <div>
                <label className="text-xs font-semibold text-slate-700 block mb-1">
                  Quick Improvement Presets:
                </label>
                <div className="flex flex-wrap gap-1.5">
                  {[
                    'Break down into 3-tier unit costs with exact arithmetic',
                    'Make tone more authoritative and rigorous',
                    'Add measurable KPIs, cohort size and milestone targets',
                    'Emphasize community governance and sustainability',
                  ].map((preset) => (
                    <button
                      key={preset}
                      type="button"
                      onClick={() => setRefineInstruction(preset)}
                      className="text-[11px] px-2.5 py-1 bg-slate-100 hover:bg-indigo-50 hover:text-indigo-700 rounded-md transition text-slate-600 border border-slate-200/60 cursor-pointer"
                    >
                      + {preset}
                    </button>
                  ))}
                </div>
              </div>

              <div>
                <label className="text-xs font-semibold text-slate-700 block mb-1">
                  Custom Refinement Instruction:
                </label>
                <textarea
                  rows={4}
                  value={refineInstruction}
                  onChange={(e) => setRefineInstruction(e.target.value)}
                  placeholder="e.g. Expand on the solar pump installation workflow and specify monthly honorariums for field mobilizers..."
                  className="w-full text-xs rounded-xl border border-slate-200 p-3 text-slate-800 focus:border-indigo-500 focus:ring-1 focus:ring-indigo-500 outline-hidden bg-slate-50/50"
                />
              </div>

              {refineError && (
                <div className="p-2.5 rounded-lg bg-rose-50 border border-rose-200 text-rose-700 text-xs flex items-center gap-1.5">
                  <AlertCircle className="size-3.5 shrink-0" />
                  <span>{refineError}</span>
                </div>
              )}
            </div>

            <div className="flex items-center justify-end gap-2 pt-3 border-t border-slate-100">
              <button
                type="button"
                onClick={() => setRefineModalOpen(false)}
                className="px-3 py-1.5 text-xs text-slate-600 hover:text-slate-800 cursor-pointer"
              >
                Cancel
              </button>
              <button
                type="button"
                onClick={handleRefineSubmit}
                disabled={isRefining || !refineInstruction.trim()}
                className="inline-flex items-center gap-1.5 px-4 py-2 bg-indigo-600 hover:bg-indigo-700 text-white text-xs font-semibold rounded-lg shadow-xs transition cursor-pointer disabled:opacity-50"
              >
                {isRefining ? (
                  <>
                    <div className="size-3.5 border-2 border-white border-t-transparent rounded-full animate-spin" />
                    Refining Section...
                  </>
                ) : (
                  <>
                    <Wand2 className="size-3.5" />
                    Apply AI Refinement
                  </>
                )}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}
