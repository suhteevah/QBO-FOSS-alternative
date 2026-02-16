import { useState, useEffect } from 'react'
import { api } from '../lib/api'
import { Calendar, Plus, Lock, Unlock, CheckCircle, AlertTriangle } from 'lucide-react'

export default function Periods() {
  const [periods, setPeriods] = useState<any[]>([])
  const [loading, setLoading] = useState(true)
  const [message, setMessage] = useState<{ type: 'success' | 'error'; text: string } | null>(null)
  const [showCreate, setShowCreate] = useState(false)
  const [readiness, setReadiness] = useState<Record<string, any>>({})
  const [form, setForm] = useState({
    name: '',
    start_date: '',
    end_date: '',
  })

  useEffect(() => { load() }, [])

  async function load() {
    setLoading(true)
    try {
      const data = await api.periods.list()
      setPeriods(data)
    } catch (err: any) {
      setMessage({ type: 'error', text: err.message })
    } finally {
      setLoading(false)
    }
  }

  async function handleCreate(e: React.FormEvent) {
    e.preventDefault()
    try {
      await api.periods.create(form)
      setMessage({ type: 'success', text: 'Period created' })
      setShowCreate(false)
      setForm({ name: '', start_date: '', end_date: '' })
      load()
    } catch (err: any) {
      setMessage({ type: 'error', text: err.message })
    }
  }

  async function handleCheckReadiness(id: string) {
    try {
      const data = await api.periods.readiness(id)
      setReadiness({ ...readiness, [id]: data })
    } catch (err: any) {
      setMessage({ type: 'error', text: err.message })
    }
  }

  async function handleClose(id: string) {
    if (!confirm('Close this accounting period? This will generate closing entries.')) return
    try {
      await api.periods.close(id)
      setMessage({ type: 'success', text: 'Period closed successfully' })
      load()
    } catch (err: any) {
      setMessage({ type: 'error', text: err.message })
    }
  }

  async function handleReopen(id: string) {
    if (!confirm('Reopen this period? This will delete closing entries.')) return
    try {
      await api.periods.reopen(id)
      setMessage({ type: 'success', text: 'Period reopened' })
      load()
    } catch (err: any) {
      setMessage({ type: 'error', text: err.message })
    }
  }

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">Accounting Periods</h1>
          <p className="text-gray-500 mt-1">Manage fiscal periods with GAAP-compliant closing entries</p>
        </div>
        <button onClick={() => setShowCreate(!showCreate)}
          className="px-4 py-2 bg-brand-600 text-white rounded-lg hover:bg-brand-700 flex items-center gap-2 transition-colors">
          <Plus className="w-4 h-4" /> New Period
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
          <h3 className="font-semibold text-gray-900">New Accounting Period</h3>
          <div className="grid grid-cols-3 gap-4">
            <div>
              <label className="block text-sm font-medium text-gray-600 mb-1">Period Name</label>
              <input type="text" required value={form.name} onChange={e => setForm({ ...form, name: e.target.value })}
                placeholder="e.g. 2025-Q1" className="w-full px-3 py-2 border rounded-lg text-sm focus:ring-2 focus:ring-brand-500 outline-none" />
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-600 mb-1">Start Date</label>
              <input type="date" required value={form.start_date} onChange={e => setForm({ ...form, start_date: e.target.value })}
                className="w-full px-3 py-2 border rounded-lg text-sm focus:ring-2 focus:ring-brand-500 outline-none" />
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-600 mb-1">End Date</label>
              <input type="date" required value={form.end_date} onChange={e => setForm({ ...form, end_date: e.target.value })}
                className="w-full px-3 py-2 border rounded-lg text-sm focus:ring-2 focus:ring-brand-500 outline-none" />
            </div>
          </div>
          <button type="submit" className="px-4 py-2 bg-brand-600 text-white rounded-lg hover:bg-brand-700 transition-colors">
            Create Period
          </button>
        </form>
      )}

      {loading ? (
        <div className="flex items-center justify-center h-48">
          <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-brand-600" />
        </div>
      ) : periods.length === 0 ? (
        <div className="bg-white rounded-xl shadow-sm border border-gray-100 px-6 py-12 text-center text-gray-400">
          <Calendar className="w-12 h-12 mx-auto mb-3 opacity-50" />
          <p>No accounting periods yet. Create your first period to get started.</p>
        </div>
      ) : (
        <div className="space-y-4">
          {periods.map((p: any) => (
            <div key={p.id} className="bg-white rounded-xl shadow-sm border border-gray-100 p-5">
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-4">
                  <div className={`w-10 h-10 rounded-lg flex items-center justify-center ${
                    p.status === 'closed' ? 'bg-gray-100' : 'bg-brand-50'
                  }`}>
                    {p.status === 'closed' ? (
                      <Lock className="w-5 h-5 text-gray-500" />
                    ) : (
                      <Unlock className="w-5 h-5 text-brand-600" />
                    )}
                  </div>
                  <div>
                    <h3 className="font-semibold text-gray-900">{p.name}</h3>
                    <p className="text-sm text-gray-500">
                      {new Date(p.start_date).toLocaleDateString()} — {new Date(p.end_date).toLocaleDateString()}
                    </p>
                  </div>
                  <span className={`px-2.5 py-0.5 rounded-full text-xs font-medium ${
                    p.status === 'closed' ? 'bg-gray-100 text-gray-600' : 'bg-green-50 text-green-700'
                  }`}>
                    {p.status === 'closed' ? 'Closed' : 'Open'}
                  </span>
                </div>
                <div className="flex gap-2">
                  {p.status === 'open' && (
                    <>
                      <button onClick={() => handleCheckReadiness(p.id)}
                        className="px-3 py-1.5 bg-gray-100 text-gray-700 rounded-lg hover:bg-gray-200 text-sm flex items-center gap-1 transition-colors">
                        <CheckCircle className="w-3.5 h-3.5" /> Check Readiness
                      </button>
                      <button onClick={() => handleClose(p.id)}
                        className="px-3 py-1.5 bg-brand-600 text-white rounded-lg hover:bg-brand-700 text-sm flex items-center gap-1 transition-colors">
                        <Lock className="w-3.5 h-3.5" /> Close Period
                      </button>
                    </>
                  )}
                  {p.status === 'closed' && (
                    <button onClick={() => handleReopen(p.id)}
                      className="px-3 py-1.5 bg-amber-100 text-amber-700 rounded-lg hover:bg-amber-200 text-sm flex items-center gap-1 transition-colors">
                      <Unlock className="w-3.5 h-3.5" /> Reopen
                    </button>
                  )}
                </div>
              </div>

              {/* Readiness Display */}
              {readiness[p.id] && (
                <div className="mt-4 pt-4 border-t border-gray-100 grid grid-cols-4 gap-4">
                  <div className="text-center">
                    <p className="text-xs text-gray-400">Unapproved Entries</p>
                    <p className={`text-lg font-bold ${readiness[p.id].unapproved_entries > 0 ? 'text-amber-600' : 'text-green-600'}`}>
                      {readiness[p.id].unapproved_entries}
                    </p>
                  </div>
                  <div className="text-center">
                    <p className="text-xs text-gray-400">Unreconciled Txns</p>
                    <p className={`text-lg font-bold ${readiness[p.id].unreconciled_transactions > 0 ? 'text-amber-600' : 'text-green-600'}`}>
                      {readiness[p.id].unreconciled_transactions}
                    </p>
                  </div>
                  <div className="text-center">
                    <p className="text-xs text-gray-400">Draft Entries</p>
                    <p className={`text-lg font-bold ${readiness[p.id].draft_entries > 0 ? 'text-amber-600' : 'text-green-600'}`}>
                      {readiness[p.id].draft_entries}
                    </p>
                  </div>
                  <div className="text-center">
                    <p className="text-xs text-gray-400">Ready to Close</p>
                    <p className={`text-lg font-bold ${readiness[p.id].ready_to_close ? 'text-green-600' : 'text-red-600'}`}>
                      {readiness[p.id].ready_to_close ? (
                        <span className="flex items-center justify-center gap-1"><CheckCircle className="w-5 h-5" /> Yes</span>
                      ) : (
                        <span className="flex items-center justify-center gap-1"><AlertTriangle className="w-5 h-5" /> No</span>
                      )}
                    </p>
                  </div>
                </div>
              )}

              {p.closed_at && (
                <p className="text-xs text-gray-400 mt-3">
                  Closed on {new Date(p.closed_at).toLocaleDateString()}
                </p>
              )}
            </div>
          ))}
        </div>
      )}
    </div>
  )
}
