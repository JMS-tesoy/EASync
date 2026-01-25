import { useState } from 'react'
import { Link } from 'react-router-dom'
import { Mail, ArrowLeft, Send, TrendingUp } from 'lucide-react'
import './Auth.css'

const API_URL = 'http://127.0.0.1:8000/api/v1'

function ForgotPassword() {
    const [email, setEmail] = useState('')
    const [loading, setLoading] = useState(false)
    const [submitted, setSubmitted] = useState(false)
    const [message, setMessage] = useState('')

    const handleSubmit = async (e) => {
        e.preventDefault()
        setLoading(true)

        try {
            const response = await fetch(`${API_URL}/security/forgot-password`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ email })
            })

            const data = await response.json()
            setMessage(data.message)
            setSubmitted(true)
        } catch (err) {
            setMessage('Failed to send reset email. Please try again.')
        } finally {
            setLoading(false)
        }
    }

    return (
        <div className="auth-container">
            <div className="auth-card glass fade-in" style={{ maxWidth: '420px' }}>
                <div className="auth-header">
                    <TrendingUp size={48} className="auth-icon" />
                    <h1 className="gradient-text">Reset Password</h1>
                    <p>We'll send you a link to reset your password</p>
                </div>

                {!submitted ? (
                    <form onSubmit={handleSubmit} className="auth-form">
                        <div className="form-group">
                            <label>
                                <Mail size={20} />
                                Email Address
                            </label>
                            <input
                                type="email"
                                value={email}
                                onChange={(e) => setEmail(e.target.value)}
                                placeholder="trader@example.com"
                                required
                            />
                        </div>

                        <button type="submit" className="btn-primary" disabled={loading}>
                            <Send size={20} />
                            {loading ? 'Sending...' : 'Send Reset Link'}
                        </button>
                    </form>
                ) : (
                    <div style={{ textAlign: 'center', padding: '20px 0' }}>
                        <Mail size={48} style={{ color: '#10b981', marginBottom: '16px' }} />
                        <p style={{ color: '#10b981', fontWeight: '600', marginBottom: '8px' }}>
                            Check your email!
                        </p>
                        <p style={{ color: 'rgba(255,255,255,0.7)', fontSize: '14px' }}>
                            {message}
                        </p>
                        <button
                            onClick={() => { setSubmitted(false); setEmail(''); }}
                            className="btn-secondary"
                            style={{ marginTop: '20px' }}
                        >
                            Send to different email
                        </button>
                    </div>
                )}

                <div className="auth-footer">
                    <p>
                        <Link to="/login" style={{ display: 'flex', alignItems: 'center', gap: '8px', justifyContent: 'center' }}>
                            <ArrowLeft size={16} />
                            Back to Login
                        </Link>
                    </p>
                </div>
            </div>
        </div>
    )
}

export default ForgotPassword
