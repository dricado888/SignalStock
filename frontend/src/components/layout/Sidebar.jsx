import { NavLink, useNavigate } from 'react-router-dom'
import { useAuth } from '../../contexts/AuthContext'

const NAV = [
  { to: '/',          label: 'Dashboard',  icon: '▦' },
  { to: '/events',    label: 'Events',     icon: '◈' },
  { to: '/watchlist', label: 'Watchlist',  icon: '★' },
]

export default function Sidebar() {
  const { user, logout } = useAuth()
  const navigate = useNavigate()

  const handleLogout = () => { logout(); navigate('/login') }

  return (
    <aside className="w-56 min-h-screen bg-navy-900 flex flex-col">
      {/* Brand */}
      <div className="px-6 py-5 border-b border-navy-800">
        <div className="text-white font-bold text-base tracking-widest uppercase">
          SignalStock
        </div>
        <div className="text-slate-500 text-xs mt-0.5 tracking-wide">
          Market Intelligence
        </div>
      </div>

      {/* Nav */}
      <nav className="flex-1 px-3 py-4 space-y-1">
        {NAV.map(({ to, label, icon }) => (
          <NavLink
            key={to}
            to={to}
            end={to === '/'}
            className={({ isActive }) =>
              `flex items-center gap-3 px-3 py-2.5 rounded-lg text-sm font-medium transition-colors ${
                isActive
                  ? 'bg-indigo-600 text-white'
                  : 'text-slate-400 hover:text-white hover:bg-navy-800'
              }`
            }
          >
            <span className="text-base">{icon}</span>
            {label}
          </NavLink>
        ))}
      </nav>

      {/* User / logout */}
      <div className="px-4 py-4 border-t border-navy-800">
        <div className="text-slate-500 text-xs truncate mb-2">{user?.email}</div>
        <button
          onClick={handleLogout}
          className="w-full text-left text-sm text-slate-400 hover:text-red-400 transition-colors px-1"
        >
          ← Logout
        </button>
      </div>
    </aside>
  )
}
