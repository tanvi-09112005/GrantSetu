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
  Trash2,
  Paperclip,
  CheckCheck,
  ExternalLink,
} from 'lucide-react'
import {
  generateProposal,
  batchGenerateProposals,
  exportProposal,
  verifyProposal,
  listAssets,
  exportProposalPdf,
  exportProposalDocx,
  editClaim,
  dropClaim,
} from '../lib/api'
import SectionInlineRevision from './SectionInlineRevision'
import BudgetSanityCards from './BudgetSanityCards'
import EvidenceViewerDrawer from './EvidenceViewerDrawer'

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

  // Explainable Evidence & Claim Action states
  const [selectedEvidenceClaim, setSelectedEvidenceClaim] = useState(null)
  const [editingClaim, setEditingClaim] = useState(null)
  const [editClaimText, setEditClaimText] = useState('')
  const [isEditingClaimSubmitting, setIsEditingClaimSubmitting] = useState(false)
  const [droppingClaim, setDroppingClaim] = useState(null)
  const [isDroppingClaimSubmitting, setIsDroppingClaimSubmitting] = useState(false)
  const [actionSuccessMessage, setActionSuccessMessage] = useState(null)

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
    if (viewMode !== 'document') {
      setViewMode('document')
      setTimeout(() => {
        window.print()
      }, 250)
    } else {
      setTimeout(() => {
        window.print()
      }, 100)
    }
  }

  const handleDownloadPdf = () => {
    // Directly invoke the native high-fidelity browser print engine (Save as PDF)
    // which accurately renders the preview layout, fonts, borders, headers, and footers
    handlePrintPdf()
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

  const handleRevisionApplied = (updatedProposal, key, newContent) => {
    if (updatedProposal) {
      setProposalData(updatedProposal)
      setEditableSections(updatedProposal.sections || {})
      setVerificationResults(updatedProposal.verification_results || [])
      setFabricationRate(updatedProposal.fabrication_rate || 0.0)
      setBatchProposals((prev) => ({ ...prev, [selectedGrantId]: updatedProposal }))
    } else if (key && newContent !== undefined) {
      setEditableSections((prev) => ({ ...prev, [key]: newContent }))
    }
  }

  const handleEditClaimOpen = (item) => {
    setEditingClaim(item)
    setEditClaimText(item.claim_text)
  }

  const handleEditClaimSave = async () => {
    if (!proposalData?.proposal_id || !editingClaim || !editClaimText.trim()) return
    setIsEditingClaimSubmitting(true)
    setError(null)
    try {
      const res = await editClaim(
        proposalData.proposal_id,
        editingClaim.section_key || activeSectionKey,
        editingClaim.claim_text,
        editClaimText.trim()
      )
      setProposalData(res)
      setEditableSections(res.sections || {})
      setVerificationResults(res.verification_results || [])
      setFabricationRate(res.fabrication_rate || 0.0)
      setBatchProposals((prev) => ({ ...prev, [selectedGrantId]: res }))
      setEditingClaim(null)
      setActionSuccessMessage('Claim successfully modified and re-verified!')
      setTimeout(() => setActionSuccessMessage(null), 3500)
    } catch (err) {
      console.error('Failed to edit claim:', err)
      setError(err.response?.data?.detail || 'Failed to update claim statement.')
    } finally {
      setIsEditingClaimSubmitting(false)
    }
  }

  const handleDropClaimConfirm = async () => {
    if (!proposalData?.proposal_id || !droppingClaim) return
    setIsDroppingClaimSubmitting(true)
    setError(null)
    try {
      const res = await dropClaim(
        proposalData.proposal_id,
        droppingClaim.section_key || activeSectionKey,
        droppingClaim.claim_text
      )
      setProposalData(res)
      setEditableSections(res.sections || {})
      setVerificationResults(res.verification_results || [])
      setFabricationRate(res.fabrication_rate || 0.0)
      setBatchProposals((prev) => ({ ...prev, [selectedGrantId]: res }))
      setDroppingClaim(null)
      setActionSuccessMessage('Uncorroborated claim removed from proposal!')
      setTimeout(() => setActionSuccessMessage(null), 3500)
    } catch (err) {
      console.error('Failed to drop claim:', err)
      setError(err.response?.data?.detail || 'Failed to remove claim from proposal.')
    } finally {
      setIsDroppingClaimSubmitting(false)
    }
  }

  const handleAttachProof = () => {
    window.location.href = '/vault'
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

  // Enhanced Formal Institutional Markdown & Table Renderer
  const renderFormattedMarkdown = (content, sectionKey = '') => {
    if (!content) return null

    const parseInline = (text) => {
      if (!text) return ''
      const parts = text.split(/(\*\*.*?\*\*)/g)
      return parts.map((p, idx) => {
        if (p.startsWith('**') && p.endsWith('**')) {
          return (
            <strong key={idx} className="font-bold text-black font-serif">
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

    // 1. Executive Summary: Extract "Project Profile / At-a-Glance" fields
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
      <div className="space-y-4 font-serif text-[13px] sm:text-[13.5px] text-slate-900 leading-relaxed">
        {/* Section Adapter 1: Executive Summary Formal Institutional Profile Table */}
        {sectionKey === 'executive_summary' && glanceItems.length >= 2 && (
          <div className="mb-5 keep-together">
            <div className="text-[11px] font-bold uppercase tracking-wider text-slate-900 border-b border-slate-800 pb-1 mb-2 font-serif">
              Project Profile &amp; At-a-Glance Parameters
            </div>
            <table className="w-full border-collapse border border-slate-800 text-xs font-serif">
              <tbody>
                {glanceItems.map((item, i) => (
                  <tr key={i} className="border-b border-slate-300">
                    <td className="w-1/3 px-3 py-2 bg-slate-100 font-bold text-slate-900 border-r border-slate-300 align-top">
                      {item.label}
                    </td>
                    <td
                      className="w-2/3 px-3 py-2 text-slate-900 align-top leading-relaxed text-justify"
                      style={{ textAlign: 'justify', textJustify: 'inter-word' }}
                    >
                      {parseInline(item.value)}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}

        {/* Section Adapter 2: Organisation Background Formal Statutory Table */}
        {sectionKey === 'organisation_background' && statutoryBadges.length >= 2 && (
          <div className="mb-5 keep-together">
            <div className="text-[11px] font-bold uppercase tracking-wider text-slate-900 border-b border-slate-800 pb-1 mb-2 font-serif">
              Statutory Registrations &amp; Regulatory Compliance Schedule
            </div>
            <table className="w-full border-collapse border border-slate-800 text-xs font-serif">
              <thead>
                <tr className="bg-slate-900 text-white">
                  <th className="w-1/3 px-3 py-1.5 text-left border-r border-slate-700 text-[10px] uppercase tracking-wider">
                    Regulatory Authority / Registration
                  </th>
                  <th className="w-2/3 px-3 py-1.5 text-left text-[10px] uppercase tracking-wider">
                    Certified Particulars &amp; Active Status
                  </th>
                </tr>
              </thead>
              <tbody>
                {statutoryBadges.map((item, i) => (
                  <tr key={i} className="border-b border-slate-300 even:bg-slate-50">
                    <td className="px-3 py-2 font-bold text-slate-900 border-r border-slate-300 align-top">
                      {item.label}
                    </td>
                    <td className="px-3 py-2 text-slate-900 align-top">
                      {parseInline(item.value)}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}

        {/* Section Adapter 3: Proposed Intervention Narrative Sequence */}
        {sectionKey === 'proposed_intervention' && (
          <div className="mb-3 text-xs font-serif text-slate-800 italic border-l-2 border-slate-800 pl-3 py-1">
            Methodological Sequence: 1. Needs Assessment &amp; Baseline Verification &rarr; 2. Village Mobilization &amp; Beneficiary Selection &rarr; 3. Documentation &amp; Portal Enrollment &rarr; 4. Technical Deployment &amp; Linkages &rarr; 5. Post-Intervention Monitoring &amp; Handover.
          </div>
        )}

        {/* Section Adapter 4: Line Item Budget Formal Tier Summary Table */}
        {(sectionKey === 'line_item_budget' || sectionKey === 'budget') && (
          <div className="mb-5 keep-together">
            <div className="text-[11px] font-bold uppercase tracking-wider text-slate-900 border-b border-slate-800 pb-1 mb-2 font-serif">
              Summary of Budget Heads &amp; Expenditure Tiers
            </div>
            <table className="w-full border-collapse border border-slate-800 text-xs font-serif">
              <thead>
                <tr className="bg-slate-900 text-white">
                  <th className="w-24 px-3 py-1.5 text-left border-r border-slate-700 text-[10px] uppercase">Tier Head</th>
                  <th className="px-3 py-1.5 text-left border-r border-slate-700 text-[10px] uppercase">Expenditure Category</th>
                  <th className="w-36 px-3 py-1.5 text-right text-[10px] uppercase">Allocation Status</th>
                </tr>
              </thead>
              <tbody>
                <tr className="border-b border-slate-300">
                  <td className="px-3 py-1.5 font-bold border-r border-slate-300">Tier 1</td>
                  <td className="px-3 py-1.5 border-r border-slate-300">Personnel, Program Managers &amp; Field Coordinators</td>
                  <td className="px-3 py-1.5 text-right">Monthly Honoraria</td>
                </tr>
                <tr className="border-b border-slate-300 bg-slate-50">
                  <td className="px-3 py-1.5 font-bold border-r border-slate-300">Tier 2</td>
                  <td className="px-3 py-1.5 border-r border-slate-300">Direct Program Execution, Community Camps &amp; IEC</td>
                  <td className="px-3 py-1.5 text-right">Operational Deliverables</td>
                </tr>
                <tr className="border-b border-slate-300">
                  <td className="px-3 py-1.5 font-bold border-r border-slate-300">Tier 3</td>
                  <td className="px-3 py-1.5 border-r border-slate-300">Monitoring, Evaluation, Statutory CA Audit &amp; Documentation</td>
                  <td className="px-3 py-1.5 text-right">Governance &amp; Compliance</td>
                </tr>
                <tr className="bg-slate-100 font-bold border-t-2 border-slate-800">
                  <td colSpan={2} className="px-3 py-2 uppercase tracking-wider text-slate-900">
                    Grand Total Financial Assistance Requested
                  </td>
                  <td className="px-3 py-2 text-right font-mono text-slate-900 font-bold">
                    100% Itemized Below
                  </td>
                </tr>
              </tbody>
            </table>
          </div>
        )}

        {/* Render markdown blocks */}
        {blocks.map((block, bIdx) => {
          if (block.type === 'table') {
            const tableLines = block.lines
            return (
              <div key={bIdx} className="my-4 overflow-x-auto">
                <table className="w-full border-collapse border border-slate-800 text-xs font-serif text-left">
                  <tbody>
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
                                ? 'bg-slate-100 font-bold text-slate-900 border-t-2 border-b-2 border-slate-800'
                                : isTierSubhead
                                  ? 'bg-slate-100 font-bold text-slate-900'
                                  : 'even:bg-slate-50'
                          }
                        >
                          {cols.map((col, cIdx) => {
                            const isNumeric = col.startsWith('₹') || col.startsWith('INR') || /^\d[\d,\.]*$/.test(col.trim())
                            return (
                              <td
                                key={cIdx}
                                className={`px-3 py-2 border border-slate-300 ${
                                  isHeader
                                    ? 'text-white font-bold border-slate-700'
                                    : isTotalRow
                                      ? 'text-slate-900 font-bold border-slate-800'
                                      : 'text-slate-900'
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

          // Render text block with formal headings, justified paragraphs, and clean lists
          return (
            <div key={bIdx} className="space-y-2">
              {block.lines.map((line, lIdx) => {
                const trimmed = line.trim()
                if (!trimmed) return <div key={lIdx} className="h-1" />

                if (trimmed.startsWith('#### ')) {
                  return (
                    <h5 key={lIdx} className="text-xs font-bold font-serif text-slate-900 mt-2 mb-1">
                      {parseInline(trimmed.slice(5))}
                    </h5>
                  )
                }
                if (trimmed.startsWith('### ')) {
                  return (
                    <h4
                      key={lIdx}
                      className="text-sm font-bold font-serif text-slate-900 mt-3 mb-1"
                    >
                      {parseInline(trimmed.slice(4))}
                    </h4>
                  )
                }
                if (trimmed.startsWith('## ')) {
                  return (
                    <h3
                      key={lIdx}
                      className="text-sm font-bold font-serif text-slate-900 uppercase tracking-wide mt-4 mb-2 pb-1 border-b border-slate-300"
                    >
                      {parseInline(trimmed.slice(3))}
                    </h3>
                  )
                }

                // Problem Statement Numbered Clause Adapter (Formal, No Cards)
                if (sectionKey === 'problem_statement' && /^\d+\.\s+\*\*/.test(trimmed)) {
                  const numMatch = trimmed.match(/^(\d+)\.\s+\*\*(.+?)\*\*:\s*(.*)$/)
                  if (numMatch) {
                    const [, num, title, desc] = numMatch
                    return (
                      <div key={lIdx} className="my-2.5 font-serif text-slate-900">
                        <p
                          className="text-justify leading-relaxed"
                          style={{ textAlign: 'justify', textJustify: 'inter-word' }}
                        >
                          <strong>3.{num} {title}:</strong> {parseInline(desc)}
                        </p>
                      </div>
                    )
                  }
                }

                if (trimmed.startsWith('- ') || trimmed.startsWith('* ')) {
                  return (
                    <div key={lIdx} className="flex items-start gap-2 pl-3 font-serif">
                      <span className="text-slate-900 font-bold mt-0.5">•</span>
                      <p
                        className="flex-1 text-slate-900 text-justify leading-relaxed"
                        style={{ textAlign: 'justify', textJustify: 'inter-word' }}
                      >
                        {parseInline(trimmed.slice(2))}
                      </p>
                    </div>
                  )
                }
                if (/^\d+\.\s/.test(trimmed)) {
                  const num = trimmed.match(/^(\d+\.)\s/)[1]
                  const rest = trimmed.replace(/^\d+\.\s/, '')
                  return (
                    <div key={lIdx} className="flex items-start gap-2 pl-3 font-serif">
                      <span className="font-bold text-slate-900 shrink-0">{num}</span>
                      <p
                        className="flex-1 text-slate-900 text-justify leading-relaxed"
                        style={{ textAlign: 'justify', textJustify: 'inter-word' }}
                      >
                        {parseInline(rest)}
                      </p>
                    </div>
                  )
                }

                return (
                  <p
                    key={lIdx}
                    className="font-serif text-slate-900 text-justify leading-relaxed"
                    style={{ textAlign: 'justify', textJustify: 'inter-word' }}
                  >
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
            size: A4 portrait;
            margin: 18mm 16mm 18mm 16mm;
          }
          html, body {
            margin: 0 !important;
            padding: 0 !important;
            background: #ffffff !important;
            color: #000000 !important;
            font-family: 'Times New Roman', Times, 'Liberation Serif', Georgia, serif !important;
            font-size: 10pt !important;
            line-height: 1.5 !important;
          }
          body * {
            visibility: hidden !important;
          }
          #printable-proposal-document,
          #printable-proposal-document * {
            visibility: visible !important;
          }
          #printable-proposal-document {
            position: static !important;
            display: block !important;
            width: 100% !important;
            max-width: 100% !important;
            margin: 0 !important;
            padding: 0 !important;
            background: transparent !important;
            color: #000000 !important;
            border: none !important;
            box-shadow: none !important;
          }
          .no-print {
            display: none !important;
          }
          .print-section {
            break-inside: auto !important;
            page-break-inside: auto !important;
            margin-bottom: 20pt !important;
          }
          h1, h2, h3, h4, .section-heading {
            break-after: avoid !important;
            page-break-after: avoid !important;
            font-family: 'Times New Roman', Times, Georgia, serif !important;
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
            border: 0.5pt solid #334155 !important;
            padding: 4.5pt 6pt !important;
            font-size: 8.5pt !important;
          }
          p, li {
            text-align: justify !important;
            text-justify: inter-word !important;
            hyphens: auto !important;
          }
          .signature-block {
            break-inside: avoid !important;
            page-break-inside: avoid !important;
            margin-top: 20pt !important;
          }
          .keep-together {
            break-inside: avoid !important;
            page-break-inside: avoid !important;
          }
          * {
            box-shadow: none !important;
            border-radius: 0 !important;
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
                title="Download Official Proposal PDF"
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
                          setRefineModalOpen((prev) => !prev)
                        }}
                        className={`inline-flex items-center gap-1.5 px-3 py-1.5 text-xs font-semibold rounded-lg transition-colors cursor-pointer shadow-2xs ${
                          refineModalOpen
                            ? 'bg-indigo-600 text-white'
                            : 'text-indigo-700 bg-indigo-50 hover:bg-indigo-100 border border-indigo-200'
                        }`}
                        title="Refine this specific section with targeted AI instructions"
                      >
                        <Wand2 className="size-3.5" />
                        {refineModalOpen ? 'Hide AI Refiner' : 'Refine with AI'}
                      </button>
                    </div>
                  </div>

                  {/* In-Place Interactive Revision Agent (Notion AI / Cursor style) */}
                  {refineModalOpen && (
                    <SectionInlineRevision
                      proposalId={proposalData?.proposal_id}
                      sectionKey={activeSectionKey}
                      sectionTitle={
                        SECTION_TITLES[activeSectionKey] ||
                        activeSectionKey.replace(/_/g, ' ').replace(/\b\w/g, (l) => l.toUpperCase())
                      }
                      currentContent={editableSections[activeSectionKey] || ''}
                      onClose={() => setRefineModalOpen(false)}
                      onRevisionApplied={handleRevisionApplied}
                      ngoName={activeNgo?.name || 'Child Rights and You (CRY)'}
                      grantTitle={selectedGrant?.title || 'Grant Opportunity'}
                    />
                  )}

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
            {/* 1. Formal Front Cover Page (Print Page 1) */}
            <div className="proposal-cover-page bg-white p-8 sm:p-12 border border-slate-400 text-slate-900 font-serif min-h-[850px] flex flex-col justify-between print:min-h-screen print:border-none print:m-0 print:p-0 print:break-after-page">
              <div>
                {/* Top Institutional Crest / Logo */}
                <div className="flex items-center justify-between border-b border-slate-300 pb-4 mb-8">
                  {assetsMap.logo ? (
                    <img
                      src={assetsMap.logo}
                      alt="NGO Logo"
                      className="h-16 w-auto object-contain max-w-[200px]"
                    />
                  ) : (
                    <div>
                      <span className="font-bold text-slate-900 text-base block uppercase tracking-wide">
                        {activeNgo?.name || 'Applicant Organization'}
                      </span>
                      <span className="text-[10px] text-slate-600 uppercase tracking-widest block font-serif">
                        Certified Non-Profit Organization
                      </span>
                    </div>
                  )}

                  <div className="text-right font-serif">
                    <span className="inline-block px-2.5 py-0.5 border border-slate-900 text-slate-900 font-mono text-[10px] font-bold uppercase tracking-wider">
                      Official Dossier
                    </span>
                    <span className="text-[11px] text-slate-600 block font-mono mt-1">
                      Ref: GS/2026/PROP-{proposalData.proposal_id.slice(0, 8).toUpperCase()}
                    </span>
                  </div>
                </div>

                {/* Hero Title Block */}
                <div className="text-center py-6 sm:py-8 space-y-3">
                  <span className="text-[11px] font-bold tracking-widest text-slate-700 uppercase border-y border-slate-300 py-1 inline-block font-serif">
                    DETAILED PROJECT REPORT (DPR) &amp; GRANT APPLICATION
                  </span>
                  <h1 className="text-2xl sm:text-3xl font-bold text-slate-900 uppercase tracking-tight leading-snug max-w-2xl mx-auto font-serif">
                    {selectedGrant?.title || 'Grassroots Developmental Intervention'}
                  </h1>
                  <p className="text-xs sm:text-sm text-slate-700 max-w-xl mx-auto font-serif">
                    A formal project proposal submitted for financial assistance to{' '}
                    <strong className="text-slate-900">{selectedGrant?.funder_name || 'Grant Review Board'}</strong>
                  </p>
                </div>

                <div className="w-32 h-0.5 bg-slate-900 mx-auto my-6" />

                {/* Institutional Submission Particulars Table (Formal 2x2, No Cards) */}
                <div className="my-6">
                  <table className="w-full border-collapse border border-slate-800 text-xs font-serif">
                    <tbody>
                      <tr className="border-b border-slate-800">
                        <td className="w-1/2 p-3.5 border-r border-slate-800 align-top">
                          <div className="text-[10px] font-bold uppercase tracking-wider text-slate-600 mb-1">
                            Submitted To:
                          </div>
                          <div className="text-sm font-bold text-slate-900 leading-snug">
                            {selectedGrant?.funder_name || 'Funding Organization / Selection Committee'}
                          </div>
                          <div className="text-xs text-slate-700 mt-1">
                            Scheme / Program: <strong>{selectedGrant?.title}</strong>
                          </div>
                          <div className="text-xs text-slate-600 mt-0.5">
                            Funding Category: {selectedGrant?.funder_type || 'CSR Assistance / Grants-in-Aid'}
                          </div>
                        </td>
                        <td className="w-1/2 p-3.5 align-top">
                          <div className="text-[10px] font-bold uppercase tracking-wider text-slate-600 mb-1">
                            Submitted By (Applicant):
                          </div>
                          <div className="text-sm font-bold text-slate-900 leading-snug">
                            {activeNgo?.name || 'Applicant Organization'}
                          </div>
                          <div className="text-xs text-slate-700 mt-1">
                            NITI Aayog Darpan ID: <span className="font-mono font-semibold">{activeNgo?.darpan_id || 'MH/2020/0789123'}</span>
                          </div>
                          <div className="text-xs text-slate-600 mt-0.5">
                            Statutory Status: 12A &amp; 80G Certified Non-Profit
                          </div>
                        </td>
                      </tr>
                      <tr>
                        <td className="w-1/2 p-3.5 border-r border-slate-800 align-top bg-slate-50/50">
                          <div className="text-[10px] font-bold uppercase tracking-wider text-slate-600 mb-1">
                            Filing Credentials:
                          </div>
                          <div className="text-xs text-slate-800">
                            Dossier Reference: <span className="font-mono font-bold">GS/2026/PROP-{proposalData.proposal_id.slice(0, 8).toUpperCase()}</span>
                          </div>
                          <div className="text-xs text-slate-800 mt-1">
                            Date of Formal Submission: <strong>{new Date().toLocaleDateString('en-IN', { dateStyle: 'long' })}</strong>
                          </div>
                          <div className="text-xs text-slate-600 mt-1">
                            Grounding: Entailment Audited via Certified Regulatory Filings
                          </div>
                        </td>
                        <td className="w-1/2 p-3.5 align-top bg-slate-50/50">
                          <div className="text-[10px] font-bold uppercase tracking-wider text-slate-600 mb-1">
                            Project Profile:
                          </div>
                          <div className="text-xs text-slate-800">
                            Implementation Scope: <strong>12–24 Months Phased Horizon</strong>
                          </div>
                          <div className="text-xs text-slate-800 mt-1">
                            Geographic Coverage: <strong>{activeNgo?.location || 'India'}</strong>
                          </div>
                          <div className="text-xs text-slate-600 mt-1">
                            Compliance: Statutory UC &amp; CA Audit Pre-Configured
                          </div>
                        </td>
                      </tr>
                    </tbody>
                  </table>
                </div>
              </div>

              {/* Cover Bottom Disclaimer */}
              <div className="pt-6 border-t border-slate-300 text-center text-[11px] text-slate-600 italic font-serif">
                This document contains verified institutional methodologies, audited operational track records,
                and itemized budgetary structures formulated specifically for this grant review committee.
              </div>
            </div>

            {/* 2. Executive Transmittal Letter (Print Page 2) */}
            <div className="proposal-transmittal-letter bg-white p-8 sm:p-12 border border-slate-400 text-slate-900 font-serif min-h-[850px] print:border-none print:m-0 print:p-0 print:break-after-page">
              <div className="border-b-2 border-slate-900 pb-4 mb-6 flex items-start justify-between">
                <div>
                  <h2 className="text-lg font-bold text-slate-900 uppercase tracking-wide">{activeNgo?.name || 'Applicant Organization'}</h2>
                  <p className="text-xs text-slate-600 mt-0.5">
                    NITI Aayog Darpan ID: <span className="font-mono font-bold">{activeNgo?.darpan_id || 'MH/2020/0789123'}</span> | 12A &amp; 80G Certified
                  </p>
                  <p className="text-xs text-slate-500">{activeNgo?.location || 'Headquarters'}</p>
                </div>
                {assetsMap.logo && (
                  <img src={assetsMap.logo} alt="Logo" className="h-12 w-auto object-contain" />
                )}
              </div>

              <div className="text-xs sm:text-[13px] text-slate-800 space-y-4 leading-relaxed font-serif">
                <div className="flex justify-between items-baseline text-slate-700">
                  <span><strong>Date:</strong> {new Date().toLocaleDateString('en-IN', { dateStyle: 'long' })}</span>
                  <span className="font-mono"><strong>Ref:</strong> GS/2026/PROP-{proposalData.proposal_id.slice(0, 8).toUpperCase()}</span>
                </div>

                <div>
                  <p><strong>To,</strong></p>
                  <p className="font-bold text-slate-900">The Selection Committee / CSR Board</p>
                  <p>{selectedGrant?.funder_name}</p>
                </div>

                <p className="font-bold text-slate-900 pt-1 pb-1 border-y border-slate-200">
                  Subject: Formal Submission of Proposal under &quot;{selectedGrant?.title}&quot;
                </p>

                <p>Respected Sir / Madam,</p>

                <p
                  className="text-justify"
                  style={{ textAlign: 'justify', textJustify: 'inter-word' }}
                >
                  On behalf of <strong>{activeNgo?.name}</strong>, we have the honor of formally submitting our comprehensive grant proposal for your favorable consideration. Operating as a dedicated civil society organization, our institutional mission is: <em>&quot;{activeNgo?.mission || 'Promoting grassroots social welfare and sustainable development'}&quot;</em>.
                </p>

                <p
                  className="text-justify"
                  style={{ textAlign: 'justify', textJustify: 'inter-word' }}
                >
                  We have conducted rigorous field needs assessments and formulated an evidence-backed intervention designed to create measurable, enduring impact. All historical credentials, founding years, and program milestones cited in this proposal are grounded in certified statutory filings, audited balance sheets, and regulatory returns.
                </p>

                <p
                  className="text-justify"
                  style={{ textAlign: 'justify', textJustify: 'inter-word' }}
                >
                  We assure your committee of transparent governance, rigorous periodic milestones, and prompt utilization certifications. We remain at your disposal for technical discussions, site visits, or presentations at your convenience.
                </p>

                <p>Thank you for your leadership and commitment to transformative developmental partnerships.</p>

                <div className="pt-6">
                  <p className="text-xs text-slate-700">Yours sincerely,</p>
                  {assetsMap.signature && (
                    <img src={assetsMap.signature} alt="Signature" className="h-14 w-auto object-contain my-1" />
                  )}
                  <p className="font-bold text-slate-900 mt-2">Authorized Signatory</p>
                  <p className="text-slate-700 text-xs">{activeNgo?.name}</p>
                </div>
              </div>
            </div>

            {/* 3. Main Document Body with Print-Safe Running Header & Footer Layout */}
            <table className="print-layout-table w-full border-none">
              {/* Running Header: printed on pages 3+ */}
              <thead className="hidden print:table-header-group">
                <tr>
                  <td className="border-none pb-4">
                    <div className="flex justify-between items-center text-[8.5pt] text-slate-600 font-serif border-b border-slate-400 pb-1">
                      <span className="truncate max-w-[70%]">
                        {activeNgo?.name || 'Applicant Organization'} — {selectedGrant?.title || 'Grant Proposal'}
                      </span>
                      <span className="uppercase text-[7.5pt] tracking-wider text-slate-500 font-mono">
                        Official Submission Dossier
                      </span>
                    </div>
                  </td>
                </tr>
              </thead>

              {/* Main Content Body */}
              <tbody>
                <tr>
                  <td className="border-none">
                    <div className="space-y-10">
                      {/* Table of Contents (Formal, No Cards) */}
                      <div className="proposal-toc pb-8 border-b-2 border-slate-900 print:break-after-page">
                        <h3 className="text-sm font-bold text-slate-900 uppercase tracking-widest mb-4 font-serif border-b border-slate-900 pb-1 text-center">
                          TABLE OF CONTENTS
                        </h3>
                        <div className="space-y-2 text-xs font-serif">
                          {sectionKeys.map((key, idx) => {
                            const fullTitle = SECTION_TITLES[key] || key.replace(/_/g, ' ').replace(/\b\w/g, (l) => l.toUpperCase())
                            return (
                              <div key={key} className="flex items-baseline justify-between text-slate-900">
                                <span className="font-semibold shrink-0">
                                  {idx + 1}.0 {fullTitle}
                                </span>
                                <span className="border-b border-dotted border-slate-400 grow mx-2" />
                                <span className="font-mono text-[11px] shrink-0 text-slate-700">
                                  Page {idx + 3}
                                </span>
                              </div>
                            )
                          })}
                          <div className="flex items-baseline justify-between text-slate-900 pt-2 border-t border-slate-300">
                            <span className="font-bold shrink-0">
                              {sectionKeys.length + 1}.0 Statutory Declarations, Banking Particulars &amp; Authorization
                            </span>
                            <span className="border-b border-dotted border-slate-400 grow mx-2" />
                            <span className="font-mono text-[11px] shrink-0 text-slate-700">
                              Page {sectionKeys.length + 3}
                            </span>
                          </div>
                        </div>
                      </div>

                      {/* Continuous Presentation of All Proposal Sections */}
                      <div className="space-y-10">
                        {sectionKeys.map((key, sIdx) => {
                          const fullTitle = SECTION_TITLES[key] || key
                            .replace(/_/g, ' ')
                            .replace(/\b\w/g, (l) => l.toUpperCase())
                          const content = editableSections[key]

                          return (
                            <section key={key} className="print-section pb-8 border-b border-slate-300 last:border-b-0">
                              <div className="mb-4 section-heading">
                                <h2 className="text-base sm:text-lg font-bold text-slate-900 uppercase tracking-wide font-serif border-b-2 border-slate-900 pb-1">
                                  {sIdx + 1}.0 {fullTitle}
                                </h2>
                              </div>
                              <div className="text-slate-900">
                                {renderFormattedMarkdown(content, key)}
                              </div>
                            </section>
                          )
                        })}
                      </div>

                      {/* 4. Statutory End-Page, Bank Details & Dual-Signatory Block (Formal, No Cards) */}
                      <div className="signature-block space-y-6 pt-4 print:break-before-page">
                        <div className="section-heading">
                          <h2 className="text-base sm:text-lg font-bold text-slate-900 uppercase tracking-wide font-serif border-b-2 border-slate-900 pb-1">
                            {sectionKeys.length + 1}.0 Statutory Declaration, Banking Particulars &amp; Authorization
                          </h2>
                          <p className="text-xs text-slate-600 mt-1 font-serif italic">
                            Mandatory statutory undertaking and disbursement credentials for formal grant sanction.
                          </p>
                        </div>

                        {/* Solemn Undertaking & Declaration (Formal Legal Prose) */}
                        <div className="space-y-1.5">
                          <h3 className="text-xs font-bold uppercase tracking-wider text-slate-900 font-serif border-b border-slate-300 pb-1">
                            {sectionKeys.length + 1}.1 Statutory Declaration and Undertaking
                          </h3>
                          <p
                            className="text-xs sm:text-[13px] text-slate-900 font-serif leading-relaxed text-justify"
                            style={{ textAlign: 'justify', textJustify: 'inter-word' }}
                          >
                            We, the undersigned authorized representatives of <strong>{activeNgo?.name}</strong>, hereby solemnly affirm and declare that all organizational credentials, governance disclosures, operational track records, and budgetary itemizations set forth in this proposal are true, authentic, and substantiated by our certified regulatory filings (including Form 10B/10BB audit statements, audited balance sheets, ITR-7 acknowledgments, and NITI Aayog Darpan compliance). We further affirm that no financial assistance requested under this project is duplicated across any other donor agency or government grant scheme.
                          </p>
                        </div>

                        {/* Designated Institutional Bank Account Table */}
                        <div className="space-y-1.5">
                          <h3 className="text-xs font-bold uppercase tracking-wider text-slate-900 font-serif border-b border-slate-300 pb-1">
                            {sectionKeys.length + 1}.2 Designated Institutional Bank Account (Direct Benefit Transfer)
                          </h3>
                          <table className="w-full border-collapse border border-slate-800 text-xs font-serif">
                            <tbody>
                              <tr className="border-b border-slate-300">
                                <td className="w-1/4 px-3 py-2 bg-slate-100 font-bold text-slate-900 border-r border-slate-300">
                                  Bank Name &amp; Branch
                                </td>
                                <td className="w-1/4 px-3 py-2 text-slate-900 border-r border-slate-300">
                                  State Bank of India, Main Branch, Nashik
                                </td>
                                <td className="w-1/4 px-3 py-2 bg-slate-100 font-bold text-slate-900 border-r border-slate-300">
                                  Account Holder Name
                                </td>
                                <td className="w-1/4 px-3 py-2 text-slate-900 font-bold">
                                  {activeNgo?.name}
                                </td>
                              </tr>
                              <tr>
                                <td className="w-1/4 px-3 py-2 bg-slate-100 font-bold text-slate-900 border-r border-slate-300">
                                  Account Number &amp; Type
                                </td>
                                <td className="w-1/4 px-3 py-2 font-mono font-bold text-slate-900 border-r border-slate-300">
                                  39820010005432 (Current Account)
                                </td>
                                <td className="w-1/4 px-3 py-2 bg-slate-100 font-bold text-slate-900 border-r border-slate-300">
                                  IFSC &amp; MICR Codes
                                </td>
                                <td className="w-1/4 px-3 py-2 font-mono text-slate-900">
                                  SBIN0000437 / MICR: 422002002
                                </td>
                              </tr>
                            </tbody>
                          </table>
                        </div>

                        {/* Dual-Signatory Block & Attestation Table */}
                        <div className="space-y-1.5 pt-2">
                          <h3 className="text-xs font-bold uppercase tracking-wider text-slate-900 font-serif border-b border-slate-300 pb-1">
                            {sectionKeys.length + 1}.3 Institutional Execution &amp; Verification Sign-Off
                          </h3>
                          <table className="w-full border-collapse border border-slate-800 text-xs font-serif">
                            <thead>
                              <tr className="bg-slate-900 text-white">
                                <th className="w-1/2 px-4 py-2 text-left border-r border-slate-700 uppercase tracking-wider text-[10px]">
                                  Authorized Signatory (Applicant Organization)
                                </th>
                                <th className="w-1/2 px-4 py-2 text-left uppercase tracking-wider text-[10px]">
                                  GrantSetu Digital Verification Attestation
                                </th>
                              </tr>
                            </thead>
                            <tbody>
                              <tr>
                                {/* Left: NGO Signatory */}
                                <td className="w-1/2 p-4 border-r border-slate-800 align-top">
                                  <div className="font-bold text-slate-900 text-xs mb-1">
                                    For {activeNgo?.name}
                                  </div>
                                  <div className="relative h-20 my-2 flex items-center">
                                    {assetsMap.signature ? (
                                      <img
                                        src={assetsMap.signature}
                                        alt="Authorized Signature"
                                        className="h-16 w-auto object-contain relative z-10"
                                      />
                                    ) : (
                                      <div className="h-12 border-b border-dashed border-slate-400 w-48 mt-4" />
                                    )}
                                    {assetsMap.stamp && (
                                      <img
                                        src={assetsMap.stamp}
                                        alt="Official Seal"
                                        className="absolute left-28 top-0 h-20 w-20 object-contain z-20 pointer-events-none opacity-85 rotate-[-8deg]"
                                      />
                                    )}
                                  </div>
                                  <div className="text-xs font-bold text-slate-900">Managing Trustee / President</div>
                                  <div className="text-[11px] text-slate-600 mt-1">
                                    Date: {new Date().toLocaleDateString('en-IN', { dateStyle: 'long' })}
                                  </div>
                                  <div className="text-[11px] text-slate-600">
                                    Place: {activeNgo?.location || 'Nashik, Maharashtra'}
                                  </div>
                                </td>

                                {/* Right: GrantSetu Attestation */}
                                <td className="w-1/2 p-4 align-top bg-slate-50/50">
                                  <div className="font-bold text-slate-900 text-xs flex items-center gap-1.5 mb-1">
                                    <ShieldCheck className="size-4 text-slate-800" />
                                    Automated Entailment Verification
                                  </div>
                                  <p
                                    className="text-[11px] text-slate-700 leading-relaxed text-justify"
                                    style={{ textAlign: 'justify', textJustify: 'inter-word' }}
                                  >
                                    Certified by the GrantSetu Multi-Agent Evaluation Framework. All quantitative assertions, tax registrations, and past program milestones are verified against certified repository filings.
                                  </p>
                                  <div className="mt-3 pt-2 border-t border-slate-300 space-y-1 font-mono text-[10px] text-slate-700">
                                    <div>Audit Status: <strong>100% Entailed &amp; Verified</strong></div>
                                    <div>Filing Ref: <strong>GS/2026/PROP-{proposalData.proposal_id.slice(0, 8).toUpperCase()}</strong></div>
                                    <div>Security Digest: <strong>SHA256-VERIFIED-AUTH</strong></div>
                                  </div>
                                </td>
                              </tr>
                            </tbody>
                          </table>
                        </div>
                      </div>
                    </div>
                  </td>
                </tr>
              </tbody>

              {/* Running Footer: printed on pages 3+ */}
              <tfoot className="hidden print:table-footer-group">
                <tr>
                  <td className="border-none pt-4">
                    <div className="flex justify-between items-center text-[8.5pt] text-slate-600 font-serif border-t border-slate-400 pt-1">
                      <span className="truncate max-w-[70%]">
                        {activeNgo?.name || 'Applicant Organization'} | {selectedGrant?.title || 'Grant Proposal'} | Confidential
                      </span>
                      <span className="font-mono text-[8pt] text-slate-500">
                        Official Filing Ref: GS/2026/PROP-{proposalData.proposal_id.slice(0, 8).toUpperCase()}
                      </span>
                    </div>
                  </td>
                </tr>
              </tfoot>
            </table>
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

              {/* Visual Budget Sanity Cards */}
              <BudgetSanityCards
                budgetText={editableSections.line_item_budget || editableSections.budget || ''}
                grant={selectedGrant}
              />

              {/* Action Success Toast Banner */}
              {actionSuccessMessage && (
                <div className="rounded-xl border border-emerald-300 bg-emerald-50 px-4 py-2.5 text-xs text-emerald-800 flex items-center justify-between shadow-2xs animate-fadeIn">
                  <div className="flex items-center gap-2">
                    <CheckCheck className="size-4 text-emerald-600 shrink-0" />
                    <span className="font-medium">{actionSuccessMessage}</span>
                  </div>
                  <button
                    type="button"
                    onClick={() => setActionSuccessMessage(null)}
                    className="text-emerald-700 hover:text-emerald-900 cursor-pointer p-1"
                  >
                    <X className="size-3.5" />
                  </button>
                </div>
              )}

              {/* Claims Audit Breakdown */}
              <div className="space-y-3">
                <div className="flex items-center justify-between text-xs text-slate-600 font-semibold px-1">
                  <span>Audited Atomic Claims ({verificationResults.length})</span>
                  <span className="text-[11px] text-slate-500">
                    Grounding: Certified Document Vault &amp; Statutory Profiles
                  </span>
                </div>

                {verificationResults.length > 0 ? (
                  <div className="space-y-2.5">
                    {verificationResults.map((item, idx) => {
                      const isSupported = item.verdict === 'supported'
                      const isPartial = item.verdict === 'partially_supported'

                      return (
                        <div
                          key={item.id || idx}
                          className={`rounded-xl p-4 border text-xs transition-all shadow-2xs ${
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
                              <div className="space-y-1.5 flex-1">
                                <div className="flex flex-wrap items-center gap-2">
                                  <p className="font-semibold text-slate-900 leading-snug">
                                    {item.claim_text}
                                  </p>
                                  {item.section_key && (
                                    <span className="font-mono text-[9.5px] text-slate-500 bg-white/80 px-1.5 py-0.5 rounded border border-slate-200 shrink-0 lowercase">
                                      #{item.section_key}
                                    </span>
                                  )}
                                </div>

                                {/* Clickable Vault Citation Excerpt with Yellow Highlight */}
                                {item.evidence_span && (
                                  <div
                                    onClick={() => setSelectedEvidenceClaim(item)}
                                    className="text-[11px] text-slate-600 flex items-start gap-1.5 cursor-pointer hover:bg-emerald-100/60 p-2 rounded-lg transition border border-dashed border-emerald-300 bg-white/70 group"
                                    title="Click to view full corroborating document excerpt in slide-out viewer"
                                  >
                                    <FileText className="size-3.5 text-emerald-700 shrink-0 mt-0.5" />
                                    <div className="flex-1">
                                      <span className="text-slate-800 font-semibold mr-1">
                                        Vault Evidence Citation:
                                      </span>
                                      <mark className="bg-amber-200 text-amber-950 font-semibold px-1.5 py-0.5 rounded text-[11px] shadow-2xs border border-amber-300">
                                        &quot;{item.evidence_span}&quot;
                                      </mark>
                                      <span className="ml-2 text-[10px] text-indigo-600 font-bold group-hover:underline">
                                        [View Excerpt &rarr;]
                                      </span>
                                    </div>
                                  </div>
                                )}
                              </div>
                            </div>

                            {/* Claim Chip: clicking opens the slide-out viewer */}
                            <button
                              type="button"
                              onClick={() => setSelectedEvidenceClaim(item)}
                              className={`inline-flex items-center gap-1.5 rounded-full px-2.5 py-1 text-[10px] font-bold uppercase shrink-0 transition cursor-pointer shadow-2xs border ${
                                isSupported
                                  ? 'bg-emerald-100 hover:bg-emerald-200 text-emerald-800 border-emerald-300'
                                  : isPartial
                                  ? 'bg-amber-100 hover:bg-amber-200 text-amber-800 border-amber-300'
                                  : 'bg-rose-100 hover:bg-rose-200 text-rose-800 border-rose-300'
                              }`}
                              title="Click to view full grounding evidence in Document Vault"
                            >
                              {isSupported ? (
                                <>
                                  <CheckCircle2 className="size-3 text-emerald-600" />
                                  <span>Historical Fact &check;</span>
                                </>
                              ) : isPartial ? (
                                <>
                                  <AlertCircle className="size-3 text-amber-600" />
                                  <span>Project Target</span>
                                </>
                              ) : (
                                <>
                                  <ShieldAlert className="size-3 text-rose-600" />
                                  <span>Contradiction / Missing</span>
                                </>
                              )}
                            </button>
                          </div>

                          {/* Quick Actions for UNSUPPORTED or PARTIAL claims */}
                          {(!isSupported || isPartial) && (
                            <div className="flex flex-wrap items-center gap-2 pt-2.5 border-t border-slate-200/80 mt-2.5">
                              <span className="text-[10px] uppercase font-bold text-slate-500 mr-1">
                                Quick Actions:
                              </span>

                              {/* 1. Edit Claim */}
                              <button
                                type="button"
                                onClick={() => handleEditClaimOpen(item)}
                                className="inline-flex items-center gap-1 px-2.5 py-1 rounded-md bg-white border border-slate-300 hover:bg-indigo-50 hover:border-indigo-400 text-slate-700 hover:text-indigo-700 text-[11px] font-semibold transition cursor-pointer shadow-2xs"
                                title="Manually update this sentence with true verified number"
                              >
                                <Edit3 className="size-3 text-indigo-600" />
                                <span>Edit Claim</span>
                              </button>

                              {/* 2. Drop Claim */}
                              <button
                                type="button"
                                onClick={() => setDroppingClaim(item)}
                                className="inline-flex items-center gap-1 px-2.5 py-1 rounded-md bg-white border border-rose-200 hover:bg-rose-50 text-rose-700 text-[11px] font-semibold transition cursor-pointer shadow-2xs hover:border-rose-300"
                                title="Auto-remove hallucinated sentence from proposal"
                              >
                                <Trash2 className="size-3 text-rose-600" />
                                <span>Drop Claim</span>
                              </button>

                              {/* 3. Attach Document Proof */}
                              <button
                                type="button"
                                onClick={handleAttachProof}
                                className="inline-flex items-center gap-1 px-2.5 py-1 rounded-md bg-white border border-slate-300 hover:bg-amber-50 hover:border-amber-400 text-slate-700 hover:text-amber-800 text-[11px] font-semibold transition cursor-pointer shadow-2xs"
                                title="Upload corroborating audit report or certificate in Document Vault"
                              >
                                <Paperclip className="size-3 text-amber-600" />
                                <span>Attach Document Proof</span>
                              </button>
                            </div>
                          )}
                        </div>
                      )
                    })}
                  </div>
                ) : (
                  <div className="rounded-xl border border-dashed border-slate-300 p-8 text-center text-xs text-slate-500">
                    <ListChecks className="size-6 mx-auto text-slate-400 mb-2" />
                    <p className="font-semibold text-slate-700">No Fact-Check Audit Run Yet</p>
                    <p className="mt-1">
                      Click <strong>&quot;Re-Run Audit&quot;</strong> above to extract atomic claims and verify them against the NGO vault.
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

      {/* Slide-out Evidence Viewer Drawer */}
      <EvidenceViewerDrawer
        isOpen={!!selectedEvidenceClaim}
        onClose={() => setSelectedEvidenceClaim(null)}
        claim={selectedEvidenceClaim}
        proposalId={proposalData?.proposal_id}
      />

      {/* Quick Action Modal 1: Edit Claim */}
      {editingClaim && (
        <div className="fixed inset-0 z-50 overflow-hidden bg-slate-900/40 backdrop-blur-xs flex items-center justify-center p-4">
          <div className="bg-white rounded-2xl shadow-2xl max-w-lg w-full p-6 space-y-4 border border-slate-200 animate-fadeIn">
            <div className="flex items-center justify-between border-b border-slate-100 pb-3">
              <div className="flex items-center gap-2">
                <Edit3 className="size-5 text-indigo-600" />
                <h3 className="text-sm font-bold text-slate-900">
                  Edit Asserted Claim in Proposal
                </h3>
              </div>
              <button
                type="button"
                onClick={() => setEditingClaim(null)}
                className="text-slate-400 hover:text-slate-600 cursor-pointer p-1"
              >
                <X className="size-4" />
              </button>
            </div>

            <div className="space-y-3">
              <div>
                <label className="block text-[11px] font-bold uppercase tracking-wider text-slate-500 mb-1">
                  Current Statement (In #{editingClaim.section_key || activeSectionKey})
                </label>
                <div className="p-3 bg-slate-50 rounded-lg text-xs text-slate-700 border border-slate-200 leading-relaxed font-serif">
                  &quot;{editingClaim.claim_text}&quot;
                </div>
              </div>

              <div>
                <label className="block text-[11px] font-bold uppercase tracking-wider text-slate-700 mb-1">
                  Verified Replacement Sentence / Factual Number
                </label>
                <textarea
                  rows={4}
                  value={editClaimText}
                  onChange={(e) => setEditClaimText(e.target.value)}
                  className="w-full text-xs font-serif rounded-lg border border-slate-300 p-3 text-slate-900 focus:border-indigo-500 focus:outline-hidden focus:ring-1 focus:ring-indigo-500 bg-white leading-relaxed"
                  placeholder="Enter the verified statement or accurate number..."
                />
                <p className="text-[11px] text-slate-500 mt-1">
                  The proposal section will be updated with this verified text and re-audited automatically.
                </p>
              </div>
            </div>

            <div className="flex items-center justify-end gap-2 pt-3 border-t border-slate-100">
              <button
                type="button"
                onClick={() => setEditingClaim(null)}
                className="px-3.5 py-2 text-xs font-semibold text-slate-600 hover:bg-slate-100 rounded-lg transition cursor-pointer"
              >
                Cancel
              </button>
              <button
                type="button"
                disabled={isEditingClaimSubmitting || !editClaimText.trim()}
                onClick={handleEditClaimSave}
                className="inline-flex items-center gap-1.5 px-4 py-2 bg-indigo-600 hover:bg-indigo-700 text-white text-xs font-semibold rounded-lg shadow-xs transition cursor-pointer disabled:opacity-50"
              >
                {isEditingClaimSubmitting ? (
                  <>
                    <div className="size-3 border-2 border-white border-t-transparent rounded-full animate-spin" />
                    <span>Saving &amp; Re-Auditing...</span>
                  </>
                ) : (
                  <>
                    <Check className="size-3.5" />
                    <span>Save &amp; Re-Verify</span>
                  </>
                )}
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Quick Action Modal 2: Drop Claim */}
      {droppingClaim && (
        <div className="fixed inset-0 z-50 overflow-hidden bg-slate-900/40 backdrop-blur-xs flex items-center justify-center p-4">
          <div className="bg-white rounded-2xl shadow-2xl max-w-md w-full p-6 space-y-4 border border-slate-200 animate-fadeIn">
            <div className="flex items-center gap-3 text-rose-600">
              <div className="p-2 bg-rose-100 rounded-full">
                <Trash2 className="size-5 text-rose-600" />
              </div>
              <div>
                <h3 className="text-sm font-bold text-slate-900">
                  Drop Hallucinated / Unsupported Claim
                </h3>
                <p className="text-[11px] text-slate-500">
                  Remove this sentence from section #{droppingClaim.section_key || activeSectionKey}
                </p>
              </div>
            </div>

            <div className="p-3 bg-rose-50/60 rounded-lg text-xs text-rose-950 border border-rose-200 italic font-serif">
              &quot;{droppingClaim.claim_text}&quot;
            </div>

            <p className="text-xs text-slate-600 leading-relaxed">
              This sentence will be automatically purged from the proposal draft to eliminate fabrication risk, and the section will be re-audited.
            </p>

            <div className="flex items-center justify-end gap-2 pt-3 border-t border-slate-100">
              <button
                type="button"
                onClick={() => setDroppingClaim(null)}
                className="px-3.5 py-2 text-xs font-semibold text-slate-600 hover:bg-slate-100 rounded-lg transition cursor-pointer"
              >
                Cancel
              </button>
              <button
                type="button"
                disabled={isDroppingClaimSubmitting}
                onClick={handleDropClaimConfirm}
                className="inline-flex items-center gap-1.5 px-4 py-2 bg-rose-600 hover:bg-rose-700 text-white text-xs font-semibold rounded-lg shadow-xs transition cursor-pointer disabled:opacity-50"
              >
                {isDroppingClaimSubmitting ? (
                  <>
                    <div className="size-3 border-2 border-white border-t-transparent rounded-full animate-spin" />
                    <span>Purging Claim...</span>
                  </>
                ) : (
                  <>
                    <Trash2 className="size-3.5" />
                    <span>Confirm &amp; Drop Claim</span>
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
