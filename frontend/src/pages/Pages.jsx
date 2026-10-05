import React, { lazy } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { useApp } from '../context/AppContext'
import { PipelineNav } from '../components/PipelineStepper'
import { GateCard, gatePrimary, isVerified } from '../components/RouteGuards'
import VerificationPanel from '../components/VerificationPanel'

const NgoRegisterWizard = lazy(() => import('../components/NgoRegisterWizard'))
const DocumentVault = lazy(() => import('../components/DocumentVault'))
const GrantDiscoveryCard = lazy(() => import('../components/GrantDiscoveryCard'))
const ProposalWorkspace = lazy(() => import('../components/ProposalWorkspace'))
const NGOProfileCard = lazy(() => import('../components/NGOProfileCard'))

export function RegisterPage() {
    const navigate = useNavigate()
    const { reloadProfiles } = useApp()
    const done = async () => {
        try {
            await reloadProfiles()
        } catch (err) {
            console.error('Failed to load profile after registration:', err)
        }
        navigate('/vault')
    }
    return <NgoRegisterWizard onComplete={done} onCancel={() => navigate('/vault')} />
}

export function VaultPage() {
    const { activeProfile, setDocCount } = useApp()
    return (
        <>
            {activeProfile && !isVerified(activeProfile) && (
                <div className="mb-6"><VerificationPanel profile={activeProfile} /></div>
            )}
            <DocumentVault
                key={activeProfile?.id}
                ngoId={activeProfile?.id}
                onDocumentCountChange={(c) => setDocCount(c)}
            />
            <PipelineNav />
        </>
    )
}

export function GrantsPage() {
    const navigate = useNavigate()
    const {
        activeProfile, activeGrant, setActiveGrant, setDiscoveredGrants,
        selectGrant, selectBatch, discoveryCache, setDiscoveryCache,
    } = useApp()

    return (
        <>
            <GrantDiscoveryCard
                key={activeProfile?.id}
                ngoId={activeProfile?.id}
                ngoProfile={activeProfile}
                onDraftProposal={(grant) => {
                    selectGrant(grant)
                    navigate('/workspace')
                }}
                onBatchDraft={(grants) => {
                    if (grants && grants.length > 0) {
                        selectBatch(grants)
                        navigate('/workspace')
                    }
                }}
                onResultsLoaded={(grants) => {
                    setDiscoveredGrants(grants)
                    if (!activeGrant && grants.length > 0) setActiveGrant(grants[0])
                }}
                cache={discoveryCache?.ngoId === activeProfile?.id ? discoveryCache : null}
                onCacheChange={(c) => setDiscoveryCache({ ...c, ngoId: activeProfile?.id })}
            />
            <PipelineNav />
        </>
    )
}

export function WorkspacePage({ stage }) {
    const { activeProfile, activeGrant, setActiveGrant, batchGrants, discoveredGrants, proposalCache } = useApp()
    const isExport = stage === 'export'

    // /export has nothing to show until a proposal exists in this session
    if (isExport && !proposalCache.current?.proposalData) {
        return (
            <>
                <GateCard
                    title="No proposal to audit yet"
                    body="Draft a proposal in the Proposal Studio first, then come back to audit and export it."
                >
                    <Link to="/workspace" className={gatePrimary}>Go to Proposal Studio</Link>
                </GateCard>
                <PipelineNav />
            </>
        )
    }

    return (
        <>
            <ProposalWorkspace
                key={activeProfile?.id}
                activeNgo={activeProfile}
                activeGrant={activeGrant}
                batchGrants={batchGrants}
                grants={discoveredGrants}
                onSelectGrant={(grant) => setActiveGrant(grant)}
                cache={proposalCache.current?.ngoId === activeProfile?.id ? proposalCache.current : null}
                onCacheChange={(c) => { proposalCache.current = { ...c, ngoId: activeProfile?.id } }}
                viewModeRequest={isExport ? 'audit' : 'editor'}
                exportStage={isExport}
            />
            <PipelineNav />
        </>
    )
}

export function ProfilePage() {
    const { activeProfile, handleProfileSaved } = useApp()
    return (
        <>
            {activeProfile && !isVerified(activeProfile) && (
                <div className="mb-6"><VerificationPanel profile={activeProfile} /></div>
            )}
            <NGOProfileCard
                key={activeProfile?.id}
                currentProfile={activeProfile}
                onProfileSaved={handleProfileSaved}
            />
        </>
    )
}

export function NotFoundPage() {
    return (
        <GateCard title="Page not found" body="That address doesn't exist in GrantSetu.">
            <Link to="/vault" className={gatePrimary}>Back to the pipeline</Link>
        </GateCard>
    )
}
