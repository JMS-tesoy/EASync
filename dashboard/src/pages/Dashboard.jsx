import { useState, useEffect } from 'react'
import Layout from '../components/Layout'
import { TrendingUp, Users, DollarSign, Shield, Activity } from 'lucide-react'
import './Dashboard.css'

const API_URL = 'http://localhost:8000/api/v1'

function Dashboard({ user, onLogout }) {
    const [stats, setStats] = useState({
        subscriptions: 0,
        balance: 0,
        protectionEvents: 0,
        trustScore: user?.trust_score || 100
    })
    const [loading, setLoading] = useState(true)

    useEffect(() => {
        fetchDashboardData()
    }, [])

    const fetchDashboardData = async () => {
        try {
            const token = localStorage.getItem('token')
            const headers = { 'Authorization': `Bearer ${token}` }

            // Fetch wallet
            const walletRes = await fetch(`${API_URL}/wallet`, { headers })
            const wallet = await walletRes.json()

            // Fetch subscriptions
            const subsRes = await fetch(`${API_URL}/subscriptions`, { headers })
            const subs = await subsRes.json()

            // Fetch protection events
            const eventsRes = await fetch(`${API_URL}/protection-events?hours=24`, { headers })
            const events = await eventsRes.json()

            setStats({
                subscriptions: subs.length,
                balance: wallet.balance_usd,
                protectionEvents: events.length,
                trustScore: user?.trust_score || 100
            })
        } catch (err) {
            console.error('Failed to fetch dashboard data:', err)
        } finally {
            setLoading(false)
        }
    }

    const statCards = [
        {
            icon: Users,
            label: 'Active Subscriptions',
            value: stats.subscriptions,
            color: '#667eea'
        },
        {
            icon: DollarSign,
            label: 'Wallet Balance',
            value: `$${(Number(stats.balance) || 0).toFixed(2)}`,
            color: '#10b981'
        },
        {
            icon: Shield,
            label: 'Trust Score',
            value: stats.trustScore,
            color: stats.trustScore >= 70 ? '#10b981' : stats.trustScore >= 40 ? '#f59e0b' : '#ef4444'
        },
        {
            icon: Activity,
            label: 'Protection Events (24h)',
            value: stats.protectionEvents,
            color: '#8b5cf6'
        }
    ]

    return (
        <Layout user={user} onLogout={onLogout}>
            <div className="dashboard fade-in">
                <div className="page-header">
                    <h1>Dashboard</h1>
                    <p>Welcome back, {user?.full_name || 'Trader'}!</p>
                </div>

                {loading ? (
                    <div className="loading">Loading...</div>
                ) : (
                    <>
                        <div className="stats-grid">
                            {statCards.map((stat, index) => (
                                <div key={index} className="stat-card glass">
                                    <div className="stat-icon" style={{ background: `${stat.color}20`, color: stat.color }}>
                                        <stat.icon size={24} />
                                    </div>
                                    <div className="stat-content">
                                        <p className="stat-label">{stat.label}</p>
                                        <h2 className="stat-value">{stat.value}</h2>
                                    </div>
                                </div>
                            ))}
                        </div>

                        <div className="dashboard-grid">
                            <div className="dashboard-card glass">
                                <h3>Quick Actions</h3>
                                <div className="quick-actions">
                                    <button className="action-btn" onClick={() => window.location.href = '/marketplace'}>
                                        <TrendingUp size={20} />
                                        Marketplace
                                    </button>
                                    <button className="action-btn" onClick={() => window.location.href = '/subscriptions'}>
                                        <Users size={20} />
                                        Manage Subscriptions
                                    </button>
                                    <button className="action-btn" onClick={() => window.location.href = '/wallet'}>
                                        <DollarSign size={20} />
                                        Add Funds
                                    </button>
                                </div>
                            </div>

                            <div className="dashboard-card glass">
                                <h3>Account Status</h3>
                                <div className="status-list">
                                    <div className="status-item">
                                        <span>Account Status</span>
                                        <span className="badge badge-success">Active</span>
                                    </div>
                                    <div className="status-item">
                                        <span>Trust Score</span>
                                        <span className={`badge ${stats.trustScore >= 70 ? 'badge-success' :
                                            stats.trustScore >= 40 ? 'badge-warning' :
                                                'badge-danger'
                                            }`}>{stats.trustScore}/100</span>
                                    </div>
                                    <div className="status-item">
                                        <span>Email</span>
                                        <span className="text-muted">{user?.email}</span>
                                    </div>
                                </div>
                            </div>
                        </div>
                    </>
                )}
            </div>
        </Layout>
    )
}

export default Dashboard
