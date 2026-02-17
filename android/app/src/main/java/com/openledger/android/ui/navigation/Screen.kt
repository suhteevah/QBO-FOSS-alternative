package com.openledger.android.ui.navigation

sealed class Screen(val route: String) {
    // Auth flow
    data object ServerSetup : Screen("server_setup")
    data object Login : Screen("login")
    data object ApiKeySetup : Screen("api_key_setup")

    // P0 — Main tabs
    data object Dashboard : Screen("dashboard")
    data object Transactions : Screen("transactions")
    data object Journal : Screen("journal")
    data object Accounts : Screen("accounts")

    // P1 — Core features
    data object JournalCreate : Screen("journal_create")
    data object ReceiptCapture : Screen("receipt_capture")
    data object Reports : Screen("reports")

    // P2 — Advanced
    data object Reconciliation : Screen("reconciliation")
    data object AiQuery : Screen("ai_query")
    data object Periods : Screen("periods")
    data object AuditLog : Screen("audit_log")
}
