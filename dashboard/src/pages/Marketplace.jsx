import Layout from '../components/Layout'
import { TrendingUp, Users, Star, DollarSign, Activity, Plus } from 'lucide-react'
import { useState, useEffect } from 'react'
import './Marketplace.css'

const API_URL = 'http://127.0.0.1:8000/api/v1'

// Mock master traders data (in production, this would come from API)
const MOCK_MASTERS = [
    {
        user_id: '550e8400-e29b-41d4-a716-446655440001',
        display_name: 'Alex Thompson',
        strategy_name: 'EUR/USD Scalper',
        bio: 'Professional forex trader with 8+ years experience.',
        monthly_fee: 99.00,
        win_rate: 68.5,
        total_signals: 1247,
        avg_profit: 2.3,
        verified: true
    },
    {
        user_id: '550e8400-e29b-41d4-a716-446655440002',
        display_name: 'Sarah Chen',
        strategy_name: 'Gold Swing Trading',
        bio: 'Gold trading specialist with high reward-to-risk ratio.',
        monthly_fee: 149.00,
        win_rate: 71.2,
        total_signals: 892,
        avg_profit: 3.8,
        verified: true
    }
]

function Marketplace({ user, onLogout }) {
    const [masters, setMasters] = useState([])
    const [loading, setLoading] = useState(true)
    const [selectedMaster, setSelectedMaster] = useState(null)
    const [subscribing, setSubscribing] = useState(false)
    const [message, setMessage] = useState({ type: '', text: '' })

    useEffect(() => {
        fetchMasters()
    }, [])

    const fetchMasters = async () => {
        try {
            const response = await fetch(`${API_URL}/masters/`)
            const data = await response.json()
            if (Array.isArray(data)) {
                setMasters(data)
            } else {
                console.error('Unexpected masters response:', data)
                setMasters([])
            }
        } catch (err) {
            console.error('Failed to fetch masters:', err)
            setMasters([])
        } finally {
            setLoading(false)
        }
    }

    const handleSubscribe = async (master) => {
        setSubscribing(true)
        setMessage({ type: '', text: '' })

        try {
            const token = localStorage.getItem('token')
            const response = await fetch(`${API_URL}/subscriptions`, {
                method: 'POST',
                headers: {
                    'Authorization': `Bearer ${token}`,
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({
                    master_id: master.user_id || master.master_id
                })
            })

            if (response.status === 401) {
                localStorage.removeItem('token')
                localStorage.removeItem('user')
                window.location.href = '/login'
                return
            }

            const data = await response.json()

            if (!response.ok) {
                throw new Error(data.detail || 'Subscription failed')
            }

            setMessage({
                type: 'success',
                text: `Successfully subscribed to ${master.display_name || master.name}! License token: ${data.license_token}`
            })

            // Redirect to subscriptions page after 2 seconds
            setTimeout(() => {
                window.location.href = '/subscriptions'
            }, 2000)
        } catch (err) {
            setMessage({
                type: 'error',
                text: err.message
            })
        } finally {
            setSubscribing(false)
        }
    }

    return (
        <Layout user={user} onLogout={onLogout}>
            <div className="marketplace fade-in">
                <div className="page-header">
                    <h1>Master Trader Marketplace</h1>
                    <p>Browse and subscribe to professional traders</p>
                </div>

                {message.text && (
                    <div className={`message ${message.type === 'success' ? 'success-message' : 'error-message'}`}>
                        {message.text}
                    </div>
                )}

                {loading ? (
                    <div className="loading">Loading marketplace...</div>
                ) : masters.length === 0 ? (
                    <div className="empty-state glass">
                        <Users size={48} style={{ color: '#667eea', marginBottom: '16px' }} />
                        <h3>No Master Traders Yet</h3>
                        <p>The marketplace will populate once traders register their profiles.</p>
                    </div>
                ) : (
                    <div className="masters-grid">
                        {masters.map(master => (
                            <div key={master.user_id} className="master-card glass">
                                <div className="master-header">
                                    <div className="master-avatar">
                                        {master.display_name.split(' ').map(n => n[0]).join('')}
                                    </div>
                                    <div className="master-info">
                                        <h3>{master.display_name}</h3>
                                        <p className="strategy">{master.strategy_name}</p>
                                    </div>
                                    {master.verified && (
                                        <div className="verified-badge" title="Verified Trader">
                                            <Star size={16} fill="currentColor" />
                                        </div>
                                    )}
                                </div>

                                <p className="master-description">{master.bio}</p>

                                <div className="master-stats">
                                    <div className="stat">
                                        <div className="stat-icon" style={{ background: '#667eea20', color: '#667eea' }}>
                                            <Activity size={18} />
                                        </div>
                                        <div>
                                            <p className="stat-label">Trust Score</p>
                                            <p className="stat-value">{master.trust_score || 95}/100</p>
                                        </div>
                                    </div>

                                    <div className="stat">
                                        <div className="stat-icon" style={{ background: '#10b98120', color: '#10b981' }}>
                                            <TrendingUp size={18} />
                                        </div>
                                        <div>
                                            <p className="stat-label">Win Rate</p>
                                            <p className="stat-value">{Number(master.win_rate).toFixed(1)}%</p>
                                        </div>
                                    </div>

                                    <div className="stat">
                                        <div className="stat-icon" style={{ background: '#f59e0b20', color: '#f59e0b' }}>
                                            <DollarSign size={18} />
                                        </div>
                                        <div>
                                            <p className="stat-label">Avg Profit</p>
                                            <p className="stat-value">{Number(master.avg_profit).toFixed(1)}%</p>
                                        </div>
                                    </div>

                                    <div className="stat">
                                        <div className="stat-icon" style={{ background: '#8b5cf620', color: '#8b5cf6' }}>
                                            <Users size={18} />
                                        </div>
                                        <div>
                                            <p className="stat-label">Signals</p>
                                            <p className="stat-value">{master.total_signals}</p>
                                        </div>
                                    </div>
                                </div>

                                <div className="master-footer">
                                    <div className="pricing">
                                        <span className="price">${Number(master.monthly_fee).toFixed(2)}</span>
                                        <span className="period">/month</span>
                                    </div>
                                    <button
                                        className="btn-subscribe"
                                        onClick={() => handleSubscribe(master)}
                                        disabled={subscribing}
                                    >
                                        <Plus size={18} />
                                        {subscribing ? 'Subscribing...' : 'Subscribe'}
                                    </button>
                                </div>
                            </div>
                        ))}
                    </div>
                )}
            </div>
        </Layout>
    )
}

export default Marketplace
