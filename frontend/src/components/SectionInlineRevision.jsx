import React, { useState, useEffect } from 'react'
import {
  Wand2,
  X,
  Sparkles,
  Check,
  RotateCcw,
  ShieldCheck,
  Columns,
  AlignLeft,
  Edit3,
  AlertCircle,
  TrendingDown,
  DollarSign,
  Users,
  Building,
  CheckCircle2,
} from 'lucide-react'
import { refineSection, applySectionRevision } from '../lib/api'

// Line-by-line LCS diff. Normalises line endings and trailing whitespace
// so invisible differences don't flag unchanged lines as changed.
function computeLineDiff(originalText = '', refinedText = '') {
  const origLines = (originalText || '').replace(/\r\n/g, '\n').split('\n')
  const refLines = (refinedText || '').replace(/\r\n/g, '\n').split('\n')
  const same = (a, b) => a.trimEnd() === b.trimEnd()

  const N = origLines.length
  const M = refLines.length

  const dp = Array.from({ length: N + 1 }, () => new Array(M + 1).fill(0))

  for (let i = 0; i < N; i++) {
    for (let j = 0; j < M; j++) {
      if (same(origLines[i], refLines[j])) {
        dp[i + 1][j + 1] = dp[i][j] + 1
      } else {
        dp[i + 1][j + 1] = Math.max(dp[i + 1][j], dp[i][j + 1])
      }
    }
  }

  let i = N
  let j = M
  const diff = []

  while (i > 0 || j > 0) {
    if (i > 0 && j > 0 && same(origLines[i - 1], refLines[j - 1])) {
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
      diff.unshift({ type: 'added', refLine: refLines[j - 1], refNum: j })
      j--
    } else {
      diff.unshift({ type: 'removed', origLine: origLines[i - 1], origNum: i })
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

// Inline styles so Tailwind purge/theme can never hide the colours
const ROW_STYLE = {
  added: { backgroundColor: '#d1fae5', borderLeft: '4px solid #10b981', color: '#064e3b' },
  removed: { backgroundColor: '#ffe4e6', borderLeft: '4px solid #f43f5e', color: '#881337' },
  unchanged: { borderLeft: '4px solid transparent', color: '#475569' },
  spacer: { backgroundColor: '#f1f5f9', borderLeft: '4px solid transparent' },
}

function DiffRow({ kind, num, sign = '', text, strike = false }) {
  return (
    <div
      style={{
        ...ROW_STYLE[kind],
        display: 'flex',
        gap: 8,
        padding: '4px 10px',
        minHeight: 24,
      }}
    >
      <span
        style={{
          width: 32,
          textAlign: 'right',
          flexShrink: 0,
          opacity: 0.6,
          userSelect: 'none',
        }}
      >
        {kind === 'spacer' ? '' : `${sign}${num ?? ''}`}
      </span>
      <span
        style={{
          flex: 1,
          whiteSpace: 'pre-wrap',
          textDecoration: strike ? 'line-through' : 'none',
        }}
      >
        {kind === 'spacer' ? ' ' : text || ' '}
      </span>
    </div>
  )
}

// Pairs removed/added runs so both columns line up row by row
function toSplitRows(diff) {
  const rows = []
  let i = 0
  while (i < diff.length) {
    if (diff[i].type === 'unchanged') {
      rows.push({ l: diff[i], r: diff[i] })
      i++
      continue
    }
    const rem = []
    const add = []
    while (i < diff.length && diff[i].type !== 'unchanged') {
      if (diff[i].type === 'removed') rem.push(diff[i])
      else add.push(diff[i])
      i++
    }
    for (let k = 0; k < Math.max(rem.length, add.length); k++) {
      rows.push({ l: rem[k] || null, r: add[k] || null })
    }
  }
  return rows
}

export default function SectionInlineRevision({
  proposalId,
  sectionKey,
  sectionTitle,
  currentContent = '',
  onClose,
  onRevisionApplied,
  ngoName = 'NGO',
  grantTitle = 'Grant Opportunity',
}) {
  const [step, setStep] = useState('prompt') // 'prompt' | 'diff'
  const [instruction, setInstruction] = useState('')
  const temperature = 0.2 // fixed (slider removed)
  const [isGenerating, setIsGenerating] = useState(false)
  const [isApplying, setIsApplying] = useState(false)
  const [error, setError] = useState(null)
  const rerunVerification = true // always on (checkbox removed)

  const [candidateText, setCandidateText] = useState('')
  const [originalSnapshot, setOriginalSnapshot] = useState(currentContent || '')
  const [diffViewMode, setDiffViewMode] = useState('split') // 'split' | 'inline' | 'edit'
  const [editedCandidate, setEditedCandidate] = useState('')

  useEffect(() => {
    setOriginalSnapshot(currentContent || '')
  }, [currentContent, sectionKey])

  const isBudgetSection =
    sectionKey?.toLowerCase().includes('budget') || sectionKey?.toLowerCase().includes('financial')
  const isNeedsSection =
    sectionKey?.toLowerCase().includes('need') || sectionKey?.toLowerCase().includes('problem')
  const isInterventionSection =
    sectionKey?.toLowerCase().includes('intervention') ||
    sectionKey?.toLowerCase().includes('method') ||
    sectionKey?.toLowerCase().includes('logframe')

  const presets = [
    ...(isNeedsSection
      ? [
          {
            icon: Users,
            label: "Emphasize rural girls' dropouts & STEM bridge courses",
            desc: 'Focus on secondary dropouts and digital bridge learning.',
            prompt:
              "Refine this problem statement to emphasize rural adolescent girls' secondary school dropouts, early marriage pressures, and lack of digital/STEM bridge learning in aspirational districts.",
          },
        ]
      : []),
    ...(isBudgetSection
      ? [
          {
            icon: TrendingDown,
            label: 'Cut admin & overhead budget by 10%',
            desc: 'Keep admin expenses under the 5% CSR statutory cap.',
            prompt:
              'Recalculate and reduce administrative and institutional overhead costs by exactly 10% across line items to maintain admin expenses strictly under the 5% CSR statutory threshold while preserving direct beneficiary training funds.',
          },
          {
            icon: DollarSign,
            label: 'Convert to itemized 3-tier unit breakdown',
            desc: 'Format into unit quantities, unit rates, and tranches.',
            prompt:
              'Structure the entire budget into clean itemized markdown tables with explicit Unit Quantities, Unit Rates (INR), Quarterly Distribution Tranches, and total sums adhering to CSR standard cost norms.',
          },
        ]
      : []),
    ...(isInterventionSection
      ? [
          {
            icon: CheckCircle2,
            label: 'Add SMART KPIs & quarterly milestone tranches',
            desc: 'Include quantifiable indicators and quarterly deliverables.',
            prompt:
              'Enrich the intervention workflow with quantifiable SMART indicators (e.g. 500 students enrolled, 85% attendance, 40 community mobilizers trained) and structured quarterly milestone deliverables.',
          },
        ]
      : []),
    {
      icon: Building,
      label: 'Align with NITI Aayog Darpan & CSR Schedule VII',
      desc: 'Align strictly with Darpan norms and Schedule VII (Item ii).',
      prompt:
        'Refine the wording to align strictly with NITI Aayog NGO Darpan guidelines and Schedule VII of the Companies Act 2013 (Item ii: Promoting Education and Livelihoods).',
    },
    {
      icon: ShieldCheck,
      label: 'Reinforce community governance & sustainability',
      desc: 'Outline ownership via SMCs, Gram Panchayats, and 3-year handover.',
      prompt:
        'Strengthen the sustainability framework by outlining community-level ownership via School Management Committees (SMCs), Gram Panchayats, and a 3-year phased handover model.',
    },
    {
      icon: Sparkles,
      label: 'Make tone more authoritative and grant-ready',
      desc: 'Executive, data-driven prose without passive boilerplate.',
      prompt:
        'Sharpen the prose to be highly executive, data-driven, and persuasive for institutional evaluation committees, eliminating passive phrasing and generic boilerplate.',
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
        true // previewOnly
      )

      setCandidateText(res.refined_text || '')
      setEditedCandidate(res.refined_text || '')
      setStep('diff')
    } catch (err) {
      console.error('Section refinement failed:', err)
      setError(
        err.response?.data?.detail ||
          'Failed to generate revision. Please check backend connection and retry.'
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
        rerunVerification
      )

      onRevisionApplied?.(updatedProposal, sectionKey, textToApply)
      onClose?.()
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
    <div className="mb-6 rounded-2xl border-2 border-indigo-500/30 bg-white shadow-xl overflow-hidden transition-all duration-300 animate-in fade-in slide-in-from-top-4">
      {/* Header Bar */}
      <div className="bg-slate-900 px-5 py-3.5 text-white flex items-center justify-between border-b border-slate-800">
        <div className="flex items-center gap-2.5">
          <div className="size-8 rounded-lg bg-indigo-500/20 text-indigo-400 border border-indigo-400/30 flex items-center justify-center">
            <Wand2 className="size-4" />
          </div>
          <div>
            <div className="flex items-center gap-2">
              <h3 className="text-xs font-bold text-white tracking-wide uppercase">
                Interactive AI Refiner
              </h3>
              <span className="text-[10px] uppercase font-mono px-2 py-0.5 rounded-full bg-indigo-500/20 text-indigo-300 border border-indigo-400/30 font-semibold">
                In-Place Mode
              </span>
            </div>
            <p className="text-[11px] text-slate-400">
              Refining <strong className="text-slate-200">{sectionTitle}</strong> for{' '}
              <span className="text-indigo-300">{ngoName}</span>
            </p>
          </div>
        </div>

        <div className="flex items-center gap-2">
          {step === 'diff' && (
            <button
              type="button"
              onClick={() => setStep('prompt')}
              className="inline-flex items-center gap-1 text-[11px] px-2.5 py-1 rounded-md text-slate-300 bg-slate-800 hover:bg-slate-700 transition cursor-pointer"
            >
              <RotateCcw className="size-3" />
              Adjust Prompt
            </button>
          )}
          <button
            type="button"
            onClick={onClose}
            className="p-1.5 rounded-lg text-slate-400 hover:text-white hover:bg-slate-800 transition cursor-pointer"
            title="Close revision editor"
          >
            <X className="size-4" />
          </button>
        </div>
      </div>

      {/* Error Alert */}
      {error && (
        <div className="mx-5 mt-4 p-3 bg-rose-50 border border-rose-200 rounded-xl text-xs text-rose-800 flex items-start gap-2">
          <AlertCircle className="size-4 text-rose-600 shrink-0 mt-0.5" />
          <div className="flex-1">{error}</div>
        </div>
      )}

      {/* STEP 1: Prompt Specification */}
      {step === 'prompt' && (
        <div className="p-5 space-y-4">
          <div>
            <label className="text-[11px] font-bold text-slate-700 uppercase tracking-wider flex items-center gap-1.5 mb-2">
              <Sparkles className="size-3.5 text-indigo-600" />
              Recommended AI Enhancement Prompts:
            </label>
            <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-2">
              {presets.map((preset, idx) => {
                const Icon = preset.icon || Sparkles
                const isSelected = instruction === preset.prompt
                return (
                  <button
                    key={idx}
                    type="button"
                    onClick={() => setInstruction(preset.prompt)}
                    className={`text-left p-2.5 rounded-xl border text-xs transition-all cursor-pointer flex items-start gap-2 ${
                      isSelected
                        ? 'bg-indigo-50 border-indigo-400 ring-2 ring-indigo-500/20 text-indigo-950 font-medium shadow-2xs'
                        : 'bg-slate-50/70 hover:bg-indigo-50/50 hover:border-indigo-200 border-slate-200 text-slate-700'
                    }`}
                  >
                    <div className="size-5 rounded-md bg-indigo-100 text-indigo-700 flex items-center justify-center shrink-0 mt-0.5">
                      <Icon className="size-3" />
                    </div>
                    <div className="min-w-0 flex-1">
                      <div className="font-semibold text-slate-900 leading-snug text-[11px]">
                        {preset.label}
                      </div>
                      {preset.desc && (
                        <p className="text-[10px] text-slate-500 mt-0.5 leading-snug">
                          {preset.desc}
                        </p>
                      )}
                    </div>
                  </button>
                )
              })}
            </div>
          </div>

          <div className="space-y-1.5">
            <div className="flex items-center justify-between">
              <label className="text-[11px] font-bold text-slate-700 uppercase tracking-wider">
                Refinement Instructions:
              </label>
              <span className="text-[10px] font-mono text-slate-400">
                {instruction.length} characters
              </span>
            </div>
            <textarea
              rows={3}
              value={instruction}
              onChange={(e) => setInstruction(e.target.value)}
              placeholder="e.g. Highlight rural adolescent girls' dropouts, align with CSR Schedule VII (Item ii), and itemize unit costs..."
              className="w-full text-xs rounded-xl border border-slate-300 p-3 text-slate-900 focus:border-indigo-500 focus:ring-2 focus:ring-indigo-500/20 outline-hidden bg-white shadow-2xs leading-relaxed"
            />
          </div>

          <div className="pt-2 flex flex-col sm:flex-row sm:items-center justify-end gap-3 border-t border-slate-100">
            <div className="flex items-center gap-2 self-end sm:self-auto">
              <button
                type="button"
                onClick={onClose}
                className="px-3 py-1.5 text-xs text-slate-600 hover:text-slate-900 transition cursor-pointer"
              >
                Cancel
              </button>
              <button
                type="button"
                onClick={() => handleGenerateRevision()}
                disabled={isGenerating || !instruction.trim()}
                className="inline-flex items-center gap-1.5 px-4 py-2 bg-indigo-600 hover:bg-indigo-700 text-white text-xs font-semibold rounded-xl shadow-xs transition cursor-pointer disabled:opacity-50"
              >
                {isGenerating ? (
                  <>
                    <div className="size-3.5 border-2 border-white border-t-transparent rounded-full animate-spin" />
                    Generating Candidate Diff...
                  </>
                ) : (
                  <>
                    <Sparkles className="size-3.5" />
                    Generate AI Revision
                  </>
                )}
              </button>
            </div>
          </div>
        </div>
      )}

      {/* STEP 2: In-Place Visual Diff & Review */}
      {step === 'diff' && (
        <div className="p-5 space-y-4">
          {/* Diff Stats & Mode Switcher Bar */}
          <div className="flex flex-wrap items-center justify-between gap-3 bg-slate-50 p-3 rounded-xl border border-slate-200">
            <div className="flex items-center gap-3 text-xs">
              <span className="font-semibold text-slate-800">Visual Diff Audit:</span>
              <span
                style={{ backgroundColor: '#d1fae5', color: '#065f46' }}
                className="inline-flex items-center gap-1 px-2 py-0.5 rounded-md font-mono font-bold text-[11px]"
              >
                +{additions} additions
              </span>
              <span
                style={{ backgroundColor: '#ffe4e6', color: '#9f1239' }}
                className="inline-flex items-center gap-1 px-2 py-0.5 rounded-md font-mono font-bold text-[11px]"
              >
                -{deletions} removals
              </span>
              <span className="text-[11px] font-mono text-slate-500">
                Word Delta: {originalWordCount} →{' '}
                <span className="font-bold text-slate-800">{candidateWordCount}</span> (
                {candidateWordCount - originalWordCount >= 0 ? '+' : ''}
                {candidateWordCount - originalWordCount})
              </span>
            </div>

            <div className="flex items-center gap-1 bg-white p-1 rounded-lg border border-slate-200 text-xs">
              {[
                { id: 'split', label: 'Side-by-Side', Icon: Columns },
                { id: 'inline', label: 'Unified Diff', Icon: AlignLeft },
                { id: 'edit', label: 'Manual Tweak', Icon: Edit3 },
              ].map(({ id, label, Icon }) => (
                <button
                  key={id}
                  type="button"
                  onClick={() => setDiffViewMode(id)}
                  className={`inline-flex items-center gap-1 px-2.5 py-1 rounded-md text-[11px] font-semibold transition cursor-pointer ${
                    diffViewMode === id
                      ? 'bg-indigo-600 text-white shadow-2xs'
                      : 'text-slate-600 hover:text-slate-900 hover:bg-slate-100'
                  }`}
                >
                  <Icon className="size-3" />
                  {label}
                </button>
              ))}
            </div>
          </div>

          {/* VIEW 1: Side-by-Side, rows aligned */}
          {diffViewMode === 'split' && (
            <div className="border border-slate-200 rounded-xl overflow-hidden bg-white font-mono text-xs">
              <div className="grid grid-cols-2 bg-slate-100 border-b border-slate-200 font-sans text-xs font-semibold text-slate-700">
                <div className="px-3.5 py-2 border-r border-slate-200">
                  Original ({originalWordCount} words)
                </div>
                <div className="px-3.5 py-2">AI Refined ({candidateWordCount} words)</div>
              </div>
              <div className="max-h-96 overflow-y-auto">
                {toSplitRows(diff).map((row, idx) => (
                  <div key={idx} className="grid grid-cols-2">
                    <div className="border-r border-slate-200">
                      {row.l ? (
                        <DiffRow
                          kind={row.l.type}
                          num={row.l.origNum}
                          sign={row.l.type === 'removed' ? '-' : ''}
                          text={row.l.origLine}
                          strike={row.l.type === 'removed'}
                        />
                      ) : (
                        <DiffRow kind="spacer" />
                      )}
                    </div>
                    <div>
                      {row.r ? (
                        <DiffRow
                          kind={row.r.type}
                          num={row.r.refNum}
                          sign={row.r.type === 'added' ? '+' : ''}
                          text={row.r.refLine}
                        />
                      ) : (
                        <DiffRow kind="spacer" />
                      )}
                    </div>
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* VIEW 2: Unified Inline Diff */}
          {diffViewMode === 'inline' && (
            <div className="rounded-xl border border-slate-200 overflow-hidden bg-white font-mono text-xs max-h-96 overflow-y-auto shadow-2xs">
              <div className="bg-slate-100 px-3.5 py-2 border-b border-slate-200 text-[11px] font-sans font-semibold text-slate-700 flex items-center justify-between">
                <span>Unified Line-by-Line Changes ({diff.length} lines)</span>
                <div className="flex items-center gap-3 text-[11px]">
                  <span className="inline-flex items-center gap-1 text-emerald-700 font-semibold">
                    <span className="size-2 rounded-full bg-emerald-500" /> Green = Added
                  </span>
                  <span className="inline-flex items-center gap-1 text-rose-700 font-semibold">
                    <span className="size-2 rounded-full bg-rose-500" /> Red = Removed
                  </span>
                </div>
              </div>
              <div>
                {diff.map((item, idx) =>
                  item.type === 'added' ? (
                    <DiffRow key={idx} kind="added" num={item.refNum} sign="+" text={item.refLine} />
                  ) : item.type === 'removed' ? (
                    <DiffRow
                      key={idx}
                      kind="removed"
                      num={item.origNum}
                      sign="-"
                      text={item.origLine}
                      strike
                    />
                  ) : (
                    <DiffRow key={idx} kind="unchanged" num={item.origNum} text={item.origLine} />
                  )
                )}
              </div>
            </div>
          )}

          {/* VIEW 3: Manual Tweak */}
          {diffViewMode === 'edit' && (
            <div className="space-y-1.5">
              <label className="text-[11px] font-semibold text-slate-700 block">
                Edit Candidate Markdown Before Applying:
              </label>
              <textarea
                rows={10}
                value={editedCandidate}
                onChange={(e) => setEditedCandidate(e.target.value)}
                className="w-full text-xs font-mono rounded-xl border border-indigo-200 p-3 text-slate-900 focus:border-indigo-500 focus:ring-1 focus:ring-indigo-500 bg-white"
                placeholder="Adjust refined markdown text..."
              />
            </div>
          )}

          {/* Action Footer */}
          <div className="pt-3 flex flex-col sm:flex-row sm:items-center justify-between gap-3 border-t border-slate-200">
            <div className="text-[11px] text-slate-500 flex items-center gap-1.5">
              <ShieldCheck className="size-4 text-indigo-600" />
              <span>Applying will save to proposal history (v+1) and re-audit section claims.</span>
            </div>

            <div className="flex items-center gap-2 self-end sm:self-auto">
              <button
                type="button"
                onClick={() => setStep('prompt')}
                className="inline-flex items-center gap-1 px-3 py-2 text-xs font-medium text-slate-600 hover:text-slate-900 bg-slate-100 hover:bg-slate-200 rounded-xl transition cursor-pointer"
              >
                <RotateCcw className="size-3.5" />
                Try Another Prompt
              </button>
              <button
                type="button"
                onClick={onClose}
                className="px-3 py-2 text-xs text-slate-600 hover:text-slate-900 transition cursor-pointer"
              >
                Discard
              </button>
              <button
                type="button"
                onClick={handleApplyRevision}
                disabled={isApplying}
                className="inline-flex items-center gap-1.5 px-5 py-2 bg-emerald-600 hover:bg-emerald-700 text-white text-xs font-bold rounded-xl shadow-xs transition cursor-pointer disabled:opacity-50"
              >
                {isApplying ? (
                  <>
                    <div className="size-3.5 border-2 border-white border-t-transparent rounded-full animate-spin" />
                    Auditing &amp; Applying...
                  </>
                ) : (
                  <>
                    <Check className="size-4" />
                    Accept &amp; Apply Revision
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