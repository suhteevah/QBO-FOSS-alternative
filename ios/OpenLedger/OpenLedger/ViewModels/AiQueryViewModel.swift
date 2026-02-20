import Foundation

@Observable
final class AiQueryViewModel {
    var query = ""
    var isLoading = false
    var error: String?
    var response: AiQueryResponse?

    private let repo: LedgerRepository

    init(repo: LedgerRepository) {
        self.repo = repo
    }

    func submit() async {
        let q = query.trimmingCharacters(in: .whitespacesAndNewlines)
        guard !q.isEmpty else { return }
        isLoading = true
        error = nil
        response = nil
        do {
            response = try await repo.aiQuery(q)
            isLoading = false
        } catch {
            self.error = error.localizedDescription
            isLoading = false
        }
    }
}
