import Foundation

@Observable
final class ServerSetupViewModel {

    var serverUrl: String = "http://"
    var isLoading: Bool = false
    var error: String?
    var successVersion: String?

    func testConnection(authRepo: AuthRepository, onSuccess: @escaping () -> Void) {
        let url = serverUrl.trimmingCharacters(in: .whitespacesAndNewlines)
            .trimmingCharacters(in: CharacterSet(charactersIn: "/"))

        guard !url.isEmpty else {
            error = "Please enter a server URL."
            return
        }

        isLoading = true
        error = nil
        successVersion = nil

        authRepo.setServerUrl(url)

        Task { @MainActor in
            do {
                let version = try await authRepo.checkHealth()
                isLoading = false
                successVersion = version
                onSuccess()
            } catch {
                isLoading = false
                self.error = "Connection failed: \(error.localizedDescription)"
            }
        }
    }
}
