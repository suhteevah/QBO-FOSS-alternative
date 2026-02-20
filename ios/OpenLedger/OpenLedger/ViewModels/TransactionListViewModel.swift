import Foundation

@Observable
final class TransactionListViewModel {
    var isLoading = true
    var error: String?
    var transactions: [BankTransactionResponse] = []

    private let repo: LedgerRepository

    init(repo: LedgerRepository) {
        self.repo = repo
    }

    func load() async {
        isLoading = true
        error = nil
        do {
            transactions = try await repo.getTransactions()
            isLoading = false
        } catch {
            self.error = error.localizedDescription
            isLoading = false
        }
    }
}
