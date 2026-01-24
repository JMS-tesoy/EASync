import { useState } from 'react'
import { Link } from 'react-router-dom'
import { UserPlus, Mail, Lock, User, TrendingUp } from 'lucide-react'
import './Auth.css'

const API_URL = 'http://127.0.0.1:8000/api/v1'

function Register({ onRegister }) {
    const [formData, setFormData] = useState({
        email: '',
        password: '',
        full_name: ''
    })
    const [error, setError] = useState('')
    const [loading, setLoading] = useState(false)

    const handleSubmit = async (e) => {
        e.preventDefault()
        setError('')
        setLoading(true)

        try {
            const response = await fetch(`${API_URL}/auth/register`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(formData)
            })

            const data = await response.json()

            if (!response.ok) {
                throw new Error(data.detail || 'Registration failed')
            }

            // Auto-login after registration
            const loginResponse = await fetch(`${API_URL}/auth/login`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    email: formData.email,
                    password: formData.password
                })
            })

            const loginData = await loginResponse.json()
            onRegister(loginData.access_token, data)
        } catch (err) {
            setError(err.message)
        } finally {
            setLoading(false)
        }
    }

    return (
        <div className="auth-container">
            <div className="auth-card glass fade-in">
                <div className="auth-header">
                    <TrendingUp size={48} className="auth-icon" />
                    <h1 className="gradient-text">Join Execution Control</h1>
                    <p>Create your trading account</p>
                </div>

                <form onSubmit={handleSubmit} className="auth-form">
                    {error && <div className="error-message">{error}</div>}

                    <div className="form-group">
                        <label>
                            <User size={20} />
                            Full Name
                        </label>
                        <input
                            type="text"
                            value={formData.full_name}
                            onChange={(e) => setFormData({ ...formData, full_name: e.target.value })}
                            placeholder="John Doe"
                        />
                    </div>

                    <div className="form-group">
                        <label>
                            <Mail size={20} />
                            Email
                        </label>
                        <input
                            type="email"
                            value={formData.email}
                            onChange={(e) => setFormData({ ...formData, email: e.target.value })}
                            placeholder="trader@example.com"
                            required
                        />
                    </div>

                    <div className="form-group">
                        <label>
                            <Lock size={20} />
                            Password
                        </label>
                        <input
                            type="password"
                            value={formData.password}
                            onChange={(e) => setFormData({ ...formData, password: e.target.value })}
                            placeholder="••••••••"
                            required
                            minLength={8}
                        />
                    </div>

                    <button type="submit" className="btn-primary" disabled={loading}>
                        <UserPlus size={20} />
                        {loading ? 'Creating account...' : 'Create Account'}
                    </button>
                </form>

                <div className="auth-footer">
                    <p>Already have an account? <Link to="/login">Sign in</Link></p>
                </div>
            </div>
        </div>
    )
}

export default Register
