import Foundation

// MARK: - Type-erased Encodable wrapper

private struct AnyEncodable: Encodable {
    private let encodeFunc: (Encoder) throws -> Void

    init(_ wrapped: any Encodable) {
        encodeFunc = wrapped.encode(to:)
    }

    func encode(to encoder: Encoder) throws {
        try encodeFunc(encoder)
    }
}

enum APIError: LocalizedError {
    case unauthorized
    case httpError(Int, String)
    case networkError(Error)
    case noServerUrl

    var errorDescription: String? {
        switch self {
        case .unauthorized:
            return "Unauthorized. Please re-authenticate."
        case .httpError(let code, let message):
            return "HTTP \(code): \(message)"
        case .networkError(let error):
            return error.localizedDescription
        case .noServerUrl:
            return "No server URL configured."
        }
    }
}

@Observable
final class APIClient {

    private let session: URLSession
    private let keychain: KeychainManager
    private let interceptor = AuthInterceptor()

    private var decoder: JSONDecoder {
        let d = JSONDecoder()
        d.keyDecodingStrategy = .convertFromSnakeCase
        return d
    }

    private var encoder: JSONEncoder {
        let e = JSONEncoder()
        e.keyEncodingStrategy = .convertToSnakeCase
        return e
    }

    init(keychain: KeychainManager, session: URLSession = .shared) {
        self.keychain = keychain
        self.session = session
    }

    // MARK: - Core request

    func request<T: Decodable>(
        _ method: String,
        path: String,
        body: (any Encodable)? = nil
    ) async throws -> T {
        guard let baseUrl = keychain.serverUrl, !baseUrl.isEmpty else {
            throw APIError.noServerUrl
        }

        guard let url = URL(string: baseUrl + path) else {
            throw APIError.noServerUrl
        }

        var urlRequest = URLRequest(url: url)
        urlRequest.httpMethod = method
        urlRequest.setValue("application/json", forHTTPHeaderField: "Content-Type")
        urlRequest.setValue("application/json", forHTTPHeaderField: "Accept")

        if let body {
            urlRequest.httpBody = try encoder.encode(AnyEncodable(body))
        }

        interceptor.apply(to: &urlRequest, keychain: keychain)

        let data: Data
        let response: URLResponse
        do {
            (data, response) = try await session.data(for: urlRequest)
        } catch {
            throw APIError.networkError(error)
        }

        guard let httpResponse = response as? HTTPURLResponse else {
            throw APIError.networkError(
                NSError(domain: "APIClient", code: -1, userInfo: [NSLocalizedDescriptionKey: "Invalid response"])
            )
        }

        switch httpResponse.statusCode {
        case 200..<300:
            return try decoder.decode(T.self, from: data)
        case 401:
            throw APIError.unauthorized
        default:
            let message = String(data: data, encoding: .utf8) ?? "Unknown error"
            throw APIError.httpError(httpResponse.statusCode, message)
        }
    }

    // MARK: - Multipart upload

    func upload<T: Decodable>(
        path: String,
        fileData: Data,
        fileName: String,
        mimeType: String
    ) async throws -> T {
        guard let baseUrl = keychain.serverUrl, !baseUrl.isEmpty else {
            throw APIError.noServerUrl
        }

        guard let url = URL(string: baseUrl + path) else {
            throw APIError.noServerUrl
        }

        let boundary = UUID().uuidString
        var urlRequest = URLRequest(url: url)
        urlRequest.httpMethod = "POST"
        urlRequest.setValue("multipart/form-data; boundary=\(boundary)", forHTTPHeaderField: "Content-Type")
        urlRequest.setValue("application/json", forHTTPHeaderField: "Accept")

        interceptor.apply(to: &urlRequest, keychain: keychain)

        var bodyData = Data()
        bodyData.append("--\(boundary)\r\n".data(using: .utf8)!)
        bodyData.append("Content-Disposition: form-data; name=\"file\"; filename=\"\(fileName)\"\r\n".data(using: .utf8)!)
        bodyData.append("Content-Type: \(mimeType)\r\n\r\n".data(using: .utf8)!)
        bodyData.append(fileData)
        bodyData.append("\r\n--\(boundary)--\r\n".data(using: .utf8)!)

        urlRequest.httpBody = bodyData

        let data: Data
        let response: URLResponse
        do {
            (data, response) = try await session.data(for: urlRequest)
        } catch {
            throw APIError.networkError(error)
        }

        guard let httpResponse = response as? HTTPURLResponse else {
            throw APIError.networkError(
                NSError(domain: "APIClient", code: -1, userInfo: [NSLocalizedDescriptionKey: "Invalid response"])
            )
        }

        switch httpResponse.statusCode {
        case 200..<300:
            return try decoder.decode(T.self, from: data)
        case 401:
            throw APIError.unauthorized
        default:
            let message = String(data: data, encoding: .utf8) ?? "Unknown error"
            throw APIError.httpError(httpResponse.statusCode, message)
        }
    }
}
