import Layout from '../components/Layout'
import { Users, Plus, Pause, Play, Download, Shield } from 'lucide-react'
import { useState, useEffect } from 'react'
import './Dashboard.css'

const API_URL = 'http://127.0.0.1:8000/api/v1'

function Subscriptions({ user, onLogout }) {
    const [subscriptions, setSubscriptions] = useState([])
    const [loading, setLoading] = useState(true)
    const [message, setMessage] = useState({ type: '', text: '' })
    const [actionLoading, setActionLoading] = useState(null)

    useEffect(() => {
        fetchSubscriptions()
    }, [])

    const fetchSubscriptions = async () => {
        try {
            const token = localStorage.getItem('token')
            const res = await fetch(`${API_URL}/subscriptions`, {
                headers: { 'Authorization': `Bearer ${token}` }
            })

            if (res.status === 401) {
                localStorage.removeItem('token')
                localStorage.removeItem('user')
                window.location.href = '/login'
                return
            }

            const data = await res.json()
            if (Array.isArray(data)) {
                setSubscriptions(data)
            }
        } catch (err) {
            console.error('Failed to fetch subscriptions:', err)
        } finally {
            setLoading(false)
        }
    }

    const handlePause = async (subscriptionId) => {
        setActionLoading(subscriptionId)
        setMessage({ type: '', text: '' })
        console.log(`[Diagnostic] Attempting to PAUSE subscription: ${subscriptionId}`)

        try {
            const token = localStorage.getItem('token')
            const res = await fetch(`${API_URL}/subscriptions/${subscriptionId}/pause/`, {
                method: 'POST',
                headers: {
                    'Authorization': `Bearer ${token}`,
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({})
            })

            console.log(`[Diagnostic] Pause Response Status: ${res.status}`)
            const data = await res.json()

            if (res.ok) {
                setMessage({ type: 'success', text: 'Signal paused successfully!' })
                fetchSubscriptions()
            } else {
                console.error('[Diagnostic] Pause failed:', data)
                setMessage({ type: 'error', text: data.detail || 'Failed to pause signal' })
            }
        } catch (err) {
            console.error('[Diagnostic] Pause error:', err)
            setMessage({ type: 'error', text: `Network error: ${err.message}` })
        } finally {
            setActionLoading(null)
            setTimeout(() => setMessage({ type: '', text: '' }), 3000)
        }
    }

    const handleResume = async (subscriptionId) => {
        setActionLoading(subscriptionId)
        setMessage({ type: '', text: '' })
        console.log(`[Diagnostic] Attempting to RESUME subscription: ${subscriptionId}`)

        try {
            const token = localStorage.getItem('token')
            const res = await fetch(`${API_URL}/subscriptions/${subscriptionId}/resume/`, {
                method: 'POST',
                headers: {
                    'Authorization': `Bearer ${token}`,
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({})
            })

            console.log(`[Diagnostic] Resume Response Status: ${res.status}`)
            const data = await res.json()

            if (res.ok) {
                setMessage({ type: 'success', text: 'Signal resumed successfully!' })
                fetchSubscriptions()
            } else {
                console.error('[Diagnostic] Resume failed:', data)
                setMessage({ type: 'error', text: data.detail || 'Failed to resume signal' })
            }
        } catch (err) {
            console.error('[Diagnostic] Resume error:', err)
            setMessage({ type: 'error', text: `Network error: ${err.message}` })
        } finally {
            setActionLoading(null)
            setTimeout(() => setMessage({ type: '', text: '' }), 3000)
        }
    }

    return (
        <Layout user={user} onLogout={onLogout}>
            <div className="dashboard fade-in">
                <div className="page-header">
                    <h1>Subscriptions</h1>
                    <p>Manage your master trader subscriptions</p>
                </div>

                {message.text && (
                    <div className={`message ${message.type === 'success' ? 'success-message' : 'error-message'}`} style={{ marginBottom: '32px' }}>
                        {message.text}
                    </div>
                )}

                {loading ? (
                    <div className="loading">Loading...</div>
                ) : (
                    <div className="marketplace fade-in" style={{ padding: 0 }}>
                        <div className="masters-grid">
                            {subscriptions.length === 0 ? (
                                <div className="empty-state glass" style={{ gridColumn: '1 / -1' }}>
                                    <Users size={48} style={{ color: '#667eea', marginBottom: '16px' }} />
                                    <h3>No Subscriptions Yet</h3>
                                    <p>Subscribe to master traders to start copying their signals</p>
                                    <button
                                        className="btn-primary"
                                        style={{ marginTop: '16px' }}
                                        onClick={() => window.location.href = '/marketplace'}
                                    >
                                        <Plus size={20} />
                                        Browse Master Traders
                                    </button>
                                </div>
                            ) : (
                                subscriptions.map(sub => (
                                    <div key={sub.subscription_id} className="master-card glass">
                                        <div className="master-header">
                                            <div className="master-avatar">
                                                {(sub.master_name || 'MT').slice(0, 2).toUpperCase()}
                                            </div>
                                            <div className="master-info">
                                                <h3>{sub.master_name || `Master #${sub.master_id.slice(0, 8)}`}</h3>
                                                <p className="strategy">Subscription #{sub.subscription_id.slice(0, 8)}</p>
                                            </div>
                                            <div className={`badge ${sub.is_active ? 'badge-success' : 'badge-danger'}`} style={{ alignSelf: 'center' }}>
                                                {sub.is_active ? 'Active' : 'Inactive'}
                                            </div>
                                        </div>

                                        <div className="master-stats">
                                            <div className="stat">
                                                <div className="stat-icon" style={{ background: '#667eea20', color: '#667eea' }}>
                                                    <Users size={18} />
                                                </div>
                                                <div>
                                                    <p className="stat-label">Status</p>
                                                    <p className="stat-value" style={{ fontSize: '14px' }}>{sub.state}</p>
                                                </div>
                                            </div>

                                            <div className="stat">
                                                <div className="stat-icon" style={{ background: '#10b98120', color: '#10b981' }}>
                                                    <Plus size={18} />
                                                </div>
                                                <div>
                                                    <p className="stat-label">Joined</p>
                                                    <p className="stat-value" style={{ fontSize: '14px' }}>{new Date(sub.created_at).toLocaleDateString()}</p>
                                                </div>
                                            </div>
                                        </div>

                                        <div className="master-footer" style={{ border: 'none', paddingTop: 0, justifyContent: 'center' }}>
                                            {sub.state === 'PAUSED_USER' ? (
                                                <button
                                                    className="btn-subscribe"
                                                    style={{ background: 'rgba(16, 185, 129, 0.2)', color: '#10b981', border: '1px solid rgba(16, 185, 129, 0.3)' }}
                                                    onClick={() => handleResume(sub.subscription_id)}
                                                    disabled={actionLoading === sub.subscription_id}
                                                >
                                                    <Play size={18} />
                                                    {actionLoading === sub.subscription_id ? 'Resuming...' : 'Resume Trading'}
                                                </button>
                                            ) : (
                                                <button
                                                    className="btn-subscribe"
                                                    style={{ background: 'rgba(239, 68, 68, 0.1)', color: '#fca5a5', border: '1px solid rgba(239, 68, 68, 0.2)' }}
                                                    onClick={() => handlePause(sub.subscription_id)}
                                                    disabled={actionLoading === sub.subscription_id}
                                                >
                                                    <Pause size={18} />
                                                    {actionLoading === sub.subscription_id ? 'Pausing...' : 'Pause Signals'}
                                                </button>
                                            )}
                                        </div>
                                    </div>
                                ))
                            )}
                        </div>

                        <div className="dashboard-card glass" style={{ marginTop: '48px', maxWidth: 'none' }}>
                            <div className="sub-header">
                                <div>
                                    <h3 style={{ fontSize: '20px', fontWeight: '600' }}>Receiver EA Setup</h3>
                                    <p className="text-muted">Install the Signal Receiver on your MT5 platform to start copying trades</p>
                                </div>
                                <Shield size={32} style={{ color: '#10b981' }} />
                            </div>
                            <div className="setup-instructions" style={{ margin: '24px 0', fontSize: '1rem', color: 'rgba(255, 255, 255, 0.8)' }}>
                                <p style={{ marginBottom: '12px' }}>1. Download the compiled Signal Receiver (<strong>SignalReceiverEA.ex5</strong>).</p>
                                <p style={{ marginBottom: '12px' }}>2. Move the file to your MT5 terminal's <strong>MQL5/Experts</strong> folder.</p>
                                <p style={{ marginBottom: '0' }}>3. Attach the EA to any chart and enter your License Token when prompted.</p>
                            </div>
                            <div className="sub-actions" style={{ justifyContent: 'flex-start', border: 'none', paddingTop: 0 }}>
                                <a
                                    href="http://localhost:8000/static/downloads/SignalReceiverEA.ex5"
                                    download
                                    className="btn-primary"
                                    style={{ textDecoration: 'none', display: 'flex', alignItems: 'center', gap: '8px', padding: '14px 28px' }}
                                >
                                    <Download size={20} />
                                    Download SignalReceiverEA.ex5
                                </a>
                            </div>
                        </div>
                    </div>
                )}
            </div>
        </Layout>
    )
}

export default Subscriptions
