package com.openledger.android.data.repository

import com.openledger.android.data.remote.OpenLedgerApi
import com.openledger.android.data.remote.dto.*
import javax.inject.Inject
import javax.inject.Singleton

@Singleton
class LedgerRepository @Inject constructor(
    private val api: OpenLedgerApi,
) {
    suspend fun getAccounts(): Result<List<AccountResponse>> = runCatching {
        val response = api.listAccounts()
        if (!response.isSuccessful) throw Exception("Failed: ${response.code()}")
        response.body()!!
    }

    suspend fun getJournalEntries(): Result<List<JournalEntryResponse>> = runCatching {
        val response = api.listJournalEntries()
        if (!response.isSuccessful) throw Exception("Failed: ${response.code()}")
        response.body()!!
    }

    suspend fun createJournalEntry(entry: JournalEntryCreate): Result<JournalEntryResponse> = runCatching {
        val response = api.createJournalEntry(entry)
        if (!response.isSuccessful) throw Exception("Failed: ${response.code()}")
        response.body()!!
    }

    suspend fun getTransactions(): Result<List<BankTransactionResponse>> = runCatching {
        val response = api.listTransactions()
        if (!response.isSuccessful) throw Exception("Failed: ${response.code()}")
        response.body()!!
    }

    suspend fun generateReport(request: ReportRequest): Result<ReportResponse> = runCatching {
        val response = when (request.reportType) {
            "profit_loss" -> api.profitLoss(request)
            "balance_sheet" -> api.balanceSheet(request)
            "trial_balance" -> api.trialBalance(request)
            else -> throw Exception("Unknown report type: ${request.reportType}")
        }
        if (!response.isSuccessful) throw Exception("Failed: ${response.code()}")
        response.body()!!
    }

    suspend fun getMe(): Result<UserResponse> = runCatching {
        val response = api.getMe()
        if (!response.isSuccessful) throw Exception("Failed: ${response.code()}")
        response.body()!!
    }

    suspend fun getPeriods(): Result<List<PeriodResponse>> = runCatching {
        val response = api.listPeriods()
        if (!response.isSuccessful) throw Exception("Failed: ${response.code()}")
        response.body()!!
    }

    suspend fun getAuditLogs(): Result<List<AuditLogResponse>> = runCatching {
        val response = api.listAuditLogs()
        if (!response.isSuccessful) throw Exception("Failed: ${response.code()}")
        response.body()!!
    }

    suspend fun aiQuery(query: String): Result<AiQueryResponse> = runCatching {
        val response = api.aiQuery(AiQueryRequest(query))
        if (!response.isSuccessful) throw Exception("Failed: ${response.code()}")
        response.body()!!
    }

    suspend fun autoMatch(): Result<List<ReconciliationSuggestion>> = runCatching {
        val response = api.autoMatch()
        if (!response.isSuccessful) throw Exception("Failed: ${response.code()}")
        response.body()!!
    }

    suspend fun getUnmatched(): Result<List<BankTransactionResponse>> = runCatching {
        val response = api.unmatchedItems()
        if (!response.isSuccessful) throw Exception("Failed: ${response.code()}")
        response.body()!!
    }
}
