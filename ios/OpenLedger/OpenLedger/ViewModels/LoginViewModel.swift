import Foundation

@Observable
final class LoginViewModel {

    var email: String = ""
    var password: String = ""
    var isLoading: Bool = false
    var error: String?

    func login(authRepo: AuthRepository, onSuccess: @escaping () -> Void) {
        guard !email.trimmingCharacters(in: .whitespaces).isEmpty,
              !password.isEmpty else {
            error = "Please enter email and password."
            return
        }

        isLoading = true
        error = nil

        Task { @MainActor in
            do {
                try await authRepo.login(email: email, password: password)
                isLoading = false
                onSuccess()
            } catch {
                isLoading = false
                self.error = "Login failed: \(error.localizedDescription)"
            }
        }
    }
}
