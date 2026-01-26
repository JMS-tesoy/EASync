import Layout from '../components/Layout'
import { useState, useEffect } from 'react'
import {
    LineChart, Line, AreaChart, Area, PieChart, Pie, Cell,
    XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer
} from 'recharts'
import {
    TrendingUp, Users, DollarSign, Activity, Download,
    Calendar, BarChart2
} from 'lucide-react'
import './MasterAnalytics.css'

const API_URL = 'http://127.0.0.1:8000/api/v1'

const COLORS = {
    primary: '#667eea',
    success: '#10b981',
    danger: '#ef4444',
    warning: '#f59e0b'
}

function MasterAnalytics({ user, onLogout }) {
    const [timeRange, setTimeRange] = useState(6)
    const [loading, setLoading] = useState(true)
    const [overview, setOverview] = useState(null)
    const [subscriberGrowth, setSubscriberGrowth] = useState(null)
    const [revenueTrend, setRevenueTrend] = useState(null)
    const [performance, setPerformance] = useState(null)
    const [recentTrades, setRecentTrades] = useState([])
    const [currentPage, setCurrentPage] = useState(1)
    const tradesPerPage = 5

    useEffect(() => {
        fetchAnalytics()
    }, [timeRange])

    const fetchAnalytics = async () => {
        setLoading(true)
        const token = localStorage.getItem('token')
        const headers = { 'Authorization': `Bearer ${token}` }

        try {
            const [overviewRes, growthRes, revenueRes, perfRes, tradesRes] = await Promise.all([
                fetch(`${API_URL}/analytics/overview`, { headers }),
                fetch(`${API_URL}/analytics/subscriber-growth?months=${timeRange}`, { headers }),
                fetch(`${API_URL}/analytics/revenue-trend?months=${timeRange}`, { headers }),
                fetch(`${API_URL}/analytics/performance?months=${timeRange}`, { headers }),
                fetch(`${API_URL}/analytics/recent-trades?limit=20`, { headers })
            ])

            setOverview(await overviewRes.json())
            setSubscriberGrowth(await growthRes.json())
            setRevenueTrend(await revenueRes.json())
            setPerformance(await perfRes.json())
            setRecentTrades(await tradesRes.json())
        } catch (err) {
            console.error('Failed to fetch analytics:', err)
        } finally {
            setLoading(false)
        }
    }

    const exportToCSV = () => {
        if (!recentTrades.length) return

        const headers = ['Trade ID', 'Symbol', 'Type', 'Open Price', 'Close Price', 'Profit', 'Opened At', 'Closed At']
        const rows = recentTrades.map(t => [
            t.trade_id,
            t.symbol,
            t.type,
            t.open_price,
            t.close_price,
            t.profit,
            new Date(t.opened_at).toLocaleString(),
            new Date(t.closed_at).toLocaleString()
        ])

        const csvContent = [
            headers.join(','),
            ...rows.map(row => row.join(','))
        ].join('\\n')

        const blob = new Blob([csvContent], { type: 'text/csv' })
        const url = window.URL.createObjectURL(blob)
        const a = document.createElement('a')
        a.href = url
        a.download = `trades_${new Date().toISOString().split('T')[0]}.csv`
        a.click()
        window.URL.revokeObjectURL(url)
    }

    const prepareSubscriberData = () => {
        if (!subscriberGrowth) return []
        return subscriberGrowth.labels.map((label, i) => ({
            month: label,
            subscribers: subscriberGrowth.data[i]
        }))
    }

    const prepareRevenueData = () => {
        if (!revenueTrend) return []
        return revenueTrend.labels.map((label, i) => ({
            month: label,
            revenue: revenueTrend.data[i]
        }))
    }

    const prepareProfitData = () => {
        if (!performance) return []
        return performance.profit_timeline.labels.map((label, i) => ({
            month: label,
            profit: performance.profit_timeline.data[i]
        }))
    }

    const prepareWinRateData = () => {
        if (!performance) return []
        return performance.win_rate_trend.labels.map((label, i) => ({
            month: label,
            winRate: performance.win_rate_trend.data[i]
        }))
    }

    const prepareDistributionData = () => {
        if (!performance) return []
        return [
            { name: 'Wins', value: performance.trade_distribution.wins },
            { name: 'Losses', value: performance.trade_distribution.losses }
        ]
    }

    // Pagination logic
    const indexOfLastTrade = currentPage * tradesPerPage
    const indexOfFirstTrade = indexOfLastTrade - tradesPerPage
    const currentTrades = recentTrades.slice(indexOfFirstTrade, indexOfLastTrade)
    const totalPages = Math.ceil(recentTrades.length / tradesPerPage)

    if (loading || !overview) {
        return (
            <Layout user={user} onLogout={onLogout}>
                <div className="analytics-page">
                    <div className="loading">Loading analytics...</div>
                </div>
            </Layout>
        )
    }

    return (
        <Layout user={user} onLogout={onLogout}>
            <div className="analytics-page fade-in">
                <div className="analytics-header">
                    <div>
                        <h1>Master Analytics Dashboard</h1>
                        <p>Track your performance and subscriber metrics</p>
                    </div>
                    <div className="header-controls">
                        <div className="time-range-selector">
                            <Calendar size={18} />
                            <select value={timeRange} onChange={(e) => setTimeRange(Number(e.target.value))}>
                                <option value={3}>Last 3 Months</option>
                                <option value={6}>Last 6 Months</option>
                                <option value={12}>Last 12 Months</option>
                            </select>
                        </div>
                        <button className="btn-export" onClick={exportToCSV}>
                            <Download size={18} />
                            Export CSV
                        </button>
                    </div>
                </div>

                {/* Overview Cards */}
                <div className="metrics-grid">
                    <div className="metric-card glass">
                        <div className="metric-icon" style={{ background: '#667eea20', color: '#667eea' }}>
                            <Users size={24} />
                        </div>
                        <div className="metric-content">
                            <p className="metric-label">Total Subscribers</p>
                            <h2 className="metric-value">{overview.total_subscribers}</h2>
                            <p className="metric-sub">{overview.active_subscribers} active</p>
                        </div>
                    </div>

                    <div className="metric-card glass">
                        <div className="metric-icon" style={{ background: '#10b98120', color: '#10b981' }}>
                            <DollarSign size={24} />
                        </div>
                        <div className="metric-content">
                            <p className="metric-label">Monthly Revenue</p>
                            <h2 className="metric-value">${overview.monthly_revenue.toFixed(2)}</h2>
                            <p className="metric-sub">from active subscribers</p>
                        </div>
                    </div>

                    <div className="metric-card glass">
                        <div className="metric-icon" style={{ background: '#f59e0b20', color: '#f59e0b' }}>
                            <TrendingUp size={24} />
                        </div>
                        <div className="metric-content">
                            <p className="metric-label">Win Rate</p>
                            <h2 className="metric-value">{overview.win_rate.toFixed(1)}%</h2>
                            <p className="metric-sub">of {overview.total_trades} trades</p>
                        </div>
                    </div>

                    <div className="metric-card glass">
                        <div className="metric-icon" style={{ background: '#8b5cf620', color: '#8b5cf6' }}>
                            <Activity size={24} />
                        </div>
                        <div className="metric-content">
                            <p className="metric-label">Total Profit</p>
                            <h2 className="metric-value" style={{ color: overview.total_profit >= 0 ? '#10b981' : '#ef4444' }}>
                                ${overview.total_profit.toFixed(2)}
                            </h2>
                            <p className="metric-sub">lifetime earnings</p>
                        </div>
                    </div>
                </div>

                {/* Charts Row 1 */}
                <div className="charts-row">
                    <div className="chart-card glass">
                        <h3>Subscriber Growth</h3>
                        <ResponsiveContainer width="100%" height={250}>
                            <LineChart data={prepareSubscriberData()}>
                                <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.1)" />
                                <XAxis dataKey="month" stroke="rgba(255,255,255,0.5)" />
                                <YAxis stroke="rgba(255,255,255,0.5)" />
                                <Tooltip
                                    contentStyle={{ background: '#1a1a2e', border: '1px solid rgba(255,255,255,0.1)' }}
                                    labelStyle={{ color: '#fff' }}
                                />
                                <Line type="monotone" dataKey="subscribers" stroke={COLORS.primary} strokeWidth={2} />
                            </LineChart>
                        </ResponsiveContainer>
                    </div>

                    <div className="chart-card glass">
                        <h3>Revenue Trend</h3>
                        <ResponsiveContainer width="100%" height={250}>
                            <AreaChart data={prepareRevenueData()}>
                                <defs>
                                    <linearGradient id="colorRevenue" x1="0" y1="0" x2="0" y2="1">
                                        <stop offset="5%" stopColor={COLORS.success} stopOpacity={0.3} />
                                        <stop offset="95%" stopColor={COLORS.success} stopOpacity={0} />
                                    </linearGradient>
                                </defs>
                                <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.1)" />
                                <XAxis dataKey="month" stroke="rgba(255,255,255,0.5)" />
                                <YAxis stroke="rgba(255,255,255,0.5)" />
                                <Tooltip
                                    contentStyle={{ background: '#1a1a2e', border: '1px solid rgba(255,255,255,0.1)' }}
                                    labelStyle={{ color: '#fff' }}
                                />
                                <Area type="monotone" dataKey="revenue" stroke={COLORS.success} fillOpacity={1} fill="url(#colorRevenue)" />
                            </AreaChart>
                        </ResponsiveContainer>
                    </div>
                </div>

                {/* Charts Row 2 */}
                <div className="charts-row">
                    <div className="chart-card glass">
                        <h3>Cumulative Profit</h3>
                        <ResponsiveContainer width="100%" height={250}>
                            <LineChart data={prepareProfitData()}>
                                <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.1)" />
                                <XAxis dataKey="month" stroke="rgba(255,255,255,0.5)" />
                                <YAxis stroke="rgba(255,255,255,0.5)" />
                                <Tooltip
                                    contentStyle={{ background: '#1a1a2e', border: '1px solid rgba(255,255,255,0.1)' }}
                                    labelStyle={{ color: '#fff' }}
                                />
                                <Line type="monotone" dataKey="profit" stroke={COLORS.success} strokeWidth={2} />
                            </LineChart>
                        </ResponsiveContainer>
                    </div>

                    <div className="chart-card glass" style={{ display: 'flex', flexDirection: 'column', gap: '20px' }}>
                        <div style={{ flex: 1 }}>
                            <h3>Win Rate Trend</h3>
                            <ResponsiveContainer width="100%" height={120}>
                                <LineChart data={prepareWinRateData()}>
                                    <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.1)" />
                                    <XAxis dataKey="month" stroke="rgba(255,255,255,0.5)" tick={{ fontSize: 12 }} />
                                    <YAxis stroke="rgba(255,255,255,0.5)" tick={{ fontSize: 12 }} />
                                    <Tooltip
                                        contentStyle={{ background: '#1a1a2e', border: '1px solid rgba(255,255,255,0.1)' }}
                                        labelStyle={{ color: '#fff' }}
                                    />
                                    <Line type="monotone" dataKey="winRate" stroke={COLORS.warning} strokeWidth={2} />
                                </LineChart>
                            </ResponsiveContainer>
                        </div>

                        <div style={{ flex: 1, display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
                            <div>
                                <h3 style={{ textAlign: 'center', marginBottom: '10px' }}>Trade Distribution</h3>
                                <ResponsiveContainer width={200} height={200}>
                                    <PieChart>
                                        <Pie
                                            data={prepareDistributionData()}
                                            cx="50%"
                                            cy="50%"
                                            labelLine={false}
                                            label={({ name, percent }) => `${name}: ${(percent * 100).toFixed(0)}%`}
                                            outerRadius={80}
                                            fill="#8884d8"
                                            dataKey="value"
                                        >
                                            <Cell fill={COLORS.success} />
                                            <Cell fill={COLORS.danger} />
                                        </Pie>
                                        <Tooltip
                                            contentStyle={{ background: '#1a1a2e', border: '1px solid rgba(255,255,255,0.1)' }}
                                            labelStyle={{ color: '#fff' }}
                                        />
                                    </PieChart>
                                </ResponsiveContainer>
                            </div>
                        </div>
                    </div>
                </div>

                {/* Recent Trades Table */}
                <div className="trades-section glass">
                    <div className="trades-header">
                        <h3>Recent Trades</h3>
                        <BarChart2 size={20} style={{ color: '#667eea' }} />
                    </div>
                    <div className="trades-table-wrapper">
                        <table className="trades-table">
                            <thead>
                                <tr>
                                    <th>Symbol</th>
                                    <th>Type</th>
                                    <th>Open Price</th>
                                    <th>Close Price</th>
                                    <th>Profit</th>
                                    <th>Closed At</th>
                                </tr>
                            </thead>
                            <tbody>
                                {currentTrades.map(trade => (
                                    <tr key={trade.trade_id}>
                                        <td><strong>{trade.symbol}</strong></td>
                                        <td>
                                            <span className={`trade-type ${trade.type.toLowerCase()}`}>
                                                {trade.type}
                                            </span>
                                        </td>
                                        <td>{trade.open_price.toFixed(5)}</td>
                                        <td>{trade.close_price.toFixed(5)}</td>
                                        <td className={trade.profit >= 0 ? 'profit-positive' : 'profit-negative'}>
                                            ${trade.profit.toFixed(2)}
                                        </td>
                                        <td>{new Date(trade.closed_at).toLocaleString()}</td>
                                    </tr>
                                ))}
                            </tbody>
                        </table>
                        {totalPages > 1 && (
                            <div className="pagination">
                                <button
                                    onClick={() => setCurrentPage(prev => Math.max(prev - 1, 1))}
                                    disabled={currentPage === 1}
                                    className="pagination-btn"
                                >
                                    Previous
                                </button>
                                <span className="pagination-info">
                                    Page {currentPage} of {totalPages}
                                </span>
                                <button
                                    onClick={() => setCurrentPage(prev => Math.min(prev + 1, totalPages))}
                                    disabled={currentPage === totalPages}
                                    className="pagination-btn"
                                >
                                    Next
                                </button>
                            </div>
                        )}
                    </div>
                </div>
            </div>
        </Layout>
    )
}

export default MasterAnalytics
