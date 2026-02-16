import { useState, useEffect } from 'react'
import { api } from '../lib/api'
import { Plus, Layers } from 'lucide-react'

const TYPE_COLORS: Record<string, string> = {
  asset: 'bg-blue-50 text-blue-700',
  liability: 'bg-purple-50 text-purple-700',
  equity: 'bg-indigo-50 text-indigo-700',
  revenue: 'bg-green-50 text-green-700',
  expense: 'bg-red-50 text-red-700',
}

export default function Accounts() {
  const [accounts, setAccounts] = useState<any[]>([])
  const [loading, setLoading] = useState(true)
  const [message, setMessage] = useState<{ type: 'success' | 'error'; text: string } | null>(null)
  const [showCreate, setShowCreate] = useState(false)
  const [form, setForm] = useState({
    name: '',
    account_number: '',
    account_type: 'asset',
    account_subtype: 'cash',
    normal_balance: 'debit',
  })

  useEffect(() => { load() }, [])

  async function load() {
    setLoading(true)
    try {
      const data = await api.accounts.list()
      setAccounts(data)
    } catch (err: any) {
      setMessage({ type: 'error', text: err.message })
    } finally {
      setLoading(false)
    }
  }

  async function handleCreate(e: React.FormEvent) {
    e.preventDefault()
    try {
      await api.accounts.create(form)
      setMessage({ type: 'success', text: 'Account created' })
      setShowCreate(false)
      setForm({ name: '', account_number: '', account_type: 'asset', account_subtype: 'cash', normal_balance: 'debit' })
      load()
    } catch (err: any) {
      setMessage({ type: 'error', text: err.message })
    }
  }

  // Group accounts by type
  const grouped = accounts.reduce((acc: Record<string, any[]>, a: any) => {
    const type = a.account_type || 'other'
    if (!acc[type]) acc[type] = []
    acc[type].push(a)
    return acc
  }, {})

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">Chart of Accounts</h1>
          <p className="text-gray-500 mt-1">GAAP-compliant chart of accounts for your organization</p>
        </div>
        <button onClick={() => setShowCreate(!showCreate)}
          className="px-4 py-2 bg-brand-600 text-white rounded-lg hover:bg-brand-700 flex items-center gap-2 transition-colors">
          <Plus className="w-4 h-4" /> Add Account
        </button>
      </div>

      {message && (
        <div className={`px-4 py-3 rounded-lg text-sm ${
          message.type === 'success' ? 'bg-green-50 text-green-700' : 'bg-red-50 text-red-700'
        }`}>
          {message.text}
        </div>
      )}

      {showCreate && (
        <form onSubmit={handleCreate} className="bg-white rounded-xl shadow-sm border border-gray-100 p-6 space-y-4">
          <h3 className="font-semibold text-gray-900">New Account</h3>
          <div className="grid grid-cols-2 lg:grid-cols-5 gap-4">
            <div>
              <label className="block text-sm font-medium text-gray-600 mb-1">Account Number</label>
              <input type="text" required value={form.account_number} onChange={e => setForm({ ...form, account_number: e.target.value })}
                placeholder="e.g. 1000" className="w-full px-3 py-2 border rounded-lg text-sm focus:ring-2 focus:ring-brand-500 outline-none" />
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-600 mb-1">Name</label>
              <input type="text" required value={form.name} onChange={e => setForm({ ...form, name: e.target.value })}
                className="w-full px-3 py-2 border rounded-lg text-sm focus:ring-2 focus:ring-brand-500 outline-none" />
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-600 mb-1">Type</label>
              <select value={form.account_type} onChange={e => setForm({ ...form, account_type: e.target.value })}
                className="w-full px-3 py-2 border rounded-lg text-sm focus:ring-2 focus:ring-brand-500 outline-none">
                <option value="asset">Asset</option>
                <option value="liability">Liability</option>
                <option value="equity">Equity</option>
                <option value="revenue">Revenue</option>
                <option value="expense">Expense</option>
              </select>
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-600 mb-1">Normal Balance</label>
              <select value={form.normal_balance} onChange={e => setForm({ ...form, normal_balance: e.target.value })}
                className="w-full px-3 py-2 border rounded-lg text-sm focus:ring-2 focus:ring-brand-500 outline-none">
                <option value="debit">Debit</option>
                <option value="credit">Credit</option>
              </select>
            </div>
            <div className="flex items-end">
              <button type="submit" className="w-full px-4 py-2 bg-brand-600 text-white rounded-lg hover:bg-brand-700 transition-colors">
                Create
              </button>
            </div>
          </div>
        </form>
      )}

      {loading ? (
        <div className="flex items-center justify-center h-48">
          <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-brand-600" />
        </div>
      ) : accounts.length === 0 ? (
        <div className="bg-white rounded-xl shadow-sm border border-gray-100 px-6 py-12 text-center text-gray-400">
          <Layers className="w-12 h-12 mx-auto mb-3 opacity-50" />
          <p>No accounts yet. Use the CLI to seed a standard GAAP chart of accounts.</p>
        </div>
      ) : (
        <div className="space-y-4">
          {['asset', 'liability', 'equity', 'revenue', 'expense'].map(type => {
            const accts = grouped[type]
            if (!accts?.length) return null
            return (
              <div key={type} className="bg-white rounded-xl shadow-sm border border-gray-100 overflow-hidden">
                <div className="px-4 py-3 bg-gray-50 border-b border-gray-100">
                  <span className={`px-2.5 py-0.5 rounded-full text-xs font-semibold uppercase ${TYPE_COLORS[type] || 'bg-gray-100 text-gray-600'}`}>
                    {type}
                  </span>
                </div>
                <table className="w-full text-sm">
                  <thead>
                    <tr className="border-b border-gray-50">
                      <th className="text-left px-4 py-2 text-gray-400 font-medium w-24">Number</th>
                      <th className="text-left px-4 py-2 text-gray-400 font-medium">Name</th>
                      <th className="text-left px-4 py-2 text-gray-400 font-medium">Subtype</th>
                      <th className="text-left px-4 py-2 text-gray-400 font-medium">Normal Balance</th>
                      <th className="text-left px-4 py-2 text-gray-400 font-medium">Status</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-gray-50">
                    {accts.sort((a: any, b: any) => a.account_number.localeCompare(b.account_number)).map((a: any) => (
                      <tr key={a.id} className="hover:bg-gray-50 transition-colors">
                        <td className="px-4 py-2.5 font-mono text-gray-600">{a.account_number}</td>
                        <td className="px-4 py-2.5 font-medium text-gray-900">{a.name}</td>
                        <td className="px-4 py-2.5 text-gray-500">{a.account_subtype?.replace(/_/g, ' ') || '—'}</td>
                        <td className="px-4 py-2.5 text-gray-500">{a.normal_balance}</td>
                        <td className="px-4 py-2.5">
                          <span className={`px-2 py-0.5 rounded-full text-xs font-medium ${
                            a.is_active ? 'bg-green-50 text-green-700' : 'bg-gray-100 text-gray-500'
                          }`}>
                            {a.is_active ? 'Active' : 'Inactive'}
                          </span>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )
          })}
        </div>
      )}
    </div>
  )
}
