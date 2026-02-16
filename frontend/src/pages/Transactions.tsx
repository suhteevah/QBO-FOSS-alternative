import { useState, useEffect, useRef } from 'react'
import { api } from '../lib/api'
import { Upload, Zap, FileText, RefreshCw, ChevronDown } from 'lucide-react'

export default function Transactions() {
  const [transactions, setTransactions] = useState<any[]>([])
  const [loading, setLoading] = useState(true)
  const [importing, setImporting] = useState(false)
  const [processing, setProcessing] = useState(false)
  const [filter, setFilter] = useState<'all' | 'reconciled' | 'unreconciled'>('all')
  const [message, setMessage] = useState<{ type: 'success' | 'error'; text: string } | null>(null)
  const fileRef = useRef<HTMLInputElement>(null)

  useEffect(() => { load() }, [filter])

  async function load() {
    setLoading(true)
    try {
      const reconciled = filter === 'all' ? undefined : filter === 'reconciled'
      const data = await api.transactions.list(reconciled)
      setTransactions(data)
    } catch (err: any) {
      setMessage({ type: 'error', text: err.message })
    } finally {
      setLoading(false)
    }
  }

  async function handleImport(e: React.ChangeEvent<HTMLInputElement>) {
    const file = e.target.files?.[0]
    if (!file) return
    setImporting(true)
    setMessage(null)
    try {
      const result = await api.transactions.import(file)
      setMessage({ type: 'success', text: `Imported ${result.imported ?? 0} transactions` })
      load()
    } catch (err: any) {
      setMessage({ type: 'error', text: err.message })
    } finally {
      setImporting(false)
      if (fileRef.current) fileRef.current.value = ''
    }
  }

  async function handleProcess() {
    setProcessing(true)
    setMessage(null)
    try {
      const result = await api.transactions.process()
      setMessage({
        type: 'success',
        text: `Classified ${result.classification?.classified ?? 0} transactions, created ${result.entry_creation?.entries_created ?? 0} journal entries`,
      })
      load()
    } catch (err: any) {
      setMessage({ type: 'error', text: err.message })
    } finally {
      setProcessing(false)
    }
  }

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">Bank Transactions</h1>
          <p className="text-gray-500 mt-1">Import, classify, and process bank transactions</p>
        </div>
        <div className="flex gap-2">
          <input type="file" ref={fileRef} onChange={handleImport} accept=".csv,.xlsx" className="hidden" />
          <button onClick={() => fileRef.current?.click()} disabled={importing}
            className="px-4 py-2 bg-white border border-gray-300 text-gray-700 rounded-lg hover:bg-gray-50 flex items-center gap-2 disabled:opacity-50 transition-colors">
            <Upload className="w-4 h-4" />
            {importing ? 'Importing...' : 'Import CSV/XLSX'}
          </button>
          <button onClick={handleProcess} disabled={processing}
            className="px-4 py-2 bg-brand-600 text-white rounded-lg hover:bg-brand-700 flex items-center gap-2 disabled:opacity-50 transition-colors">
            <Zap className="w-4 h-4" />
            {processing ? 'Processing...' : 'AI Classify & Create Entries'}
          </button>
        </div>
      </div>

      {message && (
        <div className={`px-4 py-3 rounded-lg text-sm ${
          message.type === 'success' ? 'bg-green-50 text-green-700' : 'bg-red-50 text-red-700'
        }`}>
          {message.text}
        </div>
      )}

      {/* Filter */}
      <div className="flex gap-1 bg-gray-100 rounded-lg p-1 w-fit">
        {(['all', 'unreconciled', 'reconciled'] as const).map((f) => (
          <button key={f} onClick={() => setFilter(f)}
            className={`px-4 py-1.5 rounded-md text-sm font-medium transition-colors ${
              filter === f ? 'bg-white text-gray-900 shadow-sm' : 'text-gray-500 hover:text-gray-700'
            }`}>
            {f.charAt(0).toUpperCase() + f.slice(1)}
          </button>
        ))}
      </div>

      {/* Table */}
      <div className="bg-white rounded-xl shadow-sm border border-gray-100 overflow-hidden">
        {loading ? (
          <div className="flex items-center justify-center h-48">
            <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-brand-600" />
          </div>
        ) : transactions.length === 0 ? (
          <div className="px-6 py-12 text-center text-gray-400">
            <Upload className="w-12 h-12 mx-auto mb-3 opacity-50" />
            <p>No transactions found. Import a bank statement to get started.</p>
          </div>
        ) : (
          <table className="w-full text-sm">
            <thead className="bg-gray-50 border-b border-gray-100">
              <tr>
                <th className="text-left px-4 py-3 text-gray-500 font-medium">Date</th>
                <th className="text-left px-4 py-3 text-gray-500 font-medium">Description</th>
                <th className="text-left px-4 py-3 text-gray-500 font-medium">Category</th>
                <th className="text-right px-4 py-3 text-gray-500 font-medium">Amount</th>
                <th className="text-left px-4 py-3 text-gray-500 font-medium">Confidence</th>
                <th className="text-left px-4 py-3 text-gray-500 font-medium">Status</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-50">
              {transactions.map((txn: any) => (
                <tr key={txn.id} className="hover:bg-gray-50 transition-colors">
                  <td className="px-4 py-3 text-gray-900">{new Date(txn.transaction_date).toLocaleDateString()}</td>
                  <td className="px-4 py-3 text-gray-900 max-w-xs truncate">{txn.description_cleaned || txn.description_raw}</td>
                  <td className="px-4 py-3 text-gray-600">{txn.ai_category || '—'}</td>
                  <td className={`px-4 py-3 text-right font-mono ${Number(txn.amount) < 0 ? 'text-red-600' : 'text-green-600'}`}>
                    {Number(txn.amount) < 0 ? '-' : ''}${Math.abs(Number(txn.amount)).toFixed(2)}
                  </td>
                  <td className="px-4 py-3">
                    {txn.ai_confidence ? (
                      <div className="flex items-center gap-2">
                        <div className="w-16 h-1.5 bg-gray-200 rounded-full overflow-hidden">
                          <div className="h-full bg-brand-500 rounded-full" style={{ width: `${(Number(txn.ai_confidence) * 100)}%` }} />
                        </div>
                        <span className="text-xs text-gray-500">{(Number(txn.ai_confidence) * 100).toFixed(0)}%</span>
                      </div>
                    ) : <span className="text-gray-400">—</span>}
                  </td>
                  <td className="px-4 py-3">
                    <span className={`px-2 py-0.5 rounded-full text-xs font-medium ${
                      txn.is_reconciled ? 'bg-green-50 text-green-700' : 'bg-yellow-50 text-yellow-700'
                    }`}>
                      {txn.is_reconciled ? 'Reconciled' : 'Pending'}
                    </span>
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
