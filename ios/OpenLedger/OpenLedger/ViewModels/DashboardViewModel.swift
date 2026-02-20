import Foundation

@Observable
final class DashboardViewModel {
    var isLoading = true
    var error: String?
    var userName: String?
    var userRole: String?
    var accountCount = 0
    var entryCount = 0
    var txnCount = 0

    private let repo: LedgerRepository

    init(repo: LedgerRepository) {
        self.repo = repo
    }

    func load() async {
        isLoading = true
        error = nil
        do {
            async let me = repo.getMe()
            async let accounts = repo.getAccounts()
            async let entries = repo.getJournalEntries()
            async let txns = repo.getTransactions()

            let user = try await me
            let accts = try await accounts
            let jEntries = try await entries
            let transactions = try await txns

            userName = user.fullName ?? user.email
            userRole = user.role
            accountCount = accts.count
            entryCount = jEntries.count
            txnCount = transactions.count
            isLoading = false
        } catch {
            self.error = error.localizedDescription
            isLoading = false
        }
    }
}
