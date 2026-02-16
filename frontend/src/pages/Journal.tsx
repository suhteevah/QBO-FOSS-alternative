import { useState, useEffect } from 'react'
import { api } from '../lib/api'
import { Plus, Check, XCircle, FileText } from 'lucide-react'

export default function Journal() {
  const [entries, setEntries] = useState<any[]>([])
  const [loading, setLoading] = useState(true)
  const [message, setMessage] = useState<{ type: 'success' | 'error'; text: string } | null>(null)
  const [showCreate, setShowCreate] = useState(false)
  const [form, setForm] = useState({
    entry_date: new Date().toISOString().split('T')[0],
    description: '',
    memo: '',
    lines: [
      { account_id: '', description: '', debit_amount: '', credit_amount: '' },
      { account_id: '', description: '', debit_amount: '', credit_amount: '' },
    ],
  })
  const [accounts, setAccounts] = useState<any[]>([])

  useEffect(() => {
    load()
    loadAccounts()
  }, [])

  async function load() {
    setLoading(true)
    try {
      const data = await api.journal.list()
      setEntries(data)
    } catch (err: any) {
      setMessage({ type: 'error', text: err.message })
    } finally {
      setLoading(false)
    }
  }

  async function loadAccounts() {
    try {
      const data = await api.accounts.list()
      setAccounts(data)
    } catch {}
  }

  async function handleApprove(id: string) {
    try {
      await api.journal.approve(id)
      setMessage({ type: 'success', text: 'Entry approved' })
      load()
    } catch (err: any) {
      setMessage({ type: 'error', text: err.message })
    }
  }

  async function handleVoid(id: string) {
    if (!confirm('Void this journal entry?')) return
    try {
      await api.journal.void(id)
      setMessage({ type: 'success', text: 'Entry voided' })
      load()
    } catch (err: any) {
      setMessage({ type: 'error', text: err.message })
    }
  }

  async function handleCreate(e: React.FormEvent) {
    e.preventDefault()
    try {
      await api.journal.create({
        entry_date: form.entry_date,
        description: form.description,
        memo: form.memo,
        source: 'manual',
        line_items: form.lines.filter(l => l.account_id).map(l => ({
          account_id: l.account_id,
          description: l.description,
          debit_amount: Number(l.debit_amount) || 0,
          credit_amount: Number(l.credit_amount) || 0,
        })),
      })
      setMessage({ type: 'success', text: 'Journal entry created' })
      setShowCreate(false)
      setForm({
        entry_date: new Date().toISOString().split('T')[0],
        description: '',
        memo: '',
        lines: [
          { account_id: '', description: '', debit_amount: '', credit_amount: '' },
          { account_id: '', description: '', debit_amount: '', credit_amount: '' },
        ],
      })
      load()
    } catch (err: any) {
      setMessage({ type: 'error', text: err.message })
    }
  }

  function addLine() {
    setForm({
      ...form,
      lines: [...form.lines, { account_id: '', description: '', debit_amount: '', credit_amount: '' }],
    })
  }

  function updateLine(i: number, field: string, value: string) {
    const lines = [...form.lines]
    lines[i] = { ...lines[i], [field]: value }
    setForm({ ...form, lines })
  }

  const totalDebits = form.lines.reduce((s, l) => s + (Number(l.debit_amount) || 0), 0)
  const totalCredits = form.lines.reduce((s, l) => s + (Number(l.credit_amount) || 0), 0)
  const isBalanced = totalDebits > 0 && Math.abs(totalDebits - totalCredits) < 0.005

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">Journal Entries</h1>
          <p className="text-gray-500 mt-1">Create, approve, and manage journal entries</p>
        </div>
        <button onClick={() => setShowCreate(!showCreate)}
          className="px-4 py-2 bg-brand-600 text-white rounded-lg hover:bg-brand-700 flex items-center gap-2 transition-colors">
          <Plus className="w-4 h-4" /> New Entry
        </button>
      </div>

      {message && (
        <div className={`px-4 py-3 rounded-lg text-sm ${
          message.type === 'success' ? 'bg-green-50 text-green-700' : 'bg-red-50 text-red-700'
        }`}>
          {message.text}
        </div>
      )}

      {/* Create Form */}
      {showCreate && (
        <form onSubmit={handleCreate} className="bg-white rounded-xl shadow-sm border border-gray-100 p-6 space-y-4">
          <h3 className="font-semibold text-gray-900">New Journal Entry</h3>
          <div className="grid grid-cols-3 gap-4">
            <div>
              <label className="block text-sm font-medium text-gray-600 mb-1">Date</label>
              <input type="date" value={form.entry_date} onChange={e => setForm({ ...form, entry_date: e.target.value })}
                className="w-full px-3 py-2 border rounded-lg text-sm focus:ring-2 focus:ring-brand-500 outline-none" />
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-600 mb-1">Description</label>
              <input type="text" value={form.description} onChange={e => setForm({ ...form, description: e.target.value })} required
                className="w-full px-3 py-2 border rounded-lg text-sm focus:ring-2 focus:ring-brand-500 outline-none" />
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-600 mb-1">Memo</label>
              <input type="text" value={form.memo} onChange={e => setForm({ ...form, memo: e.target.value })}
                className="w-full px-3 py-2 border rounded-lg text-sm focus:ring-2 focus:ring-brand-500 outline-none" />
            </div>
          </div>
          <div className="space-y-2">
            <p className="text-sm font-medium text-gray-600">Line Items</p>
            {form.lines.map((line, i) => (
              <div key={i} className="grid grid-cols-4 gap-2">
                <select value={line.account_id} onChange={e => updateLine(i, 'account_id', e.target.value)}
                  className="px-3 py-2 border rounded-lg text-sm focus:ring-2 focus:ring-brand-500 outline-none">
                  <option value="">Select account...</option>
                  {accounts.map((a: any) => (
                    <option key={a.id} value={a.id}>{a.account_number} — {a.name}</option>
                  ))}
                </select>
                <input type="text" placeholder="Description" value={line.description} onChange={e => updateLine(i, 'description', e.target.value)}
                  className="px-3 py-2 border rounded-lg text-sm focus:ring-2 focus:ring-brand-500 outline-none" />
                <input type="number" step="0.01" placeholder="Debit" value={line.debit_amount} onChange={e => updateLine(i, 'debit_amount', e.target.value)}
                  className="px-3 py-2 border rounded-lg text-sm focus:ring-2 focus:ring-brand-500 outline-none text-right font-mono" />
                <input type="number" step="0.01" placeholder="Credit" value={line.credit_amount} onChange={e => updateLine(i, 'credit_amount', e.target.value)}
                  className="px-3 py-2 border rounded-lg text-sm focus:ring-2 focus:ring-brand-500 outline-none text-right font-mono" />
              </div>
            ))}
            <button type="button" onClick={addLine} className="text-brand-600 text-sm hover:underline">+ Add line</button>
          </div>
          <div className="flex items-center justify-between pt-2 border-t">
            <div className="text-sm">
              <span className={isBalanced ? 'text-green-600' : 'text-red-600'}>
                Debits: ${totalDebits.toFixed(2)} | Credits: ${totalCredits.toFixed(2)}
                {isBalanced ? ' ✓ Balanced' : ' ✗ Unbalanced'}
              </span>
            </div>
            <button type="submit" disabled={!isBalanced}
              className="px-4 py-2 bg-brand-600 text-white rounded-lg hover:bg-brand-700 disabled:opacity-50 transition-colors">
              Create Entry
            </button>
          </div>
        </form>
      )}

      {/* Entries Table */}
      <div className="bg-white rounded-xl shadow-sm border border-gray-100 overflow-hidden">
        {loading ? (
          <div className="flex items-center justify-center h-48">
            <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-brand-600" />
          </div>
        ) : entries.length === 0 ? (
          <div className="px-6 py-12 text-center text-gray-400">
            <FileText className="w-12 h-12 mx-auto mb-3 opacity-50" />
            <p>No journal entries yet.</p>
          </div>
        ) : (
          <table className="w-full text-sm">
            <thead className="bg-gray-50 border-b border-gray-100">
              <tr>
                <th className="text-left px-4 py-3 text-gray-500 font-medium">Date</th>
                <th className="text-left px-4 py-3 text-gray-500 font-medium">Description</th>
                <th className="text-left px-4 py-3 text-gray-500 font-medium">Source</th>
                <th className="text-left px-4 py-3 text-gray-500 font-medium">Status</th>
                <th className="text-right px-4 py-3 text-gray-500 font-medium">Actions</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-50">
              {entries.map((entry: any) => (
                <tr key={entry.id} className="hover:bg-gray-50 transition-colors">
                  <td className="px-4 py-3">{new Date(entry.entry_date).toLocaleDateString()}</td>
                  <td className="px-4 py-3 max-w-xs truncate">{entry.description}</td>
                  <td className="px-4 py-3 text-gray-500">{entry.source?.replace(/_/g, ' ') || 'manual'}</td>
                  <td className="px-4 py-3">
                    <span className={`px-2 py-0.5 rounded-full text-xs font-medium ${
                      entry.status === 'approved' || entry.status === 'auto_approved'
                        ? 'bg-green-50 text-green-700'
                        : entry.status === 'voided'
                        ? 'bg-red-50 text-red-700'
                        : 'bg-yellow-50 text-yellow-700'
                    }`}>
                      {entry.status}
                    </span>
                  </td>
                  <td className="px-4 py-3 text-right">
                    <div className="flex justify-end gap-1">
                      {(entry.status === 'draft' || entry.status === 'pending_review') && (
                        <button onClick={() => handleApprove(entry.id)} title="Approve"
                          className="p-1.5 rounded-lg hover:bg-green-50 text-green-600 transition-colors">
                          <Check className="w-4 h-4" />
                        </button>
                      )}
                      {entry.status !== 'voided' && (
                        <button onClick={() => handleVoid(entry.id)} title="Void"
                          className="p-1.5 rounded-lg hover:bg-red-50 text-red-600 transition-colors">
                          <XCircle className="w-4 h-4" />
                        </button>
                      )}
                    </div>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>
    </div>
  )
}
