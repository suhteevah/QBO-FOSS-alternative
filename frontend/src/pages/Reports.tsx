import { useState } from 'react'
import { api } from '../lib/api'
import { BarChart3 } from 'lucide-react'

type ReportType = 'pnl' | 'balance_sheet' | 'trial_balance'

interface ReportLineItem {
  account_number: string
  account_name: string
  amount: string | number
}

interface ReportSection {
  title: string
  items: ReportLineItem[]
  subtotal: string | number
}

interface ReportData {
  report_type: string
  period: string
  generated_at: string
  accounting_basis: string
  sections: ReportSection[]
  net_total: string | number
}

export default function Reports() {
  const [reportType, setReportType] = useState<ReportType>('pnl')
  const [startDate, setStartDate] = useState(new Date(new Date().getFullYear(), 0, 1).toISOString().split('T')[0])
  const [endDate, setEndDate] = useState(new Date().toISOString().split('T')[0])
  const [asOfDate, setAsOfDate] = useState(new Date().toISOString().split('T')[0])
  const [report, setReport] = useState<ReportData | null>(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')

  async function generate() {
    setLoading(true)
    setError('')
    setReport(null)
    try {
      let data: ReportData
      if (reportType === 'pnl') {
        data = await api.reports.profitLoss(startDate, endDate)
      } else if (reportType === 'balance_sheet') {
        data = await api.reports.balanceSheet(asOfDate)
      } else {
        data = await api.reports.trialBalance(asOfDate)
      }
      setReport(data)
    } catch (err: any) {
      setError(err.message)
    } finally {
      setLoading(false)
    }
  }

  // Highlight sections that are summary-only (no line items, just a subtotal)
  const SUMMARY_TITLES = new Set([
    'Gross Profit', 'Operating Income', 'Net Income',
  ])

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold text-gray-900">Financial Reports</h1>
        <p className="text-gray-500 mt-1">Generate GAAP-compliant financial statements</p>
      </div>

      {/* Report Selector */}
      <div className="bg-white rounded-xl shadow-sm border border-gray-100 p-6">
        <div className="flex flex-wrap gap-4 items-end">
          <div>
            <label className="block text-sm font-medium text-gray-600 mb-1">Report Type</label>
            <select value={reportType} onChange={e => setReportType(e.target.value as ReportType)}
              className="px-3 py-2 border rounded-lg text-sm focus:ring-2 focus:ring-brand-500 outline-none">
              <option value="pnl">Profit & Loss</option>
              <option value="balance_sheet">Balance Sheet</option>
              <option value="trial_balance">Trial Balance</option>
            </select>
          </div>
          {reportType === 'pnl' ? (
            <>
              <div>
                <label className="block text-sm font-medium text-gray-600 mb-1">Start Date</label>
                <input type="date" value={startDate} onChange={e => setStartDate(e.target.value)}
                  className="px-3 py-2 border rounded-lg text-sm focus:ring-2 focus:ring-brand-500 outline-none" />
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-600 mb-1">End Date</label>
                <input type="date" value={endDate} onChange={e => setEndDate(e.target.value)}
                  className="px-3 py-2 border rounded-lg text-sm focus:ring-2 focus:ring-brand-500 outline-none" />
              </div>
            </>
          ) : (
            <div>
              <label className="block text-sm font-medium text-gray-600 mb-1">As of Date</label>
              <input type="date" value={asOfDate} onChange={e => setAsOfDate(e.target.value)}
                className="px-3 py-2 border rounded-lg text-sm focus:ring-2 focus:ring-brand-500 outline-none" />
            </div>
          )}
          <button onClick={generate} disabled={loading}
            className="px-4 py-2 bg-brand-600 text-white rounded-lg hover:bg-brand-700 flex items-center gap-2 disabled:opacity-50 transition-colors">
            <BarChart3 className="w-4 h-4" />
            {loading ? 'Generating...' : 'Generate Report'}
          </button>
        </div>
      </div>

      {error && <div className="bg-red-50 text-red-700 px-4 py-3 rounded-lg text-sm">{error}</div>}

      {/* Report Output */}
      {report && (
        <div className="bg-white rounded-xl shadow-sm border border-gray-100 p-6">
          {/* Report Header */}
          <div className="mb-6">
            <h2 className="text-lg font-bold text-gray-900">
              {report.report_type === 'profit_loss' && 'Profit & Loss Statement'}
              {report.report_type === 'balance_sheet' && 'Balance Sheet'}
              {report.report_type === 'trial_balance' && 'Trial Balance'}
            </h2>
            <p className="text-sm text-gray-500">{report.period}</p>
            <p className="text-xs text-gray-400 mt-1">
              Basis: {report.accounting_basis} | Generated: {new Date(report.generated_at).toLocaleString()}
            </p>
          </div>

          {/* Sections */}
          {report.sections.map((section, idx) => {
            const isSummary = SUMMARY_TITLES.has(section.title) && section.items.length === 0

            // Summary-only rows (like Gross Profit, Operating Income)
            if (isSummary) {
              return (
                <div key={idx} className="flex justify-between py-3 px-2 bg-brand-50 rounded-lg font-bold text-brand-700 text-lg mb-4">
                  <span>{section.title}</span>
                  <span className="font-mono">${Number(section.subtotal).toFixed(2)}</span>
                </div>
              )
            }

            // Regular section with line items
            return (
              <div key={idx} className="mb-6">
                <h3 className="text-sm font-semibold text-gray-400 uppercase tracking-wide mb-2">
                  {section.title}
                </h3>
                {section.items.length > 0 && (
                  <div className="space-y-1">
                    {section.items.map((item, i) => (
                      <div key={i} className="flex justify-between py-1.5 px-2 hover:bg-gray-50 rounded">
                        <span className="text-gray-700">
                          {item.account_number && (
                            <span className="text-gray-400 font-mono mr-2">{item.account_number}</span>
                          )}
                          {item.account_name}
                        </span>
                        <span className="font-mono text-gray-900">
                          ${Number(item.amount).toFixed(2)}
                        </span>
                      </div>
                    ))}
                  </div>
                )}
                <div className="flex justify-between py-2 px-2 mt-1 border-t border-gray-200 font-semibold">
                  <span>Total {section.title}</span>
                  <span className="font-mono">${Number(section.subtotal).toFixed(2)}</span>
                </div>
              </div>
            )
          })}

          {/* Net Total */}
          <div className="flex justify-between py-3 px-3 bg-gray-900 rounded-lg font-bold text-white text-lg mt-4">
            <span>
              {report.report_type === 'profit_loss' && 'Net Income'}
              {report.report_type === 'balance_sheet' && 'Total Liabilities + Equity'}
              {report.report_type === 'trial_balance' && 'Net Difference (Debits - Credits)'}
            </span>
            <span className="font-mono">${Number(report.net_total).toFixed(2)}</span>
          </div>
        </div>
      )}
    </div>
  )
}
