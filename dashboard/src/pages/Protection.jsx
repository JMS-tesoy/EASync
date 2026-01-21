import Layout from '../components/Layout'
import { Shield, AlertTriangle, Clock } from 'lucide-react'
import { useState, useEffect } from 'react'
import './Dashboard.css'

const API_URL = 'http://localhost:8000/api/v1'

function Protection({ user, onLogout }) {
    const [events, setEvents] = useState([])
    const [summary, setSummary] = useState(null)
    const [loading, setLoading] = useState(true)

    useEffect(() => {
        fetchProtectionData()
    }, [])

    const fetchProtectionData = async () => {
        try {
            const token = localStorage.getItem('token')
            const headers = { 'Authorization': `Bearer ${token}` }

            const [eventsRes, summaryRes] = await Promise.all([
                fetch(`${API_URL}/protection-events?hours=24&limit=20`, { headers }),
                fetch(`${API_URL}/protection-events/summary?hours=24`, { headers })
            ])

            setEvents(await eventsRes.json())
            setSummary(await summaryRes.json())
        } catch (err) {
            console.error('Failed to fetch protection data:', err)
        } finally {
            setLoading(false)
        }
    }

    return (
        <Layout user={user} onLogout={onLogout}>
            <div className="dashboard fade-in">
                <div className="page-header">
                    <h1>Protection Events</h1>
                    <p>Monitor signal rejections and protection triggers</p>
                </div>

                {loading ? (
                    <div className="loading">Loading...</div>
                ) : (
                    <>
                        {summary && summary.events_by_reason.length > 0 && (
                            <div className="dashboard-card glass" style={{ marginBottom: '24px' }}>
                                <h3>Event Summary (24h)</h3>
                                <div className="summary-grid">
                                    {summary.events_by_reason.map((item, idx) => (
                                        <div key={idx} className="summary-item">
                                            <span className="summary-reason">{item.reason.replace(/_/g, ' ')}</span>
                                            <span className="summary-count">{item.count} events</span>
                                        </div>
                                    ))}
                                </div>
                            </div>
                        )}

                        <div className="dashboard-card glass">
                            <h3>Recent Events</h3>
                            {events.length === 0 ? (
                                <div className="empty-state">
                                    <Shield size={48} style={{ color: '#10b981', marginBottom: '16px' }} />
                                    <h3>No Protection Events</h3>
                                    <p>All signals are passing validation checks</p>
                                </div>
                            ) : (
                                <div className="events-list">
                                    {events.map(event => (
                                        <div key={event.event_id} className="event-item">
                                            <div className="event-icon">
                                                <AlertTriangle size={20} style={{ color: '#f59e0b' }} />
                                            </div>
                                            <div className="event-details">
                                                <p className="event-reason">{event.reason.replace(/_/g, ' ')}</p>
                                                <p className="event-meta">
                                                    Sequence #{event.signal_sequence} • Latency: {event.latency_ms}ms
                                                </p>
                                            </div>
                                            <div className="event-time">
                                                <Clock size={16} />
                                                {new Date(event.event_time).toLocaleTimeString()}
                                            </div>
                                        </div>
                                    ))}
                                </div>
                            )}
                        </div>
                    </>
                )}
            </div>
        </Layout>
    )
}

export default Protection
