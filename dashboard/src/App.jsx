import { BrowserRouter as Router, Routes, Route, Navigate } from 'react-router-dom'
import { useState, useEffect } from 'react'
import Login from './pages/Login'
import Register from './pages/Register'
import Dashboard from './pages/Dashboard'
import Subscriptions from './pages/Subscriptions'
import Marketplace from './pages/Marketplace'
import BecomeMaster from './pages/BecomeMaster'
import MasterDashboard from './pages/MasterDashboard'
import Wallet from './pages/Wallet'
import Protection from './pages/Protection'
import VerifyEmail from './pages/VerifyEmail'
import ForgotPassword from './pages/ForgotPassword'
import ResetPassword from './pages/ResetPassword'
import TwoFactorSetup from './pages/TwoFactorSetup'
import MasterAnalytics from './pages/MasterAnalytics'
import './index.css'

function App() {
  const [isAuthenticated, setIsAuthenticated] = useState(() => {
    return !!localStorage.getItem('token')
  })
  const [user, setUser] = useState(() => {
    const userData = localStorage.getItem('user')
    return userData ? JSON.parse(userData) : null
  })

  useEffect(() => {
    // Sync state if localStorage changes (optional but good for multi-tab)
    const token = localStorage.getItem('token')
    const userData = localStorage.getItem('user')
    if (token && userData) {
      setIsAuthenticated(true)
      setUser(JSON.parse(userData))
    }
  }, [])

  const handleLogin = (token, userData) => {
    localStorage.setItem('token', token)
    localStorage.setItem('user', JSON.stringify(userData))
    setIsAuthenticated(true)
    setUser(userData)
  }

  const handleLogout = () => {
    localStorage.removeItem('token')
    localStorage.removeItem('user')
    setIsAuthenticated(false)
    setUser(null)
  }

  return (
    <Router>
      <Routes>
        {/* Public Auth Routes */}
        <Route
          path="/login"
          element={
            isAuthenticated ?
              <Navigate to="/dashboard" /> :
              <Login onLogin={handleLogin} />
          }
        />
        <Route
          path="/register"
          element={
            isAuthenticated ?
              <Navigate to="/dashboard" /> :
              <Register onRegister={handleLogin} />
          }
        />
        <Route path="/verify-email" element={<VerifyEmail />} />
        <Route path="/forgot-password" element={<ForgotPassword />} />
        <Route path="/reset-password" element={<ResetPassword />} />

        {/* Protected Routes */}
        <Route
          path="/dashboard"
          element={
            isAuthenticated ?
              <Dashboard user={user} onLogout={handleLogout} /> :
              <Navigate to="/login" />
          }
        />
        <Route
          path="/subscriptions"
          element={
            isAuthenticated ?
              <Subscriptions user={user} onLogout={handleLogout} /> :
              <Navigate to="/login" />
          }
        />
        <Route
          path="/marketplace"
          element={
            isAuthenticated ?
              <Marketplace user={user} onLogout={handleLogout} /> :
              <Navigate to="/login" />
          }
        />
        <Route
          path="/become-master"
          element={
            isAuthenticated ?
              <BecomeMaster user={user} onLogout={handleLogout} /> :
              <Navigate to="/login" />
          }
        />
        <Route
          path="/master-dashboard"
          element={
            isAuthenticated ?
              <MasterDashboard user={user} onLogout={handleLogout} /> :
              <Navigate to="/login" />
          }
        />
        <Route
          path="/wallet"
          element={
            isAuthenticated ?
              <Wallet user={user} onLogout={handleLogout} /> :
              <Navigate to="/login" />
          }
        />
        <Route
          path="/protection"
          element={
            isAuthenticated ?
              <Protection user={user} onLogout={handleLogout} /> :
              <Navigate to="/login" />
          }
        />
        <Route
          path="/security/2fa"
          element={
            isAuthenticated ?
              <TwoFactorSetup user={user} onLogout={handleLogout} /> :
              <Navigate to="/login" />
          }
        />
        <Route
          path="/master/analytics"
          element={
            isAuthenticated && user?.role === 'master' ?
              <MasterAnalytics user={user} onLogout={handleLogout} /> :
              <Navigate to="/dashboard" />
          }
        />
        <Route path="/" element={<Navigate to="/dashboard" />} />
      </Routes>
    </Router>
  )
}

export default App
