import { useState } from 'react'
import { api } from '../lib/api'
import { BarChart3, Download } from 'lucide-react'

type ReportType = 'pnl' | 'balance_sheet' | 'trial_balance'

export default function Reports() {
  const [reportType, setReportType] = useState<ReportType>('pnl')
  const [startDate, setStartDate] = useState(new Date(new Date().getFullYear(), 0, 1).toISOString().split('T')[0])
  const [endDate, setEndDate] = useState(new Date().toISOString().split('T')[0])
  const [asOfDate, setAsOfDate] = useState(new Date().toISOString().split('T')[0])
  const [report, setReport] = useState<any>(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')

  async function generate() {
    setLoading(true)
    setError('')
    setReport(null)
    try {
      let data: any
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

  function renderSection(title: string, items: any[], totalLabel: string, total: number | string) {
    return (
      <div className="mb-6">
        <h3 className="text-sm font-semibold text-gray-400 uppercase tracking-wide mb-2">{title}</h3>
        <div className="space-y-1">
          {items?.map((item: any, i: number) => (
            <div key={i} className="flex justify-between py-1.5 px-2 hover:bg-gray-50 rounded">
              <span className="text-gray-700">
                {item.account_number && <span className="text-gray-400 font-mono mr-2">{item.account_number}</span>}
                {item.account_name || item.name}
              </span>
              <span className="font-mono text-gray-900">${Number(item.balance ?? item.amount ?? 0).toFixed(2)}</span>
            </div>
          ))}
        </div>
        <div className="flex justify-between py-2 px-2 mt-1 border-t border-gray-200 font-semibold">
          <span>{totalLabel}</span>
          <span className="font-mono">${Number(total).toFixed(2)}</span>
        </div>
      </div>
    )
  }

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
          {reportType === 'pnl' && (
            <div>
              <h2 className="text-lg font-bold text-gray-900 mb-1">Profit & Loss Statement</h2>
              <p className="text-sm text-gray-500 mb-6">{report.start_date} to {report.end_date}</p>
              {renderSection('Revenue', report.revenue?.accounts || [], 'Total Revenue', report.revenue?.total ?? 0)}
              {renderSection('Cost of Goods Sold', report.cogs?.accounts || [], 'Total COGS', report.cogs?.total ?? 0)}
              <div className="flex justify-between py-2 px-2 bg-gray-50 rounded font-bold text-gray-900 mb-6">
                <span>Gross Profit</span>
                <span className="font-mono">${Number(report.gross_profit ?? 0).toFixed(2)}</span>
              </div>
              {renderSection('Operating Expenses', report.operating_expenses?.accounts || [], 'Total Operating Expenses', report.operating_expenses?.total ?? 0)}
              <div className="flex justify-between py-3 px-2 bg-brand-50 rounded-lg font-bold text-brand-700 text-lg">
                <span>Net Income</span>
                <span className="font-mono">${Number(report.net_income ?? 0).toFixed(2)}</span>
              </div>
            </div>
          )}

          {reportType === 'balance_sheet' && (
            <div>
              <h2 className="text-lg font-bold text-gray-900 mb-1">Balance Sheet</h2>
              <p className="text-sm text-gray-500 mb-6">As of {report.as_of}</p>
              {renderSection('Assets', report.assets?.accounts || [], 'Total Assets', report.assets?.total ?? 0)}
              {renderSection('Liabilities', report.liabilities?.accounts || [], 'Total Liabilities', report.liabilities?.total ?? 0)}
              {renderSection('Equity', report.equity?.accounts || [], 'Total Equity', report.equity?.total ?? 0)}
              <div className="flex justify-between py-3 px-2 bg-brand-50 rounded-lg font-bold text-brand-700 text-lg">
                <span>Total Liabilities + Equity</span>
                <span className="font-mono">
                  ${(Number(report.liabilities?.total ?? 0) + Number(report.equity?.total ?? 0)).toFixed(2)}
                </span>
              </div>
            </div>
          )}

          {reportType === 'trial_balance' && (
            <div>
              <h2 className="text-lg font-bold text-gray-900 mb-1">Trial Balance</h2>
              <p className="text-sm text-gray-500 mb-6">As of {report.as_of}</p>
              <table className="w-full text-sm">
                <thead className="bg-gray-50">
                  <tr>
                    <th className="text-left px-4 py-2 text-gray-500">Account</th>
                    <th className="text-right px-4 py-2 text-gray-500">Debit</th>
                    <th className="text-right px-4 py-2 text-gray-500">Credit</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-gray-50">
                  {(report.accounts || []).map((a: any, i: number) => (
                    <tr key={i} className="hover:bg-gray-50">
                      <td className="px-4 py-2">
                        <span className="font-mono text-gray-400 mr-2">{a.account_number}</span>
                        {a.account_name}
                      </td>
                      <td className="px-4 py-2 text-right font-mono">{Number(a.debit) > 0 ? `$${Number(a.debit).toFixed(2)}` : ''}</td>
                      <td className="px-4 py-2 text-right font-mono">{Number(a.credit) > 0 ? `$${Number(a.credit).toFixed(2)}` : ''}</td>
                    </tr>
                  ))}
                </tbody>
                <tfoot className="border-t-2 border-gray-300 font-bold">
                  <tr>
                    <td className="px-4 py-2">Total</td>
                    <td className="px-4 py-2 text-right font-mono">${Number(report.total_debits ?? 0).toFixed(2)}</td>
                    <td className="px-4 py-2 text-right font-mono">${Number(report.total_credits ?? 0).toFixed(2)}</td>
                  </tr>
                </tfoot>
              </table>
            </div>
          )}
        </div>
      )}
    </div>
  )
}
