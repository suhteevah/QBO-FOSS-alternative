import Foundation
import UIKit

@Observable
final class AuthRepository {

    private let api: APIClient
    private let keychain: KeychainManager

    init(api: APIClient, keychain: KeychainManager) {
        self.api = api
        self.keychain = keychain
    }

    /// Checks server health and returns the version string.
    func checkHealth() async throws -> String {
        let response: HealthResponse = try await api.request("GET", path: "/health")
        return response.version
    }

    /// Logs in with email + password, stores JWT in keychain.
    func login(email: String, password: String) async throws {
        let body = LoginRequest(email: email, password: password)
        let response: TokenResponse = try await api.request("POST", path: "/api/auth/login", body: body)
        keychain.jwtToken = response.accessToken
    }

    /// Creates an API key for this iOS device, stores the raw key, clears the JWT.
    func createApiKey(name: String) async throws {
        let deviceModel = UIDevice.current.model
        let body = ApiKeyCreateRequest(
            name: name,
            platform: "ios",
            deviceInfo: deviceModel
        )
        let response: ApiKeyCreateResponse = try await api.request("POST", path: "/api/keys/", body: body)
        keychain.apiKey = response.rawKey
        keychain.jwtToken = nil  // No longer need JWT -- API key is permanent
    }

    func setServerUrl(_ url: String) {
        keychain.serverUrl = url
    }

    func logout() {
        keychain.clear()
    }
}
