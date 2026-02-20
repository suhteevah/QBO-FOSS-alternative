import Foundation

@Observable
final class ReconciliationViewModel {
    var isLoading = false
    var error: String?
    var suggestions: [ReconciliationSuggestion] = []
    var unmatched: [BankTransactionResponse] = []

    private let repo: LedgerRepository

    init(repo: LedgerRepository) {
        self.repo = repo
    }

    func load() async {
        isLoading = true
        error = nil
        do {
            unmatched = try await repo.getUnmatched()
            isLoading = false
        } catch {
            self.error = error.localizedDescription
            isLoading = false
        }
    }

    func autoMatch() async {
        isLoading = true
        error = nil
        do {
            suggestions = try await repo.autoMatch()
            unmatched = try await repo.getUnmatched()
            isLoading = false
        } catch {
            self.error = error.localizedDescription
            isLoading = false
        }
    }
}
