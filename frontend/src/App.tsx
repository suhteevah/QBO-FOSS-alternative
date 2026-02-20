import { Routes, Route, Navigate } from 'react-router-dom'
import { useAuth } from './lib/auth'
import Layout from './components/Layout'
import Login from './pages/Login'
import Register from './pages/Register'
import Dashboard from './pages/Dashboard'
import Transactions from './pages/Transactions'
import Journal from './pages/Journal'
import Accounts from './pages/Accounts'
import Reconciliation from './pages/Reconciliation'
import Reports from './pages/Reports'
import Receipts from './pages/Receipts'
import Periods from './pages/Periods'
import ServerSetup from './pages/ServerSetup'
import ApiKeySetup from './pages/ApiKeySetup'

function PrivateRoute({ children }: { children: React.ReactNode }) {
  const { user, loading, isDesktop, hasServerUrl } = useAuth()
  if (loading) {
    return (
      <div className="min-h-screen flex items-center justify-center">
        <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-brand-600" />
      </div>
    )
  }
  // Desktop mode: redirect to server setup if no server URL configured
  if (isDesktop && !hasServerUrl) return <Navigate to="/server-setup" />
  return user ? <>{children}</> : <Navigate to="/login" />
}

function PublicRoute({ children }: { children: React.ReactNode }) {
  const { user, loading } = useAuth()
  if (loading) {
    return (
      <div className="min-h-screen flex items-center justify-center">
        <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-brand-600" />
      </div>
    )
  }
  return user ? <Navigate to="/" /> : <>{children}</>
}

export default function App() {
  return (
    <Routes>
      {/* Desktop-only: server setup and API key setup */}
      <Route path="/server-setup" element={<ServerSetup />} />
      <Route path="/api-key-setup" element={<ApiKeySetup />} />

      {/* Public routes */}
      <Route path="/login" element={<PublicRoute><Login /></PublicRoute>} />
      <Route path="/register" element={<PublicRoute><Register /></PublicRoute>} />

      {/* Private routes */}
      <Route path="/" element={<PrivateRoute><Layout /></PrivateRoute>}>
        <Route index element={<Dashboard />} />
        <Route path="transactions" element={<Transactions />} />
        <Route path="journal" element={<Journal />} />
        <Route path="accounts" element={<Accounts />} />
        <Route path="reconciliation" element={<Reconciliation />} />
        <Route path="reports" element={<Reports />} />
        <Route path="receipts" element={<Receipts />} />
        <Route path="periods" element={<Periods />} />
      </Route>

      {/* Catch-all */}
      <Route path="*" element={<Navigate to="/" />} />
    </Routes>
  )
}
