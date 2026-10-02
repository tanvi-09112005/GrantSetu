import React, { createContext, useContext, useEffect, useState, useRef } from 'react'
import { getHealth, listProfiles, listDocuments } from '../lib/api'
import { supabase } from '../lib/supabase'

const AppContext = createContext(null)

export function useApp() {
    const ctx = useContext(AppContext)
    if (!ctx) throw new Error('useApp must be used inside <AppProvider>')
    return ctx
}

export function AppProvider({ children }) {
    const [user, setUser] = useState(null)
    const [authLoading, setAuthLoading] = useState(Boolean(supabase)) // for route guards later
    const [profilesLoaded, setProfilesLoaded] = useState(false)
    const [health, setHealth] = useState(null)
    const [profiles, setProfiles] = useState([])
    const [activeProfile, setActiveProfile] = useState(null)
    const [docCount, setDocCount] = useState(0)
    const [activeGrant, setActiveGrant] = useState(null)
    const [discoveredGrants, setDiscoveredGrants] = useState([])
    const [batchGrants, setBatchGrants] = useState([])
    const [authModalOpen, setAuthModalOpen] = useState(false)
    const [discoveryCache, setDiscoveryCache] = useState(null)
    const proposalCache = useRef(null)

    // Auth state from Supabase
    useEffect(() => {
        if (!supabase) return
        supabase.auth.getSession().then(({ data }) => {
            if (data?.session?.user) setUser(data.session.user)
            setAuthLoading(false)
        })
        const { data: authListener } = supabase.auth.onAuthStateChange((_event, session) => {
            setUser(session?.user ?? null)
        })
        return () => authListener?.subscription?.unsubscribe()
    }, [])

    // Health
    useEffect(() => {
        getHealth()
            .then(setHealth)
            .catch((err) => console.error('Health check failed:', err))
    }, [])

    // Profiles when user signs in
    useEffect(() => {
        if (!user) {
            setProfiles([])
            setActiveProfile(null)
            setProfilesLoaded(false)
            return
        }
        listProfiles()
            .then((data) => {
                setProfiles(data || [])
                if (data && data.length > 0 && !activeProfile) setActiveProfile(data[0])
            })
            .catch((err) => console.error('Failed to list profiles:', err))
            .finally(() => setProfilesLoaded(true))
    }, [user])

    // Document count for active profile
    useEffect(() => {
        if (activeProfile?.id) {
            listDocuments(activeProfile.id)
                .then((docs) => setDocCount((docs || []).length))
                .catch(() => setDocCount(0))
        }
    }, [activeProfile])

    const selectGrant = (grant) => {
        setActiveGrant(grant)
        setBatchGrants([grant])
    }

    const selectBatch = (grants) => {
        setActiveGrant(grants[0])
        setBatchGrants(grants)
    }

    const reloadProfiles = async () => {
        const data = await listProfiles()
        setProfiles(data || [])
        if (data?.length) setActiveProfile(data[0])
    }

    const handleProfileSaved = (saved) => {
        setActiveProfile(saved)
        listProfiles().then((data) => {
            setProfiles(data || [])
            setActiveProfile(saved)
        })
    }

    const handleSignOut = async () => {
        if (supabase) await supabase.auth.signOut()
        setUser(null)
        setActiveProfile(null)
        setProfiles([])
        setActiveGrant(null)
        setDiscoveredGrants([])
        setBatchGrants([])
        setDiscoveryCache(null)
        proposalCache.current = null
    }

    const value = {
        user, setUser, authLoading, profilesLoaded, health,
        profiles, activeProfile, setActiveProfile,
        docCount, setDocCount,
        activeGrant, setActiveGrant,
        discoveredGrants, setDiscoveredGrants,
        batchGrants,
        selectGrant, selectBatch,
        reloadProfiles, handleProfileSaved, handleSignOut,
        authModalOpen, setAuthModalOpen, discoveryCache, setDiscoveryCache, proposalCache
    }

    return <AppContext.Provider value={value}>{children}</AppContext.Provider>
}