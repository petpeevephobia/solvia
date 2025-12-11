import { useEffect, useState } from 'react'
import { Routes, Route, Navigate } from 'react-router-dom'
import { useAuthStore } from '@/stores/authStore'
import { authService } from '@/services/auth'

// Layouts
import DashboardLayout from '@/components/layout/DashboardLayout'
import AuthLayout from '@/components/layout/AuthLayout'

// Pages
import LoginPage from '@/features/auth/LoginPage'
import CallbackPage from '@/features/auth/CallbackPage'
import DomainSelectionPage from '@/features/auth/DomainSelectionPage'
import DashboardPage from '@/features/dashboard/DashboardPage'
import AuditHistoryPage from '@/features/audit/AuditHistoryPage'
import AuditDetailPage from '@/features/audit/AuditDetailPage'
import GSCPage from '@/features/gsc/GSCPage'
import ChatPage from '@/features/chat/ChatPage'
import SettingsPage from '@/features/settings/SettingsPage'

// Protected Route wrapper - fetches user data if missing
function ProtectedRoute({ children }: { children: React.ReactNode }) {
  const { isAuthenticated, user, setUser } = useAuthStore()
  const [isLoading, setIsLoading] = useState(!user && isAuthenticated)

  useEffect(() => {
    // Fetch user data if authenticated but user is missing
    if (isAuthenticated && !user) {
      authService.getCurrentUser()
        .then(userData => {
          setUser(userData)
        })
        .catch(() => {
          // Token might be invalid, logout
          useAuthStore.getState().logout()
        })
        .finally(() => {
          setIsLoading(false)
        })
    }
  }, [isAuthenticated, user, setUser])

  if (!isAuthenticated) {
    return <Navigate to="/login" replace />
  }

  if (isLoading) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-gray-50">
        <div className="animate-spin h-8 w-8 border-4 border-primary-600 border-t-transparent rounded-full"></div>
      </div>
    )
  }

  return <>{children}</>
}

function App() {
  return (
    <Routes>
      {/* Auth routes */}
      <Route element={<AuthLayout />}>
        <Route path="/login" element={<LoginPage />} />
        <Route path="/auth/callback" element={<CallbackPage />} />
      </Route>

      {/* Domain selection (protected but separate from dashboard layout) */}
      <Route
        path="/domain-selection"
        element={
          <ProtectedRoute>
            <DomainSelectionPage />
          </ProtectedRoute>
        }
      />

      {/* Protected dashboard routes */}
      <Route
        element={
          <ProtectedRoute>
            <DashboardLayout />
          </ProtectedRoute>
        }
      >
        <Route path="/" element={<Navigate to="/dashboard" replace />} />
        <Route path="/dashboard" element={<DashboardPage />} />
        <Route path="/audit" element={<AuditHistoryPage />} />
        <Route path="/audit/:id" element={<AuditDetailPage />} />
        <Route path="/gsc" element={<GSCPage />} />
        <Route path="/chat" element={<ChatPage />} />
        <Route path="/settings" element={<SettingsPage />} />
      </Route>

      {/* Catch all */}
      <Route path="*" element={<Navigate to="/dashboard" replace />} />
    </Routes>
  )
}

export default App
