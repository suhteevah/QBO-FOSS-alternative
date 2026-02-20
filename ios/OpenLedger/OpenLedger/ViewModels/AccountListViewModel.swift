import Foundation

@Observable
final class AccountListViewModel {
    var isLoading = true
    var error: String?
    var accounts: [AccountResponse] = []

    var groupedAccounts: [(type: String, accounts: [AccountResponse])] {
        let grouped = Dictionary(grouping: accounts) { $0.accountType }
        return grouped.sorted { $0.key < $1.key }.map { (type: $0.key, accounts: $0.value) }
    }

    private let repo: LedgerRepository

    init(repo: LedgerRepository) {
        self.repo = repo
    }

    func load() async {
        isLoading = true
        error = nil
        do {
            accounts = try await repo.getAccounts()
            isLoading = false
        } catch {
            self.error = error.localizedDescription
            isLoading = false
        }
    }
}
