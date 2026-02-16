import { NavLink, Outlet } from 'react-router-dom'
import { useAuth } from '../lib/auth'
import {
  LayoutDashboard, ArrowLeftRight, BookOpen, FileText,
  Receipt, BarChart3, Shield, Clock, LogOut, Menu, X
} from 'lucide-react'
import { useState } from 'react'

const nav = [
  { to: '/', label: 'Dashboard', icon: LayoutDashboard },
  { to: '/transactions', label: 'Transactions', icon: ArrowLeftRight },
  { to: '/journal', label: 'Journal Entries', icon: BookOpen },
  { to: '/accounts', label: 'Chart of Accounts', icon: FileText },
  { to: '/reconciliation', label: 'Reconciliation', icon: Shield },
  { to: '/reports', label: 'Reports', icon: BarChart3 },
  { to: '/receipts', label: 'Receipts', icon: Receipt },
  { to: '/periods', label: 'Periods', icon: Clock },
]

export default function Layout() {
  const { user, logout } = useAuth()
  const [sidebarOpen, setSidebarOpen] = useState(false)

  return (
    <div className="flex h-screen overflow-hidden">
      {/* Sidebar */}
      <aside className={`
        fixed inset-y-0 left-0 z-50 w-64 bg-brand-950 text-white transform transition-transform duration-200
        lg:translate-x-0 lg:static lg:flex lg:flex-col
        ${sidebarOpen ? 'translate-x-0' : '-translate-x-full'}
      `}>
        <div className="flex items-center gap-2 px-6 py-5 border-b border-brand-800">
          <BookOpen className="w-7 h-7 text-brand-400" />
          <span className="text-lg font-bold tracking-tight">OpenLedger</span>
        </div>

        <nav className="flex-1 px-3 py-4 space-y-1 overflow-y-auto">
          {nav.map(({ to, label, icon: Icon }) => (
            <NavLink
              key={to}
              to={to}
              end={to === '/'}
              onClick={() => setSidebarOpen(false)}
              className={({ isActive }) =>
                `flex items-center gap-3 px-3 py-2.5 rounded-lg text-sm font-medium transition-colors
                ${isActive
                  ? 'bg-brand-800 text-white'
                  : 'text-brand-200 hover:bg-brand-900 hover:text-white'}`
              }
            >
              <Icon className="w-5 h-5 shrink-0" />
              {label}
            </NavLink>
          ))}
        </nav>

        <div className="px-4 py-4 border-t border-brand-800">
          <div className="text-xs text-brand-400 mb-1">{user?.email}</div>
          <div className="flex items-center justify-between">
            <span className="text-xs px-2 py-0.5 rounded bg-brand-800 text-brand-300 capitalize">{user?.role}</span>
            <button onClick={logout} className="text-brand-400 hover:text-white transition-colors">
              <LogOut className="w-4 h-4" />
            </button>
          </div>
        </div>
      </aside>

      {/* Overlay for mobile */}
      {sidebarOpen && (
        <div className="fixed inset-0 z-40 bg-black/50 lg:hidden" onClick={() => setSidebarOpen(false)} />
      )}

      {/* Main content */}
      <div className="flex-1 flex flex-col overflow-hidden">
        <header className="flex items-center gap-4 px-4 py-3 bg-white border-b border-gray-200 lg:px-6">
          <button className="lg:hidden" onClick={() => setSidebarOpen(true)}>
            <Menu className="w-6 h-6" />
          </button>
          <h1 className="text-lg font-semibold text-gray-800">
            {user?.full_name || user?.email}
          </h1>
        </header>
        <main className="flex-1 overflow-y-auto p-4 lg:p-6">
          <Outlet />
        </main>
      </div>
    </div>
  )
}
