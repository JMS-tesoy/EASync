import Layout from '../components/Layout'
import { Activity, Shield, DollarSign, Send } from 'lucide-react'
import { useState } from 'react'
import './Dashboard.css'
import './Auth.css'

const API_URL = 'http://localhost:8000/api/v1'

function BecomeMaster({ user, onLogout }) {
    const [formData, setFormData] = useState({
        display_name: user?.full_name || '',
        strategy_name: '',
        monthly_fee: '99',
        bio: ''
    })
    const [loading, setLoading] = useState(false)
    const [message, setMessage] = useState({ type: '', text: '' })

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
                text: 'Master profile active! You are now listed in the marketplace.'
            })

            // Update local user role in localStorage
            const updatedUser = { ...user, role: 'master' }
            localStorage.setItem('user', JSON.stringify(updatedUser))

            // Redirect after 2 seconds
            setTimeout(() => {
                window.location.href = '/marketplace'
            }, 2000)
        } catch (err) {
            setMessage({
                type: 'error',
                text: err.message
            })
        } finally {
            setLoading(false)
        }
    }

    return (
        <Layout user={user} onLogout={onLogout}>
            {/* LAYOUT FIX: 
               We use a flex container with minHeight to force vertical centering.
            */}
            <div className="dashboard fade-in" style={{
                display: 'flex',
                flexDirection: 'column',
                justifyContent: 'center',
                alignItems: 'center',
                minHeight: '85vh', // Takes up most of the screen height
                width: '100%'
            }}>

                {/* CONTENT WRAPPER: 
                   Keeps the width contained and responsive (max 600px).
                */}
                <div style={{ width: '100%', maxWidth: '600px' }}>

                    <div className="page-header" style={{ textAlign: 'center', marginBottom: '2rem' }}>
                        <h1>Become a Master Trader</h1>
                        <p>Share your trading signals and earn subscription fees</p>
                    </div>

                    <div className="auth-container" style={{ margin: '0', width: '100%' }}>
                        <form className="auth-card glass" onSubmit={handleSubmit}>
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
                                        resize: 'none' // Prevents user from breaking layout by dragging
                                    }}
                                    placeholder="Describe your trading style and risk management..."
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
                                {loading ? 'Processing...' : (
                                    <>
                                        <Send size={20} />
                                        Launch Master Profile
                                    </>
                                )}
                            </button>
                        </form>
                    </div>
                </div>
            </div>
        </Layout>
    )
}

export default BecomeMaster