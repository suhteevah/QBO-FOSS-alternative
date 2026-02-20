import Foundation

@Observable
final class AuditLogViewModel {
    var isLoading = true
    var error: String?
    var logs: [AuditLogResponse] = []

    private let repo: LedgerRepository

    init(repo: LedgerRepository) {
        self.repo = repo
    }

    func load() async {
        isLoading = true
        error = nil
        do {
            logs = try await repo.getAuditLogs()
            isLoading = false
        } catch {
            self.error = error.localizedDescription
            isLoading = false
        }
    }
}
