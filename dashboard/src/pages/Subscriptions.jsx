import Layout from '../components/Layout'
import { Users, Plus, Pause, Play } from 'lucide-react'
import { useState, useEffect } from 'react'
import './Dashboard.css'

const API_URL = 'http://localhost:8000/api/v1'

function Subscriptions({ user, onLogout }) {
    const [subscriptions, setSubscriptions] = useState([])
    const [loading, setLoading] = useState(true)

    useEffect(() => {
        fetchSubscriptions()
    }, [])

    const fetchSubscriptions = async () => {
        try {
            const token = localStorage.getItem('token')
            const res = await fetch(`${API_URL}/subscriptions`, {
                headers: { 'Authorization': `Bearer ${token}` }
            })
            const data = await res.json()
            setSubscriptions(data)
        } catch (err) {
            console.error('Failed to fetch subscriptions:', err)
        } finally {
            setLoading(false)
        }
    }

    return (
        <Layout user={user} onLogout={onLogout}>
            <div className="dashboard fade-in">
                <div className="page-header">
                    <h1>Subscriptions</h1>
                    <p>Manage your master trader subscriptions</p>
                </div>

                {loading ? (
                    <div className="loading">Loading...</div>
                ) : (
                    <div className="subscriptions-list">
                        {subscriptions.length === 0 ? (
                            <div className="empty-state glass">
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
                                <div key={sub.subscription_id} className="dashboard-card glass">
                                    <div className="sub-header">
                                        <div>
                                            <h3>Subscription #{sub.subscription_id.slice(0, 8)}</h3>
                                            <p className="text-muted">Master: {sub.master_id.slice(0, 8)}</p>
                                        </div>
                                        <span className={`badge ${sub.is_active ? 'badge-success' : 'badge-danger'}`}>
                                            {sub.is_active ? 'Active' : 'Inactive'}
                                        </span>
                                    </div>
                                    <div className="status-list">
                                        <div className="status-item">
                                            <span>State</span>
                                            <span>{sub.state}</span>
                                        </div>
                                        <div className="status-item">
                                            <span>Created</span>
                                            <span className="text-muted">{new Date(sub.created_at).toLocaleDateString()}</span>
                                        </div>
                                    </div>
                                    <div className="sub-actions">
                                        {sub.state === 'PAUSED_USER' ? (
                                            <button className="action-btn">
                                                <Play size={16} />
                                                Resume
                                            </button>
                                        ) : (
                                            <button className="action-btn">
                                                <Pause size={16} />
                                                Pause
                                            </button>
                                        )}
                                    </div>
                                </div>
                            ))
                        )}
                    </div>
                )}
            </div>
        </Layout>
    )
}

export default Subscriptions
