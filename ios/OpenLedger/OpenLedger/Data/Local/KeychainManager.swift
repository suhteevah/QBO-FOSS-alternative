import Foundation
import Security

@Observable
final class KeychainManager {

    private static let service = "com.openledger.ios"

    // MARK: - Keys

    private enum Key: String {
        case serverUrl = "server_url"
        case apiKey = "api_key"
        case jwtToken = "jwt_token"
    }

    // MARK: - Computed properties backed by Keychain

    var serverUrl: String? {
        get { read(key: .serverUrl) }
        set { save(key: .serverUrl, value: newValue) }
    }

    var apiKey: String? {
        get { read(key: .apiKey) }
        set { save(key: .apiKey, value: newValue) }
    }

    var jwtToken: String? {
        get { read(key: .jwtToken) }
        set { save(key: .jwtToken, value: newValue) }
    }

    // MARK: - Convenience queries

    func isConfigured() -> Bool {
        guard let url = serverUrl, !url.isEmpty,
              let key = apiKey, !key.isEmpty else {
            return false
        }
        return true
    }

    func hasServerUrl() -> Bool {
        guard let url = serverUrl, !url.isEmpty else { return false }
        return true
    }

    func clear() {
        delete(key: .serverUrl)
        delete(key: .apiKey)
        delete(key: .jwtToken)
    }

    // MARK: - Keychain primitives

    private func save(key: Key, value: String?) {
        // Delete first to avoid duplicates
        delete(key: key)

        guard let value, !value.isEmpty,
              let data = value.data(using: .utf8) else {
            return
        }

        let query: [String: Any] = [
            kSecClass as String: kSecClassGenericPassword,
            kSecAttrService as String: Self.service,
            kSecAttrAccount as String: key.rawValue,
            kSecValueData as String: data,
            kSecAttrAccessible as String: kSecAttrAccessibleAfterFirstUnlock,
        ]

        SecItemAdd(query as CFDictionary, nil)
    }

    private func read(key: Key) -> String? {
        let query: [String: Any] = [
            kSecClass as String: kSecClassGenericPassword,
            kSecAttrService as String: Self.service,
            kSecAttrAccount as String: key.rawValue,
            kSecReturnData as String: true,
            kSecMatchLimit as String: kSecMatchLimitOne,
        ]

        var item: CFTypeRef?
        let status = SecItemCopyMatching(query as CFDictionary, &item)

        guard status == errSecSuccess,
              let data = item as? Data,
              let string = String(data: data, encoding: .utf8) else {
            return nil
        }

        return string
    }

    @discardableResult
    private func delete(key: Key) -> Bool {
        let query: [String: Any] = [
            kSecClass as String: kSecClassGenericPassword,
            kSecAttrService as String: Self.service,
            kSecAttrAccount as String: key.rawValue,
        ]

        let status = SecItemDelete(query as CFDictionary)
        return status == errSecSuccess || status == errSecItemNotFound
    }
}
