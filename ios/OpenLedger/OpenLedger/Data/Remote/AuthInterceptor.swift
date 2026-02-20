import Foundation

struct AuthInterceptor {

    /// Applies authentication headers to the given URLRequest.
    /// Priority: API key (mobile auth) first, then JWT bearer token.
    func apply(to request: inout URLRequest, keychain: KeychainManager) {
        if let apiKey = keychain.apiKey, !apiKey.isEmpty {
            request.setValue(apiKey, forHTTPHeaderField: "X-API-Key")
        } else if let jwt = keychain.jwtToken, !jwt.isEmpty {
            request.setValue("Bearer \(jwt)", forHTTPHeaderField: "Authorization")
        }
    }
}
