import Layout from '../components/Layout'
import { TrendingUp, Users, Star, DollarSign, Activity, Plus } from 'lucide-react'
import { useState } from 'react'
import './Marketplace.css'

const API_URL = 'http://localhost:8000/api/v1'

// Mock master traders data (in production, this would come from API)
const MOCK_MASTERS = [
    {
        master_id: '550e8400-e29b-41d4-a716-446655440001',
        name: 'Alex Thompson',
        strategy: 'Scalping EUR/USD',
        trust_score: 95,
        total_signals: 1247,
        win_rate: 68.5,
        avg_profit: 2.3,
        subscribers: 156,
        monthly_fee: 99.00,
        description: 'Professional forex trader with 8+ years experience. Specializes in EUR/USD scalping with strict risk management.',
        verified: true
    },
    {
        master_id: '550e8400-e29b-41d4-a716-446655440002',
        name: 'Sarah Chen',
        strategy: 'Swing Trading Gold',
        trust_score: 88,
        total_signals: 892,
        win_rate: 71.2,
        avg_profit: 3.8,
        subscribers: 203,
        monthly_fee: 149.00,
        description: 'Gold trading specialist. Focus on medium-term swing trades with high reward-to-risk ratio.',
        verified: true
    },
    {
        master_id: '550e8400-e29b-41d4-a716-446655440003',
        name: 'Marcus Rodriguez',
        strategy: 'Multi-Pair Day Trading',
        trust_score: 92,
        total_signals: 2103,
        win_rate: 64.8,
        avg_profit: 1.9,
        subscribers: 89,
        monthly_fee: 79.00,
        description: 'Day trader covering major currency pairs. High-frequency signals with consistent returns.',
        verified: true
    }
]

function Marketplace({ user, onLogout }) {
    const [selectedMaster, setSelectedMaster] = useState(null)
    const [subscribing, setSubscribing] = useState(false)
    const [message, setMessage] = useState({ type: '', text: '' })

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
                    master_id: master.master_id
                })
            })

            const data = await response.json()

            if (!response.ok) {
                throw new Error(data.detail || 'Subscription failed')
            }

            setMessage({
                type: 'success',
                text: `Successfully subscribed to ${master.name}! License token: ${data.license_token}`
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

                <div className="masters-grid">
                    {MOCK_MASTERS.map(master => (
                        <div key={master.master_id} className="master-card glass">
                            <div className="master-header">
                                <div className="master-avatar">
                                    {master.name.split(' ').map(n => n[0]).join('')}
                                </div>
                                <div className="master-info">
                                    <h3>{master.name}</h3>
                                    <p className="strategy">{master.strategy}</p>
                                </div>
                                {master.verified && (
                                    <div className="verified-badge" title="Verified Trader">
                                        <Star size={16} fill="currentColor" />
                                    </div>
                                )}
                            </div>

                            <p className="master-description">{master.description}</p>

                            <div className="master-stats">
                                <div className="stat">
                                    <div className="stat-icon" style={{ background: '#667eea20', color: '#667eea' }}>
                                        <Activity size={18} />
                                    </div>
                                    <div>
                                        <p className="stat-label">Trust Score</p>
                                        <p className="stat-value">{master.trust_score}/100</p>
                                    </div>
                                </div>

                                <div className="stat">
                                    <div className="stat-icon" style={{ background: '#10b98120', color: '#10b981' }}>
                                        <TrendingUp size={18} />
                                    </div>
                                    <div>
                                        <p className="stat-label">Win Rate</p>
                                        <p className="stat-value">{master.win_rate}%</p>
                                    </div>
                                </div>

                                <div className="stat">
                                    <div className="stat-icon" style={{ background: '#f59e0b20', color: '#f59e0b' }}>
                                        <DollarSign size={18} />
                                    </div>
                                    <div>
                                        <p className="stat-label">Avg Profit</p>
                                        <p className="stat-value">{master.avg_profit}%</p>
                                    </div>
                                </div>

                                <div className="stat">
                                    <div className="stat-icon" style={{ background: '#8b5cf620', color: '#8b5cf6' }}>
                                        <Users size={18} />
                                    </div>
                                    <div>
                                        <p className="stat-label">Subscribers</p>
                                        <p className="stat-value">{master.subscribers}</p>
                                    </div>
                                </div>
                            </div>

                            <div className="master-footer">
                                <div className="pricing">
                                    <span className="price">${master.monthly_fee}</span>
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
            </div>
        </Layout>
    )
}

export default Marketplace
