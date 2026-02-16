import { useState, useEffect } from 'react'
import { api } from '../lib/api'
import { DollarSign, FileText, ArrowRightLeft, AlertTriangle, TrendingUp, TrendingDown } from 'lucide-react'

interface DashboardStats {
  totalAccounts: number
  totalTransactions: number
  unreconciledCount: number
  recentEntries: any[]
  bankBalance: string
}

function StatCard({ icon: Icon, label, value, color }: { icon: any; label: string; value: string | number; color: string }) {
  return (
    <div className="bg-white rounded-xl shadow-sm border border-gray-100 p-6">
      <div className="flex items-center gap-4">
        <div className={`w-12 h-12 rounded-lg flex items-center justify-center ${color}`}>
          <Icon className="w-6 h-6 text-white" />
        </div>
        <div>
          <p className="text-sm text-gray-500">{label}</p>
          <p className="text-2xl font-bold text-gray-900">{value}</p>
        </div>
      </div>
    </div>
  )
}

export default function Dashboard() {
  const [stats, setStats] = useState<DashboardStats>({
    totalAccounts: 0,
    totalTransactions: 0,
    unreconciledCount: 0,
    recentEntries: [],
    bankBalance: '$0.00',
  })
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    loadDashboard()
  }, [])

  async function loadDashboard() {
    try {
      const [accounts, transactions, entries, reconciliation] = await Promise.allSettled([
        api.accounts.list(),
        api.transactions.list(),
        api.journal.list(),
        api.reconciliation.summary(),
      ])

      setStats({
        totalAccounts: accounts.status === 'fulfilled' ? accounts.value.length : 0,
        totalTransactions: transactions.status === 'fulfilled' ? transactions.value.length : 0,
        unreconciledCount:
          reconciliation.status === 'fulfilled'
            ? reconciliation.value.unmatched_bank_transactions ?? 0
            : 0,
        recentEntries: entries.status === 'fulfilled' ? entries.value.slice(0, 5) : [],
        bankBalance: '$0.00',
      })
    } catch (err) {
      console.error('Dashboard load error:', err)
    } finally {
      setLoading(false)
    }
  }

  if (loading) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-brand-600" />
      </div>
    )
  }

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold text-gray-900">Dashboard</h1>
        <p className="text-gray-500 mt-1">Overview of your organization's finances</p>
      </div>

      {/* KPI Cards */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
        <StatCard icon={DollarSign} label="Chart of Accounts" value={stats.totalAccounts} color="bg-brand-600" />
        <StatCard icon={ArrowRightLeft} label="Bank Transactions" value={stats.totalTransactions} color="bg-emerald-600" />
        <StatCard icon={AlertTriangle} label="Unreconciled" value={stats.unreconciledCount} color="bg-amber-500" />
        <StatCard icon={FileText} label="Journal Entries" value={stats.recentEntries.length} color="bg-indigo-600" />
      </div>

      {/* Recent Journal Entries */}
      <div className="bg-white rounded-xl shadow-sm border border-gray-100 overflow-hidden">
        <div className="px-6 py-4 border-b border-gray-100">
          <h2 className="text-lg font-semibold text-gray-900">Recent Journal Entries</h2>
        </div>
        {stats.recentEntries.length === 0 ? (
          <div className="px-6 py-12 text-center text-gray-400">
            <FileText className="w-12 h-12 mx-auto mb-3 opacity-50" />
            <p>No journal entries yet. Import bank transactions or upload receipts to get started.</p>
          </div>
        ) : (
          <div className="divide-y divide-gray-50">
            {stats.recentEntries.map((entry: any) => (
              <div key={entry.id} className="px-6 py-4 flex items-center justify-between hover:bg-gray-50 transition-colors">
                <div>
                  <p className="font-medium text-gray-900">{entry.description}</p>
                  <p className="text-sm text-gray-500">{new Date(entry.entry_date).toLocaleDateString()}</p>
                </div>
                <div className="flex items-center gap-3">
                  <span className={`px-2.5 py-0.5 rounded-full text-xs font-medium ${
                    entry.status === 'approved' || entry.status === 'auto_approved'
                      ? 'bg-green-50 text-green-700'
                      : entry.status === 'voided'
                      ? 'bg-red-50 text-red-700'
                      : 'bg-yellow-50 text-yellow-700'
                  }`}>
                    {entry.status}
                  </span>
                  {entry.source === 'bank_import_csv' ? (
                    <TrendingDown className="w-4 h-4 text-gray-400" />
                  ) : (
                    <TrendingUp className="w-4 h-4 text-gray-400" />
                  )}
                </div>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  )
}
