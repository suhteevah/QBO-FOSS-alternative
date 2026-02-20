import Foundation

@Observable
final class JournalListViewModel {
    var isLoading = true
    var error: String?
    var entries: [JournalEntryResponse] = []

    private let repo: LedgerRepository

    init(repo: LedgerRepository) {
        self.repo = repo
    }

    func load() async {
        isLoading = true
        error = nil
        do {
            entries = try await repo.getJournalEntries()
            isLoading = false
        } catch {
            self.error = error.localizedDescription
            isLoading = false
        }
    }
}
