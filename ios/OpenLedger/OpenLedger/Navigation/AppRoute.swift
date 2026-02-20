import Foundation

enum AppRoute: String, Hashable {
    // Auth flow
    case serverSetup = "server_setup"
    case login = "login"
    case apiKeySetup = "api_key_setup"

    // P0 -- Main tabs
    case dashboard = "dashboard"
    case transactions = "transactions"
    case journal = "journal"
    case accounts = "accounts"

    // P1 -- Core features
    case journalCreate = "journal_create"
    case receiptCapture = "receipt_capture"
    case reports = "reports"

    // P2 -- Advanced
    case reconciliation = "reconciliation"
    case aiQuery = "ai_query"
    case periods = "periods"
    case auditLog = "audit_log"
}
