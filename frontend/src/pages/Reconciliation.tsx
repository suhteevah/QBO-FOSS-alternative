import { useState, useEffect } from 'react'
import { api } from '../lib/api'
import { ArrowRightLeft, Check, X, RefreshCw } from 'lucide-react'

export default function Reconciliation() {
  const [suggestions, setSuggestions] = useState<any[]>([])
  const [summary, setSummary] = useState<any>(null)
  const [loading, setLoading] = useState(true)
  const [message, setMessage] = useState<{ type: 'success' | 'error'; text: string } | null>(null)

  useEffect(() => { load() }, [])

  async function load() {
    setLoading(true)
    try {
      const [sugg, summ] = await Promise.all([
        api.reconciliation.suggestions(),
        api.reconciliation.summary(),
      ])
      setSuggestions(sugg)
      setSummary(summ)
    } catch (err: any) {
      setMessage({ type: 'error', text: err.message })
    } finally {
      setLoading(false)
    }
  }

  async function handleMatch(bankTxnId: string, journalEntryId: string) {
    try {
      await api.reconciliation.match(bankTxnId, journalEntryId)
      setMessage({ type: 'success', text: 'Match confirmed' })
      load()
    } catch (err: any) {
      setMessage({ type: 'error', text: err.message })
    }
  }

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">Reconciliation</h1>
          <p className="text-gray-500 mt-1">Match bank transactions to journal entries</p>
        </div>
        <button onClick={load} className="px-4 py-2 bg-white border border-gray-300 rounded-lg hover:bg-gray-50 flex items-center gap-2 transition-colors">
          <RefreshCw className="w-4 h-4" /> Refresh
        </button>
      </div>

      {message && (
        <div className={`px-4 py-3 rounded-lg text-sm ${
          message.type === 'success' ? 'bg-green-50 text-green-700' : 'bg-red-50 text-red-700'
        }`}>
          {message.text}
        </div>
      )}

      {/* Summary Cards */}
      {summary && (
        <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
          <div className="bg-white rounded-xl border border-gray-100 shadow-sm p-4 text-center">
            <p className="text-sm text-gray-500">Bank Transactions</p>
            <p className="text-2xl font-bold text-gray-900">{summary.total_bank_transactions ?? 0}</p>
          </div>
          <div className="bg-white rounded-xl border border-gray-100 shadow-sm p-4 text-center">
            <p className="text-sm text-gray-500">Matched</p>
            <p className="text-2xl font-bold text-green-600">{summary.matched_count ?? 0}</p>
          </div>
          <div className="bg-white rounded-xl border border-gray-100 shadow-sm p-4 text-center">
            <p className="text-sm text-gray-500">Unmatched Bank Txns</p>
            <p className="text-2xl font-bold text-amber-600">{summary.unmatched_bank_transactions ?? 0}</p>
          </div>
          <div className="bg-white rounded-xl border border-gray-100 shadow-sm p-4 text-center">
            <p className="text-sm text-gray-500">Match Rate</p>
            <p className="text-2xl font-bold text-brand-600">
              {summary.total_bank_transactions > 0
                ? `${((summary.matched_count / summary.total_bank_transactions) * 100).toFixed(0)}%`
                : '—'}
            </p>
          </div>
        </div>
      )}

      {/* Suggestions */}
      <div className="bg-white rounded-xl shadow-sm border border-gray-100 overflow-hidden">
        <div className="px-6 py-4 border-b border-gray-100">
          <h2 className="text-lg font-semibold text-gray-900">Match Suggestions</h2>
          <p className="text-sm text-gray-500 mt-0.5">AI-scored matches based on amount, date, and description similarity</p>
        </div>

        {loading ? (
          <div className="flex items-center justify-center h-48">
            <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-brand-600" />
          </div>
        ) : suggestions.length === 0 ? (
          <div className="px-6 py-12 text-center text-gray-400">
            <ArrowRightLeft className="w-12 h-12 mx-auto mb-3 opacity-50" />
            <p>No match suggestions. Import transactions and create journal entries first.</p>
          </div>
        ) : (
          <div className="divide-y divide-gray-50">
            {suggestions.map((s: any, i: number) => (
              <div key={i} className="px-6 py-4 hover:bg-gray-50 transition-colors">
                <div className="flex items-center justify-between">
                  <div className="flex-1 grid grid-cols-2 gap-8">
                    {/* Bank Transaction */}
                    <div>
                      <p className="text-xs text-gray-400 uppercase tracking-wide mb-1">Bank Transaction</p>
                      <p className="font-medium text-gray-900">{s.bank_transaction?.description_raw || s.bank_description || 'Unknown'}</p>
                      <p className="text-sm text-gray-500">
                        {s.bank_transaction?.transaction_date
                          ? new Date(s.bank_transaction.transaction_date).toLocaleDateString()
                          : ''}{' '}
                        &middot; ${Math.abs(Number(s.bank_transaction?.amount || s.bank_amount || 0)).toFixed(2)}
                      </p>
                    </div>
                    {/* Journal Entry */}
                    <div>
                      <p className="text-xs text-gray-400 uppercase tracking-wide mb-1">Journal Entry</p>
                      <p className="font-medium text-gray-900">{s.journal_entry?.description || s.entry_description || 'Unknown'}</p>
                      <p className="text-sm text-gray-500">
                        {s.journal_entry?.entry_date
                          ? new Date(s.journal_entry.entry_date).toLocaleDateString()
                          : ''}
                      </p>
                    </div>
                  </div>
                  <div className="flex items-center gap-4 ml-4">
                    {/* Score */}
                    <div className="text-center">
                      <div className="w-12 h-12 rounded-full border-2 flex items-center justify-center font-bold text-sm"
                        style={{
                          borderColor: (s.score ?? 0) > 0.8 ? '#16a34a' : (s.score ?? 0) > 0.5 ? '#d97706' : '#dc2626',
                          color: (s.score ?? 0) > 0.8 ? '#16a34a' : (s.score ?? 0) > 0.5 ? '#d97706' : '#dc2626',
                        }}>
                        {((s.score ?? 0) * 100).toFixed(0)}%
                      </div>
                    </div>
                    <button
                      onClick={() => handleMatch(
                        s.bank_transaction?.id || s.bank_transaction_id,
                        s.journal_entry?.id || s.journal_entry_id
                      )}
                      className="px-3 py-2 bg-green-600 text-white rounded-lg hover:bg-green-700 flex items-center gap-1 text-sm transition-colors">
                      <Check className="w-4 h-4" /> Match
                    </button>
                  </div>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  )
}
