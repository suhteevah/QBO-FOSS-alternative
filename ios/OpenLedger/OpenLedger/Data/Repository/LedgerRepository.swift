import Foundation

@Observable
final class LedgerRepository {

    private let api: APIClient

    init(api: APIClient) {
        self.api = api
    }

    func getAccounts() async throws -> [AccountResponse] {
        try await api.request("GET", path: "/api/accounts/")
    }

    func getJournalEntries() async throws -> [JournalEntryResponse] {
        try await api.request("GET", path: "/api/journal-entries/")
    }

    func createJournalEntry(_ entry: JournalEntryCreate) async throws -> JournalEntryResponse {
        try await api.request("POST", path: "/api/journal-entries/", body: entry)
    }

    func getTransactions() async throws -> [BankTransactionResponse] {
        try await api.request("GET", path: "/api/transactions/")
    }

    func generateReport(_ request: ReportRequest) async throws -> ReportResponse {
        let path: String
        switch request.reportType {
        case "profit_loss":
            path = "/api/reports/profit-loss"
        case "balance_sheet":
            path = "/api/reports/balance-sheet"
        case "trial_balance":
            path = "/api/reports/trial-balance"
        default:
            throw APIError.httpError(400, "Unknown report type: \(request.reportType)")
        }
        return try await api.request("POST", path: path, body: request)
    }

    func getMe() async throws -> UserResponse {
        try await api.request("GET", path: "/api/auth/me")
    }

    func getPeriods() async throws -> [PeriodResponse] {
        try await api.request("GET", path: "/api/periods/")
    }

    func getAuditLogs() async throws -> [AuditLogResponse] {
        try await api.request("GET", path: "/api/audit-logs/")
    }

    func aiQuery(_ query: String) async throws -> AiQueryResponse {
        let body = AiQueryRequest(query: query)
        return try await api.request("POST", path: "/api/ai/query", body: body)
    }

    func autoMatch() async throws -> [ReconciliationSuggestion] {
        try await api.request("POST", path: "/api/reconciliation/auto-match")
    }

    func getUnmatched() async throws -> [BankTransactionResponse] {
        try await api.request("GET", path: "/api/reconciliation/unmatched")
    }
}
