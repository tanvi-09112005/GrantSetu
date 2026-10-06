import React, { useState, useEffect } from 'react'
import {
  Wand2,
  X,
  Sparkles,
  ArrowRight,
  Check,
  RotateCcw,
  Sliders,
  ShieldCheck,
  Split,
  Columns,
  AlignLeft,
  Edit3,
  AlertCircle,
  FileText,
  DollarSign,
  TrendingDown,
  Users,
  Building,
  CheckCircle2,
  ListFilter,
} from 'lucide-react'
import { refineSection, applySectionRevision } from '../lib/api'

// Computes line-by-line diff for Side-by-Side and Unified Inline Diff
function computeLineDiff(originalText = '', refinedText = '') {
  const origLines = (originalText || '').split('\n')
  const refLines = (refinedText || '').split('\n')

  const N = origLines.length
  const M = refLines.length

  // Standard LCS Dynamic Programming for line alignment
  const dp = Array.from({ length: N + 1 }, () => new Array(M + 1).fill(0))

  for (let i = 0; i < N; i++) {
    for (let j = 0; j < M; j++) {
      if (origLines[i] === refLines[j]) {
        dp[i + 1][j + 1] = dp[i][j] + 1
      } else {
        dp[i + 1][j + 1] = Math.max(dp[i + 1][j], dp[i][j + 1])
      }
    }
  }

  // Backtrack to assemble diff blocks
  let i = N
  let j = M
  const diff = []

  while (i > 0 || j > 0) {
    if (i > 0 && j > 0 && origLines[i - 1] === refLines[j - 1]) {
      diff.unshift({
        type: 'unchanged',
        origLine: origLines[i - 1],
        refLine: refLines[j - 1],
        origNum: i,
        refNum: j,
      })
      i--
      j--
    } else if (j > 0 && (i === 0 || dp[i][j - 1] >= dp[i - 1][j])) {
      diff.unshift({
        type: 'added',
        refLine: refLines[j - 1],
        refNum: j,
      })
      j--
    } else if (i > 0 && (j === 0 || dp[i][j - 1] < dp[i - 1][j])) {
      diff.unshift({
        type: 'removed',
        origLine: origLines[i - 1],
        origNum: i,
      })
      i--
    }
  }

  let additions = 0
  let deletions = 0
  diff.forEach((d) => {
    if (d.type === 'added') additions++
    if (d.type === 'removed') deletions++
  })

  return { diff, additions, deletions }
}

export default function SectionRevisionDrawer({
  isOpen,
  onClose,
  proposalId,
  sectionKey,
  sectionTitle,
  currentContent = '',
  onRevisionApplied,
  ngoName = 'NGO',
  grantTitle = 'Grant Opportunity',
}) {
  const [step, setStep] = useState('prompt') // 'prompt' | 'diff'
  const [instruction, setInstruction] = useState('')
  const [temperature, setTemperature] = useState(0.2)
  const [isGenerating, setIsGenerating] = useState(false)
  const [isApplying, setIsApplying] = useState(false)
  const [error, setError] = useState(null)

  // Candidate refinement result
  const [candidateText, setCandidateText] = useState('')
  const [originalSnapshot, setOriginalSnapshot] = useState('')
  const [diffViewMode, setDiffViewMode] = useState('split') // 'split' | 'inline' | 'edit'
  const [editedCandidate, setEditedCandidate] = useState('')

  useEffect(() => {
    if (isOpen) {
      setStep('prompt')
      setInstruction('')
      setError(null)
      setOriginalSnapshot(currentContent || '')
      setCandidateText('')
      setEditedCandidate('')
    }
  }, [isOpen, currentContent, sectionKey])

  if (!isOpen) return null

  const isBudgetSection = sectionKey?.toLowerCase().includes('budget') || sectionKey?.toLowerCase().includes('financial')
  const isNeedsSection = sectionKey?.toLowerCase().includes('need') || sectionKey?.toLowerCase().includes('problem')
  const isInterventionSection = sectionKey?.toLowerCase().includes('intervention') || sectionKey?.toLowerCase().includes('method') || sectionKey?.toLowerCase().includes('logframe')

  // Smart Context-Aware Presets
  const presets = [
    ...(isNeedsSection
      ? [
          {
            icon: Users,
            label: "Emphasize rural girls' dropouts & STEM bridge courses",
            desc: 'Focus on secondary dropouts and digital bridge learning.',
            prompt: "Refine this problem statement to emphasize rural adolescent girls' secondary school dropouts, early marriage pressures, and lack of digital/STEM bridge learning in aspirational districts.",
          },
        ]
      : []),
    ...(isBudgetSection
      ? [
          {
            icon: TrendingDown,
            label: 'Cut admin & overhead budget by 10%',
            desc: 'Keep admin expenses under the 5% CSR statutory cap.',
            prompt: 'Recalculate and reduce administrative and institutional overhead costs by exactly 10% across line items to maintain admin expenses strictly under the 5% CSR statutory threshold while preserving direct beneficiary training funds.',
          },
          {
            icon: DollarSign,
            label: 'Convert to itemized 3-tier unit breakdown',
            desc: 'Format into unit quantities, unit rates, and tranches.',
            prompt: 'Structure the entire budget into clean itemized markdown tables with explicit Unit Quantities, Unit Rates (INR), Quarterly Distribution Tranches, and total sums adhering to CSR standard cost norms.',
          },
        ]
      : []),
    ...(isInterventionSection
      ? [
          {
            icon: CheckCircle2,
            label: 'Add SMART KPIs & quarterly milestone tranches',
            desc: 'Include quantifiable indicators and quarterly deliverables.',
            prompt: 'Enrich the intervention workflow with quantifiable SMART indicators (e.g. 500 students enrolled, 85% attendance, 40 community mobilizers trained) and structured quarterly milestone deliverables.',
          },
        ]
      : []),
    {
      icon: Building,
      label: 'Align with NITI Aayog Darpan & CSR Schedule VII',
      desc: 'Align strictly with Darpan norms and Schedule VII (Item ii).',
      prompt: 'Refine the wording to align strictly with NITI Aayog NGO Darpan guidelines and Schedule VII of the Companies Act 2013 (Item ii: Promoting Education and Livelihoods).',
    },
    {
      icon: ShieldCheck,
      label: 'Reinforce community governance & sustainability',
      desc: 'Outline ownership via SMCs, Gram Panchayats, and 3-year handover.',
      prompt: 'Strengthen the sustainability framework by outlining community-level ownership via School Management Committees (SMCs), Gram Panchayats, and a 3-year phased handover model.',
    },
    {
      icon: Sparkles,
      label: 'Make tone more authoritative and grant-ready',
      desc: 'Executive, data-driven prose without passive boilerplate.',
      prompt: 'Sharpen the prose to be highly executive, data-driven, and persuasive for institutional evaluation committees, eliminating passive phrasing and generic boilerplate.',
    },
  ]

  const handleGenerateRevision = async (customPrompt) => {
    const promptToUse = (customPrompt || instruction).trim()
    if (!promptToUse || !proposalId || !sectionKey) return

    setIsGenerating(true)
    setError(null)

    try {
      const res = await refineSection(
        proposalId,
        sectionKey,
        promptToUse,
        originalSnapshot,
        temperature,
        true // previewOnly = true
      )

      setCandidateText(res.refined_text || '')
      setEditedCandidate(res.refined_text || '')
      setStep('diff')
    } catch (err) {
      console.error('Section refinement failed:', err)
      setError(
        err.response?.data?.detail ||
          'Failed to generate revision. Please verify backend connection and try again.'
      )
    } finally {
      setIsGenerating(false)
    }
  }

  const handleApplyRevision = async () => {
    const textToApply = editedCandidate.trim() || candidateText.trim()
    if (!textToApply || !proposalId || !sectionKey) return

    setIsApplying(true)
    setError(null)

    try {
      const updatedProposal = await applySectionRevision(
        proposalId,
        sectionKey,
        textToApply,
        true // rerun targeted verification
      )

      onRevisionApplied?.(updatedProposal, sectionKey, textToApply)
      onClose()
    } catch (err) {
      console.error('Applying section revision failed:', err)
      setError(
        err.response?.data?.detail ||
          'Failed to apply revision and run targeted verification. Please try again.'
      )
    } finally {
      setIsApplying(false)
    }
  }

  const { diff, additions, deletions } = computeLineDiff(originalSnapshot, candidateText)

  const originalWordCount = (originalSnapshot || '').trim().split(/\s+/).filter(Boolean).length
  const candidateWordCount = (candidateText || '').trim().split(/\s+/).filter(Boolean).length

  return (
    <div className="fixed inset-0 z-50 overflow-hidden no-print">
      {/* Backdrop */}
      <div
        onClick={onClose}
        className="fixed inset-0 bg-slate-900/60 backdrop-blur-xs transition-opacity duration-300 animate-in fade-in"
      />

      {/* Slide-Over Drawer Container */}
      <div className="fixed inset-y-0 right-0 max-w-full flex pl-10">
        <div className="w-screen max-w-3xl bg-white shadow-2xl border-l border-slate-200 flex flex-col transform transition-transform duration-300 ease-in-out animate-in slide-in-from-right">
          {/* Drawer Header */}
          <div className="px-6 py-4 bg-slate-900 text-white flex items-center justify-between border-b border-slate-800 shrink-0">
            <div className="flex items-center gap-3">
              <div className="size-9 rounded-xl bg-indigo-500/20 text-indigo-400 border border-indigo-400/30 flex items-center justify-center">
                <Wand2 className="size-4" />
              </div>
              <div>
                <div className="flex items-center gap-2">
                  <h2 className="text-sm font-bold tracking-tight">Interactive Revision Agent</h2>
                  <span className="text-[10px] uppercase font-mono px-2 py-0.5 rounded-full bg-indigo-500/20 text-indigo-300 border border-indigo-400/30 font-semibold">
                    Human-in-the-Loop
                  </span>
                </div>
                <p className="text-xs text-slate-400 mt-0.5">
                  Targeting <strong className="text-slate-200 font-semibold">{sectionTitle}</strong> for{' '}
                  <span className="text-indigo-300">{ngoName}</span>
                </p>
              </div>
            </div>

            <button
              type="button"
              onClick={onClose}
              className="rounded-lg p-1.5 text-slate-400 hover:text-white hover:bg-slate-800 transition cursor-pointer"
            >
              <X className="size-5" />
            </button>
          </div>

          {/* Stepper / Mode Indicator */}
          <div className="bg-slate-100 px-6 py-2.5 border-b border-slate-200 flex items-center justify-between text-xs text-slate-600 shrink-0">
            <div className="flex items-center gap-2">
              <span
                className={`inline-flex items-center gap-1.5 font-semibold px-2.5 py-1 rounded-md transition ${
                  step === 'prompt' ? 'bg-indigo-600 text-white shadow-xs' : 'bg-white text-slate-700 border border-slate-200'
                }`}
              >
                1. Specify Revision Goal
              </span>
              <ArrowRight className="size-3.5 text-slate-400" />
              <span
                className={`inline-flex items-center gap-1.5 font-semibold px-2.5 py-1 rounded-md transition ${
                  step === 'diff' ? 'bg-indigo-600 text-white shadow-xs' : 'bg-white text-slate-500 border border-slate-200 opacity-80'
                }`}
              >
                2. Visual Diff &amp; Targeted Audit
              </span>
            </div>

            <div className="text-[11px] font-mono text-slate-500">
              Section: <span className="font-semibold text-slate-800">{sectionKey}</span>
            </div>
          </div>

          {/* Error Banner */}
          {error && (
            <div className="mx-6 mt-4 p-3 bg-rose-50 border border-rose-200 rounded-xl text-xs text-rose-800 flex items-start gap-2 shrink-0">
              <AlertCircle className="size-4 text-rose-600 shrink-0 mt-0.5" />
              <div className="flex-1">{error}</div>
            </div>
          )}

          {/* Main Body */}
          <div className="flex-1 overflow-y-auto p-6 space-y-6">
            {/* STEP 1: Prompt & Instructions */}
            {step === 'prompt' && (
              <div className="space-y-6">
                {/* Current Content Summary Box */}
                <div className="rounded-xl border border-slate-200 bg-slate-50/80 p-4 space-y-2">
                  <div className="flex items-center justify-between text-xs text-slate-700 font-semibold">
                    <span className="flex items-center gap-1.5">
                      <FileText className="size-3.5 text-slate-500" />
                      Current Section Draft ({originalWordCount} words)
                    </span>
                    <span className="text-[11px] text-slate-500 font-normal">
                      Will be preserved until you confirm diff
                    </span>
                  </div>
                  <div className="text-xs text-slate-600 max-h-28 overflow-y-auto font-mono bg-white p-3 rounded-lg border border-slate-200/80 whitespace-pre-wrap leading-relaxed">
                    {originalSnapshot || '[Section is currently empty]'}
                  </div>
                </div>

                {/* Preset Prompt Cards */}
                <div className="space-y-2.5">
                  <label className="text-xs font-bold text-slate-800 uppercase tracking-wider flex items-center gap-1.5">
                    <Sparkles className="size-3.5 text-indigo-600" />
                    Recommended AI Enhancement Prompts:
                  </label>
                  <div className="grid grid-cols-1 sm:grid-cols-2 gap-2.5">
                    {presets.map((preset, idx) => {
                      const Icon = preset.icon || Sparkles
                      return (
                        <button
                          key={idx}
                          type="button"
                          onClick={() => {
                            setInstruction(preset.prompt)
                          }}
                          className={`text-left p-3 rounded-xl border text-xs transition-all cursor-pointer flex items-start gap-2.5 ${
                            instruction === preset.prompt
                              ? 'bg-indigo-50/90 border-indigo-300 ring-2 ring-indigo-500/20 text-indigo-950 font-medium'
                              : 'bg-white hover:bg-slate-50 border-slate-200 text-slate-700'
                          }`}
                        >
                          <div className="size-6 rounded-lg bg-indigo-50 text-indigo-600 flex items-center justify-center shrink-0 mt-0.5">
                            <Icon className="size-3.5" />
                          </div>
                          <div className="min-w-0 flex-1">
                            <div className="font-semibold text-slate-900 leading-snug">{preset.label}</div>
                            {preset.desc && (
                              <p className="text-[11px] text-slate-500 mt-0.5 leading-snug">
                                {preset.desc}
                              </p>
                            )}
                          </div>
                        </button>
                      )
                    })}
                  </div>
                </div>

                {/* Custom Instruction Box */}
                <div className="space-y-2">
                  <div className="flex items-center justify-between">
                    <label className="text-xs font-bold text-slate-800 uppercase tracking-wider">
                      Custom Refinement Instructions:
                    </label>
                    <span className="text-[11px] text-slate-400 font-mono">
                      {instruction.length} characters
                    </span>
                  </div>
                  <textarea
                    rows={4}
                    value={instruction}
                    onChange={(e) => setInstruction(e.target.value)}
                    placeholder="e.g. Emphasize rural girls' dropouts, align with Schedule VII, and recalculate administrative overhead to not exceed 5% of total grant request..."
                    className="w-full text-xs rounded-xl border border-slate-300 p-3.5 text-slate-900 focus:border-indigo-500 focus:ring-2 focus:ring-indigo-500/20 outline-hidden bg-white shadow-2xs leading-relaxed"
                  />
                </div>

                {/* Model Controls */}
                <div className="rounded-xl border border-slate-200 bg-slate-50/50 p-4 flex flex-col sm:flex-row sm:items-center justify-between gap-4">
                  <div>
                    <div className="text-xs font-semibold text-slate-800 flex items-center gap-1.5">
                      <Sliders className="size-3.5 text-slate-600" />
                      Auditing Rigor &amp; Creativity
                    </div>
                    <p className="text-[11px] text-slate-500 mt-0.5">
                      Lower temperature adheres strictly to uploaded document numbers and statutory rules.
                    </p>
                  </div>

                  <div className="flex items-center gap-3 shrink-0">
                    <input
                      type="range"
                      min="0.0"
                      max="0.7"
                      step="0.1"
                      value={temperature}
                      onChange={(e) => setTemperature(parseFloat(e.target.value))}
                      className="w-24 accent-indigo-600 cursor-pointer"
                    />
                    <span className="text-xs font-mono font-bold bg-white border border-slate-200 px-2 py-1 rounded text-slate-700">
                      {temperature <= 0.1 ? 'Strict (0.1)' : temperature <= 0.3 ? 'Balanced (0.2)' : 'Creative (0.5)'}
                    </span>
                  </div>
                </div>
              </div>
            )}

            {/* STEP 2: Side-by-Side Visual Diff */}
            {step === 'diff' && (
              <div className="space-y-4">
                {/* Diff Summary Bar */}
                <div className="rounded-xl border border-slate-200 bg-slate-50 p-3.5 flex flex-wrap items-center justify-between gap-3 shadow-2xs">
                  <div className="flex items-center gap-3 text-xs">
                    <span className="font-bold text-slate-800">Visual Diff Audit:</span>
                    <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-md bg-emerald-100 text-emerald-800 font-semibold font-mono text-[11px]">
                      +{additions} lines added
                    </span>
                    <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-md bg-rose-100 text-rose-800 font-semibold font-mono text-[11px]">
                      -{deletions} lines removed
                    </span>
                    <span className="text-slate-500 font-mono text-[11px]">
                      ({originalWordCount} → {candidateWordCount} words)
                    </span>
                  </div>

                  {/* View Mode Toggle */}
                  <div className="flex items-center bg-slate-200/80 p-0.5 rounded-lg text-xs font-semibold">
                    <button
                      type="button"
                      onClick={() => setDiffViewMode('split')}
                      className={`px-2.5 py-1 rounded-md transition cursor-pointer flex items-center gap-1 ${
                        diffViewMode === 'split' ? 'bg-white text-indigo-700 shadow-2xs' : 'text-slate-600'
                      }`}
                    >
                      <Split className="size-3.5" />
                      Side-by-Side
                    </button>
                    <button
                      type="button"
                      onClick={() => setDiffViewMode('inline')}
                      className={`px-2.5 py-1 rounded-md transition cursor-pointer flex items-center gap-1 ${
                        diffViewMode === 'inline' ? 'bg-white text-indigo-700 shadow-2xs' : 'text-slate-600'
                      }`}
                    >
                      <AlignLeft className="size-3.5" />
                      Unified Inline
                    </button>
                    <button
                      type="button"
                      onClick={() => setDiffViewMode('edit')}
                      className={`px-2.5 py-1 rounded-md transition cursor-pointer flex items-center gap-1 ${
                        diffViewMode === 'edit' ? 'bg-white text-indigo-700 shadow-2xs' : 'text-slate-600'
                      }`}
                    >
                      <Edit3 className="size-3.5" />
                      Manual Tweak
                    </button>
                  </div>
                </div>

                {/* Targeted Verification Banner */}
                <div className="rounded-xl border border-emerald-200 bg-emerald-50/70 p-3 flex items-center gap-2.5 text-xs text-emerald-900">
                  <ShieldCheck className="size-4 text-emerald-600 shrink-0" />
                  <div>
                    <strong className="font-bold">Targeted Verification Loop:</strong> Confirming this revision will
                    automatically re-verify <em>only this section</em> against your NGO vault and update the proposal's
                    overall fabrication rate in real time without wasting LLM quota on other sections.
                  </div>
                </div>

                {/* Diff Renderers */}
                {diffViewMode === 'split' && (
                  <div className="grid grid-cols-1 md:grid-cols-2 gap-3 border border-slate-200 rounded-xl overflow-hidden bg-slate-100">
                    {/* Left Column: Original */}
                    <div className="bg-white flex flex-col border-r border-slate-200">
                      <div className="px-3.5 py-2 bg-slate-50 border-b border-slate-200 text-[11px] font-bold text-slate-600 uppercase tracking-wider flex items-center justify-between">
                        <span>Original Version</span>
                        <span className="font-mono font-normal text-slate-400">{originalWordCount} words</span>
                      </div>
                      <div className="p-3.5 text-xs font-mono whitespace-pre-wrap leading-relaxed space-y-1 overflow-y-auto max-h-[420px] text-slate-800">
                        {diff.map((item, idx) => {
                          if (item.type === 'added') return null
                          if (item.type === 'removed') {
                            return (
                              <div
                                key={idx}
                                className="bg-rose-50 text-rose-900 px-2 py-0.5 rounded border border-rose-200/70 line-through opacity-85"
                              >
                                {item.origLine || ' '}
                              </div>
                            )
                          }
                          return (
                            <div key={idx} className="text-slate-700 py-0.5">
                              {item.origLine || ' '}
                            </div>
                          )
                        })}
                      </div>
                    </div>

                    {/* Right Column: AI Refined */}
                    <div className="bg-white flex flex-col">
                      <div className="px-3.5 py-2 bg-indigo-50/60 border-b border-indigo-100 text-[11px] font-bold text-indigo-900 uppercase tracking-wider flex items-center justify-between">
                        <span className="flex items-center gap-1.5">
                          <Sparkles className="size-3 text-indigo-600" />
                          AI Refined Version
                        </span>
                        <span className="font-mono font-normal text-indigo-700">{candidateWordCount} words</span>
                      </div>
                      <div className="p-3.5 text-xs font-mono whitespace-pre-wrap leading-relaxed space-y-1 overflow-y-auto max-h-[420px] text-slate-900">
                        {diff.map((item, idx) => {
                          if (item.type === 'removed') return null
                          if (item.type === 'added') {
                            return (
                              <div
                                key={idx}
                                className="bg-emerald-50 text-emerald-950 font-medium px-2 py-0.5 rounded border border-emerald-200/80 shadow-2xs"
                              >
                                {item.refLine || ' '}
                              </div>
                            )
                          }
                          return (
                            <div key={idx} className="text-slate-700 py-0.5">
                              {item.refLine || ' '}
                            </div>
                          )
                        })}
                      </div>
                    </div>
                  </div>
                )}

                {diffViewMode === 'inline' && (
                  <div className="border border-slate-200 rounded-xl overflow-hidden bg-white">
                    <div className="px-3.5 py-2 bg-slate-50 border-b border-slate-200 text-[11px] font-bold text-slate-600 uppercase tracking-wider">
                      Unified Inline Diff View
                    </div>
                    <div className="p-3.5 text-xs font-mono whitespace-pre-wrap leading-relaxed space-y-1 overflow-y-auto max-h-[420px]">
                      {diff.map((item, idx) => {
                        if (item.type === 'removed') {
                          return (
                            <div
                              key={idx}
                              className="bg-rose-50 text-rose-900 px-2 py-0.5 rounded border-l-2 border-rose-500 line-through opacity-80 flex items-start gap-2"
                            >
                              <span className="text-rose-500 font-bold select-none">-</span>
                              <span>{item.origLine}</span>
                            </div>
                          )
                        }
                        if (item.type === 'added') {
                          return (
                            <div
                              key={idx}
                              className="bg-emerald-50 text-emerald-950 font-medium px-2 py-0.5 rounded border-l-2 border-emerald-500 flex items-start gap-2"
                            >
                              <span className="text-emerald-600 font-bold select-none">+</span>
                              <span>{item.refLine}</span>
                            </div>
                          )
                        }
                        return (
                          <div key={idx} className="text-slate-700 py-0.5 pl-5">
                            {item.origLine}
                          </div>
                        )
                      })}
                    </div>
                  </div>
                )}

                {diffViewMode === 'edit' && (
                  <div className="space-y-2">
                    <div className="flex items-center justify-between text-xs text-slate-700 font-semibold">
                      <span>Fine-Tune Refined Markdown Before Applying:</span>
                      <span className="font-mono text-slate-400">{editedCandidate.length} chars</span>
                    </div>
                    <textarea
                      rows={12}
                      value={editedCandidate}
                      onChange={(e) => setEditedCandidate(e.target.value)}
                      className="w-full text-xs font-mono rounded-xl border border-slate-300 p-4 text-slate-900 focus:border-indigo-500 focus:ring-2 focus:ring-indigo-500/20 outline-hidden bg-white shadow-2xs leading-relaxed"
                    />
                  </div>
                )}
              </div>
            )}
          </div>

          {/* Drawer Footer Actions */}
          <div className="px-6 py-4 bg-slate-50 border-t border-slate-200 flex items-center justify-between gap-3 shrink-0">
            {step === 'prompt' ? (
              <>
                <button
                  type="button"
                  onClick={onClose}
                  className="px-4 py-2 text-xs font-semibold text-slate-600 hover:text-slate-800 rounded-lg hover:bg-slate-200 transition cursor-pointer"
                >
                  Cancel
                </button>

                <button
                  type="button"
                  disabled={isGenerating || !instruction.trim()}
                  onClick={() => handleGenerateRevision()}
                  className="inline-flex items-center gap-2 px-5 py-2.5 bg-indigo-600 hover:bg-indigo-700 text-white text-xs font-semibold rounded-xl shadow-xs transition cursor-pointer disabled:opacity-50 disabled:cursor-not-allowed"
                >
                  {isGenerating ? (
                    <>
                      <div className="size-3.5 border-2 border-white/30 border-t-white rounded-full animate-spin" />
                      Refining Section with AI...
                    </>
                  ) : (
                    <>
                      <Wand2 className="size-3.5" />
                      Generate AI Revision Candidate
                    </>
                  )}
                </button>
              </>
            ) : (
              <>
                <button
                  type="button"
                  onClick={() => setStep('prompt')}
                  className="inline-flex items-center gap-1.5 px-3.5 py-2 text-xs font-semibold text-slate-700 bg-white border border-slate-300 hover:bg-slate-100 rounded-lg transition cursor-pointer shadow-2xs"
                >
                  <RotateCcw className="size-3.5 text-slate-500" />
                  Try Different Prompt
                </button>

                <div className="flex items-center gap-2">
                  <button
                    type="button"
                    onClick={onClose}
                    className="px-4 py-2 text-xs font-semibold text-slate-600 hover:text-slate-800 rounded-lg hover:bg-slate-200 transition cursor-pointer"
                  >
                    Discard
                  </button>

                  <button
                    type="button"
                    disabled={isApplying}
                    onClick={handleApplyRevision}
                    className="inline-flex items-center gap-2 px-5 py-2.5 bg-emerald-600 hover:bg-emerald-700 text-white text-xs font-semibold rounded-xl shadow-xs transition cursor-pointer disabled:opacity-50"
                  >
                    {isApplying ? (
                      <>
                        <div className="size-3.5 border-2 border-white/30 border-t-white rounded-full animate-spin" />
                        Auditing &amp; Applying...
                      </>
                    ) : (
                      <>
                        <Check className="size-4" />
                        Accept &amp; Apply Revision (Targeted Audit)
                      </>
                    )}
                  </button>
                </div>
              </>
            )}
          </div>
        </div>
      </div>
    </div>
  )
}
