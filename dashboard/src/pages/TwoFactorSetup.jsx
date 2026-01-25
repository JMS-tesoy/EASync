import { useState, useEffect } from 'react'
import { useNavigate } from 'react-router-dom'
import Layout from '../components/Layout'
import { Shield, Smartphone, Mail, Copy, Check, RefreshCw, X, AlertTriangle } from 'lucide-react'

const API_URL = 'http://127.0.0.1:8000/api/v1'

function TwoFactorSetup({ user, onLogout }) {
    const navigate = useNavigate()
    const [loading, setLoading] = useState(true)
    const [actionLoading, setActionLoading] = useState(false)
    const [error, setError] = useState('')
    const [success, setSuccess] = useState('')

    // 2FA Status
    const [is2FAEnabled, setIs2FAEnabled] = useState(false)
    const [currentMethod, setCurrentMethod] = useState(null)

    // Setup modal state
    const [showSetup, setShowSetup] = useState(false)
    const [setupMethod, setSetupMethod] = useState(null)
    const [qrCode, setQrCode] = useState('')
    const [secret, setSecret] = useState('')
    const [backupCodes, setBackupCodes] = useState([])
    const [verifyCode, setVerifyCode] = useState('')
    const [setupStep, setSetupStep] = useState(1) // 1 = scan/enter, 2 = verify, 3 = success
    const [copied, setCopied] = useState(false)

    const token = localStorage.getItem('token')

    // Check 2FA status on mount
    useEffect(() => {
        checkStatus()
    }, [])

    const checkStatus = async () => {
        setLoading(true)
        try {
            const response = await fetch(`${API_URL}/security/2fa/setup`, {
                headers: { 'Authorization': `Bearer ${token}` }
            })

            const data = await response.json()

            if (response.status === 400 && data.detail?.includes('already enabled')) {
                setIs2FAEnabled(true)
                const storedUser = JSON.parse(localStorage.getItem('user') || '{}')
                setCurrentMethod(storedUser.two_fa_method || 'totp')
            } else {
                setIs2FAEnabled(false)
            }
        } catch (err) {
            console.error('Error checking 2FA status:', err)
            if (user?.two_fa_enabled) {
                setIs2FAEnabled(true)
                setCurrentMethod(user.two_fa_method || 'totp')
            }
        } finally {
            setLoading(false)
        }
    }

    const startTOTPSetup = async () => {
        setActionLoading(true)
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
                setSetupMethod('totp')
                setSetupStep(1)
                setShowSetup(true)
            } else {
                setError(data.detail || 'Failed to setup 2FA')
            }
        } catch (err) {
            setError('Failed to connect to server')
        } finally {
            setActionLoading(false)
        }
    }

    const startEmailOTPSetup = async () => {
        setActionLoading(true)
        setError('')
        try {
            const response = await fetch(`${API_URL}/security/2fa/send-otp`, {
                method: 'POST',
                headers: {
                    'Authorization': `Bearer ${token}`,
                    'Content-Type': 'application/json'
                }
            })

            if (response.ok) {
                setSetupMethod('email')
                setSetupStep(2)
                setShowSetup(true)
            } else {
                const data = await response.json()
                setError(data.detail || 'Failed to send OTP')
            }
        } catch (err) {
            setError('Failed to send OTP')
        } finally {
            setActionLoading(false)
        }
    }

    const enableTwoFactor = async () => {
        setActionLoading(true)
        setError('')

        try {
            const response = await fetch(`${API_URL}/security/2fa/enable`, {
                method: 'POST',
                headers: {
                    'Authorization': `Bearer ${token}`,
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({ method: setupMethod, code: verifyCode })
            })

            const data = await response.json()

            if (response.ok) {
                setSuccess('Two-factor authentication enabled!')
                setSetupStep(3)
                setIs2FAEnabled(true)
                setCurrentMethod(setupMethod)
                const updatedUser = { ...user, two_fa_enabled: true, two_fa_method: setupMethod }
                localStorage.setItem('user', JSON.stringify(updatedUser))
            } else {
                setError(data.detail || 'Invalid verification code')
            }
        } catch (err) {
            setError('Failed to enable 2FA')
        } finally {
            setActionLoading(false)
        }
    }

    const disableTwoFactor = async () => {
        const code = prompt('Enter your 2FA code to disable:')
        if (!code) return

        setActionLoading(true)
        try {
            const response = await fetch(`${API_URL}/security/2fa/disable`, {
                method: 'POST',
                headers: {
                    'Authorization': `Bearer ${token}`,
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({ code, method: currentMethod || 'totp' })
            })

            if (response.ok) {
                setSuccess('2FA disabled successfully')
                setIs2FAEnabled(false)
                setCurrentMethod(null)
                const updatedUser = { ...user, two_fa_enabled: false, two_fa_method: null }
                localStorage.setItem('user', JSON.stringify(updatedUser))
            } else {
                const data = await response.json()
                setError(data.detail || 'Failed to disable 2FA')
            }
        } catch (err) {
            setError('Failed to disable 2FA')
        } finally {
            setActionLoading(false)
        }
    }

    const copyToClipboard = (text) => {
        navigator.clipboard.writeText(text)
        setCopied(true)
        setTimeout(() => setCopied(false), 2000)
    }

    const closeModal = () => {
        setShowSetup(false)
        setSetupMethod(null)
        setVerifyCode('')
        setSetupStep(1)
        setError('')
        if (setupStep === 3) {
            // Refresh status after successful setup
            checkStatus()
        }
    }

    return (
        <Layout user={user} onLogout={onLogout}>
            <div className="dashboard fade-in" style={{ padding: '40px 20px' }}>
                {/* Header */}
                <div className="page-header" style={{ textAlign: 'center', marginBottom: '40px' }}>
                    <Shield size={48} style={{ color: '#667eea', marginBottom: '16px' }} />
                    <h1 className="gradient-text" style={{ fontSize: '2.5rem', marginBottom: '0.5rem' }}>Two-Factor Authentication</h1>
                    <p className="text-muted">
                        {is2FAEnabled ? 'Your account is protected' : 'Add an extra layer of security to your account'}
                    </p>
                </div>

                {/* Messages */}
                {error && (
                    <div style={{
                        maxWidth: '700px', margin: '0 auto 20px',
                        background: 'rgba(239, 68, 68, 0.1)',
                        border: '1px solid rgba(239, 68, 68, 0.3)',
                        borderRadius: '8px', padding: '12px',
                        color: '#fca5a5', textAlign: 'center'
                    }}>
                        {error}
                    </div>
                )}
                {success && (
                    <div style={{
                        maxWidth: '700px', margin: '0 auto 20px',
                        background: 'rgba(16, 185, 129, 0.1)',
                        border: '1px solid rgba(16, 185, 129, 0.3)',
                        borderRadius: '8px', padding: '12px',
                        color: '#6ee7b7', textAlign: 'center'
                    }}>
                        {success}
                    </div>
                )}

                {/* Loading */}
                {loading && (
                    <div style={{ textAlign: 'center', padding: '60px' }}>
                        <RefreshCw size={32} className="spin" style={{ color: '#667eea' }} />
                        <p className="text-muted" style={{ marginTop: '16px' }}>Checking 2FA status...</p>
                    </div>
                )}

                {/* Two Cards Layout */}
                {!loading && (
                    <div style={{
                        display: 'grid',
                        gridTemplateColumns: 'repeat(auto-fit, minmax(280px, 1fr))',
                        gap: '24px',
                        maxWidth: '800px',
                        margin: '0 auto'
                    }}>
                        {/* Authenticator App Card */}
                        <div
                            className="dashboard-card glass"
                            style={{
                                textAlign: 'center',
                                border: is2FAEnabled && currentMethod === 'totp'
                                    ? '1px solid #10b981'
                                    : '1px solid rgba(255,255,255,0.1)',
                                boxShadow: is2FAEnabled && currentMethod === 'totp'
                                    ? '0 0 20px rgba(16, 185, 129, 0.2)'
                                    : 'none',
                                transform: 'scale(1)',
                                transition: 'all 0.3s ease',
                                cursor: 'default'
                            }}
                            onMouseEnter={(e) => { e.currentTarget.style.transform = 'scale(1.02)'; e.currentTarget.style.borderColor = is2FAEnabled && currentMethod === 'totp' ? '#10b981' : 'rgba(255,255,255,0.3)' }}
                            onMouseLeave={(e) => { e.currentTarget.style.transform = 'scale(1)'; e.currentTarget.style.borderColor = is2FAEnabled && currentMethod === 'totp' ? '#10b981' : 'rgba(255,255,255,0.1)' }}
                        >
                            <div style={{
                                width: '80px', height: '80px', margin: '0 auto 20px',
                                background: is2FAEnabled && currentMethod === 'totp'
                                    ? 'rgba(16, 185, 129, 0.1)'
                                    : 'rgba(255,255,255,0.05)',
                                borderRadius: '50%',
                                display: 'flex', alignItems: 'center', justifyContent: 'center',
                                position: 'relative'
                            }}>
                                {is2FAEnabled && currentMethod === 'totp' ? (
                                    <>
                                        <div className="pulse" style={{
                                            position: 'absolute', inset: 0, borderRadius: '50%',
                                            border: '2px solid #10b981', opacity: 0.5
                                        }}></div>
                                        <Check size={40} style={{ color: '#10b981' }} />
                                    </>
                                ) : (
                                    <Smartphone size={40} style={{ color: '#667eea' }} />
                                )}
                            </div>

                            <h3 style={{ marginBottom: '8px', fontSize: '1.25rem' }}>
                                {is2FAEnabled && currentMethod === 'totp' ? 'Authenticator Active' : 'Authenticator App'}
                            </h3>
                            <p className="text-muted" style={{ fontSize: '0.9rem', marginBottom: '24px', minHeight: '40px' }}>
                                {is2FAEnabled && currentMethod === 'totp'
                                    ? 'Your account is securely protected by your authenticator app.'
                                    : 'Use Google Authenticator, Authy, or similar apps to generate codes.'}
                            </p>

                            {is2FAEnabled && currentMethod === 'totp' ? (
                                <button
                                    onClick={disableTwoFactor}
                                    disabled={actionLoading}
                                    style={{
                                        width: '100%',
                                        background: 'rgba(239, 68, 68, 0.1)',
                                        border: '1px solid rgba(239, 68, 68, 0.3)',
                                        color: '#fca5a5',
                                        padding: '12px',
                                        borderRadius: '8px',
                                        cursor: 'pointer',
                                        fontSize: '14px',
                                        fontWeight: '500',
                                        transition: 'all 0.2s'
                                    }}
                                    className="hover-danger"
                                >
                                    {actionLoading ? 'Disabling...' : 'Disable 2FA'}
                                </button>
                            ) : !is2FAEnabled && (
                                <button
                                    onClick={startTOTPSetup}
                                    disabled={actionLoading}
                                    className="btn-primary"
                                    style={{ width: '100%', padding: '12px', fontSize: '14px' }}
                                >
                                    {actionLoading ? 'Loading...' : 'Enable Authenticator'}
                                </button>
                            )}
                        </div>

                        {/* Email OTP Card */}
                        <div
                            className="dashboard-card glass"
                            style={{
                                textAlign: 'center',
                                border: is2FAEnabled && currentMethod === 'email'
                                    ? '1px solid #10b981'
                                    : '1px solid rgba(255,255,255,0.1)',
                                boxShadow: is2FAEnabled && currentMethod === 'email'
                                    ? '0 0 20px rgba(16, 185, 129, 0.2)'
                                    : 'none',
                                transform: 'scale(1)',
                                transition: 'all 0.3s ease',
                                cursor: 'default'
                            }}
                            onMouseEnter={(e) => { e.currentTarget.style.transform = 'scale(1.02)'; e.currentTarget.style.borderColor = is2FAEnabled && currentMethod === 'email' ? '#10b981' : 'rgba(255,255,255,0.3)' }}
                            onMouseLeave={(e) => { e.currentTarget.style.transform = 'scale(1)'; e.currentTarget.style.borderColor = is2FAEnabled && currentMethod === 'email' ? '#10b981' : 'rgba(255,255,255,0.1)' }}
                        >
                            <div style={{
                                width: '80px', height: '80px', margin: '0 auto 20px',
                                background: is2FAEnabled && currentMethod === 'email'
                                    ? 'rgba(16, 185, 129, 0.1)'
                                    : 'rgba(255,255,255,0.05)',
                                borderRadius: '50%',
                                display: 'flex', alignItems: 'center', justifyContent: 'center',
                                position: 'relative'
                            }}>
                                {is2FAEnabled && currentMethod === 'email' ? (
                                    <>
                                        <div className="pulse" style={{
                                            position: 'absolute', inset: 0, borderRadius: '50%',
                                            border: '2px solid #10b981', opacity: 0.5
                                        }}></div>
                                        <Check size={40} style={{ color: '#10b981' }} />
                                    </>
                                ) : (
                                    <Mail size={40} style={{ color: '#667eea' }} />
                                )}
                            </div>

                            <h3 style={{ marginBottom: '8px', fontSize: '1.25rem' }}>
                                {is2FAEnabled && currentMethod === 'email' ? 'Email OTP Active' : 'Email OTP'}
                            </h3>
                            <p className="text-muted" style={{ fontSize: '0.9rem', marginBottom: '24px', minHeight: '40px' }}>
                                {is2FAEnabled && currentMethod === 'email'
                                    ? 'Your account is securely protected by email verification.'
                                    : `Receive 6-digit verification codes at ${user?.email}`}
                            </p>

                            {is2FAEnabled && currentMethod === 'email' ? (
                                <button
                                    onClick={disableTwoFactor}
                                    disabled={actionLoading}
                                    style={{
                                        width: '100%',
                                        background: 'rgba(239, 68, 68, 0.1)',
                                        border: '1px solid rgba(239, 68, 68, 0.3)',
                                        color: '#fca5a5',
                                        padding: '12px',
                                        borderRadius: '8px',
                                        cursor: 'pointer',
                                        fontSize: '14px',
                                        fontWeight: '500',
                                        transition: 'all 0.2s'
                                    }}
                                    className="hover-danger"
                                >
                                    {actionLoading ? 'Disabling...' : 'Disable 2FA'}
                                </button>
                            ) : !is2FAEnabled && (
                                <button
                                    onClick={startEmailOTPSetup}
                                    disabled={actionLoading}
                                    className="btn-primary"
                                    style={{ width: '100%', padding: '12px', fontSize: '14px' }}
                                >
                                    {actionLoading ? 'Loading...' : 'Enable Email OTP'}
                                </button>
                            )}
                        </div>
                    </div>
                )}

                {/* Setup Modal */}
                {showSetup && (
                    <div style={{
                        position: 'fixed', top: 0, left: 0, right: 0, bottom: 0,
                        background: 'rgba(0,0,0,0.8)',
                        display: 'flex', alignItems: 'center', justifyContent: 'center',
                        zIndex: 1000, padding: '20px'
                    }}>
                        <div className="dashboard-card glass" style={{
                            maxWidth: '450px', width: '100%',
                            maxHeight: '90vh', overflowY: 'auto'
                        }}>
                            {/* TOTP Setup - Step 1: Scan QR */}
                            {setupMethod === 'totp' && setupStep === 1 && (
                                <>
                                    <h3 style={{ marginBottom: '20px', textAlign: 'center' }}>Scan QR Code</h3>

                                    <div style={{
                                        background: 'white', padding: '16px', borderRadius: '12px',
                                        display: 'flex', justifyContent: 'center', marginBottom: '20px'
                                    }}>
                                        <img src={qrCode} alt="2FA QR" style={{ width: '180px', height: '180px' }} />
                                    </div>

                                    <p className="text-muted" style={{ textAlign: 'center', marginBottom: '12px', fontSize: '14px' }}>
                                        Can't scan? Enter this code manually:
                                    </p>

                                    <div style={{
                                        display: 'flex', alignItems: 'center', gap: '8px',
                                        background: 'rgba(0,0,0,0.3)', padding: '10px', borderRadius: '8px', marginBottom: '20px'
                                    }}>
                                        <code style={{ flex: 1, fontSize: '12px', wordBreak: 'break-all' }}>{secret}</code>
                                        <button onClick={() => copyToClipboard(secret)} style={{ background: 'none', border: 'none', color: '#667eea', cursor: 'pointer' }}>
                                            {copied ? <Check size={16} /> : <Copy size={16} />}
                                        </button>
                                    </div>

                                    <button onClick={() => setSetupStep(2)} className="btn-primary" style={{ width: '100%' }}>
                                        Next
                                    </button>
                                </>
                            )}

                            {/* Step 2: Verify Code */}
                            {setupStep === 2 && (
                                <>
                                    <h3 style={{ marginBottom: '20px', textAlign: 'center' }}>
                                        {setupMethod === 'email' ? 'Check Your Email' : 'Enter Verification Code'}
                                    </h3>

                                    {setupMethod === 'email' && (
                                        <p className="text-muted" style={{ textAlign: 'center', marginBottom: '20px' }}>
                                            We sent a 6-digit code to {user?.email}
                                        </p>
                                    )}

                                    <input
                                        type="text"
                                        value={verifyCode}
                                        onChange={(e) => setVerifyCode(e.target.value.replace(/\D/g, '').slice(0, 6))}
                                        placeholder="000000"
                                        style={{
                                            width: '100%', textAlign: 'center', fontSize: '28px',
                                            letterSpacing: '10px', fontFamily: 'monospace', marginBottom: '20px'
                                        }}
                                        maxLength={6}
                                    />

                                    {error && <p style={{ color: '#fca5a5', textAlign: 'center', marginBottom: '16px' }}>{error}</p>}

                                    <button
                                        onClick={enableTwoFactor}
                                        className="btn-primary"
                                        disabled={actionLoading || verifyCode.length !== 6}
                                        style={{ width: '100%' }}
                                    >
                                        {actionLoading ? 'Verifying...' : 'Enable 2FA'}
                                    </button>
                                </>
                            )}

                            {/* Step 3: Success + Backup Codes */}
                            {setupStep === 3 && (
                                <>
                                    <div style={{ textAlign: 'center', marginBottom: '20px' }}>
                                        <Check size={48} style={{ color: '#10b981', marginBottom: '12px' }} />
                                        <h3>2FA Enabled!</h3>
                                    </div>

                                    {backupCodes.length > 0 && (
                                        <>
                                            <div style={{
                                                background: 'rgba(251, 191, 36, 0.1)', border: '1px solid rgba(251, 191, 36, 0.3)',
                                                borderRadius: '8px', padding: '12px', marginBottom: '16px'
                                            }}>
                                                <div style={{ display: 'flex', alignItems: 'center', gap: '8px', marginBottom: '8px' }}>
                                                    <AlertTriangle size={18} style={{ color: '#fbbf24' }} />
                                                    <span style={{ color: '#fbbf24', fontWeight: '600', fontSize: '14px' }}>Save Backup Codes</span>
                                                </div>
                                                <p style={{ color: 'rgba(255,255,255,0.7)', fontSize: '13px', margin: 0 }}>
                                                    Store these safely. Use them if you lose your device.
                                                </p>
                                            </div>

                                            <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '6px', marginBottom: '16px' }}>
                                                {backupCodes.map((code, i) => (
                                                    <code key={i} style={{
                                                        background: 'rgba(0,0,0,0.3)', padding: '6px', borderRadius: '4px',
                                                        textAlign: 'center', fontSize: '12px'
                                                    }}>{code}</code>
                                                ))}
                                            </div>

                                            <button onClick={() => copyToClipboard(backupCodes.join('\n'))} className="btn-secondary" style={{ width: '100%', marginBottom: '12px' }}>
                                                <Copy size={16} /> Copy All
                                            </button>
                                        </>
                                    )}

                                    <button onClick={closeModal} className="btn-primary" style={{ width: '100%' }}>
                                        Done
                                    </button>
                                </>
                            )}

                            {/* Close button for steps 1 and 2 */}
                            {setupStep !== 3 && (
                                <button
                                    onClick={closeModal}
                                    style={{
                                        marginTop: '12px', width: '100%', background: 'transparent',
                                        border: '1px solid rgba(255,255,255,0.2)', color: 'rgba(255,255,255,0.6)',
                                        padding: '10px', borderRadius: '8px', cursor: 'pointer'
                                    }}
                                >
                                    Cancel
                                </button>
                            )}
                        </div>
                    </div>
                )}
            </div>
        </Layout>
    )
}

export default TwoFactorSetup
