import React from 'react'
import { Routes, Route, Navigate, useLocation } from 'react-router-dom'
import { AuthProvider, useAuth } from './context/AuthContext'
import Navbar from './components/Navbar'
import ScrollBackground from './components/ScrollBackground'
import Login from './pages/Login'
import Register from './pages/Register'
import HealthForm from './pages/HealthForm'
import Dashboard from './pages/Dashboard'
import SHAPDashboard from './pages/SHAPDashboard'
import Simulator from './pages/Simulator'
import DietChat from './pages/DietChat'

function ProtectedRoute({ children }) {
  const { user, loading } = useAuth()
  if (loading) return null
  return user ? children : <Navigate to="/login" />
}

function PublicRoute({ children }) {
  const { user, loading } = useAuth()
  if (loading) return null
  return user ? <Navigate to="/" /> : children
}

function AppRoutes() {
  const location = useLocation()
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
        </Routes>
      </main>
    </>
  )
}

export default function App() {
  return (
    <AuthProvider>
      <div className="min-h-screen">
        <AppRoutes />
      </div>
    </AuthProvider>
  )
}
