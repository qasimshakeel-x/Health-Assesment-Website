import React, { useEffect } from 'react'
import { Routes, Route, Navigate, useLocation } from 'react-router-dom'
import { AuthProvider, useAuth } from './context/AuthContext'
import { ThemeProvider } from './context/ThemeContext'
import Navbar from './components/Navbar'
import ScrollBackground from './components/ScrollBackground'
import Login from './pages/Login'
import Register from './pages/Register'
import HealthForm from './pages/HealthForm'
import Dashboard from './pages/Dashboard'
import SHAPDashboard from './pages/SHAPDashboard'
import Simulator from './pages/Simulator'
import DietChat from './pages/DietChat'
import Reports from './pages/Reports'
import Admin from './pages/Admin'
import NotFound from './pages/NotFound'

function ProtectedRoute({ children }) {
  const { user, loading } = useAuth()
  if (loading) return null
  return user ? children : <Navigate to="/login" />
}

// Role-based guard — admin/manager-only pages (08-FRONTEND-UI-SPEC §rbac).
function RoleRoute({ roles, children }) {
  const { user, loading } = useAuth()
  if (loading) return null
  if (!user) return <Navigate to="/login" />
  return roles.includes(user.role) ? children : <Navigate to="/dashboard" />
}

function PublicRoute({ children }) {
  const { user, loading } = useAuth()
  if (loading) return null
  return user ? <Navigate to="/" /> : children
}

function AppRoutes() {
  const location = useLocation()
  // Har route change pe page top se start ho (SPA scroll position persist na ho)
  useEffect(() => { window.scrollTo(0, 0) }, [location.pathname])
  const isAuthPage = ['/login', '/register'].includes(location.pathname)

  return (
    <>
      <ScrollBackground enabled={true} />
      <Navbar />
      <main className={`relative z-10 container mx-auto px-4 py-6 max-w-7xl${isAuthPage ? ' min-h-screen' : ''}`}>
        <Routes>
          <Route path="/login" element={<PublicRoute><Login /></PublicRoute>} />
          <Route path="/register" element={<PublicRoute><Register /></PublicRoute>} />
          <Route path="/" element={
            <ProtectedRoute><HealthForm /></ProtectedRoute>
          } />
          <Route path="/dashboard" element={
            <ProtectedRoute><Dashboard /></ProtectedRoute>
          } />
          <Route path="/shap/:predictionId" element={
            <ProtectedRoute><SHAPDashboard /></ProtectedRoute>
          } />
          <Route path="/simulator" element={
            <ProtectedRoute><Simulator /></ProtectedRoute>
          } />
          <Route path="/chat" element={
            <ProtectedRoute><DietChat /></ProtectedRoute>
          } />
          <Route path="/reports" element={
            <ProtectedRoute><Reports /></ProtectedRoute>
          } />
          <Route path="/admin" element={
            <RoleRoute roles={['admin', 'manager']}><Admin /></RoleRoute>
          } />
          <Route path="*" element={<NotFound />} />
        </Routes>
      </main>
    </>
  )
}

export default function App() {
  return (
    <ThemeProvider>
      <AuthProvider>
        <div className="min-h-screen">
          <AppRoutes />
        </div>
      </AuthProvider>
    </ThemeProvider>
  )
}
