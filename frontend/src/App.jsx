import React from 'react'
import { AppProvider } from './context/AppContext'
import AppRoutes from './routes'

export default function App() {
  return (
    <AppProvider>
      <AppRoutes />
    </AppProvider>
  )
}