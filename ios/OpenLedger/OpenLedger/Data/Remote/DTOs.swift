import Foundation

// MARK: - Auth

struct LoginRequest: Codable {
    let email: String
    let password: String
}

struct TokenResponse: Codable {
    let accessToken: String
    let tokenType: String
    let role: String

    init(accessToken: String, tokenType: String = "bearer", role: String) {
        self.accessToken = accessToken
        self.tokenType = tokenType
        self.role = role
    }
}

struct UserResponse: Codable {
    let id: String
    let email: String
    let fullName: String?
    let role: String
    let organizationId: String
}

// MARK: - API Keys (platform-aware for Android + iOS)

struct ApiKeyCreateRequest: Codable {
    let name: String
    let platform: String
    let deviceInfo: String?
    let expiresInDays: Int?

    init(name: String, platform: String = "ios", deviceInfo: String? = nil, expiresInDays: Int? = nil) {
        self.name = name
        self.platform = platform
        self.deviceInfo = deviceInfo
        self.expiresInDays = expiresInDays
    }
}

struct ApiKeyCreateResponse: Codable {
    let id: String
    let name: String
    let keyPrefix: String
    let rawKey: String
    let platform: String
    let deviceInfo: String?
    let expiresAt: String?
    let createdAt: String
}

struct ApiKeyResponse: Codable {
    let id: String
    let name: String
    let keyPrefix: String
    let platform: String
    let deviceInfo: String?
    let expiresAt: String?
    let lastUsedAt: String?
    let isRevoked: Bool
    let createdAt: String
}

// MARK: - Accounts

struct AccountResponse: Codable {
    let id: String
    let accountNumber: String
    let name: String
    let description: String?
    let accountType: String
    let accountSubtype: String?
    let normalBalance: String
    let isActive: Bool
}

// MARK: - Journal Entries

struct LineItemResponse: Codable {
    let id: String
    let accountId: String
    let description: String?
    let debitAmount: String
    let creditAmount: String
}

struct JournalEntryResponse: Codable {
    let id: String
    let entryNumber: String?
    let entryDate: String
    let description: String?
    let source: String
    let status: String
    let aiConfidence: String?
    let lineItems: [LineItemResponse]
    let createdAt: String

    init(
        id: String,
        entryNumber: String? = nil,
        entryDate: String,
        description: String? = nil,
        source: String,
        status: String,
        aiConfidence: String? = nil,
        lineItems: [LineItemResponse] = [],
        createdAt: String
    ) {
        self.id = id
        self.entryNumber = entryNumber
        self.entryDate = entryDate
        self.description = description
        self.source = source
        self.status = status
        self.aiConfidence = aiConfidence
        self.lineItems = lineItems
        self.createdAt = createdAt
    }
}

struct LineItemCreate: Codable {
    let accountId: String
    let description: String?
    let debitAmount: String
    let creditAmount: String

    init(accountId: String, description: String? = nil, debitAmount: String = "0.00", creditAmount: String = "0.00") {
        self.accountId = accountId
        self.description = description
        self.debitAmount = debitAmount
        self.creditAmount = creditAmount
    }
}

struct JournalEntryCreate: Codable {
    let entryDate: String
    let description: String
    let memo: String?
    let source: String
    let lineItems: [LineItemCreate]

    init(entryDate: String, description: String, memo: String? = nil, source: String = "manual", lineItems: [LineItemCreate]) {
        self.entryDate = entryDate
        self.description = description
        self.memo = memo
        self.source = source
        self.lineItems = lineItems
    }
}

// MARK: - Transactions

struct BankTransactionResponse: Codable {
    let id: String
    let transactionDate: String
    let descriptionRaw: String
    let descriptionCleaned: String?
    let amount: String
    let aiCategory: String?
    let aiConfidence: String?
    let isReconciled: Bool
    let suggestedAccountId: String?
}

// MARK: - Reports

struct ReportRequest: Codable {
    let reportType: String
    let startDate: String
    let endDate: String
    let accountingBasis: String?
}

struct ReportLineItemDto: Codable {
    let accountNumber: String
    let accountName: String
    let amount: String
}

struct ReportSection: Codable {
    let title: String
    let items: [ReportLineItemDto]
    let subtotal: String
}

struct ReportResponse: Codable {
    let reportType: String
    let period: String
    let generatedAt: String
    let accountingBasis: String
    let sections: [ReportSection]
    let netTotal: String
}

// MARK: - Receipts

struct ReceiptResponse: Codable {
    let id: String
    let merchantName: String?
    let transactionDate: String?
    let totalAmount: String?
    let taxAmount: String?
    let ocrConfidence: String?
    let isProcessed: Bool
    let createdAt: String
}

// MARK: - AI Query

struct AiQueryRequest: Codable {
    let query: String
}

struct AiQueryResponse: Codable {
    let query: String
    let interpretedAs: String
    let sqlGenerated: String?
    let results: [[String: String]]
    let tokenHash: String
    let cached: Bool

    init(
        query: String,
        interpretedAs: String,
        sqlGenerated: String? = nil,
        results: [[String: String]] = [],
        tokenHash: String,
        cached: Bool = false
    ) {
        self.query = query
        self.interpretedAs = interpretedAs
        self.sqlGenerated = sqlGenerated
        self.results = results
        self.tokenHash = tokenHash
        self.cached = cached
    }
}

// MARK: - Periods

struct PeriodResponse: Codable {
    let id: String
    let name: String
    let startDate: String
    let endDate: String
    let status: String
    let closedBy: String?
    let closedAt: String?
}

// MARK: - Audit

struct AuditLogResponse: Codable {
    let id: String
    let userId: String?
    let action: String
    let entityType: String
    let entityId: String
    let createdAt: String
}

// MARK: - Reconciliation

struct ReconciliationSuggestion: Codable {
    let transactionId: String
    let journalEntryId: String
    let matchScore: String
}

// MARK: - Health

struct HealthResponse: Codable {
    let status: String
    let version: String
}
