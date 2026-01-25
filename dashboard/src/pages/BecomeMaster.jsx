import Layout from '../components/Layout'
import { Activity, Shield, DollarSign, Send, Users, Clock, Download, Key, Copy, Check } from 'lucide-react'
import { useState, useEffect } from 'react'
import './Dashboard.css'
import './Auth.css'

const API_URL = 'http://127.0.0.1:8000/api/v1'

function BecomeMaster({ user, onLogout }) {
    const [formData, setFormData] = useState({
        display_name: user?.full_name || '',
        strategy_name: '',
        monthly_fee: '99',
        bio: ''
    })
    const [subscribers, setSubscribers] = useState([])
    const [loading, setLoading] = useState(false)
    const [fetching, setFetching] = useState(true)
    const [isExistingMaster, setIsExistingMaster] = useState(false)
    const [message, setMessage] = useState({ type: '', text: '' })
    const [copiedToken, setCopiedToken] = useState(null)

    const copyToClipboard = (text, tokenId) => {
        navigator.clipboard.writeText(text)
        setCopiedToken(tokenId)
        setTimeout(() => setCopiedToken(null), 2000)
    }

    useEffect(() => {
        if (user?.role === 'master') {
            fetchMasterData()
        } else {
            setFetching(false)
        }
    }, [user])

    const fetchMasterData = async () => {
        try {
            const token = localStorage.getItem('token')
            const headers = { 'Authorization': `Bearer ${token}` }

            // Fetch profile
            const profileRes = await fetch(`${API_URL}/masters/profile/me`, { headers })
            if (profileRes.ok) {
                const profile = await profileRes.json()
                setFormData({
                    display_name: profile.display_name,
                    strategy_name: profile.strategy_name,
                    monthly_fee: profile.monthly_fee.toString(),
                    bio: profile.bio || ''
                })
                setIsExistingMaster(true)
            }

            // Fetch subscribers
            const subsRes = await fetch(`${API_URL}/masters/my/subscribers`, { headers })
            if (subsRes.ok) {
                const subsData = await subsRes.json()
                setSubscribers(subsData)
            }
        } catch (err) {
            console.error('Failed to fetch master data:', err)
        } finally {
            setFetching(false)
        }
    }

    const handleSubmit = async (e) => {
        e.preventDefault()
        setLoading(true)
        setMessage({ type: '', text: '' })

        try {
            const token = localStorage.getItem('token')
            const response = await fetch(`${API_URL}/masters/profile`, {
                method: 'POST',
                headers: {
                    'Authorization': `Bearer ${token}`,
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify(formData)
            })

            const data = await response.json()

            if (!response.ok) {
                throw new Error(data.detail || 'Failed to update profile')
            }

            setMessage({
                type: 'success',
                text: isExistingMaster
                    ? 'Profile updated successfully!'
                    : 'Master profile active! You are now listed in the marketplace.'
            })

            if (!isExistingMaster) {
                // Update local user role
                const updatedUser = { ...user, role: 'master' }
                localStorage.setItem('user', JSON.stringify(updatedUser))
                setIsExistingMaster(true)

                setTimeout(() => {
                    window.location.href = '/marketplace'
                }, 2000)
            }
        } catch (err) {
            setMessage({
                type: 'error',
                text: err.message
            })
        } finally {
            setLoading(false)
        }
    }

    if (fetching) {
        return (
            <Layout user={user} onLogout={onLogout}>
                <div className="loading">Loading Portal...</div>
            </Layout>
        )
    }

    return (
        <Layout user={user} onLogout={onLogout}>
            <div className="dashboard fade-in" style={{
                display: 'flex',
                flexDirection: 'column',
                alignItems: 'center',
                justifyContent: 'center',
                height: 'calc(100vh - 80px)',
                width: '100%',
                padding: '20px',
                overflow: 'hidden'
            }}>

                <div style={{ width: '100%', maxWidth: '600px' }}>

                    <div className="page-header" style={{ textAlign: 'center', marginBottom: '1.5rem' }}>
                        <h1 style={{ fontSize: '1.8rem' }}>{isExistingMaster ? 'Edit Master Profile' : 'Become a Master Trader'}</h1>
                        <p style={{ fontSize: '0.9rem' }}>{isExistingMaster ? 'Update your public profile' : 'Share your trading signals and earn subscription fees'}</p>
                    </div>

                    <div style={{ margin: '0 auto', width: '100%' }}>
                        <form className="auth-card glass" style={{ maxWidth: 'none', marginBottom: '0', padding: '24px' }} onSubmit={handleSubmit}>
                            <div className="form-group">
                                <label>Display Name</label>
                                <div className="input-group">
                                    <Activity size={20} className="input-icon" />
                                    <input
                                        type="text"
                                        placeholder="Your Public Trader Name"
                                        value={formData.display_name}
                                        onChange={(e) => setFormData({ ...formData, display_name: e.target.value })}
                                        required
                                    />
                                </div>
                            </div>

                            <div className="form-group">
                                <label>Strategy Name</label>
                                <div className="input-group">
                                    <Shield size={20} className="input-icon" />
                                    <input
                                        type="text"
                                        placeholder="e.g. Gold Scalper Pro"
                                        value={formData.strategy_name}
                                        onChange={(e) => setFormData({ ...formData, strategy_name: e.target.value })}
                                        required
                                    />
                                </div>
                            </div>

                            <div className="form-group">
                                <label>Monthly Fee (USD)</label>
                                <div className="input-group">
                                    <DollarSign size={20} className="input-icon" />
                                    <input
                                        type="number"
                                        placeholder="99"
                                        value={formData.monthly_fee}
                                        onChange={(e) => setFormData({ ...formData, monthly_fee: e.target.value })}
                                        required
                                    />
                                </div>
                            </div>

                            <div className="form-group">
                                <label>Short Bio</label>
                                <textarea
                                    className="glass"
                                    style={{
                                        width: '100%',
                                        padding: '12px',
                                        borderRadius: '8px',
                                        background: 'rgba(255, 255, 255, 0.05)',
                                        border: '1px solid rgba(255, 255, 255, 0.1)',
                                        color: 'white',
                                        minHeight: '100px',
                                        marginTop: '8px',
                                        resize: 'none'
                                    }}
                                    placeholder="Describe your trading style..."
                                    value={formData.bio}
                                    onChange={(e) => setFormData({ ...formData, bio: e.target.value })}
                                />
                            </div>

                            {message.text && (
                                <p className={message.type === 'error' ? 'error-text' : 'success-text'} style={{ marginBottom: '16px' }}>
                                    {message.text}
                                </p>
                            )}

                            <button className="auth-btn" type="submit" disabled={loading}>
                                {loading ? 'Saving...' : (
                                    <>
                                        <Send size={20} />
                                        {isExistingMaster ? 'Update Profile' : 'Launch Master Profile'}
                                    </>
                                )}
                            </button>

                            {isExistingMaster && (
                                <a
                                    href="/master-dashboard"
                                    style={{
                                        display: 'block',
                                        textAlign: 'center',
                                        marginTop: '16px',
                                        color: '#667eea',
                                        textDecoration: 'none',
                                        fontSize: '14px'
                                    }}
                                >
                                    ← Back to Master Dashboard
                                </a>
                            )}
                        </form>
                    </div>
                </div>
            </div>
        </Layout>
    )
}

export default BecomeMaster
