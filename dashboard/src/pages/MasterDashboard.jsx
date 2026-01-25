import Layout from '../components/Layout'
import { Activity, Users, Clock, Download, Key, Copy, Check, TrendingUp, DollarSign, BarChart3, Send } from 'lucide-react'
import { useState, useEffect } from 'react'
import './Dashboard.css'

const API_URL = 'http://127.0.0.1:8000/api/v1'

function MasterDashboard({ user, onLogout }) {
    const [profile, setProfile] = useState(null)
    const [subscribers, setSubscribers] = useState([])
    const [loading, setLoading] = useState(true)
    const [copiedToken, setCopiedToken] = useState(null)

    const copyToClipboard = (text, tokenId) => {
        navigator.clipboard.writeText(text)
        setCopiedToken(tokenId)
        setTimeout(() => setCopiedToken(null), 2000)
    }

    useEffect(() => {
        fetchMasterData()
    }, [])

    const fetchMasterData = async () => {
        try {
            const token = localStorage.getItem('token')
            const headers = { 'Authorization': `Bearer ${token}` }

            const profileRes = await fetch(`${API_URL}/masters/profile/me`, { headers })
            if (profileRes.ok) {
                const profileData = await profileRes.json()
                setProfile(profileData)
            }

            const subsRes = await fetch(`${API_URL}/masters/my/subscribers`, { headers })
            if (subsRes.ok) {
                const subsData = await subsRes.json()
                setSubscribers(subsData)
            }
        } catch (err) {
            console.error('Failed to fetch master data:', err)
        } finally {
            setLoading(false)
        }
    }

    if (loading) {
        return (
            <Layout user={user} onLogout={onLogout}>
                <div className="loading">Loading Master Dashboard...</div>
            </Layout>
        )
    }

    if (!profile) {
        window.location.href = '/become-master'
        return null
    }

    return (
        <Layout user={user} onLogout={onLogout}>
            <div className="dashboard fade-in">
                <div className="page-header">
                    <h1>Master Dashboard</h1>
                    <p>Manage your trading signals and subscribers</p>
                </div>

                {/* Stats Row */}
                <div className="masters-grid" style={{ marginBottom: '32px' }}>
                    <div className="master-card glass" style={{ padding: '24px' }}>
                        <div style={{ display: 'flex', alignItems: 'center', gap: '16px' }}>
                            <div style={{
                                background: 'linear-gradient(135deg, #667eea 0%, #764ba2 100%)',
                                borderRadius: '12px',
                                padding: '14px',
                                display: 'flex',
                                alignItems: 'center',
                                justifyContent: 'center'
                            }}>
                                <Users size={24} color="white" />
                            </div>
                            <div>
                                <p style={{ color: 'rgba(255,255,255,0.6)', fontSize: '14px', marginBottom: '4px' }}>Total Subscribers</p>
                                <p style={{ fontSize: '28px', fontWeight: '700', color: 'white' }}>{subscribers.length}</p>
                            </div>
                        </div>
                    </div>

                    <div className="master-card glass" style={{ padding: '24px' }}>
                        <div style={{ display: 'flex', alignItems: 'center', gap: '16px' }}>
                            <div style={{
                                background: 'linear-gradient(135deg, #10b981 0%, #059669 100%)',
                                borderRadius: '12px',
                                padding: '14px',
                                display: 'flex',
                                alignItems: 'center',
                                justifyContent: 'center'
                            }}>
                                <DollarSign size={24} color="white" />
                            </div>
                            <div>
                                <p style={{ color: 'rgba(255,255,255,0.6)', fontSize: '14px', marginBottom: '4px' }}>Monthly Fee</p>
                                <p style={{ fontSize: '28px', fontWeight: '700', color: 'white' }}>${profile.monthly_fee}</p>
                            </div>
                        </div>
                    </div>

                    <div className="master-card glass" style={{ padding: '24px' }}>
                        <div style={{ display: 'flex', alignItems: 'center', gap: '16px' }}>
                            <div style={{
                                background: 'linear-gradient(135deg, #f59e0b 0%, #d97706 100%)',
                                borderRadius: '12px',
                                padding: '14px',
                                display: 'flex',
                                alignItems: 'center',
                                justifyContent: 'center'
                            }}>
                                <TrendingUp size={24} color="white" />
                            </div>
                            <div>
                                <p style={{ color: 'rgba(255,255,255,0.6)', fontSize: '14px', marginBottom: '4px' }}>Est. Revenue</p>
                                <p style={{ fontSize: '28px', fontWeight: '700', color: 'white' }}>${subscribers.length * profile.monthly_fee}</p>
                            </div>
                        </div>
                    </div>
                </div>

                {/* Two Column Layout */}
                <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '24px' }}>

                    {/* Left Column - Subscribers */}
                    <div className="dashboard-card glass">
                        <div className="sub-header" style={{ marginBottom: '20px' }}>
                            <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
                                <Users size={24} style={{ color: '#667eea' }} />
                                <h3 style={{ margin: 0 }}>My Subscribers</h3>
                            </div>
                            <span className="badge badge-success">{subscribers.length} Active</span>
                        </div>

                        <div className="status-list" style={{ maxHeight: '300px', overflowY: 'auto' }}>
                            {subscribers.length === 0 ? (
                                <p className="text-muted" style={{ textAlign: 'center', padding: '20px' }}>
                                    No subscribers yet. Your profile is live in the marketplace!
                                </p>
                            ) : (
                                subscribers.map(sub => (
                                    <div key={sub.subscription_id} className="status-item">
                                        <div style={{ display: 'flex', flexDirection: 'column', gap: '4px' }}>
                                            <span style={{ color: 'white', fontWeight: 500 }}>{sub.email}</span>
                                            <span className="text-muted" style={{ fontSize: '12px', display: 'flex', alignItems: 'center', gap: '4px' }}>
                                                <Clock size={12} /> Joined {new Date(sub.created_at).toLocaleDateString()}
                                            </span>
                                        </div>
                                        <span className={`badge ${sub.is_active ? 'badge-success' : 'badge-danger'}`}>
                                            {sub.state}
                                        </span>
                                    </div>
                                ))
                            )}
                        </div>
                    </div>

                    {/* Right Column - Signal Sender EA */}
                    <div className="dashboard-card glass">
                        <div className="sub-header" style={{ marginBottom: '20px' }}>
                            <div>
                                <h3 style={{ fontSize: '18px', fontWeight: '600', margin: 0 }}>Signal Sender EA</h3>
                                <p className="text-muted" style={{ fontSize: '13px', marginTop: '4px' }}>Broadcast trades to subscribers</p>
                            </div>
                            <Download size={24} style={{ color: '#10b981' }} />
                        </div>

                        {/* EA Configuration */}
                        <div style={{
                            background: 'rgba(102, 126, 234, 0.1)',
                            borderRadius: '12px',
                            padding: '16px',
                            border: '1px solid rgba(102, 126, 234, 0.2)'
                        }}>
                            <div style={{ display: 'flex', alignItems: 'center', gap: '8px', marginBottom: '12px' }}>
                                <Key size={16} style={{ color: '#667eea' }} />
                                <span style={{ fontSize: '13px', fontWeight: '600', color: '#667eea' }}>EA Configuration</span>
                            </div>

                            <div style={{ display: 'grid', gap: '12px' }}>
                                {/* Subscription ID */}
                                <div>
                                    <p style={{ fontSize: '11px', color: 'rgba(255,255,255,0.5)', marginBottom: '4px' }}>Subscription ID</p>
                                    <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
                                        <code style={{ fontSize: '11px', background: 'rgba(0,0,0,0.3)', padding: '8px 10px', borderRadius: '6px', flex: 1, color: '#10b981', overflow: 'hidden', textOverflow: 'ellipsis' }}>
                                            {user?.user_id || 'MASTER-DEFAULT'}
                                        </code>
                                        <button onClick={() => copyToClipboard(user?.user_id || 'MASTER-DEFAULT', 'sub-id')}
                                            style={{ background: 'rgba(16, 185, 129, 0.2)', border: 'none', borderRadius: '6px', padding: '8px', cursor: 'pointer', color: '#10b981' }}>
                                            {copiedToken === 'sub-id' ? <Check size={14} /> : <Copy size={14} />}
                                        </button>
                                    </div>
                                </div>

                                {/* Secret Key */}
                                <div>
                                    <p style={{ fontSize: '11px', color: 'rgba(255,255,255,0.5)', marginBottom: '4px' }}>Secret Key</p>
                                    <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
                                        <code style={{ fontSize: '11px', background: 'rgba(0,0,0,0.3)', padding: '8px 10px', borderRadius: '6px', flex: 1, color: '#fbbf24' }}>
                                            ea-sync-secret-key-2026
                                        </code>
                                        <button onClick={() => copyToClipboard('ea-sync-secret-key-2026', 'secret')}
                                            style={{ background: 'rgba(251, 191, 36, 0.2)', border: 'none', borderRadius: '6px', padding: '8px', cursor: 'pointer', color: '#fbbf24' }}>
                                            {copiedToken === 'secret' ? <Check size={14} /> : <Copy size={14} />}
                                        </button>
                                    </div>
                                </div>

                                {/* Ingest Server */}
                                <div>
                                    <p style={{ fontSize: '11px', color: 'rgba(255,255,255,0.5)', marginBottom: '4px' }}>Ingest Server</p>
                                    <div style={{ display: 'flex', gap: '8px' }}>
                                        <code style={{ fontSize: '11px', background: 'rgba(0,0,0,0.3)', padding: '8px 10px', borderRadius: '6px', flex: 1, color: '#a78bfa' }}>
                                            127.0.0.1:9000
                                        </code>
                                        <button onClick={() => copyToClipboard('127.0.0.1', 'host')}
                                            style={{ background: 'rgba(167, 139, 250, 0.2)', border: 'none', borderRadius: '6px', padding: '8px', cursor: 'pointer', color: '#a78bfa' }}>
                                            {copiedToken === 'host' ? <Check size={14} /> : <Copy size={14} />}
                                        </button>
                                    </div>
                                </div>
                            </div>
                        </div>

                        <div style={{ marginTop: '16px' }}>
                            <a href="http://127.0.0.1:8000/static/downloads/SignalSenderEA.ex5" download
                                className="btn-primary" style={{ textDecoration: 'none', display: 'flex', alignItems: 'center', justifyContent: 'center', gap: '8px', padding: '12px 20px', width: '100%' }}>
                                <Download size={18} />
                                Download SignalSenderEA.ex5
                            </a>
                        </div>
                    </div>
                </div>

                {/* Edit Profile Link */}
                <div style={{ marginTop: '24px', textAlign: 'center' }}>
                    <a href="/become-master" style={{ color: '#667eea', textDecoration: 'none', fontSize: '14px' }}>
                        Edit Profile Settings →
                    </a>
                </div>
            </div>
        </Layout>
    )
}

export default MasterDashboard
