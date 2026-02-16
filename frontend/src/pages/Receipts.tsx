import { useState, useEffect, useRef } from 'react'
import { api } from '../lib/api'
import { Camera, Upload, Zap, FileText } from 'lucide-react'

export default function Receipts() {
  const [receipts, setReceipts] = useState<any[]>([])
  const [loading, setLoading] = useState(true)
  const [uploading, setUploading] = useState(false)
  const [message, setMessage] = useState<{ type: 'success' | 'error'; text: string } | null>(null)
  const fileRef = useRef<HTMLInputElement>(null)

  useEffect(() => { load() }, [])

  async function load() {
    setLoading(true)
    try {
      const data = await api.receipts.list()
      setReceipts(data)
    } catch (err: any) {
      setMessage({ type: 'error', text: err.message })
    } finally {
      setLoading(false)
    }
  }

  async function handleUpload(e: React.ChangeEvent<HTMLInputElement>) {
    const file = e.target.files?.[0]
    if (!file) return
    setUploading(true)
    setMessage(null)
    try {
      await api.receipts.upload(file)
      setMessage({ type: 'success', text: 'Receipt uploaded and processed' })
      load()
    } catch (err: any) {
      setMessage({ type: 'error', text: err.message })
    } finally {
      setUploading(false)
      if (fileRef.current) fileRef.current.value = ''
    }
  }

  async function handleClassify(id: string) {
    try {
      const result = await api.receipts.classify(id)
      setMessage({
        type: 'success',
        text: `Classified: ${result.suggested_account_name} (${(result.confidence * 100).toFixed(0)}% confidence)`,
      })
    } catch (err: any) {
      setMessage({ type: 'error', text: err.message })
    }
  }

  async function handleCreateEntry(id: string) {
    try {
      await api.receipts.createEntry(id)
      setMessage({ type: 'success', text: 'Journal entry created from receipt' })
      load()
    } catch (err: any) {
      setMessage({ type: 'error', text: err.message })
    }
  }

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">Receipts</h1>
          <p className="text-gray-500 mt-1">Upload receipts for OCR processing and journal entry creation</p>
        </div>
        <div>
          <input type="file" ref={fileRef} onChange={handleUpload} accept="image/*,.pdf" className="hidden" />
          <button onClick={() => fileRef.current?.click()} disabled={uploading}
            className="px-4 py-2 bg-brand-600 text-white rounded-lg hover:bg-brand-700 flex items-center gap-2 disabled:opacity-50 transition-colors">
            <Camera className="w-4 h-4" />
            {uploading ? 'Uploading...' : 'Upload Receipt'}
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

      {loading ? (
        <div className="flex items-center justify-center h-48">
          <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-brand-600" />
        </div>
      ) : receipts.length === 0 ? (
        <div className="bg-white rounded-xl shadow-sm border border-gray-100 px-6 py-12 text-center text-gray-400">
          <Camera className="w-12 h-12 mx-auto mb-3 opacity-50" />
          <p>No receipts yet. Upload a receipt image or PDF to get started.</p>
        </div>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
          {receipts.map((r: any) => (
            <div key={r.id} className="bg-white rounded-xl shadow-sm border border-gray-100 overflow-hidden">
              <div className="p-4 space-y-3">
                <div className="flex items-center justify-between">
                  <h3 className="font-semibold text-gray-900 truncate">{r.merchant_name || 'Unknown Merchant'}</h3>
                  <span className={`px-2 py-0.5 rounded-full text-xs font-medium ${
                    r.is_processed ? 'bg-green-50 text-green-700' : 'bg-yellow-50 text-yellow-700'
                  }`}>
                    {r.is_processed ? 'Processed' : 'Pending'}
                  </span>
                </div>
                <div className="grid grid-cols-2 gap-2 text-sm">
                  <div>
                    <p className="text-gray-400">Date</p>
                    <p className="text-gray-700">{r.transaction_date ? new Date(r.transaction_date).toLocaleDateString() : '—'}</p>
                  </div>
                  <div>
                    <p className="text-gray-400">Total</p>
                    <p className="text-gray-900 font-semibold font-mono">{r.total_amount ? `$${Number(r.total_amount).toFixed(2)}` : '—'}</p>
                  </div>
                  <div>
                    <p className="text-gray-400">Tax</p>
                    <p className="text-gray-700 font-mono">{r.tax_amount ? `$${Number(r.tax_amount).toFixed(2)}` : '—'}</p>
                  </div>
                  <div>
                    <p className="text-gray-400">OCR Confidence</p>
                    <p className="text-gray-700">{r.ocr_confidence ? `${(Number(r.ocr_confidence) * 100).toFixed(0)}%` : '—'}</p>
                  </div>
                </div>
                {r.is_processed && (
                  <div className="flex gap-2 pt-2 border-t border-gray-100">
                    <button onClick={() => handleClassify(r.id)}
                      className="flex-1 px-3 py-1.5 bg-gray-100 text-gray-700 rounded-lg hover:bg-gray-200 flex items-center justify-center gap-1 text-sm transition-colors">
                      <Zap className="w-3.5 h-3.5" /> Classify
                    </button>
                    <button onClick={() => handleCreateEntry(r.id)}
                      className="flex-1 px-3 py-1.5 bg-brand-600 text-white rounded-lg hover:bg-brand-700 flex items-center justify-center gap-1 text-sm transition-colors">
                      <FileText className="w-3.5 h-3.5" /> Create Entry
                    </button>
                  </div>
                )}
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  )
}
