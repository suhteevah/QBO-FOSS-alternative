package com.openledger.android.data.remote

import com.openledger.android.data.remote.dto.*
import okhttp3.MultipartBody
import retrofit2.Response
import retrofit2.http.*

interface OpenLedgerApi {

    // ── Health ────────────────────────────────────────
    @GET("health")
    suspend fun health(): Response<HealthResponse>

    // ── Auth ──────────────────────────────────────────
    @POST("api/auth/login")
    suspend fun login(@Body request: LoginRequest): Response<TokenResponse>

    @GET("api/auth/me")
    suspend fun getMe(): Response<UserResponse>

    // ── API Keys ──────────────────────────────────────
    @POST("api/keys/")
    suspend fun createApiKey(@Body request: ApiKeyCreateRequest): Response<ApiKeyCreateResponse>

    @GET("api/keys/")
    suspend fun listApiKeys(): Response<List<ApiKeyResponse>>

    @DELETE("api/keys/{id}")
    suspend fun revokeApiKey(@Path("id") id: String): Response<Map<String, String>>

    // ── Accounts ──────────────────────────────────────
    @GET("api/accounts/")
    suspend fun listAccounts(): Response<List<AccountResponse>>

    // ── Journal ───────────────────────────────────────
    @GET("api/journal/")
    suspend fun listJournalEntries(): Response<List<JournalEntryResponse>>

    @POST("api/journal/")
    suspend fun createJournalEntry(@Body entry: JournalEntryCreate): Response<JournalEntryResponse>

    @POST("api/journal/{id}/approve")
    suspend fun approveJournalEntry(@Path("id") id: String): Response<JournalEntryResponse>

    @POST("api/journal/{id}/void")
    suspend fun voidJournalEntry(@Path("id") id: String): Response<JournalEntryResponse>

    // ── Transactions ──────────────────────────────────
    @GET("api/transactions/")
    suspend fun listTransactions(): Response<List<BankTransactionResponse>>

    // ── Reports ───────────────────────────────────────
    @POST("api/reports/profit-loss")
    suspend fun profitLoss(@Body request: ReportRequest): Response<ReportResponse>

    @POST("api/reports/balance-sheet")
    suspend fun balanceSheet(@Body request: ReportRequest): Response<ReportResponse>

    @POST("api/reports/trial-balance")
    suspend fun trialBalance(@Body request: ReportRequest): Response<ReportResponse>

    // ── Receipts ──────────────────────────────────────
    @Multipart
    @POST("api/receipts/upload")
    suspend fun uploadReceipt(@Part file: MultipartBody.Part): Response<ReceiptResponse>

    // ── AI Query ──────────────────────────────────────
    @POST("api/ai/query")
    suspend fun aiQuery(@Body request: AiQueryRequest): Response<AiQueryResponse>

    // ── Reconciliation ────────────────────────────────
    @POST("api/reconciliation/auto-match")
    suspend fun autoMatch(): Response<List<ReconciliationSuggestion>>

    @GET("api/reconciliation/unmatched")
    suspend fun unmatchedItems(): Response<List<BankTransactionResponse>>

    // ── Periods ───────────────────────────────────────
    @GET("api/periods/")
    suspend fun listPeriods(): Response<List<PeriodResponse>>

    // ── Audit ─────────────────────────────────────────
    @GET("api/audit/")
    suspend fun listAuditLogs(): Response<List<AuditLogResponse>>
}
