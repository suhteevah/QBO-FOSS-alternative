import Foundation

@Observable
final class ApiKeySetupViewModel {

    var keyName: String = "iPhone"
    var isLoading: Bool = false
    var error: String?

    func createKey(authRepo: AuthRepository, onSuccess: @escaping () -> Void) {
        guard !keyName.trimmingCharacters(in: .whitespaces).isEmpty else {
            error = "Please enter a device name."
            return
        }

        isLoading = true
        error = nil

        Task { @MainActor in
            do {
                try await authRepo.createApiKey(name: keyName)
                isLoading = false
                onSuccess()
            } catch {
                isLoading = false
                self.error = "Failed to create key: \(error.localizedDescription)"
            }
        }
    }
}
