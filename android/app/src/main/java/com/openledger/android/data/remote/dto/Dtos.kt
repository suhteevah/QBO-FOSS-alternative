package com.openledger.android.data.remote.dto

import kotlinx.serialization.SerialName
import kotlinx.serialization.Serializable

// ── Auth ──────────────────────────────────────────────
@Serializable
data class LoginRequest(val email: String, val password: String)

@Serializable
data class TokenResponse(
    @SerialName("access_token") val accessToken: String,
    @SerialName("token_type") val tokenType: String = "bearer",
    val role: String,
)

@Serializable
data class UserResponse(
    val id: String,
    val email: String,
    @SerialName("full_name") val fullName: String? = null,
    val role: String,
    @SerialName("organization_id") val organizationId: String,
)

// ── API Keys (platform-aware for Android + iOS) ──────
@Serializable
data class ApiKeyCreateRequest(
    val name: String,
    val platform: String = "android",  // "android", "ios", "web", "cli"
    @SerialName("device_info") val deviceInfo: String? = null,
    @SerialName("expires_in_days") val expiresInDays: Int? = null,
)

@Serializable
data class ApiKeyCreateResponse(
    val id: String,
    val name: String,
    @SerialName("key_prefix") val keyPrefix: String,
    @SerialName("raw_key") val rawKey: String,
    val platform: String,
    @SerialName("device_info") val deviceInfo: String? = null,
    @SerialName("expires_at") val expiresAt: String? = null,
    @SerialName("created_at") val createdAt: String,
)

@Serializable
data class ApiKeyResponse(
    val id: String,
    val name: String,
    @SerialName("key_prefix") val keyPrefix: String,
    val platform: String,
    @SerialName("device_info") val deviceInfo: String? = null,
    @SerialName("expires_at") val expiresAt: String? = null,
    @SerialName("last_used_at") val lastUsedAt: String? = null,
    @SerialName("is_revoked") val isRevoked: Boolean,
    @SerialName("created_at") val createdAt: String,
)

// ── Accounts ──────────────────────────────────────────
@Serializable
data class AccountResponse(
    val id: String,
    @SerialName("account_number") val accountNumber: String,
    val name: String,
    val description: String? = null,
    @SerialName("account_type") val accountType: String,
    @SerialName("account_subtype") val accountSubtype: String? = null,
    @SerialName("normal_balance") val normalBalance: String,
    @SerialName("is_active") val isActive: Boolean,
)

// ── Journal Entries ───────────────────────────────────
@Serializable
data class LineItemResponse(
    val id: String,
    @SerialName("account_id") val accountId: String,
    val description: String? = null,
    @SerialName("debit_amount") val debitAmount: String,
    @SerialName("credit_amount") val creditAmount: String,
)

@Serializable
data class JournalEntryResponse(
    val id: String,
    @SerialName("entry_number") val entryNumber: String? = null,
    @SerialName("entry_date") val entryDate: String,
    val description: String? = null,
    val source: String,
    val status: String,
    @SerialName("ai_confidence") val aiConfidence: String? = null,
    @SerialName("line_items") val lineItems: List<LineItemResponse> = emptyList(),
    @SerialName("created_at") val createdAt: String,
)

@Serializable
data class LineItemCreate(
    @SerialName("account_id") val accountId: String,
    val description: String? = null,
    @SerialName("debit_amount") val debitAmount: String = "0.00",
    @SerialName("credit_amount") val creditAmount: String = "0.00",
)

@Serializable
data class JournalEntryCreate(
    @SerialName("entry_date") val entryDate: String,
    val description: String,
    val memo: String? = null,
    val source: String = "manual",
    @SerialName("line_items") val lineItems: List<LineItemCreate>,
)

// ── Transactions ──────────────────────────────────────
@Serializable
data class BankTransactionResponse(
    val id: String,
    @SerialName("transaction_date") val transactionDate: String,
    @SerialName("description_raw") val descriptionRaw: String,
    @SerialName("description_cleaned") val descriptionCleaned: String? = null,
    val amount: String,
    @SerialName("ai_category") val aiCategory: String? = null,
    @SerialName("ai_confidence") val aiConfidence: String? = null,
    @SerialName("is_reconciled") val isReconciled: Boolean,
    @SerialName("suggested_account_id") val suggestedAccountId: String? = null,
)

// ── Reports ───────────────────────────────────────────
@Serializable
data class ReportRequest(
    @SerialName("report_type") val reportType: String,
    @SerialName("start_date") val startDate: String,
    @SerialName("end_date") val endDate: String,
    @SerialName("accounting_basis") val accountingBasis: String? = null,
)

@Serializable
data class ReportLineItemDto(
    @SerialName("account_number") val accountNumber: String,
    @SerialName("account_name") val accountName: String,
    val amount: String,
)

@Serializable
data class ReportSection(
    val title: String,
    val items: List<ReportLineItemDto>,
    val subtotal: String,
)

@Serializable
data class ReportResponse(
    @SerialName("report_type") val reportType: String,
    val period: String,
    @SerialName("generated_at") val generatedAt: String,
    @SerialName("accounting_basis") val accountingBasis: String,
    val sections: List<ReportSection>,
    @SerialName("net_total") val netTotal: String,
)

// ── Receipts ──────────────────────────────────────────
@Serializable
data class ReceiptResponse(
    val id: String,
    @SerialName("merchant_name") val merchantName: String? = null,
    @SerialName("transaction_date") val transactionDate: String? = null,
    @SerialName("total_amount") val totalAmount: String? = null,
    @SerialName("tax_amount") val taxAmount: String? = null,
    @SerialName("ocr_confidence") val ocrConfidence: String? = null,
    @SerialName("is_processed") val isProcessed: Boolean,
    @SerialName("created_at") val createdAt: String,
)

// ── AI Query ──────────────────────────────────────────
@Serializable
data class AiQueryRequest(val query: String)

@Serializable
data class AiQueryResponse(
    val query: String,
    @SerialName("interpreted_as") val interpretedAs: String,
    @SerialName("sql_generated") val sqlGenerated: String? = null,
    val results: List<Map<String, String>> = emptyList(),
    @SerialName("token_hash") val tokenHash: String,
    val cached: Boolean = false,
)

// ── Periods ───────────────────────────────────────────
@Serializable
data class PeriodResponse(
    val id: String,
    val name: String,
    @SerialName("start_date") val startDate: String,
    @SerialName("end_date") val endDate: String,
    val status: String,
    @SerialName("closed_by") val closedBy: String? = null,
    @SerialName("closed_at") val closedAt: String? = null,
)

// ── Audit ─────────────────────────────────────────────
@Serializable
data class AuditLogResponse(
    val id: String,
    @SerialName("user_id") val userId: String? = null,
    val action: String,
    @SerialName("entity_type") val entityType: String,
    @SerialName("entity_id") val entityId: String,
    @SerialName("created_at") val createdAt: String,
)

// ── Reconciliation ────────────────────────────────────
@Serializable
data class ReconciliationSuggestion(
    @SerialName("transaction_id") val transactionId: String,
    @SerialName("journal_entry_id") val journalEntryId: String,
    @SerialName("match_score") val matchScore: String,
)

// ── Health ────────────────────────────────────────────
@Serializable
data class HealthResponse(val status: String, val version: String)
