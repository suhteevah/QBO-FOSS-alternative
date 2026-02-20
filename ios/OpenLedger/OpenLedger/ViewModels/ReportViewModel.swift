import Foundation

@Observable
final class ReportViewModel {
    var reportType = "profit_loss"
    var startDate = Calendar.current.date(byAdding: .month, value: -1, to: .now) ?? .now
    var endDate = Date.now
    var accountingBasis: String? = "accrual"
    var isLoading = false
    var error: String?
    var report: ReportResponse?

    private let repo: LedgerRepository

    init(repo: LedgerRepository) {
        self.repo = repo
    }

    func generate() async {
        isLoading = true
        error = nil
        let formatter = DateFormatter()
        formatter.dateFormat = "yyyy-MM-dd"
        let request = ReportRequest(
            reportType: reportType,
            startDate: formatter.string(from: startDate),
            endDate: formatter.string(from: endDate),
            accountingBasis: accountingBasis
        )
        do {
            report = try await repo.generateReport(request)
            isLoading = false
        } catch {
            self.error = error.localizedDescription
            isLoading = false
        }
    }
}
