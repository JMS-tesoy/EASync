import { useState, useEffect } from 'react'
import { useNavigate } from 'react-router-dom'
import Layout from '../components/Layout'
import { Shield, Smartphone, Mail, Copy, Check, RefreshCw, Key, AlertTriangle } from 'lucide-react'

const API_URL = 'http://127.0.0.1:8000/api/v1'

function TwoFactorSetup({ user, onLogout }) {
    const navigate = useNavigate()
    const [method, setMethod] = useState('totp') // 'totp' or 'email'
    const [step, setStep] = useState(1) // 1: choose method, 2: setup, 3: verify
    const [loading, setLoading] = useState(false)
    const [error, setError] = useState('')
    const [success, setSuccess] = useState('')

    // TOTP setup data
    const [qrCode, setQrCode] = useState('')
    const [secret, setSecret] = useState('')
    const [backupCodes, setBackupCodes] = useState([])

    // Verification
    const [verifyCode, setVerifyCode] = useState('')
    const [copied, setCopied] = useState(false)

    const token = localStorage.getItem('token')
    const is2FAEnabled = user?.two_fa_enabled

    useEffect(() => {
        if (is2FAEnabled) {
            setStep(0) // Show manage view
        }
    }, [is2FAEnabled])

    const startSetup = async () => {
        if (method === 'totp') {
            setLoading(true)
            setError('')

            try {
                const response = await fetch(`${API_URL}/security/2fa/setup`, {
                    headers: { 'Authorization': `Bearer ${token}` }
                })

                const data = await response.json()

                if (response.ok) {
                    setQrCode(data.qr_code)
                    setSecret(data.secret)
                    setBackupCodes(data.backup_codes)
                    setStep(2)
                } else {
                    setError(data.detail || 'Failed to setup 2FA')
                }
            } catch (err) {
                setError('Failed to connect to server')
            } finally {
                setLoading(false)
            }
        } else {
            // Email OTP - send code first
            setLoading(true)
            try {
                const response = await fetch(`${API_URL}/security/2fa/send-otp`, {
                    method: 'POST',
                    headers: {
                        'Authorization': `Bearer ${token}`,
                        'Content-Type': 'application/json'
                    }
                })

                if (response.ok) {
                    setStep(2)
                } else {
                    const data = await response.json()
                    setError(data.detail || 'Failed to send OTP')
                }
            } catch (err) {
                setError('Failed to send OTP')
            } finally {
                setLoading(false)
            }
        }
    }

    const enableTwoFactor = async () => {
        setLoading(true)
        setError('')

        try {
            const response = await fetch(`${API_URL}/security/2fa/enable`, {
                method: 'POST',
                headers: {
                    'Authorization': `Bearer ${token}`,
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({ method, code: verifyCode })
            })

            const data = await response.json()

            if (response.ok) {
                setSuccess('Two-factor authentication enabled!')
                setStep(3)
                // Update local user
                const updatedUser = { ...user, two_fa_enabled: true, two_fa_method: method }
                localStorage.setItem('user', JSON.stringify(updatedUser))
            } else {
                setError(data.detail || 'Invalid verification code')
            }
        } catch (err) {
            setError('Failed to enable 2FA')
        } finally {
            setLoading(false)
        }
    }

    const disableTwoFactor = async () => {
        const code = prompt('Enter your 2FA code to disable:')
        if (!code) return

        setLoading(true)
        try {
            const response = await fetch(`${API_URL}/security/2fa/disable`, {
                method: 'POST',
                headers: {
                    'Authorization': `Bearer ${token}`,
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({ code, method: user.two_fa_method || 'totp' })
            })

            if (response.ok) {
                setSuccess('2FA disabled successfully')
                const updatedUser = { ...user, two_fa_enabled: false, two_fa_method: null }
                localStorage.setItem('user', JSON.stringify(updatedUser))
                setStep(1)
            } else {
                const data = await response.json()
                setError(data.detail || 'Failed to disable 2FA')
            }
        } catch (err) {
            setError('Failed to disable 2FA')
        } finally {
            setLoading(false)
        }
    }

    const copyToClipboard = (text) => {
        navigator.clipboard.writeText(text)
        setCopied(true)
        setTimeout(() => setCopied(false), 2000)
    }

    return (
        <Layout user={user} onLogout={onLogout}>
            <div className="dashboard fade-in" style={{ maxWidth: '600px', margin: '0 auto', padding: '40px 20px' }}>
                <div className="page-header" style={{ textAlign: 'center', marginBottom: '32px' }}>
                    <Shield size={48} style={{ color: '#667eea', marginBottom: '16px' }} />
                    <h1>Two-Factor Authentication</h1>
                    <p className="text-muted">Add an extra layer of security to your account</p>
                </div>

                {error && (
                    <div style={{
                        background: 'rgba(239, 68, 68, 0.1)',
                        border: '1px solid rgba(239, 68, 68, 0.3)',
                        borderRadius: '8px',
                        padding: '12px',
                        marginBottom: '20px',
                        color: '#fca5a5',
                        textAlign: 'center'
                    }}>
                        {error}
                    </div>
                )}

                {success && (
                    <div style={{
                        background: 'rgba(16, 185, 129, 0.1)',
                        border: '1px solid rgba(16, 185, 129, 0.3)',
                        borderRadius: '8px',
                        padding: '12px',
                        marginBottom: '20px',
                        color: '#6ee7b7',
                        textAlign: 'center'
                    }}>
                        {success}
                    </div>
                )}

                {/* Already enabled view */}
                {step === 0 && (
                    <div className="dashboard-card glass" style={{ textAlign: 'center' }}>
                        <Check size={48} style={{ color: '#10b981', marginBottom: '16px' }} />
                        <h3 style={{ marginBottom: '8px' }}>2FA is Enabled</h3>
                        <p className="text-muted" style={{ marginBottom: '24px' }}>
                            Your account is protected with {user?.two_fa_method === 'email' ? 'Email OTP' : 'Authenticator App'}
                        </p>
                        <button
                            onClick={disableTwoFactor}
                            className="btn-danger"
                            disabled={loading}
                            style={{
                                background: 'rgba(239, 68, 68, 0.2)',
                                border: '1px solid rgba(239, 68, 68, 0.3)',
                                color: '#fca5a5',
                                padding: '12px 24px',
                                borderRadius: '8px',
                                cursor: 'pointer'
                            }}
                        >
                            {loading ? 'Disabling...' : 'Disable 2FA'}
                        </button>
                    </div>
                )}

                {/* Step 1: Choose method */}
                {step === 1 && (
                    <div className="dashboard-card glass">
                        <h3 style={{ marginBottom: '20px' }}>Choose 2FA Method</h3>

                        <div style={{ display: 'flex', flexDirection: 'column', gap: '12px', marginBottom: '24px' }}>
                            <label
                                style={{
                                    display: 'flex',
                                    alignItems: 'center',
                                    gap: '16px',
                                    padding: '16px',
                                    background: method === 'totp' ? 'rgba(102, 126, 234, 0.2)' : 'rgba(255,255,255,0.05)',
                                    border: `1px solid ${method === 'totp' ? 'rgba(102, 126, 234, 0.5)' : 'rgba(255,255,255,0.1)'}`,
                                    borderRadius: '12px',
                                    cursor: 'pointer'
                                }}
                            >
                                <input
                                    type="radio"
                                    name="method"
                                    value="totp"
                                    checked={method === 'totp'}
                                    onChange={(e) => setMethod(e.target.value)}
                                />
                                <Smartphone size={24} style={{ color: '#667eea' }} />
                                <div>
                                    <p style={{ fontWeight: '600', marginBottom: '4px' }}>Authenticator App</p>
                                    <p className="text-muted" style={{ fontSize: '13px' }}>
                                        Use Google Authenticator, Authy, or similar
                                    </p>
                                </div>
                            </label>

                            <label
                                style={{
                                    display: 'flex',
                                    alignItems: 'center',
                                    gap: '16px',
                                    padding: '16px',
                                    background: method === 'email' ? 'rgba(102, 126, 234, 0.2)' : 'rgba(255,255,255,0.05)',
                                    border: `1px solid ${method === 'email' ? 'rgba(102, 126, 234, 0.5)' : 'rgba(255,255,255,0.1)'}`,
                                    borderRadius: '12px',
                                    cursor: 'pointer'
                                }}
                            >
                                <input
                                    type="radio"
                                    name="method"
                                    value="email"
                                    checked={method === 'email'}
                                    onChange={(e) => setMethod(e.target.value)}
                                />
                                <Mail size={24} style={{ color: '#667eea' }} />
                                <div>
                                    <p style={{ fontWeight: '600', marginBottom: '4px' }}>Email OTP</p>
                                    <p className="text-muted" style={{ fontSize: '13px' }}>
                                        Receive codes at {user?.email}
                                    </p>
                                </div>
                            </label>
                        </div>

                        <button
                            onClick={startSetup}
                            className="btn-primary"
                            disabled={loading}
                            style={{ width: '100%' }}
                        >
                            {loading ? <RefreshCw size={18} className="spin" /> : 'Continue Setup'}
                        </button>
                    </div>
                )}

                {/* Step 2: Setup */}
                {step === 2 && method === 'totp' && (
                    <div className="dashboard-card glass">
                        <h3 style={{ marginBottom: '20px' }}>Scan QR Code</h3>

                        <div style={{
                            background: 'white',
                            padding: '16px',
                            borderRadius: '12px',
                            display: 'inline-block',
                            marginBottom: '20px'
                        }}>
                            <img src={qrCode} alt="2FA QR Code" style={{ display: 'block', width: '200px', height: '200px' }} />
                        </div>

                        <p className="text-muted" style={{ marginBottom: '16px' }}>
                            Can't scan? Enter this code manually:
                        </p>

                        <div style={{
                            display: 'flex',
                            alignItems: 'center',
                            gap: '8px',
                            background: 'rgba(0,0,0,0.3)',
                            padding: '12px',
                            borderRadius: '8px',
                            marginBottom: '24px'
                        }}>
                            <code style={{ flex: 1, fontSize: '14px', wordBreak: 'break-all' }}>{secret}</code>
                            <button
                                onClick={() => copyToClipboard(secret)}
                                style={{ background: 'transparent', border: 'none', color: '#667eea', cursor: 'pointer' }}
                            >
                                {copied ? <Check size={18} /> : <Copy size={18} />}
                            </button>
                        </div>

                        <div style={{ marginBottom: '24px' }}>
                            <label style={{ display: 'block', marginBottom: '8px', fontWeight: '600' }}>
                                Enter the 6-digit code from your app:
                            </label>
                            <input
                                type="text"
                                value={verifyCode}
                                onChange={(e) => setVerifyCode(e.target.value.replace(/\D/g, '').slice(0, 6))}
                                placeholder="000000"
                                style={{
                                    width: '100%',
                                    textAlign: 'center',
                                    fontSize: '24px',
                                    letterSpacing: '8px',
                                    fontFamily: 'monospace'
                                }}
                                maxLength={6}
                            />
                        </div>

                        <button
                            onClick={enableTwoFactor}
                            className="btn-primary"
                            disabled={loading || verifyCode.length !== 6}
                            style={{ width: '100%' }}
                        >
                            {loading ? 'Verifying...' : 'Enable 2FA'}
                        </button>
                    </div>
                )}

                {step === 2 && method === 'email' && (
                    <div className="dashboard-card glass">
                        <h3 style={{ marginBottom: '20px' }}>Check Your Email</h3>
                        <p className="text-muted" style={{ marginBottom: '24px' }}>
                            We sent a 6-digit code to {user?.email}
                        </p>

                        <div style={{ marginBottom: '24px' }}>
                            <input
                                type="text"
                                value={verifyCode}
                                onChange={(e) => setVerifyCode(e.target.value.replace(/\D/g, '').slice(0, 6))}
                                placeholder="000000"
                                style={{
                                    width: '100%',
                                    textAlign: 'center',
                                    fontSize: '24px',
                                    letterSpacing: '8px',
                                    fontFamily: 'monospace'
                                }}
                                maxLength={6}
                            />
                        </div>

                        <button
                            onClick={enableTwoFactor}
                            className="btn-primary"
                            disabled={loading || verifyCode.length !== 6}
                            style={{ width: '100%' }}
                        >
                            {loading ? 'Verifying...' : 'Enable 2FA'}
                        </button>
                    </div>
                )}

                {/* Step 3: Success with backup codes */}
                {step === 3 && backupCodes.length > 0 && (
                    <div className="dashboard-card glass">
                        <div style={{ textAlign: 'center', marginBottom: '24px' }}>
                            <Check size={48} style={{ color: '#10b981', marginBottom: '16px' }} />
                            <h3>2FA Enabled Successfully!</h3>
                        </div>

                        <div style={{
                            background: 'rgba(251, 191, 36, 0.1)',
                            border: '1px solid rgba(251, 191, 36, 0.3)',
                            borderRadius: '8px',
                            padding: '16px',
                            marginBottom: '20px'
                        }}>
                            <div style={{ display: 'flex', alignItems: 'center', gap: '8px', marginBottom: '12px' }}>
                                <AlertTriangle size={20} style={{ color: '#fbbf24' }} />
                                <span style={{ color: '#fbbf24', fontWeight: '600' }}>Save Your Backup Codes</span>
                            </div>
                            <p style={{ color: 'rgba(255,255,255,0.7)', fontSize: '14px' }}>
                                Store these codes safely. You can use them to access your account if you lose your device.
                            </p>
                        </div>

                        <div style={{
                            display: 'grid',
                            gridTemplateColumns: 'repeat(2, 1fr)',
                            gap: '8px',
                            marginBottom: '24px'
                        }}>
                            {backupCodes.map((code, i) => (
                                <code key={i} style={{
                                    background: 'rgba(0,0,0,0.3)',
                                    padding: '8px',
                                    borderRadius: '4px',
                                    textAlign: 'center',
                                    fontFamily: 'monospace'
                                }}>
                                    {code}
                                </code>
                            ))}
                        </div>

                        <button
                            onClick={() => copyToClipboard(backupCodes.join('\n'))}
                            className="btn-secondary"
                            style={{ width: '100%', marginBottom: '12px' }}
                        >
                            <Copy size={18} />
                            Copy All Codes
                        </button>

                        <button
                            onClick={() => navigate('/dashboard')}
                            className="btn-primary"
                            style={{ width: '100%' }}
                        >
                            Done
                        </button>
                    </div>
                )}
            </div>
        </Layout>
    )
}

export default TwoFactorSetup
