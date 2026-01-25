import { useState, useEffect } from 'react'
import { Link, useSearchParams, useNavigate } from 'react-router-dom'
import { Lock, CheckCircle, XCircle, TrendingUp } from 'lucide-react'
import './Auth.css'

const API_URL = 'http://127.0.0.1:8000/api/v1'

function ResetPassword() {
    const [searchParams] = useSearchParams()
    const navigate = useNavigate()
    const [password, setPassword] = useState('')
    const [confirmPassword, setConfirmPassword] = useState('')
    const [loading, setLoading] = useState(false)
    const [status, setStatus] = useState('form') // form, success, error
    const [message, setMessage] = useState('')
    const token = searchParams.get('token')

    useEffect(() => {
        if (!token) {
            setStatus('error')
            setMessage('Invalid or missing reset token.')
        }
    }, [token])

    const handleSubmit = async (e) => {
        e.preventDefault()

        if (password !== confirmPassword) {
            setMessage('Passwords do not match')
            return
        }

        if (password.length < 8) {
            setMessage('Password must be at least 8 characters')
            return
        }

        setLoading(true)
        setMessage('')

        try {
            const response = await fetch(`${API_URL}/security/reset-password`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    token: token,
                    new_password: password
                })
            })

            const data = await response.json()

            if (response.ok) {
                setStatus('success')
                setMessage(data.message)
                setTimeout(() => navigate('/login'), 3000)
            } else {
                setStatus('error')
                setMessage(data.detail || 'Failed to reset password')
            }
        } catch (err) {
            setStatus('error')
            setMessage('Unable to reset password. Please try again.')
        } finally {
            setLoading(false)
        }
    }

    return (
        <div className="auth-container">
            <div className="auth-card glass fade-in" style={{ maxWidth: '420px' }}>
                <div className="auth-header">
                    <TrendingUp size={48} className="auth-icon" />
                    <h1 className="gradient-text">New Password</h1>
                    <p>Create a strong password for your account</p>
                </div>

                {status === 'form' && token && (
                    <form onSubmit={handleSubmit} className="auth-form">
                        {message && (
                            <div className="error-message">{message}</div>
                        )}

                        <div className="form-group">
                            <label>
                                <Lock size={20} />
                                New Password
                            </label>
                            <input
                                type="password"
                                value={password}
                                onChange={(e) => setPassword(e.target.value)}
                                placeholder="••••••••"
                                required
                                minLength={8}
                            />
                        </div>

                        <div className="form-group">
                            <label>
                                <Lock size={20} />
                                Confirm Password
                            </label>
                            <input
                                type="password"
                                value={confirmPassword}
                                onChange={(e) => setConfirmPassword(e.target.value)}
                                placeholder="••••••••"
                                required
                            />
                        </div>

                        <button type="submit" className="btn-primary" disabled={loading}>
                            {loading ? 'Resetting...' : 'Reset Password'}
                        </button>
                    </form>
                )}

                {status === 'success' && (
                    <div style={{ textAlign: 'center', padding: '20px 0' }}>
                        <CheckCircle size={64} style={{ color: '#10b981', marginBottom: '16px' }} />
                        <p style={{ color: '#10b981', fontWeight: '600', fontSize: '18px', marginBottom: '8px' }}>
                            Password Reset!
                        </p>
                        <p style={{ color: 'rgba(255,255,255,0.7)' }}>{message}</p>
                        <p style={{ color: 'rgba(255,255,255,0.5)', fontSize: '14px', marginTop: '12px' }}>
                            Redirecting to login...
                        </p>
                    </div>
                )}

                {status === 'error' && (
                    <div style={{ textAlign: 'center', padding: '20px 0' }}>
                        <XCircle size={64} style={{ color: '#ef4444', marginBottom: '16px' }} />
                        <p style={{ color: '#ef4444', fontWeight: '600', fontSize: '18px', marginBottom: '8px' }}>
                            Reset Failed
                        </p>
                        <p style={{ color: 'rgba(255,255,255,0.7)' }}>{message}</p>
                        <Link to="/forgot-password" className="btn-primary" style={{ display: 'inline-block', marginTop: '20px', textDecoration: 'none' }}>
                            Request New Link
                        </Link>
                    </div>
                )}

                <div className="auth-footer">
                    <p><Link to="/login">← Back to Login</Link></p>
                </div>
            </div>
        </div>
    )
}

export default ResetPassword
