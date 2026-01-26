import Layout from '../components/Layout'
import { useState, useEffect } from 'react'
import { useParams } from 'react-router-dom'
import {
    LineChart, Line, AreaChart, Area, PieChart, Pie, Cell,
    XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer
} from 'recharts'
import { TrendingUp, Users, DollarSign, Activity, ArrowLeft } from 'lucide-react'
import { Link } from 'react-router-dom'
import './PublicAnalytics.css'

const API_URL = 'http://127.0.0.1:8000/api/v1'

const COLORS = {
    primary: '#667eea',
    success: '#10b981',
    danger: '#ef4444',
    warning: '#f59e0b'
}

function PublicAnalytics({ user, onLogout }) {
    const { masterId } = useParams()
    const [timeRange] = useState(6)
    const [loading, setLoading] = useState(true)
    const [masterProfile, setMasterProfile] = useState(null)
    const [overview, setOverview] = useState(null)
    const [performance, setPerformance] = useState(null)

    useEffect(() => {
        fetchPublicAnalytics()
    }, [masterId])

    const fetchPublicAnalytics = async () => {
        setLoading(true)
        try {
            // Fetch master profile
            const profileRes = await fetch(`${API_URL}/masters/${masterId}`)
            const profileData = await profileRes.json()
            setMasterProfile(profileData)

            // For now, show limited public stats from profile
            // In future, could add a public analytics endpoint
            setOverview({
                total_trades: profileData.total_signals || 0,
                win_rate: profileData.win_rate || 0,
                avg_profit: profileData.avg_profit || 0,
                performance_history: profileData.performance_history || []
            })

        } catch (err) {
            console.error('Failed to fetch analytics:', err)
        } finally {
            setLoading(false)
        }
    }

    const preparePerformanceData = () => {
        if (!overview?.performance_history || overview.performance_history.length === 0) return []
        return overview.performance_history.map((val, i) => ({
            index: i + 1,
            profit: val
        }))
    }

    if (loading || !masterProfile) {
        return (
            <Layout user={user} onLogout={onLogout}>
                <div className="public-analytics">
                    <div className="loading">Loading analytics...</div>
                </div>
            </Layout>
        )
    }

    return (
        <Layout user={user} onLogout={onLogout}>
            <div className="public-analytics fade-in">
                <div className="analytics-header">
                    <div>
                        <Link to="/marketplace" className="back-link">
                            <ArrowLeft size={18} />
                            Back to Marketplace
                        </Link>
                        <h1>{masterProfile.display_name}</h1>
                        <p>{masterProfile.strategy_name}</p>
                    </div>
                </div>

                {/* Overview Cards */}
                <div className="metrics-grid">
                    <div className="metric-card glass">
                        <div className="metric-icon" style={{ background: '#f59e0b20', color: '#f59e0b' }}>
                            <TrendingUp size={24} />
                        </div>
                        <div className="metric-content">
                            <p className="metric-label">Win Rate</p>
                            <h2 className="metric-value">{Number(overview.win_rate).toFixed(1)}%</h2>
                            <p className="metric-sub">success rate</p>
                        </div>
                    </div>

                    <div className="metric-card glass">
                        <div className="metric-icon" style={{ background: '#10b98120', color: '#10b981' }}>
                            <DollarSign size={24} />
                        </div>
                        <div className="metric-content">
                            <p className="metric-label">Avg Profit</p>
                            <h2 className="metric-value">{Number(overview.avg_profit).toFixed(1)}%</h2>
                            <p className="metric-sub">per trade</p>
                        </div>
                    </div>

                    <div className="metric-card glass">
                        <div className="metric-icon" style={{ background: '#667eea20', color: '#667eea' }}>
                            <Activity size={24} />
                        </div>
                        <div className="metric-content">
                            <p className="metric-label">Total Signals</p>
                            <h2 className="metric-value">{overview.total_trades}</h2>
                            <p className="metric-sub">trades executed</p>
                        </div>
                    </div>
                </div>

                {/* Performance Chart */}
                {overview.performance_history && overview.performance_history.length > 0 ? (
                    <div className="chart-card glass">
                        <h3>Performance History</h3>
                        <ResponsiveContainer width="100%" height={300}>
                            <LineChart data={preparePerformanceData()}>
                                <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.1)" />
                                <XAxis dataKey="index" stroke="rgba(255,255,255,0.5)" />
                                <YAxis stroke="rgba(255,255,255,0.5)" />
                                <Tooltip
                                    contentStyle={{ background: '#1a1a2e', border: '1px solid rgba(255,255,255,0.1)' }}
                                    labelStyle={{ color: '#fff' }}
                                />
                                <Line type="monotone" dataKey="profit" stroke={COLORS.success} strokeWidth={2} />
                            </LineChart>
                        </ResponsiveContainer>
                    </div>
                ) : (
                    <div className="empty-state glass">
                        <Activity size={48} style={{ color: '#667eea', marginBottom: '16px' }} />
                        <h3>No Performance Data Yet</h3>
                        <p>This master trader hasn't reported any trades yet.</p>
                    </div>
                )}

                {/* About Section */}
                <div className="about-section glass">
                    <h3>About</h3>
                    <p>{masterProfile.bio || 'No description provided.'}</p>
                    <div className="subscription-cta">
                        <div>
                            <p className="fee-label">Subscription Fee</p>
                            <p className="fee-amount">${Number(masterProfile.monthly_fee).toFixed(2)}/month</p>
                        </div>
                        <Link to="/marketplace" className="btn-secondary">
                            View in Marketplace
                        </Link>
                    </div>
                </div>
            </div>
        </Layout>
    )
}

export default PublicAnalytics
