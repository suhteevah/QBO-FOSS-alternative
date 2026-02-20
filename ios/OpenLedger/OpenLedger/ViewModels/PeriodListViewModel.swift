import Foundation

@Observable
final class PeriodListViewModel {
    var isLoading = true
    var error: String?
    var periods: [PeriodResponse] = []

    private let repo: LedgerRepository

    init(repo: LedgerRepository) {
        self.repo = repo
    }

    func load() async {
        isLoading = true
        error = nil
        do {
            periods = try await repo.getPeriods()
            isLoading = false
        } catch {
            self.error = error.localizedDescription
            isLoading = false
        }
    }
}
