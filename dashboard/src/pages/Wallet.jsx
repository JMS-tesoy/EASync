import Layout from '../components/Layout'
import { DollarSign, ArrowUpCircle, ArrowDownCircle, Clock } from 'lucide-react'
import { useState, useEffect } from 'react'
import './Dashboard.css'

const API_URL = 'http://localhost:8000/api/v1'

function Wallet({ user, onLogout }) {
    const [wallet, setWallet] = useState(null)
    const [transactions, setTransactions] = useState([])
    const [loading, setLoading] = useState(true)

    useEffect(() => {
        fetchWalletData()
    }, [])

    const fetchWalletData = async () => {
        try {
            const token = localStorage.getItem('token')
            const headers = { 'Authorization': `Bearer ${token}` }

            const [walletRes, txRes] = await Promise.all([
                fetch(`${API_URL}/wallet`, { headers }),
                fetch(`${API_URL}/wallet/transactions?limit=10`, { headers })
            ])

            setWallet(await walletRes.json())
            setTransactions(await txRes.json())
        } catch (err) {
            console.error('Failed to fetch wallet data:', err)
        } finally {
            setLoading(false)
        }
    }

    return (
        <Layout user={user} onLogout={onLogout}>
            <div className="dashboard fade-in">
                <div className="page-header">
                    <h1>Wallet</h1>
                    <p>Manage your trading funds</p>
                </div>

                {loading ? (
                    <div className="loading">Loading...</div>
                ) : (
                    <>
                        <div className="stats-grid">
                            <div className="stat-card glass">
                                <div className="stat-icon" style={{ background: '#10b98120', color: '#10b981' }}>
                                    <DollarSign size={24} />
                                </div>
                                <div className="stat-content">
                                    <p className="stat-label">Available Balance</p>
                                    <h2 className="stat-value">${(Number(wallet?.balance_usd) || 0).toFixed(2)}</h2>
                                </div>
                            </div>
                            <div className="stat-card glass">
                                <div className="stat-icon" style={{ background: '#f59e0b20', color: '#f59e0b' }}>
                                    <Clock size={24} />
                                </div>
                                <div className="stat-content">
                                    <p className="stat-label">Reserved</p>
                                    <h2 className="stat-value">${(Number(wallet?.reserved_usd) || 0).toFixed(2)}</h2>
                                </div>
                            </div>
                        </div>

                        <div className="dashboard-card glass">
                            <h3>Recent Transactions</h3>
                            {transactions.length === 0 ? (
                                <p className="text-muted">No transactions yet</p>
                            ) : (
                                <div className="transactions-list">
                                    {transactions.map(tx => (
                                        <div key={tx.ledger_id} className="transaction-item">
                                            <div className="tx-icon">
                                                {tx.entry_type.includes('DEPOSIT') || tx.entry_type.includes('CREDIT') ? (
                                                    <ArrowUpCircle size={20} style={{ color: '#10b981' }} />
                                                ) : (
                                                    <ArrowDownCircle size={20} style={{ color: '#ef4444' }} />
                                                )}
                                            </div>
                                            <div className="tx-details">
                                                <p className="tx-desc">{tx.description}</p>
                                                <p className="tx-date">{new Date(tx.created_at).toLocaleString()}</p>
                                            </div>
                                            <div className="tx-amount" style={{
                                                color: tx.entry_type.includes('DEPOSIT') || tx.entry_type.includes('CREDIT') ? '#10b981' : '#ef4444'
                                            }}>
                                                {tx.entry_type.includes('DEPOSIT') || tx.entry_type.includes('CREDIT') ? '+' : '-'}
                                                ${(Number(tx.amount_usd) || 0).toFixed(2)}
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

export default Wallet
