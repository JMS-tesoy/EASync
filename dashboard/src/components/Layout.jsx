import { Link, useLocation } from 'react-router-dom'
import { LayoutDashboard, CreditCard, Shield, Users, LogOut, Menu, X, Activity, TrendingUp, BarChart3, Lock } from 'lucide-react'
import { useState } from 'react'
import './Layout.css'

function Layout({ children, user, onLogout }) {
    const location = useLocation()
    const [sidebarOpen, setSidebarOpen] = useState(true)

    const isMaster = user?.role === 'master'

    // Base navigation items
    const baseNavItems = [
        { path: '/dashboard', icon: LayoutDashboard, label: 'Dashboard' },
        { path: '/marketplace', icon: TrendingUp, label: 'Marketplace' },
        { path: '/subscriptions', icon: Users, label: 'Subscriptions' },
    ]

    // Add Master Dashboard for master users, or Become Master for non-masters
    const masterNavItem = isMaster
        ? { path: '/master-dashboard', icon: BarChart3, label: 'Master Dashboard' }
        : { path: '/become-master', icon: Shield, label: 'Become a Master' }

    const navItems = [
        ...baseNavItems,
        masterNavItem,
        ...(isMaster ? [{ path: '/master/analytics', icon: Activity, label: 'Analytics' }] : []),
        { path: '/wallet', icon: CreditCard, label: 'Wallet' },
        { path: '/protection', icon: Activity, label: 'Protection' },
        { path: '/security/2fa', icon: Lock, label: 'Security' },
    ]

    return (
        <div className="layout">
            <aside className={`sidebar glass ${sidebarOpen ? 'open' : 'closed'}`}>
                <div className="sidebar-header">
                    <h2 className="gradient-text">Execution Control</h2>
                    <button className="sidebar-toggle" onClick={() => setSidebarOpen(!sidebarOpen)}>
                        {sidebarOpen ? <X size={20} /> : <Menu size={20} />}
                    </button>
                </div>

                <nav className="sidebar-nav">
                    {navItems.map(item => (
                        <Link
                            key={item.path}
                            to={item.path}
                            className={`nav-item ${location.pathname === item.path ? 'active' : ''}`}
                        >
                            <item.icon size={20} />
                            {sidebarOpen && <span>{item.label}</span>}
                        </Link>
                    ))}
                </nav>

                <div className="sidebar-footer">
                    <div className="user-info">
                        {sidebarOpen && (
                            <>
                                <div className="user-avatar">{user?.email?.[0]?.toUpperCase()}</div>
                                <div className="user-details">
                                    <p className="user-name">{user?.full_name || 'User'}</p>
                                    <p className="user-email">{user?.email}</p>
                                </div>
                            </>
                        )}
                    </div>
                    <button className="btn-logout" onClick={onLogout}>
                        <LogOut size={20} />
                        {sidebarOpen && <span>Logout</span>}
                    </button>
                </div>
            </aside>

            <main className="main-content">
                {children}
            </main>
        </div>
    )
}

export default Layout
