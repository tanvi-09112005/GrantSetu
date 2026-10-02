import React from 'react'
import { Navigate, Route, Routes } from 'react-router-dom'
import AppLayout from './layouts/AppLayout'
import { RequireAuth, RequireOrg } from './components/RouteGuards'
import {
    GrantsPage, NotFoundPage, ProfilePage, RegisterPage, VaultPage, WorkspacePage,
} from './pages/Pages'

export default function AppRoutes() {
    return (
        <Routes>
            <Route element={<AppLayout />}>
                <Route index element={<Navigate to="/vault" replace />} />
                <Route path="register" element={<RegisterPage />} />

                <Route element={<RequireAuth />}>
                    <Route path="profile" element={<ProfilePage />} />
                    <Route element={<RequireOrg />}>
                        <Route path="vault" element={<VaultPage />} />
                        <Route path="grants" element={<GrantsPage />} />
                        <Route path="workspace" element={<WorkspacePage stage="workspace" />} />
                        <Route path="export" element={<WorkspacePage stage="export" />} />
                    </Route>
                </Route>

                <Route path="*" element={<NotFoundPage />} />
            </Route>
        </Routes>
    )
}