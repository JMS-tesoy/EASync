import { useState, useEffect } from 'react'
import { Link, useSearchParams } from 'react-router-dom'
import { CheckCircle, XCircle, Mail, RefreshCw, TrendingUp } from 'lucide-react'
import './Auth.css'

const API_URL = 'http://127.0.0.1:8000/api/v1'

function VerifyEmail() {
    const [searchParams] = useSearchParams()
    const [status, setStatus] = useState('loading') // loading, success, error
    const [message, setMessage] = useState('')
    const [email, setEmail] = useState('')
    const [resendLoading, setResendLoading] = useState(false)
    const [resendMessage, setResendMessage] = useState('')

    useEffect(() => {
        const token = searchParams.get('token')
        if (token) {
            verifyToken(token)
        } else {
            setStatus('pending')
            setMessage('Check your email for a verification link.')
        }
    }, [searchParams])

    const verifyToken = async (token) => {
        try {
            const response = await fetch(`${API_URL}/security/verify-email`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ token })
            })

            const data = await response.json()

            if (response.ok) {
                setStatus('success')
                setMessage(data.message)
            } else {
                setStatus('error')
                setMessage(data.detail || 'Verification failed')
            }
        } catch (err) {
            setStatus('error')
            setMessage('Unable to verify email. Please try again.')
        }
    }

    const handleResend = async (e) => {
        e.preventDefault()
        if (!email) return

        setResendLoading(true)
        setResendMessage('')

        try {
            const response = await fetch(`${API_URL}/security/resend-verification`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ email })
            })

            const data = await response.json()
            setResendMessage(data.message)
        } catch (err) {
            setResendMessage('Failed to resend. Please try again.')
        } finally {
            setResendLoading(false)
        }
    }

    return (
        <div className="auth-container">
            <div className="auth-card glass fade-in" style={{ maxWidth: '480px' }}>
                <div className="auth-header">
                    <TrendingUp size={48} className="auth-icon" />
                    <h1 className="gradient-text">Email Verification</h1>
                </div>

                <div style={{ textAlign: 'center', padding: '20px 0' }}>
                    {status === 'loading' && (
                        <div style={{ color: 'rgba(255,255,255,0.7)' }}>
                            <RefreshCw size={48} className="spin" style={{ marginBottom: '16px' }} />
                            <p>Verifying your email...</p>
                        </div>
                    )}

                    {status === 'success' && (
                        <div>
                            <CheckCircle size={64} style={{ color: '#10b981', marginBottom: '16px' }} />
                            <p style={{ color: '#10b981', fontSize: '18px', fontWeight: '600', marginBottom: '8px' }}>
                                Email Verified!
                            </p>
                            <p style={{ color: 'rgba(255,255,255,0.7)', marginBottom: '24px' }}>{message}</p>
                            <Link to="/login" className="btn-primary" style={{ textDecoration: 'none' }}>
                                Continue to Login
                            </Link>
                        </div>
                    )}

                    {status === 'error' && (
                        <div>
                            <XCircle size={64} style={{ color: '#ef4444', marginBottom: '16px' }} />
                            <p style={{ color: '#ef4444', fontSize: '18px', fontWeight: '600', marginBottom: '8px' }}>
                                Verification Failed
                            </p>
                            <p style={{ color: 'rgba(255,255,255,0.7)', marginBottom: '24px' }}>{message}</p>

                            <div style={{
                                background: 'rgba(255,255,255,0.05)',
                                borderRadius: '12px',
                                padding: '20px',
                                marginTop: '20px'
                            }}>
                                <p style={{ color: 'rgba(255,255,255,0.7)', marginBottom: '16px', fontSize: '14px' }}>
                                    Need a new verification link?
                                </p>
                                <form onSubmit={handleResend} style={{ display: 'flex', gap: '8px' }}>
                                    <input
                                        type="email"
                                        placeholder="Enter your email"
                                        value={email}
                                        onChange={(e) => setEmail(e.target.value)}
                                        style={{ flex: 1 }}
                                        required
                                    />
                                    <button type="submit" className="btn-primary" disabled={resendLoading}>
                                        {resendLoading ? <RefreshCw size={18} className="spin" /> : 'Resend'}
                                    </button>
                                </form>
                                {resendMessage && (
                                    <p style={{ color: '#10b981', fontSize: '14px', marginTop: '12px' }}>
                                        {resendMessage}
                                    </p>
                                )}
                            </div>
                        </div>
                    )}

                    {status === 'pending' && (
                        <div>
                            <Mail size={64} style={{ color: '#667eea', marginBottom: '16px' }} />
                            <p style={{ color: '#667eea', fontSize: '18px', fontWeight: '600', marginBottom: '8px' }}>
                                Check Your Email
                            </p>
                            <p style={{ color: 'rgba(255,255,255,0.7)', marginBottom: '24px' }}>
                                We've sent a verification link to your email address.
                            </p>

                            <div style={{
                                background: 'rgba(255,255,255,0.05)',
                                borderRadius: '12px',
                                padding: '20px'
                            }}>
                                <p style={{ color: 'rgba(255,255,255,0.7)', marginBottom: '16px', fontSize: '14px' }}>
                                    Didn't receive the email?
                                </p>
                                <form onSubmit={handleResend} style={{ display: 'flex', gap: '8px' }}>
                                    <input
                                        type="email"
                                        placeholder="Enter your email"
                                        value={email}
                                        onChange={(e) => setEmail(e.target.value)}
                                        style={{ flex: 1 }}
                                        required
                                    />
                                    <button type="submit" className="btn-primary" disabled={resendLoading}>
                                        {resendLoading ? <RefreshCw size={18} className="spin" /> : 'Resend'}
                                    </button>
                                </form>
                                {resendMessage && (
                                    <p style={{ color: '#10b981', fontSize: '14px', marginTop: '12px' }}>
                                        {resendMessage}
                                    </p>
                                )}
                            </div>
                        </div>
                    )}
                </div>

                <div className="auth-footer" style={{ marginTop: '20px' }}>
                    <p><Link to="/login">← Back to Login</Link></p>
                </div>
            </div>
        </div>
    )
}

export default VerifyEmail
